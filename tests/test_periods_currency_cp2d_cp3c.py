"""CP-2D and CP-3C take their period and currency strings from `PeriodBasis` (Phase 8 Task 4).

The answer key is the frozen oracle `cases/periods-currency-owner/`: `expected.json#period_basis`
(USD and EUR, 2026), loaded at run time. The default basis keeps today's 2025 USD strings
byte-for-byte.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import test_connect_cp2d as tc2d
import test_connect_cp3c as tc3
import test_method_cp2d as tm2d
import test_method_cp3c as tm3
import test_period_basis as tpb

from deploy_vii.contracts import Fact, Module
from deploy_workflow.owners import cp2d, cp3c
from deploy_workflow.owners.period_basis import (
    DEFAULT_BASIS,
    PeriodBasis,
    PeriodRefused,
    period_basis,
    run_basis,
)

_CASE = Path(__file__).resolve().parents[1] / "cases" / "periods-currency-owner"


def _load(name: str) -> Any:
    return json.loads((_CASE / name).read_text(encoding="utf-8"))


KEY = _load("expected.json")["period_basis"]
RUNS = {"USD": "R1", "EUR": "R2"}


def _basis(currency: str) -> PeriodBasis:
    run = RUNS[currency]
    settings = _load("submissions.json")["contexts"][run]["run"]
    context = tpb._context(settings["current_period"], settings["reporting_currency"])
    rows = _load("t414.json")["contexts"][run]["rows"]
    return period_basis(context, tpb._oracle_facts(rows))


@pytest.fixture(params=["USD", "EUR"])
def currency(request: pytest.FixtureRequest) -> str:
    return str(request.param)


# --- (a) the default basis is today's binding ---------------------------------------------------


def test_default_basis_bindings_are_the_frozen_ones() -> None:
    assert cp2d.fact_bindings(DEFAULT_BASIS) == cp2d.FACT_BINDINGS
    assert cp3c.fact_bindings(DEFAULT_BASIS) == cp3c.FACT_BINDINGS
    assert cp2d.SCHEDULE_PERIOD == "q4-2025" == cp3c.SCHEDULE_PERIOD
    assert list(cp2d.FACT_BINDINGS) == list(tm2d.MANIFEST["fact_bindings"])[:25]
    assert len(cp2d.FACT_BINDINGS) == 25
    assert cp2d.FACT_BINDINGS["cash_bs"] == cp2d.FactBinding(
        "T4.6", "q4-2025 · 2025-10-01 to 2025-12-31", "Cash and cash equivalents · q4-2025"
    )
    assert cp2d.FACT_BINDINGS["cfo"] == cp2d.FactBinding(
        "T4.5", "LTM Q4 25 · 2025-01-01 to 2025-12-31", "Operating cash flow · LTM Q4 25"
    )
    assert cp3c.FACT_BINDINGS["adjusted_ebitda"] == cp2d.FactBinding(
        "T4.10",
        "LTM Q4 25: 2025-01-01 to 2025-12-31",
        "LTM Q4 25 (2025-01-01 to 2025-12-31) · adjusted_ebitda",
    )


# --- (b) the 2026 binding, from the oracle ------------------------------------------------------


def test_bindings_follow_the_oracle_periods(currency: str) -> None:
    key = KEY[currency]
    got = cp2d.fact_bindings(_basis(currency))
    assert got["cash_bs"] == cp2d.FactBinding(
        "T4.6", key["t46_period"], f"Cash and cash equivalents · {key['schedule_period']}"
    )
    assert got["cash_closing"] == cp2d.FactBinding(
        "T4.10", key["ltm_period"], f"{key['ltm_column']} · cash_closing"
    )
    assert got["cfo"] == cp2d.FactBinding(
        "T4.5", key["t45_period"], f"Operating cash flow · {key['ltm_tag']}"
    )
    assert list(got) == list(cp2d.FACT_BINDINGS)
    assert key["ltm_column"] == "LTM Q4 26 (2026-01-01 to 2026-12-31)"
    assert got["cash_closing"].label == "LTM Q4 26 (2026-01-01 to 2026-12-31) · cash_closing"


def test_cp3c_bindings_share_cp2ds_rule(currency: str) -> None:
    basis = _basis(currency)
    both = cp2d.fact_bindings(basis)
    for name, binding in cp3c.fact_bindings(basis).items():
        assert binding == cp2d.bind410(name, basis), name
        if name in both:
            assert binding == both[name], name
    assert list(cp3c.fact_bindings(basis)) == list(cp3c.CP1_METRICS)


# --- (e) the schedule period is the T4.14 row's own id (M5) --------------------------------------


def _cp1_with_periods(facts: list[Fact]) -> Module:
    run = tc2d.PACK.run
    return Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id="CP-1",
        facts=tuple(facts),
        limitations=("CP-1 synthetic limitation",),
    )


def test_bind46_takes_the_q4_row_id_and_the_end_date_is_found() -> None:
    facts = tpb._calendar(2026, q4_id="Q4-FY26", fy_id="FYX")
    basis = period_basis(tpb._context("fy-2026"), facts)
    assert basis.schedule_period == "Q4-FY26"
    assert cp2d.bind46("Cash and cash equivalents", basis) == cp2d.FactBinding(
        "T4.6", "Q4-FY26 · 2026-10-01 to 2026-12-31", "Cash and cash equivalents · Q4-FY26"
    )
    module = _cp1_with_periods(facts)
    assert cp2d._balance_date(module, basis.schedule_period) == (date(2026, 12, 31), ("FYX",))
    assert cp3c._balance_date(module, basis.schedule_period) == (date(2026, 12, 31), ("FYX",))
    with pytest.raises(ValueError, match="CP-1 states no end date for q4-2025"):
        cp2d._balance_date(module)


# --- (c) the foreign-currency reason names the run currency -------------------------------------


def _facility(currency_code: str) -> cp2d.Facility:
    return cp2d.Facility(
        facility_id="f1",
        name="Term loan",
        currency=currency_code,
        principal=Decimal(50),
        maturity_date=date(2030, 1, 1),
        commitment=Decimal(50),
        drawn_amount=Decimal(50),
        annual_amortisation=Decimal(0),
        period="q4-2025",
    )


def test_fx_gap_names_the_run_currency() -> None:
    usd_run = cp2d._currency_gap(_facility("EUR"))
    assert usd_run is not None
    assert usd_run.reason == (
        "Not calculable: facility f1 is in EUR, not USD; no FX conversion is applied"
    )
    eur_run = cp2d._currency_gap(_facility("USD"), "EUR")
    assert eur_run is not None
    assert eur_run.reason == (
        "Not calculable: facility f1 is in USD, not EUR; no FX conversion is applied"
    )
    assert cp2d._currency_gap(_facility("EUR"), "EUR") is None
    assert cp2d._facility_cause(
        _facility("USD"), date(2025, 12, 31), date(2027, 12, 31), "EUR"
    ) == ("in EUR, and one is not")


def test_cp3c_fx_cause_names_the_run_currency() -> None:
    inputs = tm3._inputs("positive")
    terms = inputs.cp1.facilities[0]
    row = inputs.cp2d.wall[0]
    months = cp3c._whole_months(inputs.cp2d.horizon)
    assert months is not None
    gap = cp3c._facility(
        row,
        replace(terms, currency="USD"),
        balance_date=inputs.balance_date,
        horizon=months,
        currency="EUR",
    ).principal
    assert isinstance(gap, cp3c.Gap)
    assert gap.cause == "the total needs every facility in EUR, and one is not"
    assert gap.reason == (
        f"Not calculable: facility {row.facility_id} is in USD, not EUR; "
        "no FX conversion is applied"
    )


# --- (f) a EUR run prints no US$ ----------------------------------------------------------------


def _eur_2d(basis: PeriodBasis) -> cp2d.Cp2dInputs:
    inputs = tm2d._inputs("positive")
    facilities = tuple(
        replace(f, currency=basis.currency) for f in inputs.operands.facilities or ()
    )
    operands = replace(inputs.operands, facilities=facilities)
    return replace(inputs, operands=operands, basis=basis)


def test_cp2d_prints_the_run_money_unit(currency: str) -> None:
    basis = _basis(currency)
    result = cp2d.compute(_eur_2d(basis))
    text = repr(result)
    unit = KEY[currency]["money_unit"]
    assert unit in text
    assert (unit != "US$ m") == ("US$" not in text)
    assert {t.table_id for t in result.tables} >= {"T2E.1", "T2E.2", "T2E.4", "T2E.5"}
    assert all(
        f"({unit})" in t.columns[0] or t.table_id in ("T2E.3", "T2E.4") for t in result.tables
    )
    claims = " ".join(c.text for c in result.claims)
    assert f"{unit}" in claims


_MAT_EUR = (
    "The cash outflow from debt maturing inside the horizon is not calculated: [T2E.3.r07] needs "
    "every facility in EUR, and one is not; no FX conversion is applied."
)
_GAP_EUR = (
    "The funding gap is not calculated: [T2E.5.r07] needs every facility in EUR, and one is not."
)


def test_cp2d_foreign_facility_claim_and_limitation_name_the_run_currency() -> None:
    basis = _basis("EUR")
    inputs = _eur_2d(basis)
    facilities = tuple(replace(f, currency="USD") for f in inputs.operands.facilities or ())
    result = cp2d.compute(replace(inputs, operands=replace(inputs.operands, facilities=facilities)))
    text = repr(result)
    assert "is in USD, not EUR; no FX conversion is applied" in text
    texts = [c.text for c in result.claims]
    assert _MAT_EUR in texts
    assert _GAP_EUR in texts
    assert "not USD" not in text and "US$" not in text


def test_cp2d_facts_carry_the_run_currency(currency: str) -> None:
    basis = _basis(currency)
    result = cp2d.compute(_eur_2d(basis))
    selection = cp2d.select_cp1(tc2d.cp1_module(tm2d._operands("positive")))
    composer = cp2d._Composer(selection, result)
    for table in result.tables:
        composer.table(table)
    money = [f for f in composer.facts if f.unit == "MILLIONS"]
    assert money
    assert {f.currency for f in money} == {currency}
    assert all("US$" not in f.label for f in composer.facts) or currency == "USD"


def test_cp2d_refuses_a_fact_in_another_currency() -> None:
    basis = _basis("EUR")
    fact = tc2d._cp1_fact("cash_bs", None)
    with pytest.raises(ValueError, match="CP-2D: cash_bs is not in EUR millions"):
        cp2d._usd_millions("cash_bs", fact, basis)
    with pytest.raises(ValueError, match="CP-2D: cash_bs is not in US dollars millions"):
        cp2d._usd_millions("cash_bs", fact.model_copy(update={"currency": "EUR"}))


def _in_euro(inputs: cp3c.Cp3cInputs) -> cp3c.Cp3cInputs:
    euro = tc3._every_millions_fact(inputs, lambda f: replace(f, currency="EUR"))
    cp1 = replace(
        euro.cp1,
        cash_closing=replace(euro.cp1.cash_closing, currency="EUR"),
        facilities=tuple(replace(t, currency="EUR") for t in euro.cp1.facilities),
    )
    return replace(euro, cp1=cp1, currency="EUR", basis=_basis("EUR"))


def test_cp3c_prints_the_run_money_unit(currency: str) -> None:
    inputs = tm3._inputs("positive")
    if currency == "EUR":
        inputs = _in_euro(inputs)
    else:
        inputs = replace(inputs, basis=_basis("USD"))
    result = cp3c.compute(inputs)
    text = repr(result)
    unit = KEY[currency]["money_unit"]
    assert f"Principal ({unit})" in text
    assert f"Refinancing need ({unit})" in text
    assert (unit != "US$ m") == ("US$" not in text)


def test_cp3c_refuses_a_currency_that_is_not_the_runs(tmp_path: Path) -> None:
    store, _, attempt = tc3.seed(tmp_path)
    upstream = tc3.upstream_of(store, attempt)
    assert cp3c.select(upstream).currency == "USD"
    eur = replace(DEFAULT_BASIS, currency="EUR", money_unit="EUR m")
    with pytest.raises(PeriodRefused, match="run.reporting_currency EUR, but CP-1 reports USD"):
        cp3c.select(upstream, eur)


def test_no_context_keeps_the_default_basis() -> None:
    assert cp2d.run_basis(tc2d.PACK, tc2d.cp1_module(tm2d._operands("positive"))) is DEFAULT_BASIS


def test_cp3c_currency_mismatch_is_an_issue_line(tmp_path: Path) -> None:
    store, _, attempt = tc3.seed(tmp_path)
    upstream = tc3.upstream_of(store, attempt)
    submission = tc3.submission_of(store, attempt)
    eur = replace(DEFAULT_BASIS, currency="EUR", money_unit="EUR m")
    issues = cp3c.validate_refinancing(submission=submission, upstream=upstream, basis=eur)
    assert issues == ("Period basis refused: run.reporting_currency EUR, but CP-1 reports USD",)
    assert cp3c.validate_refinancing(submission=submission, upstream=upstream) == ()


def test_cp2d_difference_limitations_are_spelled_in_the_run_unit() -> None:
    inputs = _eur_2d(_basis("EUR"))
    ops = inputs.operands
    assert ops.closing_cash is not None and ops.closing_cash.amount is not None
    assert ops.financing is not None and ops.financing.amount is not None
    closing = replace(ops.closing_cash, amount=ops.closing_cash.amount + Decimal("1.5"))
    financing = replace(ops.financing, amount=ops.financing.amount + Decimal("2.5"))
    result = cp2d.compute(
        replace(inputs, operands=replace(ops, closing_cash=closing, financing=financing))
    )
    uses = [t for t in result.own_limitations if t.startswith("Sources and uses differ")]
    lines = [t for t in result.own_limitations if t.startswith("Financing lines differ")]
    assert uses and uses[0].endswith(" EUR m.")
    assert lines and "by (2.5) EUR m;" in lines[0]


# --- the P8-R3 guard: a 2026 CP-1 under a blank-USD context is refused, not mislabelled ----------


def _shifted_one_year(text: str | None) -> str | None:
    if text is None:
        return None
    import re

    text = re.sub(r"(?<!\d)(20\d\d)(?!\d)", lambda m: str(int(m.group(1)) + 1), text)
    return re.sub(r"Q([1-4]) 25\b", r"Q\1 26", text)


def _cp1_2026() -> Module:
    base = tc2d.cp1_module(tm2d._operands("positive"))
    facts = tuple(
        f.model_copy(
            update={
                "period": _shifted_one_year(f.period),
                "label": _shifted_one_year(f.label),
                "text": _shifted_one_year(f.text),
            }
        )
        for f in base.facts
    )
    return base.model_copy(update={"facts": facts})


def test_blank_usd_base_with_a_2026_cp1_is_refused_not_mislabelled() -> None:
    module = _cp1_2026()
    blank = run_basis(tpb._context(""), module.facts)
    assert blank is DEFAULT_BASIS
    with pytest.raises(ValueError, match="CP-1 offers 0 facts"):
        cp2d.select_cp1(module, blank)
    selected = cp2d.select_cp1(module, _basis("USD"))  # the same CP-1 reads under its own basis
    assert selected.balance_date == date.fromisoformat(KEY["USD"]["ltm_end"])
    assert {o.fact.period for o in selected.offered if o.name == "cash_bs"} == {
        KEY["USD"]["t46_period"]
    }


def test_unsourced_currency_names_the_run_money_unit() -> None:
    inputs = tc3._without_cash(tm3._inputs("positive"))
    inputs = tc3._every_millions_fact(inputs, tc3._missing)
    with pytest.raises(ValueError, match="no known EUR m fact states a currency"):
        cp3c.reporting_currency(cp1=inputs.cp1, cp2d=inputs.cp2d, unit="EUR m")
    with pytest.raises(ValueError, match="no known EUR m fact states a currency"):
        cp3c.compute(replace(inputs, basis=_basis("EUR")))
    with pytest.raises(ValueError, match="no known US[$] m fact states a currency"):
        cp3c.reporting_currency(cp1=inputs.cp1, cp2d=inputs.cp2d)
