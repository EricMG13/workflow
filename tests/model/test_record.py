"""model-call/1 records, the redacted raw archive and the invocation digest audit. No network."""

import hashlib
import json
import os
import threading
import traceback
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

from deploy_workflow.model.adapter import recorded_adapter
from deploy_workflow.model.providers import ProviderError, parse
from deploy_workflow.model.record import (
    CallLog,
    CallRecord,
    ExportMismatch,
    RawExists,
    RawMissing,
    RecordInvalid,
    ToolCallRecord,
    TornLog,
    arguments_sha256,
    export_recording,
    invocation_digest,
    invocation_preimage,
    retain_preimage,
)
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.turn import ModelSpec, TurnRequest

SECRET = "sk-or-v1-TESTONLY123456"
OPAQUE = "opaque-secret-value"
NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
DIGEST = "a" * 64
TOOL = ToolCallRecord(name="submit", arguments_sha256="b" * 64, result_bytes=12, refusal_code=None)


def fields(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": "model-call/1",
        "run_id": "run-1",
        "case_id": "case-1",
        "pathway": "credit_snapshot",
        "module_id": "CP-1",
        "step_id": "step-1",
        "attempt": 0,
        "call_index": 0,
        "config_id": "sol-medium",
        "provider": "openai",
        "requested_model": "gpt-6.1-sol",
        "reported_model": "gpt-6.1-sol",
        "requested_effort": "medium",
        "invocation_digest": DIGEST,
        "request_id": "req-1",
        "http_status": 200,
        "started_at": NOW,
        "first_byte_at": None,
        "finished_at": NOW,
        "input_tokens": None,
        "cached_read_tokens": None,
        "cache_write_tokens": None,
        "output_tokens": 0,
        "reasoning_tokens": None,
        "reserved_usd": Decimal("0.01"),
        "settled_usd": Decimal("0.0028"),
        "cost_status": "computed",
        "tool_calls": (),
        "submit_sha256": None,
        "error_class": None,
        "error": None,
    }
    base.update(over)
    return base


def record(**over: Any) -> CallRecord:
    return CallRecord(**fields(**over))


def lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text().splitlines()]


def test_round_trip_line(tmp_path: Path) -> None:
    log = CallLog(tmp_path, Redactor())
    log.append(record(tool_calls=(TOOL,)))
    (line,) = lines(tmp_path / "calls.jsonl")
    assert line["input_tokens"] is None
    assert line["output_tokens"] == 0
    assert line["settled_usd"] == "0.0028"
    assert line["reserved_usd"] == "0.01"
    assert line["schema_version"] == "model-call/1"
    assert set(line) == set(CallRecord.model_fields)
    assert line["tool_calls"][0]["name"] == "submit"
    assert CallRecord.model_validate_json(json.dumps(line)) == record(tool_calls=(TOOL,))


