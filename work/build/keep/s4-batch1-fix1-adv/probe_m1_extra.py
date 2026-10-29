"""Batch 1 fix 1 re-review, Medium 1, extra routes past `_verify_transition`'s begin-set
equality (g1x fake-module harness):

- blocked-number0: attempt 1's rejected (blocked) step, relabelled after the genuine settle to a
  first try (number 0, repair cleared).
- mid-settle: the begin-set fields relabelled *inside* the settling valid step (before the
  genuine submit, so the head Module is settled as attempt 0) and restored before the step ends,
  so the step's endpoints are equal.
- mid-rejected: the same inside attempt 1's rejected step (settled as a "rejected" attempt 0,
  so no blocked head), restored before the step ends.
- mid-sourced: the same inside attempt 1's first valid step, which settles nothing (control:
  nothing forged persists, so acceptance is harmless).
Each prints `VERDICT <case> seal=<..> verify=<..>` with the owner_workflow function:line."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from deploy_vii.execution import Execution

import probe_m1_fields as p
import test_owner_g1x as g
from test_owner_g1x import g1x  # noqa: F401  (fixture)

MODULE, SOURCED, VIEWED = g.MODULE, g.SOURCED, g.VIEWED
FIRST_TRY = {"number": 0, "repair_of": None, "repair_issues": ()}


def test_loaded_from_copy() -> None:
    print("LOADED", p.owner.__file__)
    assert "s4-batch1-fix1-adv" in p.owner.__file__


def _attempt(store: Execution, ticket_id: str) -> Any:
    return next(a for a in store.read().attempts if a.ticket_id == ticket_id)


def _mid(g1x_ns: SimpleNamespace, step: str, applied: list[Any]) -> None:
    """Relabel attempt 1 to a first try before the genuine submit of `step`, restore after."""
    real = g1x_ns.core.submit

    def submit(store: Execution, ticket_id: str, step_id: str, payload: str, rules: Any) -> Any:
        before = _attempt(store, ticket_id)
        if step_id != step or before.number != 1 or applied:
            return real(store, ticket_id, step_id, payload, rules)
        applied.append(1)
        p._rewrite(store, ticket_id, **FIRST_TRY)
        out = real(store, ticket_id, step_id, payload, rules)
        restored = p._rewrite(
            store,
            ticket_id,
            number=before.number,
            repair_of=before.repair_of,
            repair_issues=before.repair_issues,
        )
        return replace(out, journal=restored)

    g1x_ns.monkeypatch.setattr(g1x_ns.core, "submit", submit)


def _twice_rejected(root: Path) -> tuple[Any, str]:
    workflow = g._start(root)
    try:
        workflow.read_inputs()
        assert workflow.submit_review(g._sourced())["status"] == "invalid"
        workflow.read_inputs()
        assert workflow.submit_review(g._sourced())["status"] == "invalid"
    except Exception as error:  # noqa: BLE001 - the probe records a runtime stop as its verdict
        return workflow, f"runtime-stop:{type(error).__name__}:{getattr(error, 'code', error)}"
    return workflow, ""


def _shape(root: Path) -> list[Any]:
    return [(a.number, a.repair_of is not None, a.status, bool(a.issues)) for a in g._fake_attempts(root)]


def test_blocked_number0(g1x: SimpleNamespace, tmp_path: Path) -> None:
    applied: list[Any] = []

    def hook(store: Execution, ticket: str, step_id: str, journal: Any) -> Any:
        if journal.number == 1 and journal.status == "finished" and journal.issues and not applied:
            applied.append(1)
            return p._rewrite(store, ticket, **FIRST_TRY)
        return None

    p._core(g1x, hook)
    workflow, stop = _twice_rejected(tmp_path)
    print("SHAPE", _shape(tmp_path))
    p._report("blocked-number0", tmp_path, workflow, stop, applied)


def test_mid_settle(g1x: SimpleNamespace, tmp_path: Path) -> None:
    applied: list[Any] = []
    _mid(g1x, VIEWED, applied)
    workflow, stop = p._run(tmp_path)
    store = Execution(tmp_path / "store")
    head = next(h for h in store.read().heads if h.module_id == MODULE)
    print("SHAPE", _shape(tmp_path), "head-module-attempt", store.head_module(head).attempt)
    # The fake core's probe re-settles and may raise a raw ValueError inside `write_receipt`
    # (`_verify` is not wrapped there); record it, then give the hand-built receipt to the verifier.
    try:
        workflow.write_receipt(tmp_path / "receipt.json")
        seal = "accepted"
    except p.WorkflowError as error:
        seal = f"{error.code}@{p._where(error)}"
    except ValueError as error:
        seal = f"ValueError:{error}@{p._where(error)}"
    receipt = p._hand_receipt(workflow)
    try:
        p.owner.verify_owner_run_receipt(Execution(tmp_path / "store"), receipt)
        verify = "accepted"
    except p.WorkflowError as error:
        verify = f"{error.code}@{p._where(error)}"
    print(f"VERDICT mid-settle applied={bool(applied)} {stop} seal={seal} verify={verify}")
    assert applied and seal != "accepted" and verify != "accepted"


def test_mid_rejected(g1x: SimpleNamespace, tmp_path: Path) -> None:
    applied: list[Any] = []
    _mid(g1x, SOURCED, applied)
    workflow, stop = _twice_rejected(tmp_path)
    store = Execution(tmp_path / "store")
    print("SHAPE", _shape(tmp_path), "heads", [h.module_id for h in store.read().heads])
    p._report("mid-rejected", tmp_path, workflow, stop, applied)


def test_mid_sourced_control(g1x: SimpleNamespace, tmp_path: Path) -> None:
    applied: list[Any] = []
    _mid(g1x, SOURCED, applied)
    workflow, stop = p._run(tmp_path)
    seal, verify = p._verdicts(tmp_path, workflow)
    print(f"VERDICT mid-sourced applied={bool(applied)} {stop} seal={seal} verify={verify}", "SHAPE", _shape(tmp_path))
    assert applied and not stop
