"""CP-4C (restructuring fulcrum): the module's pure calculation (Stage 1).

Lease: docs/CP4C-OWNER-LEASE.md; oracle cases/cp4c-owner. From the CP-1 twelve-month total debt
and EBITDA, the term loan's CP-1 T4.18 security and seniority, the CP-2G forecast EBITDA, the
CP-2A scenario CP-2G applied, three CP-4 legal facts, the cited balance-sheet rows and the
analyst's ranks, multiples, fulcrum and plan judgments, Python computes the enterprise value of
three valuations, the strict-priority waterfall by claim rank, recovery per class, attachment
and detachment multiples, the value break and totals, and composes tables T4E.1-T4E.10, the four
reference tables, the claims and the own limitations.

Missing is never 0: every value is known, missing (with its root reason), not applicable or
conflicting. Sums, products and differences of exact values run in the 38-digit half-even context
with the Inexact trap (exact; more digits fail closed, round 8 A-2 #13); each ratio is one
division in that context (the correctly rounded rational). A partly paid rank shares its payment
by exact largest remainder (round 8 A-1) and T4E.9 adds exactly. Where neither the lease, the
rulings nor the oracle pins the wording an outcome needs, the code fails closed with ValueError.

Nothing here does I/O or touches a store, host, session or renderer. Connection, tool-use and
orchestration seams (G1-X protocol section 2) are added to this file in later stages.
"""

import math
import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Decimal, Inexact, localcontext
from fractions import Fraction
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, ValidationError

from deploy_vii import prose
from deploy_vii.business_context import (
    Category,
    Confidence,
    Quote,
    Severity,
    prohibited_issues,
)
from deploy_vii.contracts import Citation, Contract, Fact, Input, InputStatus, RunText
from deploy_vii.execution import bounded_issues, clipped
from deploy_vii.live.schema import exact_json, json_object
from deploy_vii.model._cells import CONTEXT
from deploy_vii.preparation import PreparedPack
from deploy_vii.readiness import shape_issues
from deploy_vii.report_view import fact_spelling
from deploy_workflow.owners.blank import is_blank

MODULE_ID = "CP-4C"
STEP_ID = "restructuring_fulcrum"
SCHEMA_VERSION = "restructuring-fulcrum/1"

# --- arithmetic contexts (lease "Decimal composer") -------------------------------------------
_RATIO = CONTEXT.copy()  # 38 digits, ROUND_HALF_EVEN: one division of exact decimals
_EXACT = CONTEXT.copy()  # the same context with the Inexact trap: a rounded sum or product raises
_EXACT.traps[Inexact] = True

# --- the submission schema (lease "Submission schema"; every field required) -----------------
CLASS_ID_PATTERN = r"^c[0-9]{2}$"
CASE_ID_PATTERN = r"^v[0-9]{2}$"
FULCRUM_ID_PATTERN = r"^(c[0-9]{2}|equity)$"
RANK_PATTERN = r"^[1-9]$"
MULTIPLE_PATTERN = r"^([0-9]{1,2}(\.[0-9]{1,2})?|not assessed)$"
NOT_ASSESSED = "not assessed"
EQUITY = "equity"

ClaimKind = Literal["secured_debt", "unsecured_trade", "other_liability", "administrative_priority"]
AmountSource = Literal["cp1_total_debt", "source_row", "not_stated"]
EbitdaCase = Literal["base", "down"]
ForecastYear = Literal["FY2026", "FY2027", "FY2028"]
TreatmentKind = Literal[
    "Paid in full",
    "Receives reorganised equity",
    "Equity retained",
    "No recovery",
    "Not determined",
]


class ClaimClass(Contract):
    class_id: Annotated[str, Field(pattern=CLASS_ID_PATTERN)]
    name: str
    kind: ClaimKind
    rank: Annotated[str, Field(pattern=RANK_PATTERN)]
    amount_source: AmountSource
    amount_quote: Quote | None  # the financial statement row a source_row class reads
    period_column: str | None  # the column of that row
    support: tuple[Quote, ...] = Field(max_length=2)  # no default: still required
    rationale: str
    category: Category
    limitation: str | None


class Valuation(Contract):
    case_id: Annotated[str, Field(pattern=CASE_ID_PATTERN)]
    label: str
    ebitda_case: EbitdaCase
    ebitda_year: ForecastYear
    multiple: Annotated[str, Field(pattern=MULTIPLE_PATTERN)]
    rationale: str
    category: Category
    limitation: str | None


class FulcrumJudgment(Contract):
    case_id: str
    class_ids: tuple[Annotated[str, Field(pattern=FULCRUM_ID_PATTERN)], ...] = Field(max_length=4)
    rationale: str
    category: Category
    limitation: str | None


class Treatment(Contract):
    class_id: str
    treatment: TreatmentKind


class PlanJudgment(Contract):
    case_id: str
    treatments: tuple[Treatment, ...] = Field(min_length=2, max_length=7)
    rationale: str
    category: Category
    limitation: str | None


class Assessment(Contract):
    rationale: str
    category: Category
    confidence: Confidence
    limitation: str | None


class SynthesisGap(Contract):
    """CP-4C's own gap row: the CP-2G `SynthesisGap` shape (lease)."""

    gap: str
    why_it_matters: str
    affected_analysis: str
    severity: Severity
    action: str


class RestructuringSubmission(Contract):
    claims: tuple[ClaimClass, ...] = Field(min_length=2, max_length=6)
    valuation: tuple[Valuation, ...] = Field(min_length=3, max_length=3)
    fulcrum: tuple[FulcrumJudgment, ...] = Field(min_length=3, max_length=3)
    plan: tuple[PlanJudgment, ...] = Field(min_length=3, max_length=3)
    assessment: Assessment
    gaps: tuple[SynthesisGap, ...]


# --- values ----------------------------------------------------------------------------------
def _exact(x: Decimal) -> Decimal:
    """The canonical stored form: the same value, trailing zeros dropped, no exponent and no
    negative zero (so equal inputs always give byte-equal facts)."""
    if x == 0:
        return Decimal(0)
    with localcontext() as ctx:
        # normalize() rounds to the context: keep every digit the value has
        ctx.prec = max(80, len(x.as_tuple().digits))
        return Decimal(format(x.normalize(), "f"))


@dataclass(frozen=True)
class Val:
    """A computed value: an exact amount, or None with the root reason it is missing."""

    amount: Decimal | None
    reason: str | None = None

    def __post_init__(self) -> None:
        if (self.amount is None) == (self.reason is None):
            raise ValueError("a value carries an amount or a reason, never both or neither")


def _known(x: Decimal) -> Val:
    return Val(_exact(x))


def _div(a: Decimal, b: Decimal) -> Decimal:
    """One division of exact decimals: the correctly rounded 38-digit quotient."""
    with localcontext(_RATIO):
        return _exact(a / b)


def _sub38(a: Decimal, b: Decimal) -> Decimal:
    with localcontext(_RATIO):
        return _exact(a - b)


@contextmanager
def _exactly(operation: str) -> Iterator[None]:
    """The 38-digit context with the Inexact trap; a sum, difference or product that needs more
    digits fails closed as a ValueError naming the operation (round 8 A-2 #13)."""
    try:
        with localcontext(_EXACT):
            yield
    except Inexact:
        raise ValueError(
            f"CP-4C: {operation}: the exact value needs more than 38 significant digits "
            "(round 8 A-2 #13)"
        ) from None


def _exact_sum(values: Sequence[Decimal]) -> Decimal:
    """The exact sum at the precision it needs, never under 80 digits (round 8 A-1 #5): shares
    of different scales add without rounding, so no residue can hide in a rounded total."""
    if not values:
        return Decimal(0)
    span = max(v.adjusted() for v in values) - min(int(v.as_tuple().exponent) for v in values)
    ctx = _EXACT.copy()
    ctx.prec = max(80, span + len(values) + 1)
    with localcontext(ctx):
        return _exact(sum(values, Decimal(0)))


def _allocate(rank: int, claims: Sequence[Decimal], paid: Decimal, group: Decimal) -> list[Decimal]:
    """The shares of `paid` among one rank's claims, in claims order (round 8 A-1).

    Paid in full, each share is its claim; paid nothing, each is 0. Partly paid, each exact share
    claim x paid / group is floored to the rank quantum q = 10^(paid.adjusted() - 37), the 38th
    significant digit of paid, and the (paid - sum of floors) / q leftover units go one each to
    the largest remainders, ties to the later class. The shares sum to paid exactly, each lies
    within q of its exact value, and none is negative or above its claim. A paid amount or a
    claim that is not a multiple of q needs over 38 digits: fail-closed state 14."""
    if paid == group:
        return list(claims)
    if paid == 0:
        return [Decimal(0)] * len(claims)
    exponent = paid.adjusted() - 37
    q = Fraction(10) ** exponent
    if any(Fraction(x) % q for x in (paid, *claims)):
        raise ValueError(
            f"CP-4C: rank {rank} shares {paid} among claims that are not multiples of its quantum "
            f"1E{exponent}; the allocation needs over 38 digits (round 8 A-1 fail-closed state 14)"
        )
    exact = [Fraction(c) * Fraction(paid) / Fraction(group) for c in claims]
    units = [math.floor(share / q) for share in exact]
    leftover = int(Fraction(paid) / q) - sum(units)
    by_remainder = sorted(
        range(len(claims)), key=lambda i: (exact[i] / q - units[i], i), reverse=True
    )
    for i in by_remainder[:leftover]:
        units[i] += 1
    return [_exact(Decimal(f"{u}E{exponent}")) for u in units]


# --- the waterfall (lease "Decimal composer and missing rules"; expected.waterfall_rules) -------
@dataclass(frozen=True)
class ClassClaim:
    class_id: str
    name: str
    rank: int
    claim: Val


@dataclass(frozen=True)
class ClassAllocation:
    ahead: Val  # claims of better-ranked classes
    through: Val  # claims ahead plus the claims of the class's rank
    available: Val  # value left when the class's rank is paid
    group: Val  # total claims of the class's rank
    distribution: Val
    recovery: Val
    shortfall: Val


@dataclass(frozen=True)
class Waterfall:
    classes: Mapping[str, ClassAllocation]
    residual: Val  # what remains for equity
    value_break: tuple[str, ...] | None  # the breaking rank's class ids, ("equity",), or None
    break_reason: str | None  # the root reason when the break is not determinable
    break_through: Decimal | None  # claims through the breaking rank
    total_claims: Val


def _plus(a: Val, b: Val, operation: str) -> Val:
    """a + b exactly; the first missing operand when either is missing."""
    if a.amount is None or b.amount is None:
        return a if a.amount is None else b
    with _exactly(operation):
        return _known(a.amount + b.amount)


def _rank_total(rank: int, members: Sequence[ClassClaim]) -> Val:
    """The claims of one rank: the first missing claim, else their exact sum (above zero)."""
    missing = next((c.claim for c in members if c.claim.amount is None), None)
    if missing is not None:
        return missing
    with _exactly(f"the claims of rank {rank}"):
        total = sum((c.claim.amount for c in members if c.claim.amount is not None), Decimal(0))
    if total <= 0:  # every known claim is above zero (validator, round 8 A-2 #7)
        raise ValueError(f"CP-4C: the claims of rank {rank} total {total}; invariant broken")
    return _known(total)


