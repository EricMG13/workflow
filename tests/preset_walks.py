"""One offline walk per preset: Step 1 fit measurement and the earnings_update driver (O1 Task 5).

Step 1 (brief, F4) compares, for each preset, what its frozen per-module oracles were frozen on with
what the preset binds, without a CP-1 promotion:

- the pack: a frozen CP-0 document assesses exactly the sources of the pack it was frozen on
  (`readiness.validate_review`: "Assess every prepared source exactly once"), so a preset whose
  union of module sources equals no frozen document's source set has no usable CP-0;
- each module's bound input set (`dependencies(preset plan)`) against the run its oracle was frozen
  on (`dependencies(plan(frozen requested modules))`);
- CP-1A's consumer list (`business_context.cp1a_consumers`) against the frozen literals';
- CP-1's readiness stage: a preset with several assessed consumers needs one literal covering
  exactly that set.

Nothing here invents a payload: a module with no usable frozen submission ends the walk and is
reported. Only `walk_earnings_to_stop` needs a real CP-1 promotion (11-26 minutes), so the
promotion-gated test is the only caller.
"""

import importlib
import json
from pathlib import Path
from typing import Any

import s1a_runs as s1

from deploy_vii.business_context import cp1a_consumers
from deploy_vii.contracts import PATHWAY_MODULES, Run, Source
from deploy_vii.preparation import PreparedPack
from deploy_vii.registry import dependencies, plan
from deploy_workflow.owner_workflow import OwnerWorkflow
from deploy_workflow.owners import cp1b

ROOT = Path(__file__).resolve().parents[1]
SOURCE_RULE = "Assess every prepared source exactly once"
NO_CP0 = frozenset({"CP-0", "CP-MODEL"})

# The requested modules of the run each module's oracle was frozen on (the manifests' `run`).
FROZEN_RUNS: dict[str, tuple[str, ...]] = {
    "CP-1A": ("CP-1", "CP-MODEL", "CP-1A", "CP-2"),
    "CP-2": ("CP-1", "CP-MODEL", "CP-1A", "CP-2"),
    "CP-3": ("CP-1", "CP-MODEL", "CP-1A", "CP-2", "CP-3"),
    "CP-5": ("CP-1", "CP-1A", "CP-2", "CP-3", "CP-5"),
    "CP-6": ("CP-1", "CP-1A", "CP-2", "CP-3", "CP-5", "CP-6"),
    "CP-1B": ("CP-1B", "CP-5"),
    "CP-1C": ("CP-1C",),
    "CP-1D": ("CP-1D",),
    "CP-2A": ("CP-2A",),
    "CP-2D": ("CP-1", "CP-1A", "CP-2", "CP-2D"),
    "CP-2G": ("CP-2G",),
    "CP-2H": ("CP-2H",),
    "CP-3C": ("CP-1", "CP-1A", "CP-2", "CP-2D", "CP-3C"),
    "CP-3D": ("CP-3D",),
    "CP-4": ("CP-4",),
    "CP-4C": ("CP-4C",),
    "CP-8": ("CP-8",),
}

# Sources beyond identity and financial that a module's positive oracle pack carries (cross-checked
# against the runs' `make_pack` by `tests/test_owner_preset_walks.py`). CP-1D is the
# `statements_only` case; CP-2G is the case with no CP-1D bridge. CP-5 and CP-6 review the
# other modules' outputs and add no source of their own to a preset's pack.
MODULE_SOURCES: dict[str, tuple[str, ...]] = {
    "CP-1A": ("business",),
    "CP-2": ("business",),
    "CP-2D": ("business",),
    "CP-3C": ("business",),
    "CP-3": ("business", "market"),
    "CP-3D": ("market",),
    "CP-1C": ("peers",),
    "CP-4": ("legal-covenants",),
    "CP-4C": ("legal-covenants",),
    "CP-2H": ("ratings",),
    "CP-8": ("prior_case", "update", "market_update"),
}
SOURCE_ORDER = (
    "identity",
    "financial",
    "business",
    "market",
    "legal-covenants",
    "peers",
    "ratings",
    "prior_case",
    "update",
    "market_update",
)
# CP-1 entries whose oracle ships an assessed CP-1 readiness literal, and the entry sets those
# literals cover exactly (`submissions.json` `cp1_readiness` / `cp1_downstream_review`).
READINESS_ENTRIES = frozenset(
    {"CP-1C", "CP-1D", "CP-2A", "CP-2G", "CP-2H", "CP-4C", "CP-2D", "CP-3C", "CP-L10"}
)
READINESS_LITERALS: tuple[frozenset[str], ...] = (
    frozenset({"CP-1C"}),
    frozenset({"CP-1D"}),
    frozenset({"CP-2A"}),
    frozenset({"CP-2A", "CP-2G"}),
    frozenset({"CP-2A", "CP-2G", "CP-2H"}),
    frozenset({"CP-2A", "CP-2G", "CP-4C"}),
    frozenset({"CP-2D", "CP-3C"}),
    frozenset({"CP-1D", "CP-2A", "CP-2G"}),
)


