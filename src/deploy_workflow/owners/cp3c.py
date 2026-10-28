"""CP-3C (Refinancing and liability-management risk): the module's pure calculation (Stage 1).

Lease: docs/CP3C-OWNER-LEASE.md (rev 3, frozen). Python computes, from the CP-1 head facts and
the settled CP-2D cells the lease binds, the principal payable at each maturity, the resources
available then, the refinancing need, the cost of an analyst margin step-up on interest cover
and the claims at or ahead of each facility. The analyst supplies only the step-up (or its
absence) and one feasibility judgment per refinancing path. No optional edge is read.

Missing is never 0: a value that is not calculated is a ``Gap`` carrying its reason, the first
missing operand in formula order (LEAD rulings round 5, C-2 and C-6, which extend the frozen
lease and oracle). Each reason and claim form is one the oracle (cases/cp3c-owner/expected.json)
or a ruling fixes; an input state no ruling settles raises ValueError rather than invent one.
Nothing here does I/O or touches a store, host, session or renderer. Connection, tool-use and
orchestration seams (G1-X protocol section 2) are added to this file in later stages.
"""

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from dataclasses import field as _field
from datetime import date
from decimal import ROUND_HALF_UP, Context, Decimal, localcontext
from typing import Final, Literal

from deploy_vii import prose
from deploy_vii.business_context import prohibited_issues
from deploy_vii.contracts import Contract, Fact, Identifier, Text
from deploy_vii.display import format_date
from deploy_vii.report_view import fact_spelling, figure_unit
from deploy_workflow.owners.blank import is_blank

MODULE_ID = "CP-3C"
BPS_BOUNDS = (0, 1000)

# The product's four statuses (round 13 R1 L1, the CP-4C pattern); a head fact keeps its own.
Status = Literal["known", "missing", "conflicting", "not_applicable"]
CellStatus = Status
ValueClass = Literal["source", "calculated", "analyst_judgment"]
PathKind = Literal[
    "repay_from_resources",
    "amend_and_extend",
    "market_refinancing",
    "asset_sale_or_equity",
    "liability_management",
]
Feasibility = Literal["High", "Medium", "Low", "Insufficient Information"]
Category = Literal["Analyst Interpretation", "Insufficient Information"]

II: Final = "Insufficient Information"
KINDS: tuple[PathKind, ...] = (
    "repay_from_resources",
    "amend_and_extend",
    "market_refinancing",
    "asset_sale_or_equity",
    "liability_management",
)
KIND_LABEL: Mapping[PathKind, str] = {
    "repay_from_resources": "Repay from internal resources",
    "amend_and_extend": "Amend and extend",
    "market_refinancing": "Market refinancing",
    "asset_sale_or_equity": "Asset sale or equity support",
    "liability_management": "Liability-management exercise",
}

# The oracle's builder computes at 60 significant digits (cases/cp3c-owner/builder/build.py
# sets getcontext().prec = 60); this is that precision, fixed here so a caller's context cannot
# change a stored value. Ratios are then stored at 4 dp half-up
# (manifest.json#ratio_storage_rule); amounts keep every digit.
_CONTEXT = Context(prec=60)
_FOUR_DP = Decimal("0.0001")
_ZERO = Decimal(0)
_MONTHS_PER_YEAR = Decimal(12)
_BP_PER_UNIT = Decimal(10000)

# --- submission (judgment and references only; lease "Submission schema") --------------------


class StepUp(Contract):
    """An uncited analyst margin step-up in basis points (decision D11)."""

    bps: int
    rationale: Text


class RepricingAbsence(Contract):
    reason: Text
    follow_up: Text


class PathAssessment(Contract):
    kind: PathKind
    feasibility: Feasibility
    category: Category
    text: Text
    credit_implication: Text
    basis_refs: tuple[Identifier, ...]
    limitation: str | None


class RefinancingRiskSubmission(Contract):
    repricing: StepUp | None
    repricing_absence: RepricingAbsence | None
    paths: tuple[PathAssessment, ...]


# --- validator (lease "Refusals"; wording fixed by expected.json#refusals) ---------------------

_BOTH = "repricing: give repricing or repricing_absence, not both"
_NEITHER = "repricing: give repricing or repricing_absence"
_BPS = f"repricing.bps: must be between {BPS_BOUNDS[0]} and {BPS_BOUNDS[1]}"
_ONE_PER_KIND = "paths: must hold exactly one row per kind"
_LME = (
    "paths[liability_management].feasibility: needs legal covenant capacity evidence, "
    "which is not bound; state Insufficient Information"
)
_DIGIT = re.compile(r"\d")


def _word(phrase: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z]){re.escape(phrase)}(?![A-Za-z])", re.IGNORECASE)


def _near(phrase: str, noun: str) -> re.Pattern[str]:
    """The phrase within four words of the noun, either side (the product guard's shape)."""
    bounded = rf"(?<![A-Za-z])(?:{re.escape(phrase)})(?![A-Za-z])"
    gap = r"(?:\W+\w+){0,4}?\W+"
    return re.compile(rf"{bounded}{gap}{noun}\b|\b{noun}{gap}{bounded}", re.IGNORECASE)


# The core-local check (lease "Refusals", expected.json#prohibited_guard.core_local): whole
# phrases first, then compliance words within four words of "covenant(s)".
_LOCAL_WORD: tuple[tuple[str, str], ...] = (
    ("covenant compliance", "headroom is sufficient"),
    ("recovery conclusion", "fulcrum"),
    ("refinancing outcome", "will be refinanced"),
    ("refinancing outcome", "will refinance"),
    ("refinancing outcome", "refinancing is assured"),
    ("refinancing outcome", "refinancing is certain"),
    ("refinancing outcome", "will default"),
)
_LOCAL_NEAR_COVENANT = (
    "complies",
    "complied",
    "complying",
    "compliant",
    "compliance",
    "breach",
    "breaches",
    "breached",
    "met",
    "satisfied",
)
_LOCAL_GUARD: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    *((kind, phrase, _word(phrase)) for kind, phrase in _LOCAL_WORD),
    *(
        ("covenant compliance", phrase, _near(phrase, r"(?:covenants?)"))
        for phrase in _LOCAL_NEAR_COVENANT
    ),
)


def prohibited_conclusions(path: str, text: str) -> tuple[str, ...]:
    """The product phrase guard (CP-1A default kinds), then the core-local check, one issue
    per matching phrase. A guard over phrases, not a semantic review (lease guard limits)."""
    local = tuple(
        f'{path}: prohibited conclusion ({kind}): "{phrase}"'
        for kind, phrase, pattern in _LOCAL_GUARD
        if pattern.search(text)
    )
    return prohibited_issues(path, text) + local


def _text_fields(s: RefinancingRiskSubmission) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    if s.repricing is not None and s.repricing_absence is None:
        fields.append(("repricing.rationale", s.repricing.rationale))
    elif s.repricing is None and s.repricing_absence is not None:
        fields.append(("repricing_absence.reason", s.repricing_absence.reason))
        fields.append(("repricing_absence.follow_up", s.repricing_absence.follow_up))
    for p in s.paths:
        fields.append((f"paths[{p.kind}].text", p.text))
        fields.append((f"paths[{p.kind}].credit_implication", p.credit_implication))
        if p.limitation:
            fields.append((f"paths[{p.kind}].limitation", p.limitation))
    return fields


def submission_issues(
    *, submission: RefinancingRiskSubmission, offered: Mapping[str, str]
) -> tuple[str, ...]:
    """Validator issues in the oracle's order (expected.json#refusal_order). ``offered`` maps
    each ref the read view offers to its binding name (manifest.json#fact_bindings)."""
    s = submission
    issues: list[str] = []
    if s.repricing is not None and s.repricing_absence is not None:
        issues.append(_BOTH)
    elif s.repricing is None and s.repricing_absence is None:
        issues.append(_NEITHER)
    if s.repricing is not None and not BPS_BOUNDS[0] <= s.repricing.bps <= BPS_BOUNDS[1]:
        issues.append(_BPS)
    if sorted(p.kind for p in s.paths) != sorted(KINDS):
        issues.append(_ONE_PER_KIND)
    for field, text in _text_fields(s):
        # Round 11 blank text (R3 M1) and round 12 B10, in the fallback frame (CP-3C pins none).
        # A limitation is not here: a blank one is B5's, below. `""` stays the schema's refusal.
        if not field.endswith(".limitation") and is_blank(text):
            issues.append(f"{field}: empty text")
        if _DIGIT.search(text):
            issues.append(f"{field}: must not contain a figure")
        issues.extend(prohibited_conclusions(field, text))
    for p in s.paths:
        at = f"paths[{p.kind}]"
        issues.extend(
            f"{at}.basis_refs: names a fact the view does not offer"
            for ref in p.basis_refs
            if ref not in offered
        )
        insufficient = p.category == II
        if (p.feasibility == II) != insufficient:
            issues.append(
                f"{at}.feasibility: must be Insufficient Information exactly when the category is"
            )
        if insufficient and is_blank(p.limitation or ""):  # round 11 B5, B10: blank is none
            issues.append(
                f"{at}.limitation: an Insufficient Information assessment states its limitation"
            )
        if not insufficient and p.limitation:
            issues.append(
                f"{at}.limitation: only an Insufficient Information assessment carries a limitation"
            )
        if p.feasibility != II and not p.basis_refs:
            issues.append(
                f"{at}.basis_refs: a High, Medium or Low feasibility cites at least one fact"
            )
        if p.kind == "liability_management" and p.feasibility != II:
            issues.append(_LME)
    return tuple(issues)


# --- inputs (Stage 2 binds them from the CP-1 and CP-2D heads) ---------------------------------


