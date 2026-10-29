"""Stage 4 batch 1 adversary probes, class B2/B3, on the g1x harness. Every forgery keeps the
audit directories, receipt and seal consistent. Expect identity_mismatch."""
import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from deploy_vii.execution import Execution, StepValidation
from deploy_workflow.workflow import SourceEvidence

import test_owner_g1x as g
from test_owner_g1x import g1x  # noqa: F401

owner = g.owner
MODULE, SOURCED, VIEWED = g.MODULE, g.SOURCED, g.VIEWED


def _fork(src: Path, name: str) -> Path:
    dst = src.parent / name
    shutil.copytree(src, dst)
    return dst


def _replace(root: Path, receipt: Any, field: str, kind: str, old: Any, new: Any) -> Any:
    g._swap(root, kind, old, new)
    return receipt.model_copy(
        update={field: tuple(new if r == old else r for r in getattr(receipt, field))}
    )


def _replace_submission(root: Path, receipt: Any, old: Any, new: Any) -> Any:
    if old.binding != new.binding:
        g._swap(root, "bindings", old.binding, new.binding)
    return _replace(root, receipt, "submissions", "submissions", old, new)


def _report(case: str, root: Path, forged: Any) -> str:
    g._reseal(root, forged)
    verdict = g._verdict(root, forged)
    print("VERDICT", case, verdict)
    return verdict


def test_b2_refused_record_forgeries(g1x: SimpleNamespace, tmp_path: Path) -> None:
    long_lines = tuple(f"{i:03d} " + "x" * 50 for i in range(30))
    g1x.monkeypatch.setitem(
        owner._PRECHECKS, MODULE, lambda s, b, stored: long_lines if g.GATE_MARK in stored else ()
    )
    receipt = g._refused_then_sealed(tmp_path / "run", owner.bounded_issues(long_lines))
    old = next(s for s in receipt.submissions if s.disposition == "refused")
    verdicts = {}
    root = _fork(tmp_path / "run", "drop")
    verdicts["drop-one-issue"] = _report(
        "b2-drop-one-issue", root,
        _replace_submission(root, receipt, old, old.model_copy(update={"issues": old.issues[1:]})),
    )
    root = _fork(tmp_path / "run", "reorder")
    swapped = (old.issues[1], old.issues[0], *old.issues[2:])
    verdicts["reorder"] = _report(
        "b2-reorder", root,
        _replace_submission(root, receipt, old, old.model_copy(update={"issues": swapped})),
    )
    root = _fork(tmp_path / "run", "to-invalid")
    verdicts["refused-to-invalid"] = _report(
        "b2-refused-to-invalid", root,
        _replace_submission(root, receipt, old, old.model_copy(update={"disposition": "invalid"})),
    )
    root = _fork(tmp_path / "run", "delete-refused")
    later = [s for s in receipt.submissions if s.sequence > old.sequence]
    renumbered = {s: s.model_copy(update={"sequence": s.sequence - 1}) for s in later}
    g._swap(root, "submissions", old, None)
    for s, n in renumbered.items():
        g._swap(root, "submissions", s, n)
    forged = receipt.model_copy(
        update={
            "submissions": tuple(
                renumbered.get(s, s) for s in receipt.submissions if s != old
            )
        }
    )
    verdicts["delete-refused (class D known gap)"] = _report("b2-delete-refused-D", root, forged)
    print(verdicts)
    assert {k: v for k, v in verdicts.items() if "class D" not in k} == {
        "drop-one-issue": "identity_mismatch",
        "reorder": "identity_mismatch",
        "refused-to-invalid": "identity_mismatch",
    }


