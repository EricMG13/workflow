"""Stage 4 batch 1 adversary probes, class A, on the g1x fake-module harness.

Each test prints `VERDICT <case> <verdict>` and asserts the verdict observed when written, so a
pass of this file means "the observed behaviour still holds", not "the verifier is right".
"""
import shutil
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from deploy_vii.execution import Attempt, Execution, NotAuthorized
from deploy_workflow.workflow import WorkflowError

import test_owner_g1x as g
from test_owner_g1x import g1x  # noqa: F401  (fixture)

owner = g.owner
MODULE, SOURCED, VIEWED = g.MODULE, g.SOURCED, g.VIEWED


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


def _relabel_core(g1x_ns: SimpleNamespace, when: Any, **update: Any) -> None:
    """A patched owner core: after the genuine journal of a step `when(step_id, attempt)` picks,
    the attempt is rewritten in a new snapshot (the patched runtime writes the store)."""
    real = g1x_ns.core.submit

    def submit(store: Execution, ticket_id: str, step_id: str, payload: str, rules: Any) -> Any:
        out = real(store, ticket_id, step_id, payload, rules)
        if when(step_id, out.journal):
            out = replace(out, journal=_rewrite(store, ticket_id, **update))
        return out

    g1x_ns.monkeypatch.setattr(g1x_ns.core, "submit", submit)


def _seal_and_verdict(root: Path, workflow: Any) -> str:
    try:
        receipt = workflow.write_receipt(root / "receipt.json")
    except WorkflowError as error:
        return "write_receipt:" + str(error.code)
    return g._verdict(root, receipt)


def _reject_first_try(workflow: Any) -> None:
    workflow.read_inputs()
    assert workflow.submit_review(g._sourced())["status"] == "invalid"  # page never read


# A1 (finding): attempt 1 relabelled as a first try (number 0, repair cleared) by the valid
# submission of its first step. Execution.begin cannot yield two attempt-0s on one input set.
def test_a1_repair_relabelled_attempt_zero_in_a_valid_step(g1x: SimpleNamespace, tmp_path: Path) -> None:
    _relabel_core(
        g1x,
        lambda step_id, att: step_id == SOURCED and att.number == 1 and att.status == "pending",
        number=0,
        repair_of=None,
        repair_issues=(),
    )
    workflow = g._start(tmp_path)
    _reject_first_try(workflow)
    g._drive(workflow)
    attempts = g._fake_attempts(tmp_path)
    shape = [(a.number, a.repair_of, a.status, bool(a.issues)) for a in attempts]
    head = next(h for h in Execution(tmp_path / "store").read().heads if h.module_id == MODULE)
    result = Execution(tmp_path / "store").head_module(head)
    verdict = _seal_and_verdict(tmp_path, workflow)
    print("VERDICT a1-relabel", verdict, shape, "head.attempt=", result.attempt, head.status)
    assert [a.number for a in attempts] == [0, 0] and attempts[0].inputs == attempts[1].inputs
    assert verdict == "accepted"


# A2 control: the same relabel keeping number 1 but rewriting repair_issues.
def test_a2_repair_issues_rewritten_in_a_valid_step(g1x: SimpleNamespace, tmp_path: Path) -> None:
    _relabel_core(
        g1x,
        lambda step_id, att: step_id == SOURCED and att.number == 1 and att.status == "pending",
        repair_issues=("an invented first-try issue",),
    )
    workflow = g._start(tmp_path)
    _reject_first_try(workflow)
    g._drive(workflow)
    verdict = _seal_and_verdict(tmp_path, workflow)
    print("VERDICT a2-repair-issues", verdict)
    assert verdict == "write_receipt:identity_mismatch"


# A3: the begin's own `after` carries rewritten repair_issues (begin replay).
def test_a3_repair_issues_rewritten_at_begin(g1x: SimpleNamespace, tmp_path: Path) -> None:
    real = Execution.begin

    def begin(self: Execution, module_id: str) -> Attempt:
        att = real(self, module_id)
        if module_id == MODULE and att.number == 1:
            att = _rewrite(self, att.ticket_id, repair_issues=("invented",))
        return att

    g1x.monkeypatch.setattr(Execution, "begin", begin)
    workflow = g._start(tmp_path)
    _reject_first_try(workflow)
    # the extra snapshot written by the patch is the begin's after (runtime reads after begin)
    g._drive(workflow)
    verdict = _seal_and_verdict(tmp_path, workflow)
    print("VERDICT a3-begin-repair-issues", verdict)
    assert verdict == "write_receipt:identity_mismatch"


def _fork(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst)
    return dst


def _retarget_begin(root: Path, receipt: Any, record: Any, new: Any) -> Any:
    forged = receipt.model_copy(
        update={"begins": tuple(new if b == record else b for b in receipt.begins)}
    )
    g._swap(root, "begins", record, new)
    g._reseal(root, forged)
    return forged


