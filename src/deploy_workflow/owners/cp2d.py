"""CP-2D (Liquidity) owner core: the Stage 1 calculation (docs/CP2D-OWNER-LEASE.md, Method,
as amended by docs/rulings/2026-10-28-stage1.md, CP-2D sections of rounds 2 to 9, and round 11's
maturity before D0 and blank text).

Pure functions over typed inputs. Python owns every figure: sources and uses (T2E.1), the
liquidity position (T2E.2), the run-rate cash runway (T2E.3), the maturity wall (T2E.4) and
the funding gap (T2E.5), plus the analyst-judgment and gaps ledgers (T2E.6, T2E.7), the own
limitations and the claim texts. All arithmetic is Decimal. A value that cannot be calculated
is a ``Gap`` carrying the reason of the first missing operand in formula order; it is never
read as zero, and nothing that passes ``submission_issues`` raises. No I/O, store, host,
session or render call: connections, the read view and the G1 seams are later stages.
"""

from calendar import monthrange
from dataclasses import dataclass, replace
from datetime import date
from decimal import ROUND_HALF_UP, Context, Decimal, localcontext
from typing import Literal

from deploy_vii.contracts import Contract, Identifier, Text
from deploy_vii.display import UnitClass, format_date, format_value
from deploy_vii.model._cells import CONTEXT as CP1_CONTEXT
from deploy_workflow.owners.blank import is_blank

MODULE_ID = "CP-2D"
HORIZON_BOUNDS = (1, 60)
CURRENCY = "USD"

Section = Literal["liquidity_runway", "maturity_wall", "funding_gap"]
SECTIONS: tuple[Section, ...] = ("liquidity_runway", "maturity_wall", "funding_gap")
Category = Literal[
    "Documentary Fact", "Management Language", "Analyst Interpretation", "Insufficient Information"
]
RunwayState = Literal["months", "not_reached", "missing"]
CellState = Literal["known", "gap", "not_applicable", "conflicting"]
OperandStatus = Literal["known", "missing", "conflicting", "not_applicable"]

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
    """One CP-1 T4.18 facility row at the balance date (QUARTER period over its FY alias).

    Ruling A5 (round 6): ``currency`` and ``name`` are the row's own ``currency`` and
    ``facility_name`` text facts, taken from the same row (by ``facility_id``) as the bound
    principal. They are never read through ``financial_series._maturity_figure``, which raises on
    a non-USD row and would make the 2D5 path unreachable. The Stage 2 reader builds this.
    """

    facility_id: str
    name: str
    currency: str | None
    principal: Decimal | None
    maturity_date: date | None
    commitment: Decimal | None
    drawn_amount: Decimal | None
    annual_amortisation: Decimal | None
    # Round 13 (R1 M1): the row's own CP-1 ``period`` string (one per row: the alias agrees).
    period: str


@dataclass(frozen=True)
class Operand:
    """One CP-1 head fact as the Method reads it (round 13, R1 M3): its status, its amount, its
    own ``period`` string and, when it is not known, CP-1's ``limitation`` verbatim.

    A known operand has an amount and a period; any other status has a limitation and no
    amount (the product's Fact contract)."""

    status: OperandStatus
    amount: Decimal | None
    period: str | None
    limitation: str | None

    def __post_init__(self) -> None:
        if self.status == "known":
            if self.amount is None or self.period is None:
                raise ValueError("CP-2D: a known operand needs an amount and a period")
        elif self.amount is not None or self.limitation is None:
            raise ValueError(f"CP-2D: a {self.status} operand needs a limitation and no amount")


@dataclass(frozen=True)
class Operands:
    """The CP-1 head facts the Method reads (manifest.fact_bindings names); None is no fact
    offered, which reads as missing.

    T4.5 flows are the twelve months to the balance date in the CP-1 fact's own sign; T4.6
    balances and T4.10 metrics are at the balance date, US$ m. ``liquidity_to_debt`` is a
    decimal fraction (0.4 is 40%; ruling 2D3).
    """

    # T4.5 statement history, LTM
    opening_cash: Operand | None
    cfo: Operand | None
    investing: Operand | None
    net_debt_issuance: Operand | None
    equity_issuance: Operand | None
    equity_repurchases: Operand | None
    dividends_paid: Operand | None
    other_investing_financing: Operand | None
    financing: Operand | None
    fx_effect: Operand | None
    closing_cash: Operand | None
    # T4.6 balance sheet, Q4
    cash_bs: Operand | None
    restricted_cash: Operand | None
    rcf_commitment: Operand | None
    rcf_drawn: Operand | None
    total_debt_bs: Operand | None
    # T4.10 settled metrics, cross-checked against the recomputation (never a second source)
    cash_closing: Operand | None
    total_debt: Operand | None
    undrawn_rcf: Operand | None
    liquidity: Operand | None
    liquidity_to_debt: Operand | None
    # T4.18 facility schedule: None when the schedule is absent, () when it lists no facility
    facilities: tuple[Facility, ...] | None


@dataclass(frozen=True)
class Cp2dInputs:
    operands: Operands
    balance_date: date
    submission: LiquidityBridgeSubmission
    # The CP-1 fact ids the read view offers (Stage 2 fills it from the view).
    offered_refs: frozenset[str]
    # Of those, the T4.18 maturity_date fact ids (ruling D-5).
    maturity_date_refs: frozenset[str]


# --- values that are known or carry the reason they are not ------------------------------------


@dataclass(frozen=True)
class Gap:
    """A value that is not calculated: missing, or not meaningful when ``applicable`` is
    False (shown as not_applicable)."""

    reason: str
    applicable: bool = True


@dataclass(frozen=True)
class OperandGap(Gap):
    """A CP-1 operand that is not known (round 13, R1 M3). ``reason`` is the dependants' reason
    (``Not calculable: <label> is <missing|conflicting|not applicable>``); a copy cell keeps
    ``status`` and CP-1's own ``limitation``, verbatim, as its reason."""

    status: OperandStatus = "missing"
    limitation: str | None = None


Num = Decimal | Gap

# CP-1 labels of the operands (manifest.fact_bindings labels without the period).
OPERAND_LABELS = {
    "opening_cash": "Opening cash",
    "cfo": "Operating cash flow",
    "investing": "Net cash used in investing",
    "net_debt_issuance": "Net debt issuance",
    "equity_issuance": "Equity issuance",
    "equity_repurchases": "Equity repurchases",
    "dividends_paid": "Dividends paid",
    "other_investing_financing": "Other investing and financing",
    "financing": "Net cash used in financing",
    "fx_effect": "FX effect on cash",
    "closing_cash": "Closing cash",
    "cash_bs": "Cash and cash equivalents",
    "restricted_cash": "Restricted cash",
    "rcf_commitment": "RCF commitment",
    "rcf_drawn": "RCF drawings",
    "total_debt_bs": "Total debt",
}


# The state words of CP-4C's _STATE_WORD (round 13, R1 M3).
STATE_WORD: dict[OperandStatus, str] = {
    "known": "known",
    "missing": "missing",
    "conflicting": "conflicting",
    "not_applicable": "not applicable",
}


def state_reason(label: str, status: OperandStatus) -> str:
    """The reason of an operand that is not known and of every value that depends on it."""
    return f"Not calculable: {label} is {STATE_WORD[status]}"


def missing_reason(label: str) -> str:
    """Ruling 2D-b: the reason of a missing operand and of every value that depends on it."""
    return state_reason(label, "missing")


