"""CP-3 acceptance, Stage 5 only: the closed R3 run over `cases/cp3-cp6-owner`.

Not run in Stage 2 (build-first rule): the fixtures promote CP-1 for real, 11-26 minutes per
case, once per module. Run it under the heavy-job lock (see the report's deferred commands).
Expectations come from `cases/cp3-cp6-owner/expected.json` and the CP-3 lease only.

The lease's consumption proof (D3) for CP-3 stays open until the CP-6 lease run verifies; this
file asserts what CP-3 itself consumes (CP-2, as the attempt inputs show) and that no CP-5 or
CP-6 head exists in an R3 run. It claims no consumer proof, and CP-3 ships no reader.

Not written here (listed in the Stage 2 report): the A4 tamper refusals, the blocked-CP-1A
variant, the stale-snapshot refusal and the create-time refusals.
"""

import copy
import re
from pathlib import Path
from typing import Any

import cp3_cp6_runs as runs
import pytest
import s1a_runs as s1
import test_method_cp3 as stage1

from deploy_vii.contracts import Fact, Module
from deploy_vii.execution import Attempt, Execution
from deploy_vii.live.tools import UNREAD_PAGE
from deploy_workflow.owner_workflow import (
    OwnerRunReceipt,
    OwnerWorkflow,
    verify_owner_run_receipt,
)
from deploy_workflow.owners import cp3

ORACLE = runs.oracle()
MANIFEST: dict[str, Any] = ORACLE["manifest"]
EXPECTED: dict[str, Any] = ORACLE["expected"]
CASES = ("positive", "gap")
RUN = MANIFEST["runs"][runs.RUN]
LABEL = re.compile(r"<label and period of FIG:([a-z0-9_]+)>")


class Closed:
    """One case: the CP-3-active template, and the closed run cloned from it."""

    def __init__(self, case: str, root: Path) -> None:
        self.case = case
        self.template_root = root / "template"
        self.template, self.pack = runs.reach_cp3(case, self.template_root)
        self.root = root / "closed"
        workflow = s1.clone_workflow(self.template, self.root)
        runs.close(workflow, case, self.root / "owner-receipt.json")
        self.store = Execution(self.root / "store")
        self.receipt = OwnerRunReceipt.model_validate_json(
            (self.root / "owner-receipt.json").read_text()
        )

    def fork(self, name: str) -> OwnerWorkflow:
        return s1.clone_workflow(self.template, self.root.parent / name)


@pytest.fixture(scope="module", params=CASES)
def closed(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory) -> Closed:
    return Closed(request.param, tmp_path_factory.mktemp(request.param))


def _head_module(store: Execution, module_id: str) -> Module:
    head = next(h for h in store.read().heads if h.module_id == module_id)
    return store.head_module(head)


def _bind(text: str | None, facts: dict[str, Fact]) -> str | None:
    """The oracle's CP-1 label placeholders, bound to the run's own CP-1 head."""
    if text is None:
        return None

    def label(match: re.Match[str]) -> str:
        fact = facts[match[1]]
        return f"{fact.label} · {fact.period}"

    return LABEL.sub(label, text)


def _cp1_figures(store: Execution) -> dict[str, Fact]:
    cp1 = _head_module(store, "CP-1")
    return {name: s1.figure_fact(cp1.facts, name) for name in ORACLE["submissions"]["figures"]}


def _tree(*roots: Path) -> dict[str, bytes]:
    return {
        str(p): p.read_bytes() for root in roots for p in sorted(root.rglob("*")) if p.is_file()
    }


# --- the closed run -----------------------------------------------------------------------------


def test_receipt_verifies_and_leaves_the_bytes_unchanged(closed: Closed) -> None:
    before = _tree(closed.root / "store", closed.root / "model")
    verify_owner_run_receipt(
        closed.store, closed.receipt, publication_directory=closed.root / "model"
    )
    assert _tree(closed.root / "store", closed.root / "model") == before


def test_plan_heads_and_statuses(closed: Closed) -> None:
    assert list(closed.receipt.plan) == RUN["plan_order"]
    heads = {h.module_id: h for h in closed.store.read().heads}
    assert set(heads) == {"CP-0", "CP-1", "CP-1A", "CP-2", "CP-3", "CP-MODEL"}
    for module_id in heads:
        assert _head_module(closed.store, module_id).status == "restricted", module_id
    assert closed.receipt.model is not None


def test_no_cp5_or_cp6_head_exists_in_an_r3_run(closed: Closed) -> None:
    """D3 stays open: the consumer (CP-6, R6) is not part of this run."""
    assert not {"CP-5", "CP-6"} & {h.module_id for h in closed.store.read().heads}
    assert not hasattr(cp3, "cp3_reader")


