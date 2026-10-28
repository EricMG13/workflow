"""CP-4 acceptance: the closed CP-0 -> CP-1 -> CP-4 runs over the pinned oracle.

Expectations come from `cases/cp4-owner/{expected,submissions,manifest}.json` and the CP-4 lease
only, never from the code under test. The slow fixtures promote CP-1 for real (11-26 minutes per
pack) and are built once per module; every refusal test forks a copy. Stage 5 runs this file
(`work/build/deferred-runs.md`); it is written and type-checked in Stage 2.

D3: the runs prove CP-4's consumption of its upstream (CP-0 and CP-1 heads). CP-4 has no
consumer in `plan(("CP-4",))`, so its own downstream consumption stays OPEN and no test here
claims it.
"""

import hashlib
import importlib
import shutil
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from deploy_vii import cp4_legal
from deploy_vii.contracts import Fact, Module
from deploy_vii.execution import Attempt, Execution
from deploy_vii.preparation import PreparedPack
from deploy_vii.registry import plan
from deploy_workflow import owner_workflow as ow
from deploy_workflow.owner_workflow import (
    OwnerRunReceipt,
    OwnerWorkflow,
    _verify_audit,
    _verify_calls_reads,
    verify_owner_run_receipt,
)
from deploy_workflow.owners import cp4
from deploy_workflow.workflow import WorkflowError

runs: Any = importlib.import_module("cp4_runs")
s1a: Any = importlib.import_module("s1a_runs")
stage1: Any = importlib.import_module("test_method_cp4")
EXPECTED: dict[str, Any] = stage1.EXPECTED
# The oracle's expected tables for a case; the corrected false-same run equals the gap pack's.
WANT_KEY = {"positive": "positive", "gap": "gap", "gap_false_same_definition": "gap"}


TEMPLATE_OF = {"positive": "positive", "gap": "gap", "gap_false_same_definition": "gap"}
Templates = dict[str, tuple[OwnerWorkflow, PreparedPack]]


@pytest.fixture(scope="module")
def promoted(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Templates]:
    """The lease's two genuine CP-1 promotions (positive and gap). The false-same case forks the
    gap template. Nothing advances a template; every run is a fork of it."""
    yield {
        c: runs.promoted(c, tmp_path_factory.mktemp(f"promoted-{c}")) for c in ("positive", "gap")
    }


@pytest.fixture(scope="module")
def closed(
    tmp_path_factory: pytest.TempPathFactory, promoted: Templates
) -> Iterator[dict[str, tuple[Path, Path]]]:
    out: dict[str, tuple[Path, Path]] = {}
    for case in runs.CASES:
        store, receipt, _ = runs.cp4_closed(
            case, tmp_path_factory.mktemp(case), template=promoted[TEMPLATE_OF[case]]
        )
        out[case] = (store, receipt)
    yield out


def _receipt(path: Path) -> OwnerRunReceipt:
    return OwnerRunReceipt.model_validate_json(path.read_text())


def _head(store: Execution, module_id: str) -> Any:
    return next(h for h in store.read().heads if h.module_id == module_id)


def _attempt(store: Execution, module_id: str) -> Attempt:
    result = _head(store, module_id).result_sha256
    return next(a for a in store.read().attempts if a.result_sha256 == result)