def test_b2_invented_validator_issue(g1x: SimpleNamespace, tmp_path: Path) -> None:
    """A patched core journals the viewed step invalid with an issue no validator yields."""
    real_validate = g._validate

    def invented(store: Execution, pack: Any, attempt: Any) -> StepValidation:
        if attempt.steps[-1].step_id == VIEWED and attempt.number == 0:
            return StepValidation(issues=("An invented validator issue",))
        return real_validate(store, pack, attempt)

    g1x.monkeypatch.setattr(g, "_validate", invented)  # the core's submit closes over g._validate
    workflow = g._start(tmp_path)
    workflow.read_inputs()
    g._read_page(workflow)
    assert workflow.submit_review(g._sourced())["status"] == "valid"
    workflow.read_inputs()
    assert workflow.submit_review(g._viewed())["status"] == "invalid"
    g1x.monkeypatch.setattr(g, "_validate", real_validate)
    g._drive(workflow)
    try:
        receipt = workflow.write_receipt(tmp_path / "receipt.json")
        verdict = g._verdict(tmp_path, receipt)
    except owner.WorkflowError as error:
        verdict = "write_receipt:" + error.code
    print("VERDICT b2-invented-validator-issue", verdict)
    assert verdict.endswith("identity_mismatch")


def _run_with_viewed_call(root: Path) -> Any:
    workflow = g._start(root)
    workflow.read_inputs()
    g._read_page(workflow)
    assert workflow.submit_review(g._sourced())["status"] == "valid"
    workflow.read_inputs()
    refused = workflow.invoke("read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1})
    assert refused["status"] == "refused"
    assert workflow.submit_review(g._viewed())["status"] == "valid"
    return workflow.write_receipt(root / "receipt.json")


def test_b3_tool_use_forgeries(g1x: SimpleNamespace, tmp_path: Path) -> None:
    receipt = _run_with_viewed_call(tmp_path / "run")
    assert g._verdict(tmp_path / "run", receipt) == "accepted"
    verdicts = {}
    # (1) a refused call on a non-sourced step forged ok with a body, its binding consistent
    root = _fork(tmp_path / "run", "refused-ok")
    call = next(c for c in receipt.calls if c.binding.step_id == VIEWED)
    ok = call.model_copy(update={"status": "ok", "body": "financial page:1", "error_code": None})
    forged = _replace(root, receipt, "calls", "calls", call, ok)
    sub = next(s for s in forged.submissions if s.binding.binding.step_id == VIEWED)
    nb = sub.binding.model_copy(update={"successful_call_ids": (call.call_id,)})
    forged = _replace_submission(root, forged, sub, sub.model_copy(update={"binding": nb}))
    verdicts["refused-call-forged-ok"] = _report("b3-refused-call-ok", root, forged)
    # (2) source_evidence naming a page no call read (call and binding consistent)
    root = _fork(tmp_path / "run", "evidence")
    call = next(c for c in receipt.calls if c.binding.step_id == SOURCED)
    extra = SourceEvidence(read=(*call.source_evidence.read, ("financial", "page:2")))
    forged = _replace(
        root, receipt, "calls", "calls", call, call.model_copy(update={"source_evidence": extra})
    )
    sub = next(s for s in forged.submissions if s.binding.binding.step_id == SOURCED)
    nb = sub.binding.model_copy(update={"source_evidence": extra})
    forged = _replace_submission(root, forged, sub, sub.model_copy(update={"binding": nb}))
    verdicts["evidence-unread-page"] = _report("b3-evidence-unread-page", root, forged)
    # (3) an altered read_inputs body
    root = _fork(tmp_path / "run", "read-body")
    read = receipt.input_reads[0]
    forged = _replace(
        root, receipt, "input_reads", "input-reads", read,
        read.model_copy(update={"body": read.body.replace("CP-0", "CP-9")}),
    )
    verdicts["altered-read-inputs-body"] = _report("b3-read-body", root, forged)
    # (4) the sourced step's cited page read removed: zero reads, the valid step kept
    root = _fork(tmp_path / "run", "zero-reads")
    call = next(c for c in receipt.calls if c.binding.step_id == SOURCED)
    g._swap(root, "calls", call, None)
    forged = receipt.model_copy(update={"calls": tuple(c for c in receipt.calls if c != call)})
    sub = next(s for s in forged.submissions if s.binding.binding.step_id == SOURCED)
    nb = sub.binding.model_copy(
        update={"call_ids": (), "successful_call_ids": (), "source_evidence": SourceEvidence()}
    )
    forged = _replace_submission(root, forged, sub, sub.model_copy(update={"binding": nb}))
    verdicts["zero-reads-forged-valid"] = _report("b3-zero-reads", root, forged)
    print(verdicts)
    assert set(verdicts.values()) == {"identity_mismatch"}