def pathway_modules(pathway: str) -> tuple[str, ...]:
    """The preset's requested modules (`PATHWAY_MODULES` is keyed by the pathway literal)."""
    return {str(key): value for key, value in PATHWAY_MODULES.items()}[pathway]


def _fw() -> Any:
    return importlib.import_module("test_financial_workflow")


def _sources_by_id() -> dict[str, Source]:
    """Every source a preset can need, each from the runs' own hash-checked `make_pack`, so a
    source id carries the one set of bytes every oracle that names it was frozen on."""
    import cp1c_runs
    import cp2h_runs
    import cp3_cp6_runs
    import cp4_runs
    import cp8_runs

    found: dict[str, Source] = {}
    for pack in (
        cp3_cp6_runs.make_pack("positive"),
        cp4_runs.stage1.make_pack("positive"),
        cp1c_runs.make_pack("positive"),
        cp2h_runs.make_pack("positive"),
        cp8_runs.make_pack("positive"),
    ):
        for source in pack.sources:
            if source.source_id in ("identity", "financial"):
                continue  # the financial slice's own bytes, added by `build_pack`
            if found.setdefault(source.source_id, source) != source:
                raise RuntimeError(f"source {source.source_id}: two oracles disagree on its bytes")
    return found


def preset_source_ids(pathway: str) -> tuple[str, ...]:
    """The union of the preset's modules' oracle sources, in a fixed order."""
    needed = {"identity", "financial"}
    for module in plan(pathway_modules(pathway)):
        needed.update(MODULE_SOURCES.get(module, ()))
    return tuple(source for source in SOURCE_ORDER if source in needed)


def preset_run(pathway: str) -> Run:
    """The preset's run: the earnings oracle's issuer and dates, its own id and pathway; the
    requested modules are the pathway's default."""
    manifest = json.loads((ROOT / "cases/cp1d-owner/manifest.json").read_text())
    base = dict(manifest["cases"]["statements_only"]["run"])
    base.pop("requested_modules")
    base.update(run_id=f"preset-{pathway}", pathway=pathway)
    return Run.model_validate_json(json.dumps(base))


def build_pack(pathway: str) -> PreparedPack:
    by_id = _sources_by_id()
    for source in _fw().make_pack().sources:
        by_id.setdefault(source.source_id, source)
    return PreparedPack(
        run=preset_run(pathway), sources=tuple(by_id[i] for i in preset_source_ids(pathway))
    )


def _documents(node: Any, found: list[dict[str, Any]]) -> None:
    if isinstance(node, dict):
        if {"pack_sha256", "objective", "sources", "consumers", "gaps", "analysis"} <= node.keys():
            found.append(node)
        for value in node.values():
            _documents(value, found)
    elif isinstance(node, list):
        for value in node:
            _documents(value, found)


def frozen_cp0_documents(
    pack_sha256: str = "0" * 64,
) -> list[tuple[str, dict[str, Any]]]:
    """Every frozen CP-0 readiness literal in the oracle submissions, with its oracle name and its
    `pack_sha256` bound to `pack_sha256` (the oracles carry a run-time placeholder there, which the
    runs' own `literal()` helpers bind the same way)."""
    documents: list[tuple[str, dict[str, Any]]] = []
    for path in sorted((ROOT / "cases").glob("*/submissions.json")):
        found: list[dict[str, Any]] = []
        _documents(json.loads(path.read_text()), found)
        documents.extend((path.parent.name, {**d, "pack_sha256": pack_sha256}) for d in found)
    return documents


def frozen_document_source_sets() -> set[frozenset[str]]:
    return {frozenset(s["source_id"] for s in doc["sources"]) for _, doc in frozen_cp0_documents()}


def frozen_cp1a_consumer_sets() -> set[frozenset[str]]:
    """The consumer lists of the frozen CP-1A literals (S1, and CP-3/CP-6 runs R3 and R6)."""
    sets: set[frozenset[str]] = set()
    snapshot = json.loads((ROOT / "cases/snapshot/submissions.json").read_text())
    for case in snapshot.values():
        if isinstance(case, dict) and "business_context" in case:
            sets.add(frozenset(c["module_id"] for c in case["business_context"]["consumers"]))
    r36 = json.loads((ROOT / "cases/cp3-cp6-owner/submissions.json").read_text())
    for case in ("positive", "gap"):
        for rows in r36[case]["business_context"]["consumers"].values():
            sets.add(frozenset(c["module_id"] for c in rows))
    return sets


