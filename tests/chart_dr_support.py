"""Shared fixtures for the Stage 3 DR.2 to DR.6 chart tests (W2 group d).

Every expected value comes from ``cases/charts/{dr2,dr345,dr6}-expected.json``. A CP-4C module is
rebuilt from the Stage 1 composer (``test_method_cp4c``) the way ``cp4c.restructuring`` assembles
its report, so the five oracle cases (two owner runs and three composer fixtures) need no run;
``settled_module`` takes the settled head of a real store for the two owner runs.
"""

import json
import re
from pathlib import Path
from typing import Any

import test_connect_cp4c as connect
import test_method_cp4c as stage1

from deploy_vii.bindings.shipped import SHIPPED_MAPS
from deploy_vii.contracts import ModuleView, View
from deploy_vii.render import empty_view
from deploy_vii.report_view import ReportView, build, pathways
from deploy_workflow.owners import cp4c

CHARTS = Path(__file__).parents[1] / "cases" / "charts"
CASES = stage1.CASES  # positive, gap, fixture_ev_zero, fixture_ebitda_missing, fixture_debt_missing
GAP_TEXT = re.compile(r"G\d+")


def oracle(name: str) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((CHARTS / f"{name}-expected.json").read_text())
    return loaded


def unbound(text: str) -> str:
    """An oracle spelling has ``G#``; a built one has the report's ``G<n>``."""
    return GAP_TEXT.sub("G#", text)


def composer_module(case: str) -> ModuleView:
    """The CP-4C module of a case as the composer settles it (restricted, no run)."""
    result = stage1._result(case)
    cells = {c.fact.fact_id: c.fact for c in result.cells}
    tables = (
        *(cp4c._report_table(t, cells) for t in result.tables),
        *(cp4c._reference_table(r) for r in result.references),
    )
    facts = (*cells.values(), *(f for r in result.references for f in cp4c._placed_references(r)))
    return ModuleView(
        module_id="CP-4C",
        title="Restructuring fulcrum",
        aliases=(),
        status="restricted",
        artifact_sha256="a" * 64,
        facts=facts,
        tables=tables,
        claims=(),
        limitations=result.own_limitations,
    )


def settled_module(root: Path, case: str) -> ModuleView:
    """The CP-4C head of a real store settled through the owner submit path."""
    store, _pack, _attempt, _done = connect.settled(root, case)
    module = store.head_module(connect._head(store, "CP-4C"))
    return ModuleView(
        module_id="CP-4C",
        title="Restructuring fulcrum",
        aliases=(),
        status=module.status,
        artifact_sha256=module.content_hash(),
        facts=module.facts,
        tables=module.tables,
        claims=module.claims,
        limitations=module.limitations,
    )


def view_with(
    module: ModuleView, case: str = "positive", extra: tuple[ModuleView, ...] = ()
) -> View:
    """A distressed-restructuring view holding ``module`` (and ``extra`` modules, e.g. a blocked
    upstream) in place of their unrun entries."""
    run = stage1._pack(case if case in stage1.RUNS else "positive").run
    placed = {m.module_id: m for m in (module, *extra)}
    base = empty_view(run, candidate=False)
    return View.model_validate(
        base.model_copy(
            update={"modules": tuple(placed.get(m.module_id, m) for m in base.modules)}
        ).model_dump()
    )


def store_module(store: Any, module_id: str) -> ModuleView:
    """The module entry of a seeded store's view (its status, facts and limitations as stored)."""
    return next(m for m in store.view().modules if m.module_id == module_id)


def report_of(view: View) -> ReportView:
    pathway = next(p for p in pathways() if p.id == view.run.pathway)
    return build(view, pathway, SHIPPED_MAPS)