def test_cp3_inputs_are_hash_equal_to_the_final_heads(closed: Closed) -> None:
    module = _head_module(closed.store, "CP-3")
    expected = EXPECTED[closed.case]["CP-3"]["module_inputs"]
    assert [i.input_id for i in module.inputs] == expected
    heads = {h.module_id: h for h in closed.store.read().heads}
    for item in module.inputs:
        if item.input_id in heads:
            assert item.sha256 == heads[item.input_id].result_sha256, item.input_id
    # the optional producers CP-3 never reads are not inputs
    for absent in ("CP-3C", "CP-3D", "CP-4C", "CP-2D", "CP-4", "CP-MODEL"):
        assert absent not in {i.input_id for i in module.inputs}


def test_cp_model_inputs_hold_no_cp3(closed: Closed) -> None:
    model = _head_module(closed.store, "CP-MODEL")
    assert "CP-3" not in {i.input_id for i in model.inputs}


def test_cp3_head_equals_the_oracle(closed: Closed) -> None:
    expected = EXPECTED[closed.case]["CP-3"]
    module = _head_module(closed.store, "CP-3")
    facts = _cp1_figures(closed.store)
    tables = _table_view(module)
    wanted = copy.deepcopy(expected["tables"])
    for table in wanted:
        for row in table["rows"]:
            row["label"] = _bind(row["label"], facts)
            row.pop("fact_binding", None)
            for fact in row.get("facts", []):
                fact["text"] = _bind(fact["text"], facts)
    assert tables == wanted
    assert [
        {
            "claim_id": c.claim_id,
            "text": c.text,
            "limitation": c.limitation,
            "cites": [[x.source_id, x.locator] for x in c.citations],
        }
        for c in module.claims
    ] == expected["claims"]
    assert list(module.limitations) == expected["settled_limitations"]


def _table_view(module: Module) -> list[dict[str, Any]]:
    """The oracle's table notation (as `test_method_cp3._actual_tables`, over a settled module).
    The `cp1_references` facts are bound at run time, so only their row ids and labels show."""
    facts = {fact.fact_id: fact for fact in module.facts}
    out = []
    for table in module.tables:
        rows: list[dict[str, Any]] = []
        for row in table.rows:
            item: dict[str, Any] = {"row_id": row.row_id, "label": row.label}
            if table.table_id != "cp1_references":
                item["facts"] = [stage1._cell(facts[i]) for i in row.fact_ids]
            rows.append(item)
        out.append(
            {
                "table_id": table.table_id,
                "title": table.title,
                "row_header": table.row_header,
                "columns": [c.model_dump() for c in table.columns],
                "rows": rows,
            }
        )
    return out


# --- tool use -----------------------------------------------------------------------------------


def _cp3_calls(closed: Closed) -> list[Any]:
    return [c for c in closed.receipt.calls if c.binding.module_id == "CP-3"]


def test_cp3_tool_use(closed: Closed) -> None:
    ok = [c for c in _cp3_calls(closed) if c.status == "ok"]
    if closed.case == "positive":
        reads = sorted((c.arguments["source_id"], c.arguments["first_page"]) for c in ok)
        assert reads == [("market", 1), ("market", 2)]
        assert {c.tool for c in ok} == {"read_pages"}
    else:
        assert ok == []


# --- refusals (oracle refusals.tool_use_refusals) -----------------------------------------------


def test_unread_cited_page_is_invalid_and_re_begun(closed: Closed) -> None:
    if closed.case != "positive":
        pytest.skip("cp3-unread-page is a positive-case refusal")
    workflow = closed.fork("unread")
    payload = runs.bind_figures(
        runs.literal("positive", runs.STEP),
        runs.cp1_bindings(workflow._store, runs.figure_names(runs.literal("positive", runs.STEP))),
    )
    s1.read_cited(workflow, payload, skip=[("market", "page:2")])
    outcome = workflow.submit_review(payload)
    assert outcome["status"] == "invalid"
    assert any(issue.startswith(f"{UNREAD_PAGE}: market page:2") for issue in outcome["issues"])
    attempts: list[Attempt] = [a for a in workflow._store.read().attempts if a.module_id == "CP-3"]
    assert [a.number for a in attempts] == [0, 1]
    assert attempts[1].repair_of == attempts[0].ticket_id


def test_out_of_scope_read_is_refused_not_permitted(closed: Closed) -> None:
    """Positive: the session scope is `market` only, so `financial page:1` is refused. Gap: the
    scope is empty, so any read is. A refused call is scope evidence, not a completion call."""
    workflow = closed.fork("scope")
    call = workflow.invoke(
        "read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}
    )
    assert call["status"] == "refused"
    assert call["error_code"] == "not_permitted"
