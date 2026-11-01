"""O5 done-when: the model layer end to end, offline, against a real OwnerWorkflow.

The tool loop, recorded adapter, budget, call log, raw archive, export and replay run together.
No network (an autouse fixture makes the default transport raise), no provider env var is read:
every key here is a planted test value.
"""

import http.client
import json
import os
import socket
import traceback
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, NoReturn

import pytest
from _pack import (
    SPEC,
    Rig,
    failed,
    fw,
    gap_submit,
    make_rig,
    ok,
    read_financial,
    read_identity,
    ready_submit,
    submit,
    tool_call,
)

from deploy_vii.execution import Execution
from deploy_workflow.model import adapter as adapter_module
from deploy_workflow.model import transport as transport_module
from deploy_workflow.model.adapter import (
    AdapterReply,
    LiveAdapter,
    LivePauseInForce,
    live_adapter,
    recorded_adapter,
)
from deploy_workflow.model.budget import RunStopped
from deploy_workflow.model.loop import StepStopped
from deploy_workflow.model.record import export_recording
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.transport import Response
from deploy_workflow.model.turn import ToolCall, Turn, dump_json, turn_to_json
from deploy_workflow.owner_workflow import verify_owner_run_receipt

REPO = Path(__file__).resolve().parents[2]
PLANTED = "sk-or-v1-TESTONLY123456"
LIVE_KEY = "sk-proj-OPAQUETESTKEY0000000000"
TIMING = ("started_at", "first_byte_at", "finished_at")
CONFIG = SPEC.config_id


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """The default transport must raise: any request that escapes a fake is a test failure."""

    def refuse(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("a test reached the network")

    monkeypatch.setattr(http.client, "HTTPSConnection", refuse)
    monkeypatch.setattr(http.client, "HTTPConnection", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(transport_module, "_default_connection", refuse)


def test_the_default_transport_is_refused() -> None:
    with pytest.raises(AssertionError, match="network"):
        http.client.HTTPSConnection("example.invalid")
    with pytest.raises(AssertionError, match="network"):
        transport_module._default_connection("example.invalid", 443, 1.0)


# ---------------------------------------------------------------- authoring recordings

type Entry = Turn | dict[str, Any]


def turn_of(*calls: ToolCall, text: str = "") -> Turn:
    turn = ok(*calls, text=text).turn
    assert turn is not None
    return turn


def error_response(kind: str, error_class: str, status: int | None) -> dict[str, Any]:
    return {"kind": kind, "error_class": error_class, "http_status": status}


def _line(digest: str, index: int, entry: Entry) -> str:
    response = turn_to_json(entry) if isinstance(entry, Turn) else entry
    return (
        dump_json({"invocation_digest": digest, "call_index": index, "response": response}) + "\n"
    )


@dataclass
class Ran:
    rig: Rig
    outcomes: tuple[dict[str, Any], ...] | None
    stop: StepStopped | None


def run_recorded(root: Path, script: list[Entry], *, gap: bool = True, cap: str = "1") -> Ran:
    """Author the recording for the run's real digests and run it. The digest of each request is
    read from the ``RecordingMissing`` record of a run against the recordings written so far, then
    the next scripted response is written for it (test data in the real recording format, not a
    captured turn). The last run, with every response recorded, is the one returned."""
    recordings = root / "recordings"
    recordings.mkdir(parents=True)
    lines: list[str] = []
    for round_ in range(len(script) + 1):
        adapter = recorded_adapter(SPEC, recordings)
        rig = make_rig(root / f"run{round_}", [], gap=gap, cap=cap, adapter=adapter)
        try:
            return Ran(rig, rig.loop.run(), None)
        except StepStopped as stop:
            if stop.reason != "RecordingMissing":
                return Ran(rig, None, stop)
            assert round_ < len(script), "the run asked for a response the script does not hold"
            last = rig.records()[-1]
            assert last["invocation_digest"] in stop.detail  # the digest comes from the stop
            lines.append(_line(last["invocation_digest"], last["call_index"], script[round_]))
            (recordings / "run.jsonl").write_text("".join(lines))
    raise AssertionError("unreachable: the loop returns or raises")


def markers(rig: Rig) -> tuple[list[str], list[str]]:
    folder = rig.root / "store" / "owner-run-audit" / "reservations"
    names = sorted(p.name for p in folder.iterdir())
    return [n for n in names if not n.endswith(".settled")], [
        n for n in names if n.endswith(".settled")
    ]


def seal(rig: Rig) -> None:
    """Close the run, write the receipt and verify it; the new audit kinds must not break it."""
    audit = rig.root / "store" / "owner-run-audit"
    assert any((audit / "invocations").iterdir()) and any((audit / "reservations").iterdir())
    assert rig.workflow.publish()["status"] == "refused"  # the gap pack publishes nothing
    receipt = rig.workflow.write_receipt(rig.root / "receipt.json")
    verify_owner_run_receipt(Execution(rig.root / "store"), receipt, publication_directory=None)


def shape(rig: Rig) -> list[tuple[str, int, int]]:
    return [(r["step_id"], r["attempt"], r["call_index"]) for r in rig.records()]


# ---------------------------------------------------------------- the recorded step


def test_a_full_step_with_the_recorded_adapter(tmp_path: Path) -> None:
    script: list[Entry] = [
        turn_of(tool_call("search_pack", query="identity"), read_identity()),
        turn_of(gap_submit()),
    ]
    ran = run_recorded(tmp_path, script)
    assert ran.stop is None and ran.outcomes is not None
    assert ran.outcomes[-1]["status"] == "valid" and ran.outcomes[-1]["next_step"] is None
    rig = ran.rig
    records = rig.records()
    assert [r["call_index"] for r in records] == [0, 1]  # one record per provider request
    assert {r["schema_version"] for r in records} == {"model-call/1"}
    assert {r["cost_status"] for r in records} == {"computed"}
    assert all(r["error_class"] is None and r["first_byte_at"] is None for r in records)
    assert len({r["invocation_digest"] for r in records}) == 1
    digest = records[0]["invocation_digest"]
    assert (rig.root / "store" / "owner-run-audit" / "invocations" / digest).is_file()
    assert not (rig.run_dir / "raw").exists()  # a recorded reply holds no raw body
    held, settled = markers(rig)
    assert len(held) == 2 and len(settled) == 2
    assert rig.budget.spent == Decimal("0.008") and rig.budget.reserved == 0
    seal(rig)


def test_a_refused_submit_then_a_valid_one_keeps_the_digest_and_the_attempt(
    tmp_path: Path,
) -> None:
    script: list[Entry] = [turn_of(gap_submit()), turn_of(read_identity(), gap_submit())]
    ran = run_recorded(tmp_path, script)
    assert ran.outcomes is not None and ran.outcomes[-1]["status"] == "valid"
    first, second = ran.rig.records()
    assert shape(ran.rig) == [("source_readiness", 0, 0), ("source_readiness", 0, 1)]
    assert first["invocation_digest"] == second["invocation_digest"]
    assert first["tool_calls"][0]["refusal_code"] == "refused"
    assert second["tool_calls"][-1]["refusal_code"] == "cp1_not_authorized"  # the gap pack's end
    seal(ran.rig)


def _valid_context() -> ToolCall:
    return submit("source_context", fw.context(fw.make_pack(False)))


def test_an_invalid_submit_is_repaired_inside_the_attempt(tmp_path: Path) -> None:
    script: list[Entry] = [
        turn_of(read_identity(), read_financial(), ready_submit()),
        turn_of(submit("source_context", "{}")),  # invalid: the same attempt, the same step
        turn_of(
            read_identity(),
            read_financial(),
            tool_call("search_pack", query="subsequent", source_id="financial"),
            _valid_context(),
        ),
        turn_of(text="done"),  # the next step gets no submit: the run stops there
    ]
    ran = run_recorded(tmp_path, script, gap=False)
    assert ran.stop is not None and ran.stop.reason == "NoSubmit"
    rig = ran.rig
    assert shape(rig) == [
        ("source_readiness", 0, 0),
        ("source_context", 0, 0),
        ("source_context", 0, 1),  # same attempt, the next index
        ("financials", 0, 0),
    ]
    digests = [r["invocation_digest"] for r in rig.records()]
    assert digests[1] == digests[2] and len({digests[0], digests[1], digests[3]}) == 3
    assert [r["error_class"] for r in rig.records()] == [None, None, None, "NoSubmit"]


def test_a_second_invalid_submit_starts_a_new_attempt(tmp_path: Path) -> None:
    script: list[Entry] = [
        turn_of(read_identity(), read_financial(), ready_submit()),
        turn_of(submit("source_context", "{}")),
        turn_of(submit("source_context", "{}")),
        turn_of(text="done"),
    ]
    ran = run_recorded(tmp_path, script, gap=False)
    assert ran.stop is not None and ran.stop.reason == "NoSubmit"
    assert shape(ran.rig) == [
        ("source_readiness", 0, 0),
        ("source_context", 0, 0),
        ("source_context", 0, 1),
        ("source_context", 1, 0),  # attempt 0 finished invalid: attempt 1 starts over
    ]
    digests = [r["invocation_digest"] for r in ran.rig.records()]
    assert digests[1] == digests[2] != digests[3]


# ---------------------------------------------------------------- budget


class Counting:
    """Counts what reaches the adapter; answers as the wrapped recorded adapter does."""

    def __init__(self, inner: Any) -> None:
        self.inner, self.config_id, self.sent = inner, inner.config_id, 0

    @property
    def ruling(self) -> Path | None:
        return None

    def complete(self, request: Any, **kwargs: Any) -> AdapterReply:
        self.sent += 1
        reply: AdapterReply = self.inner.complete(request, **kwargs)
        return reply


def test_a_reservation_above_the_cap_is_not_sent_and_is_recorded(tmp_path: Path) -> None:
    empty = tmp_path / "recordings"
    empty.mkdir()
    counting = Counting(recorded_adapter(SPEC, empty))
    rig = make_rig(tmp_path / "run", [], cap="0.001", adapter=counting)
    with pytest.raises(StepStopped) as stopped:
        rig.loop.run()
    assert stopped.value.reason == "BudgetExhausted" and counting.sent == 0
    (record,) = rig.records()
    assert record["error_class"] == "BudgetExhausted"
    assert (record["reserved_usd"], record["settled_usd"]) == ("0", "0")
    assert rig.budget.spent == 0 and markers(rig) == ([], [])


def test_an_unknown_charge_holds_the_reservation_and_stops_the_run(tmp_path: Path) -> None:
    script: list[Entry] = [error_response("sent_unknown", "OverallTimeout", None)]
    ran = run_recorded(tmp_path, script)
    assert ran.stop is not None and ran.stop.reason == "OverallTimeout"
    (record,) = ran.rig.records()
    assert (record["cost_status"], record["settled_usd"]) == ("unknown", None)
    assert record["http_status"] is None and Decimal(record["reserved_usd"]) > 0
    assert ran.rig.budget.spent == Decimal(record["reserved_usd"])  # held and counted
    with pytest.raises(RunStopped):
        ran.rig.budget.reserve("next-call", Decimal("0.001"), config_id=CONFIG)


# ---------------------------------------------------------------- the live pause


class Trap(Mapping[str, str]):
    """Any read of the mapping is a test failure."""

    def __init__(self) -> None:
        self.touched: list[str] = []

    def _trip(self, what: str) -> NoReturn:
        self.touched.append(what)
        raise AssertionError(f"environment touched: {what}")

    def __getitem__(self, key: str) -> str:
        self._trip("__getitem__")

    def __iter__(self) -> Iterator[str]:
        self._trip("__iter__")

    def __len__(self) -> int:
        self.touched.append("__len__")
        raise AssertionError("environment touched: __len__")

    def __contains__(self, key: object) -> bool:
        self._trip("__contains__")


def test_the_live_pause_refuses_and_touches_no_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    ruling = REPO / "docs" / "rulings" / "2026-10-31-context-plan.md"
    assert ruling.is_file()
    trap, os_trap = Trap(), Trap()
    with monkeypatch.context() as scoped:  # pytest itself reads os.environ outside the test body
        scoped.setattr(os, "environ", os_trap)
        for environ in (trap, None):
            with pytest.raises(LivePauseInForce):
                live_adapter(SPEC, ruling, environ=environ)
    assert trap.touched == [] and os_trap.touched == []


# ---------------------------------------------------------------- the live-shaped offline run


def _body(*calls: tuple[str, dict[str, Any]]) -> bytes:
    output: list[dict[str, Any]] = [
        {"type": "function_call", "call_id": f"c{i}", "name": name, "arguments": json.dumps(args)}
        for i, (name, args) in enumerate(calls)
    ]
    return json.dumps(
        {
            "id": "resp_1",
            "model": "gpt-6.1-sol",
            "status": "completed",
            "output": output,
            "usage": {"input_tokens": 900, "output_tokens": 20},
        }
    ).encode()


def live_over(
    root: Path, monkeypatch: pytest.MonkeyPatch, responses: list[Response], environ: dict[str, str]
) -> tuple[LiveAdapter, list[Any]]:
    """A real ``LiveAdapter`` over a fake transport: a tmp ruling under a patched rulings root."""
    rulings = root / "rulings"
    rulings.mkdir(parents=True)
    ruling = rulings / "lift.md"
    ruling.write_text(
        f"lifts: live-provider-pause\nby: user\ndate: 2026-11-01\nconfigs: {CONFIG}\n"
    )
    monkeypatch.setattr(adapter_module, "LIVE_RULINGS_ROOT", rulings)
    queue, requests = list(responses), []

    def transport(request: Any) -> Response:
        requests.append(request)
        return queue.pop(0)

    adapter = live_adapter(SPEC, ruling, transport=transport, environ=environ, clock=lambda: 100.0)
    return adapter, requests


def test_a_live_shaped_run_archives_raw_and_replays_to_the_same_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environ = {
        "OPENAI_API_KEY": LIVE_KEY,
        "ANTHROPIC_API_KEY": "sk-ant-OPAQUETESTKEY000000000000",
        "OPENROUTER_API_KEY": "sk-or-v1-OPAQUETESTKEY0000000000",
    }
    reads: list[tuple[str, dict[str, Any]]] = [
        ("search_pack", {"query": "identity"}),
        ("read_pages", {"source_id": "identity", "first_page": 1, "last_page": 1}),
    ]
    payload = json.loads(fw.readiness(fw.make_pack(True), gap=True))
    responses = [
        Response(200, _body(*reads), {}),
        Response(200, _body(("submit_source_readiness", payload)), {}),
    ]
    live, requests = live_over(tmp_path, monkeypatch, responses, environ)
    first = make_rig(tmp_path / "live", [], adapter=live, redactor=Redactor.from_environ(environ))
    assert first.loop.run()[-1]["status"] == "valid"
    assert len(requests) == 2
    records = first.records()
    assert [r["call_index"] for r in records] == [0, 1]
    assert {r["cost_status"] for r in records} == {"computed"}
    assert all(r["first_byte_at"] is None for r in records)
    digest = records[0]["invocation_digest"]
    for index in (0, 1):  # the redacted raw body of each call
        archived = json.loads((first.run_dir / "raw" / f"{digest}-{index}.json").read_text())
        assert archived["id"] == "resp_1"
    seal(first)

    recordings = tmp_path / "recordings"
    recordings.mkdir()
    exported = export_recording(
        first.run_dir, recordings / "run.jsonl", Redactor.from_environ(environ)
    )
    assert exported == 2
    replay = make_rig(tmp_path / "replay", [], adapter=recorded_adapter(SPEC, recordings))
    assert replay.loop.run()[-1]["status"] == "valid"
    assert not (replay.run_dir / "raw").exists()

    def without_timing(rig: Rig) -> list[dict[str, Any]]:
        return [{k: v for k, v in r.items() if k not in TIMING} for r in rig.records()]

    assert without_timing(replay) == without_timing(first)
    assert all(r["first_byte_at"] is None for r in replay.records())
    seal(replay)


# ---------------------------------------------------------------- a planted key reaches nothing


def _files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file()]


def _no_key_anywhere(root: Path, *keys: str) -> None:
    files = _files(root)
    assert files
    for path in files:
        data = path.read_bytes()
        for key in keys:
            assert key.encode() not in data, f"{key[:8]}... is in {path.relative_to(root)}"


class Boom(Exception):
    pass


def _chained() -> BaseException:
    try:
        raise Boom(f"provider failed with {PLANTED}") from ValueError(f"inner {PLANTED}")
    except Boom as error:
        return error


def test_a_key_in_a_tool_argument_and_a_raw_response_reaches_no_file(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    raw = b'{"echo":"' + PLANTED.encode() + b'"}'
    reply = ok(tool_call("search_pack", query=PLANTED), read_identity(), gap_submit(), raw=raw)
    rig = make_rig(tmp_path, [reply], redactor=Redactor([PLANTED]))
    assert rig.loop.run()[-1]["status"] == "valid"
    assert (rig.run_dir / "raw").is_dir()
    calls = list((rig.root / "store" / "owner-run-audit" / "calls").iterdir())
    assert any(b"[redacted]" in p.read_bytes() for p in calls)  # the call was made, redacted
    _no_key_anywhere(tmp_path, PLANTED)
    captured = capfd.readouterr()
    assert PLANTED not in captured.out + captured.err


@pytest.mark.parametrize("scenario", ["provider-error", "exception-chain"])
def test_a_key_in_a_provider_error_or_an_exception_chain_reaches_no_file(
    tmp_path: Path, capfd: pytest.CaptureFixture[str], scenario: str
) -> None:
    script: list[AdapterReply | BaseException] = [
        failed(
            "sent_known",
            "ProviderRejected",
            400,
            message=f"rejected {PLANTED}",
            raw=b'{"error":"' + PLANTED.encode() + b'"}',
        )
        if scenario == "provider-error"
        else _chained()
    ]
    rig = make_rig(tmp_path, script, redactor=Redactor([PLANTED]))
    with pytest.raises(StepStopped) as stopped:
        rig.loop.run()
    shown = "".join(traceback.format_exception(stopped.value)) + str(stopped.value)
    assert PLANTED not in shown and stopped.value.__cause__ is None
    _no_key_anywhere(tmp_path, PLANTED)
    captured = capfd.readouterr()
    assert PLANTED not in captured.out + captured.err


def test_a_key_reflected_by_a_live_shaped_reply_reaches_no_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    environ = {"OPENAI_API_KEY": LIVE_KEY}
    body = json.dumps({"error": {"message": f"invalid key {LIVE_KEY}"}}).encode()
    live, _ = live_over(tmp_path, monkeypatch, [Response(400, body, {})], environ)
    rig = make_rig(tmp_path / "run", [], adapter=live, redactor=Redactor.from_environ(environ))
    with pytest.raises(StepStopped) as stopped:
        rig.loop.run()
    assert stopped.value.reason == "KeyReflected"
    assert LIVE_KEY not in str(stopped.value)
    _no_key_anywhere(tmp_path, LIVE_KEY)
    captured = capfd.readouterr()
    assert LIVE_KEY not in captured.out + captured.err