def _tree(root: Path) -> dict[str, bytes]:
    return {str(p): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _cp4(store: Execution) -> tuple[Module, Attempt, Any]:
    """The settled CP-4 module, its attempt and the Stage 1 view of what it read."""
    attempt = _attempt(store, "CP-4")
    module = store.head_module(_head(store, "CP-4"))
    text = store.payload(attempt.steps[0].payload_sha256)
    submission = cp4_legal.CovenantInterpretationSubmission.model_validate_json(text)
    inputs = SimpleNamespace(
        pack=store.pack(),
        submission=submission,
        upstream=cp4_legal.upstream_of(store, attempt),
        inputs=attempt.inputs,
    )
    return module, attempt, inputs


@pytest.mark.parametrize("case", runs.CASES)
def test_receipt_verifies_and_the_store_is_unchanged(
    closed: dict[str, tuple[Path, Path]], case: str
) -> None:
    store_dir, receipt_path = closed[case]
    before = _tree(store_dir)
    verify_owner_run_receipt(Execution(store_dir), _receipt(receipt_path))
    assert _tree(store_dir) == before


@pytest.mark.parametrize("case", runs.CASES)
def test_statuses_and_plan(closed: dict[str, tuple[Path, Path]], case: str) -> None:
    store_dir, receipt_path = closed[case]
    store = Execution(store_dir)
    statuses = EXPECTED["execution"]["statuses"]
    for module_id in ("CP-0", "CP-1", "CP-4"):
        assert _head(store, module_id).status == str(statuses[module_id]).split()[0]
    assert _receipt(receipt_path).plan == plan(("CP-4",))
    assert [h.module_id for h in store.read().heads] == ["CP-0", "CP-1", "CP-4"]


@pytest.mark.parametrize("case", runs.CASES)
def test_tables_claims_and_limitations_equal_the_oracle(
    closed: dict[str, tuple[Path, Path]], case: str
) -> None:
    module, attempt, inputs = _cp4(Execution(closed[case][0]))
    want = EXPECTED[WANT_KEY[case]]["CP-4"]
    assert [t.table_id for t in module.tables] == EXPECTED["table_order"]
    facts = {f.fact_id: f for f in module.facts}
    ctx = stage1._ctx(inputs)
    bound = sum(
        stage1._check_table(t, w, facts, ctx)
        for t, w in zip(module.tables, want["tables"], strict=True)
    )
    assert bound == (11 if WANT_KEY[case] == "positive" else 9)
    got = [
        {
            "claim_id": c.claim_id,
            "text": c.text,
            "cites": stage1._cites(c.citations),
            "limitation": c.limitation,
        }
        for c in module.claims
    ]
    assert got == want["claims"]
    assert list(module.limitations) == want["settled_limitations"]
    assert list(module.inherited_limitations) == want["inherited_limitations"]
    assert [i.input_id for i in module.inputs] == want["settled_module_inputs"]
    assert [i.input_id for i in attempt.inputs] == want["attempt_inputs_in_order"]


@pytest.mark.parametrize("case", runs.CASES)
def test_d3_cp4_reads_its_upstream_heads(closed: dict[str, tuple[Path, Path]], case: str) -> None:
    """The attempt binds the CP-0 and CP-1 heads' result hashes and the settled tables carry the
    CP-1 fact's own id and the heads' hashes (the cells `_check_table` binds)."""
    store = Execution(closed[case][0])
    module, attempt, inputs = _cp4(store)
    bound = {i.input_id: i.sha256 for i in attempt.inputs}
    assert bound["CP-0"] == _head(store, "CP-0").result_sha256
    assert bound["CP-1"] == _head(store, "CP-1").result_sha256
    metric = inputs.upstream.facts[0]
    assert metric.fact_id in {f.fact_id for f in store.head_module(_head(store, "CP-1")).facts}
    texts = {f.text for f in module.facts}
    assert inputs.upstream.cp0_sha256 in texts and inputs.upstream.cp1_sha256 in texts


@pytest.mark.parametrize("case", runs.CASES)
def test_d3_cp4_consumption_stays_open(closed: dict[str, tuple[Path, Path]], case: str) -> None:
    """No module of the plan consumes CP-4: the receipt holds no head or attempt after it."""
    store = Execution(closed[case][0])
    assert EXPECTED["execution"]["published"].startswith("no CP-MODEL")
    assert _receipt(closed[case][1]).model is None
    assert [a.module_id for a in store.read().attempts][-1] == "CP-4"
    assert all(h.module_id in plan(("CP-4",)) for h in store.read().heads)


def test_semantic_refusal_then_corrected_resubmission(
    closed: dict[str, tuple[Path, Path]],
) -> None:
    case = "gap_false_same_definition"
    refusal = EXPECTED[case]["CP-4"]["refusal"]
    store = Execution(closed[case][0])
    receipt = _receipt(closed[case][1])
    records = [s for s in receipt.submissions if s.binding.binding.module_id == "CP-4"]
    assert [r.disposition for r in records] == ["refused", "valid"]
    refused, valid = records
    assert list(refused.issues) == refusal["issues"]
    assert (refused.step_sha256, refused.step_output_sha256) == (None, None)
    assert refused.binding.binding == valid.binding.binding
    assert set(refused.binding.call_ids) <= set(valid.binding.call_ids)
    cp4_attempts = [a for a in store.read().attempts if a.module_id == "CP-4"]
    assert len(cp4_attempts) == 1 and len(cp4_attempts[0].steps) == 1
    refused_snapshot = refused.snapshot_after_sha256
    assert refused_snapshot == refused.binding.binding.snapshot_sha256


# --- A1/A2 at store level ---------------------------------------------------------------------


def _facts(module: Module, table: str, field: str) -> dict[str, Fact]:
    return {f.row_id: f for f in module.facts if f.table_id == table and f.field == field}


@pytest.mark.parametrize("case", runs.CASES)
def test_cp0_authority_commands_and_limitations(
    closed: dict[str, tuple[Path, Path]], case: str
) -> None:
    store = Execution(closed[case][0])
    cp0 = store.head_module(_head(store, "CP-0"))
    want = EXPECTED[WANT_KEY[case]]["CP-0"]
    authority = {row: fact.text for row, fact in _facts(cp0, "T3", "authority").items()}
    assert authority == want["T3_authority"]
    for module_id, commands in want["T8"].items():
        for field in ("candidate_command", "exact_command", "sources", "limits", "upstream"):
            assert _facts(cp0, "T8", field)[module_id].text == commands[field], (module_id, field)
    assert list(cp0.limitations) == want["limitations"]
    assert _head(store, "CP-0").status == want["status"]


@pytest.mark.parametrize("case", ["positive", "gap", "gap_false_same_definition"])
def test_python_values_at_store_level(closed: dict[str, tuple[Path, Path]], case: str) -> None:
    module = _cp4(Execution(closed[case][0]))[0]
    facts = {f.fact_id: f for f in module.facts}
    values = EXPECTED[WANT_KEY[case]]["CP-4"]["python_values"]
    if WANT_KEY[case] == "positive":
        room, share = facts["T4.9.r01.headroom"], facts["T4.9.r01.headroom_share"]
        assert (room.amount, room.unit) == (Decimal(values["headroom"]["value"]), "MULTIPLE")
        assert (share.amount, share.unit) == (Decimal(values["headroom_share"]["value"]), "PERCENT")
        assert facts["T4.9.r01.test_on_cp_1_metric"].text == values["within"]["verdict"]
    else:
        reason = f"{cp4_legal.NOT_CALCULABLE}: {values['reason']}"
        for field in ("headroom", "headroom_share"):
            fact = facts[f"T4.9.r01.{field}"]
            assert (fact.status, fact.amount, fact.text, fact.limitation) == (
                "missing",
                None,
                None,
                reason,
            )
        assert facts["T4.9.r01.test_on_cp_1_metric"].text == values["verdict"]
    assert facts["T4C.9.r01.calculable"].text == values["T4C.9_calculable"]


@pytest.mark.parametrize("case", ["positive", "gap", "gap_false_same_definition"])
def test_source_context_is_never_a_cell(closed: dict[str, tuple[Path, Path]], case: str) -> None:
    module = _cp4(Execution(closed[case][0]))[0]
    rule = EXPECTED[WANT_KEY[case]]["CP-4"]["source_context_only"]
    forbidden = rule["must_not_appear_as_cell_values"]["values"]
    for fact in module.facts:
        if fact.amount is not None:
            assert all(fact.amount != Decimal(v) for v in forbidden), fact.fact_id
        if fact.text is not None:
            assert fact.text.strip() not in forbidden, fact.fact_id
    for row in ("r01", "r02", "r03"):
        cell = next(f for f in module.facts if f.fact_id == f"T4.10.{row}.capacity_amount")
        assert (cell.status, cell.amount, cell.text, cell.limitation) == (
            "missing",
            None,
            None,
            rule["capacity_reason"],
        )


def test_semantic_acceptance_values_never_settle(closed: dict[str, tuple[Path, Path]]) -> None:
    """The false-same payload would compose headroom 3, share 0.75, `Within threshold` and
    T4C.9 `Yes`; none of them is in the settled (corrected) module."""
    case = "gap_false_same_definition"
    module = _cp4(Execution(closed[case][0]))[0]
    unsettled = EXPECTED[case]["CP-4"]["semantic_acceptance"][
        "values_the_documented_rules_would_compose_from_these_inputs_and_that_must_not_qualify"
    ]
    facts = {f.fact_id: f for f in module.facts}
    for field, key in (("headroom", "headroom"), ("headroom_share", "headroom_share")):
        assert facts[f"T4.9.r01.{field}"].amount != Decimal(unsettled[key].split()[0])
        assert facts[f"T4.9.r01.{field}"].status == "missing"
    assert facts["T4.9.r01.test_on_cp_1_metric"].text != unsettled["verdict"]
    assert facts["T4C.9.r01.calculable"].text != unsettled["T4C.9_calculable"]


# --- A3 audit records -------------------------------------------------------------------------


def test_refusal_is_recorded_in_the_owner_run_audit(closed: dict[str, tuple[Path, Path]]) -> None:
    case = "gap_false_same_definition"
    store = Execution(closed[case][0])
    audit = store.directory / ow.AUDIT
    refused = next(
        r
        for r in _receipt(closed[case][1]).submissions
        if r.binding.binding.module_id == "CP-4" and r.disposition == "refused"
    )
    assert (audit / "payloads" / refused.binding.payload_sha256).is_file()  # raw payload
    assert (audit / "payloads" / refused.stored_payload_sha256).is_file()  # filled payload
    assert (audit / "bindings" / refused.binding.content_hash()).is_file()
    assert (audit / "submissions" / refused.content_hash()).is_file()
    assert refused.snapshot_after_sha256 == refused.binding.binding.snapshot_sha256


# --- A3b: the gate is replayed by the verifier -------------------------------------------------


def _fork(promoted: Templates, case: str, tmp_path: Path) -> OwnerWorkflow:
    workflow: OwnerWorkflow = s1a.clone_workflow(promoted[TEMPLATE_OF[case]][0], tmp_path)
    return workflow


def _verdict(store_dir: Path, receipt: OwnerRunReceipt) -> str:
    try:
        verify_owner_run_receipt(Execution(store_dir), receipt)
    except WorkflowError as error:
        return error.code
    return "accepted"


def test_run_built_with_the_gate_off_is_refused_at_the_gate_replay(
    promoted: Templates, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The false-same payload settles when `semantic_issues` is patched off (the engine alone
    composes it); with the gate restored the verifier recomputes it for the valid step, finds
    issues, and refuses. The store is unchanged by the refusal."""
    case = "gap_false_same_definition"
    workflow = _fork(promoted, case, tmp_path)
    with monkeypatch.context() as patch:
        patch.setattr(cp4, "semantic_issues", lambda *, pack, submission: ())
        body = runs.drive_reads(workflow, case)
        assert runs.drive_cp4(workflow, case, body)["status"] == "valid"
        receipt = workflow.write_receipt(tmp_path / "owner-receipt.json")
        assert _verdict(tmp_path / "store", receipt) == "accepted"  # the gate is still off
    before = _tree(tmp_path / "store")
    assert _verdict(tmp_path / "store", receipt) == "identity_mismatch"
    assert _tree(tmp_path / "store") == before


# --- A4: stale binding, repair, and the blocked case ------------------------------------------


def test_unread_cited_page_is_invalid_and_the_repair_verifies(
    promoted: Templates, tmp_path: Path
) -> None:
    workflow = _fork(promoted, "positive", tmp_path)
    outcome = runs.fail_attempt(workflow, "positive")
    assert outcome["status"] == "invalid"
    assert any("legal-covenants page:1" in issue for issue in outcome["issues"])
    store = Execution(tmp_path / "store")
    first, second = [a for a in store.read().attempts if a.module_id == "CP-4"]
    assert second.repair_of == first.ticket_id and second.number == 1
    receipt_path = runs.settle(workflow, "positive", tmp_path)[1]
    verify_owner_run_receipt(Execution(tmp_path / "store"), _receipt(receipt_path))
    assert _head(Execution(tmp_path / "store"), "CP-4").status == "restricted"


def test_attempt_one_also_failing_settles_blocked_and_the_receipt_verifies(
    promoted: Templates, tmp_path: Path
) -> None:
    workflow = _fork(promoted, "positive", tmp_path)
    for _ in range(2):
        assert runs.fail_attempt(workflow, "positive")["status"] == "invalid"
    receipt = workflow.write_receipt(tmp_path / "owner-receipt.json")
    store = Execution(tmp_path / "store")
    assert _head(store, "CP-4").status == "blocked"
    assert store.head_module(_head(store, "CP-4")).status == "blocked"
    assert _verdict(tmp_path / "store", receipt) == "accepted"


def test_snapshot_change_between_read_and_submit_is_stale(
    promoted: Templates, tmp_path: Path
) -> None:
    workflow = _fork(promoted, "positive", tmp_path)
    body = runs.drive_reads(workflow, "positive")
    Execution(tmp_path / "store").interrupt(
        workflow._binding.ticket_id, "external change between read and submit"
    )
    with pytest.raises(WorkflowError) as caught:
        runs.drive_cp4(workflow, "positive", body)
    assert caught.value.code == "stale_binding"


def test_identity_and_financial_raw_are_not_permitted(promoted: Templates, tmp_path: Path) -> None:
    workflow = _fork(promoted, "positive", tmp_path)
    for source in ("identity", "financial"):
        call = workflow.invoke("read_pages", {"source_id": source, "first_page": 1, "last_page": 1})
        assert call["error_code"] == "not_permitted"


def test_extract_statements_is_refused(promoted: Templates, tmp_path: Path) -> None:
    workflow = _fork(promoted, "positive", tmp_path)
    call = workflow.invoke(
        "extract_statements", {"source_id": "legal-covenants", "locators": ["page:1"]}
    )
    assert call["status"] != "ok"


def test_submit_without_read_inputs_is_not_permitted(promoted: Templates, tmp_path: Path) -> None:
    workflow = _fork(promoted, "positive", tmp_path)
    s1a.read_cited(workflow, runs.literal("positive", "legal_covenants"))
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(runs.literal("positive", "legal_covenants"))
    assert caught.value.code == "not_permitted"


def test_unresolved_figure_placeholder_is_invalid(promoted: Templates, tmp_path: Path) -> None:
    workflow = _fork(promoted, "positive", tmp_path)
    runs.drive_reads(workflow, "positive")
    outcome = workflow.submit_review(runs.literal("positive", "legal_covenants"))
    assert outcome["status"] == "invalid"


def test_two_ltm_candidates_fail_the_driver() -> None:
    """The FIG predicate never chooses among equal candidates (lease: the driver fails)."""
    metric = stage1.cp1_fact()
    twin = metric.model_copy(update={"fact_id": metric.fact_id + "-twin"})
    with pytest.raises(RuntimeError):
        s1a.figure_fact([metric, twin], runs.METRIC)


# --- A5: tampering refuses with identity_mismatch ---------------------------------------------


def test_each_tamper_refuses_on_its_own(
    closed: dict[str, tuple[Path, Path]], tmp_path: Path
) -> None:
    receipt = _receipt(closed["positive"][1])
    root = tmp_path / "audit"
    shutil.copytree(closed["positive"][0], root / "store")
    store = Execution(root / "store")
    assert _verdict(root / "store", receipt) == "accepted"

    # 1. an edited read_inputs body, made consistent (audit file, copy and seal agree), so only
    #    the view replay can refuse it
    reads = root / "store" / ow.AUDIT / "input-reads"
    old = next(r for r in receipt.input_reads if r.binding.module_id == "CP-4")
    assert '"cp1_status":"restricted"' in old.body
    body = old.body.replace('"cp1_status":"restricted"', '"cp1_status":"accepted"', 1)
    edited = old.model_copy(
        update={"body": body, "inputs_sha256": hashlib.sha256(body.encode()).hexdigest()}
    )
    forged = receipt.model_copy(
        update={"input_reads": tuple(edited if r == old else r for r in receipt.input_reads)}
    )
    (reads / old.content_hash()).unlink()
    (reads / edited.content_hash()).write_bytes(edited.model_dump_json().encode())
    seal = root / "store" / ow.AUDIT / "receipt.sha256"
    seal.write_text(forged.content_hash())
    _verify_audit(store, forged)  # the audit and the seal agree with the forged copy ...
    with pytest.raises(WorkflowError) as replay:  # ... so the view replay is what refuses
        _verify_calls_reads(store, forged, ow.OWNER_SPECS)
    assert replay.value.code == "identity_mismatch"
    assert _verdict(root / "store", forged) == "identity_mismatch"
    (reads / edited.content_hash()).unlink()
    (reads / old.content_hash()).write_bytes(old.model_dump_json().encode())
    seal.write_text(receipt.content_hash())
    assert _verdict(root / "store", receipt) == "accepted"

    # 2. an edited CP-4 step output: caught by the store's own blob hash check
    output = _attempt(store, "CP-4").steps[0].output_sha256 or ""
    blob = root / "store" / "blobs" / output
    original = blob.read_bytes()
    blob.write_bytes(original + b" ")
    assert _verdict(root / "store", receipt) == "identity_mismatch"
    blob.write_bytes(original)
    assert _verdict(root / "store", receipt) == "accepted"

    # 3. an edited CP-4 SettledHead: a status, then a result hash
    for update in ({"status": "accepted"}, {"result_sha256": "0" * 64}):
        heads = tuple(
            h.model_copy(update=update) if h.module_id == "CP-4" else h for h in receipt.heads
        )
        assert _verdict(root / "store", receipt.model_copy(update={"heads": heads})) == (
            "identity_mismatch"
        )


# --- A7 ---------------------------------------------------------------------------------------


@pytest.mark.skip(
    reason="blocked on G2 (Stage 3): owner_rendering and report_view.build over a verified receipt"
)
def test_a7_render_of_the_six_sections_and_two_rails() -> None:
    """Lease A7: the six FP04 sections and the evidence and limitations rails, for both packs,
    from the verified run only. Not written until G2 lands."""
