"""S.5 (Net revenues and Adjusted EBITDA) series, read from the frozen S.5 oracle.

The producer projects settled CP-1 T4.10 facts; every expected value, id rule and label below is
read from ``cases/charts/s5-expected.json`` and never typed here.
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest
from test_financial_series import BASES, change, fixture

from deploy_workflow.financial_series import cp1_chart_series

ORACLE = json.loads((Path(__file__).parents[1] / "cases/charts/s5-expected.json").read_text())
SERIES = ORACLE["chart_series"][0]
ORACLE_POINTS = SERIES["points"]


def s5(module):
    figures = cp1_chart_series(module)
    return next(f for f in figures if f.fig_id == "S.5")


def test_s5_follows_s4_and_carries_the_oracle_metadata():
    figures = cp1_chart_series(fixture())
    assert [f.fig_id for f in figures][-2:] == ["S.4", "S.5"]
    figure = figures[-1]
    assert figure.title == SERIES["title"]
    assert (figure.kind, figure.unit_class, figure.unit) == (
        SERIES["kind"],
        SERIES["unit_class"],
        SERIES["unit"],
    )
    assert figure.series == tuple(SERIES["series"])
    assert SERIES["reason"] is None and figure.reason is None


def test_s5_points_are_the_oracle_points_in_series_then_quarter_order():
    module = fixture()
    facts = {f.fact_id: f for f in module.facts}
    figure = s5(module)
    assert len(figure.points) == len(ORACLE_POINTS) == 8
    for point, expected in zip(figure.points, ORACLE_POINTS, strict=True):
        assert (point.series, point.category) == (expected["series"], expected["category"])
        coordinate = expected["fact_coordinate"]
        fact = facts[point.fact_id]
        assert fact.table_id == coordinate["table_id"] == "T4.10"
        assert fact.row_id == f"T4.10.{coordinate['row_key']['text']}"
        assert fact.field == coordinate["value_field"]
        assert fact.amount == Decimal(expected["amount_exact"])
        # Companions follow the oracle: the field_1 identity fact, then the ten T4.14 period facts.
        parts = expected["companion_coordinates"]
        assert len(point.companion_fact_ids) == len(parts) == 11
        companions = [facts[i] for i in point.companion_fact_ids]
        assert [(c.table_id, c.field) for c in companions] == [
            (part["table_id"], part["field"]) for part in parts
        ]
        assert companions[0].text == coordinate["row_key"]["text"]
        assert {c.row_id for c in companions[1:]} == {f"T4.14.{parts[1]['period_id']}"}


def test_s5_value_field_is_the_adopted_quarter_basis_of_each_period():
    module = fixture()
    fields = {p["fact_coordinate"]["value_field"] for p in ORACLE_POINTS}
    assert fields == {"model-basis:" + b for b in BASES}
    facts = {f.fact_id: f for f in module.facts}
    assert {facts[p.fact_id].field for p in s5(module).points} == fields


def test_s5_never_reads_the_cash_flow_statement():
    module = fixture()
    decoy = module.facts[0].model_copy(
        update={
            "fact_id": "T4.5.revenue.decoy",
            "table_id": "T4.5",
            "row_id": "T4.5.revenue",
            "field": "model-basis:" + BASES[0],
            "amount": Decimal(999),
            "text": None,
        }
    )
    module = module.model_copy(update={"facts": (*module.facts, decoy)})
    assert "T4.5.revenue.decoy" not in {p.fact_id for p in s5(module).points}


def test_s5_gap_quarter_stays_a_point_with_no_value_never_zero():
    module = change(
        fixture(),
        table="T4.10",
        row="T4.10.adjusted_ebitda",
        field="model-basis:" + BASES[1],
        amount=None,
        status="missing",
        limitation="Adjusted EBITDA not supplied",
    )
    facts = {f.fact_id: f for f in module.facts}
    amounts = [facts[p.fact_id].amount for p in s5(module).points]
    assert len(amounts) == 8 and amounts[5] is None
    assert [a for i, a in enumerate(amounts) if i != 5 and a is None] == []
    assert amounts[:4] == [Decimal(30)] * 4


@pytest.mark.parametrize(
    "updates",
    [
        {"unit": "UNITS"},
        {"scale": Decimal(1)},
        {"currency": "EUR"},
        {"basis": "IFRS · borrower"},
    ],
)
def test_s5_foreign_unit_currency_scale_or_basis_fails_closed(updates):
    module = change(
        fixture(),
        table="T4.10",
        row="T4.10.revenue",
        field="model-basis:" + BASES[0],
        **updates,
    )
    with pytest.raises(ValueError):
        cp1_chart_series(module)


def test_s5_period_that_does_not_match_the_quarter_dates_fails_closed():
    module = change(
        fixture(),
        table="T4.10",
        row="T4.10.adjusted_ebitda",
        field="model-basis:" + BASES[2],
        period="FY25: 2025-01-01 to 2025-12-31",
    )
    with pytest.raises(ValueError):
        cp1_chart_series(module)


def test_s5_missing_metric_row_fails_closed_not_zero_filled():
    module = fixture()
    module = module.model_copy(
        update={"facts": tuple(f for f in module.facts if f.row_id != "T4.10.revenue")}
    )
    with pytest.raises(ValueError):
        cp1_chart_series(module)


def test_s5_with_fewer_than_four_quarters_has_a_reason_and_no_points():
    module = fixture()
    module = module.model_copy(
        update={
            "facts": tuple(
                f for f in module.facts if f.row_id not in {"T4.14.q2-2025", "T4.18.q2-2025"}
            )
        }
    )
    figure = s5(module)
    assert figure.points == () and figure.reason


def test_s5_fy_alias_period_is_never_a_fifth_category():
    module = fixture()
    added = []
    for f in module.facts:
        if f.row_id in {"T4.14.q4-2025", "T4.18.q4-2025"}:
            updates = {
                "fact_id": f.fact_id.replace("q4-2025", "fy-2025"),
                "row_id": f.row_id.replace("q4-2025", "fy-2025"),
                "period": "fy-2025",
            }
            if f.field == "period_id":
                updates["text"] = "fy-2025"
            if f.field == "period_type":
                updates["text"] = "FY"
            if f.field == "start_date":
                updates["text"] = "2025-01-01"
            if f.field == "fiscal_quarter":
                updates.update(text=None, status="not_applicable", limitation="FY")
            added.append(f.model_copy(update=updates))
    module = module.model_copy(update={"facts": (*module.facts, *added)})
    figure = s5(module)
    assert {p.category for p in figure.points} == {f"Q{n} 2025" for n in range(1, 5)}
    assert len(figure.points) == 8


@pytest.mark.parametrize("status", ["unrun", "blocked", "stale", "candidate", "not_in_pathway"])
def test_s5_is_absent_for_an_unsettled_cp1(status):
    assert cp1_chart_series(fixture().model_copy(update={"status": status})) == ()
