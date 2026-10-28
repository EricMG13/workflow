"""CP-DR store runs through `OwnerWorkflow` (Stage 5; deferred from Stage 2).

Slow: one CP-0 settlement per run, tool sessions and receipts. Expected values come from
`cases/cpdr-owner/expected.json` through `tests/cpdr_runs.py`; nothing is derived here. The fast
parts of the module (adapter, RULES, view, reader, registrations, a real-store submit and probe)
are `tests/test_connect_cpdr.py`.
"""

import json
import shutil
from pathlib import Path

import cpdr_runs as runs
import pytest

from deploy_vii.execution import Attempt, Execution, ExecutionSnapshot, Head, head_of
from deploy_workflow import owner_workflow as owner
from deploy_workflow.owner_workflow import OwnerRunReceipt, verify_owner_run_receipt
from deploy_workflow.owners import cpdr
from deploy_workflow.workflow import WorkflowError

EXPECTED = runs.oracle()["expected"]


def _verify(store: Path, receipt: Path) -> None:
    sealed = OwnerRunReceipt.model_validate_json(receipt.read_bytes())
    verify_owner_run_receipt(Execution(store), sealed)


@pytest.mark.parametrize("case", runs.CASES)
def test_closed_run_settles_the_oracle_module_and_the_receipt_verifies(
    case: str, tmp_path: Path
) -> None:
    want = EXPECTED["cases"][case]
    store_path, receipt_path = runs.cpdr_closed(case, tmp_path)
    store = Execution(store_path)
    snapshot = store.read()
    plan = runs.oracle()["manifest"]["plan_order_expected"]
    assert [a.module_id for a in snapshot.attempts] == plan
    head = next(h for h in snapshot.heads if h.module_id == "CP-DR")
    module = store.head_module(head)
    assert head.status == want["module_status"]
    assert list(module.limitations) == want["settled_limitations"]
    assert list(module.inherited_limitations) == want["inherited_limitations"]
    assert [t.table_id for t in module.tables] == list(want["tables"])
    _verify(store_path, receipt_path)


@pytest.mark.parametrize("name", list(EXPECTED["refusals"]))
def test_each_refusal_is_a_journaled_invalid_step(name: str, tmp_path: Path) -> None:
    item = runs.oracle()["submissions"]["refusal_inputs"][name]
    workflow, _ = runs.start(tmp_path, empty=item["cp0"] == "cp0_readiness_review_empty_agenda")
    outcome = runs.drive(workflow, json.dumps(item["payload"]), runs.calls_of(item["calls"]))
    assert outcome["status"] == "invalid"
    assert tuple(outcome["issues"]) == tuple(EXPECTED["refusals"][name]["step_issues"])


# --- the closed run: store bytes, the D3 reader, the receipt -------------------------------------


