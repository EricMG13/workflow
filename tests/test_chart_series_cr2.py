"""CR.2 (CP-2D liquidity bridge) producer: ``cp2d_chart_series`` against the frozen oracle.

Every expected value is read from ``cases/charts/cr2-expected.json`` (chart_series.CR.2). The CP-2D
heads are the real core's over the frozen literals; the forged view only withholds facts.
"""

from decimal import Decimal

import chart_wiring_c as w
import pytest

from deploy_vii.contracts import Fact, ModuleView
from deploy_workflow.liquidity_series import cp2d_chart_series

BRIDGE = ("T2E.2.r01", "T2E.3.r05", "T2E.3.r06", "T2E.3.r07", "T2E.3.r08")


def _record(module: ModuleView):
    (record,) = cp2d_chart_series(module)
    return record


@pytest.mark.parametrize("case", w.CR2_CASES)
def test_producer_equals_the_oracle(case: str) -> None:
    module = w.module_of(w.cp2d_view(case), "CP-2D")
    expected = w.CR2_FIG[case]
    record = _record(module)
    assert w.record_meta(record) == w.oracle_meta(expected)
    assert w.record_points(record) == w.oracle_points(expected)
    assert [p.role for p in record.points] == [p["role"] for p in expected["points"]]
    assert record.note == expected["note"]
    assert record.axis_label == expected["axis_label"]


@pytest.mark.parametrize("case", w.CR2_CASES)
def test_bridge_identity_holds_on_the_returned_values(case: str) -> None:
    record = _record(w.module_of(w.cp2d_view(case), "CP-2D"))
    opening, flow, amortisation, maturities, closing = (p.value for p in record.points)
    assert None not in (opening, flow, amortisation, maturities, closing)
    assert opening + flow + amortisation + maturities == closing
    assert str(closing) == w.CR2_FIG[case]["bridge_identity"]["sum"]


def test_the_long_horizon_closing_mark_is_negative() -> None:
    record = _record(w.module_of(w.cp2d_view("long_horizon"), "CP-2D"))
    assert record.points[-1].value == Decimal(-30)
    assert record.points[-1].shown == "(30)"


@pytest.mark.parametrize("case", w.CR2_CASES)
def test_each_value_is_the_settled_fact_amount(case: str) -> None:
    module = w.module_of(w.cp2d_view(case), "CP-2D")
    facts = {f.fact_id: f for f in module.facts}
    for point in _record(module).points:
        assert point.value == facts[point.fact_id].amount


def test_five_points_and_no_lease_or_capex_step() -> None:
    record = _record(w.module_of(w.cp2d_view("positive"), "CP-2D"))
    assert tuple(p.fact_id for p in record.points) == BRIDGE


def _withheld(module: ModuleView, fact_ids: tuple[str, ...]) -> ModuleView:
    """The forged view: the named bridge facts are missing with a limitation, as the lease's
    missing rule settles them."""
    facts = tuple(
        Fact(
            fact_id=f.fact_id,
            label=f.label,
            table_id=f.table_id,
            row_id=f.row_id,
            field=f.field,
            status="missing",
            unit=f.unit,
            currency=f.currency,
            scale=f.scale,
            value_class=f.value_class,
            limitation="Not calculable: forged withheld operand",
        )
        if f.fact_id in fact_ids
        else f
        for f in module.facts
    )
    return module.model_copy(update={"facts": facts})


def test_withheld_maturities_and_closing_are_gaps_never_zero() -> None:
    module = w.module_of(w.cp2d_view("long_horizon"), "CP-2D")
    record = _record(_withheld(module, ("T2E.3.r07", "T2E.3.r08")))
    by_id = {p.fact_id: p for p in record.points}
    for fact_id in ("T2E.3.r07", "T2E.3.r08"):
        assert by_id[fact_id].value is None
        assert by_id[fact_id].shown == "∅ G#"
    assert by_id["T2E.3.r05"].value == Decimal(0)
    assert record.kind == "waterfall" and record.reason is None


def test_an_all_gap_bridge_is_the_na_frame_with_a_reason() -> None:
    module = w.module_of(w.cp2d_view("positive"), "CP-2D")
    record = _record(_withheld(module, BRIDGE))
    assert record.kind == "na"
    assert record.reason and "forged withheld operand" in record.reason
    assert [p.value for p in record.points] == [None] * 5


def test_a_bridge_fact_absent_from_the_module_fails_closed() -> None:
    module = w.module_of(w.cp2d_view("positive"), "CP-2D")
    facts = tuple(f for f in module.facts if f.fact_id != "T2E.3.r07")
    with pytest.raises(ValueError, match="T2E.3.r07"):
        cp2d_chart_series(module.model_copy(update={"facts": facts}))


def test_a_module_that_is_not_cp2d_is_refused() -> None:
    module = w.module_of(w.cp2d_view("positive"), "CP-2D")
    with pytest.raises(ValueError, match="CP-2D"):
        cp2d_chart_series(module.model_copy(update={"module_id": "CP-2"}))