def _check_value(
    what: str, status: Status, amount: Decimal | None, text: str | None, reason: str | None
) -> None:
    if status == "known" and (amount is None) == (text is None):
        raise ValueError(f"{what}: a known fact carries exactly one of amount or text")
    if status == "known" and reason is not None:
        raise ValueError(f"{what}: a known fact carries no reason")
    if status != "known" and (amount is not None or text is not None or not reason):
        raise ValueError(f"{what}: a {_STATE_WORD[status]} fact carries a reason and no value")


@dataclass(frozen=True)
class Cp1Fact:
    """One CP-1 head fact a binding names (manifest.json#fact_bindings), as read: never defaulted.

    Amounts are US$ m with unit MILLIONS. A T4.18 amount the head states in unit ``currency``
    (USD, scale 1e6) is normalised to MILLIONS by the Stage 2 binding, as CP-2D's copy rule does.
    """

    table_id: str  # T4.10 or T4.18
    period: str  # the head fact's own period label
    status: Status
    amount: Decimal | None = None
    text: str | None = None
    unit: str | None = None
    value_class: ValueClass | None = None  # the head fact's own (kept by a copied cell)
    reason: str | None = None  # the head fact's limitation when it is not known
    currency: str | None = None  # the head fact's own currency (round 13 item 5)

    def __post_init__(self) -> None:
        _check_value(f"CP-1 {self.table_id}", self.status, self.amount, self.text, self.reason)


@dataclass(frozen=True)
class Cp2dFact:
    """One settled CP-2D cell, named by its stable fact id; a missing cell keeps its reason."""

    fact_id: str
    status: Status
    amount: Decimal | None = None
    text: str | None = None
    unit: str | None = None
    period: str | None = None
    value_class: ValueClass | None = None
    reason: str | None = None
    currency: str | None = None  # the cell's own currency (round 13 item 5)

    def __post_init__(self) -> None:
        _check_value(f"CP-2D {self.fact_id}", self.status, self.amount, self.text, self.reason)


@dataclass(frozen=True)
class FacilityTerms:
    """The CP-1 T4.18 terms of one facility (QUARTER period over its FY alias)."""

    facility_id: str
    # The T4.18 row's own `currency` text fact, read by facility_id from the row the principal
    # comes from, never through financial_series._maturity_figure (ruling A5, amending C-7).
    # None: the fact is absent or not known (round 8 B6).
    currency: str | None
    facility_name: Cp1Fact
    secured_status: Cp1Fact
    seniority: Cp1Fact
    annual_amortisation: Cp1Fact


@dataclass(frozen=True)
class Cp1Operands:
    cash_closing: Cp1Fact
    undrawn_rcf: Cp1Fact
    adjusted_ebitda: Cp1Fact
    cash_interest: Cp1Fact  # the LTM outflow as CP-1 states it (negative); its magnitude is paid
    facilities: tuple[FacilityTerms, ...]


@dataclass(frozen=True)
class WallRow:
    """One CP-2D maturity-wall row (T2E.4): principal, maturity date, months, inside flag."""

    facility_id: str
    principal: Cp2dFact
    maturity_date: Cp2dFact
    months: Cp2dFact
    inside_horizon: Cp2dFact


@dataclass(frozen=True)
class Cp2dOperands:
    horizon: Cp2dFact  # T2E.3.r03
    run_rate: Cp2dFact  # T2E.3.r01, the run-rate annual flow F
    minimum_cash: Cp2dFact  # T2E.5.r04
    funding_gap: Cp2dFact  # T2E.5.r07
    wall: tuple[WallRow, ...]


@dataclass(frozen=True)
class Cp3cInputs:
    balance_date: date  # D0, CP-2D's
    as_of: date  # the run's as-of (the step-up's period)
    currency: str  # the reporting currency every summed amount is in
    cp1: Cp1Operands
    cp2d: Cp2dOperands
    submission: RefinancingRiskSubmission
    offered: Mapping[str, str]  # view ref -> binding name


# --- values that are known or carry the reason they are not (rulings C-2, C-6) ----------------


@dataclass(frozen=True)
class Gap:
    """A value that is not calculated, with its reason: missing, or not meaningful (shown as
    not_applicable) when ``applicable`` is False. Missing is never 0."""

    reason: str
    applicable: bool = True
    # Round 11 Q3: the claim cause frame of a facility gap, set where the gap is made (by its
    # kind, never by comparing reasons); None takes the reason less its prefix.
    cause: str | None = _field(default=None, compare=False)


Num = Decimal | Gap

_NOT_CALCULABLE = "Not calculable: "
_NM = " (ZERO_OR_NEGATIVE_DENOMINATOR)"


def missing_reason(label: str) -> str:
    """Ruling C-2 (the 2D-b frame): the reason of a missing operand and its dependants."""
    return f"{_NOT_CALCULABLE}{label} is missing"


# Reasons fixed by the oracle (expected.json cells) and by rulings C-2 and C-6.
REASON_MINIMUM_CASH = "Not calculable: minimum cash not assessed"
REASON_STEP_UP = "Not calculable: margin step-up not assessed"
REASON_LME = "Not calculable: liability-management capacity evidence is not bound"
REASON_STRESS = "Not calculable: no stressed case is bound"
STEP_UP_NOT_ASSESSED = "Margin step-up not assessed"
NOT_STATED = "Not calculable: facility {fid} {term} is not stated"
FX_REASON = "Not calculable: facility {fid} is in {ccy}, not {base}; no FX conversion is applied"
NOT_IN = "Not calculable: facility {fid} is not in the {source}"
NO_FACILITY = "Not calculable: no facility is in the CP-1 debt register"
NM_EBITDA = "Not meaningful: adjusted EBITDA is zero or negative" + _NM
NM_PAYABLE = "Not meaningful: principal payable at maturity is zero" + _NM
NM_INTEREST = "Not meaningful: cash interest paid is zero or negative" + _NM
NM_TOTAL = "Not meaningful: total facility principal is zero" + _NM
# Round 8 B6 (the 2D-c, 2D-b and D-4/L2 frames).
CURRENCY_UNSTATED = (
    "Not calculable: facility {fid} currency is not stated; no FX conversion is applied"
)
HORIZON_MISSING = missing_reason("CP-2D horizon")
PRE_D0 = "Not calculable: facility {fid} maturity date is before the balance date"  # round 11 B1
# Round 11 Q3 cause frames (no facility id; CP-2D L5), and round 8 B2's FX frame.
_UNSTATED_CAUSE = "the total needs every facility with its {term} stated, and one is not"
_UNMATCHED_CAUSE = (
    "the total needs every facility in both the CP-1 debt register and the CP-2D maturity wall, "
    "and one is not"
)
_PRE_D0_CAUSE = (
    "the total needs every facility to mature on or after the balance date, and one does not"
)
_FX_CAUSE = "the total needs every facility in USD, and one is not"


def _unstated_gap(fid: str, term: str) -> Gap:
    return Gap(NOT_STATED.format(fid=fid, term=term), cause=_UNSTATED_CAUSE.format(term=term))


NM_TOTAL_NEGATIVE = "Not meaningful: total facility principal is negative" + _NM


# an unsettled head fact's status as its dependants' reason names it (round 13 R1 L1, as CP-4C)
_STATE_WORD: Mapping[Status, str] = {
    "known": "known",
    "missing": "missing",
    "conflicting": "conflicting",
    "not_applicable": "not applicable",
}


def _op(value: Decimal | None, label: str, status: Status = "missing") -> Num:
    """The operand, or its gap: ``Not calculable: <label> is <missing|conflicting|not applicable>``
    (C-2 frame)."""
    if value is not None:
        return value
    return Gap(f"{_NOT_CALCULABLE}{label} is {_STATE_WORD[status]}")


def _first(*values: object) -> Gap | None:
    """The first gap in formula order, if any."""
    return next((v for v in values if isinstance(v, Gap)), None)


def _total(values: Iterable[Num]) -> Num:
    """Sum, or the first gap in formula order (a missing operand never defaults to zero)."""
    values = tuple(values)
    return _first(*values) or sum((v for v in values if not isinstance(v, Gap)), _ZERO)


def _diff(a: Num, b: Num) -> Num:
    if isinstance(a, Gap):
        return a
    if isinstance(b, Gap):
        return b
    return a - b


def _r4(x: Decimal) -> Decimal:
    return x.quantize(_FOUR_DP, rounding=ROUND_HALF_UP)


def _ratio(num: Num, den: Num, not_meaningful: str) -> Num:
    """num / den stored at 4 dp; a denominator <= 0 is not meaningful (ruling C-2)."""
    if isinstance(num, Gap):
        return num
    if isinstance(den, Gap):
        return den
    return Gap(not_meaningful, applicable=False) if den <= 0 else _r4(num / den)


# --- the composer (lease "Method"; every value a Decimal or a Gap) -----------------------------


@dataclass(frozen=True)
class FacilityOperand:
    facility_id: str
    principal: Num  # a Gap: another currency, currency or principal not stated (C-6, B6)
    maturity_date: date | Gap  # a Gap sorts after every dated facility (round 8 B6, 2D-c)
    months: int | Gap  # whole months from D0 (CP-2D's rule A1, recomputed)
    inside_horizon: bool | Gap  # maturity on or before the CP-2D horizon end
    annual_amortisation: Decimal | None  # None: not stated
    secured_status: str | None  # SECURED, UNSECURED or NOT_STATED; None is missing
    seniority: str | None


@dataclass(frozen=True)
class UnmatchedFacility:
    """A facility in only one of the CP-1 register and the CP-2D wall (ruling C-6)."""

    facility_id: str
    reason: str


