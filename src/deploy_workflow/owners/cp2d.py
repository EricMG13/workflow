"""CP-2D (Liquidity) owner core: the Stage 1 calculation (docs/CP2D-OWNER-LEASE.md, Method).

Pure functions over typed inputs. Python owns every figure: sources and uses (T2E.1), the
liquidity position (T2E.2), the run-rate cash runway (T2E.3), the maturity wall (T2E.4) and
the funding gap (T2E.5), plus the analyst-judgment and gaps ledgers (T2E.6, T2E.7), the own
limitations and the claim texts the lease fixes. All arithmetic is Decimal; a missing operand
stays ``None`` and is never read as zero. No I/O, store, host, session or render call:
connections, the read view and the G1 seams are later stages.
"""

import re
from calendar import monthrange
from dataclasses import dataclass, replace
from datetime import date
from decimal import ROUND_HALF_UP, Context, Decimal, localcontext
from typing import Literal

from deploy_vii.contracts import Contract, Identifier, Text
from deploy_vii.display import UnitClass, format_date, format_value
from deploy_vii.model._cells import CONTEXT as CP1_CONTEXT

MODULE_ID = "CP-2D"
HORIZON_BOUNDS = (1, 60)
CURRENCY = "USD"

Section = Literal["liquidity_runway", "maturity_wall", "funding_gap"]
SECTIONS: tuple[Section, ...] = ("liquidity_runway", "maturity_wall", "funding_gap")
Category = Literal[
    "Documentary Fact", "Management Language", "Analyst Interpretation", "Insufficient Information"
]
RunwayState = Literal["months", "not_reached", "missing"]
CellState = Literal["known", "gap"]

_ZERO = Decimal(0)
_ONE_DP = Decimal("0.1")
# Wide enough that sums, products and the run-rate divisions of realistic figures are exact or
# rounded far below display precision; the lease's only quantisation is the runway's 1 dp.
_CONTEXT = Context(prec=60)

# --- submission (judgment and references only; lease "Submission schema") --------------------


class MinimumCash(Contract):
    amount: Decimal
    rationale: Text
    basis_refs: tuple[Identifier, ...]


class MinimumCashAbsence(Contract):
    reason: Text
    follow_up: Text


class Assessment(Contract):
    section: Section
    category: Category
    text: Text
    credit_implication: Text
    basis_refs: tuple[Identifier, ...]
    limitation: str | None


class LiquidityBridgeSubmission(Contract):
    horizon_months: int
    minimum_cash: MinimumCash | None
    minimum_cash_absence: MinimumCashAbsence | None
    assessments: tuple[Assessment, ...]


# --- inputs -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Facility:
    """One CP-1 T4.18 facility row at the balance date (QUARTER period over its FY alias)."""

    facility_id: str
    name: str
    currency: str
    principal: Decimal | None
    maturity_date: date | None
    commitment: Decimal | None
    drawn_amount: Decimal | None
    annual_amortisation: Decimal | None


@dataclass(frozen=True)
class Operands:
    """The CP-1 head facts the Method reads (manifest.fact_bindings names); None is missing.

    T4.5 flows are the twelve months to the balance date in the CP-1 fact's own sign; T4.6
    balances and T4.10 metrics are at the balance date, US$ m. ``liquidity_to_debt`` is a
    decimal fraction (0.4 is 40%).
    """

    # T4.5 statement history, LTM
    opening_cash: Decimal | None
    cfo: Decimal | None
    investing: Decimal | None
    net_debt_issuance: Decimal | None
    equity_issuance: Decimal | None
    equity_repurchases: Decimal | None
    dividends_paid: Decimal | None
    other_investing_financing: Decimal | None
    financing: Decimal | None
    fx_effect: Decimal | None
    closing_cash: Decimal | None
    # T4.6 balance sheet, Q4
    cash_bs: Decimal | None
    restricted_cash: Decimal | None
    rcf_commitment: Decimal | None
    rcf_drawn: Decimal | None
    total_debt_bs: Decimal | None
    # T4.10 settled metrics, cross-checked against the recomputation (never a second source)
    cash_closing: Decimal | None
    total_debt: Decimal | None
    undrawn_rcf: Decimal | None
    liquidity: Decimal | None
    liquidity_to_debt: Decimal | None
    # T4.18 facility schedule
    facilities: tuple[Facility, ...]


@dataclass(frozen=True)
class Cp2dInputs:
    operands: Operands
    balance_date: date
    submission: LiquidityBridgeSubmission
    # The CP-1 fact ids the read view offers (Stage 2 fills it from the view).
    offered_refs: frozenset[str]


# --- the bridge (derived values) --------------------------------------------------------------


@dataclass(frozen=True)
class WallRow:
    facility: Facility
    months_to_maturity: int
    inside_horizon: bool
    share_of_total_debt: Decimal | None
    cumulative_share: Decimal | None