@pytest.mark.parametrize(
    "over",
    [
        {"cost_status": "unknown", "settled_usd": Decimal(1)},
        {"cost_status": "billed", "settled_usd": None},
        {"cost_status": "computed", "settled_usd": None},
        {"call_index": -1},
        {"attempt": 2},
        {"nonsense": 1},
        {"invocation_digest": "xyz"},
        {"error": f"boom {SECRET}"},
        {"step_id": f"{SECRET}"},
    ],
)
def test_invalid_records_refused(over: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        record(**over)


def test_unknown_with_no_settled_value_is_valid() -> None:
    assert record(cost_status="unknown", settled_usd=None).settled_usd is None


def test_validation_error_never_echoes_the_secret() -> None:
    with pytest.raises(ValidationError) as caught:
        record(error=SECRET)
    shown = str(caught.value) + "".join(traceback.format_exception(caught.value))
    assert "TESTONLY123456" not in shown


def test_opaque_env_value_is_redacted_from_the_written_line(tmp_path: Path) -> None:
    redactor = Redactor.from_environ({"OPENAI_API_KEY": OPAQUE})
    log = CallLog(tmp_path, redactor)
    log.append(record(error=f"failed with {OPAQUE} inside", error_class="X"))
    assert OPAQUE not in (tmp_path / "calls.jsonl").read_text()


def test_chained_exception_in_error_is_absent_from_the_log(tmp_path: Path) -> None:
    redactor = Redactor.from_environ({"OPENAI_API_KEY": OPAQUE})
    try:
        try:
            raise RuntimeError(f"inner {OPAQUE}")
        except RuntimeError as inner:
            raise ValueError("outer") from inner
    except ValueError as exc:
        err = redactor.exception(exc)
    log = CallLog(tmp_path, redactor)
    log.append(record(error=err, error_class="ValueError"))
    text = (tmp_path / "calls.jsonl").read_text()
    assert OPAQUE not in text
    assert "inner" in text


def test_refused_record() -> None:
    redactor = Redactor.from_environ({"OPENAI_API_KEY": OPAQUE})
    rec = CallRecord.refused(
        redactor,
        **{
            k: v
            for k, v in fields().items()
            if k
            not in {
                "reserved_usd",
                "settled_usd",
                "cost_status",
                "error_class",
                "error",
                "input_tokens",
                "cached_read_tokens",
                "cache_write_tokens",
                "output_tokens",
                "reasoning_tokens",
            }
        },
        error_class="BudgetExhausted",
        error=f"cap hit {OPAQUE}",
    )
    assert (rec.reserved_usd, rec.settled_usd, rec.cost_status) == (
        Decimal(0),
        Decimal(0),
        "computed",
    )
    assert rec.input_tokens is None and rec.output_tokens is None
    assert rec.error_class == "BudgetExhausted"
    assert OPAQUE not in (rec.error or "")


def test_raw_is_redacted_named_and_create_once(tmp_path: Path) -> None:
    redactor = Redactor.from_environ({"OPENAI_API_KEY": OPAQUE})
    log = CallLog(tmp_path, redactor)
    body = json.dumps({"echo": f"{SECRET} and {OPAQUE}", "n": 1}).encode()
    path = log.write_raw(DIGEST, 0, body)
    assert path == tmp_path / "raw" / f"{DIGEST}-0.json"
    text = path.read_text()
    assert "TESTONLY123456" not in text and OPAQUE not in text
    assert json.loads(text)["n"] == 1
    with pytest.raises(RawExists):
        log.write_raw(DIGEST, 0, body)
    assert log.write_raw(DIGEST, 1, body).name == f"{DIGEST}-1.json"


def test_raw_non_json_is_a_json_string(tmp_path: Path) -> None:
    log = CallLog(tmp_path, Redactor())
    path = log.write_raw(DIGEST, 0, b"data: hello\n\ndata: [DONE]\n")
    assert json.loads(path.read_text()) == "data: hello\n\ndata: [DONE]\n"


@pytest.mark.parametrize("digest, index", [("../x", 0), (DIGEST, -1), ("A" * 64, 0)])
def test_raw_refuses_bad_names(tmp_path: Path, digest: str, index: int) -> None:
    with pytest.raises(ValueError):
        CallLog(tmp_path, Redactor()).write_raw(digest, index, b"{}")


def test_call_indexes(tmp_path: Path) -> None:
    log = CallLog(tmp_path, Redactor())
    assert log.next_call_index("CP-1", "step-1", 0) == 0
    for expected in (0, 1, 2):
        index = log.next_call_index("CP-1", "step-1", 0)
        assert index == expected
        log.append(record(call_index=index))
    assert log.next_call_index("CP-1", "step-1", 1) == 0
    assert log.next_call_index("CP-1", "step-2", 0) == 0
    assert log.next_call_index("CP-2", "step-1", 0) == 0


def test_concurrent_appends_stay_intact(tmp_path: Path) -> None:
    log = CallLog(tmp_path, Redactor())

    def work(t: int) -> None:
        for i in range(50):
            log.append(record(step_id=f"s{t}", call_index=i))

    threads = [threading.Thread(target=work, args=(t,)) for t in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(lines(tmp_path / "calls.jsonl")) == 100


PREIMAGE: dict[str, Any] = {
    "run_id": "run-1",
    "module_id": "CP-1",
    "step_id": "step-1",
    "attempt": 0,
    "upstream_hashes": ["c" * 64, "b" * 64],
    "prompt_sha256": "d" * 64,
}


def digest_of(**over: Any) -> str:
    return invocation_digest(**{**PREIMAGE, **over})


def test_digest_value_and_sensitivity() -> None:
    expected = hashlib.sha256(
        json.dumps(
            {
                "run_id": "run-1",
                "module_id": "CP-1",
                "step_id": "step-1",
                "attempt": 0,
                "upstream_hashes": ["b" * 64, "c" * 64],
                "prompt_sha256": "d" * 64,
                "method_version": "deploy-v-r14",
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    assert digest_of() == expected
    assert digest_of(upstream_hashes=["b" * 64, "c" * 64]) == expected
    for name, value in {
        "run_id": "run-2",
        "module_id": "CP-2",
        "step_id": "step-2",
        "attempt": 1,
        "upstream_hashes": ["b" * 64],
        "prompt_sha256": "e" * 64,
        "method_version": "deploy-v-r15",
    }.items():
        assert digest_of(**{name: value}) != expected, name


def test_retain_preimage_create_once(tmp_path: Path) -> None:
    store = SimpleNamespace(directory=tmp_path)
    pre = invocation_preimage(**PREIMAGE)
    digest = retain_preimage(store, pre)
    assert digest == digest_of()
    retain_preimage(store, pre)
    path = tmp_path / "owner-run-audit" / "invocations" / digest
    assert json.loads(path.read_bytes())["run_id"] == "run-1"
    path.write_bytes(b"{}")
    with pytest.raises(ValueError, match="corrupt"):
        retain_preimage(store, pre)


OPENAI_BODY = {
    "id": "resp_1",
    "model": "gpt-6.1-sol",
    "status": "completed",
    "output": [{"type": "message", "content": [{"type": "output_text", "text": "hello"}]}],
    "usage": {"input_tokens": 10, "output_tokens": 5},
}


OK_RECORD = record(request_id="resp_1", input_tokens=10, output_tokens=5)


def test_export_recording_replays_through_recorded_adapter(tmp_path: Path) -> None:
    run, out = tmp_path / "run", tmp_path / "rec"
    run.mkdir()
    out.mkdir()
    log = CallLog(run, Redactor())
    log.write_raw(DIGEST, 0, json.dumps(OPENAI_BODY).encode())
    log.append(OK_RECORD)
    export_recording(run, out / "r.jsonl", Redactor())
    model = ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium")
    reply = recorded_adapter(model, out).complete(
        TurnRequest((), (), 10, "medium"),
        invocation_digest=DIGEST,
        call_index=0,
        reservation_id="r",
    )
    assert reply.kind == "ok"
    assert reply.turn is not None and reply.turn.text == "hello"
    assert reply.usage is not None and reply.usage.output_tokens == 5


def test_export_recording_error_reply(tmp_path: Path) -> None:
    run, out = tmp_path / "run", tmp_path / "rec"
    run.mkdir()
    out.mkdir()
    log = CallLog(run, Redactor())
    log.write_raw(DIGEST, 0, json.dumps({"error": {"message": "bad request"}}).encode())
    log.append(record(http_status=400, cost_status="computed", error_class="HttpError"))
    export_recording(run, out / "r.jsonl", Redactor())
    model = ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium")
    reply = recorded_adapter(model, out).complete(
        TurnRequest((), (), 10, "medium"),
        invocation_digest=DIGEST,
        call_index=0,
        reservation_id="r",
    )
    assert reply.kind != "ok" and reply.http_status == 400


def test_export_recording_raw_missing(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    CallLog(run, Redactor()).append(OK_RECORD)
    with pytest.raises(RawMissing):
        export_recording(run, tmp_path / "r.jsonl", Redactor())


@pytest.mark.parametrize(
    "status, kind, error_class",
    [("unknown", "sent_unknown", "IdleTimeout"), ("computed", "not_sent", "KeyMissing")],
)
def test_export_null_status_records_use_the_ruled_format(
    tmp_path: Path, status: str, kind: str, error_class: str
) -> None:
    run = tmp_path / "run"
    run.mkdir()
    CallLog(run, Redactor()).append(
        record(
            http_status=None,
            cost_status=status,
            settled_usd=None if status == "unknown" else Decimal(0),
            error_class=error_class,
        )
    )
    out = tmp_path / "r.jsonl"
    assert export_recording(run, out, Redactor()) == 1
    assert json.loads(out.read_text())["response"] == {
        "kind": kind,
        "error_class": error_class,
        "http_status": None,
    }


def test_adapter_reads_null_status_recording(tmp_path: Path) -> None:
    run, out = tmp_path / "run", tmp_path / "rec"
    run.mkdir()
    out.mkdir()
    CallLog(run, Redactor()).append(
        record(
            http_status=None,
            cost_status="unknown",
            settled_usd=None,
            error_class="IdleTimeout",
        )
    )
    export_recording(run, out / "r.jsonl", Redactor())
    model = ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium")
    reply = recorded_adapter(model, out).complete(
        TurnRequest((), (), 10, "medium"),
        invocation_digest=DIGEST,
        call_index=0,
        reservation_id="r",
    )
    assert reply.kind == "sent_unknown" and reply.http_status is None


# ---------------------------------------------------------------- fix round 1


ANTHROPIC = {
    "provider": "anthropic",
    "config_id": "opus-medium",
    "requested_model": "claude-opus-5-5",
}


def sse(*deltas: str) -> str:
    events: list[dict[str, Any]] = [
        {
            "type": "message_start",
            "message": {"id": "msg_1", "model": "claude-opus-5-5", "usage": {"input_tokens": 3}},
        },
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
    ]
    events += [
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": t}}
        for t in deltas
    ]
    events += [
        {"type": "content_block_stop", "index": 0},
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn"},
            "usage": {"output_tokens": 4},
        },
        {"type": "message_stop"},
    ]
    return "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events)


def archived(path: Path) -> Any:
    return json.loads(path.read_text())


def test_raw_withholds_key_reflected_by_record(tmp_path: Path) -> None:
    log = CallLog(tmp_path, Redactor())
    path = log.write_raw(DIGEST, 0, b'{"a": 1}', error_class="KeyReflected")
    assert archived(path) == "[withheld: KeyReflected; 8 bytes]"


def test_raw_withholds_invalid_utf8(tmp_path: Path) -> None:
    body = SECRET.encode("utf-16-le")
    path = CallLog(tmp_path, Redactor()).write_raw(DIGEST, 0, body, error_class=None)
    assert archived(path) == f"[withheld: InvalidUtf8; {len(body)} bytes]"


def test_raw_withholds_bytes_that_are_not_utf8(tmp_path: Path) -> None:
    path = CallLog(tmp_path, Redactor()).write_raw(DIGEST, 0, b'{"a": "\xff"}')
    assert archived(path) == "[withheld: InvalidUtf8; 10 bytes]"


@pytest.mark.parametrize(
    "text",
    [
        sse("x sk-or", "-v1-TESTONLY123456 y"),
        sse("PH").replace("PH", "\\u0073" + SECRET[1:]),
        sse("PH").replace("PH", "\\u006f" + OPAQUE[1:]),
    ],
    ids=["split", "escaped", "escaped-env"],
)
def test_raw_withholds_bodies_that_hold_a_key_once_decoded(tmp_path: Path, text: str) -> None:
    red = Redactor.from_environ({"ANTHROPIC_API_KEY": OPAQUE})
    path = CallLog(tmp_path, red).write_raw(DIGEST, 0, red.bytes_(text.encode()))
    stored = archived(path)
    assert stored.startswith("[withheld: KeyReflected;")
    again = parse("anthropic", 200, stored.encode(), {}, red)
    assert not (isinstance(again, ProviderError) and again.error_class == "KeyReflected")


def test_raw_survives_a_deeply_nested_body(tmp_path: Path) -> None:
    body = ("[" * 100000 + "]" * 100000).encode()
    path = CallLog(tmp_path, Redactor()).write_raw(DIGEST, 0, body)
    assert path.is_file()


def test_planted_key_in_sse_is_absent_from_raw(tmp_path: Path) -> None:
    body = sse(f"k {SECRET}").encode()
    path = CallLog(tmp_path, Redactor()).write_raw(DIGEST, 0, body)
    assert "TESTONLY123456" not in path.read_text()


def test_anthropic_sse_exports_and_replays(tmp_path: Path) -> None:
    run, out = tmp_path / "run", tmp_path / "rec"
    run.mkdir()
    out.mkdir()
    log = CallLog(run, Redactor())
    log.write_raw(DIGEST, 0, sse("hel", "lo").encode())
    log.append(
        record(
            **ANTHROPIC,
            request_id="msg_1",
            reported_model="claude-opus-5-5",
            input_tokens=3,
            output_tokens=4,
        )
    )
    export_recording(run, out / "r.jsonl", Redactor())
    model = ModelSpec("opus-medium", "anthropic", "claude-opus-5-5", "medium")
    reply = recorded_adapter(model, out).complete(
        TurnRequest((), (), 10, "medium"),
        invocation_digest=DIGEST,
        call_index=0,
        reservation_id="r",
    )
    assert reply.turn is not None and reply.turn.text == "hello"


def test_torn_tail_is_refused(tmp_path: Path) -> None:
    log = CallLog(tmp_path, Redactor())
    log.append(record())
    path = tmp_path / "calls.jsonl"
    path.write_bytes(path.read_bytes() + b'{"torn')
    before = path.read_bytes()
    with pytest.raises(TornLog):
        log.append(record(call_index=1))
    assert path.read_bytes() == before


def test_raw_is_linked_into_place_without_temp_files(tmp_path: Path) -> None:
    log = CallLog(tmp_path, Redactor())
    log.write_raw(DIGEST, 0, b"{}")
    with pytest.raises(RawExists):
        log.write_raw(DIGEST, 0, b"{}")
    assert sorted(p.name for p in (tmp_path / "raw").iterdir()) == [f"{DIGEST}-0.json"]


def test_directories_are_fsynced_after_creating_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: dict[int, str] = {}
    synced: list[str] = []
    real_open, real_fsync = os.open, os.fsync

    def spy_open(p: Any, *a: Any, **k: Any) -> int:
        fd = real_open(p, *a, **k)
        opened[fd] = str(p)
        return fd

    def spy_fsync(fd: int) -> None:
        synced.append(opened.get(fd, "?"))
        real_fsync(fd)

    monkeypatch.setattr(os, "open", spy_open)
    monkeypatch.setattr(os, "fsync", spy_fsync)
    run = tmp_path / "run"
    log = CallLog(run, Redactor())
    log.append(record())
    log.write_raw(DIGEST, 0, b"{}")
    assert str(run) in synced and str(run / "raw") in synced


def test_empty_crash_left_raw_file_is_raw_missing(tmp_path: Path) -> None:
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / f"{DIGEST}-0.json").write_bytes(b"")
    CallLog(tmp_path, Redactor()).append(OK_RECORD)
    with pytest.raises(RawMissing):
        export_recording(tmp_path, tmp_path / "o.jsonl", Redactor())


# R2: export follows the record


def exported(tmp_path: Path, *records: CallRecord, bodies: dict[int, bytes] | None = None) -> Any:
    run = tmp_path / "run"
    log = CallLog(run, Redactor())
    for index, body in (bodies or {}).items():
        log.write_raw(DIGEST, index, body)
    for rec in records:
        log.append(rec)
    out = tmp_path / "o.jsonl"
    export_recording(run, out, Redactor())
    return [json.loads(x)["response"] for x in out.read_text().splitlines()]


def test_key_reflected_record_exports_sent_unknown(tmp_path: Path) -> None:
    body = json.dumps(OPENAI_BODY).encode()
    (resp,) = exported(
        tmp_path,
        record(
            cost_status="unknown", settled_usd=None, error_class="KeyReflected", output_tokens=None
        ),
        bodies={0: body},
    )
    assert (resp["kind"], resp["error_class"], resp["http_status"]) == (
        "sent_unknown",
        "KeyReflected",
        200,
    )


def test_invalid_utf8_error_exports_the_records_kind(tmp_path: Path) -> None:
    (resp,) = exported(
        tmp_path,
        record(
            http_status=400,
            cost_status="unknown",
            settled_usd=None,
            error_class="Http",
            output_tokens=None,
        ),
        bodies={0: b'{"error": {"message": "bad \xff"}}'},
    )
    assert resp["kind"] == "sent_unknown"


def test_error_record_with_usage_and_billed_exports_them(tmp_path: Path) -> None:
    (resp,) = exported(
        tmp_path,
        record(
            http_status=422,
            cost_status="billed",
            settled_usd=Decimal("0.5"),
            error_class="Refusal",
            input_tokens=7,
            output_tokens=2,
        ),
    )
    assert resp["kind"] == "sent_usage" and resp["billed_usd"] == "0.5"
    assert resp["usage"]["input_tokens"] == 7 and resp["usage"]["output_tokens"] == 2


def test_error_record_is_not_reparsed_so_no_raw_is_needed(tmp_path: Path) -> None:
    (resp,) = exported(tmp_path, record(http_status=400, error_class="Http", output_tokens=None))
    assert resp["kind"] == "sent_known"


def test_ok_record_disagreeing_with_raw_is_refused(tmp_path: Path) -> None:
    body = json.dumps(OPENAI_BODY).encode()
    cases: list[tuple[dict[str, Any], str]] = [
        ({"output_tokens": 999}, "usage"),
        ({"request_id": "other"}, "request_id"),
        ({"reported_model": "other"}, "reported_model"),
    ]
    for over, name in cases:
        rec = record(request_id="resp_1", input_tokens=10, output_tokens=5)
        rec = rec.model_copy(update=over)
        with pytest.raises(ExportMismatch) as caught:
            exported(tmp_path / name, rec, bodies={0: body})
        assert caught.value.field == name


def test_ok_record_with_a_raw_that_is_not_a_turn_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ExportMismatch):
        exported(tmp_path, OK_RECORD, bodies={0: b"not json at all"})


def test_ok_record_tool_call_hash_must_match(tmp_path: Path) -> None:
    body = json.dumps(
        {
            **OPENAI_BODY,
            "output": [
                {
                    "type": "function_call",
                    "call_id": "c1",
                    "name": "submit",
                    "arguments": '{"k": 1}',
                }
            ],
        }
    ).encode()
    good = ToolCallRecord(
        name="submit",
        arguments_sha256=arguments_sha256({"k": 1}),
        result_bytes=None,
        refusal_code=None,
    )
    base = {"request_id": "resp_1", "input_tokens": 10, "output_tokens": 5}
    assert exported(tmp_path / "ok", record(**base, tool_calls=(good,)), bodies={0: body})
    bad = good.model_copy(update={"arguments_sha256": "f" * 64})
    with pytest.raises(ExportMismatch):
        exported(tmp_path / "bad", record(**base, tool_calls=(bad,)), bodies={0: body})


@pytest.mark.parametrize(
    "error_class, cost, settled",
    [("IdleTimeout", "computed", Decimal(0)), ("KeyMissing", "unknown", None)],
)
def test_null_status_kind_must_agree_with_cost_status(
    tmp_path: Path, error_class: str, cost: str, settled: Decimal | None
) -> None:
    with pytest.raises(ExportMismatch):
        exported(
            tmp_path,
            record(
                http_status=None, error_class=error_class, cost_status=cost, settled_usd=settled
            ),
        )


def test_null_status_billed_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ExportMismatch):
        exported(
            tmp_path,
            record(
                http_status=None,
                error_class="KeyMissing",
                cost_status="billed",
                settled_usd=Decimal(1),
            ),
        )


def test_conflicting_records_for_one_call_are_refused(tmp_path: Path) -> None:
    body = json.dumps(OPENAI_BODY).encode()
    null = record(
        http_status=None, cost_status="unknown", settled_usd=None, error_class="IdleTimeout"
    )
    with pytest.raises(ValueError, match="conflicting"):
        exported(tmp_path, OK_RECORD, null, bodies={0: body})


# R3: build redacts every string


def test_build_redacts_exact_values_in_every_string_field() -> None:
    red = Redactor.from_environ({"OPENAI_API_KEY": OPAQUE})
    rec = CallRecord.build(red, **fields(request_id=f"req {OPAQUE}", reported_model=OPAQUE))
    assert OPAQUE not in (rec.request_id or "") + (rec.reported_model or "")


def test_build_redacts_key_shaped_values_instead_of_refusing() -> None:
    red = Redactor()
    tool = ToolCallRecord(
        name=f"t {SECRET}", arguments_sha256="b" * 64, result_bytes=None, refusal_code=SECRET
    )
    rec = CallRecord.build(
        red,
        **fields(
            reported_model=f"x {SECRET}",
            request_id=SECRET,
            error_class=f"E {SECRET}",
            tool_calls=(tool,),
        ),
    )
    assert "TESTONLY123456" not in rec.model_dump_json()
    assert rec.tool_calls[0].name.startswith("t ")


def test_build_surfaces_validation_errors_without_input() -> None:
    with pytest.raises(RecordInvalid) as caught:
        CallRecord.build(Redactor(), **fields(http_status="not-an-int", call_index=-1))
    assert "not-an-int" not in str(caught.value) and "call_index" in str(caught.value)


def test_tool_call_record_hides_input_in_errors() -> None:
    with pytest.raises(ValidationError) as caught:
        ToolCallRecord(name="n", arguments_sha256=SECRET, result_bytes=None, refusal_code=None)
    assert "TESTONLY123456" not in str(caught.value)
    with pytest.raises(ValidationError) as caught:
        record(
            tool_calls=(
                {
                    "name": "n",
                    "arguments_sha256": SECRET,
                    "result_bytes": None,
                    "refusal_code": None,
                },
            )
        )
    assert "TESTONLY123456" not in str(caught.value)


# R4(e): preimage


def test_retain_preimage_canonicalises_like_the_digest(tmp_path: Path) -> None:
    unsorted = {**invocation_preimage(**PREIMAGE), "upstream_hashes": ["c" * 64, "b" * 64]}
    assert retain_preimage(SimpleNamespace(directory=tmp_path), unsorted) == digest_of()


@pytest.mark.parametrize(
    "over",
    [
        {"upstream_hashes": "cb"},
        {"attempt": 2},
        {"attempt": True},
        {"attempt": "0"},
        {"upstream_hashes": ["zz"]},
        {"upstream_hashes": ["B" * 64]},
        {"prompt_sha256": "d" * 63},
        {"step_id": SECRET},
        {"run_id": ""},
    ],
)
def test_preimage_refuses_bad_values(tmp_path: Path, over: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        digest_of(**over)
    pre = {**invocation_preimage(**PREIMAGE), **over}
    with pytest.raises(ValueError):
        retain_preimage(SimpleNamespace(directory=tmp_path), pre)


@pytest.mark.parametrize("drop", [True, False])
def test_retain_preimage_refuses_a_wrong_key_set(tmp_path: Path, drop: bool) -> None:
    pre = invocation_preimage(**PREIMAGE)
    if drop:
        del pre["step_id"]
    else:
        pre["extra"] = 1
    with pytest.raises(ValueError, match="seven"):
        retain_preimage(SimpleNamespace(directory=tmp_path), pre)


def test_bare_json_string_body_round_trips_as_itself(tmp_path: Path) -> None:
    inner = '{"error":{"message":"x"}}'
    body = json.dumps(inner).encode()
    path = CallLog(tmp_path, Redactor()).write_raw(DIGEST, 0, body)
    assert archived(path) == json.dumps(inner)  # the quotes are kept: not a text body


def test_error_record_whose_raw_was_swapped_for_a_turn_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ExportMismatch) as caught:
        exported(
            tmp_path,
            record(cost_status="unknown", settled_usd=None, error_class="UnparsableReply"),
            bodies={0: json.dumps(OPENAI_BODY).encode()},
        )
    assert caught.value.field == "outcome"


# ---------------------------------------------------------------- fix round 2


def test_anthropic_turn_with_cache_creation_split_exports(tmp_path: Path) -> None:
    usage = {
        "input_tokens": 3,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "cache_creation": {"ephemeral_5m_input_tokens": 0, "ephemeral_1h_input_tokens": 0},
        "output_tokens": 1,
    }
    events: list[dict[str, Any]] = [
        {
            "type": "message_start",
            "message": {"id": "msg_1", "model": "claude-opus-5-5", "usage": usage},
        },
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "hi"}},
        {"type": "content_block_stop", "index": 0},
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn"},
            "usage": {"output_tokens": 4},
        },
        {"type": "message_stop"},
    ]
    body = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()
    turn = parse("anthropic", 200, body, {}, Redactor())
    assert not isinstance(turn, ProviderError)
    assert turn.usage.cache_write_5m_tokens is not None  # the split the record does not keep
    u = turn.usage
    (resp,) = exported(
        tmp_path,
        record(
            **ANTHROPIC,
            request_id="msg_1",
            reported_model="claude-opus-5-5",
            input_tokens=u.input_tokens,
            cached_read_tokens=u.cached_read_tokens,
            cache_write_tokens=u.cache_write_tokens,
            output_tokens=u.output_tokens,
            reasoning_tokens=u.reasoning_tokens,
        ),
        bodies={0: body},
    )
    assert resp["text"] == "hi"


