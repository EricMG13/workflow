"""EV/EBITDA admission, statistics and basis selection (Phase 7, Design 3-6).

Pure arithmetic, no I/O. Every operation runs in CP-1C's 38-digit half-even context; the oracle is
`cases/valuation-context-owner/expected.json`. A gap is a `None` multiple with a reason: no path
returns zero (or any other amount) in place of a value that cannot be calculated.
"""

import calendar
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, localcontext

from deploy_workflow.context import IssuerMarket, UserMultiple
from deploy_workflow.owners import cp1c

CTX = cp1c.CTX
MIN_ADMITTED = cp1c.MIN_INCLUDED_PEERS
PEER_MONTHS = 12
PRECEDENT_MONTHS = 36
# CP-4C's multiple field allows two digits and two decimals (`cp4c.py` MULTIPLE_PATTERN).
MAX_MULTIPLE = Decimal("99.99")
MIN_MULTIPLE = Decimal("0.01")
# Above this a value cannot be rounded to 2 dp inside the 38-digit context; it is over the limit anyway.
UNROUNDABLE = Decimal(10) ** 30
CENTS = Decimal("0.01")
TENTHS = Decimal("0.1")

INCLUDED = "Included"
INSUFFICIENT = "Insufficient Information"
NOT_STATED = "Not stated by the user"
NTM_GAP = "NTM needs a forecast EBITDA that CP-1C does not read"
EBITDA_GAP = "CP-1 LTM adjusted EBITDA is not a known positive amount"
EV_ZERO = "Excluded: enterprise value is zero"
EV_NEGATIVE = "Excluded: enterprise value is negative"
NOT_FINITE = "Excluded: enterprise value or EBITDA is not a finite number"
EBITDA_NOT_POSITIVE = "Excluded: EBITDA is not above zero"
NTM_NOT_APPLIED = "an NTM multiple is not applied to LTM EBITDA"
NO_DATE = "Excluded: no deal date, the window cannot be checked"

PUBLIC, PRECEDENTS, BLEND = "public_comps", "precedents", "blend"
ISSUER, USER, AUTO = "issuer_trading", "user_multiple", "auto"


@dataclass(frozen=True)
class AdmittedRecord:
    origin: str  # user_comps now; cp_dr_public when O7d lands
    kind: str  # "peer" or "precedent"
    name: str
    figures_date: date | None
    source: str
    ev: Decimal
    ebitda: Decimal


@dataclass(frozen=True)
class Admission:
    record: AdmittedRecord
    multiple: Decimal | None  # exact EV / EBITDA when both are above zero, admitted or not
    included: bool
    reason: str  # "Included" or "Excluded: <why>"


@dataclass(frozen=True)
class SetStats:
    n_total: int
    n_admitted: int
    minimum: Decimal | None
    median: Decimal | None
    maximum: Decimal | None
    outliers: int | None  # None while the median is missing


@dataclass(frozen=True)
class Selection:
    requested: str
    selected_basis: str | None
    multiple: Decimal | None
    reason: str
    ebitda_basis: str
    implied_ev: Decimal | None


# --- admission ------------------------------------------------------------------------------------