@dataclass(frozen=True)
class Bridge:
    horizon_months: int
    minimum_cash: Decimal | None
    balance_date: date
    horizon_end: date
    run_rate_net_cash_flow_annual: Decimal | None
    run_rate_net_cash_flow_monthly: Decimal | None
    run_rate_net_cash_flow_horizon: Decimal | None
    maturity_inside_horizon: bool | None
    maturities_in_horizon: Decimal | None
    amortisation_in_horizon: Decimal | None
    cash_at_horizon_end_before_refinancing: Decimal | None
    undrawn_revolver: Decimal | None
    undrawn_term_commitment: Decimal | None
    available_liquidity: Decimal | None
    liquidity_to_total_debt: Decimal | None
    resources_at_horizon_end: Decimal | None
    cash_only_headroom: Decimal | None
    headroom: Decimal | None
    funding_gap: Decimal | None
    runway_state: RunwayState
    runway_reason: str | None
    months_to_minimum_cash: Decimal | None
    sources_and_uses_closing_cash_calculated: Decimal | None
    sources_and_uses_difference: Decimal | None
    wall: tuple[WallRow, ...]


def _total(*values: Decimal | None) -> Decimal | None:
    """Sum, or None when any operand is missing (a missing operand never defaults to zero)."""
    if any(v is None for v in values):
        return None
    return sum((v for v in values if v is not None), _ZERO)


def _diff(a: Decimal | None, b: Decimal | None) -> Decimal | None:
    """a - b, or None when either is missing."""
    return None if a is None or b is None else a - b


def add_months(start: date, months: int) -> date:
    """Calendar month arithmetic, the day clamped to the end of the target month."""
    year, index = divmod(start.month - 1 + months, 12)
    year += start.year
    month = index + 1
    return date(year, month, min(start.day, monthrange(year, month)[1]))


def months_between(start: date, end: date) -> int:
    """Whole calendar months; one less when the later day-of-month is earlier."""
    months = (end.year - start.year) * 12 + (end.month - start.month)
    return months - 1 if end.day < start.day else months


def _facilities_known(facilities: tuple[Facility, ...]) -> bool:
    """Every term of every facility is known; an empty schedule is missing, not zero debt."""
    return bool(facilities) and all(
        f.principal is not None
        and f.maturity_date is not None
        and f.commitment is not None
        and f.drawn_amount is not None
        and f.annual_amortisation is not None
        for f in facilities
    )


def _check_currency(facilities: tuple[Facility, ...]) -> None:
    foreign = [f.facility_id for f in facilities if f.currency != CURRENCY]
    if foreign:
        # The lease sets such rows and every total to missing "with a limitation", but fixes no
        # wording and no frozen pack exercises it: fail closed rather than invent the text.
        raise ValueError(f"CP-2D has no fixed treatment wording for non-USD facilities: {foreign}")


def _schedule(
    facilities: tuple[Facility, ...], horizon_months: int, horizon_end: date
) -> tuple[Decimal, Decimal]:
    """(maturities, amortisation) inside the horizon; every facility field is known here."""
    maturities = _ZERO
    amortisation = _ZERO
    for f in facilities:
        assert f.principal is not None and f.maturity_date is not None
        assert f.annual_amortisation is not None
        if f.maturity_date <= horizon_end:
            maturities += f.principal
        else:
            amortisation += min(f.annual_amortisation * horizon_months / 12, f.principal)
    return maturities, amortisation


def _wall(
    facilities: tuple[Facility, ...],
    balance_date: date,
    horizon_end: date,
    total_debt: Decimal | None,
) -> tuple[WallRow, ...]:
    """Rows in maturity order with running share; the shares are missing without a positive
    total debt, and there are no rows while a facility term is missing."""
    if not _facilities_known(facilities):
        return ()
    ordered = sorted(facilities, key=lambda f: (f.maturity_date or date.max, f.facility_id))
    rows: list[WallRow] = []
    cumulative = _ZERO
    for f in ordered:
        assert f.principal is not None and f.maturity_date is not None
        share = None if total_debt is None or total_debt == 0 else f.principal / total_debt
        if share is not None:
            cumulative += share
        rows.append(
            WallRow(
                facility=f,
                months_to_maturity=months_between(balance_date, f.maturity_date),
                inside_horizon=f.maturity_date <= horizon_end,
                share_of_total_debt=share,
                cumulative_share=None if share is None else cumulative,
            )
        )
    return tuple(rows)


# Runway gap reasons fixed by lease Method 3 (expected.json for the first).
RUNWAY_NO_MINIMUM = "Not calculable: minimum cash not assessed"
RUNWAY_NO_REVOLVER = "Not calculable: revolver undisclosed"


def _runway(
    *,
    annual: Decimal | None,
    cash: Decimal | None,
    undrawn: Decimal | None,
    minimum_cash: Decimal | None,
) -> tuple[RunwayState, str | None, Decimal | None]:
    """Months until cash reaches minimum cash from run-rate cash flow alone (Method 3)."""
    if minimum_cash is None:
        return "missing", RUNWAY_NO_MINIMUM, None
    if annual is None or cash is None:
        return "missing", None, None
    if undrawn is None:
        # A revolver is never negative, so cash alone clearing the minimum is enough.
        if annual >= 0 and cash - minimum_cash >= 0:
            return "not_reached", None, None
        return "missing", RUNWAY_NO_REVOLVER, None
    start = cash + undrawn - minimum_cash
    if annual >= 0:
        if start >= 0:
            return "not_reached", None, None
        return "months", None, _ZERO.quantize(_ONE_DP)
    months = max(_ZERO, start) * 12 / -annual
    return "months", None, months.quantize(_ONE_DP, rounding=ROUND_HALF_UP)


