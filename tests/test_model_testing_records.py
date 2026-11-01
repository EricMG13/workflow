from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from deploy_workflow.model.record import CallRecord
from deploy_workflow.model_testing.records import (
    JournalError,
    RunMeta,
    read_journal,
    read_run,
)

NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


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
        "invocation_digest": "a" * 64,
        "request_id": "req-1",
        "http_status": 200,
        "started_at": NOW,
        "first_byte_at": None,
        "finished_at": NOW,
        "input_tokens": 10,
        "cached_read_tokens": None,
        "cache_write_tokens": None,
        "output_tokens": 5,
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


def write(path: Path, *records: CallRecord) -> Path:
    path.write_text("".join(r.model_dump_json() + "\n" for r in records))
    return path


def write_raw(path: Path, **over: Any) -> Path:
    body = json.loads(record().model_dump_json())
    body.update(over)
    path.write_text(json.dumps(body) + "\n")
    return path


def run_body(**over: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "case_id": "case-1",
        "pathway": "credit_snapshot",
        "config_id": "sol-medium",
        "run_id": "run-1",
        "mode": "offline",
        "cap_usd": "1.50",
        "sources": [
            {
                "source_id": "s1",
                "path": "a.pdf",
                "sha256": "c" * 64,
                "media_type": "application/pdf",
                "converted_sha256": None,
            }
        ],
        "cp_dr_invoked": False,
        "replayed_from_run": None,
        "outcome": "settled",
        "stopped_reason": None,
    }
    body.update(over)
    return body


def write_run(run_dir: Path, **over: Any) -> None:
    (run_dir / "run.json").write_text(json.dumps(run_body(**over)))


def test_reads_valid_journal(tmp_path: Path) -> None:
    a, b = record(call_index=0), record(call_index=1)
    assert read_journal(write(tmp_path / "c.jsonl", a, b)) == (a, b)


def test_refuses_duplicate_call(tmp_path: Path) -> None:
    p = write(tmp_path / "c.jsonl", record(), record())
    with pytest.raises(JournalError, match="duplicate call"):
        read_journal(p)


def test_refuses_blank_and_unparsable_line(tmp_path: Path) -> None:
    p = tmp_path / "c.jsonl"
    p.write_text(record().model_dump_json() + "\n\n")
    with pytest.raises(JournalError, match="line 2"):
        read_journal(p)
    p.write_text("{not json\n")
    with pytest.raises(JournalError, match="line 1"):
        read_journal(p)


def test_refuses_key_material(tmp_path: Path) -> None:
    p = write_raw(tmp_path / "c.jsonl", error="401 invalid key sk-proj-abcdef123456")
    with pytest.raises(JournalError, match="key material") as e:
        read_journal(p)
    assert "abcdef123456" not in str(e.value)


def test_refuses_long_bare_key(tmp_path: Path) -> None:
    key = "sk-" + "ab-_cd" * 4
    p = write_raw(tmp_path / "c.jsonl", error=f"bad {key}")
    with pytest.raises(JournalError, match="key material") as e:
        read_journal(p)
    assert key not in str(e.value)


def test_refuses_unknown_config(tmp_path: Path) -> None:
    p = write(tmp_path / "c.jsonl", record(config_id="opus-high"))
    with pytest.raises(JournalError, match="opus-high"):
        read_journal(p)


def test_refuses_provider_mismatch(tmp_path: Path) -> None:
    p = write(tmp_path / "c.jsonl", record(provider="anthropic"))
    with pytest.raises(JournalError, match="provider"):
        read_journal(p)


def test_settled_requires_known_cost(tmp_path: Path) -> None:
    p = write_raw(tmp_path / "c.jsonl", cost_status="unknown", settled_usd="0.01")
    with pytest.raises(JournalError, match="settled_usd"):
        read_journal(p)


def test_null_tokens_stay_none(tmp_path: Path) -> None:
    (rec,) = read_journal(write(tmp_path / "c.jsonl", record(reasoning_tokens=None)))
    assert rec.reasoning_tokens is None


def test_reads_run_json(tmp_path: Path) -> None:
    write_run(tmp_path)
    rec = record()
    write(tmp_path / "calls.jsonl", rec)
    meta, records = read_run(tmp_path)
    assert isinstance(meta, RunMeta)
    assert meta.cap_usd == Decimal("1.50")
    assert meta.sources[0].source_id == "s1"
    assert meta.ruling_path is None
    assert records == (rec,)


def test_missing_calls_is_no_records(tmp_path: Path) -> None:
    write_run(tmp_path, outcome="stopped", stopped_reason="cap")
    assert read_run(tmp_path)[1] == ()


def test_missing_run_json(tmp_path: Path) -> None:
    with pytest.raises(JournalError, match="no run.json"):
        read_run(tmp_path)


def test_live_run_needs_ruling_fields(tmp_path: Path) -> None:
    write_run(tmp_path, mode="live")
    with pytest.raises(JournalError, match="ruling"):
        read_run(tmp_path)
    write_run(tmp_path, ruling_path="r.md", ruling_sha256="d" * 64, ruling_date="2026-11-01")
    with pytest.raises(JournalError, match="ruling"):
        read_run(tmp_path)


def test_stopped_reason_exactly_when_stopped(tmp_path: Path) -> None:
    write_run(tmp_path, outcome="stopped")
    with pytest.raises(JournalError, match="stopped_reason"):
        read_run(tmp_path)
    write_run(tmp_path, stopped_reason="x")
    with pytest.raises(JournalError, match="stopped_reason"):
        read_run(tmp_path)


def test_live_run_with_ruling_reads(tmp_path: Path) -> None:
    write_run(
        tmp_path,
        mode="live",
        ruling_path="r.md",
        ruling_sha256="d" * 64,
        ruling_date="2026-11-01",
    )
    assert read_run(tmp_path)[0].ruling_date == "2026-11-01"


@pytest.mark.parametrize("field", ["run_id", "case_id", "pathway", "config_id"])
def test_record_from_other_run_refused(tmp_path: Path, field: str) -> None:
    write_run(tmp_path)
    other = {
        "run_id": "run-2",
        "case_id": "case-2",
        "pathway": "earnings_update",
        "config_id": "sol-high",
    }
    write(tmp_path / "calls.jsonl", record(**{field: other[field]}))
    with pytest.raises(JournalError, match=field):
        read_run(tmp_path)


def test_bad_run_json_never_echoes_input(tmp_path: Path) -> None:
    write_run(tmp_path, mode="sk-proj-abcdef123456")
    with pytest.raises(JournalError) as e:
        read_run(tmp_path)
    assert "abcdef123456" not in str(e.value)
