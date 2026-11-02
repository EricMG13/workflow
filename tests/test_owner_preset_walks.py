"""One offline walk per preset (Part B O1 Task 5, done-when part 2).

Step 1 comes first (brief, F4): the expected end state of each preset, measured against the frozen
oracles without a CP-1 promotion. `EXPECTED` is that table; `test_step1_table` recomputes it from
the registry (`dependencies`, `cp1a_consumers`) and the oracle files and fails when the two differ.
Only the CP-0 rows are `measured` (a product validator refuses every frozen document); every
`:inputs`, `:consumers`, `:readiness` misfit and the earnings CP-1D stop are `predicted` by a static
comparison, and the gated walk submits the frozen CP-1D payload to observe what it really returns.

Measured result (see `tests/preset_walks.py`): five presets have no frozen CP-0 document for their
sources, so their walk ends at CP-0 as an oracle gap and no payload is invented. `earnings_update`
is the one preset whose CP-0, CP-1, CP-1B and CP-MODEL have frozen literals; its walk stops at
CP-1D, whose frozen submission was frozen on a run without CP-1B (bound inputs differ). Its walk
needs a real CP-1 promotion (11-26 minutes), so it runs only under `RUN_PROMOTION=1` (ruling B16:
written, committed and not run here).

`test_walk_earnings_update` and `test_no_later_module_before_publish` each drive their own
promoted run, so a selective or reversed run cannot fail either.
"""

import json
import os
from pathlib import Path
from typing import Any

import preset_walks as pw
import pytest

from deploy_vii.contracts import PATHWAY_MODULES
from deploy_vii.cp_model_workflow import verify_cp_model_publication
from deploy_vii.preparation import PreparedPack
from deploy_vii.readiness import ReadinessReview, validate_review
from deploy_vii.registry import dependencies, plan
from deploy_vii.source_context import SourceContextReview, validate_source_context
from deploy_workflow.owner_workflow import OwnerWorkflow
from deploy_workflow.workflow import WorkflowError

promotion = pytest.mark.skipif(
    os.environ.get("RUN_PROMOTION") != "1", reason="real CP-1 promotion, 11-26 min; deferred"
)

BASE = ("identity", "financial")
# Step 1: the expected end state of each preset's walk. `first_gap` is the first module (or stage)
# whose frozen submission does not fit the preset; `misfits` are all measured misfits in plan
# order (those behind the first gap are never reached). `cp5_covered`: the frozen CP-5 oracle
# (cases/cp5-owner, over {CP-0, CP-1, CP-1A, CP-2, CP-3}) covers the preset's CP-5 fan-in, so
# CP-5 could settle; for every other preset CP-5 would add unreviewed claims and settle blocked.
EXPECTED: dict[str, dict[str, Any]] = {
    "credit_snapshot": {
        "sources": (*BASE, "business", "market", "legal-covenants"),
        "first_gap": "CP-0",
        "first_gap_basis": "measured",
        "misfits": ("CP-3:inputs", "CP-5:inputs"),
        "cp5_covered": False,
    },
    "earnings_update": {
        "sources": BASE,
        "first_gap": "CP-1D",
        "first_gap_basis": "predicted",
        "misfits": ("CP-1D:inputs", "CP-5:inputs"),
        "cp5_covered": False,
    },
    "relative_value": {
        "sources": (*BASE, "business", "market", "peers"),
        "first_gap": "CP-0",
        "first_gap_basis": "measured",
        "misfits": (
            "CP-1:readiness",
            "CP-1A:consumers",
            "CP-2:inputs",
            "CP-3C:inputs",
            "CP-3:inputs",
            "CP-5:inputs",
        ),
        "cp5_covered": False,
    },
    "covenant_refinancing": {
        "sources": (*BASE, "business", "legal-covenants"),
        "first_gap": "CP-0",
        "first_gap_basis": "measured",
        "misfits": ("CP-1A:consumers", "CP-3C:inputs", "CP-5:inputs"),
        "cp5_covered": False,
    },
    "distressed_restructuring": {
        "sources": (*BASE, "business", "legal-covenants", "ratings"),
        "first_gap": "CP-0",
        "first_gap_basis": "measured",
        "misfits": ("CP-1:readiness", "CP-1A:consumers", "CP-5:inputs"),
        "cp5_covered": False,
    },
    "portfolio_decision": {
        "sources": (*BASE, "business", "market", "prior_case", "update", "market_update"),
        "first_gap": "CP-0",
        "first_gap_basis": "measured",
        "misfits": ("CP-8:inputs",),
        "cp5_covered": True,
    },
}
# Every misfit row is `predicted`: a static comparison of bound inputs, consumer lists or readiness
# entry sets, not an observed refusal. Only a first gap at CP-0 is `measured`.
GAP_PRESETS = sorted(p for p in EXPECTED if EXPECTED[p]["first_gap"] == "CP-0")


def test_step1_table_covers_all_six_presets() -> None:
    assert sorted(EXPECTED) == sorted(PATHWAY_MODULES)