def compose_bridge(
    *,
    operands: Operands,
    horizon_months: int,
    minimum_cash: Decimal | None,
    balance_date: date,
) -> Bridge:
    """Method items 1-6, pure Decimal. Missing operands make their dependants missing."""
    low, high = HORIZON_BOUNDS
    if not low <= horizon_months <= high:
        raise ValueError("horizon_months must be between 1 and 60")
    if minimum_cash is not None and minimum_cash < 0:
        raise ValueError("minimum_cash.amount must not be negative")
    _check_currency(operands.facilities)
    o = operands
    horizon_end = add_months(balance_date, horizon_months)
    with localcontext(_CONTEXT):
        annual = _diff(_total(o.cfo, o.investing, o.financing), o.net_debt_issuance)
        monthly = None if annual is None else annual / 12
        over_horizon = None if annual is None else annual * horizon_months / 12
        known_schedule = _facilities_known(o.facilities)
        maturities, amortisation = (
            _schedule(o.facilities, horizon_months, horizon_end) if known_schedule else (None, None)
        )
        end_cash = _diff(_total(o.cash_bs, over_horizon), _total(amortisation, maturities))
        undrawn = _diff(o.rcf_commitment, o.rcf_drawn)
        term_undrawn = (
            sum(
                (
                    f.commitment - f.drawn_amount
                    for f in o.facilities
                    if f.commitment is not None and f.drawn_amount is not None
                ),
                _ZERO,
            )
            if known_schedule
            else None
        )
        available = _total(o.cash_bs, undrawn)
        to_debt = (
            None
            if available is None or o.total_debt_bs is None or o.total_debt_bs == 0
            # CP-1 divides with the model context (38 digits, half-even); the cross-check
            # against T4.10 liquidity_to_debt is exact only on the same division.
            else CP1_CONTEXT.divide(available, o.total_debt_bs)
        )
        resources = _total(end_cash, undrawn)
        cash_only = _diff(end_cash, minimum_cash)
        headroom = _diff(resources, minimum_cash)
        gap = None if headroom is None else max(_ZERO, -headroom)
        state, reason, months = _runway(
            annual=annual, cash=o.cash_bs, undrawn=undrawn, minimum_cash=minimum_cash
        )
        calculated_close = _total(
            o.opening_cash,
            o.cfo,
            o.investing,
            o.net_debt_issuance,
            o.equity_issuance,
            o.equity_repurchases,
            o.dividends_paid,
            o.other_investing_financing,
            o.fx_effect,
        )
        difference = _diff(calculated_close, o.closing_cash)
        wall = _wall(o.facilities, balance_date, horizon_end, o.total_debt_bs)
    return Bridge(
        horizon_months=horizon_months,
        minimum_cash=minimum_cash,
        balance_date=balance_date,
        horizon_end=horizon_end,
        run_rate_net_cash_flow_annual=annual,
        run_rate_net_cash_flow_monthly=monthly,
        run_rate_net_cash_flow_horizon=over_horizon,
        maturity_inside_horizon=(
            any(
                f.maturity_date is not None and f.maturity_date <= horizon_end for f in o.facilities
            )
            if known_schedule
            else None
        ),
        maturities_in_horizon=maturities,
        amortisation_in_horizon=amortisation,
        cash_at_horizon_end_before_refinancing=end_cash,
        undrawn_revolver=undrawn,
        undrawn_term_commitment=term_undrawn,
        available_liquidity=available,
        liquidity_to_total_debt=to_debt,
        resources_at_horizon_end=resources,
        cash_only_headroom=cash_only,
        headroom=headroom,
        funding_gap=gap,
        runway_state=state,
        runway_reason=reason,
        months_to_minimum_cash=months,
        sources_and_uses_closing_cash_calculated=calculated_close,
        sources_and_uses_difference=difference,
        wall=wall,
    )


def bridge_of(inputs: Cp2dInputs) -> Bridge:
    minimum = inputs.submission.minimum_cash
    return compose_bridge(
        operands=inputs.operands,
        horizon_months=inputs.submission.horizon_months,
        minimum_cash=None if minimum is None else minimum.amount,
        balance_date=inputs.balance_date,
    )


def check_cp1_totals(*, operands: Operands, bridge: Bridge) -> tuple[str, ...]:
    """The recomputation must equal CP-1's settled T4.10 metrics (a cross-check, Method 2)."""
    pairs: tuple[tuple[str, Decimal | None, Decimal | None], ...] = (
        ("cash_closing", operands.cash_closing, operands.cash_bs),
        ("total_debt", operands.total_debt, operands.total_debt_bs),
        ("undrawn_rcf", operands.undrawn_rcf, bridge.undrawn_revolver),
        ("liquidity", operands.liquidity, bridge.available_liquidity),
        ("liquidity_to_debt", operands.liquidity_to_debt, bridge.liquidity_to_total_debt),
    )
    return tuple(
        f"CP-1 {name} {settled} differs from the recomputed {mine}"
        for name, settled, mine in pairs
        if not (settled is None and mine is None)
        and (settled is None or mine is None or settled != mine)
    )


