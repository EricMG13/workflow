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
The Stage 1 calculation does no I/O and touches no store, host, session or renderer. The Stage 2
section at the end connects it (G1-X protocol section 2): the store adapter over the bound CP-1
and CP-2D heads (CP-2D read through `cp2d_reader`), validation, the composed module, the exact
`read_inputs` view, the journal seams and the consumer reader the lease pins.
"""

import hashlib
import json
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from dataclasses import field as _field
from datetime import date
from decimal import ROUND_HALF_UP, Context, Decimal, localcontext
from types import MappingProxyType
from typing import Any, Final, Literal

from pydantic import ValidationError

from deploy_vii import prose
from deploy_vii.business_context import prohibited_issues, spelled
from deploy_vii.contracts import (
    Citation,
    Claim,
    Contract,
    Fact,
    Hash,
    Identifier,
    Input,
    Module,
    ReportTable,
    Run,
    TableColumn,
    TableRow,
    Text,
)
from deploy_vii.display import format_date
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
    Head,
    Qualification,
    StepValidation,
    bounded_issues,
    clipped,
    current_inputs,
    head_of,
    inherited_limitations,
)
from deploy_vii.live.schema import exact_json, json_object, normalise
from deploy_vii.live.submission import Submitted
from deploy_vii.preparation import PreparedPack
from deploy_vii.readiness import shape_issues
from deploy_vii.report_view import fact_spelling, figure_unit
from deploy_workflow.owners import cp2d
from deploy_workflow.owners.blank import is_blank
from deploy_workflow.owners.cp1a import probe_one_step
from deploy_workflow.owners.cp2d import Cp2dHead
from deploy_workflow.owners.cp2g import stale_issues

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
        # Stage 2 round 5 item 7 (Info 3): the module's own frame, not its producer's.
        _check_value(f"CP-3C {self.table_id}", self.status, self.amount, self.text, self.reason)


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
        _check_value(f"CP-3C {self.fact_id}", self.status, self.amount, self.text, self.reason)


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


def _unstated_gap(fid: str, term: str, status: Status = "missing") -> Gap:
    """Round 8 B6: a term that is missing (or a NOT_STATED flag) is not stated. Stage 2 round 5
    item 7 (Info 2): a conflicting or not applicable term names its status in the same frame."""
    reason = (
        NOT_STATED.format(fid=fid, term=term)
        if status == "missing"
        else f"{_NOT_CALCULABLE}facility {fid} {term} is {_STATE_WORD[status]}"
    )
    return Gap(reason, cause=_UNSTATED_CAUSE.format(term=term))


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
    # The status of each unsettled term above ("annual amortisation", "secured status",
    # "seniority"), from the head fact; one absent here is missing (Stage 2 round 5 item 7).
    statuses: Mapping[str, Status] = _field(default_factory=dict)


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
            status = f.statuses.get(term, "missing") if value is None else "missing"
            return _unstated_gap(f.facility_id, term, status)
        if value not in table:  # CP-1's ranking vocabulary is closed (ruling C-6): an invariant
            raise ValueError(
                clipped(("CP-3C ", f.facility_id, ": unknown ranking flag ", repr(value)))
            )
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
        term = "annual amortisation"
        return _unstated_gap(f.facility_id, term, f.statuses.get(term, "missing"))
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
        # The oracle's reason for a minimum cash that is missing; Stage 2 round 5 item 7
        # (Info 2): a conflicting or not applicable one names its status in the C-2 frame.
        minimum: Num
        if o.minimum_cash is not None:
            minimum = o.minimum_cash
        elif o.status("minimum_cash") == "missing":
            minimum = Gap(REASON_MINIMUM_CASH)
        else:
            minimum = _op(None, "minimum cash", o.status("minimum_cash"))
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
        raise ValueError(clipped(("CP-3C ", fact.fact_id, ": inside-horizon flag ", repr(flag))))
    return None if flag is None else flag == "Yes"


UNSOURCED_CURRENCY = (
    "CP-3C: the reporting currency is not sourced: cash_closing is not known and no known "
    "US$ m fact states a currency"
)


def _millions_read(cp1: Cp1Operands, cp2d: Cp2dOperands) -> list[tuple[str, Cp1Fact | Cp2dFact]]:
    """Every US$ m fact CP-3C reads besides cash_closing, in reading order, by its name."""
    return [
        ("undrawn_rcf", cp1.undrawn_rcf),
        ("adjusted_ebitda", cp1.adjusted_ebitda),
        ("cash_interest", cp1.cash_interest),
        *((f"{t.facility_id}.annual_amortisation", t.annual_amortisation) for t in cp1.facilities),
        *((f.fact_id, f) for f in (cp2d.run_rate, cp2d.minimum_cash, cp2d.funding_gap)),
        *((r.principal.fact_id, r.principal) for r in cp2d.wall),
    ]


def _cash_currency(cash: Cp1Fact) -> str:
    if cash.currency is None or is_blank(cash.currency):
        raise ValueError("CP-3C cash_closing: currency is not set")
    return cash.currency


def reporting_currency(*, cp1: Cp1Operands, cp2d: Cp2dOperands) -> str:
    """The currency every summed amount is in (round 13 item 5; Stage 2 round 5 item 7, Info 1):
    CP-1 T4.10 ``cash_closing``'s own currency when that fact is known (it must be set);
    otherwise the currency the first known US$ m fact read states (``check_currency`` then holds
    every other one to it). When cash_closing is not known and no known US$ m fact states a
    currency (none is known, or every one is blank), the currency is unsourced: an invariant
    raise, never a stamped default."""
    if cp1.cash_closing.status == "known":
        return _cash_currency(cp1.cash_closing)
    for _, fact in _millions_read(cp1, cp2d):
        stated = fact.currency
        if fact.status == "known" and fact.unit == _MILLIONS and stated and not is_blank(stated):
            return stated
    raise ValueError(UNSOURCED_CURRENCY)


def check_currency(*, cp1: Cp1Operands, cp2d: Cp2dOperands, currency: str) -> None:
    """Round 13 item 5 (R1 L2): the reporting currency is CP-1 T4.10 ``cash_closing``'s own
    currency, which must be set, and every known MILLIONS fact CP-3C reads states the same one.
    A cash_closing that is not known states none: the currency is then the one the known
    US$ m facts state, and an unsourced one raises (``reporting_currency``)."""
    cash = cp1.cash_closing
    if cash.status == "known":
        if _cash_currency(cash) != currency:
            raise ValueError(
                f"CP-3C: reporting currency {currency!r} is not cash_closing's {cash.currency!r}"
            )
    else:
        reporting_currency(cp1=cp1, cp2d=cp2d)
    for name, fact in _millions_read(cp1, cp2d):
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
        # Round 8 B6 (2D-c); Stage 2 round 5 item 7: an unsettled principal names its status.
        principal = (
            _unstated_gap(fid, "principal", row.principal.status) if amount is None else amount
        )
    stated = _stated_text(
        row.maturity_date.fact_id, row.maturity_date.status, row.maturity_date.text
    )
    maturity: date | Gap
    months: int | Gap
    inside: bool | Gap
    if stated is None:  # round 8 B6 (2D-c): no position
        maturity = months = inside = _unstated_gap(fid, "maturity date", row.maturity_date.status)
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
        statuses={
            term: fact.status
            for term, fact in (
                ("annual amortisation", terms.annual_amortisation),
                ("secured status", terms.secured_status),
                ("seniority", terms.seniority),
            )
            if fact.status != "known"
        },
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
            ("minimum_cash", cp2d.minimum_cash),
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
            raise ValueError(
                clipped(("CP-3C claim figure ", fact_id, ": not a known computed figure"))
            )
        unit = figure_unit(cell.fact())
        if unit is None:
            raise ValueError(clipped(("CP-3C claim figure ", fact_id, ": no figure unit")))
        return "{" + fact_id + "|" + unit + "}"

    def chip(self, fact_id: str) -> str:
        if self.cells[fact_id].status == "known":
            raise ValueError(clipped(("CP-3C claim chip ", fact_id, ": a chip names a gap")))
        return "[" + fact_id + "]"

    def either(self, fact_id: str) -> str:
        return self.fig(fact_id) if self.cells[fact_id].status == "known" else self.chip(fact_id)

    def claim(self, claim_id: str, template: str, names: Sequence[str]) -> ClaimText:
        gaps = {k for k, v in self.cells.items() if v.status != "known"}
        found = prose.check(template, refs=self.cells.keys() - gaps, gaps=gaps)
        if found:
            raise ValueError(clipped(("CP-3C ", claim_id, ": ", "; ".join(bounded_issues(found)))))
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
        raise ValueError("CP-3C submission is invalid: " + "; ".join(bounded_issues(issues)))
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


# =============================================================================================
# Stage 2: the connection (docs/CP3C-OWNER-LEASE.md Public API; docs/G1X-OWNER-CORE-PROTOCOL.md)
# =============================================================================================

STEP_ID = "refinancing_risk"
STEP_IDS: tuple[str, ...] = (STEP_ID,)
SCHEMAS: Mapping[str, type[Contract]] = MappingProxyType({STEP_ID: RefinancingRiskSubmission})
QUALIFICATION = Qualification(implementation="implemented")
# G1-X section 2: a settled owner-only head adds exactly this input after its attempt inputs.
SUBMISSION_INPUT = STEP_ID.replace("_", "-") + "-submission"
EDGES = ("CP-0", "CP-1", "CP-2D")
# manifest.json#optional_edges.unread, in the view tree's order: absent from the attempt inputs,
# the view and the trace; each is an own limitation.
UNREAD_OPTIONAL_EDGES = ("CP-1A", "CP-2A", "CP-4", "CP-3D")
CP1: Final = "CP-1"
CP2D: Final = "CP-2D"
_SCALE = Decimal(1000000)

# --- the bindings (cases/cp3c-owner/manifest.json `fact_bindings`) ------------------------------

CP1_METRICS = ("cash_closing", "undrawn_rcf", "adjusted_ebitda", "cash_interest")
FACT_BINDINGS: Mapping[str, cp2d.FactBinding] = MappingProxyType(
    {
        name: cp2d.FactBinding(
            "T4.10",
            "LTM Q4 25: 2025-01-01 to 2025-12-31",
            f"LTM Q4 25 (2025-01-01 to 2025-12-31) · {name}",
        )
        for name in CP1_METRICS
    }
)
# T4.18: the QUARTER period at the latest period end wins over its FY alias; the alias must agree
# on every term; one row per facility_id. Names are `<facility_id>.<term>`.
SCHEDULE_PERIOD = "q4-2025"
FACILITY_TERMS = ("secured_status", "seniority", "annual_amortisation", "facility_name")
_ALIAS_TERMS = ("currency", "rate_type", *FACILITY_TERMS)
# CP-2D: the stable fact ids of the CP-2D oracle; the wall cells are named
# `cp2d.<facility_id>.<field>` (T2E.4 columns 1-4 of the facility's row).
CP2D_FACTS: Mapping[str, str] = MappingProxyType(
    {
        "cp2d.horizon": "T2E.3.r03",
        "cp2d.run_rate": "T2E.3.r01",
        "cp2d.min_cash": "T2E.5.r04",
        "cp2d.funding_gap": "T2E.5.r07",
    }
)
WALL_FIELDS = ("principal", "maturity_date", "months", "inside_horizon")
_VALUE_CLASSES: Mapping[str, ValueClass] = {
    "source": "source",
    "calculated": "calculated",
    "analyst_judgment": "analyst_judgment",
}


@dataclass(frozen=True)
class Offered:
    """One upstream fact the read view offers and T3D.9 traces, by its binding name."""

    name: str
    source: Literal["CP-1", "CP-2D"]
    fact: Fact


@dataclass(frozen=True)
class Cp1Selection:
    operands: Cp1Operands
    balance_date: date
    offered: tuple[Offered, ...]
    facilities: tuple[Mapping[str, str | None], ...]  # the view's facility list (text only)


@dataclass(frozen=True)
class Selection:
    """What the bindings select from the bound CP-1 and CP-2D heads: the Stage 1 operands, the
    balance date, the reporting currency and the offered facts (sorted by name)."""

    cp1: Cp1Operands
    cp2d: Cp2dOperands
    balance_date: date
    currency: str
    offered: tuple[Offered, ...]
    facilities: tuple[Mapping[str, str | None], ...]

    @property
    def refs(self) -> tuple[tuple[str, str], ...]:
        """(binding name, the ref the view offers for it)."""
        return tuple((o.name, o.fact.fact_id) for o in self.offered)

    def named(self, name: str) -> Fact | None:
        return next((o.fact for o in self.offered if o.name == name), None)

    def by_ref(self, ref: str) -> Fact | None:
        return next((o.fact for o in self.offered if o.fact.fact_id == ref), None)


def _value_class(name: str, fact: Fact) -> ValueClass | None:
    if fact.value_class is None:
        return None
    read = _VALUE_CLASSES.get(fact.value_class)
    if read is None:
        raise ValueError(clipped(("CP-3C ", name, ": a ", fact.value_class, " fact is not read")))
    return read


def _cp1_fact(name: str, fact: Fact, *, money: bool) -> Cp1Fact:
    """A CP-1 head fact as Stage 1 reads it. A money term must be in millions (unit MILLIONS, or
    `currency` at scale 1e6, normalised to MILLIONS; a gap takes that unit, its twin's)."""
    millions = fact.unit in (_MILLIONS, "currency") and fact.scale == _SCALE
    if money and fact.unit is not None and not millions:
        raise ValueError(clipped(("CP-3C ", name, ": not an amount in millions")))
    if fact.period is None:
        raise ValueError(clipped(("CP-3C ", name, ": the CP-1 fact states no period")))
    return Cp1Fact(
        table_id=fact.table_id,
        period=fact.period,
        status=fact.status,
        amount=fact.amount,
        text=fact.text,
        unit=_MILLIONS if money else fact.unit,
        value_class=_value_class(name, fact),
        reason=None if fact.status == "known" else fact.limitation,
        currency=fact.currency,
    )


def _rows(module: Module, table_id: str) -> dict[str, dict[str, Fact]]:
    rows: dict[str, dict[str, Fact]] = {}
    for fact in module.facts:
        if fact.table_id == table_id:
            row = rows.setdefault(fact.row_id, {})
            if fact.field in row:
                raise ValueError(clipped(("CP-3C: duplicate CP-1 coordinate ", fact.fact_id)))
            row[fact.field] = fact
    return rows


def _known_text(row: Mapping[str, Fact], field: str) -> str | None:
    fact = row.get(field)
    return fact.text if fact is not None and fact.status == "known" else None


def _balance_date(module: Module) -> tuple[date, tuple[str, ...]]:
    """The end date of the schedule period (T4.14) and the other periods ending that day."""
    ends: dict[str, str] = {}
    for row in _rows(module, "T4.14").values():
        pid, end = _known_text(row, "period_id"), _known_text(row, "end_date")
        if pid is not None and end is not None:
            ends[pid] = end
    if SCHEDULE_PERIOD not in ends:
        raise ValueError(f"CP-3C: CP-1 states no end date for {SCHEDULE_PERIOD}")
    aliases = tuple(
        p for p, e in ends.items() if e == ends[SCHEDULE_PERIOD] and p != SCHEDULE_PERIOD
    )
    return date.fromisoformat(ends[SCHEDULE_PERIOD]), aliases


def _same(a: Fact | None, b: Fact | None) -> bool:
    if a is None or b is None:
        return a is b
    return (a.amount, a.text, a.status, a.unit, a.currency, a.scale) == (
        b.amount,
        b.text,
        b.status,
        b.unit,
        b.currency,
        b.scale,
    )


def _facility_rows(module: Module, aliases: tuple[str, ...]) -> dict[str, dict[str, Fact]]:
    """The T4.18 row of each facility at the schedule period; each FY alias row must agree on
    every term CP-3C reads."""
    chosen: dict[str, dict[str, Fact]] = {}
    by_period: dict[tuple[str, str], dict[str, Fact]] = {}
    for row in _rows(module, "T4.18").values():
        fid = _known_text(row, "facility_id")
        period = row["facility_id"].period if "facility_id" in row else None
        if fid is None or period is None:
            raise ValueError("CP-3C: a CP-1 T4.18 row has no known facility_id and period")
        if (fid, period) in by_period:
            raise ValueError(clipped(("CP-3C: facility ", fid, " has two T4.18 rows in ", period)))
        by_period[fid, period] = row
        if period == SCHEDULE_PERIOD:
            chosen[fid] = row
    for alias in aliases:
        listed = {fid for (fid, period) in by_period if period == alias}
        if listed != set(chosen):
            raise ValueError(f"CP-3C: the {alias} T4.18 rows are not the {SCHEDULE_PERIOD} rows")
        for fid, row in chosen.items():
            for term in _ALIAS_TERMS:
                if not _same(row.get(term), by_period[fid, alias].get(term)):
                    raise ValueError(
                        clipped(
                            (
                                f"CP-3C: facility {fid} {term} differs between its ",
                                f"{SCHEDULE_PERIOD} row and its {alias} alias",
                            )
                        )
                    )
    return chosen


def _terms(fid: str, row: Mapping[str, Fact]) -> FacilityTerms:
    def term(field: str) -> Cp1Fact:
        fact = row.get(field)
        if fact is None:
            raise ValueError(clipped(("CP-3C: facility ", fid, " has no CP-1 ", field, " fact")))
        return _cp1_fact(f"{fid}.{field}", fact, money=field == "annual_amortisation")

    return FacilityTerms(
        facility_id=fid,
        currency=_known_text(row, "currency"),
        facility_name=term("facility_name"),
        secured_status=term("secured_status"),
        seniority=term("seniority"),
        annual_amortisation=term("annual_amortisation"),
    )


def select_cp1(cp1: Module) -> Cp1Selection:
    """Apply the CP-1 bindings. Each T4.10 name selects exactly one fact (zero or several raise);
    a fact CP-1 reports missing, conflicting or not applicable is read as that status."""
    index: dict[tuple[str, str, str], list[Fact]] = {}
    for fact in cp1.facts:
        if fact.table_id == "T4.10":
            index.setdefault((fact.table_id, fact.period or "", fact.label), []).append(fact)
    offered: list[Offered] = []
    metrics: dict[str, Cp1Fact] = {}
    for name, b in FACT_BINDINGS.items():
        hits = index.get((b.table_id, b.period, b.label), [])
        if len(hits) != 1:
            raise ValueError(f"CP-3C: CP-1 offers {len(hits)} facts for {name}, not exactly one")
        offered.append(Offered(name, CP1, hits[0]))
        metrics[name] = _cp1_fact(name, hits[0], money=True)
    balance, aliases = _balance_date(cp1)
    rows = _facility_rows(cp1, aliases)
    facilities = tuple(_terms(fid, row) for fid, row in rows.items())
    offered += [
        Offered(f"{fid}.{term}", CP1, row[term])
        for fid, row in rows.items()
        for term in FACILITY_TERMS
    ]
    listed = tuple(
        {"facility_id": fid}
        | {k: _known_text(row, k) for k in ("facility_name", "secured_status", "seniority")}
        | {"rate_type": _known_text(row, "rate_type")}
        for fid, row in rows.items()
    )
    operands = Cp1Operands(
        cash_closing=metrics["cash_closing"],
        undrawn_rcf=metrics["undrawn_rcf"],
        adjusted_ebitda=metrics["adjusted_ebitda"],
        cash_interest=metrics["cash_interest"],
        facilities=facilities,
    )
    return Cp1Selection(operands, balance, tuple(offered), listed)


def _cp2d_fact(fact: Fact) -> Cp2dFact:
    unit = fact.unit
    if unit in (_MILLIONS, "currency"):
        if fact.scale != _SCALE:
            raise ValueError(clipped(("CP-3C ", fact.fact_id, ": not an amount in millions")))
        unit = _MILLIONS
    return Cp2dFact(
        fact_id=fact.fact_id,
        status=fact.status,
        amount=fact.amount,
        text=fact.text,
        unit=unit,
        period=fact.period,
        value_class=_value_class(fact.fact_id, fact),
        reason=None if fact.status == "known" else fact.limitation,
        currency=fact.currency,
    )


def _facility_of(label: str) -> str:
    """The facility id of a CP-2D wall row, labelled `<name> (<facility_id>)`."""
    _, sep, tail = label.rpartition(" (")
    if not sep or not tail.endswith(")") or len(tail) == 1:
        raise ValueError(clipped(("CP-3C: CP-2D wall row ", label, " names no facility id")))
    return tail[:-1]


def _reader_agrees(read: Cp2dHead, ops: Cp2dOperands, labels: Sequence[str]) -> None:
    """D3: the figures `cp2d_reader` gives for the bound head are the head's own cells."""

    def value(f: Cp2dFact) -> tuple[Decimal | None, str | None]:
        return f.amount, (f.reason if f.amount is None else None)

    horizon = None if read.horizon_months is None else Decimal(read.horizon_months)
    pairs: list[tuple[str, object, object]] = [
        (ops.horizon.fact_id, horizon, ops.horizon.amount),
        (
            ops.minimum_cash.fact_id,
            (read.minimum_cash, read.minimum_cash_absent),
            value(ops.minimum_cash),
        ),
        (
            ops.funding_gap.fact_id,
            (read.funding_gap, read.funding_gap_missing),
            value(ops.funding_gap),
        ),
        ("T2E.4", tuple(w.facility for w in read.wall), tuple(labels)),
    ]
    flag = {True: "Yes", False: "No"}
    for w, r in zip(read.wall, ops.wall, strict=False):
        when = None if w.maturity_date is None else w.maturity_date.isoformat()
        inside = None if w.inside_horizon is None else flag[w.inside_horizon]
        pairs += [
            (r.principal.fact_id, w.principal, r.principal.amount),
            (r.maturity_date.fact_id, when, r.maturity_date.text),
            (r.months.fact_id, w.months_to_maturity, r.months.amount),
            (r.inside_horizon.fact_id, inside, r.inside_horizon.text),
        ]
    for fact_id, reader, head in pairs:
        if reader != head:
            raise ValueError(
                clipped(("CP-3C: cp2d_reader and the CP-2D head disagree on ", fact_id))
            )


def select_cp2d(module: Module, read: Cp2dHead) -> tuple[Cp2dOperands, tuple[Offered, ...]]:
    """The CP-2D figures through `cp2d_reader`, each with its head cell's status, unit, period,
    value class and reason (the reader exposes none of these, nor T2E.3.r01: the run-rate flow
    is read from its cell, the pin extension expected.json#consumption names)."""
    facts = {f.fact_id: f for f in module.facts}

    def fact(fact_id: str) -> Fact:
        if fact_id not in facts:
            raise ValueError(clipped(("CP-3C: the CP-2D head has no fact ", fact_id)))
        return facts[fact_id]

    table = next((t for t in module.tables if t.table_id == "T2E.4"), None)
    if table is None:
        raise ValueError("CP-3C: the CP-2D head has no maturity wall (T2E.4)")
    offered = [Offered(name, CP2D, fact(fid)) for name, fid in CP2D_FACTS.items()]
    wall = []
    for row in table.rows:
        fid = _facility_of(row.label)
        cells = [fact(i) for i in row.fact_ids[: len(WALL_FIELDS)]]
        offered += [
            Offered(f"cp2d.{fid}.{f}", CP2D, c) for f, c in zip(WALL_FIELDS, cells, strict=True)
        ]
        wall.append(WallRow(fid, *(_cp2d_fact(c) for c in cells)))
    named = {o.name: _cp2d_fact(o.fact) for o in offered[: len(CP2D_FACTS)]}
    ops = Cp2dOperands(
        horizon=named["cp2d.horizon"],
        run_rate=named["cp2d.run_rate"],
        minimum_cash=named["cp2d.min_cash"],
        funding_gap=named["cp2d.funding_gap"],
        wall=tuple(wall),
    )
    _reader_agrees(read, ops, [row.label for row in table.rows])
    return ops, tuple(offered)


# --- the bound upstream -----------------------------------------------------------------------


@dataclass(frozen=True)
class Upstream:
    """What one CP-3C attempt binds, read once from the journal (`cp3c_upstream`): the input set,
    `execution.current_inputs` now (or its refusal text), the run's as-of, the settled CP-1 and
    CP-2D modules of the bound heads, `cp2d_reader` over the bound CP-2D head, and what settlement
    will inherit (`execution.inherited_limitations`). CP-0 is an edge whose status and
    limitations CP-3C inherits and whose content it never reads."""

    bound: tuple[Input, ...]
    current: tuple[Input, ...] | str
    as_of: date
    cp1: Module
    cp2d: Module
    cp2d_read: Cp2dHead
    inherited: tuple[str, ...]


def cp3c_upstream(*, store: Execution, attempt: Attempt) -> Upstream:
    """A refusal of `current_inputs` (an upstream gone stale, unrun or blocked, or CP-0 no longer
    authorizing CP-3C) is kept as text: the validator reports it as a staleness issue. A bound
    input whose blob is another module's raises."""
    snapshot = store.read()
    current: tuple[Input, ...] | str
    try:
        current = current_inputs(snapshot, MODULE_ID)
    except ValueError as error:  # NotAuthorized included: reported, never passed as current
        current = str(error)

    def bound(module_id: str) -> Module:
        item = next((i for i in attempt.inputs if i.input_id == module_id), None)
        if item is None:
            raise ValueError(f"The CP-3C attempt binds no {module_id} input")
        module = store.result(item.sha256)
        if module.module_id != module_id:
            raise ValueError(
                f"The CP-3C attempt's {module_id} input is a {module.module_id} module"
            )
        return module

    cp1, settled = bound(CP1), bound(CP2D)
    return Upstream(
        bound=attempt.inputs,
        current=current,
        as_of=snapshot.run.as_of,
        cp1=cp1,
        cp2d=settled,
        cp2d_read=cp2d.cp2d_reader(store, head_of(settled)),
        inherited=inherited_limitations(snapshot, attempt, (), store.head_module),
    )


def select(upstream: Upstream) -> Selection:
    """The store adapter: the bound heads -> the Stage 1 operands. `submit`, `probe` and `view`
    reach the CP-1 and CP-2D facts only through this selection."""
    cp1 = select_cp1(upstream.cp1)
    ops, cp2d_offered = select_cp2d(upstream.cp2d, upstream.cp2d_read)
    return Selection(
        cp1=cp1.operands,
        cp2d=ops,
        balance_date=cp1.balance_date,
        currency=reporting_currency(cp1=cp1.operands, cp2d=ops),
        offered=tuple(sorted((*cp1.offered, *cp2d_offered), key=lambda o: o.name)),
        facilities=cp1.facilities,
    )


def _inputs_from(
    upstream: Upstream, selection: Selection, submission: RefinancingRiskSubmission
) -> Cp3cInputs:
    return Cp3cInputs(
        balance_date=selection.balance_date,
        as_of=upstream.as_of,
        currency=selection.currency,
        cp1=selection.cp1,
        cp2d=selection.cp2d,
        submission=submission,
        offered={ref: name for name, ref in selection.refs},
    )


def _inputs(
    store: Execution, attempt: Attempt, submission: RefinancingRiskSubmission
) -> Cp3cInputs:
    upstream = cp3c_upstream(store=store, attempt=attempt)
    return _inputs_from(upstream, select(upstream), submission)


# --- validation -------------------------------------------------------------------------------


def _provenance_issues(upstream: Upstream) -> tuple[str, ...]:
    """The supplied CP-1 and CP-2D modules (and the CP-2D read) are the bound heads."""
    issues = []
    for module_id, module in ((CP1, upstream.cp1), (CP2D, upstream.cp2d)):
        item = next((i for i in upstream.bound if i.input_id == module_id), None)
        read = upstream.cp2d_read.head_sha256 if module_id == CP2D else module.content_hash()
        if (
            item is None
            or module.module_id != module_id
            or module.content_hash() != item.sha256
            or read != item.sha256
        ):
            issues.append(f"Upstream {module_id}: the supplied module is not the bound input")
    return tuple(issues)


def validate_refinancing(
    *, submission: RefinancingRiskSubmission, upstream: Upstream
) -> tuple[str, ...]:
    """Staleness alone when a bound upstream changed (no content check runs on it), then
    provenance alone, else the calculation-level issues over the refs the view offers."""
    stale = stale_issues(bound=upstream.bound, current=upstream.current)
    if stale:
        return stale
    provenance = _provenance_issues(upstream)
    if provenance:
        return provenance
    offered = {ref: name for name, ref in select(upstream).refs}
    return submission_issues(submission=submission, offered=offered)


# --- the composed module ----------------------------------------------------------------------


class RefinancingRiskReport(Contract):
    """The composed CP-3C module body of a valid submission (a step's retained output)."""

    run: Run
    pack_sha256: Hash
    submission_sha256: Hash
    facts: tuple[Fact, ...]
    tables: tuple[ReportTable, ...]
    claims: tuple[Claim, ...]
    limitations: tuple[str, ...]


def _copied(cell: Cell, selection: Selection) -> Fact | None:
    """The upstream fact a copy (an operand and no formula) copies."""
    if cell.formula is not None:
        return None
    if cell.cp2d_operand is not None:
        return selection.by_ref(cell.cp2d_operand)
    if cell.cp1_operand is not None:
        operand = cell.cp1_operand
        if operand.startswith("T4.18 "):
            fid, term = operand.removeprefix("T4.18 ").rsplit(" ", 1)
            operand = f"{fid}.{term}"
        return selection.named(operand)
    return None


def _cell_fact(cell: Cell, selection: Selection) -> Fact:
    """A cell as a Module fact (lease Composer; acceptance 1): a copy keeps its upstream fact's
    citations and calculation id; a known computed cell names its calculation; a US$ m cell is
    at scale 1e6, as CP-1 and CP-2D write theirs."""
    extra: dict[str, Any] = {"scale": _SCALE} if cell.unit == _MILLIONS else {}
    source = _copied(cell, selection)
    copy = cell.formula is None and (cell.cp1_operand or cell.cp2d_operand) is not None
    if copy and source is None:  # an invariant: every operand names a bound fact
        raise ValueError(clipped(("CP-3C ", cell.fact_id, ": its upstream fact is not bound")))
    if source is not None:
        extra |= {"citations": source.citations, "calculation_id": source.calculation_id}
    elif cell.formula is not None and cell.status == "known":
        extra["calculation_id"] = f"calc:{cell.fact_id}"
    return cell.fact().model_copy(update=extra)


def _report_table(table: Table) -> ReportTable:
    single = len(table.columns) == 1
    fields = ["value"] if single else [f"c{n}" for n in range(1, len(table.columns) + 1)]
    return ReportTable(
        table_id=table.table_id,
        title=table.title,
        columns=tuple(
            TableColumn(field=f, label=c) for f, c in zip(fields, table.columns, strict=True)
        ),
        rows=tuple(
            TableRow(row_id=r.row_id, label=r.label, fact_ids=tuple(c.fact_id for c in r.cells))
            for r in table.rows
        ),
        row_header=table.row_header,
    )


# T3D.7-T3D.9 (lease freeze note 4: text rows): the row header and the (field, heading) columns
# after the row label.
_TEXT_TABLES: Mapping[str, tuple[str, tuple[tuple[str, str], ...]]] = {
    "T3D.7": ("Judgment", (("value", "Value"),)),
    "T3D.8": ("Item", (("kind", "Kind"),)),
    "T3D.9": ("Name", (("module", "Module"), ("ref", "Table or id"), ("shown", "Shown"))),
}


def _text_table(table: TextTable) -> tuple[ReportTable, list[Fact]]:
    header, columns = _TEXT_TABLES[table.table_id]
    judged: Literal["analyst_judgment"] | None = (
        "analyst_judgment" if table.table_id == "T3D.7" else None
    )
    facts: list[Fact] = []
    rows: list[TableRow] = []
    for n, (label, *values) in enumerate(table.rows, 1):
        row_id = f"r{n:02d}"
        ids = []
        for (field, _), text in zip(columns, values, strict=True):
            one = len(columns) == 1
            fact_id = f"{table.table_id}.{row_id}" + ("" if one else f".{field}")
            facts.append(
                Fact(
                    fact_id=fact_id,
                    label=label if one else f"{label} · {field}",
                    table_id=table.table_id,
                    row_id=row_id,
                    field=field,
                    text=text,
                    value_class=judged,
                )
            )
            ids.append(fact_id)
        rows.append(TableRow(row_id=row_id, label=label, fact_ids=tuple(ids)))
    report = ReportTable(
        table_id=table.table_id,
        title=table.title,
        columns=tuple(TableColumn(field=f, label=h) for f, h in columns),
        rows=tuple(rows),
        row_header=header,
    )
    return report, facts


def _module_claims(
    result: Cp3cResult, selection: Selection, facts: Mapping[str, Fact]
) -> tuple[Claim, ...]:
    """Each claim's template as its run text, citing what the bound names and the referenced
    cells it lists (`cites_from`) cite, each citation once."""

    def cited(item: str) -> tuple[Citation, ...]:
        fact = selection.named(item) or facts.get(item)
        if fact is None:
            raise ValueError(clipped(("CP-3C: a claim cites ", item, ", which is not bound")))
        return fact.citations

    return tuple(
        Claim(
            claim_id=c.claim_id,
            text=c.template,
            citations=tuple(dict.fromkeys(x for item in c.cites_from for x in cited(item))),
        )
        for c in result.claims
    )


def refinancing_risk(
    *, pack: PreparedPack, submission: RefinancingRiskSubmission, upstream: Upstream
) -> RefinancingRiskReport:
    """The composed CP-3C tables, facts, claims and own limitations of a valid submission;
    raises ValueError on any validation issue."""
    issues = validate_refinancing(submission=submission, upstream=upstream)
    if issues:
        raise ValueError("; ".join(bounded_issues(issues)))
    selection = select(upstream)
    result = compute(_inputs_from(upstream, selection, submission))
    facts = [_cell_fact(c, selection) for t in result.tables for r in t.rows for c in r.cells]
    tables = [_report_table(t) for t in result.tables]
    for text in (result.judgments, result.gaps_ledger, result.trace):
        table, rows = _text_table(text)
        tables.append(table)
        facts += rows
    return RefinancingRiskReport(
        run=pack.run,
        pack_sha256=pack.content_hash(),
        submission_sha256=submission.content_hash(),
        facts=tuple(facts),
        tables=tuple(tables),
        claims=_module_claims(result, selection, {f.fact_id: f for f in facts}),
        limitations=result.own_limitations,
    )


def cp3c_module(*, report: RefinancingRiskReport, inputs: Sequence[Input], attempt: int) -> Module:
    """The CP-3C candidate: the report bound to `inputs` and, as the settled tail (G1-X section
    2), the digest of the retained submission."""
    run = report.run
    return Module(
        run_id=run.run_id,
        issuer_id=run.issuer_id,
        as_of=run.as_of,
        module_id=MODULE_ID,
        inputs=(*inputs, Input(input_id=SUBMISSION_INPUT, sha256=report.submission_sha256)),
        facts=report.facts,
        tables=report.tables,
        claims=report.claims,
        limitations=report.limitations,
        attempt=attempt,
    )


# --- the exact `read_inputs` view (manifest.json view_tree_draft) -----------------------------


def context_block(*, pack: PreparedPack, upstream: Upstream) -> dict[str, object]:
    """The step's one read, all Python's: the required edges' statuses, one entry per bound name
    (a missing fact included, with its status and its limitation, never a number), the facility
    list (text only), the unread optional edges, the submission bounds and the limitations
    settlement will inherit. No quote, citation or record at any depth."""
    for module in (upstream.cp1, upstream.cp2d):
        if module.run_id != pack.run.run_id:
            raise ValueError(f"CP-3C: the bound {module.module_id} module belongs to another run")
    selection = select(upstream)
    return {
        "upstream": [
            {"module_id": i.input_id, "status": i.status}
            for i in upstream.bound
            if i.input_id in EDGES
        ],
        "facts": [
            {
                "ref": o.fact.fact_id,
                "name": o.name,
                "source": o.source,
                "label": o.fact.label,
                "period": o.fact.period,
                "unit": figure_unit(o.fact) or o.fact.unit,
                "shown": spelled(o.fact)
                if o.fact.status == "known"
                else _STATE_WORD[o.fact.status],
                "status": o.fact.status,
                "limitation": o.fact.limitation,
            }
            for o in selection.offered
        ],
        "facilities": [dict(f) for f in selection.facilities],
        "unread_optional_edges": list(UNREAD_OPTIONAL_EDGES),
        "bounds": {
            "repricing_bps": list(BPS_BOUNDS),
            "path_kinds": list(KINDS),
            "feasibility": ["High", "Medium", "Low", II],
        },
        "inherited_limitations": list(upstream.inherited),
    }


def view(historical: Execution, attempt: Attempt) -> tuple[str, str]:
    """(sha256, body) of `context_block` over the bound heads as compact JSON (registered in G1's
    `_VIEWS["refinancing_risk"]`; an exact view, counted as tool use)."""
    upstream = cp3c_upstream(store=historical, attempt=attempt)
    block = context_block(pack=historical.pack(), upstream=upstream)
    body = json.dumps(block, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(body.encode()).hexdigest(), body


# --- the journal: validator, probe and submit -------------------------------------------------


def _parsed(payload: str) -> tuple[RefinancingRiskSubmission | None, tuple[str, ...]]:
    """The submission, or its shape issues (protocol section 6: model text is read only through
    `json_object`; the schema validates the bounded document's exact re-serialisation)."""
    document = json_object(payload)
    try:
        if document is None:
            RefinancingRiskSubmission.model_validate_json(payload)  # for its shape issue only
            return None, ("(root): not a bounded JSON object",)
        return RefinancingRiskSubmission.model_validate_json(exact_json(document)), ()
    except ValidationError as error:
        return None, shape_issues(error)


def _validate_step(store: Execution, pack: PreparedPack, attempt: Attempt) -> StepValidation:
    """The step validator `submit` hands the journal and the verifier replays: the retained
    response against the bound upstream; a valid step's output is the composed report."""
    submission, shape = _parsed(store.payload(attempt.steps[-1].payload_sha256))
    if submission is None:
        return StepValidation(issues=shape)
    upstream = cp3c_upstream(store=store, attempt=attempt)
    issues = validate_refinancing(submission=submission, upstream=upstream)
    if issues:
        return StepValidation(issues=issues)
    report = refinancing_risk(pack=pack, submission=submission, upstream=upstream)
    return StepValidation(output=report.model_dump_json())


# The validator the module's own entry hands `Execution.submit_step` (R4-2 invalid-step replay).
ENTRY_VALIDATOR = _validate_step


def _candidate(output: str, attempt: Attempt) -> Module:
    report = RefinancingRiskReport.model_validate_json(output)
    return cp3c_module(report=report, inputs=attempt.inputs, attempt=attempt.number)


def probe(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    """Raises `WorkflowError("identity_mismatch")` unless the settled attempt and head rebuild
    exactly from the journaled payload over the frozen snapshot."""
    probe_one_step(store, snapshot, attempt, validate=_validate_step, build=_candidate)


def submit(
    store: Execution,
    ticket_id: str,
    step_id: str,
    payload: str,
    rules: Callable[[str], tuple[str, ...]] | None,
) -> Submitted:
    """Journal the one `refinancing_risk` response, validate it, then settle CP-3C with the
    Python candidate in the same call. An invalid step finishes the attempt rejected (or blocked
    on the repair): there is no within-attempt repair. A crash after the step resumes from the
    retained step."""
    if rules is not None:
        raise ValueError("CP-3C has no tool-loop rules (rule mode none)")
    if step_id != STEP_ID:
        raise ValueError(f"CP-3C has one step, {STEP_ID}")
    normalised, resolved = normalise(RefinancingRiskSubmission, payload)
    attempt = next((a for a in store.read().attempts if a.ticket_id == ticket_id), None)
    if attempt is None or attempt.module_id != MODULE_ID or attempt.status != "pending":
        raise ValueError("Ticket is absent, finished or belongs to another module")
    digest = hashlib.sha256(normalised.encode()).hexdigest()
    if attempt.steps and attempt.steps[0].payload_sha256 != digest:
        raise ValueError("Ticket already retains a different response; resume or interrupt")
    if not attempt.steps or attempt.steps[0].status == "pending":
        attempt = store.submit_step(
            ticket_id,
            MODULE_ID,
            STEP_IDS,
            STEP_ID,
            normalised,
            lambda pack, current: _validate_step(store, pack, current),
        )
    if attempt.status == "finished":
        return Submitted(attempt, normalised, resolved, (), (), None)
    outcome = _validate_step(store, store.pack(), attempt)
    if outcome.issues or not outcome.retained_as(attempt.steps[0]):
        raise ValueError("Retained CP-3C output differs from trusted validation")
    candidate = _candidate(outcome.output or "", attempt)
    journal = store.finish(
        ticket_id,
        candidate.model_dump_json(),
        lambda supplied: () if supplied == candidate else ("CP-3C candidate differs",),
        qualification=QUALIFICATION,
    )
    return Submitted(journal, normalised, resolved, (), (), None)


# --- the consumer reader (lease Public API; expected.json#consumption.cp3c_consumed_by) ----------


@dataclass(frozen=True)
class NeedRow:
    """One facility's refinancing need (T3D.1 column 9); None is a gap with its reason."""

    facility: str
    need: Decimal | None
    missing: str | None


@dataclass(frozen=True)
class Cp3cHead:
    """What `cp3c_reader` exposes of a settled CP-3C head: total principal payable at maturity,
    the refinancing need or why it is missing, the per-facility need rows, the added annual cash
    interest or why it is missing, the claims at or ahead of the most junior facility (Base), the
    path feasibility judgments, the own limitations, the head hash and status. A head that is
    not accepted or restricted (blocked, stale) exposes its status and hash and no figures."""

    status: str
    head_sha256: str
    total_principal_payable: Decimal | None = None
    need: Decimal | None = None
    need_missing: str | None = None
    need_rows: tuple[NeedRow, ...] = ()
    added_interest: Decimal | None = None
    added_interest_missing: str | None = None
    base_claims: Decimal | None = None
    paths: tuple[tuple[PathKind, str], ...] = ()
    own_limitations: tuple[str, ...] = ()


def cp3c_reader(store: Execution, head: Head) -> Cp3cHead:
    """The consumer reader the lease pins (no consumer binds it yet)."""
    if head.module_id != MODULE_ID:
        raise ValueError("CP-3C reader: not a CP-3C head")
    if head.status not in ("accepted", "restricted"):
        return Cp3cHead(head.status, head.result_sha256)
    module = store.head_module(head)
    facts = {f.fact_id: f for f in module.facts}
    tables = {t.table_id: t for t in module.tables}

    def read(fact_id: str) -> Fact:
        if fact_id not in facts:
            raise ValueError(f"CP-3C head has no fact {fact_id}")
        return facts[fact_id]

    def missing(fact: Fact) -> str | None:
        return None if fact.amount is not None else fact.limitation

    def feasibility(row_id: str) -> str:
        text = read(f"T3D.6.{row_id}.c1").text
        if text is None:
            raise ValueError(f"CP-3C head: the feasibility of path {row_id} is not stated")
        return text

    need, added = read("T3D.2.r03"), read("T3D.3.r06")
    kinds = {label: kind for kind, label in KIND_LABEL.items()}
    return Cp3cHead(
        status=head.status,
        head_sha256=head.result_sha256,
        total_principal_payable=read("T3D.2.r01").amount,
        need=need.amount,
        need_missing=missing(need),
        need_rows=tuple(
            NeedRow(
                r.label, read(f"T3D.1.{r.row_id}.c9").amount, missing(read(f"T3D.1.{r.row_id}.c9"))
            )
            for r in tables["T3D.1"].rows
        ),
        added_interest=added.amount,
        added_interest_missing=missing(added),
        base_claims=read("T3D.5.r01.c1").amount,
        paths=tuple((kinds[r.label], feasibility(r.row_id)) for r in tables["T3D.6"].rows),
        own_limitations=module.limitations,
    )