# A4: a begin record whose `before` is an older ancestor (the root snapshot).
def test_a4_begin_on_an_older_ancestor(g1x: SimpleNamespace, tmp_path: Path) -> None:
    receipt = g._sealed(tmp_path / "run")
    root = _fork(tmp_path / "run", tmp_path / "older")
    store = Execution(root / "store")
    record = next(b for b in receipt.begins if b.module_id == MODULE)
    cp0 = next(b for b in receipt.begins if b.module_id == "CP-0")
    new = record.model_copy(update={"snapshot_before_sha256": cp0.snapshot_before_sha256})
    forged = _retarget_begin(root, receipt, record, new)
    verdict = g._verdict(root, forged)
    print("VERDICT a4-older-ancestor", verdict)
    assert verdict == "identity_mismatch"
    assert store is not None


# A5: two begin records with swapped ticket ids.
def test_a5_swapped_ticket_ids(g1x: SimpleNamespace, tmp_path: Path) -> None:
    receipt = g._sealed(tmp_path / "run")
    root = _fork(tmp_path / "run", tmp_path / "swap")
    a, b = receipt.begins
    na = a.model_copy(update={"ticket_id": b.ticket_id})
    nb = b.model_copy(update={"ticket_id": a.ticket_id})
    forged = receipt.model_copy(update={"begins": (na, nb)})
    g._swap(root, "begins", a, na)
    g._swap(root, "begins", b, nb)
    g._reseal(root, forged)
    verdict = g._verdict(root, forged)
    print("VERDICT a5-swapped-tickets", verdict)
    assert verdict == "identity_mismatch"


# A6: NotAuthorized at `_expected_begin` (CP-0 no longer commands the module) is mapped, and a
# programming error inside `current_inputs` is not.
def test_a6_not_authorized_and_programming_error(g1x: SimpleNamespace, tmp_path: Path) -> None:
    receipt = g._sealed(tmp_path)
    store = Execution(tmp_path / "store")
    record = next(b for b in receipt.begins if b.module_id == MODULE)
    before = owner._snapshot(store, record.snapshot_before_sha256)
    heads = tuple(
        h.model_copy(update={"commands": ()}) if h.module_id == "CP-0" else h for h in before.heads
    )
    stripped = before.model_copy(update={"heads": heads})
    with pytest.raises(NotAuthorized):
        owner.current_inputs(stripped, MODULE)
    with pytest.raises(WorkflowError) as caught:
        owner._expected_begin(stripped, MODULE, record.ticket_id)
    print("VERDICT a6-not-authorized", caught.value.code)
    assert caught.value.code == "identity_mismatch"
    with pytest.MonkeyPatch.context() as m:
        m.setattr(owner, "current_inputs", lambda *a: (_ for _ in ()).throw(TypeError("bug")))
        with pytest.raises(TypeError):
            owner.verify_owner_run_receipt(store, receipt)
    print("VERDICT a6-typeerror-propagates ok")


# A7: the pending attempt relabelled finished with an interruption, no issues and no head, in the
# begin's own after (lenient begin, as adv-4's dangling case).
def test_a7_pending_relabelled_finished_interrupted(g1x: SimpleNamespace, tmp_path: Path) -> None:
    g1x.monkeypatch.setattr(Execution, "begin", g._lenient_begin(MODULE))
    workflow = g._start(tmp_path)
    g._drive(workflow)
    store = Execution(tmp_path / "store")
    real = Execution.begin
    workflow._begin(MODULE)
    extra = g._fake_attempts(tmp_path)[-1]
    _rewrite(store, extra.ticket_id, status="finished", interruption="host stopped")
    # the begin record's after still names the pending snapshot; re-point it at the relabel
    rec = workflow._begins[-1]
    new = rec.model_copy(update={"snapshot_after_sha256": store.read().content_hash()})
    owner._retain(store, "begins", new)
    (store.directory / owner.AUDIT / "begins" / rec.content_hash()).unlink()
    workflow._begins[-1] = new
    workflow._current_sha256 = store.read().content_hash()
    verdict = _seal_and_verdict(tmp_path, workflow)
    print("VERDICT a7-relabel-finished-interrupted", verdict)
    assert verdict == "write_receipt:identity_mismatch"
    assert real is not None


# A8: genuine within-run control: one rejected try and its repair verify.
def test_a8_genuine_repair_control(g1x: SimpleNamespace, tmp_path: Path) -> None:
    workflow = g._start(tmp_path)
    _reject_first_try(workflow)
    g._drive(workflow)
    verdict = _seal_and_verdict(tmp_path, workflow)
    print("VERDICT a8-genuine-repair", verdict)
    assert verdict == "accepted"
