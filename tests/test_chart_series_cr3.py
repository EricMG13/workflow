"""CR.3 (CP-3C refinancing need by maturity) producer: ``cp3c_chart_series`` against the oracle.

Every expected value is read from ``cases/charts/cr3-expected.json`` (chart_series.CR.3). The pack
cases are the real CP-3C core's heads; the composer fixtures carry no tables, so their T3D.1 rows
are laid out from the composer's own maturity rows (``chart_wiring_c.fixture_register``).
"""

from decimal import Decimal

import chart_wiring_c as w
import pytest

from deploy_vii.contracts import ModuleView
from deploy_workflow.liquidity_series import cp3c_chart_series


def _record(module: ModuleView):
    (record,) = cp3c_chart_series(module)
    return record


@pytest.mark.parametrize("case", w.CR3_PACK_CASES)
def test_pack_cases_equal_the_oracle(case: str) -> None:
    record = _record(w.module_of(w.cp3c_view(case), "CP-3C"))
    expected = w.CR3_FIG[case]
    assert w.record_meta(record) == w.oracle_meta(expected)
    assert w.record_points(record) == w.oracle_points(expected)


@pytest.mark.parametrize("case", w.CR3_FIXTURES)
def test_fixtures_equal_the_oracle(case: str) -> None:
    record = _record(w.fixture_register(case).module)
    expected = w.CR3_FIG[case]
    meta = w.oracle_meta(expected)
    if meta["reason"] is not None:  # the fixture reason is generic: the wiring never compares it
        assert record.reason
        meta["reason"] = record.reason
    assert w.record_meta(record) == meta
    assert w.record_points(record) == w.oracle_points(expected)


def test_negative_resources_stay_negative() -> None:
    for case, fact_ids in (
        ("fixture_two_facilities", ["T3D.1.r02.c7"]),
        ("fixture_burn", ["T3D.1.r01.c7"]),
    ):
        record = _record(w.fixture_register(case).module)
        negatives = [p.fact_id for p in record.points if p.value is not None and p.value < 0]
        assert negatives == fact_ids == w.CR3["adversarial_cases"][0]["negative_point_fact_ids"][case]
        assert all(p.shown.startswith("(") for p in record.points if p.fact_id in fact_ids)


def test_categories_are_facility_rows_in_row_order() -> None:
    record = _record(w.fixture_register("fixture_two_facilities").module)
    assert [p.category for p in record.points[::2]] == ["notes", "term-loan"]
    assert [p.series for p in record.points] == [
        "Principal payable at maturity",
        "Resources at maturity",
    ] * 2


def test_the_pack_category_is_the_row_label_and_the_sublabel_is_the_maturity_date() -> None:
    record = _record(w.module_of(w.cp3c_view("positive"), "CP-3C"))
    assert {p.category for p in record.points} == {"Northbridge Term Loan (term-loan)"}
    assert {p.sublabel for p in record.points} == {w.CR3_FIG["positive"]["points"][0]["axis_sublabel"]}


def test_a_gap_resource_keeps_the_principal_mark_known() -> None:
    record = _record(w.module_of(w.cp3c_view("gap_minimum_cash"), "CP-3C"))
    principal, resources = record.points
    assert principal.value == Decimal(50) and principal.shown == "50"
    assert resources.value is None and resources.shown == "∅ G#"
    assert record.kind == "grouped"


def test_the_all_gap_chart_is_the_na_frame() -> None:
    record = _record(w.fixture_register("fixture_amortisation_missing").module)
    assert record.kind == "na" and record.reason
    assert [p.value for p in record.points] == [None, None]


def test_an_absent_register_fails_closed() -> None:
    module = w.module_of(w.cp3c_view("positive"), "CP-3C")
    facts = tuple(f for f in module.facts if f.fact_id != "T3D.1.r01.c7")
    with pytest.raises(ValueError, match="T3D.1.r01.c7"):
        cp3c_chart_series(module.model_copy(update={"facts": facts}))