def waterfall(*, classes: Sequence[ClassClaim], enterprise_value: Val) -> Waterfall:
    """Absolute priority by rank number (lowest first); classes of one rank share pro rata.

    paid = min(available, group); recovery = paid / group, one 38-digit division; the
    distributions are `_allocate`'s exact shares of paid (round 8 A-1); shortfall = claim -
    distribution at 38 digits (so claim = distribution + shortfall is not an invariant; only the
    T4E.9 balance is). A missing claim blocks its rank, every lower rank and the residual; a
    missing enterprise value blocks every allocation. Nothing becomes 0. The composer makes a
    negative enterprise value missing and the validator refuses a claim at or below zero, so
    either one here is a broken invariant (round 8 A-2 #7)."""
    ev = enterprise_value.amount
    if ev is not None and ev < 0:
        raise ValueError("CP-4C: the enterprise value is negative; invariant broken")
    for c in classes:
        if c.claim.amount is not None and c.claim.amount < 0:
            raise ValueError(f"CP-4C: the claim of {c.class_id} is negative; invariant broken")
    out: dict[str, ClassAllocation] = {}
    available, ahead = enterprise_value, Val(Decimal(0))
    found = False
    value_break: tuple[str, ...] | None = None
    break_reason: str | None = None
    break_through: Decimal | None = None
    for rank in sorted({c.rank for c in classes}):
        members = [c for c in classes if c.rank == rank]
        group = _rank_total(rank, members)
        through = _plus(ahead, group, f"the claims through rank {rank}")
        a, g = available.amount, group.amount
        if a is None or g is None:  # blocked: every share, the break and the residual
            cut = available if a is None else group
            for c in members:
                out[c.class_id] = ClassAllocation(
                    ahead=ahead,
                    through=through,
                    available=available,
                    group=group,
                    distribution=cut,
                    recovery=cut,
                    shortfall=cut,
                )
            if not found:
                found, break_reason = True, cut.reason
            available = cut
        else:
            paid = min(a, g)
            recovery = Val(_div(paid, g))
            claims = [c.claim.amount for c in members if c.claim.amount is not None]
            shares = _allocate(rank, claims, paid, g)  # a known rank total has no missing claim
            for c, claim, share in zip(members, claims, shares, strict=True):
                out[c.class_id] = ClassAllocation(
                    ahead=ahead,
                    through=through,
                    available=available,
                    group=group,
                    distribution=Val(share),
                    recovery=recovery,
                    shortfall=Val(_sub38(claim, share)),
                )
            if not found and paid < g:
                found, value_break, break_through = (
                    True,
                    tuple(c.class_id for c in members),
                    through.amount,
                )
            with _exactly(f"the value left after rank {rank}"):
                available = _known(a - paid)
        ahead = through
    if not found:
        value_break = (EQUITY,)
    return Waterfall(
        classes=out,
        residual=available,
        value_break=value_break,
        break_reason=break_reason,
        break_through=break_through,
        total_claims=ahead,
    )


# --- the inputs (Stage 2 binds them from the settled heads and the pack) ----------------------
LTM_COLUMN = "LTM Q4 25 (2025-01-01 to 2025-12-31)"
LTM_PERIOD = "LTM Q4 25: 2025-01-01 to 2025-12-31"
CP1_METRICS = ("total_debt", "ebitda")
YEARS: tuple[ForecastYear, ...] = ("FY2026", "FY2027", "FY2028")
CASE_ROW: Mapping[EbitdaCase, str] = {"base": "b", "down": "d"}
CASE_WORD: Mapping[EbitdaCase, str] = {"base": "base", "down": "downside"}
SECURED, SENIOR = "SECURED", "SENIOR"
CP4_FACILITY_ID = "T4C.11.r01.facility_id"
CP4_FACILITY = "T4C.11.r01.facility"
CP4_PERMITS = "T4.10.r02.permits"
CP4_CONDITIONS = "T4.10.r02.conditions"
CP4_RATING = "T4.13.rating.rating"
CP4_FACTS = (CP4_FACILITY_ID, CP4_FACILITY, CP4_PERMITS, CP4_CONDITIONS, CP4_RATING)


def select_cp1(facts: Iterable[Fact]) -> dict[str, Fact]:
    """metric -> the unique T4.10 fact labelled `<LTM column> · <metric>` (manifest
    fact_selection_rule.cp1); zero or several fail, and so does another period."""
    facts = tuple(facts)
    out: dict[str, Fact] = {}
    for metric in CP1_METRICS:
        label = f"{LTM_COLUMN} · {metric}"
        found = [f for f in facts if f.table_id == "T4.10" and f.label == label]
        if len(found) != 1:
            raise ValueError(
                f"CP-4C needs exactly one T4.10 fact labelled {label}, found {len(found)}"
            )
        if found[0].period != LTM_PERIOD:
            raise ValueError(f"CP-4C: CP-1 {metric} is not for {LTM_PERIOD}")
        out[metric] = found[0]
    return out


@dataclass(frozen=True)
class Cp1Head:
    status: InputStatus
    t410: tuple[Fact, ...]  # CP-1 facts; the T4.10 LTM total debt and EBITDA are selected
    facility_id: str  # the secured facility's T4.18 id (manifest fact_selection_rule.cp1_t418)
    secured_status: Fact  # T4.18 <facility>.secured_status at the quarter period
    seniority: Fact  # T4.18 <facility>.seniority at the quarter period


@dataclass(frozen=True)
class Cp2gEbitda:
    case: EbitdaCase
    year: ForecastYear
    fact: Fact  # T2H.4.<b|d><26|27|28>.ebitda


@dataclass(frozen=True)
class Cp2gHead:
    status: InputStatus
    ebitda: tuple[Cp2gEbitda, ...]
    base_first: Fact  # T2H.7.b01.base_first
    down_first: Fact  # T2H.7.b01.down_first
    down_ebitda_source: Fact  # T2H.3.d01.source: text "CP-2A T2B.1.<row>.ebitda_decline"
    down_interest_source: Fact  # T2H.3.d02.source: text "CP-2A T2B.1.<row>.interest_increase"

    def of(self, case: EbitdaCase, year: ForecastYear) -> Cp2gEbitda:
        found = [e for e in self.ebitda if e.case == case and e.year == year]
        if len(found) != 1:
            raise ValueError(f"CP-4C needs exactly one CP-2G EBITDA for {case} {year}")
        e = found[0]
        want = f"T2H.4.{CASE_ROW[case]}{26 + YEARS.index(year)}.ebitda"
        if e.fact.fact_id != want or not (e.fact.period or "").startswith(f"{year}:"):
            raise ValueError(f"CP-4C: the CP-2G EBITDA for {case} {year} is not {want} of {year}")
        return e

    def first(self, case: EbitdaCase) -> Fact:
        return self.base_first if case == "base" else self.down_first


_SHOCKS = ("ebitda_decline", "interest_increase")


@dataclass(frozen=True)
class Cp2aHead:
    status: InputStatus
    facts: tuple[Fact, ...]  # T2B.1 facts

    def fact(self, fact_id: str) -> Fact:
        found = [f for f in self.facts if f.fact_id == fact_id]
        if len(found) != 1:
            raise ValueError(f"CP-4C needs exactly one CP-2A fact {fact_id}")
        return found[0]

    def base_period(self, row: str) -> str:
        """The one period the row's `ebitda_decline` and `interest_increase` facts state
        (round 13 item 5, R1 L2). A shock with no period is not a period conflict (Stage 2
        round 5 item 16): only stated periods are compared. Two stated periods that differ raise,
        and so does a row that states none (fail closed, never a default)."""
        facts = (self.fact(f"T2B.1.{row}.{name}") for name in _SHOCKS)
        stated = tuple(dict.fromkeys(f.period for f in facts if f.period is not None))
        if len(stated) > 1:
            raise ValueError("CP-4C: CP-2A T2B.1 facts differ in period")
        if not stated:
            raise ValueError("CP-4C: CP-2A T2B.1 facts state no period")
        return stated[0]


@dataclass(frozen=True)
class Cp4Head:
    status: InputStatus
    facts: tuple[Fact, ...]  # the CP-4 head's facts; T4C.11, T4.10 and T4.13 ones are read

    def fact(self, fact_id: str) -> Fact:
        found = [f for f in self.facts if f.fact_id == fact_id]
        if len(found) != 1:
            raise ValueError(f"CP-4C needs exactly one CP-4 fact {fact_id}")
        return found[0]


@dataclass(frozen=True)
class Cp4cContext:
    """Everything the step reads besides the submission (lease Public API, D3)."""

    pack: PreparedPack
    cp1: Cp1Head
    cp2a: Cp2aHead
    cp2g: Cp2gHead
    cp4: Cp4Head
    cp3c_status: InputStatus | None = None  # a declared optional edge this version never reads


@dataclass(frozen=True)
class Cp4cInputs:
    context: Cp4cContext
    submission: RestructuringSubmission


# --- source rows (lease: claims are read from the cited balance-sheet row) --------------------
SCOPE = ("financial", "legal-covenants")
_HEADER = "Period end"
_CELLS = re.compile(r"  +")


def _pages(pack: PreparedPack) -> dict[tuple[str, str], str]:
    return {
        (s.source_id, span.locator): span.text
        for s in pack.sources
        if s.status == "ready"
        for span in s.spans
    }


def _header(page: str) -> tuple[str, ...]:
    """The statement's header cells (`Period end  <column>  ...`); none when absent."""
    for line in page.split("\n"):
        if line.startswith(_HEADER + "  "):
            return tuple(_CELLS.split(line))
    return ()


_FIGURE = re.compile(r"-?[0-9]+(\.[0-9]+)?")  # the ASCII cell grammar (round 10; fix 1 Q4)


def _row_amount(page: str, quote: str, column: str) -> Decimal | None:
    """The amount under `column` on the cited row: the one page line that starts with the quote
    (fix 1 Q1). None, the round 8 A-2 #11 outcome, when no line or several different lines start
    with the quote, when the row's cells do not line up with the header's (Q2), or when the cell
    is not an ASCII decimal figure (Q4); also when the quote cuts a cell (Q6: its cells are a
    prefix of the line's, each one equal) or the line is not one physical line (Q7)."""
    lines = {x.removesuffix("\r") for x in page.split("\n") if x.startswith(quote)}
    header = _header(page)
    if len(lines) != 1 or column not in header[1:]:
        return None
    line = lines.pop()
    cells, quoted = _CELLS.split(line), _CELLS.split(quote)
    if len(line.splitlines()) != 1 or cells[: len(quoted)] != quoted:
        return None
    if len(cells) != len(header):
        return None
    cell = cells[header.index(column)]
    return Decimal(cell) if _FIGURE.fullmatch(cell) else None


def _debt_claim(debt: Fact) -> Val:
    """CP-1 total debt as the secured class's claim (round 8 A-2 #6; round 11 B2)."""
    if debt.status != "known":
        state = _STATE_WORD[debt.status]
        return Val(None, f"Not calculable: total debt is {state} in CP-1 for {LTM_PERIOD}")
    if debt.amount is None:
        raise ValueError(f"CP-4C: CP-1 total debt {debt.fact_id} is known without an amount")
    return _known(debt.amount)


# an unsettled CP-1 fact's state as its reason names it (round 8 A-2 #6, round 11 B2 and B6)
_STATE_WORD = {
    "missing": "missing",
    "conflicting": "conflicting",
    "not_applicable": "not applicable",
}


