from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from deploy_workflow.model_testing.faults import (
    MAX_FIX_ROUNDS,
    FaultRecord,
    append_fault,
    fix_rounds,
    needs_owner,
    read_faults,
)


def _fault(fault_id: str = "f1", **over: Any) -> FaultRecord:
    base: dict[str, Any] = {
        "schema_version": "fault/1",
        "fault_id": fault_id,
        "run_id": "r1",
        "case_id": "c1",
        "pathway": "p",
        "module_id": "m1",
        "step_id": "s1",
        "config_id": "sol-medium",
        "fault_class": "prompt",
        "assigned_by": "reviewer-1",
        "confirmed_by": "controller",
        "evidence": ("digest-1",),
        "fix_ref": None,
        "rerun_run_id": None,
        "rerun_passed": None,
    }
    base.update(over)
    return FaultRecord(**base)


def test_append_and_read(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "faults.jsonl"
    path.parent.mkdir()
    a, b = _fault("f1"), _fault("f2", fix_ref="abc123", rerun_run_id="r2", rerun_passed=True)
    append_fault(path, a)
    append_fault(path, b)
    assert read_faults(path) == (a, b)
    assert read_faults(tmp_path / "missing.jsonl") == ()


def test_read_refuses_unparsable_line(tmp_path: Path) -> None:
    path = tmp_path / "faults.jsonl"
    append_fault(path, _fault("f1"))
    with path.open("a") as fh:
        fh.write("{not json\n")
    with pytest.raises(ValueError, match="line 2"):
        read_faults(path)


def test_duplicate_fault_refused(tmp_path: Path) -> None:
    path = tmp_path / "faults.jsonl"
    append_fault(path, _fault("f1"))
    with pytest.raises(ValueError, match="duplicate fault_id"):
        append_fault(path, _fault("f1", fault_class="harness"))
    assert len(read_faults(path)) == 1


def test_assigner_differs_from_confirmer() -> None:
    with pytest.raises(ValidationError, match="differ"):
        _fault(assigned_by="same", confirmed_by="same")


def test_evidence_required() -> None:
    with pytest.raises(ValidationError):
        _fault(evidence=())


def test_needs_owner_after_two_failed_rounds() -> None:
    assert MAX_FIX_ROUNDS == 2
    one = [_fault("f1", fix_ref="x1", rerun_passed=False)]
    assert fix_rounds(one, "c1", "m1", "prompt") == 1
    assert not needs_owner(one, "c1", "m1", "prompt")
    two = [*one, _fault("f2", fix_ref="x2", rerun_passed=False)]
    assert fix_rounds(two, "c1", "m1", "prompt") == 2
    assert needs_owner(two, "c1", "m1", "prompt")
    # other class / module / case are counted apart
    assert not needs_owner(two, "c1", "m1", "product")
    assert not needs_owner(two, "c1", "m2", "prompt")
    assert not needs_owner(two, "c2", "m1", "prompt")
    # the last fix passing clears it; a rerun not yet run keeps it open
    passed = [*one, _fault("f2", fix_ref="x2", rerun_passed=True)]
    assert not needs_owner(passed, "c1", "m1", "prompt")
    pending = [*one, _fault("f2", fix_ref="x2", rerun_passed=None)]
    assert needs_owner(pending, "c1", "m1", "prompt")
    assert not needs_owner([], "c1", "m1", "prompt")


def test_model_fault_needs_no_fix_ref() -> None:
    m = _fault("f1", fault_class="model", fix_ref=None)
    assert m.fix_ref is None
    assert fix_rounds([m, m], "c1", "m1", "model") == 0
    assert not needs_owner([m, m], "c1", "m1", "model")