@dataclass(frozen=True)
class Operands:
    """Every operand of the Method in US$ m; None is missing, never 0."""

    cash: Decimal | None
    undrawn_revolver: Decimal | None
    run_rate_annual: Decimal | None
    minimum_cash: Decimal | None
    adjusted_ebitda: Decimal | None
    cash_interest_paid: Decimal | None  # a positive magnitude
    facilities: tuple[FacilityOperand, ...]
    unmatched: tuple[UnmatchedFacility, ...] = ()
    # The status of each unsettled operand above, by field name; one absent here is missing.
    statuses: Mapping[str, Status] = _field(default_factory=dict)

    def status(self, name: str) -> Status:
        return self.statuses.get(name, "missing")


@dataclass(frozen=True)
class MaturityRow:
    facility: FacilityOperand
    amortisation_before_maturity: Num
    principal_payable: Num
    resources: Num
    applied: Num
    need: Num
    cover: Num


@dataclass(frozen=True)
class CreditorRow:
    facility: FacilityOperand
    share: Num
    claims_at_or_ahead: Num
    claims_over_ebitda: Num


@dataclass(frozen=True)
class Refinancing:
    operands: Operands
    step_up_bps: Decimal | None
    base_resources: Num
    maturities: tuple[MaturityRow, ...]  # wall order: maturity date, then facility_id (C-4)
    creditors: tuple[CreditorRow, ...]  # by rank, then wall order; wall order when unranked
    unmatched: tuple[UnmatchedFacility, ...]  # by facility_id, after every dated facility
    total_principal: Num
    total_principal_payable: Num
    total_applied: Num
    total_need: Num
    principal_after_horizon: Num
    nearest_maturity: date | Gap
    months_to_nearest: int | Gap
    payable_over_ebitda: Num
    need_over_ebitda: Num
    cash_interest_paid: Num
    added_interest: Num
    pro_forma_interest: Num
    interest_cover: Num
    pro_forma_interest_cover: Num
    junior_claims: Num
    junior_over_ebitda: Num


def _add_months(start: date, months: int) -> date:
    year, index = divmod(start.month - 1 + months, 12)
    year += start.year
    month = index + 1
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    last = (31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)[month - 1]
    return date(year, month, min(start.day, last))


def months_from(balance_date: date, maturity: date) -> int:
    """Ruling A1: the largest n with D0 + n months on or before the maturity (31 Dec to 30 Jun
    is 6)."""
    months = (maturity.year - balance_date.year) * 12 + (maturity.month - balance_date.month)
    return months - 1 if _add_months(balance_date, months) > maturity else months


def wall_position(*, balance_date: date, maturity: date, horizon_months: int) -> tuple[int, bool]:
    """CP-2D's whole-month rule: (months from D0, inside the horizon); inside when the maturity
    is on or before D0 + horizon."""
    inside = maturity <= _add_months(balance_date, horizon_months)
    return months_from(balance_date, maturity), inside


_SECURED_RANK = {"SECURED": 0, "UNSECURED": 1}
_SENIORITY_RANK = {
    "SUPER_SENIOR": 0,
    "SENIOR": 1,
    "SENIOR_SUBORDINATED": 2,
    "SUBORDINATED": 3,
    "JUNIOR": 4,
}


def _rank(f: FacilityOperand) -> tuple[int, int] | Gap:
    """(security, seniority), compared lexicographically; NOT_STATED or missing is a Gap."""
    ranks: list[int] = []
    for term, value, table in (
        ("secured status", f.secured_status, _SECURED_RANK),
        ("seniority", f.seniority, _SENIORITY_RANK),
    ):
        if value is None or value == "NOT_STATED":
            return _unstated_gap(f.facility_id, term)
        if value not in table:  # CP-1's ranking vocabulary is closed (ruling C-6): an invariant
            raise ValueError(f"CP-3C {f.facility_id}: unknown ranking flag {value!r}")
        ranks.append(table[value])
    return ranks[0], ranks[1]


def _wall_key(f: FacilityOperand) -> tuple[bool, date, str]:
    """Wall order (C-4): maturity date, then facility_id; an undated facility after every dated
    one, by facility_id (round 8 B6, 2D-c)."""
    dated = isinstance(f.maturity_date, date)
    return (
        not dated,
        f.maturity_date if isinstance(f.maturity_date, date) else date.min,
        f.facility_id,
    )


def _earlier(a: int | Gap, b: int | Gap) -> int | Gap:
    if isinstance(a, Gap):
        return a
    if isinstance(b, Gap):
        return b
    return min(a, b)


def _amortised(f: FacilityOperand, months: int | Gap) -> Num:
    """min(annual amortisation x months / 12, principal), the operands in formula order."""
    if f.annual_amortisation is None:
        return _unstated_gap(f.facility_id, "annual amortisation")
    if isinstance(months, Gap):
        return months
    if isinstance(f.principal, Gap):
        return f.principal
    return min(f.annual_amortisation * months / _MONTHS_PER_YEAR, f.principal)


def _resources(
    base: Num, flow: Num, months: int | Gap, amortised_to: Num, paid_before: Decimal
) -> Num:
    if isinstance(base, Gap):
        return base
    if isinstance(flow, Gap):
        return flow
    if isinstance(months, Gap):
        return months
    if isinstance(amortised_to, Gap):
        return amortised_to
    return base + flow * months / _MONTHS_PER_YEAR - amortised_to - paid_before


def _maturity_rows(
    base: Num, flow: Num, ordered: Sequence[FacilityOperand], unmatched: Sequence[Gap]
) -> tuple[MaturityRow, ...]:
    """The resources reason (ruling C-2) is the first gap in formula order: cash, revolver and
    minimum cash (``base``), the flow, the facility's months to maturity, then each facility's
    amortisation in wall order and the unmatched facilities (each amortised-to sum needs every
    facility)."""
    rows: list[MaturityRow] = []
    paid_before = _ZERO  # principal paid from resources at earlier maturities
    for f in ordered:
        own = _amortised(f, f.months)
        balloon = _diff(f.principal, own)
        amortised_to = _total(
            (*(_amortised(g, _earlier(f.months, g.months)) for g in ordered), *unmatched)
        )
        resources = _resources(base, flow, f.months, amortised_to, paid_before)
        if isinstance(resources, Gap) or isinstance(balloon, Gap):
            # A balloon gap is f's own amortisation gap, which ``amortised_to`` carries.
            lost = resources if isinstance(resources, Gap) else balloon
            rows.append(MaturityRow(f, own, balloon, resources, lost, lost, lost))
            continue
        applied = min(balloon, max(_ZERO, resources))
        cover = Gap(NM_PAYABLE, applicable=False) if balloon == 0 else _r4(applied / balloon)
        paid_before += applied
        rows.append(MaturityRow(f, own, balloon, resources, applied, balloon - applied, cover))
    return tuple(rows)


def _creditor_rows(
    ordered: Sequence[FacilityOperand], unmatched: Sequence[Gap], total: Num, ebitda: Num
) -> tuple[tuple[CreditorRow, ...], Num]:
    """The rows, and the claims at or ahead of the most junior facility. One facility not
    ranked (or unmatched) leaves every claim missing, the rows in wall order; a row names its
    own facility first, the junior total the first such facility in wall order."""
    ranked = [(f, _rank(f)) for f in ordered]
    unranked = _first(*(r for _, r in ranked if isinstance(r, Gap)), *unmatched)
    # A share's denominator: zero and negative totals have their own reasons (C-6, B6).
    nm = NM_TOTAL_NEGATIVE if isinstance(total, Decimal) and total < 0 else NM_TOTAL
    rows: list[CreditorRow] = []
    if unranked is not None:
        for f, r in ranked:
            gap = r if isinstance(r, Gap) else unranked
            rows.append(CreditorRow(f, _ratio(f.principal, total, nm), gap, gap))
        return tuple(rows), unranked
    ranks = {f.facility_id: r for f, r in ranked if not isinstance(r, Gap)}
    for f in sorted(ordered, key=lambda f: (ranks[f.facility_id], *_wall_key(f))):
        own = ranks[f.facility_id]
        claims = _total(g.principal for g in ordered if ranks[g.facility_id] <= own)
        share = _ratio(f.principal, total, nm)
        rows.append(CreditorRow(f, share, claims, _ratio(claims, ebitda, NM_EBITDA)))
    # Lease Method 7 (method_rules.lme_capacity): the largest claims at or ahead of any rank.
    # The last rank's claims hold every facility, so a gap there is the gap of every rank.
    if not rows:
        return (), Gap(NO_FACILITY)
    last = rows[-1].claims_at_or_ahead
    known = [c for r in rows if isinstance(c := r.claims_at_or_ahead, Decimal)]
    return tuple(rows), last if isinstance(last, Gap) else max(known)


def _repriced(payable: Num, step: Num) -> Num:
    """principal repriced x margin step-up / 10000, the operands in formula order."""
    if isinstance(payable, Gap):
        return payable
    if isinstance(step, Gap):
        return step
    return payable * step / _BP_PER_UNIT