@pytest.mark.parametrize("cost", ["unknown", "billed"])
def test_error_record_with_tokens_exports_sent_usage_before_unknown(
    tmp_path: Path, cost: str
) -> None:
    (resp,) = exported(
        tmp_path,
        record(
            cost_status=cost,
            settled_usd=None if cost == "unknown" else Decimal("0.2"),
            error_class="ResponseError",
            input_tokens=10,
            output_tokens=5,
        ),
    )
    assert resp["kind"] == "sent_usage" and resp["usage"]["input_tokens"] == 10
    assert ("billed_usd" in resp) == (cost == "billed")


def test_error_record_unknown_without_tokens_is_sent_unknown(tmp_path: Path) -> None:
    (resp,) = exported(
        tmp_path,
        record(cost_status="unknown", settled_usd=None, error_class="X", output_tokens=None),
    )
    assert resp["kind"] == "sent_unknown" and "usage" not in resp


def test_lone_upstream_hash_string_is_refused() -> None:
    with pytest.raises(ValueError):
        digest_of(upstream_hashes="b" * 64)
    with pytest.raises(ValueError):
        invocation_preimage(**{**PREIMAGE, "upstream_hashes": "b" * 64})


def test_ok_turn_billed_cost_must_equal_the_records_settled_usd(tmp_path: Path) -> None:
    def body(cost: float) -> bytes:
        return json.dumps(
            {
                "id": "gen-1",
                "model": "deepseek/deepseek-v4.1-flash-1017",
                "choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": cost},
            }
        ).encode()

    def rec(settled: str) -> CallRecord:
        return record(
            provider="openrouter",
            config_id="deepseek-max",
            requested_effort="max",
            requested_model="deepseek/deepseek-v4.1-flash-1017",
            reported_model="deepseek/deepseek-v4.1-flash-1017",
            request_id="gen-1",
            input_tokens=10,
            output_tokens=5,
            cost_status="billed",
            settled_usd=Decimal(settled),
        )

    assert exported(tmp_path / "ok", rec("0.0001"), bodies={0: body(0.0001)})
    with pytest.raises(ExportMismatch) as caught:
        exported(tmp_path / "bad", rec("0.0002"), bodies={0: body(0.0001)})
    assert caught.value.field == "billed_usd"


def test_a_mapper_crash_withholds_the_body_fail_closed(tmp_path: Path) -> None:
    body = json.dumps({"output": [{"type": "message", "content": 5}]}).encode()
    path = CallLog(tmp_path, Redactor()).write_raw(DIGEST, 0, body, error_class="ProviderRejected")
    assert archived(path) == f"[withheld: MapperError; {len(body)} bytes]"
