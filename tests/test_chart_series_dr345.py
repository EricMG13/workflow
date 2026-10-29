"""DR.3-5 (CP-4C value allocation): the three waterfall records ``cp4c_chart_series`` selects.

Expectations come from ``cases/charts/dr345-expected.json`` (``chart_series.DR.3-5.<case>``).
The waterfall builds up to the enterprise value (rulings item 6.4): classes by (rank, id), the
equity residual, then the total. The producer selects; conservation is checked here on the
settled values and nothing is recomputed.
"""

from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

import chart_dr_support as support
import pytest

from deploy_vii.contracts import Fact
from deploy_workflow.restructuring_series import cp4c_chart_series

ORACLE = support.oracle("dr345")
RECORDS = ORACLE["chart_series"]["DR.3-5"]
FIG_IDS = ["DR.3", "DR.4", "DR.5"]


def _waterfalls(case: str) -> tuple[list[Any], dict[str, Fact]]:
    module = support.composer_module(case)
    figures = cp4c_chart_series(module)
    assert [f.fig_id for f in figures] == ["DR.2", *FIG_IDS]
    return list(figures[1:]), {fact.fact_id: fact for fact in module.facts}


@pytest.mark.parametrize("case", support.CASES)
def test_record_fields_equal_the_oracle(case: str) -> None:
    figures, _ = _waterfalls(case)
    for figure, fig_id in zip(figures, FIG_IDS, strict=True):
        want = RECORDS[case][fig_id]
        assert figure.title == want["title"]
        assert figure.kind == want["kind"]
        assert (figure.unit_class, figure.unit, figure.currency) == ("amount", "MILLIONS", "USD")
        assert list(figure.series) == want["series"] == ["Value allocation"]
        assert figure.reason == want["reason"]


@pytest.mark.parametrize("case", support.CASES)
def test_steps_equal_the_oracle_in_order(case: str) -> None:
    figures, _ = _waterfalls(case)
    for figure, fig_id in zip(figures, FIG_IDS, strict=True):
        want = RECORDS[case][fig_id]["points"]
        assert [
            (p.series, p.category, p.fact_id, list(p.companion_fact_ids), p.role)
            for p in figure.points
        ] == [
            (w["series"], w["category"], w["fact_id"], w["companion_fact_ids"], w["role"])
            for w in want
        ]
        roles = [p.role for p in figure.points]
        assert roles[-2:] == ["residual", "total"] and set(roles[:-2]) == {"value"}
        assert all(p.hatched for p in figure.points) is RECORDS[case][fig_id]["hatched"]


@pytest.mark.parametrize("case", support.CASES)
def test_values_are_the_settled_facts_and_gaps_are_never_zero(case: str) -> None:
    figures, facts = _waterfalls(case)
    for figure, fig_id in zip(figures, FIG_IDS, strict=True):
        for point, want in zip(figure.points, RECORDS[case][fig_id]["points"], strict=True):
            fact = facts[point.fact_id]
            if want["state"] == "known":
                assert fact.status == "known" and fact.amount == Decimal(want["value"])
                assert fact.decimals == 2
            else:
                assert want["value"] is None and fact.status == "missing"
                assert fact.amount is None and fact.limitation == want["reason"]


def test_conservation_holds_on_the_settled_positive_values() -> None:
    figures, facts = _waterfalls("positive")
    with localcontext() as ctx:
        ctx.prec = 60
        for figure, fig_id in zip(figures, FIG_IDS, strict=True):
            assert RECORDS["positive"][fig_id]["conservation"]["holds"] is True
            values = [facts[p.fact_id].amount for p in figure.points]
            assert None not in values
            assert sum(values[:-1], Decimal(0)) == values[-1]


def test_the_partial_gap_keeps_its_known_marks_and_withholds_conservation() -> None:
    figures, facts = _waterfalls("gap")
    base, downside, stress = figures
    assert base.kind == downside.kind == "waterfall" and stress.kind == "na"
    assert RECORDS["gap"]["DR.3"]["conservation"]["holds"] is None
    known = [p.category for p in base.points if facts[p.fact_id].status == "known"]
    assert known == ["Senior secured term loan", "Enterprise value"]
    assert stress.title == "Value allocation, Stress"
    assert stress.reason == "Not calculable: the EV multiple was not assessed"


def test_a_zero_enterprise_value_is_a_known_zero_waterfall_not_n_a() -> None:
    figures, facts = _waterfalls("fixture_ev_zero")
    downside = figures[1]
    assert downside.kind == "waterfall"
    assert facts[downside.points[-1].fact_id].amount == 0
    assert all(facts[p.fact_id].status == "known" for p in downside.points)


def test_a_missing_ebitda_gives_na_frames_for_the_scenarios_it_blocks() -> None:
    figures, _ = _waterfalls("fixture_ebitda_missing")
    assert [f.kind for f in figures] == ["waterfall", "na", "na"]
    assert (
        figures[1].reason
        == figures[2].reason
        == "Not calculable: downside FY2026 EBITDA is missing in CP-2G (synthetic upstream fixture)"
    )


def test_missing_debt_leaves_the_enterprise_value_as_the_one_known_mark() -> None:
    figures, facts = _waterfalls("fixture_debt_missing")
    for figure in figures:
        assert figure.kind == "waterfall"
        known = [p for p in figure.points if facts[p.fact_id].status == "known"]
        assert [p.role for p in known] == ["total"]


def test_the_checks_travel_as_companions_of_the_enterprise_value_not_as_steps() -> None:
    figures, _ = _waterfalls("positive")
    total = figures[0].points[-1]
    assert [c for c in total.companion_fact_ids if c.startswith("T4E.9.")] == [
        "T4E.9.v01.total_claims",
        "T4E.9.v01.creditor_distributions",
        "T4E.9.v01.balance",
    ]
    assert not any(p.fact_id.endswith((".balance", ".total_claims")) for p in figures[0].points)


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_the_settled_owner_head_gives_the_same_records(case: str, tmp_path: Path) -> None:
    figures = cp4c_chart_series(support.settled_module(tmp_path, case))
    assert [f.fig_id for f in figures] == ["DR.2", *FIG_IDS]
    for figure, fig_id in zip(figures[1:], FIG_IDS, strict=True):
        want = RECORDS[case][fig_id]
        assert (figure.kind, figure.title, figure.reason) == (
            want["kind"],
            want["title"],
            want["reason"],
        )
        assert [p.fact_id for p in figure.points] == [w["fact_id"] for w in want["points"]]


def test_a_class_without_a_rank_fails_closed() -> None:
    module = support.composer_module("positive")
    broken = module.model_copy(
        update={"facts": tuple(f for f in module.facts if f.fact_id != "T4E.2.c01.rank")}
    )
    with pytest.raises(ValueError, match="T4E.2.c01.rank"):
        cp4c_chart_series(broken)