def compose_refinancing(*, operands: Operands, step_up_bps: int | None) -> Refinancing:
    """The Method over the operands, pure Decimal; ``step_up_bps`` None is an unassessed step-up."""
    o = operands
    ids = [f.facility_id for f in o.facilities] + [u.facility_id for u in o.unmatched]
    if len(set(ids)) != len(ids):
        raise ValueError("CP-3C: a facility_id repeats")
    with localcontext(_CONTEXT):
        ordered = tuple(sorted(o.facilities, key=_wall_key))
        unmatched = tuple(sorted(o.unmatched, key=lambda u: u.facility_id))
        # Undated in CP-3C's view, so after every dated facility (2D-c); every total needs it.
        extra = tuple(Gap(u.reason, cause=_UNMATCHED_CAUSE) for u in unmatched)
        # No facility at all: each facility-dependent value takes this one reason (C-6).
        none = None if ordered or unmatched else Gap(NO_FACILITY)
        minimum: Num = Gap(REASON_MINIMUM_CASH) if o.minimum_cash is None else o.minimum_cash
        cash_and_revolver = _total(
            (
                _op(o.cash, "cash and cash equivalents", o.status("cash")),
                _op(o.undrawn_revolver, "undrawn revolver", o.status("undrawn_revolver")),
            )
        )
        base = _diff(cash_and_revolver, minimum)
        flow = _op(o.run_rate_annual, "CP-2D run-rate annual flow", o.status("run_rate_annual"))
        ebitda = _op(o.adjusted_ebitda, "adjusted EBITDA", o.status("adjusted_ebitda"))
        paid = _op(o.cash_interest_paid, "cash interest paid", o.status("cash_interest_paid"))
        rows = _maturity_rows(base, flow, ordered, extra)
        total = none or _total((*(f.principal for f in ordered), *extra))
        creditors, junior = _creditor_rows(ordered, extra, total, ebitda)
        payable = none or _total((*(r.principal_payable for r in rows), *extra))
        # Without a matched facility there is no row; the resources operands still come first.
        pool = none or _first(base, flow)
        applied = pool or _total((*(r.applied for r in rows), *extra))
        need = pool or _total((*(r.need for r in rows), *extra))
        # Outside the horizon needs each position: an unknown one is that facility's gap.
        after = [
            r.facility.inside_horizon
            if isinstance(r.facility.inside_horizon, Gap)
            else r.principal_payable
            for r in rows
            if r.facility.inside_horizon is not True
        ]
        step: Num = Gap(REASON_STEP_UP) if step_up_bps is None else Decimal(step_up_bps)
        added = _repriced(payable, step)
        pro_forma = _total((paid, added))
        undated = none or _first(*(f.maturity_date for f in ordered), *extra)
        return Refinancing(
            operands=o,
            step_up_bps=None if isinstance(step, Gap) else step,
            base_resources=base,
            maturities=rows,
            creditors=creditors,
            unmatched=unmatched,
            total_principal=total,
            total_principal_payable=payable,
            total_applied=applied,
            total_need=need,
            principal_after_horizon=none or _total((*after, *extra)),
            nearest_maturity=undated or ordered[0].maturity_date,
            months_to_nearest=undated or ordered[0].months,
            payable_over_ebitda=_ratio(payable, ebitda, NM_EBITDA),
            need_over_ebitda=_ratio(need, ebitda, NM_EBITDA),
            cash_interest_paid=paid,
            added_interest=added,
            pro_forma_interest=pro_forma,
            interest_cover=_ratio(ebitda, paid, NM_INTEREST),
            pro_forma_interest_cover=_ratio(ebitda, pro_forma, NM_INTEREST),
            junior_claims=junior,
            junior_over_ebitda=_ratio(junior, ebitda, NM_EBITDA),
        )


# --- operands from the bound upstream facts ---------------------------------------------------

_MILLIONS = "MILLIONS"


def _amount(
    what: str, status: Status, amount: Decimal | None, unit: str | None, want: str
) -> Decimal | None:
    if status != "known":
        return None
    if amount is None or unit != want:
        raise ValueError(f"CP-3C {what}: expected a {want} amount")
    return amount


def _cp1_amount(name: str, fact: Cp1Fact) -> Decimal | None:
    return _amount(name, fact.status, fact.amount, fact.unit, _MILLIONS)


def _cp2d_amount(fact: Cp2dFact, want: str = _MILLIONS) -> Decimal | None:
    return _amount(fact.fact_id, fact.status, fact.amount, fact.unit, want)


def _stated_text(what: str, status: Status, text: str | None) -> str | None:
    """A text fact's text, or None when it is not known; a known fact without text is refused."""
    if status != "known":
        return None
    if text is None:
        raise ValueError(f"CP-3C {what}: expected a text fact")
    return text


def _cp1_text(name: str, fact: Cp1Fact) -> str | None:
    return _stated_text(name, fact.status, fact.text)


def _whole_months(fact: Cp2dFact) -> int | None:
    """A CP-2D count of months, or None when the cell is missing."""
    months = _cp2d_amount(fact, "months")
    if months is not None and months != months.to_integral_value():
        raise ValueError(f"CP-3C {fact.fact_id}: needs a whole number of months")
    return None if months is None else int(months)


def _flag(fact: Cp2dFact) -> bool | None:
    """CP-2D's inside-horizon flag, or None when the cell is missing."""
    flag = _stated_text(fact.fact_id, fact.status, fact.text)
    if flag not in (None, "Yes", "No"):
        raise ValueError(f"CP-3C {fact.fact_id}: inside-horizon flag {flag!r}")
    return None if flag is None else flag == "Yes"


def check_currency(*, cp1: Cp1Operands, cp2d: Cp2dOperands, currency: str) -> None:
    """Round 13 item 5 (R1 L2): the reporting currency is CP-1 T4.10 ``cash_closing``'s own
    currency, which must be set, and every known MILLIONS fact CP-3C reads states the same one.
    A missing cash_closing states none, so the reporting currency stands unchecked then."""
    cash = cp1.cash_closing
    if cash.status == "known":
        if cash.currency is None or is_blank(cash.currency):
            raise ValueError("CP-3C cash_closing: currency is not set")
        if cash.currency != currency:
            raise ValueError(
                f"CP-3C: reporting currency {currency!r} is not cash_closing's {cash.currency!r}"
            )
    read: list[tuple[str, Cp1Fact | Cp2dFact]] = [
        ("undrawn_rcf", cp1.undrawn_rcf),
        ("adjusted_ebitda", cp1.adjusted_ebitda),
        ("cash_interest", cp1.cash_interest),
        *((f"{t.facility_id}.annual_amortisation", t.annual_amortisation) for t in cp1.facilities),
        *((f.fact_id, f) for f in (cp2d.run_rate, cp2d.minimum_cash, cp2d.funding_gap)),
        *((r.principal.fact_id, r.principal) for r in cp2d.wall),
    ]
    for name, fact in read:
        if fact.status == "known" and fact.unit == _MILLIONS and fact.currency != currency:
            raise ValueError(f"CP-3C {name}: currency {fact.currency!r} is not {currency!r}")


def _facility(
    row: WallRow, terms: FacilityTerms, *, balance_date: date, horizon: int | Gap, currency: str
) -> FacilityOperand:
    fid = row.facility_id
    principal: Num
    if terms.currency is None:  # round 8 B6 (2D-c); the currency per A5
        principal = Gap(
            CURRENCY_UNSTATED.format(fid=fid), cause=_UNSTATED_CAUSE.format(term="currency")
        )
    elif terms.currency != currency:  # ruling C-6 with 2D5's reason
        fx = FX_REASON.format(fid=fid, ccy=terms.currency, base=currency)
        principal = Gap(fx, cause=_FX_CAUSE)
    else:
        amount = _cp2d_amount(row.principal)
        unstated = _unstated_gap(fid, "principal")  # round 8 B6 (2D-c)
        principal = unstated if amount is None else amount
    stated = _stated_text(
        row.maturity_date.fact_id, row.maturity_date.status, row.maturity_date.text
    )
    maturity: date | Gap
    months: int | Gap
    inside: bool | Gap
    if stated is None:  # round 8 B6 (2D-c): no position
        maturity = months = inside = _unstated_gap(fid, "maturity date")
    elif (maturity := date.fromisoformat(stated)) < balance_date:
        # Round 11 B1: the date stays known; the position takes the unstated date's slot.
        months = inside = Gap(PRE_D0.format(fid=fid), cause=_PRE_D0_CAUSE)
    else:
        # Ruling C-6 and round 8 B6: CP-3C uses its recomputed position; the copies show CP-2D's.
        months = months_from(balance_date, maturity)
        inside = (
            horizon if isinstance(horizon, Gap) else maturity <= _add_months(balance_date, horizon)
        )
    return FacilityOperand(
        facility_id=fid,
        principal=principal,
        maturity_date=maturity,
        months=months,
        inside_horizon=inside,
        annual_amortisation=_cp1_amount(f"{fid}.annual_amortisation", terms.annual_amortisation),
        secured_status=_cp1_text(f"{fid}.secured_status", terms.secured_status),
        seniority=_cp1_text(f"{fid}.seniority", terms.seniority),
    )


def _sources(
    cp1: Cp1Operands, cp2d: Cp2dOperands
) -> tuple[dict[str, FacilityTerms], dict[str, WallRow]]:
    """The CP-1 register and the CP-2D wall by facility_id."""
    terms = {t.facility_id: t for t in cp1.facilities}
    wall = {r.facility_id: r for r in cp2d.wall}
    if len(terms) != len(cp1.facilities) or len(wall) != len(cp2d.wall):
        raise ValueError("CP-3C: a facility_id repeats")
    return terms, wall


