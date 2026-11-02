"""Phase 2 done-when (identity and periods): an earnings run on a non-test `run_id` reaches CP-1B
with the context's periods, and the pack-B fixture builds against the real validators.

Answer keys, never edited here: `cases/earnings/expected.json#positive/points` (E-QOQ-FLAT),
`cases/context-identity-periods/{manifest,expected,overlays}.json`, `submissions-b.json`.

The walk to CP-1B needs a real CP-1 promotion (11-26 minutes), so it runs only under
`RUN_PROMOTION=1` and is built, not done. The other tests are fast: they drive the real CP-0 and
CP-1 `source_context` validators on the packs, with no promotion.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from deploy_vii.preparation import PreparedPack, prepare
from deploy_vii.readiness import ReadinessReview, validate_review
from deploy_vii.source_context import SourceContextReview, validate_source_context
from deploy_workflow.context import load_context, preparation_request
from deploy_workflow.owner_workflow import OwnerWorkflow

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests"
IDP = ROOT / "cases" / "context-identity-periods"
RUN_ID = "ctx-phase2-1"  # not one of the three frozen earnings test ids
TEST_RUN_IDS = ("slice-cp1b-flat-v1", "slice-cp1b-no-yoy-v1", "slice-cp1b-missing-source-v1")
CONTEXT = "ctx-match"

PROMOTION = pytest.mark.skipif(
    os.environ.get("RUN_PROMOTION") != "1", reason="real CP-1 promotion, 11-26 min; deferred"
)


def _tests(module: str) -> Any:
    """A helper module of `tests/` (not a package): imported the way the sibling suites do."""
    if str(TESTS) not in sys.path:
        sys.path.insert(0, str(TESTS))
    return importlib.import_module(module)


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _context_pack(root: Path) -> PreparedPack:
    """Pack E for `ctx-match`: the context goes through `preparation_request` and `prepare`, with
    a non-test run id; identity and financial are the frozen earnings sources (page-cited)."""
    entry = _json(IDP / "manifest.json")["contexts"][CONTEXT]
    raw = (IDP / entry["file"]).read_bytes()
    (root / "in").mkdir(parents=True)
    (root / "in" / "context.json").write_bytes(raw)
    request = preparation_request(
        load_context(raw), run_id=RUN_ID, context_path="context.json", sources=()
    )
    prepared = prepare(request, root / "in", root / "prepared")
    frozen = _tests("test_financial_workflow").make_pack().sources
    return PreparedPack(run=prepared.run, sources=(*frozen, *prepared.sources))


def _earnings_cp0(pack: PreparedPack) -> str:
    """The earnings preset's frozen CP-0 plus the oracle's `context` assessment (overlay)."""
    review = json.loads(_tests("preset_walks").earnings_cp0(pack))
    overlay = _json(IDP / "overlays.json")["per_context"][CONTEXT]
    review["sources"].append(overlay["cp0_readiness_source"])
    return json.dumps(review, ensure_ascii=False)


def _earnings_source_context(pack: PreparedPack) -> str:
    """The CP-1D oracle's `statements_only` source_context plus the `context` assessment."""
    cp1d = _tests("cp1d_runs")
    document = json.loads(cp1d.literal("statements_only", "cp1_source_context", pack))
    document["sources"].append(
        _json(IDP / "overlays.json")["per_context"][CONTEXT]["cp1_source_context_source"]
    )
    return json.dumps(document, ensure_ascii=False)


def test_done_when_pack_carries_the_context_periods(tmp_path: Path) -> None:
    entry = _json(IDP / "manifest.json")["contexts"][CONTEXT]
    pack = _context_pack(tmp_path)
    assert pack.run.run_id == RUN_ID and RUN_ID not in TEST_RUN_IDS
    assert pack.run.pathway == "earnings_update"
    assert list(pack.run.requested_modules) == entry["run"]["requested_modules"]
    held = [s for s in pack.sources if s.source_id == "context"]
    assert [s.sha256 for s in held] == [entry["sha256"]]
    assert [s.source_id for s in pack.sources] == ["identity", "financial", "context"]


def test_done_when_cp0_and_source_context_validate_with_the_context_source(tmp_path: Path) -> None:
    pack = _context_pack(tmp_path)
    assert validate_review(pack, ReadinessReview.model_validate_json(_earnings_cp0(pack))) == ()
    assert (
        validate_source_context(
            pack, SourceContextReview.model_validate_json(_earnings_source_context(pack))
        )
        == ()
    )


