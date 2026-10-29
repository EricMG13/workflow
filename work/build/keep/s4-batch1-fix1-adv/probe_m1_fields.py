"""Batch 1 fix 1 re-review, Medium 1: try to get past `_verify_transition`'s begin-set equality on
the g1x fake-module harness. Each case prints `VERDICT <case> seal=<..> verify=<..>` where the
verdict carries the owner_workflow function:line that raised. A case passes when the forgery was
applied and both verdicts refuse; `accepted` anywhere fails the case."""
import importlib
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

import pytest

from deploy_vii.execution import Attempt, Execution
from deploy_workflow.workflow import WorkflowError

import test_owner_g1x as g
from test_owner_g1x import g1x  # noqa: F401  (fixture)

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")
MODULE, SOURCED, VIEWED = g.MODULE, g.SOURCED, g.VIEWED


def test_loaded_from_copy() -> None:
    print("LOADED", owner.__file__)
    assert "s4-batch1" in owner.__file__


def _where(error: BaseException) -> str:
    tb, last = error.__traceback__, "?"
    while tb is not None:
        if tb.tb_frame.f_code.co_filename.endswith("owner_workflow.py"):
            last = f"{tb.tb_frame.f_code.co_name}:{tb.tb_lineno}"
        tb = tb.tb_next
    return last


def _rewrite(store: Execution, ticket_id: str, **update: Any) -> Attempt:
    snap = store.read()
    att = next(a for a in snap.attempts if a.ticket_id == ticket_id)
    forged = att.model_copy(update=update)
    store._write(
        snap.model_copy(
            update={
                "parent": snap.content_hash(),
                "attempts": tuple(forged if a.ticket_id == ticket_id else a for a in snap.attempts),
            }
        )
    )
    return forged


def _hand_receipt(workflow: Any) -> Any:
    """The receipt `write_receipt` would build, sealed, for `verify_owner_run_receipt`."""
    store = workflow._store
    snapshot = store.read()
    receipt = owner.OwnerRunReceipt(
        run=snapshot.run,
        pack_sha256=snapshot.pack_sha256,
        snapshot_sha256=snapshot.content_hash(),
        participant=workflow._participant,
        transport=workflow._transport,
        plan=workflow._plan,
        heads=tuple(owner._settled(store, h.module_id) for h in snapshot.heads),
        model=workflow._model,
        begins=tuple(workflow._begins),
        refusals=tuple(workflow._refusals),
        calls=tuple(workflow._calls),
        input_reads=tuple(workflow._reads),
        submissions=tuple(workflow._submissions),
        publications=tuple(workflow._publications),
    )
    seal = store.directory / owner.AUDIT / "receipt.sha256"
    if seal.exists():
        seal.unlink()
    owner._put(seal, receipt.content_hash().encode())
    return receipt


def _verdicts(root: Path, workflow: Any) -> tuple[str, str]:
    store = Execution(root / "store")
    try:
        receipt = workflow.write_receipt(root / "receipt.json")
        seal = "accepted"
    except WorkflowError as error:
        seal = f"{error.code}@{_where(error)}"
        try:
            receipt = _hand_receipt(workflow)
        except Exception as error2:  # noqa: BLE001 - probe reports it
            return seal, f"no-receipt:{type(error2).__name__}:{error2}"
    try:
        owner.verify_owner_run_receipt(store, receipt)
        verify = "accepted"
    except WorkflowError as error:
        verify = f"{error.code}@{_where(error)}"
    return seal, verify


def _core(g1x_ns: SimpleNamespace, hook: Callable[[Execution, str, str, Any], Any]) -> None:
    real = g1x_ns.core.submit

    def submit(store: Execution, ticket_id: str, step_id: str, payload: str, rules: Any) -> Any:
        out = real(store, ticket_id, step_id, payload, rules)
        forged = hook(store, ticket_id, step_id, out.journal)
        return out if forged is None else replace(out, journal=forged)

    g1x_ns.monkeypatch.setattr(g1x_ns.core, "submit", submit)


def _run(root: Path, reject_first: bool = True) -> tuple[Any, str]:
    workflow = g._start(root)
    try:
        if reject_first:
            workflow.read_inputs()
            assert workflow.submit_review(g._sourced())["status"] == "invalid"
        g._drive(workflow)
    except Exception as error:  # noqa: BLE001 - the probe records a runtime stop as its verdict
        return workflow, f"runtime-stop:{type(error).__name__}:{getattr(error, 'code', error)}"
    return workflow, ""


def _report(case: str, root: Path, workflow: Any, stop: str, applied: list[Any]) -> None:
    seal, verify = _verdicts(root, workflow)
    print(f"VERDICT {case} applied={bool(applied)} {stop} seal={seal} verify={verify}")
    assert applied, case
    assert seal != "accepted" and verify != "accepted", case