def compose_operands(
    *, cp1: Cp1Operands, cp2d: Cp2dOperands, balance_date: date, currency: str
) -> Operands:
    """The Method's operands from the bound facts; a missing fact stays missing."""
    if cp1.cash_interest.period != cp1.adjusted_ebitda.period:
        raise ValueError("CP-3C: cash interest and adjusted EBITDA cover different periods")
    interest = _cp1_amount("cash_interest", cp1.cash_interest)
    terms, wall = _sources(cp1, cp2d)
    months = _whole_months(cp2d.horizon)
    horizon: int | Gap = Gap(HORIZON_MISSING) if months is None else months  # round 8 B6 (2D-b)
    facilities = tuple(
        _facility(
            row,
            terms[row.facility_id],
            balance_date=balance_date,
            horizon=horizon,
            currency=currency,
        )
        for row in cp2d.wall
        if row.facility_id in terms
    )
    unmatched = tuple(
        UnmatchedFacility(
            fid,
            NOT_IN.format(
                fid=fid, source="CP-2D maturity wall" if fid in terms else "CP-1 debt register"
            ),
        )
        for fid in sorted(terms.keys() ^ wall.keys())
    )
    statuses = {
        name: fact.status
        for name, fact in (
            ("cash", cp1.cash_closing),
            ("undrawn_revolver", cp1.undrawn_rcf),
            ("run_rate_annual", cp2d.run_rate),
            ("adjusted_ebitda", cp1.adjusted_ebitda),
            ("cash_interest_paid", cp1.cash_interest),
        )
        if fact.status != "known"
    }
    return Operands(
        cash=_cp1_amount("cash_closing", cp1.cash_closing),
        undrawn_revolver=_cp1_amount("undrawn_rcf", cp1.undrawn_rcf),
        run_rate_annual=_cp2d_amount(cp2d.run_rate),
        minimum_cash=_cp2d_amount(cp2d.minimum_cash),
        adjusted_ebitda=_cp1_amount("adjusted_ebitda", cp1.adjusted_ebitda),
        cash_interest_paid=None if interest is None else interest.copy_negate(),  # exact
        facilities=facilities,
        unmatched=unmatched,
        statuses=statuses,
    )


# --- cells and tables ---------------------------------------------------------------------------

# A gap's report-wide G<n> is bound at render time (expected.json shown_pattern "∅ G<n>").
# A conflicting fact is spelled as a gap, as the product spells it (report_view.py:932-933).
GAP_SHOWN: Mapping[CellStatus, str] = {
    "missing": "∅ G#",
    "conflicting": "∅ G#",
    "not_applicable": "∅ G# n.m.",
}


@dataclass(frozen=True)
class Cell:
    """One table cell: a product fact's coordinates, value, spelling and lineage marker."""

    fact_id: str
    table_id: str
    row_id: str
    field: str
    label: str
    status: CellStatus
    shown: str
    value_class: ValueClass
    amount: Decimal | None = None
    text: str | None = None
    unit: str | None = None
    currency: str | None = None
    period: str | None = None
    formula: str | None = None
    reason: str | None = None
    cp1_operand: str | None = None
    cp2d_operand: str | None = None

    def fact(self) -> Fact:
        """The product Fact of this cell, without citations or calculation id (Stage 2)."""
        return Fact(
            fact_id=self.fact_id,
            label=self.label,
            table_id=self.table_id,
            row_id=self.row_id,
            field=self.field,
            amount=self.amount,
            text=self.text,
            status=self.status,
            unit=self.unit,
            currency=self.currency,
            period=self.period,
            value_class=self.value_class,
            formula=self.formula,
            limitation=self.reason,
        )


@dataclass(frozen=True)
class Row:
    row_id: str
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
class TextTable:
    """T3D.7-T3D.9: text rows, no facts (lease freeze note 4)."""

    table_id: str
    title: str
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class _Spec:
    """A cell before its coordinates."""

    status: CellStatus
    value_class: ValueClass
    amount: Decimal | None = None
    text: str | None = None
    unit: str | None = None
    period: str | None = None
    formula: str | None = None
    reason: str | None = None
    cp1_operand: str | None = None
    cp2d_operand: str | None = None


def _known(
    amount: Decimal, unit: str, period: str, value_class: ValueClass = "calculated"
) -> _Spec:
    return _Spec("known", value_class, amount=amount, unit=unit, period=period)


def _text(text: str, value_class: ValueClass, formula: str | None = None) -> _Spec:
    return _Spec("known", value_class, text=text, formula=formula)


def _gap(reason: str, unit: str | None, value_class: ValueClass = "calculated") -> _Spec:
    return _Spec("missing", value_class, unit=unit, reason=reason)


def _value(x: Num, unit: str, period: str, formula: str) -> _Spec:
    """A computed value: known with its formula, or a gap with its reason (ruling C-2)."""
    if isinstance(x, Gap):
        status: CellStatus = "missing" if x.applicable else "not_applicable"
        return _Spec(status, "calculated", unit=unit, reason=x.reason)
    return replace(_known(x, unit, period), formula=formula)


def _copy(fact: Cp1Fact | Cp2dFact, at: str) -> _Spec:
    """A copied upstream fact: its own value, unit, period, value_class and reason (C-7)."""
    if fact.value_class is None:
        raise ValueError(f"CP-3C {at}: a copied fact keeps its value_class, and none is bound")
    if fact.status != "known" and fact.reason is not None:  # an unsettled fact has a reason
        gap = _gap(fact.reason, fact.unit, fact.value_class)
        return replace(gap, status=fact.status, period=fact.period)
    if fact.text is not None:
        return _text(fact.text, fact.value_class)
    if fact.amount is None or fact.unit is None or fact.period is None:
        raise ValueError(f"CP-3C {at}: a copied amount needs its unit and period")
    return _known(fact.amount, fact.unit, fact.period, fact.value_class)


def _from_cp2d(fact: Cp2dFact) -> _Spec:
    return replace(_copy(fact, fact.fact_id), cp2d_operand=fact.fact_id)


def _from_cp1(fact: Cp1Fact, operand: str) -> _Spec:
    return replace(_copy(fact, operand), cp1_operand=operand)


def _materialise(
    spec: _Spec, *, table_id: str, row_id: str, field: str, label: str, currency: str
) -> Cell:
    fact_id = f"{table_id}.{row_id}" if field == "value" else f"{table_id}.{row_id}.{field}"
    cell = Cell(
        fact_id=fact_id,
        table_id=table_id,
        row_id=row_id,
        field=field,
        label=label,
        status=spec.status,
        shown=GAP_SHOWN.get(spec.status, ""),
        value_class=spec.value_class,
        amount=spec.amount,
        text=spec.text,
        unit=spec.unit,
        currency=currency if spec.unit == _MILLIONS else None,  # every US$ m cell, gap or not
        period=spec.period,
        formula=spec.formula,
        reason=spec.reason,
        cp1_operand=spec.cp1_operand,
        cp2d_operand=spec.cp2d_operand,
    )
    fact = cell.fact()  # the product contract validates the cell
    if spec.status != "known":
        return cell
    return replace(cell, shown=fact_spelling(fact, None)[2])


Line = tuple[str, Sequence[_Spec]]


def _table(
    table_id: str,
    title: str,
    row_header: str,
    columns: Sequence[str],
    rows: Sequence[Line],
    currency: str,
) -> Table:
    single = len(columns) == 1
    out = []
    for index, (label, specs) in enumerate(rows, 1):
        if len(specs) != len(columns):
            raise ValueError(
                f"{table_id} row {index}: {len(specs)} cells for {len(columns)} columns"
            )
        row_id = f"r{index:02d}"
        cells = tuple(
            _materialise(
                spec,
                table_id=table_id,
                row_id=row_id,
                field="value" if single else f"c{n}",
                label=label if single else column,
                currency=currency,
            )
            for n, (column, spec) in enumerate(zip(columns, specs, strict=True), 1)
        )
        out.append(Row(row_id, label, cells))
    return Table(table_id, title, row_header, tuple(columns), tuple(out))


@dataclass(frozen=True)
class _Context:
    """What the table and claim builders read besides the composer's values."""

    inputs: Cp3cInputs
    refinancing: Refinancing
    terms: Mapping[str, FacilityTerms]
    wall: Mapping[str, WallRow]
    balance: str  # the balance-date period
    flows: str  # the LTM window of flows and ratios

    @property
    def ids(self) -> tuple[str, ...]:
        """Every facility in wall order, the unmatched ones last (ruling C-6)."""
        r = self.refinancing
        matched = (m.facility.facility_id for m in r.maturities)
        return (*matched, *(u.facility_id for u in r.unmatched))

    def label(self, facility_id: str) -> str:
        """'<name> (<id>)'; with no name (not in the register, or missing: round 8 B6) the id."""
        if facility_id not in self.terms:
            return facility_id
        text = _cp1_text(f"{facility_id}.facility_name", self.terms[facility_id].facility_name)
        return facility_id if text is None else f"{text} ({facility_id})"

    def unmatched(self, columns: Sequence[tuple[str | None, ValueClass]]) -> list[Line]:
        """A row per unmatched facility, every cell missing with its reason (ruling C-6)."""
        return [
            (self.label(u.facility_id), [_gap(u.reason, unit, cls) for unit, cls in columns])
            for u in self.refinancing.unmatched
        ]

    def usd(self, x: Num, formula: str) -> _Spec:
        return _value(x, _MILLIONS, self.balance, formula)

    def usd_flow(self, x: Num, formula: str) -> _Spec:
        return _value(x, _MILLIONS, self.flows, formula)

    def percent(self, x: Num, formula: str) -> _Spec:
        return _value(x, "PERCENT", self.balance, formula)

    def multiple(self, x: Num, formula: str) -> _Spec:
        return _value(x, "MULTIPLE", self.flows, formula)