def _bytes(root: Path) -> dict[str, bytes]:
    return {str(p): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _head(store: Execution, module_id: str = "CP-DR") -> Head:
    return next(h for h in store.read().heads if h.module_id == module_id)


@pytest.mark.parametrize("case", runs.CASES)
def test_verifying_the_receipt_leaves_the_store_unchanged_and_the_reader_reads_the_head(
    case: str, tmp_path: Path
) -> None:
    """Acceptance 1 (store bytes unchanged) and the D3 reader on the closed-run head (D3 OPEN)."""
    store_path, receipt_path = runs.cpdr_closed(case, tmp_path)
    before = _bytes(store_path)
    _verify(store_path, receipt_path)
    assert _bytes(store_path) == before
    store = Execution(store_path)
    got = cpdr.cpdr_reader(store, _head(store))
    book = EXPECTED["cases"][case]["bookkeeping"]
    assert got.status == EXPECTED["cases"][case]["module_status"]
    assert [(g.gap_id, g.status, g.questions, g.answered) for g in got.gaps] == [
        (g["gap_id"], g["status"], g["questions"], g["answered"]) for g in book["gaps"]
    ]
    assert got.totals is not None
    assert got.totals.questions_total == book["questions_total"]
    assert got.unresolved == tuple(
        f.removeprefix("TDR.2.").removesuffix(".answer")
        for f in EXPECTED["cases"][case]["consumption_facts"]["missing_for_unresolved"]
    )


def test_a_receipt_of_the_closed_run_names_the_plan_and_both_heads(tmp_path: Path) -> None:
    _, receipt_path = runs.cpdr_closed("partial", tmp_path)
    receipt = OwnerRunReceipt.model_validate_json(receipt_path.read_bytes())
    assert list(receipt.plan) == runs.oracle()["manifest"]["plan_order_expected"]
    assert [h.module_id for h in receipt.heads] == ["CP-0", "CP-DR"]


# --- acceptance 6: the blocked case through OwnerWorkflow ----------------------------------------


def test_the_blocked_case_settles_blocked_and_its_receipt_verifies(tmp_path: Path) -> None:
    subs = runs.oracle()["submissions"]
    workflow, _ = runs.start(tmp_path)
    calls = runs.calls_of("blocked")
    zero = runs.drive(workflow, json.dumps(subs["cpdr"]["blocked"]["attempt_0"]), calls)
    one = runs.drive(workflow, json.dumps(subs["cpdr"]["blocked"]["attempt_1"]), calls)
    assert tuple(zero["issues"]) == tuple(EXPECTED["blocked"]["attempt_0"]["issues"])
    assert tuple(one["issues"]) == tuple(EXPECTED["blocked"]["attempt_1"]["issues"])
    workflow.write_receipt(tmp_path / "owner-receipt.json")
    _verify(tmp_path / "store", tmp_path / "owner-receipt.json")
    store = Execution(tmp_path / "store")
    head = _head(store)
    assert head.status == "blocked"
    got = cpdr.cpdr_reader(store, head)
    assert (got.status, got.gaps, got.totals, got.unresolved) == ("blocked", (), None, ())
    assert store.head_module(head).tables == ()
    assert store.head_module(head).claims == ()


# --- acceptance 5: the run-level refusals --------------------------------------------------------


def test_submit_without_its_own_read_inputs_is_not_permitted(tmp_path: Path) -> None:
    workflow, _ = runs.start(tmp_path)
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(runs.literal("partial"))
    assert caught.value.code == "not_permitted"


def test_a_tool_outside_the_pack_tools_is_refused_not_permitted(tmp_path: Path) -> None:
    workflow, _ = runs.start(tmp_path)
    workflow.read_inputs()
    refused = workflow.invoke("extract_statements", {"source_id": "financial"})
    assert (refused["status"], refused["error_code"]) == ("refused", "not_permitted")


def test_a_snapshot_change_between_read_and_submit_is_stale(tmp_path: Path) -> None:
    workflow, _ = runs.start(tmp_path)
    workflow.read_inputs()
    Execution(tmp_path / "store").interrupt(
        workflow._binding.ticket_id, "external change between read and submit"
    )
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(runs.literal("partial"))
    assert caught.value.code == "stale_binding"


# --- acceptance 8: the tamper recipe, at verifier level ------------------------------------------

TARGET = "TDR.1.missing-ownership-transaction.status"


def _forge(store_path: Path, receipt_path: Path) -> tuple[Execution, OwnerRunReceipt]:
    """The recipe of `expected.tamper`: edit the settled status fact, rewrite every hash that names
    it (blob, snapshot, head, attempt, receipt, the settling submission record, the seal)."""
    store = Execution(store_path)
    receipt = OwnerRunReceipt.model_validate_json(receipt_path.read_bytes())
    snapshot = store.read()
    old = _head(store)
    module = store.head_module(old)
    forged = module.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"text": "Resolved"}) if f.fact_id == TARGET else f
                for f in module.facts
            )
        }
    )
    new_sha = store._store(forged.model_dump_json())
    new_head = head_of(forged, cpdr.QUALIFICATION)
    assert new_head.result_sha256 == new_sha
    attempt = next(a for a in snapshot.attempts if a.result_sha256 == old.result_sha256)
    new_attempt = attempt.model_copy(update={"result_sha256": new_sha})
    new_snapshot = snapshot.model_copy(
        update={
            "heads": tuple(new_head if h.module_id == "CP-DR" else h for h in snapshot.heads),
            "attempts": tuple(
                new_attempt if a.ticket_id == attempt.ticket_id else a for a in snapshot.attempts
            ),
        }
    )
    store._write(new_snapshot)
    digest = new_snapshot.content_hash()
    settling = next(
        s
        for s in receipt.submissions
        if s.binding.binding.module_id == "CP-DR"
        and s.snapshot_after_sha256 == receipt.snapshot_sha256
    )
    edited = settling.model_copy(update={"snapshot_after_sha256": digest})
    audit = store_path / owner.AUDIT / "submissions"
    (audit / settling.content_hash()).unlink()
    (audit / edited.content_hash()).write_bytes(edited.model_dump_json().encode())
    forged_receipt = receipt.model_copy(
        update={
            "snapshot_sha256": digest,
            "heads": tuple(
                h.model_copy(update={"result_sha256": new_sha}) if h.module_id == "CP-DR" else h
                for h in receipt.heads
            ),
            "submissions": tuple(edited if s is settling else s for s in receipt.submissions),
        }
    )
    (store_path / owner.AUDIT / "receipt.sha256").write_text(forged_receipt.content_hash())
    return store, forged_receipt


def test_a_forged_status_fact_reaches_the_probe_and_is_refused_there(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runs.cpdr_closed("partial", tmp_path / "run")
    shutil.copytree(tmp_path / "run" / "store", tmp_path / "forged")
    store, receipt = _forge(tmp_path / "forged", tmp_path / "run" / "owner-receipt.json")
    # everything upstream of the probe passes on the forged copy ...
    owner._verify_audit(store, receipt)
    reached: list[str] = []

    def spy(executed: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
        reached.append(attempt.module_id)
        cpdr.probe(executed, snapshot, attempt)

    monkeypatch.setitem(owner._PROBES, "CP-DR", spy)
    # ... and the CP-DR probe is what refuses it
    with pytest.raises(WorkflowError) as caught:
        verify_owner_run_receipt(store, receipt)
    assert caught.value.code == "identity_mismatch"
    assert reached == ["CP-DR"]
