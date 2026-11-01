"""PeriodBasis: one reading of the context's period and currency for the owners (Phase 8 Task 1).

Synthetic CP-1 T4.14 facts, no pack. The default is today's 2025 literals.
"""

from __future__ import annotations

from datetime import date

import pytest

from deploy_vii.contracts import Fact
from deploy_workflow.context import RunContext, RunSettings
from deploy_workflow.owners.period_basis import (
    DEFAULT_BASIS,
    DEFAULT_CURRENCY,
    PeriodRefused,
    currency_basis,
    period_basis,
)


def _row(
    row: str,
    period_id: str,
    kind: str,
    year: str,
    quarter: str | None,
    start: str,
    end: str,
    currency: str = "USD",
) -> list[Fact]:
    fields = {
        "period_id": period_id,
        "period_type": kind,
        "fiscal_year": year,
        "start_date": start,
        "end_date": end,
        "currency": currency,
    }
    facts = [
        Fact(
            fact_id=f"{row}-{name}",
            label=f"{row} {name}",
            table_id="T4.14",
            row_id=row,
            field=name,
            text=text,
        )
        for name, text in fields.items()
    ]
    facts.append(
        Fact(
            fact_id=f"{row}-fiscal_quarter",
            label=f"{row} fiscal_quarter",
            table_id="T4.14",
            row_id=row,
            field="fiscal_quarter",
            text=quarter,
            status="known" if quarter else "not_applicable",
            limitation=None if quarter else "an FY row has no quarter",
        )
    )
    return facts


def _calendar(
    year: int = 2026, currency: str = "USD", q4_id: str = "Q4", fy_id: str = "FY"
) -> list[Fact]:
    return [
        *_row("r1", fy_id, "FY", f"FY{year}", None, f"{year}-01-01", f"{year}-12-31", currency),
        *_row("r2", q4_id, "QUARTER", str(year), "4", f"{year}-10-01", f"{year}-12-31", currency),
    ]


def _context(period: str, currency: str = "USD") -> RunContext:
    run = RunSettings.model_construct(current_period=period, reporting_currency=currency)
    return RunContext.model_construct(run=run)


def test_default_basis_is_todays_literals() -> None:
    b = DEFAULT_BASIS
    assert (b.currency, b.money_unit) == ("USD", "US$ m")
    assert (b.base_year, b.years) == (2025, (2026, 2027, 2028))
    assert (b.ltm_start, b.ltm_end, b.q4_start) == (
        date(2025, 1, 1),
        date(2025, 12, 31),
        date(2025, 10, 1),
    )
    assert b.ltm_tag == "LTM Q4 25"
    assert b.ltm_column == "LTM Q4 25 (2025-01-01 to 2025-12-31)"
    assert b.ltm_period == "LTM Q4 25: 2025-01-01 to 2025-12-31"
    assert b.t45_period == "LTM Q4 25 · 2025-01-01 to 2025-12-31"
    assert b.t46_period == "q4-2025 · 2025-10-01 to 2025-12-31"
    assert b.schedule_period == "q4-2025"
    assert b.bs_period == "Q4 2025: 2025-12-31"
    assert b.bs_column == "Q4 2025-12-31"
    assert b.bridge_basis_line == "Basis: FY2025 (January 1-December 31, 2025)"
    assert b.year_labels == ("FY2026", "FY2027", "FY2028")
    assert b.not_reached_text == "Not reached by FY2028"
    assert b.balance_date_text == "31 December 2025"
    assert (DEFAULT_CURRENCY.currency, DEFAULT_CURRENCY.money_unit) == ("USD", "US$ m")


def test_none_context_gives_default() -> None:
    assert period_basis(None, []) is DEFAULT_BASIS
    assert currency_basis(None, []) == DEFAULT_CURRENCY


def test_fy2026_calendar() -> None:
    b = period_basis(_context("fy-2026"), _calendar(2026, q4_id="q4-2026", fy_id="fy-2026"))
    assert b.ltm_column == "LTM Q4 26 (2026-01-01 to 2026-12-31)"
    assert b.years == (2027, 2028, 2029)
    assert b.year_labels == ("FY2027", "FY2028", "FY2029")
    assert b.not_reached_text == "Not reached by FY2029"
    assert b.bs_period == "Q4 2026: 2026-12-31"
    assert b.balance_date_text == "31 December 2026"
    assert b.schedule_period == "q4-2026"
    assert b.bridge_basis_line == "Basis: FY2026 (January 1-December 31, 2026)"
    assert b.q4_start == date(2026, 10, 1)


