"""FP 04 populated S.4: the CP-1 maturity series on the covenant_refinancing run, read from the
frozen ``cases/charts/s4fp04-expected.json``."""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from test_connect_cp2d import _literal, _submit, make_upstream

from deploy_workflow.financial_series import cp1_chart_series

ORACLE = json.loads((Path(__file__).parents[1] / "cases/charts/s4fp04-expected.json").read_text())
SERIES = ORACLE["chart_series"][0]
POINT = SERIES["points"][0]


@pytest.fixture
def cp1(tmp_path: Path):
    store, attempt = make_upstream(tmp_path, charts=True)
    _submit(store, attempt, _literal("positive"))
    return next(m for m in store.view().modules if m.module_id == "CP-1")


def _s4(module):
    return next(f for f in cp1_chart_series(module) if f.fig_id == "S.4")


def test_s4_is_the_oracle_series_on_the_settled_cp1(cp1) -> None:
    figure = _s4(cp1)
    assert (figure.kind, figure.unit_class, figure.unit) == (
        SERIES["kind"],
        SERIES["unit_class"],
        SERIES["unit"],
    )
    assert figure.title == SERIES["title"]
    assert figure.series == tuple(SERIES["series"])
    assert figure.reason is None and SERIES["reason"] is None
    (point,) = figure.points
    facts = {f.fact_id: f for f in cp1.facts}
    assert (point.series, point.category) == (POINT["series"], POINT["category"])
    principal = facts[point.fact_id]
    assert principal.amount == Decimal(POINT["amount_exact"])
    assert (principal.table_id, principal.field) == ("T4.18", POINT["fact_coordinate"]["field"])
    # The QUARTER alias row counts once; the FY alias never doubles it.
    assert principal.period == POINT["fact_coordinate"]["row"]["period_id"]


def test_s4_companions_follow_the_oracle_order(cp1) -> None:
    (point,) = _s4(cp1).points
    facts = {f.fact_id: f for f in cp1.facts}
    companions = [facts[i] for i in point.companion_fact_ids]
    assert [(c.table_id, c.field) for c in companions] == [
        (part["table_id"], part["field"]) for part in POINT["companion_coordinates"]
    ]
    assert {c.period for c in companions} == {"q4-2025"}


def test_s4_gap_is_a_reason_and_no_point_never_a_zero_bin(cp1) -> None:
    gap = cp1.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"text": None, "status": "missing", "limitation": "Not stated"})
                if f.table_id == "T4.18" and f.field == "maturity_date"
                else f
                for f in cp1.facts
            )
        }
    )
    figure = _s4(gap)
    assert figure.points == () and figure.series == () and figure.reason