# --- spelling ---------------------------------------------------------------------------------


def amount_text(value: Decimal) -> str:
    """US$ m prose spelling: 0 dp half-up, negatives in brackets (display.py)."""
    return format_value(value, "amount", "known") + " US$ m"


def _months_text(value: Decimal | int) -> str:
    return f"{value} months"


# --- own limitations and ledgers --------------------------------------------------------------

RUN_RATE_BASIS = (
    "Run-rate basis: the twelve months to {date} are held flat over the horizon; no forecast, "
    "growth, seasonality or new borrowing is assumed."
)
MINIMUM_CASH_ASSUMED = "Minimum cash is an analyst assumption, not a source figure."
MINIMUM_CASH_NOT_ASSESSED = (
    "Minimum cash was not assessed, so headroom and funding gap are not calculated."
)
RUNWAY_BASIS = (
    "Months until cash reaches minimum cash use run-rate cash flow alone and exclude maturities "
    "and amortisation; the maturity wall and funding gap tables show their effect."
)
INTEREST_AFTER_MATURITY = (
    "Cash interest stays in the run-rate cash flow after the maturity date; interest on a repaid "
    "facility is not removed, which is conservative."
)
SOURCES_AND_USES_DIFFER = "Sources and uses differ from reported closing cash by {amount}."
FUNDING_GAP_ON_CASH_ALONE = (
    "The funding gap is not calculated because the revolver is undisclosed; the cash-only "
    "headroom over minimum cash is shown as a lower bound."
)

_REVOLVER = ("rcf_commitment", "rcf_drawn")
# Operands whose absence has pinned wording: the revolver (fixture) and none other. The T4.10
# cross-check facts follow the revolver (they are CP-1's own figures of the same quantities).
_UNPINNED_WHEN_MISSING = (
    "opening_cash",
    "cfo",
    "investing",
    "net_debt_issuance",
    "equity_issuance",
    "equity_repurchases",
    "dividends_paid",
    "other_investing_financing",
    "financing",
    "fx_effect",
    "closing_cash",
    "cash_bs",
    "restricted_cash",
    "total_debt_bs",
    "cash_closing",
    "total_debt",
)


def _missing(operands: Operands, names: tuple[str, ...]) -> list[str]:
    missing = [n for n in names if getattr(operands, n) is None]
    if not operands.facilities:
        missing.append("T4.18 facilities")
    elif not _facilities_known(operands.facilities):
        missing.append("T4.18 facility terms")
    return missing


def _limitations(*, operands: Operands, bridge: Bridge) -> tuple[tuple[str, str, str], ...]:
    """(T2E.7 label, kind, text) for each own limitation, in the lease's order."""
    unpinned = _missing(operands, _UNPINNED_WHEN_MISSING)
    if unpinned:
        raise ValueError(f"CP-2D has no fixed limitation wording for missing operands: {unpinned}")
    out = [
        (
            "Run-rate basis",
            "Limitation",
            RUN_RATE_BASIS.format(date=format_date(bridge.balance_date)),
        )
    ]
    if bridge.minimum_cash is None:
        out.append(("Minimum cash", "Gap", MINIMUM_CASH_NOT_ASSESSED))
    else:
        out.append(("Minimum cash", "Limitation", MINIMUM_CASH_ASSUMED))
    out.append(("Runway basis", "Limitation", RUNWAY_BASIS))
    if bridge.maturity_inside_horizon:
        out.append(("Interest after maturity", "Limitation", INTEREST_AFTER_MATURITY))
    difference = bridge.sources_and_uses_difference
    if difference is not None and difference != 0:
        # Label as the oracle builder pins it (cases/cp2d-owner/builder/build.py limitations()).
        out.append(
            (
                "Sources and uses difference",
                "Limitation",
                SOURCES_AND_USES_DIFFER.format(amount=amount_text(difference)),
            )
        )
    if bridge.undrawn_revolver is None:
        out.append(("Funding gap on cash alone", "Limitation", FUNDING_GAP_ON_CASH_ALONE))
    return tuple(out)


def own_limitations(*, operands: Operands, bridge: Bridge) -> tuple[str, ...]:
    return tuple(text for _, _, text in _limitations(operands=operands, bridge=bridge))


# --- result types -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Cell:
    """One table fact. A gap cell's spelling needs the report's G number (Stage 2)."""

    fact_id: str
    state: CellState
    shown: str | None
    amount: Decimal | None = None
    unit: str | None = None
    value_class: str | None = None
    cp1_operand: str | None = None
    cp1_unit: str | None = None
    reason: str | None = None

    def spell(self, *, gap_id: str | None = None) -> str:
        if self.state == "gap":
            return format_value(None, "amount", "gap", gap_id=gap_id)
        assert self.shown is not None
        return self.shown


@dataclass(frozen=True)
class Row:
    label: str
    cells: tuple[Cell, ...]


