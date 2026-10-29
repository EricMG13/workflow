"""Batch 1 fix 1 re-review, CP-MODEL routes on the S1a positive fixture (slow).

- p1: genuine control at the tip (first publication fails after `begin`, interrupted; the second
  begins attempt 1 and publishes): must be accepted by `write_receipt` and
  `verify_owner_run_receipt`.
- intr-*: the first publication fails and a patched `Execution.interrupt` also rewrites a begin-set
  field of the interrupted CP-MODEL attempt; the second publication is genuine.
- reach-*: the three rebuilt High 1 forgeries (the test module's own helper); the receipt
  `write_receipt` would have sealed is built by hand, sealed, and given to
  `verify_owner_run_receipt`. Prints the owner_workflow function:line that refused each.
"""
import importlib
from pathlib import Path
from typing import Any

import pytest

import deploy_vii.cp_model_workflow as cpm
from deploy_vii.execution import Attempt, Execution
from deploy_workflow.workflow import WorkflowError

import test_owner_s1a as t
from test_owner_s1a import positive_promoted  # noqa: F401  (fixture)

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")
runs = t.runs


def test_loaded_from_copy() -> None:
    print("LOADED", owner.__file__, t.__file__)
    assert "s4-batch1-fix1-adv" in owner.__file__ and "s4-batch1-fix1-adv" in t.__file__


def _where(error: BaseException) -> str:
    tb, last = error.__traceback__, "?"
    while tb is not None:
        if tb.tb_frame.f_code.co_filename.endswith("owner_workflow.py"):
            last = f"{tb.tb_frame.f_code.co_name}:{tb.tb_lineno}"
        tb = tb.tb_next
    return last


def _hand_receipt(workflow: Any) -> Any:
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


def _verdicts(workflow: Any, root: Path) -> tuple[str, str]:
    try:
        receipt = workflow.write_receipt(root / "receipt.json")
        seal = "accepted"
    except WorkflowError as error:
        seal = f"{error.code}@{_where(error)}"
        receipt = _hand_receipt(workflow)
    try:
        owner.verify_owner_run_receipt(
            Execution(root / "store"), receipt, publication_directory=workflow._publication_directory
        )
        verify = "accepted"
    except WorkflowError as error:
        verify = f"{error.code}@{_where(error)}"
    return seal, verify


def _walked(promoted: Any, root: Path) -> Any:
    workflow = runs.clone_workflow(promoted[0], root)
    assert runs.drive_cp1a(workflow, promoted[1], "positive")["status"] == "valid"
    outcome = runs.drive_cp2(workflow, "positive", runs.read_cp2(workflow))
    assert outcome["status"] == "valid", outcome["issues"]
    return workflow


def _fail_first_write(monkeypatch: pytest.MonkeyPatch) -> None:
    real_write = cpm._write
    calls = [0]

    def failing_once(output: Path, files: dict[str, str]) -> None:
        calls[0] += 1
        if calls[0] == 1:
            raise OSError("disk full (probe)")
        real_write(output, files)

    monkeypatch.setattr(cpm, "_write", failing_once)


def _shape(root: Path) -> list[Any]:
    return [
        (a.number, a.status, a.repair_of is not None, len(a.inputs), a.interruption is not None)
        for a in Execution(root / "store").read().attempts
        if a.module_id == "CP-MODEL"
    ]


def test_p1_genuine_second_attempt(positive_promoted: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = _walked(positive_promoted, tmp_path)
    _fail_first_write(monkeypatch)
    first, second = workflow.publish(), workflow.publish()
    seal, verify = _verdicts(workflow, tmp_path)
    print("VERDICT p1-genuine", first["status"], second["status"], _shape(tmp_path), seal, verify)
    assert (seal, verify) == ("accepted", "accepted")


@pytest.mark.parametrize("field", ["repair_issues", "inputs"])
def test_intr_forge(positive_promoted: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str) -> None:
    workflow = _walked(positive_promoted, tmp_path)
    _fail_first_write(monkeypatch)
    real_interrupt = Execution.interrupt
    applied: list[Any] = []

    def interrupt(self: Execution, ticket_id: str, reason: str) -> Attempt:
        out = real_interrupt(self, ticket_id, reason)
        if applied:
            return out
        applied.append(1)
        snap = self.read()
        update = (
            {"repair_issues": ("invented",)}
            if field == "repair_issues"
            else {"inputs": tuple(i for i in out.inputs if i.input_id != "CP-1")}
        )
        forged = out.model_copy(update=update)
        self._write(
            snap.model_copy(
                update={
                    "parent": snap.content_hash(),
                    "attempts": tuple(forged if a.ticket_id == ticket_id else a for a in snap.attempts),
                }
            )
        )
        return forged

    monkeypatch.setattr(Execution, "interrupt", interrupt)
    first, second = workflow.publish(), workflow.publish()
    seal, verify = _verdicts(workflow, tmp_path)
    print("VERDICT intr-" + field, first["status"], second["status"], workflow._phase, _shape(tmp_path), seal, verify)
    assert applied
    assert seal != "accepted" and verify != "accepted"


def _drop(inputs: Any, snapshot: Any) -> Any:
    return tuple(i for i in inputs if i.input_id != "CP-1")


def _other(inputs: Any, snapshot: Any) -> Any:
    stranger = next(h.result_sha256 for h in snapshot.heads if h.module_id == "CP-1A")
    return tuple(i.model_copy(update={"sha256": stranger}) if i.input_id == "CP-1" else i for i in inputs)


@pytest.mark.parametrize("case", ["drop", "other", "failed-first"])
def test_reach(positive_promoted: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    forge = _other if case == "other" else _drop
    workflow = t._publish_forged_cp_model(
        positive_promoted, tmp_path, monkeypatch, forge, fail_first_write=case == "failed-first"
    )
    # the verifier's own replay must not see the producer patch
    import deploy_vii.execution as ex

    assert owner.current_inputs is ex.current_inputs, "patch leaked into the verifier"
    seal, verify = _verdicts(workflow, tmp_path)
    print("VERDICT reach-" + case, workflow._phase, _shape(tmp_path), seal, verify)
    assert seal.startswith("identity_mismatch") and verify.startswith("identity_mismatch")