# Reasons fixed by the oracle (minimum cash), the lease (runway) and rulings 2D2, 2D5, 2D-c.
MINIMUM_NOT_ASSESSED_CELL = "Minimum cash not assessed"
NOT_ASSESSED = "Not calculable: minimum cash not assessed"
RUNWAY_NO_MINIMUM = NOT_ASSESSED
RUNWAY_NO_REVOLVER = "Not calculable: revolver undisclosed"
# Undisclosed revolver: the table gap reasons stay as pinned by the oracle builder (2D2).
REV_COMMITMENT = "Revolver commitment not disclosed in the CP-1 register"
REV_DRAWN = "Revolver drawings not disclosed in the CP-1 register"
REV_UNDRAWN = "Undrawn revolver not calculable: commitment undisclosed"
REV_AVAILABLE = "Available liquidity not calculable: revolver undisclosed"
REV_RATIO = "Not calculable: available liquidity missing"
# Commitment known, drawings missing (ruling L1).
DRAWINGS_UNDRAWN = "Undrawn revolver not calculable: drawings undisclosed"
DRAWINGS_AVAILABLE = "Available liquidity not calculable: revolver drawings undisclosed"
RUNWAY_NO_DRAWINGS = "Not calculable: revolver drawings undisclosed"
FX_REASON = "Not calculable: facility {fid} is in {ccy}, not USD; no FX conversion is applied"
CURRENCY_UNSTATED = (
    "Not calculable: facility {fid} currency is not stated; no FX conversion is applied"
)
DATE_UNSTATED = "Not calculable: facility {fid} maturity date is not stated"
PRINCIPAL_UNSTATED = "Not calculable: facility {fid} principal is not stated"
# Round 11 (LEAD rulings, "CP-2D, a maturity before D0"): the CP-3C B1 rule. The date stays known;
# its position (months from D0, inside-horizon) and every dependant take this reason.
PRE_D0 = "Not calculable: facility {fid} maturity date is before the balance date"
ZERO_DEBT = "Not meaningful: total debt is zero (ZERO_OR_NEGATIVE_DENOMINATOR)"
NEGATIVE_DEBT = "Not meaningful: total debt is negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
# An absent T4.18 schedule, and one that lists no facility (ruling D-3).
SCHEDULE_MISSING = missing_reason("T4.18 facility schedule")
SCHEDULE_EMPTY = "Not calculable: the T4.18 facility schedule lists no facility"


def _operand(operands: Operands, name: str) -> Operand | None:
    operand: Operand | None = getattr(operands, name)
    return operand


def _amount(operands: Operands, name: str) -> Decimal | None:
    """The operand's amount: None unless the CP-1 fact is known."""
    operand = _operand(operands, name)
    return None if operand is None else operand.amount


def _absent(operands: Operands, name: str) -> bool:
    """No fact offered, or one CP-1 reports missing (an undisclosed term)."""
    operand = _operand(operands, name)
    return operand is None or operand.status == "missing"


def _periods(operands: Operands, spec: str) -> tuple[str, ...]:
    """The CP-1 periods of the known operands named in ``spec`` (names joined by ``+``)."""
    out: list[str] = []
    for name in spec.split("+"):
        operand = _operand(operands, name)
        if operand is not None and operand.period is not None:
            out.append(operand.period)
    return tuple(out)


def _op(operands: Operands, name: str) -> Num:
    operand = _operand(operands, name)
    if operand is None:
        return Gap(missing_reason(OPERAND_LABELS[name]))
    if operand.amount is not None:
        return operand.amount
    return OperandGap(
        state_reason(OPERAND_LABELS[name], operand.status),
        status=operand.status,
        limitation=operand.limitation,
    )


def _total(*values: Num) -> Num:
    """Sum, or the first gap in formula order (a missing operand never defaults to zero)."""
    for v in values:
        if isinstance(v, Gap):
            return v
    return sum((v for v in values if not isinstance(v, Gap)), _ZERO)


def _diff(a: Num, b: Num) -> Num:
    """a - b, or the first gap."""
    if isinstance(a, Gap):
        return a
    if isinstance(b, Gap):
        return b
    return a - b


def _neg(value: Num) -> Num:
    return value if isinstance(value, Gap) else _ZERO - value


def _ratio(numerator: Num, denominator: Num) -> Num:
    """CP-1's ratio rule: a denominator <= 0 is not meaningful; division in CP-1's context."""
    if isinstance(numerator, Gap):
        return numerator
    if isinstance(denominator, Gap):
        return denominator
    if denominator == 0:
        return Gap(ZERO_DEBT, applicable=False)
    if denominator < 0:
        return Gap(NEGATIVE_DEBT, applicable=False)
    return CP1_CONTEXT.divide(numerator, denominator)


def add_months(start: date, months: int) -> date:
    """Calendar month arithmetic, the day clamped to the end of the target month."""
    year, index = divmod(start.month - 1 + months, 12)
    year += start.year
    month = index + 1
    return date(year, month, min(start.day, monthrange(year, month)[1]))


def months_between(start: date, end: date) -> int:
    """Ruling A1 (round 6): the largest n with ``add_months(start, n) <= end``, so months below
    the horizon mean inside it and months above it mean outside."""
    months = (end.year - start.year) * 12 + (end.month - start.month)
    return months - 1 if add_months(start, months) > end else months


# --- facilities (rulings 2D5, 2D6, 2D-c) ------------------------------------------------------


def _ordered(facilities: tuple[Facility, ...]) -> tuple[Facility, ...]:
    """Maturity date then facility_id; an undated facility after every dated one, by id."""
    return tuple(
        sorted(
            facilities,
            key=lambda f: (f.maturity_date is None, f.maturity_date or date.min, f.facility_id),
        )
    )


def _currency_gap(f: Facility) -> Gap | None:
    if f.currency is None:
        return Gap(CURRENCY_UNSTATED.format(fid=f.facility_id))
    if f.currency != CURRENCY:
        return Gap(FX_REASON.format(fid=f.facility_id, ccy=f.currency))
    return None


def _date_gap(f: Facility) -> Gap | None:
    return Gap(DATE_UNSTATED.format(fid=f.facility_id)) if f.maturity_date is None else None


def _position_gap(f: Facility, balance_date: date) -> Gap | None:
    """Why the facility has no place against D0: its date is unstated, or before D0 (round 11,
    the CP-3C B1 rule in the unstated date's slot)."""
    if f.maturity_date is not None and f.maturity_date < balance_date:
        return Gap(PRE_D0.format(fid=f.facility_id))
    return _date_gap(f)


def _term(f: Facility, value: Decimal | None, term: str) -> Num:
    """Ruling D-3: the 2D-c frame for commitment, drawn amount and annual amortisation."""
    if value is None:
        return Gap(f"Not calculable: facility {f.facility_id} {term} is not stated")
    return value


def _principal(f: Facility) -> Num:
    if f.principal is None:
        return Gap(PRINCIPAL_UNSTATED.format(fid=f.facility_id))
    return f.principal


def _usd_principal(f: Facility) -> Num:
    """The principal as a US$ amount: missing when unstated or not in USD."""
    principal = _principal(f)
    if isinstance(principal, Gap):
        return principal
    return _currency_gap(f) or principal


def _amortisation(f: Facility, horizon_months: int) -> Num:
    """min(annual amortisation x H / 12, principal) for a facility maturing after the horizon."""
    annual = _term(f, f.annual_amortisation, "annual amortisation")
    principal = _principal(f)
    if isinstance(annual, Gap):
        return annual
    if isinstance(principal, Gap):
        return principal
    return min(annual * horizon_months / 12, principal)