def step1(pathway: str) -> dict[str, Any]:
    """The expected end state of the preset's walk, measured without a promotion."""
    modules = pathway_modules(pathway)
    planned = plan(modules)
    graph = dependencies(planned)
    analytical = tuple(m for m in planned if m not in NO_CP0)
    run = preset_run(pathway)
    misfits: list[str] = []
    entries = {m for m in analytical if m != "CP-1"}
    assessed = frozenset(entries & READINESS_ENTRIES)
    if assessed and assessed not in READINESS_LITERALS:
        misfits.append("CP-1:readiness")
    if "CP-1A" in planned:
        consumers = frozenset(cp1a_consumers(PreparedPack(run=run, sources=())))
        if consumers not in frozen_cp1a_consumer_sets():
            misfits.append("CP-1A:consumers")
    for module in analytical:
        if module in ("CP-1", "CP-1A"):
            continue
        if module not in FROZEN_RUNS:
            misfits.append(f"{module}:no_oracle")
        elif graph[module] != dependencies(plan(FROZEN_RUNS[module]))[module]:
            misfits.append(f"{module}:inputs")
    sources = frozenset(preset_source_ids(pathway))
    first_gap: str | None
    if sources not in frozen_document_source_sets():
        first_gap = "CP-0"
    else:
        first_gap = next(
            (m for m in analytical if any(x.startswith(m + ":") for x in misfits)), None
        )
    return {
        "plan": planned,
        "sources": tuple(preset_source_ids(pathway)),
        "first_gap": first_gap,
        "misfits": tuple(misfits),
        "cp5_covered": graph["CP-5"] == dependencies(plan(FROZEN_RUNS["CP-5"]))["CP-5"],
        "cp_model_in_cp5": "CP-MODEL" in graph["CP-5"],
    }


# --- the earnings_update walk (the one preset whose CP-0 and CP-1 have frozen literals) ----------


def earnings_cp0(pack: PreparedPack) -> str:
    """The earnings oracle's CP-0 (`test_earnings_workflow.foundation_review`: rows CP-1, CP-1B,
    CP-5) with CP-1D's row taken from the CP-1D oracle's `statements_only` literal. CP-1D has no
    row in the earnings oracle and CP-1B none in the CP-1D oracle: each row is frozen where its
    module is."""
    import cp1d_runs

    earnings = importlib.import_module("test_earnings_workflow")
    review = json.loads(earnings.foundation_review(pack))
    frozen = json.loads(cp1d_runs.literal("statements_only", "readiness_review", pack))
    row = next(c for c in frozen["consumers"] if c["module_id"] == "CP-1D")
    rows = review["consumers"]
    review["consumers"] = [*rows[:2], row, *rows[2:]]
    return json.dumps(review, ensure_ascii=False)


def cp1b_payload() -> str:
    """E-QOQ-FLAT's pair and assessments, from the frozen manifest and `owner-expected.json`."""
    manifest = json.loads((ROOT / "cases/earnings/manifest.json").read_text())
    case = next(c for c in manifest["cases"] if c["case_id"] == "E-QOQ-FLAT")
    review = json.loads((ROOT / "cases/earnings/owner-expected.json").read_text())["review"]
    return cp1b.EarningsDeltaOwnerReview(
        prior_period_id=case["prior_period_id"],
        current_period_id=case["current_period_id"],
        comparison_assessment=review["comparison_assessment_by_case"]["E-QOQ-FLAT"],
        driver_assessment=review["driver_assessment"],
        guidance_assessment=review["guidance_assessment"],
    ).model_dump_json()


def start_earnings(root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    """The preset workflow with CP-0 settled; CP-1's source_context step is active. Fast."""
    pack = build_pack("earnings_update")
    workflow = OwnerWorkflow.create(root / "store", pack, publication_directory=root / "model")
    review = earnings_cp0(pack)
    s1.read_cited(workflow, review)
    s1.submit_valid(workflow, review)
    return workflow, pack


def walk_earnings_to_stop(root: Path) -> tuple[OwnerWorkflow, PreparedPack]:
    """CP-0, CP-1 (the CP-1D oracle's `statements_only` stages) and CP-1B settled; the walk is at
    the CP-MODEL stop. The slow part (11-26 minutes)."""
    import cp1d_runs

    workflow, pack = start_earnings(root)
    cp1d_runs.drive_cp1(workflow, pack, "statements_only")
    workflow.read_inputs()
    s1.submit_valid(workflow, cp1b_payload())
    return workflow, pack


def submit_frozen_cp1d(workflow: OwnerWorkflow) -> dict[str, Any]:
    """CP-1D active: its view, the oracle's literal reads and the frozen `earnings_quality`
    payload with its figures bound, exactly as the CP-1D oracle drives it. Returns the outcome
    as the workflow gives it (valid or invalid; never required to be valid)."""
    import cp1d_runs

    body = cp1d_runs.read_view(workflow)
    cp1d_runs.tool_calls(workflow, "statements_only")
    return cp1d_runs.drive_cp1d(workflow, "statements_only", body)
