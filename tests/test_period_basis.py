"""PeriodBasis: one reading of the context's period and currency for the owners (Phase 8 Task 1).

Synthetic CP-1 T4.14 facts, no pack. The default is today's 2025 literals.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import date
from pathlib import Path
from typing import Any

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
    fy, q4 = _calendar()[:7], _calendar()[7:]
    with pytest.raises(PeriodRefused, match="no single period for fy-2026"):
        period_basis(_context("fy-2026"), q4)
    with pytest.raises(PeriodRefused, match="no single period for fy-2026"):
        period_basis(
            _context("fy-2026"),
            q4 + _row("r3", "FY2", "FY", "2026", None, "2026-01-01", "2026-12-31") + fy,
        )
    with pytest.raises(PeriodRefused, match="no single period for q4-2026"):
        period_basis(_context("fy-2026"), fy)
    shifted = [*fy, *_row("r2", "Q4", "QUARTER", "2026", "4", "2026-09-01", "2026-11-30")]
    with pytest.raises(PeriodRefused, match="not at the fiscal year end"):
        period_basis(_context("fy-2026"), shifted)


@pytest.mark.parametrize("row_id", ["r1", "r2"])
@pytest.mark.parametrize("how", ["absent", "not_known"])
def test_matched_row_without_known_currency_refused(row_id: str, how: str) -> None:
    facts = []
    for fact in _calendar():
        if fact.row_id == row_id and fact.field == "currency":
            if how == "absent":
                continue
            fact = fact.model_copy(
                update={"status": "missing", "text": None, "limitation": "not stated"}
            )
        facts.append(fact)
    with pytest.raises(PeriodRefused, match="has no known currency"):
        period_basis(_context("fy-2026"), facts)


def test_matched_row_with_other_currency_refused() -> None:
    facts = [
        f.model_copy(update={"text": "EUR"}) if f.row_id == "r1" and f.field == "currency" else f
        for f in _calendar()
    ]
    with pytest.raises(PeriodRefused, match="reporting_currency USD, but CP-1 reports"):
        period_basis(_context("fy-2026"), facts)


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


_CASE = Path(__file__).resolve().parents[1] / "cases" / "periods-currency-owner"
# The oracle pins CP-2E's own basis in the same block; it is not a PeriodBasis field (P8-P18).
_NOT_PERIOD_BASIS = {"cp2e_periods"}


def _load(name: str) -> Any:
    return json.loads((_CASE / name).read_text(encoding="utf-8"))


def _oracle_facts(rows: list[dict[str, Any]]) -> list[Fact]:
    """The pinned T4.14 rows as CP-1 facts, each from its cell's text and status."""
    facts = []
    for number, row in enumerate(rows):
        for name, cell in row.items():
            known = cell["status"] == "known"
            facts.append(
                Fact(
                    fact_id=f"t414-{number}-{name}",
                    label=f"{row['period_id']['text']} {name}",
                    table_id="T4.14",
                    row_id=f"row{number}",
                    field=name,
                    text=cell["text"],
                    status=cell["status"],
                    limitation=None if known else f"{cell['status']} in the pinned row",
                )
            )
    return facts


def _plain(value: object) -> object:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, tuple):
        return list(value)
    return value


@pytest.mark.parametrize(("run", "currency"), [("R1", "USD"), ("R2", "EUR")])
def test_period_basis_equals_oracle_block(run: str, currency: str) -> None:
    pinned = _load("t414.json")["contexts"][run]
    key = _load("expected.json")["period_basis"][currency]
    settings = _load("submissions.json")["contexts"][run]["run"]
    context = _context(settings["current_period"], settings["reporting_currency"])
    basis = period_basis(context, _oracle_facts(pinned["rows"]))
    wanted = {name: value for name, value in key.items() if name not in _NOT_PERIOD_BASIS}
    assert wanted
    for name, value in wanted.items():
        assert _plain(getattr(basis, name)) == value, name
    own = {f.name for f in dataclasses.fields(basis)}
    own |= {"year_labels", "not_reached_text", "balance_date_text"}
    assert own == set(wanted)
