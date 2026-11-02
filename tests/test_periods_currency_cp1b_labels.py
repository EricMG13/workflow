"""Phase 8 Task 6b: CP-1B row labels and fact shape take the run's money unit (B17-9, B18)."""

import json
from pathlib import Path

import pytest
from test_earnings_render import _change_fact, _module, _replace, _seed

from deploy_vii import report_view
from deploy_vii.bindings import cp1b

ROOT = Path(__file__).parents[1]
_EXPECTED = json.loads((ROOT / "cases/periods-currency-owner/expected.json").read_text())
_RENDER = json.loads((ROOT / "cases/earnings/render-expected.json").read_text())
# Answer keys, read at run time; the code under test never derives them.
EUR_LABELS = {
    row["row_id"]: row["label"]
    for rows in _EXPECTED["module_oracles"]["CP-1B@EUR"]["row_labels"].values()
    for row in rows
}
EUR_UNIT = _EXPECTED["runs"]["R3"]["modules"]["CP-1B"]["money_unit"]
USD_LABELS = {
    row["row_id"]: row["label"]
    for table in _RENDER["layout"]["tables"]
    if table["table_id"] in {"T1B.1", "T1B.2"}
    for row in table["rows"]
}
LAYOUT_ERROR = "CP1B layout has invalid ordered rows or labels"
NON_ISO = ["", " ", "usd", "eur", "US$", "EURO", "\u20ac", "EUR\n", "{unit}", "123"]


def _in_currency(view, currency, labels):
    """The seeded module with every money fact in ``currency`` and rows labelled by ``labels``."""
    module = _module(view)
    facts = tuple(
        f.model_copy(update={"currency": currency}) if f.unit == "MILLIONS" else f
        for f in module.facts
    )
    tables = tuple(
        t.model_copy(
            update={
                "rows": tuple(
                    r.model_copy(update={"label": labels.get(r.row_id, r.label)}) for r in t.rows
                )
            }
        )
        for t in module.tables
    )
    return _replace(view, module.model_copy(update={"facts": facts, "tables": tables}))


def test_default_layouts_equal_the_usd_key():
    rows = {rid: label for l in cp1b.cp1b_layouts() for rid, label in l.rows}
    assert {k: v for k, v in rows.items() if k in USD_LABELS} == USD_LABELS
    assert cp1b.cp1b_layouts() == cp1b._CP1B_LAYOUTS


def test_layouts_in_the_oracle_unit_equal_the_oracle_labels():
    rows = {rid: label for l in cp1b.cp1b_layouts(EUR_UNIT) for rid, label in l.rows}
    assert {k: v for k, v in rows.items() if k in EUR_LABELS} == EUR_LABELS


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_usd_module_validates_unchanged(case):
    report_view._validate_cp1b_layout(_module(_seed(case)))


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_eur_facts_with_oracle_labels_validate(case):
    report_view._validate_cp1b_layout(_module(_in_currency(_seed(case), "EUR", EUR_LABELS)))


def test_eur_labels_over_usd_facts_refuse():
    view = _in_currency(_seed(), "USD", EUR_LABELS)
    with pytest.raises(ValueError, match=LAYOUT_ERROR):
        report_view._validate_cp1b_layout(_module(view))


def test_usd_labels_over_eur_facts_refuse():
    view = _in_currency(_seed(), "EUR", USD_LABELS)
    with pytest.raises(ValueError, match=LAYOUT_ERROR):
        report_view._validate_cp1b_layout(_module(view))


@pytest.mark.parametrize("bad", NON_ISO)
def test_a_non_iso_money_currency_refuses(bad):
    view = _in_currency(_seed(), bad, EUR_LABELS)
    with pytest.raises(ValueError, match="reporting currency"):
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
    view = _change_fact(_in_currency(_seed(), "EUR", EUR_LABELS), fact_id, currency="USD")
    with pytest.raises(ValueError, match="incompatible native dimensions"):
        report_view._validate_cp1b_layout(_module(view))


def test_revenue_prior_eur_current_usd_refuses():
    view = _change_fact(_seed(), "cp1b:T1B.1:revenue:prior", currency="EUR")
    with pytest.raises(ValueError, match="incompatible native dimensions"):
        report_view._validate_cp1b_layout(_module(view))


def test_gap_money_rows_take_the_revenue_current_currency():
    view = _in_currency(_seed("gap"), "EUR", EUR_LABELS)
    gaps = [f for f in _module(view).facts if f.unit == "MILLIONS" and f.status != "known"]
    assert gaps
    assert {f.currency for f in gaps} == {"EUR"}
    report_view._validate_cp1b_layout(_module(view))


def test_gap_money_fact_without_currency_has_no_fallback():
    view = _change_fact(
        _in_currency(_seed("gap"), "EUR", EUR_LABELS), "cp1b:T1B.1:revenue:prior", currency=None
    )
    with pytest.raises(ValueError, match="incompatible native dimensions"):
        report_view._validate_cp1b_layout(_module(view))


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_revenue_current_without_currency_refuses(case):
    view = _change_fact(_seed(case), "cp1b:T1B.1:revenue:current", currency=None)
    with pytest.raises(ValueError, match="reporting currency"):
        report_view._validate_cp1b_layout(_module(view))