@dataclass(frozen=True)
class Table:
    table_id: str
    title: str
    row_header: str
    columns: tuple[str, ...]
    rows: tuple[Row, ...]


@dataclass(frozen=True)
class Ledger:
    """T2E.6 / T2E.7: two-text rows (the lease and oracle fix titles and rows, not columns)."""

    table_id: str
    title: str
    rows: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ClaimText:
    claim_id: str
    template: str
    text: str
    references: tuple[str, ...]
    cites_from: tuple[str, ...]


@dataclass(frozen=True)
class Cp2dResult:
    bridge: Bridge
    tables: tuple[Table, ...]
    judgments: Ledger
    gaps_ledger: Ledger
    own_limitations: tuple[str, ...]
    claims: tuple[ClaimText, ...]
    status: Literal["restricted"]


# --- cells ------------------------------------------------------------------------------------

_UNIT_CLASS: dict[str, UnitClass] = {"MILLIONS": "amount", "PERCENT": "percent"}
# CP-1 T4.5 / T4.6 facts carry unit "currency"; copies normalise it to MILLIONS (lease).
_CP1_CURRENCY = "currency"


def _num(
    value: Decimal,
    unit: str,
    value_class: str,
    cp1_operand: str | None = None,
    cp1_unit: str | None = None,
) -> Cell:
    shown = format_value(value, _UNIT_CLASS[unit], "known")
    return Cell("", "known", shown, value, unit, value_class, cp1_operand, cp1_unit)


def _money(value: Decimal | None, value_class: str = "calculated") -> Cell:
    assert value is not None
    return _num(value, "MILLIONS", value_class)


def _copy(value: Decimal | None, value_class: str, operand: str) -> Cell:
    """A copied CP-1 T4.5/T4.6 fact: own value class, unit currency normalised to MILLIONS."""
    assert value is not None
    return _num(value, "MILLIONS", value_class, operand, _CP1_CURRENCY)


def _text(shown: str, value_class: str, cp1_operand: str | None = None) -> Cell:
    return Cell("", "known", shown, value_class=value_class, cp1_operand=cp1_operand)


def _gap(reason: str, unit: str = "MILLIONS") -> Cell:
    return Cell("", "gap", None, unit=unit, reason=reason)


def _number(table_id: str, rows: list[tuple[str, list[Cell]]]) -> tuple[Row, ...]:
    """Assign fact ids T2E.<n>.rNN (one value column) or T2E.<n>.rNN.cK."""
    out = []
    for r, (label, cells) in enumerate(rows, 1):
        multi = len(cells) > 1
        named = tuple(
            replace(cell, fact_id=f"{table_id}.r{r:02d}" + (f".c{c}" if multi else ""))
            for c, cell in enumerate(cells, 1)
        )
        out.append(Row(label, named))
    return tuple(out)


# --- tables -----------------------------------------------------------------------------------

RUNWAY_ROW = (
    "Months until cash reaches minimum cash from run-rate cash flow alone "
    "(excludes maturities and amortisation)"
)
NOT_ASSESSED = "Not calculable: minimum cash not assessed"


def _sources_and_uses(o: Operands, b: Bridge) -> Table:
    assert o.equity_issuance is not None and o.equity_repurchases is not None
    d0 = b.balance_date.isoformat()
    opening = add_months(b.balance_date, -12).isoformat()
    rows: list[tuple[str, list[Cell]]] = [
        (f"Opening cash ({opening})", [_copy(o.opening_cash, "calculated", "opening_cash")]),
        ("Operating cash flow", [_copy(o.cfo, "calculated", "cfo")]),
        ("Net cash used in investing", [_copy(o.investing, "calculated", "investing")]),
        ("Net debt issued", [_copy(o.net_debt_issuance, "calculated", "net_debt_issuance")]),
        (
            "Equity issuance and repurchases",
            [
                _copy(
                    o.equity_issuance + o.equity_repurchases,
                    "calculated",
                    "equity_issuance+equity_repurchases",
                )
            ],
        ),
        ("Dividends paid", [_copy(o.dividends_paid, "calculated", "dividends_paid")]),
        (
            "Other investing and financing",
            [_copy(o.other_investing_financing, "calculated", "other_investing_financing")],
        ),
        ("FX effect on cash", [_copy(o.fx_effect, "calculated", "fx_effect")]),
        ("Closing cash (calculated)", [_money(b.sources_and_uses_closing_cash_calculated)]),
        ("Closing cash (reported)", [_copy(o.closing_cash, "calculated", "closing_cash")]),
        ("Difference (calculated less reported)", [_money(b.sources_and_uses_difference)]),
    ]
    return Table(
        "T2E.1",
        "Liquidity sources and uses",
        "Line",
        (f"Twelve months to {d0} (US$ m)",),
        _number("T2E.1", rows),
    )