def claim_classes(
    submission: RestructuringSubmission, context: Cp4cContext
) -> tuple[ClassClaim, ...]:
    """Each class's claim: CP-1 total debt for the secured class, the cited row's amount for a
    source_row class, missing for a class no source states (lease: no amount is typed)."""
    pages = _pages(context.pack)
    debt = select_cp1(context.cp1.t410)["total_debt"]
    out: list[ClassClaim] = []
    for c in submission.claims:
        if c.amount_source == "cp1_total_debt":
            claim = _debt_claim(debt)
        elif c.amount_source == "source_row":
            q, column = c.amount_quote, c.period_column
            amount = None
            if q is not None and column is not None:
                amount = _row_amount(pages[(q.source_id, q.locator)], q.quote, column)
            if amount is None:  # the validator refuses an uncited row or one with no number
                raise ValueError(f"CP-4C: {c.class_id} reads no number; invariant broken")
            claim = _known(amount)
        else:
            claim = Val(None, f"Not calculable: no supplied source states the claim of {c.name}")
        out.append(ClassClaim(c.class_id, c.name, int(c.rank), claim))
    return tuple(out)


R_EV_NA = "Not calculable: the EV multiple was not assessed"


def _upstream_reason(f: Fact) -> str:
    if not f.limitation:
        raise ValueError(f"CP-4C: unsettled upstream fact {f.fact_id} states no limitation")
    return f.limitation


@dataclass(frozen=True)
class _Value:
    """One valuation's operands and enterprise value."""

    source: Cp2gEbitda
    ebitda: Val
    multiple: Decimal | None
    ev: Val


def _valuation(v: Valuation, cp2g: Cp2gHead) -> _Value:
    source = cp2g.of(v.ebitda_case, v.ebitda_year)
    f = source.fact
    if f.status != "known":  # missing, not applicable or conflicting: its own limitation (A-4)
        ebitda = Val(None, _upstream_reason(f))
    elif f.amount is None:
        raise ValueError(f"CP-4C: CP-2G {f.fact_id} is known without an amount")
    else:
        ebitda = _known(f.amount)
    multiple = None if v.multiple == NOT_ASSESSED else Decimal(v.multiple)
    if ebitda.amount is None:
        ev = ebitda
    elif multiple is None:
        ev = Val(None, R_EV_NA)
    else:
        with _exactly(f"the enterprise value of {v.case_id}"):
            product = ebitda.amount * multiple
        if product < 0:  # negative EBITDA (round 8 A-2 #7)
            case = f"{CASE_WORD[v.ebitda_case]} {v.ebitda_year}"
            ev = Val(None, f"Not calculable: {case} EBITDA is negative in CP-2G")
        else:
            ev = _known(product)
    return _Value(source=source, ebitda=ebitda, multiple=multiple, ev=ev)


# --- the phrase guard (lease "Phrase guard (recovery boundary)") ------------------------------
PRODUCT_GUARD_KINDS = ("peer ranking", "instrument recommendation")
CORE_GUARD_PHRASES: Mapping[str, tuple[str, ...]] = {
    "outcome certainty": (
        "recovery is guaranteed",
        "recovery is assured",
        "recovery is certain",
        "guaranteed recovery",
        "assured recovery",
        "plan will be confirmed",
        "confirmation is assured",
        "confirmation is certain",
    ),
    "probability weighting": (
        "probability-weighted",
        "probability weighted",
        "probability of",
        "weighted by probability",
        "expected value",
        "likelihood-weighted",
    ),
}
_CORE_GUARD = tuple(
    (kind, phrase, re.compile(rf"(?<![A-Za-z]){re.escape(phrase)}(?![A-Za-z])", re.IGNORECASE))
    for kind, phrases in CORE_GUARD_PHRASES.items()
    for phrase in phrases
)


def guard_issues(path: str, text: str) -> tuple[str, ...]:
    """The product's peer-ranking and instrument-recommendation phrases (recovery conclusions
    are CP-4C's to state, so that kind is not checked), then the core-local outcome-certainty
    and probability-weighting phrases, word-bounded and case-insensitive. A phrase guard, not a
    semantic review."""
    found = list(prohibited_issues(path, text, kinds=PRODUCT_GUARD_KINDS))
    found += [
        f'{path}: prohibited conclusion ({kind}): "{phrase}"'
        for kind, phrase, pattern in _CORE_GUARD
        if pattern.search(text)
    ]
    return tuple(found)


# --- validation (lease "Refusals"; expected.refusal_rules.order) ------------------------------
HIGH_ISSUE = (
    "assessment.confidence: High is not allowed: multiples, ranks and plan treatment are uncited "
    "analyst assumptions"
)


FieldKind = Literal["name", "run", "plain"]
# The reference delimiters of composed claim text (`{fact_id|token}`, `[fact_id]`): a claim name or
# valuation label holding one does not compose, so it is refused (round 12 B7). `|` is no
# delimiter outside a reference.
_RESERVED = re.compile(r"[{}\[\]]")


def _text_fields(sub: RestructuringSubmission) -> list[tuple[str, str | None, FieldKind]]:
    """(path, text, kind) of every text field, in the pinned order: a class name or valuation
    label (one line, no bare figure, no reference syntax: round 8 A-2 #9, round 11 B3, round 12
    B7), run text (the rationales) or plain text. No kind may be blank (`blank.is_blank`)."""
    out: list[tuple[str, str | None, FieldKind]] = []
    for i, c in enumerate(sub.claims):
        out += [(f"claims[{i}].name", c.name, "name")]
        out += [(f"claims[{i}].rationale", c.rationale, "run")]
        out += [(f"claims[{i}].limitation", c.limitation, "plain")]
    rows: tuple[tuple[str, Sequence[Valuation | FulcrumJudgment | PlanJudgment]], ...] = (
        ("valuation", sub.valuation),
        ("fulcrum", sub.fulcrum),
        ("plan", sub.plan),
    )
    for key, items in rows:
        for i, x in enumerate(items):
            if isinstance(x, Valuation):
                out += [(f"{key}[{i}].label", x.label, "name")]
            out += [(f"{key}[{i}].rationale", x.rationale, "run")]
            out += [(f"{key}[{i}].limitation", x.limitation, "plain")]
    a = sub.assessment
    out += [
        ("assessment.rationale", a.rationale, "run"),
        ("assessment.limitation", a.limitation, "plain"),
    ]
    for i, g in enumerate(sub.gaps):
        for name in ("gap", "why_it_matters", "affected_analysis", "action"):
            out.append((f"gaps[{i}].{name}", getattr(g, name), "plain"))
    return out


def _term_loan_secured(cp1: Cp1Head) -> bool:
    """CP-1 T4.18 shows the secured facility SECURED and SENIOR (lease; round 8 A-2 #2)."""
    secured, senior = cp1.secured_status, cp1.seniority
    return (secured.status, secured.text, senior.status, senior.text) == (
        "known",
        SECURED,
        "known",
        SENIOR,
    )


def _source_row_issues(i: int, c: ClaimClass, pages: Mapping[tuple[str, str], str]) -> list[str]:
    """A source_row class's cited row: v03, v04, v05, then round 8 A-2 #3, #11 and #7."""
    q = c.amount_quote
    if q is None:
        return [f"claims[{i}].amount_quote: a source_row class cites the row it reads"]
    if is_blank(q.quote):  # round 13 addendum 3: a quote is analyst text under the blank class
        return [f"claims[{i}].amount_quote.quote: empty text"]
    page = pages.get(("financial", q.locator), "")
    if q.source_id != "financial" or q.quote not in page:
        where = (f"claims[{i}].amount_quote: quote not found under ", q.source_id, " ", q.locator)
        return [clipped(where)]
    column = c.period_column
    if column not in _header(page)[1:]:
        what = f"claims[{i}].period_column: not a column of the quoted statement: "
        return [clipped((what, str(column)))]
    if column != _PINNED_COLUMN:
        return [
            (
                f"claims[{i}].period_column: claims are the 31 December 2025 balances; use "
                f"{_PINNED_COLUMN}"
            )
        ]
    amount = _row_amount(page, q.quote, column)
    if amount is None:
        return [f"claims[{i}].amount_quote: the quoted row has no number under {column}"]
    return _claim_above_zero(i, c, amount)


def _claim_above_zero(i: int, c: ClaimClass, amount: Decimal) -> list[str]:
    if amount > 0:
        return []
    parts = (f"claims[{i}]: a claim class needs a claim above zero; ", c.name, " reads ")
    return [clipped((*parts, str(_exact(amount))))]


def _claim_issues(
    i: int, c: ClaimClass, pages: Mapping[tuple[str, str], str], ctx: Cp4cContext
) -> list[str]:
    issues: list[str] = []
    mismatch = (c.kind == "secured_debt") != (c.amount_source == "cp1_total_debt")
    if mismatch:
        issues.append(
            f"claims[{i}].amount_source: cp1_total_debt is the secured_debt class's source and "
            "no other class's"
        )
    if c.kind == "secured_debt" and not _term_loan_secured(ctx.cp1):
        issues.append(
            f"claims[{i}].kind: CP-1 T4.18 does not show {ctx.cp1.facility_id} SECURED and "
            "SENIOR, so no class can be secured_debt"
        )
    if mismatch:
        pass
    elif c.amount_source == "source_row":
        issues += _source_row_issues(i, c, pages)
    else:
        if c.amount_quote is not None:
            issues.append(f"claims[{i}].amount_quote: only a source_row class cites an amount row")
        if c.period_column is not None:
            issues.append(f"claims[{i}].period_column: only a source_row class names a column")
        if c.amount_source == "cp1_total_debt":
            debt = select_cp1(ctx.cp1.t410)["total_debt"].amount
            issues += [] if debt is None else _claim_above_zero(i, c, debt)
    for j, q in enumerate(c.support):
        if is_blank(q.quote):  # round 13 addendum 3: before the page-occurrence check
            issues.append(f"claims[{i}].support[{j}].quote: empty text")
        elif q.source_id not in SCOPE:
            what = f"claims[{i}].support[{j}].source_id: not in this step's source scope: "
            issues.append(clipped((what, q.source_id)))
        elif q.quote not in pages.get((q.source_id, q.locator), ""):
            what = f"claims[{i}].support[{j}]: quote not found under "
            issues.append(clipped((what, q.source_id, " ", q.locator)))
    return issues


def _fulcrum_issues(
    sub: RestructuringSubmission, known: set[str], falls: Mapping[str, Waterfall]
) -> list[str]:
    issues: list[str] = []
    for i, f in enumerate(sub.fulcrum):
        bad = False
        for cid in f.class_ids:
            if cid not in known:
                issues.append(f"fulcrum[{i}].class_ids: not a claim class: {cid}")
                bad = True
        if len(set(f.class_ids)) != len(f.class_ids):
            issues.append(f"fulcrum[{i}].class_ids: duplicate class")
            bad = True
        if bad or f.case_id != f"v{i + 1:02d}":
            continue
        brk = falls[f.case_id].value_break
        if brk is None:
            if f.class_ids:
                issues.append(
                    f"fulcrum[{i}].class_ids: the value break is not determinable in {f.case_id}, "
                    "so no class can be named"
                )
        elif sorted(f.class_ids) != sorted(brk):
            named = ", ".join(f.class_ids) or "no class"
            issues.append(
                f"fulcrum[{i}].class_ids: value breaks at {', '.join(brk)} in {f.case_id}; the "
                f"judgment names {named}"
            )
    return issues


def _fits(treatment: str, value: Decimal | None, equity: bool) -> bool:
    """The plan-fit rule (expected.waterfall_rules.plan_fit)."""
    if value is None:
        return treatment == "Not determined"
    if equity:
        return (value > 0 and treatment == "Equity retained") or (
            value == 0 and treatment == "No recovery"
        )
    return (
        (value == 1 and treatment == "Paid in full")
        or (0 < value < 1 and treatment == "Receives reorganised equity")
        or (value == 0 and treatment == "No recovery")
    )