def _schedule_gap(operands: Operands) -> Gap | None:
    """Ruling D-3: an absent schedule is missing; an empty one is missing unless total debt is a
    known zero, when nothing is owed and the schedule totals are a known zero."""
    if operands.facilities is None:
        return Gap(SCHEDULE_MISSING)
    if operands.facilities or _amount(operands, "total_debt_bs") == 0:
        return None
    return Gap(SCHEDULE_EMPTY)


def _schedule(
    ordered: tuple[Facility, ...],
    horizon_months: int,
    balance_date: date,
    horizon_end: date,
    absent: Gap | None,
) -> tuple[Num, Num]:
    """(maturities, amortisation) inside the horizon, each missing at its first gap."""
    if absent is not None:
        return absent, absent
    maturities: Num = _ZERO
    amortisation: Num = _ZERO
    for f in ordered:
        blocked = _currency_gap(f) or _position_gap(f, balance_date)
        if blocked is not None:
            maturities = _total(maturities, blocked)
            amortisation = _total(amortisation, blocked)
            continue
        assert f.maturity_date is not None
        if f.maturity_date <= horizon_end:
            maturities = _total(maturities, _principal(f))
        else:
            amortisation = _total(amortisation, _amortisation(f, horizon_months))
    return maturities, amortisation


def _undrawn_term(ordered: tuple[Facility, ...], absent: Gap | None) -> Num:
    """Undrawn term commitment: the sum of commitment less drawn (shown, not counted)."""
    if absent is not None:
        return absent
    total: Num = _ZERO
    for f in ordered:
        undrawn = _diff(
            _term(f, f.commitment, "commitment"), _term(f, f.drawn_amount, "drawn amount")
        )
        total = _total(total, _currency_gap(f) or undrawn)
    return total


def _inside(
    ordered: tuple[Facility, ...], balance_date: date, horizon_end: date, absent: Gap | None
) -> bool | Gap:
    """Whether any facility matures inside the horizon; missing while a facility with no
    position (undated, or dated before D0) decides."""
    if absent is not None:
        return absent
    placed = [f.maturity_date for f in ordered if _position_gap(f, balance_date) is None]
    if any(d is not None and d <= horizon_end for d in placed):
        return True
    unplaced = next((g for f in ordered if (g := _position_gap(f, balance_date)) is not None), None)
    return False if unplaced is None else unplaced


@dataclass(frozen=True)
class WallRow:
    facility: Facility
    principal: Num
    maturity_date: date | Gap
    months_to_maturity: int | Gap
    inside_horizon: bool | Gap
    share_of_total_debt: Num
    cumulative_share: Num


def _wall(
    ordered: tuple[Facility, ...], balance_date: date, horizon_end: date, total_debt: Num
) -> tuple[WallRow, ...]:
    """One row per facility in wall order. A row whose share or date is missing makes its own
    and every later cumulative share missing with the first reason."""
    rows: list[WallRow] = []
    cumulative: Num = _ZERO
    for f in ordered:
        amount = _usd_principal(f)
        share = _ratio(amount, total_debt)
        undated = _date_gap(f)
        if isinstance(cumulative, Gap):
            pass
        elif isinstance(share, Gap):
            cumulative = share
        elif undated is not None:
            cumulative = undated
        else:
            cumulative += share
        unplaced = _position_gap(f, balance_date)
        if f.maturity_date is None:
            assert undated is not None
            dated: date | Gap = undated
            months: int | Gap = undated
            inside: bool | Gap = undated
        elif unplaced is not None:  # round 11: before D0, the date stays known
            dated = f.maturity_date
            months = inside = unplaced
        else:
            dated = f.maturity_date
            months = months_between(balance_date, f.maturity_date)
            inside = f.maturity_date <= horizon_end
        rows.append(WallRow(f, amount, dated, months, inside, share, cumulative))
    return tuple(rows)


# --- runway ------------------------------------------------------------------------------------


def _wide(value: Decimal) -> Context:
    """A context with room for one decimal place on a value of any magnitude."""
    return Context(prec=max(_CONTEXT.prec, value.adjusted() + 3))


def _runway(
    *,
    annual: Num,
    cash: Num,
    undrawn: Num,
    minimum_cash: Decimal | None,
    revolver_reason: str = RUNWAY_NO_REVOLVER,
) -> tuple[RunwayState, str | None, Decimal | None]:
    """Months until cash reaches minimum cash from run-rate cash flow alone (Method 3)."""
    if minimum_cash is None:
        return "missing", RUNWAY_NO_MINIMUM, None
    if isinstance(cash, Gap):
        return "missing", cash.reason, None
    if isinstance(annual, Gap):
        return "missing", annual.reason, None
    if isinstance(undrawn, Gap):
        # A revolver is never negative, so cash alone clearing the minimum is enough.
        if annual >= 0 and cash - minimum_cash >= 0:
            return "not_reached", None, None
        return "missing", revolver_reason, None
    start = cash + undrawn - minimum_cash
    if annual >= 0:
        if start >= 0:
            return "not_reached", None, None
        return "months", None, _ZERO.quantize(_ONE_DP)
    months = max(_ZERO, start) * 12 / -annual
    return "months", None, months.quantize(_ONE_DP, context=_wide(months), rounding=ROUND_HALF_UP)


# --- the bridge (derived values) --------------------------------------------------------------


@dataclass(frozen=True)
class Bridge:
    horizon_months: int
    minimum_cash: Decimal | None
    balance_date: date
    horizon_end: date
    ordered_facilities: tuple[Facility, ...]
    run_rate_net_cash_flow_annual: Num
    run_rate_net_cash_flow_monthly: Num
    run_rate_net_cash_flow_horizon: Num
    maturity_inside_horizon: bool | Gap
    maturities_in_horizon: Num
    amortisation_in_horizon: Num
    cash_at_horizon_end_before_refinancing: Num
    undrawn_revolver: Num
    undrawn_term_commitment: Num
    available_liquidity: Num
    liquidity_to_total_debt: Num
    resources_at_horizon_end: Num
    cash_only_headroom: Num
    headroom: Num
    funding_gap: Num
    runway_state: RunwayState
    runway_reason: str | None
    months_to_minimum_cash: Decimal | None
    sources_and_uses_closing_cash_calculated: Num
    sources_and_uses_difference: Num
    financing_lines_difference: Num
    wall: tuple[WallRow, ...]