def window_start(as_of: date, months: int) -> date:
    """as_of counted back by calendar months, same day, clamped to the month end."""
    index = as_of.year * 12 + (as_of.month - 1) - months
    year, month = divmod(index, 12)
    month += 1
    day = min(as_of.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _value_refusal(record: AdmittedRecord) -> str | None:
    if not (record.ev.is_finite() and record.ebitda.is_finite()):
        return NOT_FINITE
    if record.ev == 0:
        return EV_ZERO
    if record.ev < 0:
        return EV_NEGATIVE
    if record.ebitda <= 0:
        return EBITDA_NOT_POSITIVE
    return None


def _window_refusal(record: AdmittedRecord, start: date, months: int) -> str | None:
    if record.figures_date is None:
        return NO_DATE
    if record.figures_date >= start:
        return None
    what = "deal dated" if record.kind == "precedent" else "figures dated"
    verb = "is" if record.kind == "precedent" else "are"
    return f"Excluded: {what} {record.figures_date} {verb} before {start} ({months}-month limit)"


def admit(records: Sequence[AdmittedRecord], as_of: date, months: int) -> tuple[Admission, ...]:
    start = window_start(as_of, months)
    return tuple(_admit_one(r, start, months) for r in records)


def _admit_one(record: AdmittedRecord, start: date, months: int) -> Admission:
    refusal = _value_refusal(record)
    multiple = None if refusal else CTX.divide(record.ev, record.ebitda)
    refusal = refusal or _window_refusal(record, start, months)
    return Admission(record, multiple, refusal is None, refusal or INCLUDED)


# --- statistics -----------------------------------------------------------------------------------


def _included(admissions: Sequence[Admission]) -> list[Decimal]:
    return [a.multiple for a in admissions if a.included and a.multiple is not None]


def stats(admissions: Sequence[Admission]) -> SetStats:
    values = _included(admissions)
    median = cp1c.peer_median(values)
    return SetStats(
        n_total=len(admissions),
        n_admitted=len(values),
        minimum=min(values) if values else None,
        median=median,
        maximum=max(values) if values else None,
        outliers=None if median is None else _outlier_count(values, median),
    )


def _outlier_count(values: Sequence[Decimal], median: Decimal) -> int:
    flags = (cp1c.outlier(v, median) for v in values)
    return sum(1 for f in flags if f is not None and f[1] == "Outlier")


# --- selection ------------------------------------------------------------------------------------


def _two_dp(value: Decimal) -> Decimal:
    return CTX.quantize(value, CENTS)  # ROUND_HALF_EVEN from the context


def _one_dp(value: Decimal) -> str:
    """Display rule (half-up, 1 dp), computed in CTX. Too large to round: shown unrounded."""
    if value.copy_abs() >= UNROUNDABLE:
        return format(value, "f")
    with localcontext(CTX):
        return str(value.quantize(TENTHS, rounding=ROUND_HALF_UP))


def _shown_two_dp(value: Decimal) -> str:
    """Display rule (half-up, 2 dp) as T1C.10 shows a multiple; the selection itself is half-even."""
    if value.copy_abs() >= UNROUNDABLE:
        return format(value, "f")
    with localcontext(CTX):
        return str(value.quantize(CENTS, rounding=ROUND_HALF_UP))


def _limit_reason(shown: str, edge: str, limit: Decimal) -> str:
    return f"the selected multiple {shown} is {edge} the {limit} limit of the CP-4C field; no multiple is selected"


def _gap(
    requested: str, basis: str | None, reason: str, ebitda_basis: str = NOT_STATED
) -> Selection:
    return Selection(requested, basis, None, reason, ebitda_basis, None)


def _chosen(
    requested: str,
    basis: str,
    value: Decimal,
    reason: str,
    issuer_ebitda: Decimal | None,
    ebitda_basis: str = NOT_STATED,
) -> Selection:
    """A selected multiple (rounded half-even to 2 dp) and its implied EV; never clamped."""
    if value >= UNROUNDABLE:  # cannot be rounded in CTX, and is far over the limit
        return _gap(
            requested, basis, _limit_reason(str(value), "above", MAX_MULTIPLE), ebitda_basis
        )
    multiple = _two_dp(value)
    if multiple > MAX_MULTIPLE:
        return _gap(
            requested, basis, _limit_reason(str(multiple), "above", MAX_MULTIPLE), ebitda_basis
        )
    if multiple < MIN_MULTIPLE:  # rounds to 0.00: CP-4C refuses a zero multiple
        return _gap(
            requested, basis, _limit_reason(str(multiple), "below", MIN_MULTIPLE), ebitda_basis
        )
    if ebitda_basis == "NTM":  # an NTM multiple is not applied to LTM EBITDA
        return Selection(requested, basis, multiple, reason, ebitda_basis, None)
    if issuer_ebitda is None or issuer_ebitda <= 0:
        reason = f"{reason}; implied EV not calculable: {EBITDA_GAP}"
        return Selection(requested, basis, multiple, reason, ebitda_basis, None)
    return Selection(
        requested, basis, multiple, reason, ebitda_basis, CTX.multiply(multiple, issuer_ebitda)
    )


def _thin(label: str, s: SetStats) -> str:
    return f"{label} {s.n_admitted} admitted of {MIN_ADMITTED} required"


def _median_selection(
    requested: str, basis: str, s: SetStats, noun: str, months: int, ebitda: Decimal | None
) -> Selection:
    if s.median is None:
        return _gap(
            requested,
            None,
            f"requested {basis}, {s.n_admitted} admitted of {MIN_ADMITTED} required; no fallback",
        )
    reason = f"{basis}: median of {s.n_admitted} admitted {noun} ({months}-month window)"
    return _chosen(requested, basis, s.median, reason, ebitda)


def _auto(pub: SetStats, prec: SetStats, ebitda: Decimal | None) -> Selection:
    if pub.median is not None:
        reason = f"auto: public comps, {pub.n_admitted} admitted of {MIN_ADMITTED} required ({PEER_MONTHS}-month window)"
        return _chosen(AUTO, PUBLIC, pub.median, reason, ebitda)
    if prec.median is not None:
        reason = f"auto: precedents, {prec.n_admitted} admitted of {MIN_ADMITTED} required ({PRECEDENT_MONTHS}-month window)"
        return _chosen(AUTO, PRECEDENTS, prec.median, reason, ebitda)
    reason = (
        f"auto: {_thin('public comps', pub)} ({PEER_MONTHS}-month window); "
        f"{_thin('precedents', prec)} ({PRECEDENT_MONTHS}-month window); no multiple is selected"
    )
    return _gap(AUTO, INSUFFICIENT, reason)


def _blend(pub: SetStats, prec: SetStats, ebitda: Decimal | None) -> Selection:
    if pub.median is None or prec.median is None:
        short = [
            _thin(label, s)
            for label, s in (("public comps", pub), ("precedents", prec))
            if s.median is None
        ]
        return _gap(BLEND, None, f"requested blend, {', '.join(short)}; no fallback")
    average = CTX.divide(CTX.add(pub.median, prec.median), Decimal(2))
    reason = (
        f"blend: plain average of the public comps median {_shown_two_dp(pub.median)} "
        f"and the precedents median {_shown_two_dp(prec.median)}"
    )
    return _chosen(BLEND, BLEND, average, reason, ebitda)


def _issuer_ev(market: IssuerMarket) -> tuple[Decimal, str]:
    """(EV, how it was stated): `ev_m` wins when given, else market cap plus net debt."""
    if market.ev_m:
        return Decimal(market.ev_m), f"enterprise value {_one_dp(Decimal(market.ev_m))} (stated"
    ev = CTX.add(Decimal(market.market_cap_m), Decimal(market.net_debt_m))
    return (
        ev,
        f"enterprise value {_one_dp(ev)} (market cap {market.market_cap_m} plus net debt {market.net_debt_m}",
    )


def _issuer(market: IssuerMarket | None, ebitda: Decimal | None) -> Selection:
    if market is None:
        return _gap(ISSUER, ISSUER, "no issuer market data is in the context")
    if market.ebitda_basis == "NTM":
        return _gap(ISSUER, ISSUER, NTM_GAP, market.ebitda_basis)
    if ebitda is None or ebitda <= 0:
        return _gap(ISSUER, ISSUER, EBITDA_GAP, market.ebitda_basis)
    ev, how = _issuer_ev(market)
    if ev <= 0:
        return _gap(ISSUER, ISSUER, f"the issuer's {how}) is not above zero", market.ebitda_basis)
    reason = (
        f"{ISSUER}: {how}, as of {market.as_of}) over CP-1 LTM adjusted EBITDA {_one_dp(ebitda)}"
    )
    return _chosen(ISSUER, ISSUER, CTX.divide(ev, ebitda), reason, ebitda, market.ebitda_basis)


def _user(user: UserMultiple | None, ebitda: Decimal | None) -> Selection:
    if user is None or not user.value:
        return _gap(USER, USER, "no user multiple is in the context")
    value = Decimal(user.value)
    if value <= 0:
        return _gap(USER, USER, "the user multiple is not above zero", user.basis)
    reason = f"user-supplied ({user.basis} basis)"
    if user.rationale:
        reason += f"; rationale: {user.rationale}"
    if user.basis == "NTM":
        reason += f"; implied EV not calculable: {NTM_NOT_APPLIED}"
    return _chosen(USER, USER, value, reason, ebitda, user.basis)


def select_basis(
    requested: str,
    public: Sequence[Admission],
    precedents: Sequence[Admission],
    issuer: IssuerMarket | None,
    user: UserMultiple | None,
    issuer_ebitda: Decimal | None,
) -> Selection:
    pub, prec = stats(public), stats(precedents)
    if requested == AUTO:
        return _auto(pub, prec, issuer_ebitda)
    if requested == PUBLIC:
        return _median_selection(requested, PUBLIC, pub, "public comps", PEER_MONTHS, issuer_ebitda)
    if requested == PRECEDENTS:
        return _median_selection(
            requested, PRECEDENTS, prec, "precedents", PRECEDENT_MONTHS, issuer_ebitda
        )
    if requested == BLEND:
        return _blend(pub, prec, issuer_ebitda)
    if requested == ISSUER:
        return _issuer(issuer, issuer_ebitda)
    if requested == USER:
        return _user(user, issuer_ebitda)
    raise ValueError(f"Unknown valuation basis: {requested!r}")