def _plan_issues(
    sub: RestructuringSubmission, ids: Sequence[str], falls: Mapping[str, Waterfall]
) -> list[str]:
    issues: list[str] = []
    known = {*ids, EQUITY}
    for i, p in enumerate(sub.plan):
        bad = False
        seen: list[str] = []
        for j, t in enumerate(p.treatments):
            if t.class_id not in known:
                what = f"plan[{i}].treatments[{j}].class_id: not a claim class: "
                issues.append(clipped((what, t.class_id)))
                bad = True
            elif t.class_id in seen:
                issues.append(f"plan[{i}].treatments[{j}].class_id: duplicate class {t.class_id}")
                bad = True
            seen.append(t.class_id)
        for cid in (*ids, EQUITY):
            if cid not in seen:
                issues.append(f"plan[{i}].treatments: no treatment for {cid}")
                bad = True
        if bad or p.case_id != f"v{i + 1:02d}":
            continue
        w = falls[p.case_id]
        for j, t in enumerate(p.treatments):
            equity = t.class_id == EQUITY
            value = w.residual.amount if equity else w.classes[t.class_id].recovery.amount
            if not _fits(t.treatment, value, equity):
                issues.append(
                    f"plan[{i}].treatments[{j}]: {t.treatment} does not fit the waterfall result "
                    f"of {t.class_id} in {p.case_id}"
                )
    return issues


def _reference_facts(sub: RestructuringSubmission, ctx: Cp4cContext) -> tuple[Fact, ...]:
    """The upstream facts the module carries in its reference tables, which is what its prose
    resolves through at settlement (expected.references_rule)."""
    return tuple(r.fact for table in _references(sub, ctx) for r in table.rows)


def content_issues(inputs: Cp4cInputs) -> tuple[str, ...]:
    """Content issues of a parsed submission, in the pinned order: claims, valuation case ids,
    fulcrum and plan case ids, fulcrum and plan against the waterfall (only when claims and
    valuation are structurally valid), assessment, then per text field prose and guard issues."""
    sub, ctx = inputs.submission, inputs.context
    pages = _pages(ctx.pack)
    issues: list[str] = []
    ids: list[str] = []
    structural = True
    for i, c in enumerate(sub.claims):
        before = len(issues)
        if c.class_id in ids:
            issues.append(f"claims[{i}].class_id: duplicate class {c.class_id}")
        ids.append(c.class_id)
        issues += _claim_issues(i, c, pages, ctx)
        structural = structural and len(issues) == before
    secured = [i for i, c in enumerate(sub.claims) if c.kind == "secured_debt"]
    if len(secured) != 1:
        issues.append("claims: exactly one secured_debt class is required")
        structural = False
    else:
        (k,) = secured
        top = int(sub.claims[k].rank)
        if any(int(c.rank) <= top for j, c in enumerate(sub.claims) if j != k):
            issues.append(
                f"claims[{k}].rank: the secured_debt class ranks first, ahead of every other class"
            )
            structural = False
    for i, v in enumerate(sub.valuation):
        if v.case_id != f"v{i + 1:02d}":
            issues.append(f"valuation[{i}].case_id: expected v{i + 1:02d}")
            structural = False
    judged: tuple[tuple[str, Sequence[FulcrumJudgment | PlanJudgment]], ...] = (
        ("fulcrum", sub.fulcrum),
        ("plan", sub.plan),
    )
    for key, rows in judged:
        for i, x in enumerate(rows):
            if x.case_id != f"v{i + 1:02d}":
                issues.append(f"{key}[{i}].case_id: expected v{i + 1:02d}")
    if structural:
        classes = claim_classes(sub, ctx)
        falls = {
            v.case_id: waterfall(classes=classes, enterprise_value=_valuation(v, ctx.cp2g).ev)
            for v in sub.valuation
        }
        issues += _fulcrum_issues(sub, {*ids, EQUITY}, falls)
        issues += _plan_issues(sub, ids, falls)
    if sub.assessment.confidence == "High":
        issues.append(HIGH_ISSUE)
    bound = prose.bind(_reference_facts(sub, ctx))
    names = (ctx.pack.run.issuer_name,)
    for path, text, kind in _text_fields(sub):
        if text is None:
            continue
        if is_blank(text):  # round 11 blank class and round 12 B10, every kind (R3 M2)
            issues.append(f"{path}: empty text")
            continue
        if kind == "name":  # a name or label is no run text and is not guarded (round 8 A-2 #9)
            if text.splitlines() != [text]:
                issues.append(f"{path}: one line only")
            else:  # round 11 B3: as the claims spell it (a valuation label in lower case)
                spelt = text.lower() if path.startswith("valuation") else text
                issues += [
                    clipped((path, ": Bare figure: ", t))
                    for t in prose.bare_figures(spelt, names=names)
                ]
                if _RESERVED.search(text):  # round 12 B7: CP-8's pinned frame
                    issues.append(f"{path}: reference syntax is not allowed")
            continue
        if kind == "run":  # a rationale becomes `Claim.text` (Stage 2 round 3 item 2)
            found = prose.issues(text, bound, names=names)
            issues += [clipped((path, ": ", issue)) for issue in found]
            if not found:
                issues += _run_text_issues(path, text)
        issues += guard_issues(path, text)
    return tuple(issues)


_RUN_TEXT: TypeAdapter[str] = TypeAdapter(RunText)


def _run_text_issues(path: str, text: str) -> list[str]:
    """Stage 2 round 3 item 2: text built as `Claim.text` is checked with that very type
    (`RunText`, one `TypeAdapter` built once), so a malformed reference is a journaled issue and
    composition never raises after the binding write. The message never echoes the input."""
    try:
        _RUN_TEXT.validate_python(text)
    except ValidationError as error:
        found = error.errors(include_input=False, include_url=False, include_context=False)
        return [clipped((path, ": ", item["msg"])) for item in found]
    return []


def _parsed(payload: str) -> tuple[RestructuringSubmission | None, tuple[str, ...]]:
    """The submission, or its shape issues (protocol section 6: model text is read only through
    `json_object`). The schema validates the bounded document's exact re-serialisation, never the
    raw text; text `json_object` refuses keeps Pydantic's own shape issue (the frozen r12 frame),
    and is refused even if Pydantic would parse it (the CP-2G precedent)."""
    document = json_object(payload)
    try:
        if document is None:
            RestructuringSubmission.model_validate_json(payload)  # for its shape issue only
            return None, ("(root): not a bounded JSON object",)
        return RestructuringSubmission.model_validate_json(exact_json(document)), ()
    except ValidationError as error:
        return None, shape_issues(error)


def payload_issues(payload: str, context: Cp4cContext) -> tuple[str, ...]:
    """Shape issues alone (a payload that does not parse gets no content check), else the
    content issues."""
    submission, shape = _parsed(payload)
    if submission is None:
        return shape
    return content_issues(Cp4cInputs(context=context, submission=submission))


def stale_issues(*, bound: Sequence[Input], current: Sequence[Input] | str) -> tuple[str, ...]:
    """Every bound upstream that changed (CP-2G precedent), in the `cp2_synthesis._stale_issues`
    form; returned alone, like shape issues (rulings round 5, G-decisions)."""
    if isinstance(current, str):
        return (clipped(("Stale inputs: ", current)),)
    was = {item.input_id: item for item in bound}
    now = {item.input_id: item for item in current}

    def state(item: Input | None) -> str:
        return "absent" if item is None else f"{item.status} {item.sha256[:12]}"

    return tuple(
        f"Stale input {key}: bound {state(was.get(key))}, current {state(now.get(key))}"
        for key in dict.fromkeys((*was, *now))
        if was.get(key) != now.get(key)
    )


# --- cells, tables, references, claims -------------------------------------------------------
UnitKind = Literal["amount", "multiple", "percent", "pp"]
_UNIT: Mapping[UnitKind, str] = {
    "amount": "MILLIONS",
    "multiple": "MULTIPLE",
    "percent": "PERCENT",
    "pp": "pp",
}
_MILLIONS = Decimal(1000000)
ValueClass = Literal["source", "normalized", "calculated", "analyst_judgment"]
CellStatus = Literal["known", "missing", "not_applicable", "conflicting"]
_UPSTREAM = ("cp1:", "cp2a:", "cp2g:", "cp4:")


@dataclass(frozen=True)
class Cell:
    """One table cell: the product Fact it settles as, its lineage, the submission quotes that
    back it (if any) and its display spelling."""

    fact: Fact
    derives_from: tuple[str, ...]
    quoted: tuple[Citation, ...]
    shown: str | None  # report_view.fact_spelling of a known fact; None while unsettled


@dataclass(frozen=True)
class Row:
    row_id: str
    label: str
    fact_ids: tuple[str, ...]


@dataclass(frozen=True)
class Table:
    table_id: str
    title: str
    rows: tuple[Row, ...]


@dataclass(frozen=True)
class Reference:
    row_id: str
    label: str
    fact: Fact  # the upstream fact, verbatim


@dataclass(frozen=True)
class RefTable:
    table_id: str
    title: str
    row_header: str
    rows: tuple[Reference, ...]


@dataclass(frozen=True)
class Claim:
    claim_id: str
    text: str  # run text: {fact_id|unit} figures and [fact_id] chips
    limitation: str | None
    references: tuple[str, ...]  # upstream fact ids the analyst's text names as figures


@dataclass(frozen=True)
class RestructuringResult:
    cells: tuple[Cell, ...]
    tables: tuple[Table, ...]
    references: tuple[RefTable, RefTable, RefTable, RefTable]  # cp1, cp2g, cp2a, cp4
    claims: tuple[Claim, ...]
    own_limitations: tuple[str, ...]
    waterfalls: Mapping[str, Waterfall]  # by valuation case id
    enterprise_values: Mapping[str, Val]


TABLES = {
    "T4E.1": "Upstream register",
    "T4E.2": "Claims register",
    "T4E.3": "Valuation scenarios",
    "T4E.4": "Waterfall allocation",
    "T4E.5": "Recovery by class",
    "T4E.6": "Attachment and detachment",
    "T4E.7": "Fulcrum identification",
    "T4E.8": "Plan treatment",
    "T4E.9": "Waterfall totals",
    "T4E.10": "Gaps ledger",
}


@dataclass
class _Draft:
    fact: Fact  # citations are settled in `_Book.cells`
    derives: tuple[str, ...]
    quoted: tuple[Citation, ...]