_T3D1_COLUMNS = (
    "Principal (US$ m)",
    "Maturity date",
    "Months from {d0}",
    "Inside CP-2D horizon",
    "Amortisation before maturity (US$ m)",
    "Principal payable at maturity (US$ m)",
    "Resources at maturity (US$ m)",
    "Resources applied (US$ m)",
    "Refinancing need (US$ m)",
    "Resources cover of principal at maturity",
)
_RESOURCES_FORMULA = (
    "cash + undrawn revolver - minimum cash + run-rate flow x months / 12"
    " - amortisation to the date - earlier principal paid from resources"
)
_APPLIED_FORMULA = "min(principal payable at maturity, max(0, resources at maturity))"
# (unit, value_class) per column of an unmatched facility's row (the copies' classes).
_T3D1_GAPS: tuple[tuple[str | None, ValueClass], ...] = (
    (_MILLIONS, "source"),
    (None, "source"),
    ("months", "calculated"),
    (None, "calculated"),
    *((_MILLIONS, "calculated"),) * 5,
    ("PERCENT", "calculated"),
)
_T3D4_GAPS: tuple[tuple[str | None, ValueClass], ...] = (
    (None, "source"),
    (None, "source"),
    (_MILLIONS, "source"),
    ("PERCENT", "calculated"),
    (_MILLIONS, "calculated"),
    ("MULTIPLE", "calculated"),
)


def _t3d1(c: _Context) -> Table:
    rows: list[Line] = []
    for m in c.refinancing.maturities:
        w = c.wall[m.facility.facility_id]
        cells = [
            _from_cp2d(w.principal),
            _from_cp2d(w.maturity_date),
            _from_cp2d(w.months),
            _from_cp2d(w.inside_horizon),
            c.usd(
                m.amortisation_before_maturity, "min(annual amortisation x months / 12, principal)"
            ),
            c.usd(m.principal_payable, "principal - amortisation before maturity"),
            c.usd(m.resources, _RESOURCES_FORMULA),
            c.usd(m.applied, _APPLIED_FORMULA),
            c.usd(m.need, "principal payable at maturity - resources applied"),
            c.percent(m.cover, "resources applied / principal payable at maturity"),
        ]
        rows.append((c.label(m.facility.facility_id), cells))
    rows += c.unmatched(_T3D1_GAPS)
    columns = tuple(col.format(d0=c.balance) for col in _T3D1_COLUMNS)
    title = "Refinancing need by maturity"
    return _table("T3D.1", title, "Facility", columns, rows, c.inputs.currency)


def _single(c: _Context, table_id: str, title: str, rows: Sequence[tuple[str, _Spec]]) -> Table:
    lines = [(label, [spec]) for label, spec in rows]
    return _table(table_id, title, "Line", ("Value",), lines, c.inputs.currency)


def _t3d2(c: _Context) -> Table:
    r, cp2d = c.refinancing, c.inputs.cp2d
    months = (
        _gap(r.months_to_nearest.reason, "months")
        if isinstance(r.months_to_nearest, Gap)
        else replace(
            _known(Decimal(r.months_to_nearest), "months", c.balance),
            formula="months from the balance date to the earliest maturity",
        )
    )
    nearest = (
        _gap(r.nearest_maturity.reason, None)
        if isinstance(r.nearest_maturity, Gap)
        else _text(r.nearest_maturity.isoformat(), "calculated", "earliest maturity date")
    )
    outside = "sum of principal payable at maturity of facilities outside the CP-2D horizon"
    payable = "sum of principal payable at maturity"
    rows = [
        (
            "Principal payable at maturity, all facilities",
            c.usd(r.total_principal_payable, payable),
        ),
        (
            "Resources applied at the maturity dates",
            c.usd(r.total_applied, "sum of resources applied"),
        ),
        ("Refinancing need after resources", c.usd(r.total_need, "sum of refinancing need")),
        ("Principal maturing after the CP-2D horizon", c.usd(r.principal_after_horizon, outside)),
        ("Nearest maturity date", nearest),
        ("Months to the nearest maturity", months),
        ("LTM adjusted EBITDA", _from_cp1(c.inputs.cp1.adjusted_ebitda, "adjusted_ebitda")),
        (
            "Principal payable at maturity / LTM adjusted EBITDA",
            c.multiple(r.payable_over_ebitda, "principal payable at maturity / adjusted EBITDA"),
        ),
        (
            "Refinancing need / LTM adjusted EBITDA",
            c.multiple(r.need_over_ebitda, "refinancing need / adjusted EBITDA"),
        ),
        ("CP-2D funding gap at its horizon end", _from_cp2d(cp2d.funding_gap)),
        ("Minimum cash applied (analyst assumption set in CP-2D)", _from_cp2d(cp2d.minimum_cash)),
        ("CP-2D horizon (analyst judgment)", _from_cp2d(cp2d.horizon)),
    ]
    return _single(c, "T3D.2", "Refinancing burden", rows)


def _t3d3(c: _Context) -> Table:
    r = c.refinancing
    bps = r.step_up_bps
    step_up = (
        _gap(STEP_UP_NOT_ASSESSED, "basis_points", "analyst_judgment")
        if bps is None
        else _known(bps, "basis_points", c.inputs.as_of.isoformat(), "analyst_judgment")
    )
    paid = c.usd_flow(r.cash_interest_paid, "negation of the CP-1 cash interest outflow")
    pro_forma = "cash interest paid + added annual cash interest"
    pro_forma_cover = "adjusted EBITDA / pro forma annual cash interest"
    rows = [
        ("Cash interest paid, LTM", replace(paid, cp1_operand="cash_interest")),
        ("LTM adjusted EBITDA", _from_cp1(c.inputs.cp1.adjusted_ebitda, "adjusted_ebitda")),
        (
            "Interest cover, LTM",
            c.multiple(r.interest_cover, "adjusted EBITDA / cash interest paid"),
        ),
        ("Margin step-up (analyst assumption)", step_up),
        (
            "Principal repriced (all principal payable at maturity)",
            c.usd(r.total_principal_payable, "sum of principal payable at maturity"),
        ),
        (
            "Added annual cash interest",
            c.usd_flow(r.added_interest, "principal repriced x margin step-up / 10000"),
        ),
        ("Pro forma annual cash interest", c.usd_flow(r.pro_forma_interest, pro_forma)),
        ("Pro forma interest cover", c.multiple(r.pro_forma_interest_cover, pro_forma_cover)),
    ]
    return _single(c, "T3D.3", "Refinancing cost sensitivity", rows)


_RANKING_FORMULA = (
    "sum of principal of facilities ranking at or ahead (secured before unsecured, then seniority)"
)


def _t3d4(c: _Context) -> Table:
    rows: list[Line] = []
    for cr in c.refinancing.creditors:
        fid = cr.facility.facility_id
        terms = c.terms[fid]
        cells = [
            _from_cp1(terms.secured_status, f"T4.18 {fid} secured_status"),
            _from_cp1(terms.seniority, f"T4.18 {fid} seniority"),
            _from_cp2d(c.wall[fid].principal),
            c.percent(cr.share, "principal / total facility principal"),
            c.usd(cr.claims_at_or_ahead, _RANKING_FORMULA),
            c.multiple(cr.claims_over_ebitda, "claims at or ahead / adjusted EBITDA"),
        ]
        rows.append((c.label(fid), cells))
    rows += c.unmatched(_T3D4_GAPS)
    columns = (
        "Security",
        "Seniority",
        "Principal (US$ m)",
        "Share of total principal",
        "Claims at or ahead (US$ m)",
        "Claims at or ahead / LTM adjusted EBITDA",
    )
    return _table("T3D.4", "Creditor position", "Facility", columns, rows, c.inputs.currency)


def _t3d5(c: _Context) -> Table:
    r = c.refinancing
    junior = "claims at or ahead of the most junior facility / adjusted EBITDA"
    rows: list[Line] = [
        (
            "Claims at or ahead of the most junior facility (US$ m)",
            [
                c.usd(r.junior_claims, "largest claims at or ahead among the facilities"),
                _gap(REASON_LME, _MILLIONS),
                _gap(REASON_STRESS, _MILLIONS),
            ],
        ),
        (
            "Claims at or ahead of the most junior facility / LTM adjusted EBITDA",
            [
                c.multiple(r.junior_over_ebitda, junior),
                _gap(REASON_LME, "MULTIPLE"),
                _gap(REASON_STRESS, "MULTIPLE"),
            ],
        ),
    ]
    columns = ("Base", "LME", "Stress")
    return _table("T3D.5", "LME capacity", "Measure", columns, rows, c.inputs.currency)


def _path(s: RefinancingRiskSubmission, kind: PathKind) -> PathAssessment:
    (path,) = (p for p in s.paths if p.kind == kind)  # the validator holds one row per kind
    return path


def _t3d6(c: _Context) -> Table:
    rows: list[Line] = []
    for kind in KINDS:
        p = _path(c.inputs.submission, kind)
        basis = ", ".join(c.inputs.offered[ref] for ref in p.basis_refs) or "none"
        texts = (p.feasibility, p.text, p.credit_implication, basis)
        rows.append((KIND_LABEL[kind], [_text(t, "analyst_judgment") for t in texts]))
    columns = ("Feasibility", "Assessment", "Credit implication", "Basis")
    return _table("T3D.6", "Refinancing paths", "Path", columns, rows, c.inputs.currency)


# --- own limitations, ledgers and trace -----------------------------------------------------------

