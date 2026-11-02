"""Phase 5 Task 4: a run with a draft legal document reaches CP-4 with the draft limitation.

The oracle is `cases/context-attachments-owner/` (`draft-ok`): its pack, its CP-0 review, its
CP-1 source context and its CP-4 `legal_covenants` payload, all read at run time. The draft
limitation is `expected.json#draft_limitation`, never copied here (P5-P5). Ruling P5T4-R1 splits
the test by speed.

Fast part (runs here): CP-0 with the draft assessment settles, and a context edited to `executed`
after preparation changes nothing, because the pack is frozen and `context_facts` reads the frozen
spans, never the live file (`context.py` `context_facts`).

Slow part (`RUN_PROMOTION=1`, release CI): CP-1 settles, the CP-4 submission quoting the draft
source settles, the CP-4 head carries the draft limitation, and the sealed receipt verifies. It
needs the real CP-1 promotion (11-26 minutes), so it is collected and skipped here (B16).
"""

import importlib
import json
import os
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from deploy_vii import cp4_legal
from deploy_vii.delivery import cp0_view
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare_source
from deploy_vii.render import render
from deploy_workflow.context import context_facts
from deploy_workflow.owner_workflow import OWNER_SPECS, OwnerWorkflow, verify_owner_run_receipt

attach: Any = importlib.import_module("test_owner_cp0_attachments")
runs: Any = importlib.import_module("cp4_runs")
s1a: Any = importlib.import_module("s1a_runs")
draft: Any = importlib.import_module("test_cp4_draft")

CASE = attach.CASE
EXPECTED = attach.EXPECTED
SUBMISSIONS = attach.SUBMISSIONS
DRAFT_LIMITATION: str = EXPECTED["draft_limitation"]
SYNTHETIC_LINE: str = json.loads(
    (attach.ROOT / "cases/cp1d-owner/expected.json").read_text(encoding="utf-8")
)["cases"]["positive"]["settled_limitations"][7]
DRAFT_CASE = "draft-ok"
LEGAL_ID = "legal-draft"


def _start(pack: PreparedPack, root: Path) -> OwnerWorkflow:
    return OwnerWorkflow.create(
        root / "store", pack, specs=OWNER_SPECS, publication_directory=root / "model"
    )


def _settle_cp0(workflow: OwnerWorkflow, pack: PreparedPack) -> str:
    review = attach._review(DRAFT_CASE, pack)
    s1a.read_cited(workflow, review)
    s1a.submit_valid(workflow, review)
    return str(review)


def _live_context_pack(live: Path) -> PreparedPack:
    """The `draft-ok` pack with its context source prepared from `live`, a file the test owns."""
    live.write_bytes((CASE / "context-draft.json").read_bytes())
    request = SourceRequest(source_id="context", path=str(live), media_type="text/plain")
    context = prepare_source(request, live.read_bytes())
    base = attach._pack(DRAFT_CASE)
    sources = tuple(context if s.source_id == "context" else s for s in base.sources)
    return PreparedPack(run=base.run, sources=sources)


# --- fast part: CP-0 with the draft assessment settles ------------------------------------------


def test_the_draft_pack_is_a_draft_context_with_a_draft_legal_source() -> None:
    pack = attach._pack(DRAFT_CASE)
    facts = context_facts(pack)
    assert facts is not None and facts.attachments.legal_documents == "draft"
    assert {s.source_id for s in pack.sources} >= {LEGAL_ID, "context"}
    review = json.loads(attach._review(DRAFT_CASE, pack))
    assessed = {s["source_id"]: s["authority"] for s in review["sources"]}
    assert (
        assessed[LEGAL_ID] == EXPECTED["cases"][DRAFT_CASE]["M"]["CP-0"]["T3.legal-draft.authority"]
    )


def test_cp0_with_the_draft_assessment_settles(tmp_path: Path) -> None:
    pack = attach._pack(DRAFT_CASE)
    assert EXPECTED["cases"][DRAFT_CASE]["P"]["issues"] == []
    workflow = _start(pack, tmp_path)
    _settle_cp0(workflow, pack)
    heads = {h.module_id for h in workflow._store.read().heads}
    assert "CP-0" in heads


def test_a_context_edited_to_executed_after_preparation_changes_nothing(tmp_path: Path) -> None:
    live = tmp_path / "context.json"
    pack = _live_context_pack(live)
    workflow = _start(pack, tmp_path)
    # the user edits the live file after preparation
    live.write_bytes((CASE / "context-executed.json").read_bytes())
    assert json.loads(live.read_text(encoding="utf-8"))["attachments"]["legal_documents"] == (
        "executed"
    )
    facts = context_facts(pack)
    assert facts is not None and facts.attachments.legal_documents == "draft"
    _settle_cp0(workflow, pack)
    heads = {h.module_id for h in workflow._store.read().heads}
    assert "CP-0" in heads


def test_the_same_review_is_refused_when_the_pack_froze_the_executed_context(
    tmp_path: Path,
) -> None:
    """The control: a pack prepared from the executed context asks for an executed legal source,
    so the draft assessment is refused. The frozen draft above is therefore what settled."""
    live = tmp_path / "context.json"
    live.write_bytes((CASE / "context-executed.json").read_bytes())
    request = SourceRequest(source_id="context", path=str(live), media_type="text/plain")
    context = prepare_source(request, live.read_bytes())
    base = attach._pack(DRAFT_CASE)
    sources = tuple(context if s.source_id == "context" else s for s in base.sources)
    pack = PreparedPack(run=base.run, sources=sources)
    issues = attach._gate(pack, attach._review(DRAFT_CASE, pack))
    assert list(issues) == [EXPECTED["texts"]["legal_executed_missing"]]


