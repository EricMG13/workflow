"""Read a run directory: ``run.json`` (O2) and ``calls.jsonl`` (O5 ``model-call/1`` records).

The record shapes belong to the orchestrator; this module imports O5's ``CallRecord`` and
mirrors ``run_pathway._write_run_json`` so neither can drift. Errors never carry input values.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import ValidationError, model_validator

from deploy_vii.contracts import Contract, PathwayId
from deploy_workflow.model.record import CallRecord
from deploy_workflow.model_testing.configs import CONFIGS


class JournalError(ValueError):
    """A run directory or call journal cannot be read as written by the orchestrator."""


class RunSource(Contract):
    source_id: str
    path: str
    sha256: str
    media_type: str
    converted_sha256: str | None


class RunMeta(Contract):
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
        ruling = (self.ruling_path, self.ruling_sha256, self.ruling_date)
        if (self.mode == "live") != all(v is not None for v in ruling) or (
            self.mode != "live" and any(v is not None for v in ruling)
        ):
            raise ValueError("the ruling fields are set exactly when mode is live")
        if (self.outcome == "stopped") != (self.stopped_reason is not None):
            raise ValueError("stopped_reason is set exactly when outcome is stopped")
        return self


def _messages(error: ValidationError) -> str:
    found = error.errors(include_input=False, include_url=False, include_context=False)
    return "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in found)


def read_journal(path: Path) -> tuple[CallRecord, ...]:
    records: list[CallRecord] = []
    seen: set[tuple[str, str, str, int, int]] = set()
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        where = f"{path.name} line {number}"
        if not line.strip():
            raise JournalError(f"{where}: blank line")
        try:
            record = CallRecord.model_validate_json(line)
        except ValidationError as error:
            raise JournalError(f"{where}: {_messages(error)}") from None
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


def read_run(run_dir: Path) -> tuple[RunMeta, tuple[CallRecord, ...]]:
    run_json = run_dir / "run.json"
    if not run_json.is_file():
        raise JournalError(f"no run.json in {run_dir}: the run was refused or crashed")
    try:
        meta = RunMeta.model_validate_json(run_json.read_text())
    except ValidationError as error:
        raise JournalError(f"run.json: {_messages(error)}") from None
    calls = run_dir / "calls.jsonl"
    records = read_journal(calls) if calls.is_file() else ()
    for number, record in enumerate(records, start=1):
        for field in ("run_id", "case_id", "pathway", "config_id"):
            if getattr(record, field) != getattr(meta, field):
                raise JournalError(f"calls.jsonl record {number}: {field} differs from run.json")
    return meta, records