def _other_ticket(store: Execution, module_id: str, number: int | None = None) -> str:
    return next(
        a.ticket_id
        for a in store.read().attempts
        if a.module_id == module_id and (number is None or a.number == number)
    )


FIELD_FORGES: dict[str, Callable[[Attempt, Execution], dict[str, Any]]] = {
    "module_id": lambda a, s: {"module_id": "CP-0"},
    "inputs": lambda a, s: {"inputs": a.inputs[:-1]},
    "number0": lambda a, s: {"number": 0, "repair_of": None, "repair_issues": ()},
    "number_only": lambda a, s: {"number": 0},
    "repair_of": lambda a, s: {"repair_of": _other_ticket(s, "CP-0")},
    "repair_issues": lambda a, s: {"repair_issues": ("invented",)},
}


# 1. A valid step of the repair attempt: the first (pending after) and the settling (finished after).
@pytest.mark.parametrize("step", [SOURCED, VIEWED])
@pytest.mark.parametrize("field", list(FIELD_FORGES))
def test_valid_step(g1x: SimpleNamespace, tmp_path: Path, step: str, field: str) -> None:
    applied: list[Any] = []

    def hook(store: Execution, ticket: str, step_id: str, journal: Attempt) -> Any:
        if step_id == step and journal.number == 1 and not journal.issues and not applied:
            applied.append(1)
            return _rewrite(store, ticket, **FIELD_FORGES[field](journal, store))
        return None

    _core(g1x, hook)
    workflow, stop = _run(tmp_path)
    _report(f"valid-{step}-{field}", tmp_path, workflow, stop, applied)


# 2. The rejected step (attempt 0's journaled invalid step that finishes it).
@pytest.mark.parametrize(
    "field",
    ["module_id", "inputs", "number1", "repair_of", "repair_issues"],
)
def test_rejected_step(g1x: SimpleNamespace, tmp_path: Path, field: str) -> None:
    applied: list[Any] = []
    forges = {
        "module_id": lambda a, s: {"module_id": "CP-0"},
        "inputs": lambda a, s: {"inputs": a.inputs[:-1]},
        "number1": lambda a, s: {"number": 1},
        "repair_of": lambda a, s: {"repair_of": _other_ticket(s, "CP-0")},
        "repair_issues": lambda a, s: {"repair_issues": ("invented",)},
    }

    def hook(store: Execution, ticket: str, step_id: str, journal: Attempt) -> Any:
        if journal.number == 0 and journal.status == "finished" and journal.issues and not applied:
            applied.append(1)
            return _rewrite(store, ticket, **forges[field](journal, store))
        return None

    _core(g1x, hook)
    workflow, stop = _run(tmp_path)
    _report(f"rejected-{field}", tmp_path, workflow, stop, applied)


# 2b. A gate-refused submission whose patched precheck also rewrites the pending attempt.
def test_refused_submission_rewrites(g1x: SimpleNamespace, tmp_path: Path) -> None:
    applied: list[Any] = []
    real = owner._PRECHECKS[MODULE]

    def precheck(store: Any, binding: Any, stored: str) -> tuple[str, ...]:
        issues = real(store, binding, stored)
        if issues and not applied:
            applied.append(1)
            _rewrite(Execution(store.directory), binding.ticket_id, repair_issues=("invented",))
        return issues

    g1x.monkeypatch.setitem(owner._PRECHECKS, MODULE, precheck)
    workflow = g._start(tmp_path)
    stop = ""
    try:
        workflow.read_inputs()
        g._read_page(workflow)
        assert workflow.submit_review(g._sourced(g.GATE_MARK))["status"] == "refused"
        workflow._current_sha256 = workflow._store.read().content_hash()
        workflow.read_inputs()
        assert workflow.submit_review(g._sourced())["status"] == "valid"
        workflow.read_inputs()
        assert workflow.submit_review(g._viewed())["status"] == "valid"
    except Exception as error:  # noqa: BLE001
        stop = f"runtime-stop:{type(error).__name__}:{getattr(error, 'code', error)}"
    _report("refused-precheck-rewrite", tmp_path, workflow, stop, applied)


# 3. An interrupt inside a step (patched core interrupts the attempt and relabels it).
@pytest.mark.parametrize("relabel", [False, True])
def test_interrupt_in_step(g1x: SimpleNamespace, tmp_path: Path, relabel: bool) -> None:
    applied: list[Any] = []

    def hook(store: Execution, ticket: str, step_id: str, journal: Attempt) -> Any:
        if step_id == SOURCED and journal.number == 1 and journal.status == "pending" and not applied:
            applied.append(1)
            out = store.interrupt(ticket, "host stopped")
            if relabel:
                out = _rewrite(store, ticket, number=0, repair_of=None, repair_issues=())
            return out
        return None

    _core(g1x, hook)
    workflow, stop = _run(tmp_path)
    _report(f"interrupt-relabel={relabel}", tmp_path, workflow, stop, applied)