@pytest.mark.parametrize("pathway", sorted(EXPECTED))
def test_step1_table(pathway: str) -> None:
    measured = pw.step1(pathway)
    expected = EXPECTED[pathway]
    compared = {k: v for k, v in expected.items() if k != "first_gap_basis"}
    assert {k: measured[k] for k in compared} == compared
    assert (measured["first_gap"] == "CP-0") == (expected["first_gap_basis"] == "measured")
    # Ruling B1: CP-MODEL is no input of CP-5 in any preset. This is a registry-only check; the
    # receipt-level rejection (`test_receipt_rejects_model_in_cp5_inputs`) moves to O2 Task 5
    # on cases/o2-synthetic (ruling B21).
    assert not measured["cp_model_in_cp5"]
    assert "CP-MODEL" not in dependencies(plan(pw.pathway_modules(pathway)))["CP-5"]


def test_only_portfolio_decision_fan_in_is_covered_by_the_frozen_cp5_oracle() -> None:
    assert [p for p in EXPECTED if EXPECTED[p]["cp5_covered"]] == ["portfolio_decision"]


# --- the pack and fixture tables are the oracles' own ----------------------------------------


def test_module_source_table_matches_the_runs_make_pack() -> None:
    import cp1c_runs
    import cp1d_runs
    import cp2h_runs
    import cp3_cp6_runs
    import cp3c_runs
    import cp3d_runs
    import cp4_runs
    import cp4c_runs
    import cp8_runs

    def extras(pack: PreparedPack) -> tuple[str, ...]:
        return tuple(s.source_id for s in pack.sources if s.source_id not in BASE)

    assert extras(cp3_cp6_runs.make_pack("positive")) == ("business", "market")
    assert extras(cp3_cp6_runs.make_pack("gap")) == ("business",)
    assert extras(cp3c_runs.make_pack()) == pw.MODULE_SOURCES["CP-3C"]
    assert extras(cp4_runs.stage1.make_pack("positive")) == pw.MODULE_SOURCES["CP-4"]
    assert extras(cp4c_runs.make_pack("positive")) == pw.MODULE_SOURCES["CP-4C"]
    assert extras(cp3d_runs.make_pack("positive")) == pw.MODULE_SOURCES["CP-3D"]
    assert extras(cp1c_runs.make_pack("positive")) == pw.MODULE_SOURCES["CP-1C"]
    assert extras(cp2h_runs.make_pack("positive")) == pw.MODULE_SOURCES["CP-2H"]
    assert extras(cp8_runs.make_pack("positive")) == pw.MODULE_SOURCES["CP-8"]
    assert extras(cp1d_runs.make_pack("statements_only")) == ()
    # the frozen runs recorded in FROZEN_RUNS are the manifests' own
    cp1d = cp1d_runs.make_pack("statements_only")
    assert cp1d.run.requested_modules[-1:] == pw.FROZEN_RUNS["CP-1D"]
    assert cp8_runs.make_pack("positive").run.requested_modules[-1:] == pw.FROZEN_RUNS["CP-8"]


@pytest.mark.parametrize("pathway", sorted(EXPECTED))
def test_preset_pack_carries_the_measured_sources(pathway: str) -> None:
    pack = pw.build_pack(pathway)
    assert tuple(s.source_id for s in pack.sources) == EXPECTED[pathway]["sources"]
    assert pack.run.requested_modules == pw.pathway_modules(pathway)


# --- the five presets with no frozen CP-0: the walk ends at CP-0 -----------------------------


@pytest.mark.parametrize("pathway", GAP_PRESETS)
def test_walk_ends_at_cp0_without_a_frozen_document(pathway: str, tmp_path: Path) -> None:
    pack = pw.build_pack(pathway)
    workflow = OwnerWorkflow.create(
        tmp_path / "store", pack, publication_directory=tmp_path / "model"
    )
    assert workflow._plan == plan(pw.pathway_modules(pathway))
    assert workflow._binding.module_id == "CP-0"
    assert workflow._phase == "analytical" and not workflow._begins[1:]
    ids = {s.source_id for s in pack.sources}
    refused = 0
    for oracle, document in pw.frozen_cp0_documents(pack.content_hash()):
        assert {s["source_id"] for s in document["sources"]} != ids, oracle
        # every frozen literal parses, `draft` authority included (Phase 5 Task 1 admitted it)
        review = ReadinessReview.model_validate_json(json.dumps(document))
        assert pw.SOURCE_RULE in validate_review(pack, review), oracle
        refused += 1
    assert refused == len(pw.frozen_cp0_documents())
    with pytest.raises(WorkflowError, match="not_permitted"):
        workflow.write_receipt(tmp_path / "receipt.json")
    with pytest.raises(WorkflowError, match="not_permitted"):
        workflow.publish()


# --- earnings_update: CP-0, CP-1, CP-1B, publish, then the CP-1D oracle gap -------------------


