"""Fault records: classify a failed module run as product, prompt, harness or model.

Spec §9a.2: each module gets at most ``MAX_FIX_ROUNDS`` fix rounds per fault class; after that
the open faults go to the user. Model faults are recorded, never fixed, so they never count.
"""

from __future__ import annotations

import fcntl
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, ValidationError, model_validator

from deploy_vii.contracts import Contract, Identifier

FaultClass = Literal["product", "prompt", "harness", "model"]

MAX_FIX_ROUNDS = 2


class FaultRecord(Contract):
    schema_version: Literal["fault/1"]
    fault_id: Identifier
    run_id: str
    case_id: str
    pathway: str
    module_id: str
    step_id: str
    config_id: str
    fault_class: FaultClass
    assigned_by: str
    confirmed_by: str
    evidence: tuple[Annotated[str, Field(min_length=1)], ...]
    fix_ref: str | None
    rerun_run_id: str | None
    rerun_passed: bool | None

    @model_validator(mode="after")
    def _checks(self) -> Self:
        if self.assigned_by == self.confirmed_by:
            raise ValueError("assigned_by and confirmed_by must differ")
        if not self.evidence:
            raise ValueError("evidence needs at least one entry")
        return self


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _parse(text: str, name: str) -> tuple[FaultRecord, ...]:
    out: list[FaultRecord] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            out.append(FaultRecord.model_validate_json(line))
        except ValidationError as exc:
            where = "; ".join(
                f"{'.'.join(str(p) for p in e['loc']) or 'record'}: {e['msg']}"
                for e in exc.errors(include_input=False)
            )
            raise ValueError(f"{name} line {number}: unparsable fault record ({where})") from None
    return tuple(out)


def append_fault(path: Path, record: FaultRecord) -> None:
    """Append one fsynced JSONL line under an exclusive flock; a duplicate ``fault_id`` is refused."""
    data = (record.model_dump_json() + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        size = os.fstat(fd).st_size
        if size:
            if os.pread(fd, 1, size - 1) != b"\n":
                raise ValueError(f"{path.name} ends mid-line; repair it before appending")
            existing = _parse(os.pread(fd, size, 0).decode(), path.name)
            if any(f.fault_id == record.fault_id for f in existing):
                raise ValueError(f"duplicate fault_id {record.fault_id!r} in {path.name}")
        view = memoryview(data)
        while view:
            view = view[os.write(fd, view) :]
        os.fsync(fd)
        if size == 0:
            _fsync_dir(path.parent)  # new file: make its directory entry durable
    finally:
        os.close(fd)  # closing releases the lock


def read_faults(path: Path) -> tuple[FaultRecord, ...]:
    """Every record in file order. An unparsable line raises with its line number."""
    if not path.exists():
        return ()
    return _parse(path.read_text(encoding="utf-8"), path.name)


def _fixes(
    faults: Iterable[FaultRecord], case_id: str, module_id: str, fault_class: FaultClass
) -> list[FaultRecord]:
    return [
        f
        for f in faults
        if (f.case_id, f.module_id, f.fault_class) == (case_id, module_id, fault_class)
        and f.fix_ref is not None
    ]


def fix_rounds(
    faults: Iterable[FaultRecord], case_id: str, module_id: str, fault_class: FaultClass
) -> int:
    """Fix rounds spent: records of this class on this module that carry a ``fix_ref``.
    Model faults are never fixed, so they count zero."""
    if fault_class == "model":
        return 0
    return len(_fixes(tuple(faults), case_id, module_id, fault_class))


def needs_owner(
    faults: Iterable[FaultRecord], case_id: str, module_id: str, fault_class: FaultClass
) -> bool:
    """True when the rounds are spent and the latest fix's rerun has not passed."""
    records = tuple(faults)
    if fix_rounds(records, case_id, module_id, fault_class) < MAX_FIX_ROUNDS:
        return False
    return _fixes(records, case_id, module_id, fault_class)[-1].rerun_passed is not True