@dataclass
class _Book:
    """The module's cells in creation order, and each table's rows."""

    drafts: dict[str, _Draft] = field(default_factory=dict)
    rows: dict[str, list[Row]] = field(default_factory=lambda: {t: [] for t in TABLES})

    def _add(self, fact: Fact, derives: Sequence[str], quoted: Sequence[Citation] = ()) -> None:
        if fact.fact_id in self.drafts:
            raise ValueError(f"CP-4C: duplicate fact {fact.fact_id}")
        self.drafts[fact.fact_id] = _Draft(fact, tuple(derives), tuple(quoted))

    def num(
        self,
        at: tuple[str, str, str],
        label: str,
        value: Decimal,
        unit: UnitKind,
        formula: str,
        *,
        period: str,
        value_class: ValueClass | None = "calculated",
        derives: Sequence[str] = (),
        keep_lineage: bool = False,
        quoted: Sequence[Citation] = (),
    ) -> None:
        table, row, name = at
        fid = f"{table}.{row}.{name}"
        calculated = value_class == "calculated"
        amount_unit = unit == "amount"
        fact = Fact(
            fact_id=fid,
            label=label,
            table_id=table,
            row_id=row,
            field=name,
            amount=_exact(value),
            unit=_UNIT[unit],
            currency="USD" if amount_unit else None,
            scale=_MILLIONS if amount_unit else Decimal(1),
            decimals=2 if amount_unit else None,
            period=period,
            calculation_id=f"calc:{fid}" if calculated else None,
            value_class=value_class,
            formula=formula,
        )
        self._add(fact, derives if calculated or keep_lineage else (), quoted)

    def gap(
        self,
        at: tuple[str, str, str],
        label: str,
        unit: UnitKind,
        reason: str,
        *,
        period: str,
        status: CellStatus = "missing",
    ) -> None:
        table, row, name = at
        fact = Fact(
            fact_id=f"{table}.{row}.{name}",
            label=label,
            table_id=table,
            row_id=row,
            field=name,
            status=status,
            unit=_UNIT[unit],
            period=period,
            limitation=reason,
        )
        self._add(fact, ())

    def value(
        self,
        at: tuple[str, str, str],
        label: str,
        v: Val,
        unit: UnitKind,
        formula: str,
        derives: Sequence[str],
        *,
        period: str,
    ) -> None:
        if v.amount is None:
            assert v.reason is not None
            self.gap(at, label, unit, v.reason, period=period)
        else:
            self.num(at, label, v.amount, unit, formula, period=period, derives=derives)

    def text(
        self,
        at: tuple[str, str, str],
        label: str,
        value: str,
        *,
        value_class: ValueClass | None = None,
        derives: Sequence[str] = (),
        quoted: Sequence[Citation] = (),
    ) -> None:
        table, row, name = at
        fact = Fact(
            fact_id=f"{table}.{row}.{name}",
            label=label,
            table_id=table,
            row_id=row,
            field=name,
            text=value,
            value_class=value_class,
            citations=tuple(quoted),
        )
        self._add(fact, derives, quoted)

    def unsettled_text(
        self, at: tuple[str, str, str], label: str, reason: str, status: CellStatus
    ) -> None:
        table, row, name = at
        fact = Fact(
            fact_id=f"{table}.{row}.{name}",
            label=label,
            table_id=table,
            row_id=row,
            field=name,
            status=status,
            limitation=reason,
        )
        self._add(fact, ())

    def copy_text(self, at: tuple[str, str, str], label: str, upstream: Fact, lineage: str) -> None:
        """A text that restates an upstream fact: known with its lineage, or unsettled with the
        upstream status and limitation (copies keep the upstream status; rulings round 2 L10-c,
        round 5 G-decisions)."""
        if upstream.status == "known" and upstream.text is not None:
            self.text(at, label, upstream.text, derives=(lineage,))
        else:
            self.unsettled_text(at, label, _upstream_reason(upstream), _copy_status(upstream))

    def row(self, table: str, row_id: str, label: str, fields: Sequence[str]) -> None:
        ids = tuple(f"{table}.{row_id}.{f}" for f in fields)
        for fid in ids:
            if fid not in self.drafts:
                raise ValueError(f"CP-4C: row {table}.{row_id} names no fact {fid}")
        self.rows[table].append(Row(row_id=row_id, label=label, fact_ids=ids))

    def status(self, fact_id: str) -> str:
        return self.drafts[fact_id].fact.status

    def cells(self, upstream: Mapping[str, Fact]) -> tuple[Cell, ...]:
        """Settle the lineage citations (expected.lineage_rule): a quoted cell cites its quotes;
        a calculated cell the ordered, de-duplicated citations of the facts it derives from. A
        known fact never derives from a fact that is not known."""
        memo: dict[str, tuple[Citation, ...]] = {}

        def cited(fid: str, trail: tuple[str, ...]) -> tuple[Citation, ...]:
            if fid in memo:
                return memo[fid]
            if fid in trail:
                raise ValueError(f"CP-4C: lineage cycle through {fid}")
            d = self.drafts[fid]
            out: list[Citation] = list(d.quoted)
            if not d.quoted and d.fact.value_class == "calculated":
                for dep in d.derives:
                    more = (
                        upstream[dep].citations
                        if dep.startswith(_UPSTREAM)
                        else cited(dep, (*trail, fid))
                    )
                    out += [c for c in more if c not in out]
            memo[fid] = tuple(out)
            return memo[fid]

        out: list[Cell] = []
        for fid, d in self.drafts.items():
            if d.fact.status == "known":
                for dep in d.derives:
                    source = (
                        upstream.get(dep) if dep.startswith(_UPSTREAM) else self.drafts[dep].fact
                    )
                    if source is None or source.status != "known":
                        raise ValueError(
                            f"CP-4C: known {fid} derives from {dep}, which is not known"
                        )
            fact = d.fact.model_copy(update={"citations": cited(fid, ())})
            shown = fact_spelling(fact, None)[2] if fact.status == "known" else None
            out.append(Cell(fact=fact, derives_from=d.derives, quoted=d.quoted, shown=shown))
        return tuple(out)


def _copy_status(f: Fact) -> CellStatus:
    """An unsettled upstream fact's status, kept by its copy: missing, not applicable or
    conflicting (round 8 A-4; round 6g)."""
    if f.status == "known":
        raise ValueError(f"CP-4C: upstream fact {f.fact_id} is known; invariant broken")
    return f.status


def _citation(pack: PreparedPack, quote: Quote) -> Citation:
    """A submission quote as a Citation with the pack's source hash (validated before)."""
    digest = next(
        (s.sha256 for s in pack.sources if s.source_id == quote.source_id and s.status == "ready"),
        None,
    )
    if digest is None:
        raise ValueError(f"CP-4C: quoted source {quote.source_id} is not a ready pack source")
    return Citation(
        source_id=quote.source_id, source_sha256=digest, locator=quote.locator, quote=quote.quote
    )


@dataclass(frozen=True)
class _Run:
    """What the composer reads, resolved once."""

    sub: RestructuringSubmission
    ctx: Cp4cContext
    cp1: Mapping[str, Fact]
    classes: tuple[ClassClaim, ...]
    values: Mapping[str, _Value]
    falls: Mapping[str, Waterfall]
    scenario_row: str
    upstream: Mapping[str, Fact]


_PINNED_COLUMN = "Q4 2025-12-31"  # the column BS_PERIOD and the balance-date limitation state
BS_PERIOD = "Q4 2025: 2025-12-31"
_PINNED_RATING = "Insufficient Information"
_PINNED_CONDITIONS = (
    "Prior written consent of every lender; no automatic additional debt basket is provided"
)


_SOURCE_D01 = re.compile(r"CP-2A T2B\.1\.(s[0-9]{2})\.ebitda_decline")
_SOURCE_D02 = re.compile(r"CP-2A T2B\.1\.(s[0-9]{2})\.interest_increase")


def _scenario_row(cp2g: Cp2gHead) -> str:
    """The CP-2A T2B.1 row CP-2G applied, named by the settled CP-2G `T2H.3.d01.source` and
    `T2H.3.d02.source` texts (round 13 item 2, R1 M2). CP-2G writes them once for all years."""
    d01 = _SOURCE_D01.fullmatch(cp2g.down_ebitda_source.text or "")
    d02 = _SOURCE_D02.fullmatch(cp2g.down_interest_source.text or "")
    if d01 is None or d02 is None or d01[1] != d02[1]:
        raise ValueError(
            "CP-4C: CP-2G T2H.3.d01 and T2H.3.d02 sources name no single CP-2A T2B.1 row"
        )
    return d01[1]


def _upstream_map(ctx: Cp4cContext, cp1: Mapping[str, Fact]) -> dict[str, Fact]:
    out = {f"cp1:{metric}": f for metric, f in cp1.items()}
    for f in (ctx.cp1.secured_status, ctx.cp1.seniority):
        out[f"cp1:{ctx.cp1.facility_id}.{f.field}"] = f
    out.update({f"cp2g:{e.fact.fact_id}": e.fact for e in ctx.cp2g.ebitda})
    out.update({f"cp2g:{f.fact_id}": f for f in (ctx.cp2g.base_first, ctx.cp2g.down_first)})
    out.update({f"cp2a:{f.fact_id}": f for f in ctx.cp2a.facts})
    out.update({f"cp4:{f.fact_id}": f for f in ctx.cp4.facts})
    return out


def _check_cp4_head(ctx: Cp4cContext) -> None:
    """The own limitations state the frozen CP-4 head: rating Insufficient Information and the
    every-lender consent. Any other head stays fail-closed until Stage 2 words it (round 8 A-2
    #4)."""
    rating, conditions = ctx.cp4.fact(CP4_RATING), ctx.cp4.fact(CP4_CONDITIONS)
    if rating.text != _PINNED_RATING:
        raise ValueError(
            f"CP-4C: the CP-4 lender protection rating is {rating.text!r}; the own limitation "
            f"states {_PINNED_RATING}, so another rating fails closed (round 8 A-2 #4)"
        )
    if conditions.text != _PINNED_CONDITIONS:
        raise ValueError(
            "CP-4C: the CP-4 additional-debt conditions differ from the every-lender consent the "
            "new-money limitation states, so they fail closed (round 8 A-2 #4)"
        )


def _resolve(inputs: Cp4cInputs) -> _Run:
    sub, ctx = inputs.submission, inputs.context
    found = content_issues(inputs)
    if found:
        raise ValueError("CP-4C submission has issues: " + "; ".join(bounded_issues(found)))
    cp1 = select_cp1(ctx.cp1.t410)
    _check_cp4_head(ctx)
    classes = claim_classes(sub, ctx)
    values = {v.case_id: _valuation(v, ctx.cp2g) for v in sub.valuation}
    falls = {k: waterfall(classes=classes, enterprise_value=v.ev) for k, v in values.items()}
    return _Run(
        sub=sub,
        ctx=ctx,
        cp1=cp1,
        classes=classes,
        values=values,
        falls=falls,
        scenario_row=_scenario_row(ctx.cp2g),
        upstream=_upstream_map(ctx, cp1),
    )


_FIELDS_T4E1 = ("module", "status", "basis", "read", "limitation")
CP3C_UNREAD = (
    "CP-3C (refinancing and liability management) is an optional input that this version never "
    "reads."
)


def _t4e1(b: _Book, run: _Run) -> None:
    ctx = run.ctx
    rows = (
        (
            "u_cp1",
            "CP-1",
            ctx.cp1.status,
            f"Base period {LTM_PERIOD}",
            "T4.10 total debt and EBITDA; T4.18 term loan security and seniority",
            "Inherits CP-1's own limitations.",
        ),
        (
            "u_cp2a",
            "CP-2A",
            ctx.cp2a.status,
            f"Base period {ctx.cp2a.base_period(run.scenario_row)}",
            "T2B.1 name and shock sizes of the downside scenario CP-2G applied",
            "Shock sizes are analyst assumptions.",
        ),
        (
            "u_cp2g",
            "CP-2G",
            ctx.cp2g.status,
            "Forecast years FY2026 to FY2028 from the CP-1 twelve-month base",
            "T2H.4 forecast EBITDA and T2H.7 first year the free cash flow test is reached",
            "Forecast on analyst-assumed drivers.",
        ),
        (
            "u_cp4",
            "CP-4",
            ctx.cp4.status,
            "Executed term loan terms, current restatement",
            "T4C.11 facility map, T4.10 additional-debt consent, T4.13 lender protection rating",
            (
                "Selected executed terms only; security, guarantees, default, cure and voting terms "
                "are not supplied."
            ),
        ),
        (  # a bound CP-3C shows its Input status and is still not read (round 8 A-2 #1)
            "u_cp3c",
            "CP-3C",
            ctx.cp3c_status or "not part of this run",
            "Not applicable",
            "Nothing read",
            CP3C_UNREAD,
        ),
    )
    for row, *values in rows:
        for name, value in zip(_FIELDS_T4E1, values, strict=True):
            b.text(("T4E.1", row, name), name.capitalize(), value)
        b.row("T4E.1", row, values[0], _FIELDS_T4E1)


