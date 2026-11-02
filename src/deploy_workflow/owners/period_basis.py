"""One reading of the run context's period and currency for the owners (Phase 8 Task 1).

``period_basis`` turns ``run.current_period`` (an ``fy-YYYY`` or ``q4-YYYY`` base) and
``run.reporting_currency`` into every period and currency string the owners print, dated from the
CP-1 T4.14 period register. ``currency_basis`` reads the currency alone, for any base kind. With no
context the answer is ``DEFAULT_BASIS`` (the 2025 literals the owners carried before).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date

from deploy_vii.contracts import Fact
from deploy_vii.model.dates import fiscal_year_number
from deploy_workflow.context import RunContext
from deploy_workflow.context_periods import resolve

_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_BASE = re.compile(r"(fy|q4)-(\d{4})")
_PERIOD_FIELDS = ("start_date", "end_date")


class PeriodRefused(ValueError):
    """The context or the CP-1 register gives no usable period or currency; names the field."""


@dataclass(frozen=True)
class CurrencyBasis:
    currency: str
    money_unit: str


def _currency(code: str) -> CurrencyBasis:
    return CurrencyBasis(code, "US$ m" if code == "USD" else f"{code} m")


DEFAULT_CURRENCY = _currency("USD")


def _long_date(day: date, with_year: bool) -> str:
    text = f"{_MONTHS[day.month - 1]} {day.day}"
    return f"{text}, {day.year}" if with_year else text


@dataclass(frozen=True)
class PeriodBasis:
    currency: str
    money_unit: str
    base_year: int
    years: tuple[int, int, int]
    ltm_start: date
    ltm_end: date
    q4_start: date
    ltm_tag: str
    ltm_column: str
    ltm_period: str
    t45_period: str
    t46_period: str
    schedule_period: str
    bs_period: str
    bs_column: str
    bridge_basis_line: str

    @property
    def year_labels(self) -> tuple[str, str, str]:
        a, b, c = self.years
        return (f"FY{a}", f"FY{b}", f"FY{c}")

    @property
    def not_reached_text(self) -> str:
        return f"Not reached by {self.year_labels[-1]}"

    @property
    def balance_date_text(self) -> str:
        end = self.ltm_end
        return f"{end.day} {_MONTHS[end.month - 1]} {end.year}"


def _basis(
    currency: CurrencyBasis, year: int, start: date, end: date, q4_start: date, q4_id: str
) -> PeriodBasis:
    tag = f"LTM Q4 {year % 100:02d}"
    window = f"{start} to {end}"
    if start.year == end.year:
        span = f"{_long_date(start, False)}-{_long_date(end, True)}"
    else:
        span = f"{_long_date(start, True)}-{_long_date(end, True)}"
    return PeriodBasis(
        currency=currency.currency,
        money_unit=currency.money_unit,
        base_year=year,
        years=(year + 1, year + 2, year + 3),
        ltm_start=start,
        ltm_end=end,
        q4_start=q4_start,
        ltm_tag=tag,
        ltm_column=f"{tag} ({window})",
        ltm_period=f"{tag}: {window}",
        t45_period=f"{tag} · {window}",
        t46_period=f"{q4_id} · {q4_start} to {end}",
        schedule_period=q4_id,
        bs_period=f"Q4 {year}: {end}",
        bs_column=f"Q4 {end}",
        bridge_basis_line=f"Basis: FY{year} ({span})",
    )


DEFAULT_BASIS = _basis(
    DEFAULT_CURRENCY, 2025, date(2025, 1, 1), date(2025, 12, 31), date(2025, 10, 1), "q4-2025"
)


def _period_register(facts: Iterable[Fact]) -> dict[str, dict[str, Fact]]:
    """The CP-1 T4.14 rows by `period_id`, as `cpl10._period_register` reads them: a repeated
    field of one row, a row without a known `period_id` and two rows sharing one `period_id` all
    refuse."""
    rows: dict[str, dict[str, Fact]] = {}
    for fact in facts:
        if fact.table_id != "T4.14":
            continue
        row = rows.setdefault(fact.row_id, {})
        if fact.field in row:
            raise PeriodRefused("CP-1 T4.14 register is unusable: ambiguous_coordinate")
        row[fact.field] = fact
    register: dict[str, dict[str, Fact]] = {}
    for row in rows.values():
        identity = row.get("period_id")
        if identity is None or identity.status != "known" or not identity.text:
            raise PeriodRefused("CP-1 T4.14 register is unusable: incomplete_register")
        if identity.text in register:
            raise PeriodRefused("CP-1 T4.14 register is unusable: ambiguous_coordinate")
        register[identity.text] = row
    return register


def _check_currency(
    context: RunContext, register: Mapping[str, Mapping[str, Fact]]
) -> CurrencyBasis:
    wanted = context.run.reporting_currency
    reported = set()
    for row in register.values():
        fact = row.get("currency")
        if fact is not None and fact.status == "known" and fact.text:
            reported.add(fact.text)
    if not reported:
        raise PeriodRefused(f"run.reporting_currency {wanted}, but CP-1 T4.14 reports no currency")
    if reported != {wanted}:
        raise PeriodRefused(
            f"run.reporting_currency {wanted}, but CP-1 reports {', '.join(sorted(reported))}"
        )
    return _currency(wanted)


def _row_basis(wanted: str, year: str, period_id: str, row: Mapping[str, Fact]) -> None:
    """A matched period row states the run's currency and `MILLIONS` itself, and its fiscal year
    reads (as vii reads it) as the context year; otherwise refuse."""
    fact = row.get("currency")
    if fact is None or fact.status != "known" or not fact.text:
        raise PeriodRefused(
            f"run.reporting_currency {wanted}, but CP-1 T4.14 period {period_id} "
            "has no known currency"
        )
    if fact.text != wanted:
        raise PeriodRefused(f"run.reporting_currency {wanted}, but CP-1 reports {fact.text}")
    _check_unit(period_id, row)
    spelled = row["fiscal_year"].text or ""
    if fiscal_year_number(spelled) != int(year):
        raise PeriodRefused(
            f"CP-1 T4.14 period {period_id} fiscal_year {spelled} reads as "
            f"{fiscal_year_number(spelled)}, not {year}"
        )


def _check_unit(period_id: str, row: Mapping[str, Fact]) -> None:
    fact = row.get("unit")
    if fact is None or fact.status != "known" or fact.text != "MILLIONS":
        raise PeriodRefused(f"CP-1 T4.14 period {period_id} unit is not MILLIONS")


def _check_window(start: date, end: date, q4_start: date) -> None:
    """The Q4 row (ending with the year) starts strictly inside the fiscal year, so it is neither
    the year nor before it; the year is 52 or 53 weeks (364 to 371 days)."""
    days = (end - start).days + 1
    if not start < q4_start:
        raise PeriodRefused(f"CP-1 T4.14 Q4 starts {q4_start}, not inside the fiscal year {start}")
    if not 364 <= days <= 371:
        raise PeriodRefused(f"CP-1 T4.14 fiscal year {start} to {end} covers {days} days")


def currency_basis(context: RunContext | None, cp1_facts: Iterable[Fact]) -> CurrencyBasis:
    """The run's currency, checked against CP-1's T4.14 `currency`; any base kind, blank included."""
    if context is None:
        return DEFAULT_CURRENCY
    register = _period_register(cp1_facts)
    currency = _check_currency(context, register)
    for period_id, row in register.items():
        _check_unit(period_id, row)
    return currency


def _row_dates(period_id: str, row: Mapping[str, Fact]) -> tuple[date, date]:
    values = []
    for field in _PERIOD_FIELDS:
        fact = row.get(field)
        try:
            if fact is None or fact.status != "known" or fact.text is None:
                raise ValueError(field)
            values.append(date.fromisoformat(fact.text))
        except ValueError as error:
            raise PeriodRefused(f"CP-1 T4.14 period {period_id} has no valid {field}") from error
    start, end = values
    if start > end:
        raise PeriodRefused(f"CP-1 T4.14 period {period_id} starts after it ends")
    return start, end


def _one(register: Mapping[str, Mapping[str, Fact]], period: str) -> str:
    key = resolve(period, register)
    if key is None:
        raise PeriodRefused(f"CP-1 T4.14 has no single period for {period}")
    return key


def period_basis(context: RunContext | None, cp1_facts: Iterable[Fact]) -> PeriodBasis:
    """The period and currency strings for an `fy-YYYY` or `q4-YYYY` base; anything else refuses."""
    if context is None:
        return DEFAULT_BASIS
    base = _BASE.fullmatch(context.run.current_period)
    if base is None:
        raise PeriodRefused(
            f"run.current_period {context.run.current_period}: forecast years need an fy or q4 base"
        )
    year = base[2]
    register = _period_register(cp1_facts)
    currency = _check_currency(context, register)
    fy_id, q4_id = _one(register, f"fy-{year}"), _one(register, f"q4-{year}")
    for period_id in (fy_id, q4_id):
        _row_basis(currency.currency, year, period_id, register[period_id])
    start, end = _row_dates(fy_id, register[fy_id])
    q4_start, q4_end = _row_dates(q4_id, register[q4_id])
    if q4_end != end:
        raise PeriodRefused(f"CP-1 T4.14 Q4 {year} ends {q4_end}, not at the fiscal year end {end}")
    _check_window(start, end, q4_start)
    return _basis(currency, int(year), start, end, q4_start, q4_id)


def run_basis(context: RunContext | None, cp1_facts: Iterable[Fact]) -> PeriodBasis:
    """The basis an owner reads for its run (ruling P8-R3): `period_basis`, except for a context
    with no base period.

    Documented fail-open: a blank `run.current_period` (allowed off earnings runs; every frozen
    pins-context case has one) with `run.reporting_currency` USD returns `DEFAULT_BASIS`, so the
    frozen Phase 6 behaviour stays. The guard: the owner then binds the 2025 labels, and a CP-1
    of another year offers no such fact, so selection refuses ("CP-1 offers 0 facts") rather
    than labelling 2026 figures as 2025. A blank base with any other currency refuses here."""
    if context is None:
        return DEFAULT_BASIS
    if not context.run.current_period:
        if context.run.reporting_currency != DEFAULT_CURRENCY.currency:
            raise PeriodRefused(
                f"run.current_period is blank and run.reporting_currency is "
                f"{context.run.reporting_currency}: a non-USD run needs an fy or q4 base"
            )
        return DEFAULT_BASIS
    return period_basis(context, cp1_facts)
