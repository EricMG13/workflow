"""CP-3D Stage 2 store runs (deferred to Stage 5): the owner core through `OwnerWorkflow`.

Written with the Stage 2 build and not run there (`work/build/deferred-runs.md`). Every expected
value is read from `cases/cp3d-owner/expected.json` and the literals from `submissions.json`;
nothing is derived here. The consumption proof (D3) stays OPEN: the reader test pins what the
reader exposes and claims no consumer.
"""

import importlib
import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from deploy_vii.execution import Execution
from deploy_workflow.owner_workflow import OwnerRunReceipt, verify_owner_run_receipt
from deploy_workflow.owners import cp3d
from deploy_workflow.workflow import WorkflowError

runs: Any = importlib.import_module("cp3d_runs")
s1a: Any = importlib.import_module("s1a_runs")
connect: Any = importlib.import_module("test_connect_cp3d")
base: Any = importlib.import_module("test_method_cp3d")

ORACLE = runs.oracle()
CASES = runs.CASES


def _closed(case: str, tmp_path: Path) -> tuple[Execution, Path]:
    store, receipt = runs.cp3d_closed(case, tmp_path)
    return Execution(store), receipt


@pytest.fixture(scope="module")
def closed(tmp_path_factory: pytest.TempPathFactory) -> dict[str, tuple[Execution, Path]]:
    return {c: _closed(c, tmp_path_factory.mktemp(f"cp3d-{c}")) for c in CASES}


@pytest.mark.parametrize("case", CASES)
def test_closed_run_settles_restricted_with_the_expected_module(
    closed: dict[str, tuple[Execution, Path]], case: str
) -> None:
    store, _ = closed[case]
    want = ORACLE["expected"]["cases"][case]
    head = runs.head_of_module(store, "CP-3D")
    module = store.head_module(head)
    assert head.status == want["status"] == "restricted"
    assert [i.input_id for i in module.inputs] == want["module_inputs"]
    cp0 = runs.head_of_module(store, "CP-0")
    assert next(i for i in module.inputs if i.input_id == "CP-0").sha256 == cp0.result_sha256
    assert [t.table_id for t in module.tables] == [t["table_id"] for t in want["tables"]]
    facts = {f.fact_id: f for f in module.facts}
    for table in want["tables"]:
        for row in table["rows"]:
            for cell in row["facts"]:
                fact = facts[cell["fact_id"]]
                assert connect._fact_view(fact) == connect._expected_view(cell), cell["fact_id"]
    assert [(c.claim_id, c.text) for c in module.claims] == [
        (c["claim_id"], c["text"]) for c in want["claims"]
    ]
    assert list(module.limitations) == want["own_limitations"]
    assert list(module.inherited_limitations) == want["inherited_limitations"]


@pytest.mark.parametrize("case", CASES)
def test_closed_run_receipt_verifies_and_store_bytes_are_unchanged(
    closed: dict[str, tuple[Execution, Path]], case: str
) -> None:
    store, receipt_path = closed[case]
    before = sorted(
        (p.relative_to(store.directory), p.read_bytes())
        for p in store.directory.rglob("*")
        if p.is_file()
    )
    receipt = OwnerRunReceipt.model_validate_json(receipt_path.read_text(encoding="utf-8"))
    verify_owner_run_receipt(store, receipt)
    after = sorted(
        (p.relative_to(store.directory), p.read_bytes())
        for p in store.directory.rglob("*")
        if p.is_file()
    )
    assert before == after


@pytest.fixture(scope="module")
def after_cp0(tmp_path_factory: pytest.TempPathFactory) -> Any:
    root = tmp_path_factory.mktemp("cp3d-after-cp0")
    workflow, _ = runs.after_cp0("positive", root)
    return workflow, root


def _fork(after_cp0: Any, tmp_path: Path) -> Any:
    return s1a.clone_workflow(after_cp0[0], tmp_path / "fork")


@pytest.mark.parametrize("entry", base.MUTATIONS["entries"], ids=lambda e: e["id"])
def test_each_refusal_mutation_is_journaled_with_exactly_its_issue(
    after_cp0: Any, tmp_path: Path, entry: dict[str, Any]
) -> None:
    workflow = _fork(after_cp0, tmp_path)
    raw = base._edited(ORACLE["submissions"][base.MUTATIONS["base"]], entry["edits"])
    outcome = runs.drive_cp3d(workflow, "positive", text=json.dumps(raw))
    expected = base.STAGE2_REFUSAL_DELTA.get(entry["id"], entry["issue"])
    assert (outcome["status"], outcome["issues"]) == ("invalid", [expected])