def compose_bridge(
    *,
    operands: Operands,
    horizon_months: int,
    minimum_cash: Decimal | None,
    balance_date: date,
) -> Bridge:
    """Method items 1-6, pure Decimal. A missing operand makes its dependants gaps."""
    low, high = HORIZON_BOUNDS
    if not low <= horizon_months <= high:
        raise ValueError("horizon_months must be between 1 and 60")
    if minimum_cash is not None and minimum_cash < 0:
        raise ValueError("minimum_cash.amount must not be negative")
    if minimum_cash is not None and minimum_cash == 0:
        minimum_cash = _ZERO  # "-0" is stored unsigned
    o = operands
    horizon_end = add_months(balance_date, horizon_months)
    ordered = _ordered(o.facilities or ())
    absent = _schedule_gap(o)
    undisclosed = _absent(o, "rcf_commitment")
    drawings = not undisclosed and _absent(o, "rcf_drawn")
    with localcontext(_CONTEXT):
        # "Closing cash" in Methods 3 and 5 is T4.6 cash_bs (ruling 2D7).
        cash = _op(o, "cash_bs")
        annual = _diff(
            _total(_op(o, "cfo"), _op(o, "investing"), _op(o, "financing")),
            _op(o, "net_debt_issuance"),
        )
        monthly = annual if isinstance(annual, Gap) else annual / 12
        over_horizon = annual if isinstance(annual, Gap) else annual * horizon_months / 12
        maturities, amortisation = _schedule(
            ordered, horizon_months, balance_date, horizon_end, absent
        )
        end_cash = _diff(_total(cash, over_horizon), _total(amortisation, maturities))
        undrawn: Num = _diff(_op(o, "rcf_commitment"), _op(o, "rcf_drawn"))
        available = _total(cash, undrawn)
        resources = _total(end_cash, undrawn)
        revolver_reason = RUNWAY_NO_DRAWINGS if drawings else RUNWAY_NO_REVOLVER
        if undisclosed or drawings:
            undrawn = Gap(REV_UNDRAWN if undisclosed else DRAWINGS_UNDRAWN)
            if not isinstance(cash, Gap):
                available = Gap(REV_AVAILABLE if undisclosed else DRAWINGS_AVAILABLE)
            if not isinstance(end_cash, Gap):
                resources = Gap(revolver_reason)
        to_debt = _ratio(available, _op(o, "total_debt_bs"))
        # The builder pins REV_RATIO for an undisclosed revolver (build.py:516). With drawings
        # undisclosed the ratio keeps its operand's reason, DRAWINGS_AVAILABLE (round 9 item 1).
        if isinstance(available, Gap) and available.reason == REV_AVAILABLE:
            to_debt = Gap(REV_RATIO)
        if minimum_cash is None:
            cash_only: Num = Gap(NOT_ASSESSED)
            headroom: Num = Gap(NOT_ASSESSED)
        else:
            cash_only = _diff(end_cash, minimum_cash)
            headroom = _diff(resources, minimum_cash)
        gap = headroom if isinstance(headroom, Gap) else max(_ZERO, -headroom)
        state, reason, months = _runway(
            annual=annual,
            cash=cash,
            undrawn=undrawn,
            minimum_cash=minimum_cash,
            revolver_reason=revolver_reason,
        )
        # Sources and uses use CP-1's financing total; the lines are display rows (2D9).
        financing = _op(o, "financing")
        calculated_close = _total(
            _op(o, "opening_cash"),
            _op(o, "cfo"),
            _op(o, "investing"),
            financing,
            _op(o, "fx_effect"),
        )
        difference = _diff(calculated_close, _op(o, "closing_cash"))
        lines = _total(
            _op(o, "net_debt_issuance"),
            _op(o, "equity_issuance"),
            _op(o, "equity_repurchases"),
            _op(o, "dividends_paid"),
            _op(o, "other_investing_financing"),
        )
        lines_difference = _diff(lines, financing)
        wall = _wall(ordered, balance_date, horizon_end, _op(o, "total_debt_bs"))
        term_undrawn = _undrawn_term(ordered, absent)
    return Bridge(
        horizon_months=horizon_months,
        minimum_cash=minimum_cash,
        balance_date=balance_date,
        horizon_end=horizon_end,
        ordered_facilities=ordered,
        run_rate_net_cash_flow_annual=annual,
        run_rate_net_cash_flow_monthly=monthly,
        run_rate_net_cash_flow_horizon=over_horizon,
        maturity_inside_horizon=_inside(ordered, balance_date, horizon_end, absent),
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
        financing_lines_difference=lines_difference,
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


CP1_DIFFERS = (
    "CP-1's {label} differs from the value recomputed from its line items; CP-2D uses the "
    "recomputed value and shows both."
)
CP1_REPORTS_NO = "CP-1 reports no {label}; the value recomputed from its line items is used."


def check_cp1_totals(*, operands: Operands, bridge: Bridge) -> tuple[tuple[str, str], ...]:
    """(label, limitation) for each CP-1 T4.10 metric that disagrees with the recomputation.

    Ruling 2D-d: a settled result, not a refusal. CP-2D's arithmetic uses its recomputed value;
    a missing recomputation is a 2D-b gap and adds nothing here.
    """
    pairs: tuple[tuple[str, Decimal | None, Num], ...] = (
        ("cash_closing", _amount(operands, "cash_closing"), _op(operands, "cash_bs")),
        ("total_debt", _amount(operands, "total_debt"), _op(operands, "total_debt_bs")),
        ("undrawn_rcf", _amount(operands, "undrawn_rcf"), bridge.undrawn_revolver),
        ("liquidity", _amount(operands, "liquidity"), bridge.available_liquidity),
        (
            "liquidity_to_debt",
            _amount(operands, "liquidity_to_debt"),
            bridge.liquidity_to_total_debt,
        ),
    )
    out: list[tuple[str, str]] = []
    for label, settled, mine in pairs:
        if isinstance(mine, Gap):
            continue
        if settled is None:
            out.append((label, CP1_REPORTS_NO.format(label=label)))
        elif settled != mine:
            out.append((label, CP1_DIFFERS.format(label=label)))
    return tuple(out)


# --- spelling ---------------------------------------------------------------------------------


def amount_text(value: Decimal) -> str:
    """US$ m prose spelling: 0 dp half-up, negatives in brackets (display.py)."""
    return format_value(value, "amount", "known") + " US$ m"


def exact_amount_text(value: Decimal) -> str:
    """Ruling L3: a difference spelled exactly (normalised, negatives in brackets, no
    rounding), in US$ m. Trailing zeros are stripped from the text: ``Decimal.normalize`` would
    round to the context precision."""
    body = format(value.copy_abs(), "f")
    if "." in body:
        body = body.rstrip("0").rstrip(".")
    return (f"({body})" if value < 0 else body) + " US$ m"


def _months_text(value: Decimal | int) -> str:
    return f"{value} months"


# --- own limitations --------------------------------------------------------------------------

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
FINANCING_LINES_DIFFER = (
    "Financing lines differ from CP-1's net cash used in financing by {amount}; sources and "
    "uses use the financing total."
)
FX_LIMITATION = (
    "Facility {fid} is denominated in {ccy}; maturity-wall totals and shares are not calculated "
    "because no FX conversion is applied."
)
TERM_LIMITATION = (
    "Facility {fid} {term} is not stated; maturity-wall figures that need it are not calculated."
)
PRE_D0_LIMITATION = (
    "Facility {fid} maturity date is before the balance date; maturity-wall figures that need it "
    "are not calculated."
)
FUNDING_GAP_ON_CASH_ALONE = (
    "The funding gap is not calculated because the revolver is undisclosed; the cash-only "
    "headroom over minimum cash is shown as a lower bound."
)
FUNDING_GAP_ON_CASH_ALONE_DRAWINGS = (
    "The funding gap is not calculated because the revolver drawings are undisclosed; the "
    "cash-only headroom over minimum cash is shown as a lower bound."
)
SCHEDULE_EMPTY_LIMITATION = (
    "The T4.18 facility schedule lists no facility; maturity-wall figures are not calculated."
)


def _known_nonzero(value: Num) -> Decimal | None:
    return value if not isinstance(value, Gap) and value != 0 else None


def _facility_limitations(f: Facility, balance_date: date) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    fid = f.facility_id
    if f.currency is not None and f.currency != CURRENCY:
        out.append(
            (
                f"Facility currency ({fid})",
                "Limitation",
                FX_LIMITATION.format(fid=fid, ccy=f.currency),
            )
        )
    terms: tuple[tuple[str, object], ...] = (
        ("maturity date", f.maturity_date),
        ("principal", f.principal),
        ("currency", f.currency),
        ("commitment", f.commitment),
        ("drawn amount", f.drawn_amount),
        ("annual amortisation", f.annual_amortisation),
    )
    for term, value in terms:
        if value is None:
            out.append(
                (
                    f"Facility {term} ({fid})",
                    "Gap",
                    TERM_LIMITATION.format(fid=fid, term=term),
                )
            )
        elif term == "maturity date" and _position_gap(f, balance_date) is not None:
            # Round 11: a stated date the Method cannot place is a Limitation, in this slot.
            text = PRE_D0_LIMITATION.format(fid=fid)
            out.append((f"Facility maturity date ({fid})", "Limitation", text))
    return out


def _limitations(*, operands: Operands, bridge: Bridge) -> tuple[tuple[str, str, str], ...]:
    """(T2E.7 label, kind, text) for each own limitation, in a fixed order."""
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
    if bridge.maturity_inside_horizon is True:
        out.append(("Interest after maturity", "Limitation", INTEREST_AFTER_MATURITY))
    difference = _known_nonzero(bridge.sources_and_uses_difference)
    if difference is not None:
        out.append(
            (
                "Sources and uses difference",
                "Limitation",
                SOURCES_AND_USES_DIFFER.format(amount=exact_amount_text(difference)),
            )
        )
    lines = _known_nonzero(bridge.financing_lines_difference)
    if lines is not None:
        out.append(
            (
                "Financing lines difference",
                "Limitation",
                FINANCING_LINES_DIFFER.format(amount=exact_amount_text(lines)),
            )
        )
    if isinstance(bridge.maturities_in_horizon, Gap) and (
        bridge.maturities_in_horizon.reason == SCHEDULE_EMPTY
    ):
        out.append(("Facility schedule", "Gap", SCHEDULE_EMPTY_LIMITATION))
    for f in bridge.ordered_facilities:
        out += _facility_limitations(f, bridge.balance_date)
    for label, text in check_cp1_totals(operands=operands, bridge=bridge):
        out.append((f"CP-1 {label} cross-check", "Limitation", text))
    if isinstance(bridge.undrawn_revolver, Gap):
        text = (
            FUNDING_GAP_ON_CASH_ALONE_DRAWINGS
            if bridge.undrawn_revolver.reason == DRAWINGS_UNDRAWN
            else FUNDING_GAP_ON_CASH_ALONE
        )
        out.append(("Funding gap on cash alone", "Limitation", text))
    return tuple(out)


def own_limitations(*, operands: Operands, bridge: Bridge) -> tuple[str, ...]:
    return tuple(text for _, _, text in _limitations(operands=operands, bridge=bridge))


# --- result types -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Cell:
    """One table fact. A gap or not_applicable cell's spelling needs the report's G number,
    assigned in Stage 2."""

    fact_id: str
    state: CellState
    shown: str | None
    amount: Decimal | None = None
    unit: str | None = None
    value_class: str | None = None
    cp1_operand: str | None = None
    cp1_unit: str | None = None
    reason: str | None = None
    # Round 13 (R1 M1): set in _num for a known numeric cell only. ``differing_periods`` holds
    # the operand periods of a sum or difference that disagree; _number raises on it (the cell's
    # fact id is assigned there) and no returned cell carries any.
    period: str | None = None
    differing_periods: tuple[str, ...] = ()

    def spell(self, *, gap_id: str | None = None) -> str:
        if self.state in ("gap", "conflicting"):
            return format_value(None, "amount", "gap", gap_id=gap_id)
        if self.state == "not_applicable":
            return format_value(None, "amount", "not_meaningful", gap_id=gap_id)
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
    """T2E.6 / T2E.7: one text column (ruling 2D8 fixes the row header and the column)."""

    table_id: str
    title: str
    row_header: str
    column: tuple[str, str]  # (field, label)
    rows: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ClaimText:
    """A claim: ``{id|US$ m}`` slots are resolved into ``text``; ``[id]`` chips name gap cells
    and stay in ``text`` until Stage 2 spells them with the report's G numbers."""

    claim_id: str
    template: str
    text: str
    references: tuple[str, ...]
    chips: tuple[str, ...]
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


_COPY_STATE: dict[OperandStatus, CellState] = {
    "known": "known",
    "missing": "gap",
    "conflicting": "conflicting",
    "not_applicable": "not_applicable",
}


def _gap_cell(
    gap: Gap,
    unit: str | None,
    value_class: str,
    cp1_operand: str | None = None,
    cp1_unit: str | None = None,
    *,
    copied: bool = False,
) -> Cell:
    """A gap or not_applicable cell carries its known twin's class, and a copied gap its
    ``cp1_operand`` and ``cp1_unit`` (round 13, R1 M1). A copy of a CP-1 operand keeps CP-1's
    status and limitation (R1 M3); every other cell takes the dependants' reason."""
    if copied and isinstance(gap, OperandGap):
        return Cell(
            "",
            _COPY_STATE[gap.status],
            None,
            unit=unit,
            value_class=value_class,
            cp1_operand=cp1_operand,
            cp1_unit=cp1_unit,
            reason=gap.limitation,
        )
    state: CellState = "gap" if gap.applicable else "not_applicable"
    return Cell(
        "",
        state,
        None,
        unit=unit,
        value_class=value_class,
        cp1_operand=cp1_operand,
        cp1_unit=cp1_unit,
        reason=gap.reason,
    )


def _num(
    value: Num,
    unit: str,
    value_class: str,
    balance: str,
    cp1_operand: str | None = None,
    cp1_unit: str | None = None,
    periods: tuple[str, ...] = (),
    *,
    copied: bool = False,
) -> Cell:
    """A numeric cell. Its ``period`` (round 13, R1 M1): the one period its CP-1 operands share
    (``periods``; a copy keeps it verbatim), else the balance date ``balance``."""
    if isinstance(value, Gap):
        return _gap_cell(value, unit, value_class, cp1_operand, cp1_unit, copied=copied)
    value = _ZERO if value == 0 else value
    shown = format_value(value, _UNIT_CLASS[unit], "known")
    shared = sorted(set(periods))
    return Cell(
        "",
        "known",
        shown,
        value,
        unit,
        value_class,
        cp1_operand,
        cp1_unit,
        period=shared[0] if len(shared) == 1 else balance if not shared else None,
        differing_periods=tuple(shared) if len(shared) > 1 else (),
    )


def _money(value: Num, balance: str, value_class: str = "calculated") -> Cell:
    return _num(value, "MILLIONS", value_class, balance)


def _copy(o: Operands, value: Num, value_class: str, operand: str, balance: str) -> Cell:
    """A copied CP-1 T4.5/T4.6 fact: own value class, unit currency normalised to MILLIONS,
    CP-1's period (the shared one for a sum), CP-1's status and limitation when not known."""
    return _num(
        value,
        "MILLIONS",
        value_class,
        balance,
        operand,
        _CP1_CURRENCY,
        _periods(o, operand),
        copied=True,
    )


def _text(shown: str | Gap, value_class: str, cp1_operand: str | None = None) -> Cell:
    if isinstance(shown, Gap):
        return _gap_cell(shown, None, value_class, cp1_operand)
    return Cell("", "known", shown, value_class=value_class, cp1_operand=cp1_operand)


def _months_cell(value: int | Decimal | Gap, value_class: str, balance: str) -> Cell:
    if isinstance(value, Gap):
        return _gap_cell(value, "months", value_class)
    return Cell(
        "", "known", _months_text(value), Decimal(value), "months", value_class, period=balance
    )


def _number(table_id: str, rows: list[tuple[str, list[Cell]]]) -> tuple[Row, ...]:
    """Assign fact ids T2E.<n>.rNN (one value column) or T2E.<n>.rNN.cK."""
    out = []
    for r, (label, cells) in enumerate(rows, 1):
        multi = len(cells) > 1
        named = []
        for c, cell in enumerate(cells, 1):
            fact_id = f"{table_id}.r{r:02d}" + (f".c{c}" if multi else "")
            if cell.differing_periods:
                raise ValueError(f"CP-2D: operands of {fact_id} differ in period")
            named.append(replace(cell, fact_id=fact_id))
        out.append(Row(label, tuple(named)))
    return tuple(out)


# --- tables -----------------------------------------------------------------------------------

RUNWAY_ROW = (
    "Months until cash reaches minimum cash from run-rate cash flow alone "
    "(excludes maturities and amortisation)"
)


def _t410(o: Operands, value: Num, operand: str, balance: str, unit: str = "MILLIONS") -> Cell:
    """A cell CP-2D recomputes and tags with the CP-1 T4.10 metric it cross-checks: it keeps
    that metric's period when CP-1 offers it."""
    return _num(value, unit, "calculated", balance, operand, periods=_periods(o, operand))


def _sources_and_uses(o: Operands, b: Bridge) -> Table:
    d0 = b.balance_date.isoformat()
    opening = add_months(b.balance_date, -12).isoformat()
    equity = _total(_op(o, "equity_issuance"), _op(o, "equity_repurchases"))
    rows: list[tuple[str, list[Cell]]] = [
        (
            f"Opening cash ({opening})",
            [_copy(o, _op(o, "opening_cash"), "calculated", "opening_cash", d0)],
        ),
        ("Operating cash flow", [_copy(o, _op(o, "cfo"), "calculated", "cfo", d0)]),
        (
            "Net cash used in investing",
            [_copy(o, _op(o, "investing"), "calculated", "investing", d0)],
        ),
        (
            "Net debt issued",
            [_copy(o, _op(o, "net_debt_issuance"), "calculated", "net_debt_issuance", d0)],
        ),
        (
            "Equity issuance and repurchases",
            [_copy(o, equity, "calculated", "equity_issuance+equity_repurchases", d0)],
        ),
        (
            "Dividends paid",
            [_copy(o, _op(o, "dividends_paid"), "calculated", "dividends_paid", d0)],
        ),
        (
            "Other investing and financing",
            [
                _copy(
                    o,
                    _op(o, "other_investing_financing"),
                    "calculated",
                    "other_investing_financing",
                    d0,
                )
            ],
        ),
        ("FX effect on cash", [_copy(o, _op(o, "fx_effect"), "calculated", "fx_effect", d0)]),
        ("Closing cash (calculated)", [_money(b.sources_and_uses_closing_cash_calculated, d0)]),
        (
            "Closing cash (reported)",
            [_copy(o, _op(o, "closing_cash"), "calculated", "closing_cash", d0)],
        ),
        ("Difference (calculated less reported)", [_money(b.sources_and_uses_difference, d0)]),
    ]
    return Table(
        "T2E.1",
        "Liquidity sources and uses",
        "Line",
        (f"Twelve months to {d0} (US$ m)",),
        _number("T2E.1", rows),
    )


def _position(o: Operands, b: Bridge) -> Table:
    d0 = b.balance_date.isoformat()
    undisclosed = _absent(o, "rcf_commitment")
    commitment: Num = Gap(REV_COMMITMENT) if undisclosed else _op(o, "rcf_commitment")
    drawn: Num = Gap(REV_DRAWN) if undisclosed and _absent(o, "rcf_drawn") else _op(o, "rcf_drawn")
    rows: list[tuple[str, list[Cell]]] = [
        ("Cash and cash equivalents", [_copy(o, _op(o, "cash_bs"), "source", "cash_bs", d0)]),
        ("Restricted cash", [_copy(o, _op(o, "restricted_cash"), "source", "restricted_cash", d0)]),
        ("Revolver commitment", [_copy(o, commitment, "source", "rcf_commitment", d0)]),
        ("Revolver drawn", [_copy(o, drawn, "source", "rcf_drawn", d0)]),
        (
            "Undrawn committed revolver",
            [_t410(o, b.undrawn_revolver, "undrawn_rcf", d0)],
        ),
        (
            "Undrawn term loan commitment (not counted as liquidity)",
            [
                _num(
                    b.undrawn_term_commitment,
                    "MILLIONS",
                    "calculated",
                    d0,
                    "T4.18 commitment - drawn_amount",
                    periods=tuple(f.period for f in b.ordered_facilities),
                )
            ],
        ),
        (
            "Available liquidity",
            [_t410(o, b.available_liquidity, "liquidity", d0)],
        ),
        ("Total debt", [_copy(o, _op(o, "total_debt_bs"), "source", "total_debt_bs", d0)]),
        (
            "Liquidity to total debt",
            [_t410(o, b.liquidity_to_total_debt, "liquidity_to_debt", d0, "PERCENT")],
        ),
    ]
    return Table(
        "T2E.2",
        "Liquidity position",
        "Line",
        (f"{b.balance_date.isoformat()} (US$ m)",),
        _number("T2E.2", rows),
    )


def _runway_cell(b: Bridge) -> Cell:
    d0 = b.balance_date.isoformat()
    if b.runway_state == "not_reached":
        return Cell("", "known", "Not reached at run rate", unit="months", value_class="calculated")
    if b.runway_state == "months":
        assert b.months_to_minimum_cash is not None
        return _months_cell(b.months_to_minimum_cash, "calculated", d0)
    assert b.runway_reason is not None
    return _gap_cell(Gap(b.runway_reason), "months", "calculated")


def _runway_table(b: Bridge) -> Table:
    d0 = b.balance_date.isoformat()
    rows: list[tuple[str, list[Cell]]] = [
        (
            "Run-rate net cash flow before new borrowing, per year",
            [_money(b.run_rate_net_cash_flow_annual, d0)],
        ),
        (
            "Run-rate net cash flow before new borrowing, per month",
            [_money(b.run_rate_net_cash_flow_monthly, d0)],
        ),
        ("Horizon (analyst judgment)", [_months_cell(b.horizon_months, "analyst_judgment", d0)]),
        ("Horizon end date", [_text(b.horizon_end.isoformat(), "calculated")]),
        ("Run-rate net cash flow over the horizon", [_money(b.run_rate_net_cash_flow_horizon, d0)]),
        # Outflows are shown negative (method_rules.table_signs).
        (
            "Scheduled amortisation inside the horizon",
            [_money(_neg(b.amortisation_in_horizon), d0)],
        ),
        ("Maturities inside the horizon", [_money(_neg(b.maturities_in_horizon), d0)]),
        (
            "Cash at horizon end before refinancing",
            [_money(b.cash_at_horizon_end_before_refinancing, d0)],
        ),
        (RUNWAY_ROW, [_runway_cell(b)]),
    ]
    return Table("T2E.3", "Cash runway", "Line", ("Value",), _number("T2E.3", rows))


def _wall_table(b: Bridge) -> Table:
    d0 = b.balance_date.isoformat()
    rows: list[tuple[str, list[Cell]]] = []
    for w in b.wall:
        f = w.facility
        dated = w.maturity_date
        inside = w.inside_horizon
        rows.append(
            (
                f"{f.name} ({f.facility_id})",
                [
                    _num(
                        w.principal,
                        "MILLIONS",
                        "source",
                        d0,
                        "T4.18 principal",
                        periods=(f.period,),
                    ),
                    _text(
                        dated if isinstance(dated, Gap) else dated.isoformat(),
                        "source",
                        "T4.18 maturity_date",
                    ),
                    _months_cell(w.months_to_maturity, "calculated", d0),
                    _text(
                        inside if isinstance(inside, Gap) else ("Yes" if inside else "No"),
                        "calculated",
                    ),
                    _num(w.share_of_total_debt, "PERCENT", "calculated", d0),
                    _num(w.cumulative_share, "PERCENT", "calculated", d0),
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


def _funding_table(o: Operands, b: Bridge) -> Table:
    d0 = b.balance_date.isoformat()
    minimum: Num = Gap(MINIMUM_NOT_ASSESSED_CELL) if b.minimum_cash is None else b.minimum_cash
    rows: list[tuple[str, list[Cell]]] = [
        (
            "Cash at horizon end before refinancing",
            [_money(b.cash_at_horizon_end_before_refinancing, d0)],
        ),
        (
            "Undrawn committed revolver",
            [_t410(o, b.undrawn_revolver, "undrawn_rcf", d0)],
        ),
        ("Resources at horizon end", [_money(b.resources_at_horizon_end, d0)]),
        ("Minimum cash (analyst judgment)", [_money(minimum, d0, "analyst_judgment")]),
        (
            "Cash-only headroom over minimum cash (excludes any revolver)",
            [_money(b.cash_only_headroom, d0)],
        ),
        ("Headroom over minimum cash", [_money(b.headroom, d0)]),
        ("Funding gap", [_money(b.funding_gap, d0)]),
    ]
    return Table("T2E.5", "Funding gap", "Line", ("Value (US$ m)",), _number("T2E.5", rows))


# --- claims (lease "Submission schema"; rulings 2D2, 2D5, 2D-b) --------------------------------

LIQ_UNDISCLOSED = (
    "Available liquidity at {d} is not calculated: [T2E.2.r07] needs the undrawn committed "
    "revolver, which is undisclosed; cash is {cash}."
)
LIQ_DRAWINGS = (
    "Available liquidity at {d} is not calculated: [T2E.2.r07] needs the revolver drawings, "
    "which are undisclosed; cash is {cash}."
)
GAP_UNDISCLOSED = (
    "The funding gap is not calculated because the revolver is undisclosed; cash-only headroom "
    "over the assumed minimum cash is {headroom}."
)
GAP_DRAWINGS = (
    "The funding gap is not calculated because the revolver drawings are undisclosed; cash-only "
    "headroom over the assumed minimum cash is {headroom}."
)
# Ruling L5: claims name no facility id.
MAT_FX = (
    "The cash outflow from debt maturing inside the horizon is not calculated: [T2E.3.r07] needs "
    "every facility in USD, and one is not; no FX conversion is applied."
)
# Round 6f (d): an unstated currency does not prove "one is not" in USD; MAT_FX needs a stated
# foreign currency.
MAT_CURRENCY = (
    "The cash outflow from debt maturing inside the horizon is not calculated: [T2E.3.r07] needs "
    "every facility with its currency stated, and one is not; no FX conversion is applied."
)
# Ruling D-2 forms 3 (with L5) and 4.
GAP_FACILITY = "The funding gap is not calculated: [T2E.5.r07] needs every facility {cause}."
# Round 11: the pre-D0 cause in the L5 frame, in the maturity date's slot.
PRE_D0_CAUSE = "to mature on or after the balance date, and one does not"
GAP_OPERAND = (
    "The funding gap is not calculated: [T2E.5.r07] needs {label}, which is "
    "{state}."  # state: missing, conflicting or not applicable (round 13, R1 M3)
)
# Form 4 labels for the schedule itself; no ruling fixes them (reported to LEAD). They omit
# "T4.18": a claim's literal text may carry no bare figure (prose.bare_figures).
SCHEDULE_LABELS = {
    SCHEDULE_MISSING: "the facility schedule",
    SCHEDULE_EMPTY: "a facility in the facility schedule",
}
# The gap's operands in formula order: cash at horizon end, then the revolver (form 5).
_GAP_OPERANDS = ("cash_bs", "cfo", "investing", "financing", "net_debt_issuance")
GAP_NOT_ASSESSED = "The funding gap is not calculated: the minimum cash has not been assessed."


class _Claims:
    """Writes claims with ``{id|US$ m}`` slots for known cells and ``[id]`` chips for gaps."""

    def __init__(self, tables: tuple[Table, ...]) -> None:
        self.cells = {c.fact_id: c for t in tables for r in t.rows for c in r.cells}

    def slot(self, fact_id: str) -> str:
        cell = self.cells[fact_id]
        if cell.state != "known":
            return f"[{fact_id}]"
        if cell.unit != "MILLIONS":
            raise ValueError(f"A claim may reference only a US$ m cell: {fact_id}")
        return "{" + fact_id + "|US$ m}"

    def known(self, fact_id: str) -> bool:
        return self.cells[fact_id].state == "known"

    def claim(self, claim_id: str, template: str, cites: tuple[str, ...]) -> ClaimText:
        refs: list[str] = []
        chips: list[str] = []
        text = template
        for fact_id, cell in self.cells.items():
            slot = "{" + fact_id + "|US$ m}"
            if slot in template:
                refs.append(fact_id)
                text = text.replace(slot, f"{cell.shown} US$ m")
            if f"[{fact_id}]" in template:
                chips.append(fact_id)
        order = sorted(refs, key=lambda r: template.index("{" + r + "|"))
        chip_order = sorted(chips, key=lambda r: template.index(f"[{r}]"))
        return ClaimText(
            claim_id, template, text, tuple(order), tuple(chip_order), cites + tuple(order)
        )


def _currency_facility(b: Bridge) -> Facility | None:
    return next((f for f in b.ordered_facilities if _currency_gap(f) is not None), None)


def _facility_cause(f: Facility, balance_date: date, horizon_end: date) -> str | None:
    """Ruling D-2 form 3: what a facility lacks for the funding gap, in the ruled order (FX,
    currency, maturity date (unstated, or before D0: round 11), principal; annual amortisation
    when it matures after the horizon)."""
    if f.currency is not None and f.currency != CURRENCY:
        need = "in USD"
    elif f.currency is None:
        need = "with its currency stated"
    elif f.maturity_date is None:
        need = "with its maturity date stated"
    elif f.maturity_date < balance_date:
        return PRE_D0_CAUSE
    elif f.principal is None:
        need = "with its principal stated"
    elif f.annual_amortisation is None and f.maturity_date > horizon_end:
        need = "with its annual amortisation stated"
    else:
        return None
    return f"{need}, and one is not"


def _gap_missing(o: Operands, b: Bridge) -> str | None:
    """Forms 3 and 4 of ruling D-2 for a missing funding gap, or None for the revolver form."""
    for f in b.ordered_facilities:
        cause = _facility_cause(f, b.balance_date, b.horizon_end)
        if cause is not None:
            return GAP_FACILITY.format(cause=cause)
    for name in _GAP_OPERANDS:
        operand = _operand(o, name)
        if operand is None or operand.status != "known":
            status: OperandStatus = "missing" if operand is None else operand.status
            return GAP_OPERAND.format(label=OPERAND_LABELS[name], state=STATE_WORD[status])
    schedule = b.maturities_in_horizon
    if isinstance(schedule, Gap) and schedule.reason in SCHEDULE_LABELS:
        return GAP_OPERAND.format(label=SCHEDULE_LABELS[schedule.reason], state="missing")
    return None


def _claims(o: Operands, b: Bridge, tables: tuple[Table, ...]) -> tuple[ClaimText, ...]:
    c = _Claims(tables)
    d0 = format_date(b.balance_date)
    revolver = b.undrawn_revolver
    drawings = isinstance(revolver, Gap) and revolver.reason == DRAWINGS_UNDRAWN
    if isinstance(revolver, Gap) and not c.known("T2E.2.r07"):
        form = LIQ_DRAWINGS if drawings else LIQ_UNDISCLOSED
        liquidity = form.format(d=d0, cash=c.slot("T2E.2.r01"))
    else:
        liquidity = (
            f"Available liquidity at {d0} is {c.slot('T2E.2.r07')} (cash {c.slot('T2E.2.r01')} "
            f"plus undrawn committed revolver {c.slot('T2E.2.r05')})."
        )
    foreign = _currency_facility(b)
    if foreign is not None:
        maturities = MAT_CURRENCY if foreign.currency is None else MAT_FX
    else:
        maturities = (
            f"The cash outflow from debt maturing inside the horizon is {c.slot('T2E.3.r07')} "
            f"against total debt of {c.slot('T2E.2.r08')}."
        )
    out = [
        c.claim("CP-2D-LIQ-01", liquidity, ("cash_closing", "undrawn_rcf", "liquidity")),
        c.claim(
            "CP-2D-RUN-01",
            f"Run-rate net cash flow before new borrowing is {c.slot('T2E.3.r01')} a year on the "
            f"twelve months to {d0}; cash at the end of the assessed horizon before any "
            f"refinancing is {c.slot('T2E.3.r08')}.",
            ("cfo", "investing", "financing", "net_debt_issuance", "cash_bs"),
        ),
        c.claim(
            "CP-2D-MAT-01",
            maturities,
            ("T4.18 principal", "T4.18 maturity_date", "total_debt"),
        ),
    ]
    gap_cites = ("cash_bs", "undrawn_rcf")
    if b.minimum_cash is None:
        out.append(c.claim("CP-2D-GAP-01", GAP_NOT_ASSESSED, ()))
    elif not isinstance(b.funding_gap, Gap) and b.funding_gap == 0:
        template = (
            f"Resources at the horizon end exceed the assumed minimum cash by "
            f"{c.slot('T2E.5.r06')}; no funding gap arises."
        )
        out.append(c.claim("CP-2D-GAP-01", template, gap_cites))
    elif not isinstance(b.funding_gap, Gap):
        gap = c.slot("T2E.5.r07")
        template = (
            f"Resources at the horizon end fall short of the assumed minimum cash by {gap}; "
            f"a funding gap of {gap} arises."
        )
        out.append(c.claim("CP-2D-GAP-01", template, gap_cites))
    else:
        # Form 5 (the revolver) is reached only when forms 3 and 4 find nothing, so cash at the
        # horizon end, and with it T2E.5.r05, is known there.
        missing = _gap_missing(o, b)
        form = GAP_DRAWINGS if drawings else GAP_UNDISCLOSED
        template = missing or form.format(headroom=c.slot("T2E.5.r05"))
        out.append(c.claim("CP-2D-GAP-01", template, gap_cites))
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
    return Ledger("T2E.6", "Analyst judgments", "Judgment", ("value", "Value"), rows)


def compute(inputs: Cp2dInputs) -> Cp2dResult:
    """Tables T2E.1-T2E.7, own limitations, claims and status.

    Raises ValueError only for a submission that ``submission_issues`` refuses; every missing
    operand, facility term, currency or cross-check difference settles as gaps and limitations.
    """
    o = inputs.operands
    issues = submission_issues(
        submission=inputs.submission,
        offered_refs=inputs.offered_refs,
        maturity_date_refs=inputs.maturity_date_refs,
    )
    if issues:
        raise ValueError("; ".join(issues))
    bridge = bridge_of(inputs)
    limitations = _limitations(operands=o, bridge=bridge)
    tables = (
        _sources_and_uses(o, bridge),
        _position(o, bridge),
        _runway_table(bridge),
        _wall_table(bridge),
        _funding_table(o, bridge),
    )
    return Cp2dResult(
        bridge=bridge,
        tables=tables,
        judgments=_judgments(bridge, inputs.submission),
        gaps_ledger=Ledger(
            "T2E.7",
            "Gaps ledger",
            "Item",
            ("kind", "Kind"),
            tuple((label, kind) for label, kind, _ in limitations),
        ),
        own_limitations=tuple(text for _, _, text in limitations),
        claims=_claims(o, bridge, tables),
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
WALL_DATE_ISSUE = "the maturity_wall assessment must cite T4.18 maturity_date"

# Rulings 2D1/2D-a: the oracle builder's FORBIDDEN list (build.py:390-392) is the closed list,
# matched as case-insensitive substrings over the analyst's submitted text fields only. The
# over-match inside other words ("buyer") is a recorded guard limit.
FORBIDDEN = (
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


EMPTY_TEXT = "{path}: empty text"
"""Round 11 (LEAD rulings, "Blank text is one defect class"): no CP-2D frame is pinned, so the
fallback frame. A `Text` field's schema refusal of "" stands; this catches whitespace-only text,
where round 12 B10 counts Unicode format (`Cf`) characters as blank (`owners.blank.is_blank`)."""


def analyst_text_fields(submission: LiquidityBridgeSubmission) -> list[tuple[str, str]]:
    """(path, text) of the analyst's submitted text fields, in submission order (2D-a: the
    builder's check, build.py:393-401). Paths are 0-based."""
    fields: list[tuple[str, str]] = []
    for i, a in enumerate(submission.assessments):
        fields.append((f"assessments[{i}].text", a.text))
        fields.append((f"assessments[{i}].credit_implication", a.credit_implication))
        if a.limitation is not None:
            fields.append((f"assessments[{i}].limitation", a.limitation))
    if submission.minimum_cash is not None:
        fields.append(("minimum_cash.rationale", submission.minimum_cash.rationale))
    absence = submission.minimum_cash_absence
    if absence is not None:
        fields += [
            ("minimum_cash_absence.reason", absence.reason),
            ("minimum_cash_absence.follow_up", absence.follow_up),
        ]
    return fields


def submission_issues(
    *,
    submission: LiquidityBridgeSubmission,
    offered_refs: frozenset[str],
    maturity_date_refs: frozenset[str],
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
    fields = analyst_text_fields(s)
    issues += [EMPTY_TEXT.format(path=path) for path, text in fields if is_blank(text)]
    texts = [text for _, text in fields]
    if any(ch.isdigit() for t in texts for ch in t):
        issues.append(DIGIT_ISSUE)
    if any(stem in t.lower() for t in texts for stem in FORBIDDEN):
        issues.append(CONCLUSION_ISSUE)
    refs = [r for a in s.assessments for r in a.basis_refs]
    if s.minimum_cash is not None:
        refs += s.minimum_cash.basis_refs
    if any(r not in offered_refs for r in refs):
        issues.append(BASIS_ISSUE)
    for a in s.assessments:
        if a.section == "maturity_wall" and not maturity_date_refs & set(a.basis_refs):
            issues.append(WALL_DATE_ISSUE)
    for a in s.assessments:
        carried = a.limitation is not None
        stated = a.limitation is not None and not is_blank(a.limitation)
        insufficient = a.category == "Insufficient Information"
        if insufficient and not stated:
            issues.append(INSUFFICIENT_ISSUE)
        if carried and not insufficient:
            issues.append(LIMITATION_ISSUE)
    return tuple(dict.fromkeys(issues))