_FIELDS_T4E2 = (
    "name",
    "kind",
    "rank",
    "security",
    "claim",
    "basis",
    "facility",
    "lender_protection",
    "additional_debt",
)
SECURITY_TEXT = {
    "unsecured_trade": "UNSECURED",
    "other_liability": "UNSECURED",
    "administrative_priority": "PRIORITY",
}
NOT_A_FACILITY = "The class is not a facility governed by the legal source"
_LEGAL = (
    ("facility", "Facility", CP4_FACILITY),
    ("lender_protection", "Lender protection", CP4_RATING),
    ("additional_debt", "Additional debt", CP4_CONDITIONS),
)


def _t4e2(b: _Book, run: _Run) -> None:
    pack, cp1h = run.ctx.pack, run.ctx.cp1
    for c, k in zip(run.sub.claims, run.classes, strict=True):
        r = c.class_id
        b.text(("T4E.2", r, "name"), "Class", c.name, value_class="analyst_judgment")
        b.text(("T4E.2", r, "kind"), "Kind", c.kind, value_class="analyst_judgment")
        b.text(("T4E.2", r, "rank"), "Rank", c.rank, value_class="analyst_judgment")
        if c.kind == "secured_debt":
            secured = cp1h.secured_status
            assert secured.text is not None  # _term_loan_secured (validator)
            b.text(
                ("T4E.2", r, "security"),
                "Security",
                secured.text,
                derives=(f"cp1:{cp1h.facility_id}.secured_status",),
                quoted=tuple(_citation(pack, q) for q in c.support),
            )
        else:
            b.text(
                ("T4E.2", r, "security"),
                "Security",
                SECURITY_TEXT[c.kind],
                value_class="analyst_judgment",
            )
        if k.claim.amount is None:
            assert k.claim.reason is not None
            b.gap(("T4E.2", r, "claim"), "Claim", "amount", k.claim.reason, period=BS_PERIOD)
        elif c.amount_source == "cp1_total_debt":
            b.num(
                ("T4E.2", r, "claim"),
                "Claim",
                k.claim.amount,
                "amount",
                "CP-1 total debt",
                period=LTM_PERIOD,
                derives=("cp1:total_debt",),
            )
        else:
            assert c.amount_quote is not None
            b.num(
                ("T4E.2", r, "claim"),
                "Claim",
                k.claim.amount,
                "amount",
                "quoted statement figure",
                period=BS_PERIOD,
                value_class="source",
                quoted=(_citation(pack, c.amount_quote),),
            )
        if c.amount_source == "cp1_total_debt":
            basis = f"CP-1 T4.10 total debt · {LTM_PERIOD}"
        elif c.amount_source == "source_row":
            assert c.amount_quote is not None
            q = c.amount_quote
            basis = f"{q.source_id} {q.locator}, column {c.period_column}"
        else:
            basis = "No supplied source states this claim"
        b.text(("T4E.2", r, "basis"), "Basis", basis)
        for name, label, fid in _LEGAL:
            if c.kind == "secured_debt":
                b.copy_text(("T4E.2", r, name), label, run.ctx.cp4.fact(fid), f"cp4:{fid}")
            else:
                b.unsettled_text(("T4E.2", r, name), label, NOT_A_FACILITY, "not_applicable")
        b.row("T4E.2", r, c.name, _FIELDS_T4E2)
    b.text(("T4E.2", "eq", "name"), "Class", "Equity")
    b.text(("T4E.2", "eq", "kind"), "Kind", "equity")
    b.text(("T4E.2", "eq", "rank"), "Rank", "Residual")
    b.text(("T4E.2", "eq", "security"), "Security", "RESIDUAL")
    b.gap(
        ("T4E.2", "eq", "claim"),
        "Claim",
        "amount",
        "Equity is the residual claimant and has no claim amount",
        period=BS_PERIOD,
        status="not_applicable",
    )
    b.text(("T4E.2", "eq", "basis"), "Basis", "Residual after all claims")
    for name, label, _fid in _LEGAL:
        b.unsettled_text(("T4E.2", "eq", name), label, NOT_A_FACILITY, "not_applicable")
    b.row("T4E.2", "eq", "Equity", _FIELDS_T4E2)


_FIELDS_T4E3 = (
    "scenario",
    "ebitda_basis",
    "ebitda",
    "multiple",
    "ev",
    "implied_ltm_multiple",
    "first_break",
    "cp2a_scenario",
    "ebitda_decline",
)
NO_SCENARIO = "The base valuation uses no CP-2A scenario"


def _cp1_ebitda(f: Fact) -> Val:
    """CP-1 EBITDA as the implied multiple's denominator: a known positive amount, else missing
    with the round 8 A-2 #5 reason naming its state (round 11 B6; no own line)."""
    if f.status != "known":
        return Val(
            None, f"Not calculable: EBITDA is {_STATE_WORD[f.status]} in CP-1 for {LTM_PERIOD}"
        )
    if f.amount is None:  # an upstream contract break, as for total debt (fix 1 Q3)
        raise ValueError(f"CP-4C: CP-1 EBITDA {f.fact_id} is known without an amount; invariant")
    if f.amount <= 0:
        return Val(
            None,
            f"Not calculable: EBITDA is zero or negative in CP-1 for {LTM_PERIOD} "
            "(ZERO_OR_NEGATIVE_DENOMINATOR)",
        )
    return _known(f.amount)


def _t4e3(b: _Book, run: _Run) -> None:
    row = run.scenario_row
    name = run.ctx.cp2a.fact(f"T2B.1.{row}.name")
    decline = run.ctx.cp2a.fact(f"T2B.1.{row}.ebitda_decline")
    cp1_ebitda = _cp1_ebitda(run.cp1["ebitda"])
    for v in run.sub.valuation:
        r, val = v.case_id, run.values[v.case_id]
        f = val.source.fact
        period = str(f.period)
        b.text(("T4E.3", r, "scenario"), "Valuation", v.label, value_class="analyst_judgment")
        b.text(
            ("T4E.3", r, "ebitda_basis"),
            "EBITDA basis",
            f"CP-2G {CASE_WORD[v.ebitda_case]} case {v.ebitda_year}",
        )
        if val.ebitda.amount is None:
            assert val.ebitda.reason is not None
            b.gap(
                ("T4E.3", r, "ebitda"),
                "EBITDA",
                "amount",
                val.ebitda.reason,
                period=period,
                status=_copy_status(f),
            )
        else:
            b.num(
                ("T4E.3", r, "ebitda"),
                "EBITDA",
                val.ebitda.amount,
                "amount",
                f"Copy of CP-2G {f.fact_id}",
                period=period,
                derives=(f"cp2g:{f.fact_id}",),
            )
        if val.multiple is None:
            b.gap(("T4E.3", r, "multiple"), "EV multiple", "multiple", R_EV_NA, period=period)
        else:
            b.num(
                ("T4E.3", r, "multiple"),
                "EV multiple",
                val.multiple,
                "multiple",
                "analyst input",
                period=period,
                value_class="analyst_judgment",
            )
        b.value(
            ("T4E.3", r, "ev"),
            "Enterprise value",
            val.ev,
            "amount",
            "EBITDA x EV multiple",
            (f"T4E.3.{r}.ebitda", f"T4E.3.{r}.multiple"),
            period=period,
        )
        if val.ev.amount is None or cp1_ebitda.amount is None:
            implied = val.ev if val.ev.amount is None else cp1_ebitda
        else:
            implied = Val(_div(val.ev.amount, cp1_ebitda.amount))
        b.value(
            ("T4E.3", r, "implied_ltm_multiple"),
            "Implied multiple of CP-1 EBITDA",
            implied,
            "multiple",
            "Enterprise value / CP-1 EBITDA",
            (f"T4E.3.{r}.ev", "cp1:ebitda"),
            period=LTM_PERIOD,
        )
        first = run.ctx.cp2g.first(v.ebitda_case)
        b.copy_text(
            ("T4E.3", r, "first_break"),
            "First year free cash flow at or below zero (CP-2G)",
            first,
            f"cp2g:{first.fact_id}",
        )
        if v.ebitda_case == "down":
            b.copy_text(
                ("T4E.3", r, "cp2a_scenario"), "CP-2A scenario", name, f"cp2a:{name.fact_id}"
            )
            if decline.status == "known" and decline.amount is not None:
                b.num(
                    ("T4E.3", r, "ebitda_decline"),
                    "CP-2A EBITDA decline",
                    decline.amount,
                    "percent",
                    f"Copy of CP-2A {decline.fact_id}",
                    period=LTM_PERIOD,
                    value_class=decline.value_class,
                    derives=(f"cp2a:{decline.fact_id}",),
                    keep_lineage=True,
                )
            else:
                b.gap(
                    ("T4E.3", r, "ebitda_decline"),
                    "CP-2A EBITDA decline",
                    "percent",
                    _upstream_reason(decline),
                    period=LTM_PERIOD,
                    status=_copy_status(decline),
                )
        else:
            b.unsettled_text(
                ("T4E.3", r, "cp2a_scenario"), "CP-2A scenario", NO_SCENARIO, "not_applicable"
            )
            b.gap(
                ("T4E.3", r, "ebitda_decline"),
                "CP-2A EBITDA decline",
                "percent",
                NO_SCENARIO,
                period=LTM_PERIOD,
                status="not_applicable",
            )
        b.row("T4E.3", r, v.label, _FIELDS_T4E3)


NC_EBITDA = "Not calculable: EBITDA is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
FIRST_BASE = "The first valuation is the comparison base"
NO_CLAIM = "Equity has no claim amount"
NO_RECOVERY = "Equity has no claim amount, so no recovery percentage"
FITS, UNDETERMINED = "Fits the waterfall", "Not determinable"


def _pp(a: Decimal, b: Decimal) -> Decimal:
    """Percent minus percent in percentage points: (a - b) in the 38-digit context, x 100."""
    with localcontext(_RATIO):
        return _exact((a - b).scaleb(2))


def _multiple_of(
    at: tuple[str, str, str],
    label: str,
    b: _Book,
    num: Val,
    ebitda: Val,
    formula: str,
    derives: Sequence[str],
    period: str,
) -> None:
    """Claims / EBITDA: missing with the numerator's reason, the EBITDA reason, or NC_EBITDA."""
    if num.amount is None:
        assert num.reason is not None
        b.gap(at, label, "multiple", num.reason, period=period)
    elif ebitda.amount is None:
        b.gap(at, label, "multiple", ebitda.reason or NC_EBITDA, period=period)
    elif ebitda.amount <= 0:
        b.gap(at, label, "multiple", NC_EBITDA, period=period)
    else:
        b.num(
            at,
            label,
            _div(num.amount, ebitda.amount),
            "multiple",
            formula,
            period=period,
            derives=derives,
        )


