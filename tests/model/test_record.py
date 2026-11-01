"""model-call/1 records, the redacted raw archive and the invocation digest audit. No network."""

import hashlib
import json
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
from deploy_workflow.model.record import (
    CallLog,
    CallRecord,
    RawExists,
    RawMissing,
    ToolCallRecord,
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


def test_export_recording_replays_through_recorded_adapter(tmp_path: Path) -> None:
    run, out = tmp_path / "run", tmp_path / "rec"
    run.mkdir()
    out.mkdir()
    log = CallLog(run, Redactor())
    log.write_raw(DIGEST, 0, json.dumps(OPENAI_BODY).encode())
    log.append(record())
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
    CallLog(run, Redactor()).append(record())
    with pytest.raises(RawMissing):
        export_recording(run, tmp_path / "r.jsonl", Redactor())


@pytest.mark.parametrize("status, kind", [("unknown", "sent_unknown"), ("computed", "not_sent")])
def test_export_null_status_records_use_the_ruled_format(
    tmp_path: Path, status: str, kind: str
) -> None:
    run = tmp_path / "run"
    run.mkdir()
    CallLog(run, Redactor()).append(
        record(
            http_status=None,
            cost_status=status,
            settled_usd=None if status == "unknown" else Decimal(0),
            error_class="IdleTimeout",
        )
    )
    out = tmp_path / "r.jsonl"
    assert export_recording(run, out, Redactor()) == 1
    assert json.loads(out.read_text())["response"] == {
        "kind": kind,
        "error_class": "IdleTimeout",
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