# --- fast part: the rendered report (ruling P5T2-R6) --------------------------------------------


def _rendered_cp4() -> dict[str, Any]:
    """The CP-4 module of the settled `draft-ok` report as the delivered HTML carries it: the
    report composed by `cp4_legal`, bound as a Module, shown through `delivery.cp0_view` and
    `render` (the path `delivery.py` publishes), then read back from the page's `report-data`
    block, which is what the page's script displays."""
    pack, _upstream = draft._upstream(DRAFT_CASE)
    module = cp4_legal.cp4_module(draft._report(DRAFT_CASE), draft._inputs(pack), 1)
    # delivery.py:172-177 and execution.py:488 both derive `restricted` from non-empty limitations
    restricted = module.model_copy(update={"status": "restricted"})
    page = render(cp0_view(pack, restricted, accepted=True))
    found = re.search(
        r'<script id="report-data" type="application/json">(.*?)</script>', page, re.DOTALL
    )
    assert found is not None
    data = json.loads(found.group(1))
    shown: dict[str, Any] = next(m for m in data["modules"] if m["module_id"] == "CP-4")
    return shown


def test_the_rendered_cp4_report_states_the_draft_limitation() -> None:
    shown = _rendered_cp4()
    want = EXPECTED["cases"][DRAFT_CASE]["M"]["CP-4"]["own_limitations"]
    assert shown["limitations"].count(DRAFT_LIMITATION) == 1
    assert shown["limitations"] == want["exact_order"]
    assert len(shown["limitations"]) == want["total_count"]


def test_the_rendered_t4d1_row_of_the_draft_source_equals_the_key() -> None:
    shown = _rendered_cp4()
    table = next(t for t in shown["tables"] if t["table_id"] == "T4D.1")
    facts = {f["fact_id"]: f for f in shown["facts"]}
    rows = {
        row["label"]: [facts[i]["table_display"] for i in row["fact_ids"][:3]]
        for row in table["rows"]
    }
    want = EXPECTED["cases"][DRAFT_CASE]["M"]["CP-4"]["T4D.1"]
    for label, cells in want.items():
        if isinstance(cells, dict):
            assert rows[label] == list(cells.values()), label


# --- slow part: CP-1, CP-4 and the receipt (release CI) -----------------------------------------

_PROMOTION = pytest.mark.skipif(
    os.environ.get("RUN_PROMOTION") != "1", reason="real CP-1 promotion, 11-26 min; deferred (B16)"
)


def _promoted(root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    """CP-0 and CP-1 settled on the draft pack; CP-4 begun and untouched."""
    pack = attach._pack(DRAFT_CASE)
    workflow = _start(pack, root)
    _settle_cp0(workflow, pack)
    context = json.dumps(SUBMISSIONS["cp1_source_context_draft_ok"], ensure_ascii=False)
    s1a.drive_cp1(
        workflow,
        pack,
        "positive",
        context=context.replace(attach.PLACEHOLDER, pack.content_hash()),
        business_search=False,
    )
    return workflow, pack


@pytest.fixture(scope="module")
def settled(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[OwnerWorkflow, Path]]:
    root = tmp_path_factory.mktemp("cp4-draft-run")
    workflow, _pack = _promoted(root)
    call = workflow.invoke("read_pages", {"source_id": LEGAL_ID, "first_page": 1, "last_page": 3})
    assert call["status"] == "ok", call["error_code"]
    s1a.search(workflow, LEGAL_ID, runs.SEARCH["positive"])
    body: dict[str, Any] = json.loads(workflow.read_inputs()["body"])
    text = json.dumps(SUBMISSIONS["cases"][DRAFT_CASE]["cp4_legal_covenants"], ensure_ascii=False)
    outcome = workflow.submit_review(runs.bind_metric(text, runs.metric_ref(workflow._store, body)))
    assert outcome["status"] == "valid", outcome["issues"]
    yield workflow, root


@_PROMOTION
def test_the_cp4_head_carries_the_draft_limitation_once(
    settled: tuple[OwnerWorkflow, Path],
) -> None:
    workflow, _root = settled
    store = workflow._store
    head = next(h for h in store.read().heads if h.module_id == "CP-4")
    limitations = list(store.head_module(head).limitations)
    want = EXPECTED["cases"][DRAFT_CASE]["M"]["CP-4"]["own_limitations"]
    # The oracle runs are synthetic, so `execution.py` appends one line after the module's own
    # limitations: pinned at cases/cp1d-owner/expected.json#cases/positive/settled_limitations/7.
    own = want["exact_order"]
    assert limitations[: len(own)] == own
    assert len(own) == want["total_count"]
    assert limitations[len(own) :] == [SYNTHETIC_LINE]
    assert limitations.count(DRAFT_LIMITATION) == 1


@_PROMOTION
def test_the_sealed_receipt_verifies(settled: tuple[OwnerWorkflow, Path]) -> None:
    workflow, root = settled
    receipt = workflow.write_receipt(root / "owner-receipt.json")
    verify_owner_run_receipt(workflow._store, receipt)