# (T3D.8 label, kind, text), verbatim from expected.json#cases.<case>.own_limitations.
_RUN_RATE = (
    "Run-rate basis",
    "Limitation",
    (
        "Run-rate basis: the annual cash flow of the liquidity analysis is held flat to each "
        "maturity date, including dates after its horizon; no forecast, growth, seasonality or "
        "new borrowing is assumed."
    ),
)
_RESOURCES = (
    "Resources basis",
    "Limitation",
    (
        "Resources at a maturity are cash and undrawn committed revolver at the balance date plus "
        "the held run-rate flow, less amortisation to that date, earlier principal paid from "
        "resources and the minimum cash; the refinancing of an earlier shortfall is not modelled."
    ),
)
_REVOLVER = (
    "Revolver availability",
    "Limitation",
    (
        "Any undrawn committed revolver is assumed to be available at every maturity date, even "
        "where it matures earlier; its own maturity is not read."
    ),
)
_MINIMUM_CASH = {
    True: (
        "Minimum cash",
        "Limitation",
        "Minimum cash is an analyst assumption, not a source figure.",
    ),
    False: (
        "Minimum cash",
        "Gap",
        (
            "Minimum cash was not assessed, so resources at maturity and the refinancing need are "
            "not calculated."
        ),
    ),
}
_STEP_UP = {
    True: (
        "Margin step-up",
        "Limitation",
        (
            "The margin step-up is an analyst assumption applied to all principal payable at "
            "maturity; it is not a source or market figure."
        ),
    ),
    False: (
        "Margin step-up",
        "Gap",
        "No margin step-up was assessed, so the cost effect of a refinancing is not calculated.",
    ),
}
_FIXED_TAIL = (
    (
        "Reference rate level",
        "Limitation",
        (
            "No reference rate level is stated in any source, so the all-in cost of a refinancing "
            "is not calculated; only a margin step-up over the current terms is shown."
        ),
    ),
    (
        "Market access",
        "Limitation",
        (
            "No market pricing or lender-appetite evidence is read, so feasibility judgments rest "
            "on the credit metrics alone."
        ),
    ),
    (
        "Liability-management capacity",
        "Limitation",
        (
            "Liability-management capacity is not calculated: the legal covenant analysis is not "
            "read, and it does not yet quantify basket amounts."
        ),
    ),
    ("Stress case", "Limitation", "No stressed case is shown: the downside analysis is not read."),
    (
        "Business context",
        "Limitation",
        (
            "Business and ownership context is not read, so owner support and asset-sale routes "
            "are not weighed."
        ),
    ),
    (
        "Ranking basis",
        "Limitation",
        (
            "Ranking follows the secured and seniority flags of each facility; guarantees, "
            "collateral value and structural subordination are not assessed."
        ),
    ),
)


# Own lines of ruling C-6 (the texts are ruled; the T3D.8 labels and kinds follow CP-2D's D-1).
_NO_FACILITY_LINE = (
    "Facility schedule",
    "Gap",
    "No facility is in the CP-1 debt register; refinancing figures are not calculated.",
)
_FX_LINE = (
    "Facility {fid} is denominated in {ccy}; maturity-wall totals and shares are not calculated "
    "because no FX conversion is applied."
)
_WALL_LINE = (
    "CP-2D's maturity wall for facility {fid} differs from the position recomputed from its "
    "horizon and maturity date; CP-3C uses the recomputed position and shows both."
)
# Round 8 B6: the 2D-c own line (label `Facility <term> (<id>)`, Gap, per D-1), and a wall
# row that states no months or flag (label `CP-2D maturity wall cross-check (<id>)`).
_UNSTATED_LINE = (
    "Facility {fid} {term} is not stated; maturity-wall figures that need it are not calculated."
)
_WALL_NONE_LINE = (
    "CP-2D's maturity wall for facility {fid} states no {what}; CP-3C uses the position "
    "recomputed from its horizon and maturity date."
)


# Round 11 B1 and B2 (the ruled texts; labels `Facility <term> (<id>)`).
_PRE_D0_LINE = (
    "Facility {fid} maturity date is before the balance date; maturity-wall figures that need it "
    "are not calculated."
)
_CREDITOR_LINE = (
    "Facility {fid} {term} is not stated; creditor-position figures that need it are not "
    "calculated."
)


def _unstated(fid: str, term: str, text: str = _UNSTATED_LINE) -> tuple[str, str, str]:
    return (f"Facility {term} ({fid})", "Gap", text.format(fid=fid, term=term))


def _wall_lines(row: WallRow, f: FacilityOperand) -> list[str]:
    """CP-2D's months and inside flag against the recomputed position (C-6, round 8 B6). With
    no maturity date, or no horizon, there is no recomputed value to set beside CP-2D's."""
    fid = f.facility_id
    checks: tuple[tuple[str, object, object], ...] = (
        ("months to maturity", _whole_months(row.months), f.months),
        ("inside-horizon flag", _flag(row.inside_horizon), f.inside_horizon),
    )
    known = [(what, stated, mine) for what, stated, mine in checks if not isinstance(mine, Gap)]
    lines = [_WALL_NONE_LINE.format(fid=fid, what=w) for w, stated, _ in known if stated is None]
    if any(stated is not None and stated != mine for _, stated, mine in known):
        lines.append(_WALL_LINE.format(fid=fid))
    return lines


def _facility_lines(c: _Context) -> list[tuple[str, str, str]]:
    """Facility by facility in wall order (round 11 B2): currency, maturity date (unstated or
    before D0), principal, annual amortisation, secured status, seniority, wall row."""
    r = c.refinancing
    lines = [] if r.maturities or r.unmatched else [_NO_FACILITY_LINE]
    for m in r.maturities:
        f = m.facility
        fid, ccy = f.facility_id, c.terms[f.facility_id].currency
        if ccy is None:
            lines.append(_unstated(fid, "currency"))
        elif ccy != c.inputs.currency:
            lines.append(
                (f"Facility currency ({fid})", "Limitation", _FX_LINE.format(fid=fid, ccy=ccy))
            )
        if isinstance(f.maturity_date, Gap):
            lines.append(_unstated(fid, "maturity date"))
        elif f.maturity_date < c.inputs.balance_date:
            text = _PRE_D0_LINE.format(fid=fid)
            lines.append((f"Facility maturity date ({fid})", "Limitation", text))
        if ccy == c.inputs.currency and isinstance(f.principal, Gap):
            lines.append(_unstated(fid, "principal"))
        if f.annual_amortisation is None:
            lines.append(_unstated(fid, "annual amortisation"))
        for term, value in (("secured status", f.secured_status), ("seniority", f.seniority)):
            if value is None or value == "NOT_STATED":
                lines.append(_unstated(fid, term, _CREDITOR_LINE))
        label = f"CP-2D maturity wall cross-check ({fid})"
        lines += [(label, "Limitation", text) for text in _wall_lines(c.wall[fid], f)]
    # The same words as the cells' reason (ruling C-6).
    lines += [
        (f"Facility register and wall ({u.facility_id})", "Gap", u.reason) for u in r.unmatched
    ]
    return lines


def _limitations(c: _Context) -> tuple[tuple[str, str, str], ...]:
    """(T3D.8 label, kind, text) per own limitation, in the oracle's order."""
    s = c.inputs.submission
    paths = []
    for kind in KINDS:
        limitation = _path(s, kind).limitation
        if limitation:
            paths.append((KIND_LABEL[kind], "Gap", limitation))
    return (
        _RUN_RATE,
        _RESOURCES,
        _REVOLVER,
        _MINIMUM_CASH[c.inputs.cp2d.minimum_cash.status == "known"],
        _STEP_UP[s.repricing is not None],
        *_FIXED_TAIL,
        *_facility_lines(c),
        *paths,
    )


def _upstream_shown(
    name: str,
    status: Status,
    amount: Decimal | None,
    text: str | None,
    unit: str | None,
    period: str | None,
) -> str:
    if status != "known":
        return GAP_SHOWN[status]
    fact = Fact(fact_id="upstream", label=name, amount=amount, text=text, unit=unit, period=period)
    return fact_spelling(fact, None)[2]


def _trace(c: _Context) -> TextTable:
    """T3D.9: [name, module, table or stable id, shown] for each name read, CP-1 then CP-2D."""
    cp1, cp2d = c.inputs.cp1, c.inputs.cp2d
    named_cp1: list[tuple[str, Cp1Fact]] = [
        ("cash_closing", cp1.cash_closing),
        ("undrawn_rcf", cp1.undrawn_rcf),
        ("adjusted_ebitda", cp1.adjusted_ebitda),
        ("cash_interest", cp1.cash_interest),
    ]
    for fid in (i for i in c.ids if i in c.terms):
        t = c.terms[fid]
        named_cp1 += [
            (f"{fid}.facility_name", t.facility_name),
            (f"{fid}.secured_status", t.secured_status),
            (f"{fid}.seniority", t.seniority),
            (f"{fid}.annual_amortisation", t.annual_amortisation),
        ]
    named_cp2d: list[tuple[str, Cp2dFact]] = [
        ("cp2d.horizon", cp2d.horizon),
        ("cp2d.run_rate", cp2d.run_rate),
        ("cp2d.min_cash", cp2d.minimum_cash),
        ("cp2d.funding_gap", cp2d.funding_gap),
    ]
    for fid in (i for i in c.ids if i in c.wall):
        w = c.wall[fid]
        named_cp2d += [
            (f"cp2d.{fid}.principal", w.principal),
            (f"cp2d.{fid}.maturity_date", w.maturity_date),
            (f"cp2d.{fid}.months", w.months),
            (f"cp2d.{fid}.inside_horizon", w.inside_horizon),
        ]
    rows = [
        (
            name,
            "CP-1",
            f"{f.table_id} {f.period.partition(':')[0]}",
            _upstream_shown(name, f.status, f.amount, f.text, f.unit, f.period),
        )
        for name, f in named_cp1
    ] + [
        (
            name,
            "CP-2D",
            f.fact_id,
            _upstream_shown(name, f.status, f.amount, f.text, f.unit, f.period),
        )
        for name, f in named_cp2d
    ]
    return TextTable("T3D.9", "Upstream trace", tuple(rows))