@pytest.mark.parametrize("context_name", ["ctx-b-match", "ctx-b-punct", "ctx-b-mismatch"])
def test_pack_b_fixture_cp0_and_source_context_settle(tmp_path: Path, context_name: str) -> None:
    """Pack B from the oracle files only: the real CP-0 submission settles, and CP-1's
    `source_context` (borrower entity and scope, `context` assessment) is accepted. No promotion."""
    s1a = _tests("s1a_runs")
    workflow, pack, literals = s1a.start_with_context(tmp_path, context_name)
    assert [s.source_id for s in pack.sources] == ["identity", "financial", "business", "context"]
    identity = next(s for s in pack.sources if s.source_id == "identity")
    assert identity.sha256 == _json(IDP / "sources" / "identity-b.json")["sha256"]
    s1a.drive_cp0(workflow, pack, "positive", text=json.dumps(literals["readiness"]))
    text = json.dumps(literals["source_context"], ensure_ascii=False)
    s1a.read_cited(workflow, text)
    s1a.search(workflow, "financial", "subsequent")
    s1a.search(workflow, "business", "acquisition")
    assert s1a.submit_valid(workflow, text)["issues"] == []


def test_pack_b_without_a_context_is_the_identity_b_pack() -> None:
    pack = _tests("s1a_runs").make_pack_b(None)
    assert [s.source_id for s in pack.sources] == ["identity", "financial", "business"]


def test_pack_b_refuses_a_case_without_literals(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no 'gap' case"):
        _tests("s1a_runs").s1a_closed_with_context("gap", tmp_path, "ctx-b-match")


def _walk_to_cp1b(root: Path, pack: PreparedPack) -> OwnerWorkflow:
    """CP-0, CP-1 (the CP-1D `statements_only` stages) and CP-1B, submitted with the frozen
    E-QOQ-FLAT payload, which is the context's pair. The slow part (11-26 minutes)."""
    s1a, cp1d, walks = _tests("s1a_runs"), _tests("cp1d_runs"), _tests("preset_walks")
    workflow = OwnerWorkflow.create(root / "store", pack, publication_directory=root / "model")
    review = _earnings_cp0(pack)
    s1a.read_cited(workflow, review)
    s1a.submit_valid(workflow, review)
    s1a.drive_cp1(
        workflow,
        pack,
        "positive",
        context=_earnings_source_context(pack),
        business_search=False,
        narrative_tool_check=False,
        readiness=lambda wf, _ready: cp1d.readiness_payload(
            "statements_only", cp1d.downstream_inputs(wf)
        ),
    )
    workflow.read_inputs()
    s1a.submit_valid(workflow, walks.cp1b_payload())
    return workflow


@PROMOTION
def test_non_test_run_reaches_cp1b_with_context_periods(tmp_path: Path) -> None:
    """Answer key `cases/earnings/expected.json#positive/points`: the CP-1B head the owner path
    composes for the context's q3-2025 -> q4-2025 equals the E-QOQ-FLAT points. No delivery
    assertion: `earnings_update` has no delivery scope (ruling)."""
    key = _json(ROOT / "cases" / "earnings" / "expected.json")["positive"]
    pack = _context_pack(tmp_path)
    workflow = _walk_to_cp1b(tmp_path, pack)
    store = workflow._store
    head = next(h for h in store.read().heads if h.module_id == "CP-1B")
    owned = {f.fact_id: f for f in store.head_module(head).facts}
    compared = 0
    for point in key["points"]:
        prefix = f"cp1b:T1B.1:{point['measure_id']}"
        if f"{prefix}:delta" not in owned:
            continue  # the measure is not a T1B.1 row
        compared += 1
        delta = owned[f"{prefix}:delta"]
        assert delta.status == point["delta_status"], point["measure_id"]
        want = None if point["delta"] is None else Decimal(point["delta"])
        assert delta.amount == want, point["measure_id"]
        for side in ("prior", "current"):
            value = point[f"{side}_value"]
            assert owned[f"{prefix}:{side}"].amount == (
                None if value is None else Decimal(value)
            ), (point["measure_id"], side)
    assert compared >= 7