def test_earnings_cp0_and_source_context_validate_on_the_preset_pack() -> None:
    """The measured fit: the earnings oracle's CP-0 with CP-1D's frozen row, and the CP-1D
    oracle's `statements_only` source_context, both pass the product validators on the preset's
    pack."""
    import cp1d_runs

    pack = pw.build_pack("earnings_update")
    review = ReadinessReview.model_validate_json(pw.earnings_cp0(pack))
    assert validate_review(pack, review) == ()
    context = SourceContextReview.model_validate_json(
        cp1d_runs.literal("statements_only", "cp1_source_context", pack)
    )
    assert validate_source_context(pack, context) == ()


def test_earnings_cp0_settles_and_cp1_source_context_is_accepted(tmp_path: Path) -> None:
    """The first two steps of the walk run without a promotion: CP-0 settles on the composed
    document (a real submission through the owner API), and CP-1's source_context literal is
    accepted on the preset pack."""
    import cp1d_runs
    import s1a_runs

    workflow, pack = pw.start_earnings(tmp_path)
    assert [b.module_id for b in workflow._begins] == ["CP-0", "CP-1"]
    assert workflow._binding.module_id == "CP-1"
    assert workflow._binding.step_id == "source_context"
    context = cp1d_runs.literal("statements_only", "cp1_source_context", pack)
    s1a_runs.read_cited(workflow, context)
    s1a_runs.search(workflow, "financial", "subsequent")
    outcome = s1a_runs.submit_valid(workflow, context)
    assert outcome["issues"] == []
    assert workflow._binding.step_id != "source_context"


def test_earnings_cp1b_payload_is_the_frozen_pair_and_assessments() -> None:
    payload = json.loads(pw.cp1b_payload())
    assert payload == {
        "prior_period_id": "q3-2025",
        "current_period_id": "q4-2025",
        "comparison_assessment": "flat_sequential",
        "driver_assessment": "not_supplied",
        "guidance_assessment": "not_supplied",
    }


@pytest.fixture
def earnings_at_stop(tmp_path: Path) -> Any:
    workflow, pack = pw.walk_earnings_to_stop(tmp_path)
    return tmp_path, workflow, pack


@promotion
def test_no_later_module_before_publish(earnings_at_stop: Any) -> None:
    """At the CP-MODEL stop no later module can be read, searched or submitted."""
    _, workflow, _ = earnings_at_stop
    assert workflow._phase == "walked"
    assert [b.module_id for b in workflow._begins] == ["CP-0", "CP-1", "CP-1B"]
    with pytest.raises(WorkflowError, match="not_permitted"):
        workflow.read_inputs()
    with pytest.raises(WorkflowError, match="not_permitted"):
        workflow.invoke("read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1})
    with pytest.raises(WorkflowError, match="not_permitted"):
        workflow.submit_review("{}")
    assert [b.module_id for b in workflow._begins] == ["CP-0", "CP-1", "CP-1B"]


@promotion
def test_walk_earnings_update(earnings_at_stop: Any) -> None:
    root, workflow, _ = earnings_at_stop
    published = workflow.publish()
    assert published["status"] == "ok", published
    assert verify_cp_model_publication(workflow._store, root / "model") == ()
    # every module planned before CP-MODEL, then the first publication, then the rest
    assert [b.module_id for b in workflow._begins][:4] == ["CP-0", "CP-1", "CP-1B", "CP-1D"]
    assert len(workflow._publications) == 1
    assert workflow._publications[0].status == "published"
    assert (
        workflow._begins[3].snapshot_before_sha256
        == workflow._publications[0].snapshot_after_sha256
    )
    # publish takes the snapshot CP-1B's settled submission left, not the one its begin left
    assert workflow._submissions[-1].binding.binding.module_id == "CP-1B"
    assert (
        workflow._submissions[-1].snapshot_after_sha256
        == workflow._publications[0].snapshot_before_sha256
    )
    # CP-1B is a single-step module bound at its begin's snapshot
    assert (
        workflow._begins[2].snapshot_after_sha256
        == workflow._submissions[-1].binding.binding.snapshot_sha256
    )
    # CP-5's bound set is the registry's and holds no CP-MODEL input (ruling B1)
    assert "CP-MODEL" not in dependencies(plan(pw.pathway_modules("earnings_update")))["CP-5"]
    assert workflow._phase == "analytical"
    assert workflow._binding.module_id == "CP-1D"
    # the published CP-MODEL holds a head: publish() reads it back (_record) before "published"
    assert {h.module_id for h in workflow._store.read().heads} == {
        "CP-0",
        "CP-1",
        "CP-1B",
        "CP-MODEL",
    }
    # The Step 1 stop at CP-1D is a prediction (bound inputs differ). Observe it: submit the
    # frozen CP-1D payload. The first promotion run must pin the status here; until
    # then only a refusal of the call itself fails.
    outcome = pw.submit_frozen_cp1d(workflow)
    assert outcome["status"] in ("valid", "invalid"), outcome
    if outcome["status"] == "valid":
        assert "CP-1D" in {h.module_id for h in workflow._store.read().heads}
    else:
        assert workflow._binding.module_id == "CP-1D"
        assert workflow._phase == "analytical"
    with pytest.raises(WorkflowError, match="not_permitted"):
        workflow.write_receipt(root / "receipt.json")