def _judgments(c: _Context, step_up: Cell) -> TextTable:
    s = c.inputs.submission
    first = (
        "Margin step-up",
        "not assessed" if s.repricing is None else f"{step_up.shown} (analyst assumption)",
    )
    rows = (first, *((KIND_LABEL[k], _path(s, k).category) for k in KINDS))
    return TextTable("T3D.7", "Analyst judgments", rows)


# --- claims (lease "Composer"; templates and gap forms fixed by expected.json) ---------------


@dataclass(frozen=True)
class ClaimText:
    claim_id: str
    template: str  # run text: {fact_id|unit} figures, [fact_id] chips
    text: str  # the resolved spelling
    references: tuple[str, ...]
    cites_from: tuple[str, ...]  # bound names, then the referenced cells (Stage 2 citations)


class _Claims:
    def __init__(self, cells: Mapping[str, Cell]) -> None:
        self.cells = cells

    def fig(self, fact_id: str) -> str:
        cell = self.cells[fact_id]
        if cell.status != "known" or cell.amount is None or cell.value_class == "analyst_judgment":
            raise ValueError(f"CP-3C claim figure {fact_id}: not a known computed figure")
        unit = figure_unit(cell.fact())
        if unit is None:
            raise ValueError(f"CP-3C claim figure {fact_id}: no figure unit")
        return "{" + fact_id + "|" + unit + "}"

    def chip(self, fact_id: str) -> str:
        if self.cells[fact_id].status == "known":
            raise ValueError(f"CP-3C claim chip {fact_id}: a chip names a gap")
        return "[" + fact_id + "]"

    def either(self, fact_id: str) -> str:
        return self.fig(fact_id) if self.cells[fact_id].status == "known" else self.chip(fact_id)

    def claim(self, claim_id: str, template: str, names: Sequence[str]) -> ClaimText:
        gaps = {k for k, v in self.cells.items() if v.status != "known"}
        found = prose.check(template, refs=self.cells.keys() - gaps, gaps=gaps)
        if found:
            raise ValueError(f"CP-3C {claim_id}: {'; '.join(found)}")
        parts, refs = [], []
        for run in prose.tokenize(template, gaps=gaps):
            if run.kind == "text":
                parts.append(run.text)
                continue
            cell = self.cells[run.text]
            refs.append(run.text)
            unit = figure_unit(cell.fact()) if run.figure and cell.unit == _MILLIONS else None
            parts.append(f"{cell.shown} {unit}" if unit else cell.shown)
        references = tuple(dict.fromkeys(refs))
        return ClaimText(claim_id, template, "".join(parts), references, (*names, *references))


def _because(value: Num) -> str:
    """A computed gap as a claim's cause (C-3, round 8 B2, round 11 Q3): a facility gap's frame,
    otherwise the reason less its prefix."""
    if not isinstance(value, Gap):
        raise TypeError("CP-3C: a claim cause needs a value that is not calculated")
    return value.cause or value.reason.removeprefix(_NOT_CALCULABLE)


def _names(c: _Context, cp1: Sequence[str], cp2d: Sequence[str]) -> list[str]:
    """Bound names per facility in wall order; an unmatched facility names the half it has."""
    return [
        name
        for fid in c.ids
        for name in (
            *(f"{fid}.{n}" for n in cp1 if fid in c.terms),
            *(f"cp2d.{fid}.{n}" for n in cp2d if fid in c.wall),
        )
    ]


def _claims(c: _Context, cells: Mapping[str, Cell]) -> tuple[ClaimText, ...]:
    """The pinned claims, the gap forms of rulings C-1 and C-3, and a chip for any other cell
    that is not known (the fig-or-chip rule those rulings apply; listed for LEAD)."""
    k = _Claims(cells)
    need = cells["T3D.2.r03"]
    if need.status == "known":
        tail = (
            "after the resources available at each maturity date the refinancing need is "
            f"{k.fig('T3D.2.r03')}."
        )
    elif need.reason == REASON_MINIMUM_CASH:
        tail = (
            f"the refinancing need after resources is {k.chip('T3D.2.r03')}, because the "
            "minimum cash has not been assessed."
        )
    else:
        tail = (
            f"the refinancing need after resources is {k.chip('T3D.2.r03')}, because "
            f"{_because(c.refinancing.total_need)}."
        )
    need_names = _names(c, ("annual_amortisation",), ("principal",))
    need_names += ["cash_closing", "undrawn_rcf", "cp2d.run_rate", "cp2d.min_cash"]
    claims = [
        k.claim(
            "CP-3C-NEED-01",
            f"Principal payable at maturity totals {k.either('T3D.2.r01')}; {tail}",
            need_names,
        ),
        k.claim(
            "CP-3C-HORIZON-01",
            f"The liquidity analysis reports a funding gap of {k.either('T3D.2.r10')} at its "
            f"horizon end, while {k.either('T3D.2.r04')} falls due after that horizon.",
            ["cp2d.funding_gap", "cp2d.horizon", *_names(c, (), ("inside_horizon",))],
        ),
        _burden_claim(c, k),
        _cost_claim(c, k),
        _lme_claim(c, k),
    ]
    return tuple(claims)


def _burden_claim(c: _Context, k: _Claims) -> ClaimText:
    head = f"Principal payable at maturity is {k.either('T3D.2.r08')} of adjusted EBITDA for the "
    head += f"twelve months to {format_date(c.inputs.balance_date)}"
    if k.cells["T3D.2.r08"].reason == NM_EBITDA:  # ruling C-3
        head += ", because adjusted EBITDA is zero or negative"
    template = f"{head}; the refinancing need is {k.either('T3D.2.r09')} of the same earnings."
    return k.claim("CP-3C-BURDEN-01", template, ["adjusted_ebitda"])


def _cost_claim(c: _Context, k: _Claims) -> ClaimText:
    if c.inputs.submission.repricing is None:
        return k.claim(
            "CP-3C-COST-01",
            "The cost of a margin step-up on the principal payable at maturity is not calculated: "
            f"added annual cash interest is {k.chip('T3D.3.r06')} because no step-up was assessed.",
            [],
        )
    now, after = c.refinancing.interest_cover, c.refinancing.pro_forma_interest_cover
    adds = (
        "An assumed margin step-up on the principal payable at maturity adds "
        f"{k.either('T3D.3.r06')} to annual cash interest"
    )
    # Ruling C-1: the verb follows the stored covers; a cover not known takes its chip.
    if isinstance(now, Gap) or isinstance(after, Gap):
        tail = (
            f"; interest cover is {k.either('T3D.3.r03')} before and {k.either('T3D.3.r08')} "
            "after it."
        )
    elif after == now:
        tail = f" and leaves interest cover at {k.fig('T3D.3.r03')}."
    else:
        verb = "lowers" if after < now else "changes"
        tail = f" and {verb} interest cover from {k.fig('T3D.3.r03')} to {k.fig('T3D.3.r08')}."
    return k.claim("CP-3C-COST-01", adds + tail, ["cash_interest", "adjusted_ebitda"])


def _lme_claim(c: _Context, k: _Claims) -> ClaimText:
    junior = k.cells["T3D.5.r01.c1"]
    cause = "" if junior.status == "known" else f", because {_because(c.refinancing.junior_claims)}"
    return k.claim(
        "CP-3C-LME-01",
        f"Claims at or ahead of the most junior facility are {k.either('T3D.5.r01.c1')} before "
        f"any liability-management exercise{cause}; the position after such an exercise is "
        f"{k.chip('T3D.5.r01.c2')} because the legal capacity evidence is not bound.",
        _names(c, ("secured_status", "seniority"), ("principal",)),
    )


# --- the module result ------------------------------------------------------------------------


@dataclass(frozen=True)
class Cp3cResult:
    refinancing: Refinancing
    tables: tuple[Table, ...]  # T3D.1-T3D.6
    judgments: TextTable  # T3D.7
    gaps_ledger: TextTable  # T3D.8
    trace: TextTable  # T3D.9
    claims: tuple[ClaimText, ...]
    own_limitations: tuple[str, ...]
    status: Literal["restricted"]  # own limitations are never empty (lease)


def compute(inputs: Cp3cInputs) -> Cp3cResult:
    """CP-3C's tables, ledgers, claims and own limitations for a valid submission."""
    issues = submission_issues(submission=inputs.submission, offered=inputs.offered)
    if issues:
        raise ValueError("CP-3C submission is invalid: " + "; ".join(issues))
    check_currency(cp1=inputs.cp1, cp2d=inputs.cp2d, currency=inputs.currency)
    operands = compose_operands(
        cp1=inputs.cp1, cp2d=inputs.cp2d, balance_date=inputs.balance_date, currency=inputs.currency
    )
    repricing = inputs.submission.repricing
    refinancing = compose_refinancing(
        operands=operands, step_up_bps=None if repricing is None else repricing.bps
    )
    terms, wall = _sources(inputs.cp1, inputs.cp2d)
    c = _Context(
        inputs=inputs,
        refinancing=refinancing,
        terms=terms,
        wall=wall,
        balance=inputs.balance_date.isoformat(),
        flows=inputs.cp1.adjusted_ebitda.period,
    )
    tables = (_t3d1(c), _t3d2(c), _t3d3(c), _t3d4(c), _t3d5(c), _t3d6(c))
    cells = {cell.fact_id: cell for t in tables for row in t.rows for cell in row.cells}
    limitations = _limitations(c)
    return Cp3cResult(
        refinancing=refinancing,
        tables=tables,
        judgments=_judgments(c, cells["T3D.3.r04"]),
        gaps_ledger=TextTable(
            "T3D.8", "Gaps ledger", tuple((label, kind) for label, kind, _ in limitations)
        ),
        trace=_trace(c),
        claims=_claims(c, cells),
        own_limitations=tuple(text for _, _, text in limitations),
        status="restricted",
    )
