"""No genuine refusal: genuine runs with a within-attempt step repair (the producer's
`WITHIN_ATTEMPT_REPAIR` extended to the g1x fake module's steps, in the producer and the verifier
alike) must be accepted by `write_receipt` and `verify_owner_run_receipt`, on attempt 0 and on a
repair attempt 1. Also checks every submission transition keeps the five begin-set fields."""
import importlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import deploy_vii.execution as ex
from deploy_vii.execution import Execution
from deploy_workflow.workflow import WorkflowError

import test_owner_g1x as g
from test_owner_g1x import g1x  # noqa: F401  (fixture)

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")
MODULE, SOURCED, VIEWED = g.MODULE, g.SOURCED, g.VIEWED
FIELDS = ("module_id", "inputs", "number", "repair_of", "repair_issues")


def _repairable(g1x_ns: SimpleNamespace, *steps: str) -> None:
    table = {**ex.WITHIN_ATTEMPT_REPAIR, MODULE: frozenset(steps)}
    g1x_ns.monkeypatch.setattr(ex, "WITHIN_ATTEMPT_REPAIR", table)
    g1x_ns.monkeypatch.setattr(owner, "WITHIN_ATTEMPT_REPAIR", table)


def _verdicts(root: Path, workflow: Any) -> tuple[str, str]:
    try:
        receipt = workflow.write_receipt(root / "receipt.json")
    except WorkflowError as error:
        return "write_receipt:" + error.code, "n/a"
    return "accepted", g._verdict(root, receipt)


def _fields_kept(root: Path, workflow: Any) -> bool:
    store = Execution(root / "store")
    for s in workflow._submissions:
        before = owner._snapshot(store, s.binding.binding.snapshot_sha256)
        after = owner._snapshot(store, s.snapshot_after_sha256)
        a = next(x for x in before.attempts if x.ticket_id == s.binding.binding.ticket_id)
        b = next(x for x in after.attempts if x.ticket_id == s.binding.binding.ticket_id)
        if any(getattr(a, f) != getattr(b, f) for f in FIELDS):
            return False
    return True


def _repaired_steps(root: Path) -> list[Any]:
    return [(a.number, [s.step_id for s in a.step_repairs], a.status) for a in g._fake_attempts(root)]


def test_w1_viewed_step_repaired_in_attempt_0(g1x: SimpleNamespace, tmp_path: Path) -> None:
    _repairable(g1x, VIEWED)
    workflow = g._start(tmp_path)
    workflow.read_inputs()
    g._read_page(workflow)
    assert workflow.submit_review(g._sourced())["status"] == "valid"
    workflow.read_inputs()
    assert workflow.submit_review(g._viewed(g.INVALID_MARK))["status"] == "invalid"
    workflow.read_inputs()
    assert workflow.submit_review(g._viewed())["status"] == "valid"
    verdicts = _verdicts(tmp_path, workflow)
    print("VERDICT w1", _repaired_steps(tmp_path), verdicts, "fields-kept", _fields_kept(tmp_path, workflow))
    assert verdicts == ("accepted", "accepted") and _fields_kept(tmp_path, workflow)
    assert _repaired_steps(tmp_path) == [(0, [VIEWED], "finished")]


def test_w2_viewed_step_repaired_in_repair_attempt_1(g1x: SimpleNamespace, tmp_path: Path) -> None:
    _repairable(g1x, VIEWED)
    workflow = g._start(tmp_path)
    workflow.read_inputs()
    assert workflow.submit_review(g._sourced())["status"] == "invalid"  # page never read
    workflow.read_inputs()
    g._read_page(workflow)
    assert workflow.submit_review(g._sourced())["status"] == "valid"
    workflow.read_inputs()
    assert workflow.submit_review(g._viewed(g.INVALID_MARK))["status"] == "invalid"
    workflow.read_inputs()
    assert workflow.submit_review(g._viewed())["status"] == "valid"
    verdicts = _verdicts(tmp_path, workflow)
    print("VERDICT w2", _repaired_steps(tmp_path), verdicts, "fields-kept", _fields_kept(tmp_path, workflow))
    assert verdicts == ("accepted", "accepted") and _fields_kept(tmp_path, workflow)
    assert [n for n, _, _ in _repaired_steps(tmp_path)] == [0, 1]


def test_w3_sourced_step_repaired_in_attempt_0(g1x: SimpleNamespace, tmp_path: Path) -> None:
    _repairable(g1x, SOURCED)
    workflow = g._start(tmp_path)
    workflow.read_inputs()
    assert workflow.submit_review(g._sourced())["status"] == "invalid"  # page never read
    g._drive(workflow)
    verdicts = _verdicts(tmp_path, workflow)
    print("VERDICT w3", _repaired_steps(tmp_path), verdicts, "fields-kept", _fields_kept(tmp_path, workflow))
    assert verdicts == ("accepted", "accepted") and _fields_kept(tmp_path, workflow)
    assert _repaired_steps(tmp_path) == [(0, [SOURCED], "finished")]


def test_w4_genuine_attempt_1_blocked(g1x: SimpleNamespace, tmp_path: Path) -> None:
    """Attempt 0 rejected, attempt 1 rejected too (settles blocked): both submissions finish."""
    workflow = g._start(tmp_path)
    workflow.read_inputs()
    assert workflow.submit_review(g._sourced())["status"] == "invalid"
    workflow.read_inputs()
    assert workflow.submit_review(g._sourced())["status"] == "invalid"
    verdicts = _verdicts(tmp_path, workflow)
    print("VERDICT w4", _repaired_steps(tmp_path), verdicts, "fields-kept", _fields_kept(tmp_path, workflow))
    assert verdicts == ("accepted", "accepted") and _fields_kept(tmp_path, workflow)
