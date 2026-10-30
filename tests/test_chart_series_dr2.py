"""DR.2 (CP-4C recovery by class): the series record ``cp4c_chart_series`` selects.

Expectations come from ``cases/charts/dr2-expected.json`` (``chart_series.DR.2.<case>``), read
here and never derived from the code under test. The producer selects settled facts and
spells nothing: every point value is the ``Fact.amount`` of its fact id.
"""

from decimal import Decimal
from pathlib import Path
from typing import Any

import chart_dr_support as support
import pytest

from deploy_vii.contracts import Fact
from deploy_workflow.restructuring_series import cp4c_chart_series

ORACLE = support.oracle("dr2")
RECORDS = ORACLE["chart_series"]["DR.2"]


def _dr2(case: str) -> tuple[Any, dict[str, Fact]]:
    module = support.composer_module(case)
    figures = cp4c_chart_series(module)
    assert figures[0].fig_id == "DR.2"
    return figures[0], {fact.fact_id: fact for fact in module.facts}


@pytest.mark.parametrize("case", support.CASES)
def test_record_fields_equal_the_oracle(case: str) -> None:
    figure, _ = _dr2(case)
    want = RECORDS[case]
    assert figure.fig_id == want["fig_id"] == "DR.2"
    assert figure.title == want["title"]
    assert figure.kind == want["kind"]
    assert figure.unit_class == want["unit_class"] == "percent"
    assert figure.unit == want["unit"] == "PERCENT"
    assert list(figure.series) == want["series"]
    assert figure.reason == want["reason"]


@pytest.mark.parametrize("case", support.CASES)
def test_points_equal_the_oracle_in_order(case: str) -> None:
    figure, _ = _dr2(case)
    want = RECORDS[case]["points"]
    assert [
        (p.series, p.category, p.fact_id, list(p.companion_fact_ids), p.hatched)
        for p in figure.points
    ] == [
        (w["series"], w["category"], w["fact_id"], w["companion_fact_ids"], w["hatched"])
        for w in want
    ]
    assert len(figure.points) == RECORDS[case]["point_count"]
    assert all(p.role == "value" for p in figure.points)


@pytest.mark.parametrize("case", support.CASES)
def test_each_point_is_its_settled_fact_never_a_recomputed_or_zero_filled_value(
    case: str,
) -> None:
    figure, facts = _dr2(case)
    for point, want in zip(figure.points, RECORDS[case]["points"], strict=True):
        fact = facts[point.fact_id]
        if want["state"] == "known":
            assert fact.status == "known"
            assert fact.amount == Decimal(want["value"])
        else:
            assert want["state"] == "gap" and want["value"] is None
            assert fact.status == "missing" and fact.amount is None
            assert fact.limitation == want["reason"]
    gaps = [w for w in RECORDS[case]["points"] if w["state"] == "gap"]
    assert len(gaps) == RECORDS[case]["gap_count"]


@pytest.mark.parametrize("case", support.CASES)
def test_the_equity_recovery_drops_out_and_is_listed(case: str) -> None:
    figure, facts = _dr2(case)
    want = [d["fact_id"] for d in RECORDS[case]["dropped_equity_marks"]]
    assert list(figure.dropped_fact_ids) == want
    assert all(facts[f].status == "not_applicable" for f in want)
    assert not set(want) & {p.fact_id for p in figure.points}


def test_a_known_zero_recovery_is_a_plotted_point_not_a_gap() -> None:
    figure, facts = _dr2("fixture_ev_zero")
    zero = [p for p in figure.points if facts[p.fact_id].amount == 0]
    assert len(zero) == 6 and all(facts[p.fact_id].status == "known" for p in zero)


def test_no_plottable_point_is_the_na_kind_with_the_module_reason() -> None:
    figure, facts = _dr2("fixture_debt_missing")
    assert figure.kind == "na"
    assert figure.reason == (
        "Not calculable: total debt is missing in CP-1 for LTM Q4 25: 2025-01-01 to 2025-12-31"
    )
    assert all(facts[p.fact_id].status == "missing" for p in figure.points)


def test_a_missing_multiple_leaves_the_bare_scenario_name_as_the_series() -> None:
    figure, _ = _dr2("gap")
    assert list(figure.series) == ["Base 4.00x", "Downside 3.00x", "Stress"]
    assert {p.series for p in figure.points} == set(figure.series)


def test_hatching_follows_the_basis_of_the_multiple() -> None:
    module = support.composer_module("positive")
    sourced = module.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"value_class": "source"})
                if f.fact_id == "T4E.3.v02.multiple"
                else f
                for f in module.facts
            )
        }
    )
    figure = cp4c_chart_series(sourced)[0]
    by_series = {p.series: p.hatched for p in figure.points}
    assert by_series == {"Base 4.00x": True, "Downside 3.00x": False, "Stress 2.00x": True}


def test_a_missing_multiple_hatches_by_default() -> None:
    figure, _ = _dr2("gap")
    assert all(p.hatched for p in figure.points if p.series == "Stress")


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_the_settled_owner_head_gives_the_same_record(case: str, tmp_path: Path) -> None:
    figure = cp4c_chart_series(support.settled_module(tmp_path, case))[0]
    want = RECORDS[case]
    assert (figure.kind, list(figure.series), figure.reason) == (
        want["kind"],
        want["series"],
        want["reason"],
    )
    assert [p.fact_id for p in figure.points] == [w["fact_id"] for w in want["points"]]


def test_a_module_without_the_recovery_tables_supplies_no_figure() -> None:
    module = support.composer_module("positive")
    bare = module.model_copy(update={"facts": (), "tables": ()})
    assert cp4c_chart_series(bare) == ()


def test_a_recovery_row_with_no_scenario_fact_fails_closed() -> None:
    module = support.composer_module("positive")
    broken = module.model_copy(
        update={"facts": tuple(f for f in module.facts if f.fact_id != "T4E.3.v02.scenario")}
    )
    with pytest.raises(ValueError, match="T4E.3.v02.scenario"):
        cp4c_chart_series(broken)
