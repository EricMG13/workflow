"""CP-4 acceptance: the closed CP-0 -> CP-1 -> CP-4 runs over the pinned oracle.

Expectations come from `cases/cp4-owner/{expected,submissions,manifest}.json` and the CP-4 lease
only, never from the code under test. The slow fixtures promote CP-1 for real (11-26 minutes per
pack) and are built once per module; every refusal test forks a copy. Stage 5 runs this file
(`work/build/deferred-runs.md`); it is written and type-checked in Stage 2.

D3: the runs prove CP-4's consumption of its upstream (CP-0 and CP-1 heads). CP-4 has no
consumer in `plan(("CP-4",))`, so its own downstream consumption stays OPEN and no test here
claims it.
"""

import importlib
import json
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from deploy_vii import cp4_legal
from deploy_vii.contracts import Module
from deploy_vii.execution import Attempt, Execution
from deploy_vii.registry import plan
from deploy_workflow.owner_workflow import OwnerRunReceipt, OwnerWorkflow, verify_owner_run_receipt
from deploy_workflow.workflow import WorkflowError

runs: Any = importlib.import_module("cp4_runs")
s1a: Any = importlib.import_module("s1a_runs")
stage1: Any = importlib.import_module("test_method_cp4")
EXPECTED: dict[str, Any] = stage1.EXPECTED
# The oracle's expected tables for a case; the corrected false-same run equals the gap pack's.
WANT_KEY = {"positive": "positive", "gap": "gap", "gap_false_same_definition": "gap"}


@pytest.fixture(scope="module")
def closed(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict[str, tuple[Path, Path]]]:
    out: dict[str, tuple[Path, Path]] = {}
    for case in runs.CASES:
        store, receipt, _ = runs.cp4_closed(case, tmp_path_factory.mktemp(case))
        out[case] = (store, receipt)
    yield out


@pytest.fixture(scope="module")
def promoted(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict[str, Any]]:
    out: dict[str, Any] = {}
    for case in ("positive", "gap"):
        out[case] = runs.promoted(case, tmp_path_factory.mktemp(f"promoted-{case}"))
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


# --- A4 tool-use refusals (forks of the promoted state) ----------------------------------------


def _fork(promoted: dict[str, Any], case: str, tmp_path: Path) -> OwnerWorkflow:
    template, _pack = promoted[case]
    workflow: OwnerWorkflow = s1a.clone_workflow(template, tmp_path)
    return workflow


def test_unread_cited_page_is_invalid_and_repaired(
    promoted: dict[str, Any], tmp_path: Path
) -> None:
    workflow = _fork(promoted, "positive", tmp_path)
    s1a.search(workflow, "legal-covenants", runs.SEARCH["positive"])
    body = json.loads(workflow.read_inputs()["body"])
    outcome = runs.drive_cp4(workflow, "positive", body)
    assert outcome["status"] == "invalid"
    assert any("legal-covenants page:1" in issue for issue in outcome["issues"])
    attempts = [a for a in workflow._store.read().attempts if a.module_id == "CP-4"]
    assert attempts[-1].repair_of == attempts[0].ticket_id


def test_identity_and_financial_raw_are_not_permitted(
    promoted: dict[str, Any], tmp_path: Path
) -> None:
    workflow = _fork(promoted, "positive", tmp_path)
    for source in ("identity", "financial"):
        call = workflow.invoke("read_pages", {"source_id": source, "first_page": 1, "last_page": 1})
        assert call["error_code"] == "not_permitted"


def test_extract_statements_is_refused(promoted: dict[str, Any], tmp_path: Path) -> None:
    workflow = _fork(promoted, "positive", tmp_path)
    call = workflow.invoke(
        "extract_statements", {"source_id": "legal-covenants", "locators": ["page:1"]}
    )
    assert call["status"] != "ok"


def test_submit_without_read_inputs_is_not_permitted(
    promoted: dict[str, Any], tmp_path: Path
) -> None:
    workflow = _fork(promoted, "positive", tmp_path)
    s1a.read_cited(workflow, runs.literal("positive", "legal_covenants"))
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(runs.literal("positive", "legal_covenants"))
    assert caught.value.code == "not_permitted"


def test_unresolved_figure_placeholder_is_invalid(promoted: dict[str, Any], tmp_path: Path) -> None:
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