def _position(o: Operands, b: Bridge) -> Table:
    assert b.undrawn_revolver is not None and b.liquidity_to_total_debt is not None
    rows: list[tuple[str, list[Cell]]] = [
        ("Cash and cash equivalents", [_copy(o.cash_bs, "source", "cash_bs")]),
        ("Restricted cash", [_copy(o.restricted_cash, "source", "restricted_cash")]),
        ("Revolver commitment", [_copy(o.rcf_commitment, "source", "rcf_commitment")]),
        ("Revolver drawn", [_copy(o.rcf_drawn, "source", "rcf_drawn")]),
        (
            "Undrawn committed revolver",
            [_num(b.undrawn_revolver, "MILLIONS", "calculated", "undrawn_rcf")],
        ),
        (
            "Undrawn term loan commitment (not counted as liquidity)",
            [
                _num(
                    _required(b.undrawn_term_commitment),
                    "MILLIONS",
                    "calculated",
                    "T4.18 commitment - drawn_amount",
                )
            ],
        ),
        (
            "Available liquidity",
            [_num(_required(b.available_liquidity), "MILLIONS", "calculated", "liquidity")],
        ),
        ("Total debt", [_copy(o.total_debt_bs, "source", "total_debt_bs")]),
        (
            "Liquidity to total debt",
            [_num(b.liquidity_to_total_debt, "PERCENT", "calculated", "liquidity_to_debt")],
        ),
    ]
    return Table(
        "T2E.2",
        "Liquidity position",
        "Line",
        (f"{b.balance_date.isoformat()} (US$ m)",),
        _number("T2E.2", rows),
    )


def _required(value: Decimal | None) -> Decimal:
    assert value is not None
    return value


def _runway_cell(b: Bridge) -> Cell:
    if b.runway_state == "not_reached":
        return Cell("", "known", "Not reached at run rate", unit="months", value_class="calculated")
    if b.runway_state == "months":
        months = _required(b.months_to_minimum_cash)
        return Cell("", "known", _months_text(months), months, "months", "calculated")
    if b.runway_reason in (RUNWAY_NO_MINIMUM, RUNWAY_NO_REVOLVER):
        return _gap(b.runway_reason, "months")
    raise ValueError("CP-2D has no fixed runway gap wording for a missing cash flow or cash")


def _runway_table(b: Bridge) -> Table:
    rows: list[tuple[str, list[Cell]]] = [
        (
            "Run-rate net cash flow before new borrowing, per year",
            [_money(b.run_rate_net_cash_flow_annual)],
        ),
        (
            "Run-rate net cash flow before new borrowing, per month",
            [_money(b.run_rate_net_cash_flow_monthly)],
        ),
        (
            "Horizon (analyst judgment)",
            [
                Cell(
                    "",
                    "known",
                    _months_text(b.horizon_months),
                    Decimal(b.horizon_months),
                    "months",
                    "analyst_judgment",
                )
            ],
        ),
        ("Horizon end date", [_text(b.horizon_end.isoformat(), "calculated")]),
        ("Run-rate net cash flow over the horizon", [_money(b.run_rate_net_cash_flow_horizon)]),
        # Outflows are shown negative (method_rules.table_signs).
        (
            "Scheduled amortisation inside the horizon",
            [_money(_ZERO - _required(b.amortisation_in_horizon))],
        ),
        ("Maturities inside the horizon", [_money(_ZERO - _required(b.maturities_in_horizon))]),
        (
            "Cash at horizon end before refinancing",
            [_money(b.cash_at_horizon_end_before_refinancing)],
        ),
        (RUNWAY_ROW, [_runway_cell(b)]),
    ]
    return Table("T2E.3", "Cash runway", "Line", ("Value",), _number("T2E.3", rows))


def _wall_table(b: Bridge) -> Table:
    rows: list[tuple[str, list[Cell]]] = []
    for w in b.wall:
        f = w.facility
        assert f.maturity_date is not None
        rows.append(
            (
                f"{f.name} ({f.facility_id})",
                [
                    _num(_required(f.principal), "MILLIONS", "source", "T4.18 principal"),
                    _text(f.maturity_date.isoformat(), "source", "T4.18 maturity_date"),
                    Cell(
                        "",
                        "known",
                        _months_text(w.months_to_maturity),
                        Decimal(w.months_to_maturity),
                        "months",
                        "calculated",
                    ),
                    _text("Yes" if w.inside_horizon else "No", "calculated"),
                    # compute refuses a missing or zero total debt, so the shares are known.
                    _num(_required(w.share_of_total_debt), "PERCENT", "calculated"),
                    _num(_required(w.cumulative_share), "PERCENT", "calculated"),
                ],
            )
        )
    columns = (
        "Principal (US$ m)",
        "Maturity date",
        f"Months from {b.balance_date.isoformat()}",
        "Inside horizon",
        "Share of total debt",
        "Cumulative share",
    )
    return Table("T2E.4", "Maturity wall", "Facility", columns, _number("T2E.4", rows))