@pytest.mark.parametrize("entry", ORACLE["submissions"]["tool_use_refusals"], ids=lambda e: e["id"])
def test_each_tool_use_case_yields_exactly_its_issues_through_rules(
    after_cp0: Any, tmp_path: Path, entry: dict[str, Any]
) -> None:
    workflow = _fork(after_cp0, tmp_path)
    raw = base._edited(ORACLE["submissions"]["positive"], entry.get("edits", []))
    for source, locator in entry["reads"]:
        page = int(locator.split(":")[1])
        call = workflow.invoke(
            "read_pages", {"source_id": source, "first_page": page, "last_page": page}
        )
        assert call["status"] == "ok"
    for _ in range(entry["searches"]):
        s1a.search(workflow, "market", runs.SEARCH_QUERY)
    outcome = workflow.submit_review(json.dumps(raw))
    assert (outcome["status"], outcome["issues"]) == ("invalid", entry["issues"])


def test_extract_statements_and_read_inputs_are_refused_not_permitted(
    after_cp0: Any, tmp_path: Path
) -> None:
    workflow = _fork(after_cp0, tmp_path)
    extract = workflow.invoke(
        "extract_statements", {"source_id": "financial", "first_page": 5, "last_page": 5}
    )
    assert (extract["status"], extract["error_code"]) == ("refused", "not_permitted")
    with pytest.raises(WorkflowError) as error:
        workflow.read_inputs()
    assert error.value.args[0] == "not_permitted"


def test_blocked_case_settles_blocked_after_two_invalid_attempts(
    after_cp0: Any, tmp_path: Path
) -> None:
    blocked = ORACLE["submissions"]["blocked"]
    workflow = _fork(after_cp0, tmp_path)
    first = base._edited(ORACLE["submissions"]["positive"], blocked["attempt_0"]["edits"])
    one = runs.drive_cp3d(workflow, "positive", text=json.dumps(first))
    assert (one["status"], one["issues"]) == ("invalid", [blocked["attempt_0"]["issue"]])
    second = base._edited(ORACLE["submissions"]["positive"], blocked["attempt_1"]["edits"])
    two = runs.drive_cp3d(workflow, "positive", text=json.dumps(second))
    assert (two["status"], two["issues"]) == ("invalid", [blocked["attempt_1"]["issue"]])
    store = Execution(tmp_path / "fork" / "store")
    assert runs.head_of_module(store, "CP-3D").status == "blocked"


@pytest.mark.parametrize("case", CASES)
def test_reader_over_the_settled_head_exposes_the_pinned_values(
    closed: dict[str, tuple[Execution, Path]], case: str
) -> None:
    """D3 stays OPEN: no consumer reads this; the reader only exposes what the oracle pins."""
    store, _ = closed[case]
    head = runs.head_of_module(store, "CP-3D")
    got = cp3d.cp3d_reader(store, head)
    assert got.head_sha256 == head.result_sha256 and got.status == head.status
    pinned = ORACLE["expected"]["consumption"]["reader_pinned_for_cp3c"]["positive_values"]
    if case == "positive":
        assert format(got.discount_margin_mid.amount, "f") == pinned["dm_mid"]
        assert format(got.intensity_mid.amount, "f") == pinned["lam_mid"]
        assert format(got.probability_mid.amount, "f") == pinned["pd_mid"]
    else:
        assert got.intensity_mid.amount is None and got.probability_mid.amount is None
    assert list(got.own_limitations) == ORACLE["expected"]["cases"][case]["own_limitations"]


def test_copy_of_a_closed_store_keeps_the_run_verifiable(
    closed: dict[str, tuple[Execution, Path]], tmp_path: Path
) -> None:
    store, receipt_path = closed["positive"]
    shutil.copytree(store.directory, tmp_path / "store")
    receipt = OwnerRunReceipt.model_validate_json(receipt_path.read_text(encoding="utf-8"))
    verify_owner_run_receipt(Execution(tmp_path / "store"), receipt)