def test_q4_and_fy_base_give_equal_basis() -> None:
    facts = _calendar(2026)
    assert period_basis(_context("q4-2026"), facts) == period_basis(_context("fy-2026"), facts)


def test_non_calendar_year() -> None:
    facts = [
        *_row("r1", "FY", "FY", "FY2026", None, "2025-07-01", "2026-06-30"),
        *_row("r2", "q4-2026", "QUARTER", "2026", "4", "2026-04-01", "2026-06-30"),
    ]
    b = period_basis(_context("fy-2026"), facts)
    assert b.ltm_column == "LTM Q4 26 (2025-07-01 to 2026-06-30)"
    assert b.t46_period == "q4-2026 · 2026-04-01 to 2026-06-30"
    assert b.bridge_basis_line == "Basis: FY2026 (July 1, 2025-June 30, 2026)"
    assert b.balance_date_text == "30 June 2026"


@pytest.mark.parametrize("period", ["q2-2026", "h2-2026", ""])
def test_other_base_kinds_refused(period: str) -> None:
    with pytest.raises(PeriodRefused, match=r"run\.current_period"):
        period_basis(_context(period), _calendar())


def test_missing_or_duplicate_period_rows_refused() -> None:
    fy, q4 = _calendar()[:6], _calendar()[6:]
    with pytest.raises(PeriodRefused):
        period_basis(_context("fy-2026"), q4)
    with pytest.raises(PeriodRefused):
        period_basis(
            _context("fy-2026"),
            q4 + _row("r3", "FY2", "FY", "2026", None, "2026-01-01", "2026-12-31") + fy,
        )
    with pytest.raises(PeriodRefused):
        period_basis(_context("fy-2026"), fy)
    shifted = [*fy, *_row("r2", "Q4", "QUARTER", "2026", "4", "2026-09-01", "2026-11-30")]
    with pytest.raises(PeriodRefused):
        period_basis(_context("fy-2026"), shifted)


def test_currency_mismatch_refused() -> None:
    with pytest.raises(PeriodRefused, match="reporting_currency EUR, but CP-1 reports USD"):
        period_basis(_context("fy-2026", "EUR"), _calendar())
    with pytest.raises(PeriodRefused, match="reporting_currency EUR, but CP-1 reports USD"):
        currency_basis(_context("fy-2026", "EUR"), _calendar())


def test_eur_unit_token() -> None:
    b = period_basis(_context("fy-2026", "EUR"), _calendar(currency="EUR"))
    assert (b.currency, b.money_unit) == ("EUR", "EUR m")


def test_period_id_from_matched_row() -> None:
    facts = _calendar(q4_id="Q4-FY26", fy_id="FYX")
    b = period_basis(_context("fy-2026"), facts)
    assert b.schedule_period == "Q4-FY26"
    assert b.t46_period == "Q4-FY26 · 2026-10-01 to 2026-12-31"


@pytest.mark.parametrize("period", ["q3-2026", "h2-2026", ""])
def test_currency_basis_any_base(period: str) -> None:
    got = currency_basis(_context(period, "EUR"), _calendar(currency="EUR"))
    assert (got.currency, got.money_unit) == ("EUR", "EUR m")
    with pytest.raises(PeriodRefused, match="reporting_currency EUR, but CP-1 reports USD"):
        currency_basis(_context(period, "EUR"), _calendar())


def test_register_refuses_ambiguous_rows() -> None:
    dup = _calendar() + _row("r1", "FY", "FY", "2026", None, "2026-01-01", "2026-12-31")[:1]
    with pytest.raises(PeriodRefused, match="ambiguous_coordinate"):
        period_basis(_context("fy-2026"), dup)
    same_id = _calendar() + _row("r9", "FY", "FY", "2025", None, "2025-01-01", "2025-12-31")
    with pytest.raises(PeriodRefused, match="ambiguous_coordinate"):
        period_basis(_context("fy-2026"), same_id)
    no_id = [f for f in _calendar() if f.field != "period_id" or f.row_id != "r2"]
    with pytest.raises(PeriodRefused, match="incomplete_register"):
        period_basis(_context("fy-2026"), no_id)


def test_no_currency_rows_refused() -> None:
    with pytest.raises(PeriodRefused, match="currency"):
        currency_basis(_context("q3-2026"), [])