def _funding_table(b: Bridge) -> Table:
    assert b.undrawn_revolver is not None
    assessed = b.minimum_cash is not None
    rows: list[tuple[str, list[Cell]]] = [
        (
            "Cash at horizon end before refinancing",
            [_money(b.cash_at_horizon_end_before_refinancing)],
        ),
        (
            "Undrawn committed revolver",
            [_num(b.undrawn_revolver, "MILLIONS", "calculated", "undrawn_rcf")],
        ),
        ("Resources at horizon end", [_money(b.resources_at_horizon_end)]),
        (
            "Minimum cash (analyst judgment)",
            [
                _money(b.minimum_cash, "analyst_judgment")
                if assessed
                else _gap("Minimum cash not assessed")
            ],
        ),
        (
            "Cash-only headroom over minimum cash (excludes any revolver)",
            [_money(b.cash_only_headroom) if assessed else _gap(NOT_ASSESSED)],
        ),
        ("Headroom over minimum cash", [_money(b.headroom) if assessed else _gap(NOT_ASSESSED)]),
        ("Funding gap", [_money(b.funding_gap) if assessed else _gap(NOT_ASSESSED)]),
    ]
    return Table("T2E.5", "Funding gap", "Line", ("Value (US$ m)",), _number("T2E.5", rows))


# --- claims (lease "Submission schema"; figures are references to own cells) ------------------


def _claims(b: Bridge, tables: tuple[Table, ...]) -> tuple[ClaimText, ...]:
    cells = {c.fact_id: c for t in tables for r in t.rows for c in r.cells}
    d0 = format_date(b.balance_date)

    def ref(fact_id: str) -> str:
        cell = cells[fact_id]
        if cell.state != "known" or cell.unit != "MILLIONS":
            raise ValueError(f"A claim may reference only a known US$ m cell: {fact_id}")
        return "{" + fact_id + "|US$ m}"

    def claim(
        claim_id: str, template: str, refs: tuple[str, ...], cites: tuple[str, ...]
    ) -> ClaimText:
        text = template
        for fact_id in refs:
            text = text.replace(ref(fact_id), f"{cells[fact_id].shown} US$ m")
        unique = tuple(dict.fromkeys(refs))
        return ClaimText(claim_id, template, text, unique, cites + unique)

    out = [
        claim(
            "CP-2D-LIQ-01",
            f"Available liquidity at {d0} is {ref('T2E.2.r07')} (cash {ref('T2E.2.r01')} plus "
            f"undrawn committed revolver {ref('T2E.2.r05')}).",
            ("T2E.2.r07", "T2E.2.r01", "T2E.2.r05"),
            ("cash_closing", "undrawn_rcf", "liquidity"),
        ),
        claim(
            "CP-2D-RUN-01",
            f"Run-rate net cash flow before new borrowing is {ref('T2E.3.r01')} a year on the "
            f"twelve months to {d0}; cash at the end of the assessed horizon before any "
            f"refinancing is {ref('T2E.3.r08')}.",
            ("T2E.3.r01", "T2E.3.r08"),
            ("cfo", "investing", "financing", "net_debt_issuance", "cash_bs"),
        ),
        claim(
            "CP-2D-MAT-01",
            f"The cash outflow from debt maturing inside the horizon is {ref('T2E.3.r07')} "
            f"against total debt of {ref('T2E.2.r08')}.",
            ("T2E.3.r07", "T2E.2.r08"),
            ("T4.18 principal", "T4.18 maturity_date", "total_debt"),
        ),
    ]
    if b.minimum_cash is None:
        out.append(
            claim(
                "CP-2D-GAP-01",
                "The funding gap is not calculated: the minimum cash has not been assessed.",
                (),
                (),
            )
        )
    elif b.funding_gap == 0:
        out.append(
            claim(
                "CP-2D-GAP-01",
                f"Resources at the horizon end exceed the assumed minimum cash by "
                f"{ref('T2E.5.r06')}; no funding gap arises.",
                ("T2E.5.r06",),
                ("cash_bs", "undrawn_rcf"),
            )
        )
    else:
        gap = ref("T2E.5.r07")
        out.append(
            claim(
                "CP-2D-GAP-01",
                f"Resources at the horizon end fall short of the assumed minimum cash by {gap}; "
                f"a funding gap of {gap} arises.",
                ("T2E.5.r07", "T2E.5.r07"),
                ("cash_bs", "undrawn_rcf"),
            )
        )
    return tuple(out)


# --- the module calculation -------------------------------------------------------------------


def _judgments(b: Bridge, submission: LiquidityBridgeSubmission) -> Ledger:
    categories = {a.section: a.category for a in submission.assessments}
    minimum = (
        "not assessed"
        if b.minimum_cash is None
        else amount_text(b.minimum_cash) + " (analyst assumption)"
    )
    rows = (
        ("Horizon", _months_text(b.horizon_months)),
        ("Minimum cash", minimum),
        ("Liquidity runway", categories["liquidity_runway"]),
        ("Maturity wall", categories["maturity_wall"]),
        ("Funding gap", categories["funding_gap"]),
    )
    return Ledger("T2E.6", "Analyst judgments", rows)