def _allocation(b: _Book, run: _Run) -> None:
    """T4E.4, T4E.5, T4E.6 and T4E.8, valuation by valuation, class by class, then equity."""
    first_case = run.sub.valuation[0].case_id
    treat = {p.case_id: {t.class_id: t.treatment for t in p.treatments} for p in run.sub.plan}
    classes = run.classes
    for v in run.sub.valuation:
        r0, w, val = v.case_id, run.falls[v.case_id], run.values[v.case_id]
        period = str(val.source.fact.period)
        for c, k in zip(run.sub.claims, classes, strict=True):
            x = w.classes[k.class_id]
            r = f"{r0}{k.class_id}"
            lab = f"{v.label} · {c.name}"
            better = [o for o in classes if o.rank < k.rank]
            same = [o for o in classes if o.rank == k.rank]
            b.value(
                ("T4E.4", r, "claim"),
                "Claim",
                k.claim,
                "amount",
                "From T4E.2",
                (f"T4E.2.{k.class_id}.claim",),
                period=period,
            )
            b.value(
                ("T4E.4", r, "value_available"),
                "Value available to the class",
                x.available,
                "amount",
                "Enterprise value less distributions to better-ranked classes",
                (f"T4E.3.{r0}.ev", *(f"T4E.4.{r0}{o.class_id}.distribution" for o in better)),
                period=period,
            )
            b.value(
                ("T4E.4", r, "distribution"),
                "Distribution",
                x.distribution,
                "amount",
                "Claim x value paid to the rank / total claims of the rank",
                (
                    f"T4E.4.{r}.claim",
                    f"T4E.4.{r}.value_available",
                    *(f"T4E.4.{r0}{o.class_id}.claim" for o in same),
                ),
                period=period,
            )
            b.value(
                ("T4E.4", r, "shortfall"),
                "Shortfall",
                x.shortfall,
                "amount",
                "Claim - distribution",
                (f"T4E.4.{r}.claim", f"T4E.4.{r}.distribution"),
                period=period,
            )
            b.row("T4E.4", r, lab, ("claim", "value_available", "distribution", "shortfall"))
            b.value(
                ("T4E.5", r, "recovery"),
                "Recovery",
                x.recovery,
                "percent",
                "Value paid to the rank / total claims of the rank",
                (f"T4E.4.{r}.distribution", f"T4E.4.{r}.claim"),
                period=period,
            )
            base = run.falls[first_case].classes[k.class_id].recovery
            change = ("T4E.5", r, "vs_first_pp")
            change_label = "Change from first valuation"
            if r0 == first_case:
                b.gap(
                    change,
                    change_label,
                    "pp",
                    FIRST_BASE,
                    period=LTM_PERIOD,
                    status="not_applicable",
                )
            elif x.recovery.amount is None or base.amount is None:
                reason = x.recovery.reason or base.reason
                assert reason is not None
                b.gap(change, change_label, "pp", reason, period=LTM_PERIOD)
            else:
                b.num(
                    change,
                    change_label,
                    _pp(x.recovery.amount, base.amount),
                    "pp",
                    "(recovery - first-valuation recovery) x 100, percentage points",
                    period=period,
                    derives=(f"T4E.5.{r}.recovery", f"T4E.5.{first_case}{k.class_id}.recovery"),
                )
            b.row("T4E.5", r, lab, ("recovery", "vs_first_pp"))
            b.value(
                ("T4E.6", r, "claims_ahead"),
                "Claims ahead",
                x.ahead,
                "amount",
                "Claims of better-ranked classes",
                tuple(f"T4E.4.{r0}{o.class_id}.claim" for o in better),
                period=period,
            )
            b.value(
                ("T4E.6", r, "claims_through"),
                "Claims through the class",
                x.through,
                "amount",
                "Claims ahead + claims of the rank",
                tuple(f"T4E.4.{r0}{o.class_id}.claim" for o in classes if o.rank <= k.rank),
                period=period,
            )
            _multiple_of(
                ("T4E.6", r, "attach_multiple"),
                "Attachment multiple",
                b,
                x.ahead,
                val.ebitda,
                "Claims ahead / EBITDA",
                (f"T4E.6.{r}.claims_ahead", f"T4E.3.{r0}.ebitda"),
                period,
            )
            _multiple_of(
                ("T4E.6", r, "detach_multiple"),
                "Detachment multiple",
                b,
                x.through,
                val.ebitda,
                "Claims through the class / EBITDA",
                (f"T4E.6.{r}.claims_through", f"T4E.3.{r0}.ebitda"),
                period,
            )
            b.row(
                "T4E.6",
                r,
                lab,
                ("claims_ahead", "claims_through", "attach_multiple", "detach_multiple"),
            )
            b.text(
                ("T4E.8", r, "treatment"),
                "Treatment",
                treat[r0][k.class_id],
                value_class="analyst_judgment",
            )
            known = x.recovery.amount is not None
            b.text(
                ("T4E.8", r, "fit"),
                "Fit with the waterfall",
                FITS if known else UNDETERMINED,
                derives=(f"T4E.5.{r}.recovery",) if known else (),
            )
            b.row("T4E.8", r, lab, ("treatment", "fit"))
        r = f"{r0}eq"
        lab = f"{v.label} · Equity"
        b.gap(
            ("T4E.4", r, "claim"),
            "Claim",
            "amount",
            NO_CLAIM,
            period=period,
            status="not_applicable",
        )
        b.value(
            ("T4E.4", r, "value_available"),
            "Value available to the class",
            w.residual,
            "amount",
            "Enterprise value less all creditor distributions",
            (f"T4E.3.{r0}.ev", *(f"T4E.4.{r0}{o.class_id}.distribution" for o in classes)),
            period=period,
        )
        b.value(
            ("T4E.4", r, "distribution"),
            "Distribution",
            w.residual,
            "amount",
            "Residual value",
            (f"T4E.4.{r}.value_available",),
            period=period,
        )
        b.gap(
            ("T4E.4", r, "shortfall"),
            "Shortfall",
            "amount",
            NO_CLAIM,
            period=period,
            status="not_applicable",
        )
        b.row("T4E.4", r, lab, ("claim", "value_available", "distribution", "shortfall"))
        b.gap(
            ("T4E.5", r, "recovery"),
            "Recovery",
            "percent",
            NO_RECOVERY,
            period=period,
            status="not_applicable",
        )
        b.gap(
            ("T4E.5", r, "vs_first_pp"),
            "Change from first valuation",
            "pp",
            NO_RECOVERY,
            period=period,
            status="not_applicable",
        )
        b.row("T4E.5", r, lab, ("recovery", "vs_first_pp"))
        b.text(
            ("T4E.8", r, "treatment"),
            "Treatment",
            treat[r0][EQUITY],
            value_class="analyst_judgment",
        )
        known = w.residual.amount is not None
        b.text(
            ("T4E.8", r, "fit"),
            "Fit with the waterfall",
            FITS if known else UNDETERMINED,
            derives=(f"T4E.4.{r}.distribution",) if known else (),
        )
        b.row("T4E.8", r, lab, ("treatment", "fit"))


