"""Read a run directory: ``run.json`` (O2) and ``calls.jsonl`` (O5 ``model-call/1`` records).

The record shapes belong to the orchestrator; this module imports O5's ``CallRecord`` and
mirrors ``run_pathway._write_run_json`` so neither can drift. Errors never carry input values.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import ConfigDict, ValidationError, model_validator

from deploy_vii.contracts import Contract, PathwayId
from deploy_workflow.model.record import CallRecord, strings
from deploy_workflow.model.redact import KEY_PATTERN
from deploy_workflow.model_testing.configs import CONFIGS


class JournalError(ValueError):
    """A run directory or call journal cannot be read as written by the orchestrator."""


class RunSource(Contract):
    model_config = ConfigDict(hide_input_in_errors=True)

    source_id: str
    path: str
    sha256: str
    media_type: str
    converted_sha256: str | None


class RunMeta(Contract):
    model_config = ConfigDict(hide_input_in_errors=True)

    case_id: str
    pathway: PathwayId
    config_id: str
    run_id: str
    mode: Literal["offline", "live"]
    cap_usd: Decimal
    sources: tuple[RunSource, ...]
    cp_dr_invoked: bool
    replayed_from_run: str | None
    outcome: Literal["settled", "stopped"]
    stopped_reason: str | None
    ruling_path: str | None = None
    ruling_sha256: str | None = None
    ruling_date: str | None = None

    @model_validator(mode="after")
    def _checked(self) -> RunMeta:
        if not (self.cap_usd.is_finite() and self.cap_usd > 0):
            raise ValueError("cap_usd must be a finite amount above zero")
        for text in strings(self.model_dump(mode="json")):
            if KEY_PATTERN.search(text):
                raise ValueError("a run.json field holds key material")  # never the value
        ruling = (self.ruling_path, self.ruling_sha256, self.ruling_date)
        if (self.mode == "live") != all(v is not None for v in ruling) or (
            self.mode != "live" and any(v is not None for v in ruling)
        ):
            raise ValueError("the ruling fields are set exactly when mode is live")
        if (self.outcome == "stopped") != (self.stopped_reason is not None):
            raise ValueError("stopped_reason is set exactly when outcome is stopped")
        return self


def _messages(error: ValidationError) -> str:
    """Locations and messages only; an input-supplied key name never appears."""
    found = error.errors(include_input=False, include_url=False, include_context=False)
    parts = []
    for e in found:
        loc = [str(x) for x in e["loc"]]
        if e["type"] == "extra_forbidden" and loc:
            loc[-1] = "unexpected field"
        parts.append(f"{'.'.join(loc)}: {e['msg']}")
    return KEY_PATTERN.sub("[redacted]", "; ".join(parts))


def _check(where: str, line: bytes) -> tuple[CallRecord | None, str]:
    """Parse one journal line; return the record or the refusal text (raised by the caller
    outside any except block so no input-bearing exception stays as context)."""
    try:
        text = line.decode("utf-8")
    except UnicodeDecodeError:
        return None, f"{where}: not UTF-8"
    if not text.strip():
        return None, f"{where}: blank line"
    try:
        return CallRecord.model_validate_json(text), ""
    except ValidationError as error:
        return None, f"{where}: {_messages(error)}"


def read_journal(path: Path) -> tuple[CallRecord, ...]:
    records: list[CallRecord] = []
    seen: set[tuple[str, str, str, int, int]] = set()
    for number, line in enumerate(path.read_bytes().splitlines(), start=1):
        where = f"{path.name} line {number}"
        record, refusal = _check(where, line)
        if record is None:
            raise JournalError(refusal)
        config = CONFIGS.get(record.config_id)
        if config is None:
            raise JournalError(f"{where}: unknown config_id {record.config_id}")
        if record.provider != config.provider:
            raise JournalError(f"{where}: provider does not match config {record.config_id}")
        key = (record.run_id, record.module_id, record.step_id, record.attempt, record.call_index)
        if key in seen:
            raise JournalError(f"{where}: duplicate call {key}")
        seen.add(key)
        records.append(record)
    return tuple(records)


def _read_meta(run_json: Path) -> tuple[RunMeta | None, str]:
    try:
        text = run_json.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return None, "run.json: not UTF-8"
    try:
        return RunMeta.model_validate_json(text), ""
    except ValidationError as error:
        return None, f"run.json: {_messages(error)}"


def read_run(run_dir: Path) -> tuple[RunMeta, tuple[CallRecord, ...]]:
    run_json = run_dir / "run.json"
    if not run_json.is_file():
        raise JournalError(f"no run.json in {run_dir}: the run was refused or crashed")
    meta, refusal = _read_meta(run_json)
    if meta is None:
        raise JournalError(refusal)
    calls = run_dir / "calls.jsonl"
    if calls.is_symlink() or calls.exists():
        if not calls.is_file():
            raise JournalError("calls.jsonl is not a regular file")
        records = read_journal(calls)
    else:
        records = ()
    for number, record in enumerate(records, start=1):
        for field in ("run_id", "case_id", "pathway", "config_id"):
            if getattr(record, field) != getattr(meta, field):
                raise JournalError(f"calls.jsonl record {number}: {field} differs from run.json")
    return meta, records
