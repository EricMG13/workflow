"""CP-2E store runs: the closed two-module run over the oracle, CP-0 then CP-2E.

DEFERRED to Stage 5 (brief step 7): written, not run at Stage 2. Expectations come from
`cases/cp2e-owner/expected.json` only. The D3 test pins what the reader exposes; consumption is
OPEN, so nothing here claims completion. Not written: the tamper, stale_binding, blocked and
begin-refused cases (they need the oracle recipes' store forgery; listed under Not verified).
"""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from cp2e_runs import CASES, cp2e_closed, drive_cp0, literal, oracle, start

from deploy_vii.execution import Execution
from deploy_workflow.owner_workflow import (
    OwnerRunReceipt,
    verify_owner_run_receipt,
)
from deploy_workflow.owners import cp2e
from deploy_workflow.workflow import WorkflowError

EXPECTED: dict[str, Any] = oracle()["expected"]
SUBMISSIONS: dict[str, Any] = oracle()["submissions"]


@dataclass
class Closed:
    case: str
    root: Path
    store: Execution
    receipt: OwnerRunReceipt
    expected: dict[str, Any]


@pytest.fixture(scope="module", params=CASES)
def closed(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Closed:
    case: str = request.param
    root = tmp_path_factory.mktemp(f"cp2e-{case}")
    store_path, receipt_path = cp2e_closed(case, root)
    receipt = OwnerRunReceipt.model_validate_json(receipt_path.read_bytes())
    return Closed(case, root, Execution(store_path), receipt, EXPECTED["cases"][case])


def _head(store: Execution, module_id: str) -> Any:
    return next(h for h in store.read().heads if h.module_id == module_id)


def test_plan_heads_and_status(closed: Closed) -> None:
    assert [h.module_id for h in closed.store.read().heads] == EXPECTED["plan"]["plan"]
    assert _head(closed.store, "CP-2E").status == closed.expected["status"]


def test_inputs_are_the_pack_cp0_and_the_submission_tail(closed: Closed) -> None:
    module = closed.store.head_module(_head(closed.store, "CP-2E"))
    assert [i.input_id for i in module.inputs] == closed.expected["module_inputs"]
    cp0 = _head(closed.store, "CP-0")
    assert next(i for i in module.inputs if i.input_id == "CP-0").sha256 == cp0.result_sha256


def test_tables_claims_and_limitations_equal_the_oracle(closed: Closed) -> None:
    module = closed.store.head_module(_head(closed.store, "CP-2E"))
    layouts = [
        t.model_dump(mode="json", exclude={"rows": {"__all__": {"row_kind"}}}, exclude_none=True)
        for t in module.tables
    ]
    assert layouts == closed.expected["module_tables"]
    assert [c.claim_id for c in module.claims] == [c["claim_id"] for c in closed.expected["claims"]]
    assert (
        list(module.limitations)[: len(closed.expected["own_limitations"])]
        == (closed.expected["own_limitations"])
    )
    assert list(module.inherited_limitations) == closed.expected["inherited_limitations"]


def test_the_receipt_verifies_and_the_store_is_unchanged(closed: Closed) -> None:
    before = {p: p.read_bytes() for p in sorted(closed.root.rglob("*")) if p.is_file()}
    verify_owner_run_receipt(closed.store, closed.receipt)
    assert before == {p: p.read_bytes() for p in sorted(closed.root.rglob("*")) if p.is_file()}


def test_tool_use_precedes_the_submit(closed: Closed) -> None:
    required = closed.expected["tool_use_required"]
    binding = next(
        r.binding.binding
        for r in closed.receipt.submissions
        if r.binding.binding.module_id == "CP-2E"
    )
    calls = [c for c in closed.receipt.calls if c.binding == binding and c.status == "ok"]
    pages = {
        (c.arguments["source_id"], f"page:{n}")
        for c in calls
        if c.tool == "read_pages"
        for n in range(c.arguments["first_page"], c.arguments["last_page"] + 1)
    }
    assert {tuple(p) for p in required["read_pages_cover"]} <= pages
    assert sum(c.tool == "search_pack" for c in calls) >= required["search_pack_min"]
    assert required["read_inputs_calls"] == 0
    assert not [r for r in closed.receipt.input_reads if r.binding == binding]


def test_extract_statements_and_read_inputs_are_refused(tmp_path: Path) -> None:
    workflow, pack = start("positive", tmp_path)
    drive_cp0(workflow, pack, "positive")
    refused = workflow.invoke("extract_statements", {"source_id": "financial"})
    assert refused["error_code"] == "not_permitted"
    with pytest.raises(WorkflowError, match="not_permitted"):
        workflow.read_inputs()


@pytest.mark.parametrize("row", EXPECTED["tool_use_refusals"], ids=lambda r: r["id"])
def test_journaled_tool_use_refusals(row: dict[str, Any], tmp_path: Path) -> None:
    source = next(r for r in SUBMISSIONS["tool_use_refusals"] if r["id"] == row["id"])
    workflow, pack = start("positive", tmp_path)
    drive_cp0(workflow, pack, "positive")
    for sid, loc in source["reads"]:
        number = int(loc.split(":")[1])
        workflow.invoke("read_pages", {"source_id": sid, "first_page": number, "last_page": number})
    if source["searches"]:
        workflow.invoke("search_pack", {"query": "hedge", "source_id": "financial"})
    outcome = workflow.submit_review(literal("positive", "macro_fx"))
    assert outcome["status"] == "invalid"
    assert row["issue"] in outcome["issues"]


# --- D3 (OPEN): the reader exposes what the lease pins; no completion is claimed ------------------
def test_d3_reader_exposes_the_pinned_values_of_the_settled_head(closed: Closed) -> None:
    head = _head(closed.store, "CP-2E")
    read = cp2e.cp2e_reader(closed.store, head)
    assert read.head_sha256 == head.result_sha256
    assert read.status == closed.expected["status"]
    if closed.case == "positive":
        pinned = EXPECTED["consumption"]["reader_pinned"]["positive_values"]
        assert read.floating_debt.amount == Decimal(pinned["floating"]["amount"])
        assert read.shocks[0].added_interest.amount == Decimal(
            pinned["first_shock_gross"]["amount"]
        )
        assert read.shocks[0].cov_after.amount == Decimal(pinned["first_shock_cov_after"]["amount"])
    assert EXPECTED["consumption"]["status"] == "OPEN"