def _joined(names: Sequence[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


EQUITY_BREAK = "Equity (every creditor class is paid in full)"
NOT_IMPAIRED = "No creditor class is impaired"
_FIELDS_T4E7 = ("value_break", "analyst_fulcrum", "agreement", "ev_cover", "break_multiple")
_FIELDS_T4E9 = ("ev", "total_claims", "creditor_distributions", "equity_residual", "balance")


def _fulcrum_and_totals(b: _Book, run: _Run) -> None:
    names = {c.class_id: c.name for c in run.sub.claims}
    ids = [k.class_id for k in run.classes]
    named = {f.case_id: f.class_ids for f in run.sub.fulcrum}
    for v in run.sub.valuation:
        r, w, val = v.case_id, run.falls[v.case_id], run.values[v.case_id]
        period = str(val.source.fact.period)
        brk = w.value_break
        if brk is None:
            assert w.break_reason is not None
            b.unsettled_text(
                ("T4E.7", r, "value_break"), "Where value breaks", w.break_reason, "missing"
            )
        elif brk == (EQUITY,):
            b.text(
                ("T4E.7", r, "value_break"),
                "Where value breaks",
                EQUITY_BREAK,
                derives=tuple(f"T4E.5.{r}{i}.recovery" for i in ids),
            )
        else:
            b.text(
                ("T4E.7", r, "value_break"),
                "Where value breaks",
                _joined([names[i] for i in brk]),
                derives=tuple(f"T4E.5.{r}{i}.recovery" for i in brk),
            )
        judged = named[r]
        b.text(
            ("T4E.7", r, "analyst_fulcrum"),
            "Fulcrum named by the analyst",
            _joined(["Equity" if i == EQUITY else names[i] for i in judged])
            if judged
            else "None named",
            value_class="analyst_judgment",
        )
        agrees = brk is not None and sorted(judged) == sorted(brk)
        if brk is not None and not agrees:  # content_issues refuses this before composition
            raise ValueError(f"CP-4C: the analyst's fulcrum of {r} disagrees with the waterfall")
        b.text(
            ("T4E.7", r, "agreement"),
            "Agreement",
            "Agrees with the waterfall" if agrees else "Value break not determinable",
            derives=(f"T4E.7.{r}.value_break", f"T4E.7.{r}.analyst_fulcrum")
            if brk is not None
            else (),
        )
        ev, total = val.ev, w.total_claims
        if ev.amount is None or total.amount is None:
            cover = ev if ev.amount is None else total
        else:
            cover = Val(_div(ev.amount, total.amount))
        b.value(
            ("T4E.7", r, "ev_cover"),
            "Enterprise value / total claims",
            cover,
            "multiple",
            "Enterprise value / total claims",
            (f"T4E.3.{r}.ev", f"T4E.9.{r}.total_claims"),
            period=period,
        )
        at, label = (
            ("T4E.7", r, "break_multiple"),
            "EBITDA multiple needed to cover the fulcrum class",
        )
        if brk == (EQUITY,):
            b.gap(at, label, "multiple", NOT_IMPAIRED, period=period, status="not_applicable")
        elif brk is None:
            assert w.break_reason is not None
            b.gap(at, label, "multiple", w.break_reason, period=period)
        else:
            assert w.break_through is not None
            _multiple_of(
                at,
                label,
                b,
                Val(w.break_through),
                val.ebitda,
                "Claims through the fulcrum rank / EBITDA",
                (f"T4E.6.{r}{brk[0]}.detach_multiple",),
                period,
            )
        b.row("T4E.7", r, v.label, _FIELDS_T4E7)
        dists = [w.classes[i].distribution for i in ids]
        blocked = next((d for d in dists if d.amount is None), None)
        if blocked is None:  # summed exactly, never in the rounding context (round 8 A-1 #5)
            paid = Val(_exact_sum([a for d in dists if (a := d.amount) is not None]))
        else:
            paid = blocked
        b.value(
            ("T4E.9", r, "ev"),
            "Enterprise value",
            ev,
            "amount",
            "From T4E.3",
            (f"T4E.3.{r}.ev",),
            period=period,
        )
        b.value(
            ("T4E.9", r, "total_claims"),
            "Total creditor claims",
            total,
            "amount",
            "Sum of the claims of the creditor classes",
            tuple(f"T4E.2.{i}.claim" for i in ids),
            period=period,
        )
        b.value(
            ("T4E.9", r, "creditor_distributions"),
            "Distributions to creditors",
            paid,
            "amount",
            "Sum of creditor distributions",
            tuple(f"T4E.4.{r}{i}.distribution" for i in ids),
            period=period,
        )
        b.value(
            ("T4E.9", r, "equity_residual"),
            "Residual to equity",
            w.residual,
            "amount",
            "From T4E.4",
            (f"T4E.4.{r}eq.distribution",),
            period=period,
        )
        e, dsum, left = ev.amount, paid.amount, w.residual.amount
        if e is None or left is None:
            balance = ev if e is None else w.residual
        elif dsum is None:  # a blocked share blocks the residual too
            raise ValueError(f"CP-4C: {r} has a residual but a missing share; invariant broken")
        else:
            gap = _exact_sum([e, dsum.copy_negate(), left.copy_negate()])
            if gap != 0:  # the exact allocation conserves the enterprise value (round 8 A-1 #5)
                raise AssertionError(f"CP-4C: T4E.9 of {r} is off by {gap}; conservation broken")
            balance = Val(gap)
        b.value(
            ("T4E.9", r, "balance"),
            "Balance",
            balance,
            "amount",
            "Enterprise value - creditor distributions - residual",
            (f"T4E.9.{r}.ev", f"T4E.9.{r}.creditor_distributions", f"T4E.9.{r}.equity_residual"),
            period=period,
        )
        b.row("T4E.9", r, v.label, _FIELDS_T4E9)


def _t4e10(b: _Book, run: _Run) -> None:
    for n, gap in enumerate(run.sub.gaps, 1):
        r = f"g{n:02d}"
        b.text(("T4E.10", r, "id"), "Gap id", f"CP-4C-GAP-{n:03d}")
        for name, label in (
            ("gap", "Gap"),
            ("why_it_matters", "Why it matters"),
            ("affected_analysis", "Affected analysis"),
        ):
            b.text(("T4E.10", r, name), label, getattr(gap, name), value_class="analyst_judgment")
        b.text(("T4E.10", r, "severity"), "Severity", gap.severity)
        b.text(("T4E.10", r, "action"), "Action", gap.action, value_class="analyst_judgment")
        b.row(
            "T4E.10",
            r,
            f"Gap {n}",
            ("id", "gap", "why_it_matters", "affected_analysis", "severity", "action"),
        )


def _references(
    sub: RestructuringSubmission, ctx: Cp4cContext
) -> tuple[RefTable, RefTable, RefTable, RefTable]:
    """The four reference tables: the upstream facts verbatim (expected.references_rule)."""
    cp1 = select_cp1(ctx.cp1.t410)
    cp1_rows = [
        Reference(f"ref{n:02d}", f"{cp1[m].label} · {cp1[m].period}", cp1[m])
        for n, m in enumerate(CP1_METRICS, 1)
    ]
    for f in (ctx.cp1.secured_status, ctx.cp1.seniority):
        label = f"T4.18 · {ctx.cp1.facility_id} · {f.field} · {f.period}"
        cp1_rows.append(Reference(f"ref{len(cp1_rows) + 1:02d}", label, f))
    used: dict[str, Fact] = {}
    for v in sub.valuation:
        f = ctx.cp2g.of(v.ebitda_case, v.ebitda_year).fact
        used.setdefault(f.fact_id, f)  # one row per distinct fact id
    cp2g_facts = [*used.values(), ctx.cp2g.base_first, ctx.cp2g.down_first]
    row = _scenario_row(ctx.cp2g)
    cp2a_facts = [ctx.cp2a.fact(f"T2B.1.{row}.{name}") for name in ("name", *_SHOCKS)]
    cp4_facts = [ctx.cp4.fact(fid) for fid in CP4_FACTS]

    def refs(facts: Sequence[Fact]) -> tuple[Reference, ...]:
        return tuple(Reference(f"ref{n:02d}", f.label, f) for n, f in enumerate(facts, 1))

    return (
        RefTable(
            "cp1_references",
            "CP-1 facts referenced in CP-4C text and copied into T4E.2 and T4E.3",
            "CP-1 fact",
            tuple(cp1_rows),
        ),
        RefTable(
            "cp2g_references",
            "CP-2G facts read by CP-4C (T2H.4 EBITDA, T2H.7 first year of the free cash flow test)",
            "CP-2G fact",
            refs(cp2g_facts),
        ),
        RefTable(
            "cp2a_references",
            "CP-2A facts read by CP-4C (T2B.1 scenario applied by CP-2G)",
            "CP-2A fact",
            refs(cp2a_facts),
        ),
        RefTable(
            "cp4_references",
            "CP-4 facts read by CP-4C (T4C.11, T4.10, T4.13)",
            "CP-4 fact",
            refs(cp4_facts),
        ),
    )


VAL_LIMIT = "Valuation on analyst-assumed multiples"


def _figures(text: str) -> list[str]:
    return [run.text for run in prose.tokenize(text) if run.figure]


def _claims(b: _Book, run: _Run, references: Sequence[RefTable]) -> tuple[Claim, ...]:
    upstream = {r.fact.fact_id for t in references for r in t.rows}

    def ref(fid: str, token: str) -> str:
        return "{" + fid + "|" + token + "}" if b.status(fid) == "known" else f"[{fid}]"

    def analyst(cid: str, text: str, limitation: str | None) -> Claim:
        return Claim(cid, text, limitation, tuple(f for f in _figures(text) if f in upstream))

    sub = run.sub
    out = [analyst(f"T4E.2.{c.class_id}.rationale", c.rationale, c.limitation) for c in sub.claims]
    out += [
        analyst(f"T4E.3.{v.case_id}.rationale", v.rationale, v.limitation) for v in sub.valuation
    ]
    for v in sub.valuation:
        r, lab = v.case_id, v.label.lower()
        out.append(
            Claim(
                f"T4E.3.{r}.ev",
                f"In the {lab} valuation, enterprise value is {ref(f'T4E.3.{r}.ev', 'US$ m')} on "
                f"EBITDA of {ref(f'T4E.3.{r}.ebitda', 'US$ m')}.",
                VAL_LIMIT,
                (),
            )
        )
    for v in sub.valuation:
        r, lab = v.case_id, v.label.lower()
        parts = "; ".join(
            f"{c.name} {ref(f'T4E.5.{r}{c.class_id}.recovery', '%')}" for c in sub.claims
        )
        out.append(
            Claim(
                f"T4E.5.{r}",
                f"In the {lab} valuation the classes recover as follows: {parts}.",
                VAL_LIMIT,
                (),
            )
        )
    out += [analyst(f"T4E.7.{f.case_id}.rationale", f.rationale, f.limitation) for f in sub.fulcrum]
    names = {c.class_id: c.name for c in sub.claims}
    for v in sub.valuation:
        r, lab, brk = v.case_id, v.label.lower(), run.falls[v.case_id].value_break
        if brk is None:
            text = (
                f"In the {lab} valuation the fulcrum cannot be determined: [T4E.7.{r}.value_break]."
            )
        elif brk == (EQUITY,):
            text = (
                f"In the {lab} valuation every creditor class is paid in full and equity is the "
                "residual claimant."
            )
        else:
            one = len(brk) == 1
            text = (
                f"In the {lab} valuation value breaks at {_joined([names[i] for i in brk])}, which "
                f"{'is' if one else 'are'} the fulcrum; {'it is' if one else 'they are'} covered "
                f"in full only at an EBITDA multiple of {ref(f'T4E.7.{r}.break_multiple', 'x')}."
            )
        out.append(Claim(f"T4E.7.{r}.fulcrum", text, VAL_LIMIT, ()))
    out += [analyst(f"T4E.8.{p.case_id}.rationale", p.rationale, p.limitation) for p in sub.plan]
    a = sub.assessment
    out.append(analyst("T4E.3.assessment", a.rationale, a.limitation))
    return tuple(out)


_FIXED_LIMITATIONS = (
    (
        "Multiples, claim ranks and plan treatment are analyst assumptions without a source "
        "citation; no market or restructuring-plan source is an input."
    ),
    (
        "Value available to claims is the enterprise value only: balance-sheet cash is not added and "
        "restructuring, administrative and financing costs are not deducted unless a claim class "
        "states them."
    ),
    (
        "The waterfall applies strict priority by the analyst's rank number; classes of one rank "
        "share pro rata. Collateral value, guarantees, structural subordination and intercreditor "
        "terms are not modelled."
    ),
    (
        "Claims are the 31 December 2025 balances: accrued interest, fees, make-whole amounts, lease "
        "and pension claims, contingent and rejection-damage claims are not stated in any source and "
        "are not modelled; they are not zero."
    ),
    (
        "New-money or priming debt is not modelled: the legal source requires the consent of every "
        "lender for additional debt, so no debt-in-possession financing is assumed."
    ),
    (
        "Enterprise value is the analyst's multiple applied to a CP-2G forecast EBITDA that rests on "
        "analyst-assumed drivers; it is not a market or court valuation."
    ),
    (
        "The fulcrum is the first rank whose recovery is below its claim; the analyst's named fulcrum "
        "is checked against it. Plan treatment is checked for fit with the recovery, not for legal "
        "feasibility."
    ),
    (
        "Recoveries are not probability-weighted and the valuations are not scenarios of equal "
        "likelihood."
    ),
    CP3C_UNREAD,
    (
        "The lender protection rating is read from CP-4 and stays Insufficient Information: security, "
        "guarantee, default, cure and voting terms are not supplied."
    ),
)
_NC = "Not calculable: "


def _own_limitations(run: _Run) -> tuple[str, ...]:
    out = list(_FIXED_LIMITATIONS)
    for k in run.classes:
        if k.claim.amount is None:
            reason = str(k.claim.reason).replace(_NC, "")
            out.append(
                f"The claim of {k.name} is not available: {reason}; every recovery at or below "
                "its rank is Not calculable."
            )
    for v in run.sub.valuation:
        ev = run.values[v.case_id].ev
        if ev.amount is None:
            reason = str(ev.reason).replace(_NC, "")
            out.append(
                f"The enterprise value of the {v.label.lower()} valuation is not available: "
                f"{reason}; every recovery in it is Not calculable."
            )
    for v in run.sub.valuation:
        if run.falls[v.case_id].value_break is None and run.values[v.case_id].ev.amount is not None:
            out.append(
                f"The fulcrum of the {v.label.lower()} valuation cannot be determined, so the "
                "analyst names none."
            )
    out += [f"Gap ({g.severity}): {g.gap}" for g in run.sub.gaps]
    return tuple(out)


def compute(inputs: Cp4cInputs) -> RestructuringResult:
    """The restructuring waterfall of one valid submission. Raises ValueError on any issue, on a
    fail-closed state (round 8 A-2 #4, #13, A-1 state 14) or a broken invariant, and
    AssertionError if T4E.9 does not balance exactly."""
    run = _resolve(inputs)
    b = _Book()
    _t4e1(b, run)
    _t4e2(b, run)
    _t4e3(b, run)
    _allocation(b, run)
    _fulcrum_and_totals(b, run)
    _t4e10(b, run)
    references = _references(run.sub, run.ctx)
    claims = _claims(b, run, references)
    cells = b.cells(run.upstream)
    bound = prose.bind((*(c.fact for c in cells), *(r.fact for t in references for r in t.rows)))
    names = (run.ctx.pack.run.issuer_name,)
    for claim in claims:  # Python wording around analyst names (class names, labels) must hold
        found = prose.issues(claim.text, bound, names=names)
        if found:
            raise ValueError(
                f"CP-4C: claim {claim.claim_id} is not valid run text ({'; '.join(found)}): a "
                "class name or valuation label carries a figure or a reserved character; an "
                "invariant raise (round 8 A-2 #9)"
            )
    return RestructuringResult(
        cells=cells,
        tables=tuple(Table(t, title, tuple(b.rows[t])) for t, title in TABLES.items()),
        references=references,
        claims=claims,
        own_limitations=_own_limitations(run),
        waterfalls=run.falls,
        enterprise_values={k: v.ev for k, v in run.values.items()},
    )