def compute(inputs: Cp2dInputs) -> Cp2dResult:
    """Tables T2E.1-T2E.7, own limitations, claims and status for a valid submission.

    Fails closed (ValueError) where the lease or oracle fixes no wording: an undisclosed
    revolver, any other missing operand, a non-USD facility, a zero total debt, an invalid
    submission, or a recomputation that disagrees with CP-1's settled T4.10 metrics.
    """
    o = inputs.operands
    unpinned = _missing(o, _UNPINNED_WHEN_MISSING + _REVOLVER)
    if unpinned:
        raise ValueError(
            f"CP-2D has no fixed table or claim wording for missing operands: {unpinned}"
        )
    if o.total_debt_bs == 0:
        raise ValueError("CP-2D has no fixed wording for shares of a zero total debt")
    submission = inputs.submission
    issues = submission_issues(submission=submission, offered_refs=inputs.offered_refs)
    if issues:
        raise ValueError("; ".join(issues))
    bridge = bridge_of(inputs)
    mismatches = check_cp1_totals(operands=o, bridge=bridge)
    if mismatches:
        raise ValueError("; ".join(mismatches))
    limitations = _limitations(operands=o, bridge=bridge)
    tables = (
        _sources_and_uses(o, bridge),
        _position(o, bridge),
        _runway_table(bridge),
        _wall_table(bridge),
        _funding_table(bridge),
    )
    return Cp2dResult(
        bridge=bridge,
        tables=tables,
        judgments=_judgments(bridge, inputs.submission),
        gaps_ledger=Ledger(
            "T2E.7", "Gaps ledger", tuple((label, kind) for label, kind, _ in limitations)
        ),
        own_limitations=tuple(text for _, _, text in limitations),
        claims=_claims(bridge, tables),
        # Own limitations always hold the run-rate basis, so the module is restricted.
        status="restricted",
    )


# --- calculation-level validation (lease "Refusals"; wording expected.json#refusals) -----------

HORIZON_ISSUE = "horizon_months must be between 1 and 60"
NEGATIVE_MINIMUM_ISSUE = "minimum_cash.amount must not be negative"
BOTH_ISSUE = "give minimum_cash or minimum_cash_absence, not both"
NEITHER_ISSUE = "give minimum_cash or minimum_cash_absence"
SECTION_ISSUE = "assessments must hold exactly one row per section"
DIGIT_ISSUE = "text must not contain a figure"
CONCLUSION_ISSUE = "text carries a prohibited conclusion"
BASIS_ISSUE = "basis_refs names a fact the view does not offer"
INSUFFICIENT_ISSUE = "an Insufficient Information assessment states its limitation"
LIMITATION_ISSUE = "only an Insufficient Information assessment carries a limitation"

# The stems the oracle pins (manifest analyst_judgment_policy; builder FORBIDDEN list), each
# matched from a word boundary so a stem also catches its inflections ("refinancing").
PROHIBITED_STEMS = (
    "refinanc",
    "recommend",
    "buy",
    "sell",
    "overweight",
    "underweight",
    "fulcrum",
    "recovery",
    "covenant breach",
    "covenant test is met",
    "in compliance with",
    "covenant compliance",
    "default will",
    "lme",
    "liability management",
)
_PROHIBITED = re.compile(r"\b(?:" + "|".join(re.escape(s) for s in PROHIBITED_STEMS) + ")")


def _texts(submission: LiquidityBridgeSubmission) -> list[str]:
    texts: list[str] = []
    for a in submission.assessments:
        texts += [a.text, a.credit_implication]
        if a.limitation is not None:
            texts.append(a.limitation)
    if submission.minimum_cash is not None:
        texts.append(submission.minimum_cash.rationale)
    if submission.minimum_cash_absence is not None:
        texts += [submission.minimum_cash_absence.reason, submission.minimum_cash_absence.follow_up]
    return texts


def submission_issues(
    *, submission: LiquidityBridgeSubmission, offered_refs: frozenset[str]
) -> tuple[str, ...]:
    """Validator issues of a CP-2D submission, each once, in the lease's order."""
    s = submission
    issues: list[str] = []
    low, high = HORIZON_BOUNDS
    if not low <= s.horizon_months <= high:
        issues.append(HORIZON_ISSUE)
    if s.minimum_cash is not None and s.minimum_cash.amount < 0:
        issues.append(NEGATIVE_MINIMUM_ISSUE)
    if s.minimum_cash is not None and s.minimum_cash_absence is not None:
        issues.append(BOTH_ISSUE)
    if s.minimum_cash is None and s.minimum_cash_absence is None:
        issues.append(NEITHER_ISSUE)
    sections = [a.section for a in s.assessments]
    if sorted(sections) != sorted(SECTIONS):
        issues.append(SECTION_ISSUE)
    texts = _texts(s)
    if any(ch.isdigit() for t in texts for ch in t):
        issues.append(DIGIT_ISSUE)
    if any(_PROHIBITED.search(t.casefold()) for t in texts):
        issues.append(CONCLUSION_ISSUE)
    refs = [r for a in s.assessments for r in a.basis_refs]
    if s.minimum_cash is not None:
        refs += s.minimum_cash.basis_refs
    if any(r not in offered_refs for r in refs):
        issues.append(BASIS_ISSUE)
    for a in s.assessments:
        carried = a.limitation is not None
        stated = a.limitation is not None and a.limitation.strip() != ""
        insufficient = a.category == "Insufficient Information"
        if insufficient and not stated:
            issues.append(INSUFFICIENT_ISSUE)
        if carried and not insufficient:
            issues.append(LIMITATION_ISSUE)
    return tuple(dict.fromkeys(issues))