# 4. The final snapshot: (a) one more snapshot appended after the last step; (b) the last step's
# `after` replaced by a relabelled sibling (receipt re-pointed and resealed).
def test_final_snapshot_appended(g1x: SimpleNamespace, tmp_path: Path) -> None:
    workflow, stop = _run(tmp_path)
    assert not stop
    store = Execution(tmp_path / "store")
    ticket = _other_ticket(store, MODULE, 1)
    _rewrite(store, ticket, number=0, repair_of=None, repair_issues=())
    workflow._current_sha256 = store.read().content_hash()
    _report("final-appended", tmp_path, workflow, "", [1])


def test_final_snapshot_replaced(g1x: SimpleNamespace, tmp_path: Path) -> None:
    workflow, stop = _run(tmp_path)
    assert not stop
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    store = Execution(tmp_path / "store")
    final = store.read()
    ticket = _other_ticket(store, MODULE, 1)
    forged_attempts = tuple(
        a.model_copy(update={"number": 0, "repair_of": None, "repair_issues": ()})
        if a.ticket_id == ticket
        else a
        for a in final.attempts
    )
    sibling = final.model_copy(update={"attempts": forged_attempts})  # same parent as `final`
    store._write(sibling)
    last = receipt.submissions[-1]
    moved = last.model_copy(update={"snapshot_after_sha256": sibling.content_hash()})
    g._swap(tmp_path, "submissions", last, moved)
    forged = receipt.model_copy(
        update={
            "snapshot_sha256": sibling.content_hash(),
            "submissions": (*receipt.submissions[:-1], moved),
        }
    )
    g._reseal(tmp_path, forged)
    try:
        owner.verify_owner_run_receipt(store, forged)
        verify = "accepted"
    except WorkflowError as error:
        verify = f"{error.code}@{_where(error)}"
    print(f"VERDICT final-replaced verify={verify}")
    assert verify != "accepted"


# 5. A step of another ticket rewrites attempt 0 (same module) or CP-0's attempt.
@pytest.mark.parametrize(
    "target,update",
    [
        ("attempt0", {"number": 1}),
        ("attempt0", {"inputs": ()}),
        ("attempt0", {"repair_issues": ("invented",)}),
        ("cp0", {"number": 1}),
        ("cp0", {"repair_of": "00000000-0000-4000-8000-000000000000"}),
    ],
)
def test_other_ticket(g1x: SimpleNamespace, tmp_path: Path, target: str, update: dict[str, Any]) -> None:
    applied: list[Any] = []

    def hook(store: Execution, ticket: str, step_id: str, journal: Attempt) -> Any:
        if step_id == SOURCED and journal.number == 1 and journal.status == "pending" and not applied:
            applied.append(1)
            other = _other_ticket(store, MODULE, 0) if target == "attempt0" else _other_ticket(store, "CP-0")
            _rewrite(store, other, **update)
            return next(a for a in store.read().attempts if a.ticket_id == ticket)
        return None

    _core(g1x, hook)
    workflow, stop = _run(tmp_path)
    _report(f"other-{target}-{sorted(update)}", tmp_path, workflow, stop, applied)


# 6. The attempt does not exist before the step (unit level on `_verify_transition`).
def test_attempt_absent_before(g1x: SimpleNamespace, tmp_path: Path) -> None:
    workflow, stop = _run(tmp_path)
    assert not stop
    store = Execution(tmp_path / "store")
    final = store.read()
    ticket = _other_ticket(store, MODULE, 1)
    without = final.model_copy(update={"attempts": tuple(a for a in final.attempts if a.ticket_id != ticket)})
    results = []
    for name, before, after, tid in [
        ("absent-before", without, final, ticket),
        ("absent-both", without, without, ticket),
        ("none-ticket", final, final, None),
    ]:
        try:
            owner._verify_transition(before, after, "submission", tid, None)
            results.append((name, "accepted"))
        except WorkflowError as error:
            results.append((name, error.code))
    print("VERDICT absent", results)
    assert all(code == "identity_mismatch" for _, code in results)


# Control: the genuine repaired run is accepted by both.
def test_control_genuine_repair(g1x: SimpleNamespace, tmp_path: Path) -> None:
    workflow, stop = _run(tmp_path)
    seal, verify = _verdicts(tmp_path, workflow)
    print(f"VERDICT control-genuine-repair {stop} seal={seal} verify={verify}")
    assert (seal, verify) == ("accepted", "accepted")
