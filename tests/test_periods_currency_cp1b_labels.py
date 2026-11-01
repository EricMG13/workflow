"""Phase 8 Task 6b: CP-1B row labels and fact shape take the run's money unit (B17-9, B18)."""

import pytest
from test_earnings_render import _change_fact, _module, _replace, _seed

from deploy_vii import report_view
from deploy_vii.bindings import cp1b
from deploy_vii.report_view import scale_label

USD_LABELS = (
    ("T1B.1", "revenue", "Revenue (US$ m)"),
    ("T1B.1", "ebitda", "Reported EBITDA (US$ m)"),
    ("T1B.1", "adjusted_ebitda", "Adjusted EBITDA (US$ m)"),
    ("T1B.1", "ebitda_margin", "EBITDA margin (%; change pp)"),
    ("T1B.1", "cfo_reported", "Reported CFO (US$ m)"),
    ("T1B.1", "capex", "Signed capex (US$ m)"),
    ("T1B.1", "fcf", "Levered FCF (US$ m)"),
    ("T1B.2", "cash_closing", "Closing cash (US$ m)"),
    ("T1B.2", "total_debt", "Total debt (US$ m)"),
    ("T1B.2", "net_debt", "Net debt (US$ m)"),
)
LAYOUT_ERROR = "CP1B layout has invalid ordered rows or labels"


def _in_currency(view, currency, *, labels=None):
    """The seeded module with every money fact in ``currency`` and rows labelled for ``labels``."""
    unit = scale_label("MILLIONS", labels or currency)
    module = _module(view)
    facts = tuple(
        f.model_copy(update={"currency": currency}) if f.unit == "MILLIONS" else f
        for f in module.facts
    )
    tables = tuple(
        t.model_copy(
            update={
                "rows": tuple(
                    r.model_copy(update={"label": r.label.replace("US$ m", unit)}) for r in t.rows
                )
            }
        )
        for t in module.tables
    )
    return _replace(view, module.model_copy(update={"facts": facts, "tables": tables}))


def test_default_layouts_equal_todays_usd_labels():
    layouts = cp1b.cp1b_layouts()
    assert layouts == cp1b._CP1B_LAYOUTS
    rows = {(l.table_id, rid): label for l in layouts for rid, label in l.rows}
    for table, row, label in USD_LABELS:
        assert rows[(table, row)] == label


def test_layouts_format_the_unit_into_nine_money_labels():
    rows = [label for l in cp1b.cp1b_layouts("EUR m") for _, label in l.rows]
    assert sum("(EUR m)" in label for label in rows) == 9
    assert not any("US$" in label for label in rows)


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_usd_module_validates_unchanged(case):
    report_view._validate_cp1b_layout(_module(_seed(case)))


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_eur_facts_with_eur_labels_validate(case):
    report_view._validate_cp1b_layout(_module(_in_currency(_seed(case), "EUR")))


def test_eur_labels_over_usd_facts_refuse():
    view = _in_currency(_seed(), "USD", labels="EUR")
    with pytest.raises(ValueError, match=LAYOUT_ERROR):
        report_view._validate_cp1b_layout(_module(view))


def test_usd_labels_over_eur_facts_refuse():
    view = _in_currency(_seed(), "EUR", labels="USD")
    with pytest.raises(ValueError, match=LAYOUT_ERROR):
        report_view._validate_cp1b_layout(_module(view))


@pytest.mark.parametrize(
    "fact_id",
    [
        "cp1b:T1B.1:revenue:prior",
        "cp1b:T1B.1:revenue:delta",
        "cp1b:T1B.2:net_debt:current",
        "cp1b:T1B.2:total_debt:prior",
        "cp1b:T1B.2:cash_closing:delta",
    ],
)
def test_a_money_fact_in_another_currency_refuses(fact_id):
    view = _change_fact(_in_currency(_seed(), "EUR"), fact_id, currency="USD")
    with pytest.raises(ValueError, match="incompatible native dimensions"):
        report_view._validate_cp1b_layout(_module(view))


def test_revenue_prior_eur_current_usd_refuses():
    view = _change_fact(_seed(), "cp1b:T1B.1:revenue:prior", currency="EUR")
    with pytest.raises(ValueError, match="incompatible native dimensions"):
        report_view._validate_cp1b_layout(_module(view))


def test_gap_money_rows_take_the_revenue_current_currency():
    view = _in_currency(_seed("gap"), "EUR")
    gaps = [f for f in _module(view).facts if f.unit == "MILLIONS" and f.status != "known"]
    assert gaps
    assert {f.currency for f in gaps} == {"EUR"}
    report_view._validate_cp1b_layout(_module(view))


def test_gap_money_fact_without_currency_has_no_fallback():
    view = _change_fact(
        _in_currency(_seed("gap"), "EUR"), "cp1b:T1B.1:revenue:prior", currency=None
    )
    with pytest.raises(ValueError, match="incompatible native dimensions"):
        report_view._validate_cp1b_layout(_module(view))


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_revenue_current_without_currency_refuses(case):
    view = _change_fact(_seed(case), "cp1b:T1B.1:revenue:current", currency=None)
    with pytest.raises(ValueError, match="reporting currency"):
        report_view._validate_cp1b_layout(_module(view))
