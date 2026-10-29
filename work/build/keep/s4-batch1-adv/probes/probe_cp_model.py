"""CP-MODEL publication probes on the S1a promoted positive fixture (slow: one promotion).

P1 genuine control: the first publication fails after `begin` (the files cannot be written), the
attempt is interrupted, the second publication begins attempt 1 and publishes; it must verify.
P2/P3: adv-4's drop-cp1 / other-cp1 with a patched runtime that also lets `finish`/`interrupt`
pass the forged inputs (the builder's tests stop at the producer, `not_permitted`), so the forged
receipt reaches the verifier. P4: P2 with the publication-path `_expected_begin` made lenient,
to see whether the final deterministic binding alone refuses it."""
import importlib
from pathlib import Path
from typing import Any

import pytest

import deploy_vii.cp_model_workflow as cpm
import deploy_vii.execution as ex
from deploy_vii.execution import Attempt, Execution
from deploy_workflow.workflow import WorkflowError

import test_owner_s1a as t
from test_owner_s1a import positive_promoted  # noqa: F401

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")
runs = t.runs


def _walked(promoted: Any, root: Path) -> Any:
    workflow = runs.clone_workflow(promoted[0], root)
    assert runs.drive_cp1a(workflow, promoted[1], "positive")["status"] == "valid"
    outcome = runs.drive_cp2(workflow, "positive", runs.read_cp2(workflow))
    assert outcome["status"] == "valid", outcome["issues"]
    return workflow


def _verdict(workflow: Any, root: Path) -> str:
    try:
        receipt = workflow.write_receipt(root / "receipt.json")
    except WorkflowError as error:
        return "write_receipt:" + error.code
    try:
        owner.verify_owner_run_receipt(
            Execution(root / "store"), receipt, publication_directory=workflow._publication_directory
        )
    except WorkflowError as error:
        return "verify:" + error.code
    return "accepted"


def test_p1_genuine_second_attempt_after_failed_first(positive_promoted: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = _walked(positive_promoted, tmp_path)
    real_write = cpm._write
    calls = [0]

    def failing_once(output: Path, files: dict[str, str]) -> None:
        calls[0] += 1
        if calls[0] == 1:
            raise OSError("disk full (probe)")
        real_write(output, files)

    monkeypatch.setattr(cpm, "_write", failing_once)
    first = workflow.publish()
    second = workflow.publish()
    attempts = [a for a in Execution(tmp_path / "store").read().attempts if a.module_id == "CP-MODEL"]
    shape = [(a.number, a.status, bool(a.issues), a.interruption is not None, a.repair_of is not None) for a in attempts]
    verdict = _verdict(workflow, tmp_path)
    print("VERDICT p1-second-attempt", first["status"], second["status"], shape, verdict)
    assert verdict == "accepted"


def _forged_publish(promoted: Any, root: Path, monkeypatch: pytest.MonkeyPatch, forge: Any) -> Any:
    workflow = _walked(promoted, root)
    real_begin = Execution.begin
    real_inputs = ex.current_inputs

    def begin(self: Execution, module_id: str) -> Attempt:
        attempt = real_begin(self, module_id)
        if module_id != "CP-MODEL":
            return attempt
        snapshot = self.read()
        forged = attempt.model_copy(update={"inputs": forge(attempt.inputs, snapshot)})
        self._write(
            snapshot.model_copy(
                update={
                    "parent": snapshot.content_hash(),
                    "attempts": tuple(forged if a.ticket_id == attempt.ticket_id else a for a in snapshot.attempts),
                }
            )
        )
        return forged

    def lenient_inputs(snapshot: Any, module_id: str) -> Any:
        # the patched producer: finish/interrupt of a pending CP-MODEL take its recorded inputs
        pending = [a for a in snapshot.attempts if a.module_id == module_id and a.status == "pending"]
        if module_id == "CP-MODEL" and pending:
            return pending[-1].inputs
        return real_inputs(snapshot, module_id)

    monkeypatch.setattr(Execution, "begin", begin)
    monkeypatch.setattr(ex, "current_inputs", lenient_inputs)  # execution.py's own global only
    out = workflow.publish()
    monkeypatch.setattr(ex, "current_inputs", real_inputs)
    print("publish", out, workflow._phase)
    return workflow


def _drop(inputs: Any, snapshot: Any) -> Any:
    return tuple(i for i in inputs if i.input_id != "CP-1")


def _other(inputs: Any, snapshot: Any) -> Any:
    stranger = next(h.result_sha256 for h in snapshot.heads if h.module_id == "CP-1A")
    return tuple(i.model_copy(update={"sha256": stranger}) if i.input_id == "CP-1" else i for i in inputs)


def test_p2_drop_cp1_reaching_the_verifier(positive_promoted: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = _forged_publish(positive_promoted, tmp_path, monkeypatch, _drop)
    verdict = _verdict(workflow, tmp_path)
    print("VERDICT p2-drop-cp1", workflow._phase, verdict)
    assert verdict.endswith("identity_mismatch")


def test_p3_other_cp1_reaching_the_verifier(positive_promoted: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = _forged_publish(positive_promoted, tmp_path, monkeypatch, _other)
    verdict = _verdict(workflow, tmp_path)
    print("VERDICT p3-other-cp1", workflow._phase, verdict)
    assert verdict.endswith("identity_mismatch")


def test_p4_drop_cp1_final_binding_alone(positive_promoted: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = _forged_publish(positive_promoted, tmp_path, monkeypatch, _drop)
    real = owner._expected_begin

    def lenient(before: Any, module_id: str, ticket_id: str) -> Any:
        if module_id != "CP-MODEL":
            return real(before, module_id, ticket_id)
        final = Execution(tmp_path / "store").read()
        return next(a for a in final.attempts if a.ticket_id == ticket_id)

    monkeypatch.setattr(owner, "_expected_begin", lenient)
    verdict = _verdict(workflow, tmp_path)
    print("VERDICT p4-final-binding-alone", workflow._phase, verdict)
    assert verdict.endswith("identity_mismatch")
