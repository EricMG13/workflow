"""CP-3C (Refinancing and liability-management risk): the module's pure calculation (Stage 1).

Lease: docs/CP3C-OWNER-LEASE.md (rev 3, frozen). Python computes, from the CP-1 head facts and
the settled CP-2D cells the lease binds, the principal payable at each maturity, the resources
available then, the refinancing need, the cost of an analyst margin step-up on interest cover
and the claims at or ahead of each facility. The analyst supplies only the step-up (or its
absence) and one feasibility judgment per refinancing path. No optional edge is read.

Missing is never 0: a missing operand makes each dependent value missing, and a table cell
states a reason only where the lease or the oracle (cases/cp3c-owner/expected.json) fixes its
wording; anywhere else the table build raises ValueError rather than invent one. Nothing here
does I/O or touches a store, host, session or renderer. Connection, tool-use and orchestration
seams (G1-X protocol section 2) are added to this file in later stages.
"""

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from decimal import ROUND_HALF_UP, Context, Decimal, localcontext
from typing import Final, Literal

from deploy_vii import prose
from deploy_vii.business_context import prohibited_issues
from deploy_vii.contracts import Contract, Fact, Identifier, Text
from deploy_vii.display import format_date
from deploy_vii.report_view import fact_spelling, figure_unit

MODULE_ID = "CP-3C"
BPS_BOUNDS = (0, 1000)

Status = Literal["known", "missing"]
CellStatus = Literal["known", "missing", "not_applicable"]
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

NOT_APPLICABLE: Final = "n.m."  # a defined ratio over a non-positive denominator, never missing
Ratio = Decimal | Literal["n.m."] | None

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

# The oracle's builder computes in Python's default decimal context; this is that context,
# fixed here so a caller's context cannot change a stored value. Ratios are then stored at
# 4 dp half-up (manifest.json#ratio_storage_rule); amounts keep every digit.
_CONTEXT = Context(prec=28)
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
        if insufficient and not p.limitation:
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
    if status == "missing" and (amount is not None or text is not None or not reason):
        raise ValueError(f"{what}: a missing fact carries a reason and no value")


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
    reason: str | None = None  # the head fact's limitation when missing

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

    def __post_init__(self) -> None:
        _check_value(f"CP-2D {self.fact_id}", self.status, self.amount, self.text, self.reason)


@dataclass(frozen=True)
class FacilityTerms:
    """The CP-1 T4.18 terms of one facility (QUARTER period over its FY alias)."""

    facility_id: str
    currency: str
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


# --- the composer (lease "Method"; every value a Decimal) -------------------------------------


@dataclass(frozen=True)
class FacilityOperand:
    facility_id: str
    principal: Decimal
    maturity_date: date
    months: int  # whole months from D0 (CP-2D's rule)
    inside_horizon: bool  # maturity on or before the CP-2D horizon end
    annual_amortisation: Decimal | None
    secured_status: str | None  # SECURED, UNSECURED or NOT_STATED; None is missing
    seniority: str | None


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


@dataclass(frozen=True)
class MaturityRow:
    facility: FacilityOperand
    amortisation_before_maturity: Decimal | None
    principal_payable: Decimal | None
    resources: Decimal | None
    applied: Decimal | None
    need: Decimal | None
    cover: Ratio


@dataclass(frozen=True)
class CreditorRow:
    facility: FacilityOperand
    share: Decimal
    claims_at_or_ahead: Decimal | None
    claims_over_ebitda: Ratio


@dataclass(frozen=True)
class Refinancing:
    operands: Operands
    step_up_bps: Decimal | None
    base_resources: Decimal | None
    maturities: tuple[MaturityRow, ...]  # ascending months, ties by facility_id
    creditors: tuple[CreditorRow, ...]  # by rank, then months, then facility_id
    total_principal: Decimal
    total_principal_payable: Decimal | None
    total_applied: Decimal | None
    total_need: Decimal | None
    principal_after_horizon: Decimal | None
    nearest_maturity: date
    months_to_nearest: int
    payable_over_ebitda: Ratio
    need_over_ebitda: Ratio
    added_interest: Decimal | None
    pro_forma_interest: Decimal | None
    interest_cover: Ratio
    pro_forma_interest_cover: Ratio
    junior_claims: Decimal | None
    junior_over_ebitda: Ratio


def _add_months(start: date, months: int) -> date:
    year, index = divmod(start.month - 1 + months, 12)
    year += start.year
    month = index + 1
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    last = (31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)[month - 1]
    return date(year, month, min(start.day, last))


def wall_position(*, balance_date: date, maturity: date, horizon_months: int) -> tuple[int, bool]:
    """CP-2D's whole-month rule: (months from D0, inside the horizon). One month fewer when the
    maturity's day of month is earlier than D0's; inside when on or before D0 + horizon."""
    months = (maturity.year - balance_date.year) * 12 + (maturity.month - balance_date.month)
    if maturity.day < balance_date.day:
        months -= 1
    return months, maturity <= _add_months(balance_date, horizon_months)


_SECURED_RANK = {"SECURED": 0, "UNSECURED": 1}
_SENIORITY_RANK = {
    "SUPER_SENIOR": 0,
    "SENIOR": 1,
    "SENIOR_SUBORDINATED": 2,
    "SUBORDINATED": 3,
    "JUNIOR": 4,
}


def _rank(f: FacilityOperand) -> tuple[int, int] | None:
    """(security, seniority), compared lexicographically; NOT_STATED or missing ranks nothing."""
    ranks: list[int] = []
    for value, table in ((f.secured_status, _SECURED_RANK), (f.seniority, _SENIORITY_RANK)):
        if value is None or value == "NOT_STATED":
            return None
        if value not in table:
            raise ValueError(f"CP-3C {f.facility_id}: unknown ranking flag {value!r}")
        ranks.append(table[value])
    return ranks[0], ranks[1]


def _r4(x: Decimal) -> Decimal:
    return x.quantize(_FOUR_DP, rounding=ROUND_HALF_UP)


def _ratio(num: Decimal | None, den: Decimal | None) -> Ratio:
    if num is None or den is None:
        return None
    return NOT_APPLICABLE if den <= 0 else _r4(num / den)


def _total(values: Iterable[Decimal | None]) -> Decimal | None:
    total = _ZERO
    for v in values:
        if v is None:
            return None
        total += v
    return total


def _amortised(f: FacilityOperand, months: int) -> Decimal | None:
    """Amortisation paid on f over the first ``months``, capped at its principal."""
    if f.annual_amortisation is None:
        return None
    return min(f.annual_amortisation * months / _MONTHS_PER_YEAR, f.principal)


def _base(o: Operands) -> Decimal | None:
    """Cash plus undrawn committed revolver less minimum cash, before any flow."""
    if o.cash is None or o.undrawn_revolver is None or o.minimum_cash is None:
        return None
    return o.cash + o.undrawn_revolver - o.minimum_cash


def _maturity_rows(o: Operands, ordered: Sequence[FacilityOperand]) -> tuple[MaturityRow, ...]:
    """Missingness is the same at every maturity: the base and the flow do not depend on the
    date, and one missing amortisation leaves every amortised-to sum (and its balloon) missing,
    so no maturity is ever known after an unknown one."""
    base, annual = _base(o), o.run_rate_annual
    rows: list[MaturityRow] = []
    paid_before = _ZERO  # principal paid from resources at earlier maturities
    for f in ordered:
        own = _amortised(f, f.months)
        balloon = None if own is None else f.principal - own
        amortised_to = _total(_amortised(g, min(f.months, g.months)) for g in ordered)
        resources = None
        if base is not None and annual is not None and amortised_to is not None:
            flow = annual * f.months / _MONTHS_PER_YEAR
            resources = base + flow - amortised_to - paid_before
        applied = need = None
        cover: Ratio = None
        if resources is not None and balloon is not None:
            applied = min(balloon, max(_ZERO, resources))
            need = balloon - applied
            cover = NOT_APPLICABLE if balloon == 0 else _r4(applied / balloon)
            paid_before += applied
        rows.append(MaturityRow(f, own, balloon, resources, applied, need, cover))
    return tuple(rows)


def _creditor_rows(
    ordered: Sequence[FacilityOperand], total: Decimal, ebitda: Decimal | None
) -> tuple[CreditorRow, ...]:
    ranks = {f.facility_id: r for f in ordered if (r := _rank(f)) is not None}
    if len(ranks) < len(ordered):  # one unranked facility leaves every claim missing
        return tuple(CreditorRow(f, _r4(f.principal / total), None, None) for f in ordered)
    rows = []
    for f in sorted(ordered, key=lambda f: (ranks[f.facility_id], f.months, f.facility_id)):
        own = ranks[f.facility_id]
        claims = sum((g.principal for g in ordered if ranks[g.facility_id] <= own), _ZERO)
        rows.append(CreditorRow(f, _r4(f.principal / total), claims, _ratio(claims, ebitda)))
    return tuple(rows)


def compose_refinancing(*, operands: Operands, step_up_bps: int | None) -> Refinancing:
    """The Method over the operands, pure Decimal; ``step_up_bps`` None is an unassessed step-up."""
    o = operands
    if not o.facilities:
        raise ValueError(
            "CP-3C: no facility to refinance; the lease pins no output for it (not pinned)"
        )
    if len({f.facility_id for f in o.facilities}) != len(o.facilities):
        raise ValueError("CP-3C: a facility_id repeats")
    with localcontext(_CONTEXT):
        ordered = tuple(sorted(o.facilities, key=lambda f: (f.months, f.facility_id)))
        total = sum((f.principal for f in ordered), _ZERO)
        if total <= 0:
            raise ValueError("CP-3C: total facility principal is not positive (not pinned)")
        rows = _maturity_rows(o, ordered)
        creditors = _creditor_rows(ordered, total, o.adjusted_ebitda)
        payable = _total(r.principal_payable for r in rows)
        need = _total(r.need for r in rows)
        step = None if step_up_bps is None else Decimal(step_up_bps)
        added = None if step is None or payable is None else payable * step / _BP_PER_UNIT
        pro_forma = (
            None if added is None or o.cash_interest_paid is None else o.cash_interest_paid + added
        )
        # Claims are all known or all missing (one unranked facility ranks nothing).
        claims = [c.claims_at_or_ahead for c in creditors if c.claims_at_or_ahead is not None]
        junior = max(claims) if len(claims) == len(creditors) else None
        return Refinancing(
            operands=o,
            step_up_bps=step,
            base_resources=_base(o),
            maturities=rows,
            creditors=creditors,
            total_principal=total,
            total_principal_payable=payable,
            total_applied=_total(r.applied for r in rows),
            total_need=need,
            principal_after_horizon=_total(
                r.principal_payable for r in rows if not r.facility.inside_horizon
            ),
            nearest_maturity=ordered[0].maturity_date,
            months_to_nearest=ordered[0].months,
            payable_over_ebitda=_ratio(payable, o.adjusted_ebitda),
            need_over_ebitda=_ratio(need, o.adjusted_ebitda),
            added_interest=added,
            pro_forma_interest=pro_forma,
            interest_cover=_ratio(o.adjusted_ebitda, o.cash_interest_paid),
            pro_forma_interest_cover=_ratio(o.adjusted_ebitda, pro_forma),
            junior_claims=junior,
            junior_over_ebitda=_ratio(junior, o.adjusted_ebitda),
        )


# --- operands from the bound upstream facts ---------------------------------------------------

_MILLIONS = "MILLIONS"


def _amount(
    what: str, status: Status, amount: Decimal | None, unit: str | None, want: str
) -> Decimal | None:
    if status == "missing":
        return None
    if amount is None or unit != want:
        raise ValueError(f"CP-3C {what}: expected a {want} amount")
    return amount


def _cp1_amount(name: str, fact: Cp1Fact) -> Decimal | None:
    return _amount(name, fact.status, fact.amount, fact.unit, _MILLIONS)


def _cp2d_amount(fact: Cp2dFact, want: str = _MILLIONS) -> Decimal | None:
    return _amount(fact.fact_id, fact.status, fact.amount, fact.unit, want)


def _known_text(what: str, status: Status, text: str | None) -> str:
    if status != "known" or text is None:
        raise ValueError(f"CP-3C {what}: missing, and no wording is pinned for it (not pinned)")
    return text


def _cp1_text(name: str, fact: Cp1Fact) -> str | None:
    return None if fact.status == "missing" else _known_text(name, fact.status, fact.text)


def _whole_months(fact: Cp2dFact) -> int:
    months = _cp2d_amount(fact, "months")
    if months is None or months != months.to_integral_value():
        raise ValueError(f"CP-3C {fact.fact_id}: needs a known whole number of months (not pinned)")
    return int(months)


def _facility(
    row: WallRow, terms: FacilityTerms, *, balance_date: date, horizon: int, currency: str
) -> FacilityOperand:
    fid = row.facility_id
    if terms.currency != currency:
        raise ValueError(
            f"CP-3C {fid}: a facility in currency {terms.currency} is not summed with {currency}; "
            "the lease pins no wording for that limitation (not pinned)"
        )
    principal = _cp2d_amount(row.principal)
    if principal is None:
        raise ValueError(f"CP-3C {fid}: wall principal missing (not pinned)")
    maturity = date.fromisoformat(
        _known_text(row.maturity_date.fact_id, row.maturity_date.status, row.maturity_date.text)
    )
    months = _whole_months(row.months)
    flag = _known_text(
        row.inside_horizon.fact_id, row.inside_horizon.status, row.inside_horizon.text
    )
    if flag not in ("Yes", "No"):
        raise ValueError(f"CP-3C {row.inside_horizon.fact_id}: inside-horizon flag {flag!r}")
    inside = flag == "Yes"
    position = wall_position(balance_date=balance_date, maturity=maturity, horizon_months=horizon)
    if position != (months, inside):
        raise ValueError(
            f"CP-3C {fid}: the CP-2D wall row disagrees with its own maturity and horizon"
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


def _terms_by_id(cp1: Cp1Operands, cp2d: Cp2dOperands) -> dict[str, FacilityTerms]:
    terms = {t.facility_id: t for t in cp1.facilities}
    wall = [r.facility_id for r in cp2d.wall]
    if len(terms) != len(cp1.facilities) or len(set(wall)) != len(wall) or set(wall) != set(terms):
        raise ValueError(
            "CP-3C: the CP-1 facility register and the CP-2D wall name different facilities"
        )
    return terms


def compose_operands(
    *, cp1: Cp1Operands, cp2d: Cp2dOperands, balance_date: date, currency: str
) -> Operands:
    """The Method's operands from the bound facts; a missing fact stays missing."""
    if cp1.cash_interest.period != cp1.adjusted_ebitda.period:
        raise ValueError("CP-3C: cash interest and adjusted EBITDA cover different periods")
    interest = _cp1_amount("cash_interest", cp1.cash_interest)
    terms = _terms_by_id(cp1, cp2d)
    horizon = _whole_months(cp2d.horizon)
    facilities = tuple(
        _facility(
            row,
            terms[row.facility_id],
            balance_date=balance_date,
            horizon=horizon,
            currency=currency,
        )
        for row in cp2d.wall
    )
    return Operands(
        cash=_cp1_amount("cash_closing", cp1.cash_closing),
        undrawn_revolver=_cp1_amount("undrawn_rcf", cp1.undrawn_rcf),
        run_rate_annual=_cp2d_amount(cp2d.run_rate),
        minimum_cash=_cp2d_amount(cp2d.minimum_cash),
        adjusted_ebitda=_cp1_amount("adjusted_ebitda", cp1.adjusted_ebitda),
        cash_interest_paid=None if interest is None else interest.copy_negate(),  # exact
        facilities=facilities,
    )


# --- cells and tables ---------------------------------------------------------------------------

# A gap's report-wide G<n> is bound at render time (expected.json shown_pattern "∅ G<n>").
GAP_SHOWN: Mapping[CellStatus, str] = {"missing": "∅ G#", "not_applicable": "∅ G# n.m."}

# Reasons the oracle fixes (expected.json cells); no other reason is ever written.
REASON_MINIMUM_CASH = "Not calculable: minimum cash not assessed"
REASON_STEP_UP = "Not calculable: margin step-up not assessed"
REASON_LME = "Not calculable: liability-management capacity evidence is not bound"
REASON_STRESS = "Not calculable: no stressed case is bound"
STEP_UP_NOT_ASSESSED = "Margin step-up not assessed"


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


def _gap(reason: str | None, unit: str, value_class: ValueClass = "calculated") -> _Spec:
    """A missing cell; a None reason means no reason is pinned, and the cell build refuses it."""
    return _Spec("missing", value_class, unit=unit, reason=reason)


def _value(x: Ratio, unit: str, period: str, formula: str, why: str | None = None) -> _Spec:
    """A computed value: known, missing for the pinned reason ``why``, or not applicable."""
    if x is None:
        return _gap(why, unit)
    if isinstance(x, Decimal):
        return replace(_known(x, unit, period), formula=formula)
    return _Spec("not_applicable", "calculated", unit=unit)  # the oracle pins no n.m. reason


def _copy(fact: Cp1Fact | Cp2dFact, at: str) -> _Spec:
    """A copied upstream fact: its own value, unit, period, value_class and reason."""
    if fact.value_class is None:
        raise ValueError(f"CP-3C {at}: a copied fact keeps its value_class, and none is bound")
    if fact.status == "missing":
        if fact.unit is None:
            raise ValueError(f"CP-3C {at}: a copied gap keeps its unit, and none is bound")
        return _gap(fact.reason, fact.unit, fact.value_class)
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
    if spec.status != "known" and spec.reason is None:
        raise ValueError(
            f"CP-3C {fact_id}: {spec.status} with no reason the oracle pins for it (not pinned)"
        )
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
    why_resources: str | None  # the pinned reason a resources-dependent value is missing
    why_step_up: str | None  # the pinned reason a step-up-dependent value is missing

    def label(self, facility_id: str) -> str:
        name = self.terms[facility_id].facility_name
        text = _known_text(f"{facility_id}.facility_name", name.status, name.text)
        return f"{text} ({facility_id})"

    def usd(self, x: Ratio, formula: str, why: str | None = None) -> _Spec:
        return _value(x, _MILLIONS, self.balance, formula, why)

    def usd_flow(self, x: Ratio, formula: str, why: str | None = None) -> _Spec:
        return _value(x, _MILLIONS, self.flows, formula, why)

    def percent(self, x: Ratio, formula: str, why: str | None = None) -> _Spec:
        return _value(x, "PERCENT", self.balance, formula, why)

    def multiple(self, x: Ratio, formula: str, why: str | None = None) -> _Spec:
        return _value(x, "MULTIPLE", self.flows, formula, why)


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


def _t3d1(c: _Context) -> Table:
    res = c.why_resources
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
            c.usd(m.resources, _RESOURCES_FORMULA, res),
            c.usd(m.applied, _APPLIED_FORMULA, res),
            c.usd(m.need, "principal payable at maturity - resources applied", res),
            c.percent(m.cover, "resources applied / principal payable at maturity", res),
        ]
        rows.append((c.label(m.facility.facility_id), cells))
    columns = tuple(col.format(d0=c.balance) for col in _T3D1_COLUMNS)
    title = "Refinancing need by maturity"
    return _table("T3D.1", title, "Facility", columns, rows, c.inputs.currency)


def _single(c: _Context, table_id: str, title: str, rows: Sequence[tuple[str, _Spec]]) -> Table:
    lines = [(label, [spec]) for label, spec in rows]
    return _table(table_id, title, "Line", ("Value",), lines, c.inputs.currency)


def _t3d2(c: _Context) -> Table:
    r, cp2d, res = c.refinancing, c.inputs.cp2d, c.why_resources
    months = replace(
        _known(Decimal(r.months_to_nearest), "months", c.balance),
        formula="months from the balance date to the earliest maturity",
    )
    outside = "sum of principal payable at maturity of facilities outside the CP-2D horizon"
    payable = "sum of principal payable at maturity"
    nearest = _text(r.nearest_maturity.isoformat(), "calculated", "earliest maturity date")
    rows = [
        (
            "Principal payable at maturity, all facilities",
            c.usd(r.total_principal_payable, payable),
        ),
        (
            "Resources applied at the maturity dates",
            c.usd(r.total_applied, "sum of resources applied", res),
        ),
        ("Refinancing need after resources", c.usd(r.total_need, "sum of refinancing need", res)),
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
            c.multiple(r.need_over_ebitda, "refinancing need / adjusted EBITDA", res),
        ),
        ("CP-2D funding gap at its horizon end", _from_cp2d(cp2d.funding_gap)),
        ("Minimum cash applied (analyst assumption set in CP-2D)", _from_cp2d(cp2d.minimum_cash)),
        ("CP-2D horizon (analyst judgment)", _from_cp2d(cp2d.horizon)),
    ]
    return _single(c, "T3D.2", "Refinancing burden", rows)


def _t3d3(c: _Context) -> Table:
    r, step = c.refinancing, c.why_step_up
    bps = r.step_up_bps
    step_up = (
        _gap(STEP_UP_NOT_ASSESSED, "basis_points", "analyst_judgment")
        if bps is None
        else _known(bps, "basis_points", c.inputs.as_of.isoformat(), "analyst_judgment")
    )
    paid = c.usd_flow(r.operands.cash_interest_paid, "negation of the CP-1 cash interest outflow")
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
            c.usd_flow(r.added_interest, "principal repriced x margin step-up / 10000", step),
        ),
        ("Pro forma annual cash interest", c.usd_flow(r.pro_forma_interest, pro_forma, step)),
        ("Pro forma interest cover", c.multiple(r.pro_forma_interest_cover, pro_forma_cover, step)),
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
    if status == "missing":
        return GAP_SHOWN["missing"]
    fact = Fact(fact_id="upstream", label=name, amount=amount, text=text, unit=unit, period=period)
    return fact_spelling(fact, None)[2]


def _trace(c: _Context) -> TextTable:
    """T3D.9: [name, module, table or stable id, shown] for each name read, CP-1 then CP-2D."""
    cp1, cp2d = c.inputs.cp1, c.inputs.cp2d
    order = [m.facility.facility_id for m in c.refinancing.maturities]
    named_cp1: list[tuple[str, Cp1Fact]] = [
        ("cash_closing", cp1.cash_closing),
        ("undrawn_rcf", cp1.undrawn_rcf),
        ("adjusted_ebitda", cp1.adjusted_ebitda),
        ("cash_interest", cp1.cash_interest),
    ]
    for fid in order:
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
    for fid in order:
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
                f"CP-3C claim figure {fact_id}: not a known computed figure (not pinned)"
            )
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


def _claims(c: _Context, cells: Mapping[str, Cell]) -> tuple[ClaimText, ...]:
    k = _Claims(cells)
    order = [m.facility.facility_id for m in c.refinancing.maturities]
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
        raise ValueError("CP-3C CP-3C-NEED-01: no gap form is pinned for this reason (not pinned)")
    need_names = [
        n for fid in order for n in (f"{fid}.annual_amortisation", f"cp2d.{fid}.principal")
    ]
    need_names += ["cash_closing", "undrawn_rcf", "cp2d.run_rate", "cp2d.min_cash"]
    claims = [
        k.claim(
            "CP-3C-NEED-01",
            f"Principal payable at maturity totals {k.fig('T3D.2.r01')}; {tail}",
            need_names,
        ),
        k.claim(
            "CP-3C-HORIZON-01",
            f"The liquidity analysis reports a funding gap of {k.either('T3D.2.r10')} at its "
            f"horizon end, while {k.fig('T3D.2.r04')} falls due after that horizon.",
            ["cp2d.funding_gap", "cp2d.horizon", *(f"cp2d.{fid}.inside_horizon" for fid in order)],
        ),
        k.claim(
            "CP-3C-BURDEN-01",
            f"Principal payable at maturity is {k.fig('T3D.2.r08')} of adjusted EBITDA for the "
            f"twelve months to {format_date(c.inputs.balance_date)}; the refinancing need is "
            f"{k.either('T3D.2.r09')} of the same earnings.",
            ["adjusted_ebitda"],
        ),
        _cost_claim(c, k),
        k.claim(
            "CP-3C-LME-01",
            f"Claims at or ahead of the most junior facility are {k.fig('T3D.5.r01.c1')} before "
            "any liability-management exercise; the position after such an exercise is "
            f"{k.chip('T3D.5.r01.c2')} because the legal capacity evidence is not bound.",
            [
                n
                for fid in order
                for n in (f"{fid}.secured_status", f"{fid}.seniority", f"cp2d.{fid}.principal")
            ],
        ),
    ]
    return tuple(claims)


def _cost_claim(c: _Context, k: _Claims) -> ClaimText:
    if c.inputs.submission.repricing is None:
        return k.claim(
            "CP-3C-COST-01",
            "The cost of a margin step-up on the principal payable at maturity is not calculated: "
            f"added annual cash interest is {k.chip('T3D.3.r06')} because no step-up was assessed.",
            [],
        )
    now, after = c.refinancing.interest_cover, c.refinancing.pro_forma_interest_cover
    if not (isinstance(now, Decimal) and isinstance(after, Decimal) and after < now):
        # The pinned template says the step-up "lowers" interest cover; it states nothing else.
        raise ValueError(
            "CP-3C CP-3C-COST-01: interest cover is not lowered; no wording is pinned (not pinned)"
        )
    return k.claim(
        "CP-3C-COST-01",
        "An assumed margin step-up on the principal payable at maturity adds "
        f"{k.fig('T3D.3.r06')} to annual cash interest and lowers interest cover from "
        f"{k.fig('T3D.3.r03')} to "
        f"{k.fig('T3D.3.r08')}.",
        ["cash_interest", "adjusted_ebitda"],
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
    operands = compose_operands(
        cp1=inputs.cp1, cp2d=inputs.cp2d, balance_date=inputs.balance_date, currency=inputs.currency
    )
    repricing = inputs.submission.repricing
    refinancing = compose_refinancing(
        operands=operands, step_up_bps=None if repricing is None else repricing.bps
    )
    c = _Context(
        inputs=inputs,
        refinancing=refinancing,
        terms=_terms_by_id(inputs.cp1, inputs.cp2d),
        wall={w.facility_id: w for w in inputs.cp2d.wall},
        balance=inputs.balance_date.isoformat(),
        flows=inputs.cp1.adjusted_ebitda.period,
        why_resources=REASON_MINIMUM_CASH if inputs.cp2d.minimum_cash.status == "missing" else None,
        why_step_up=REASON_STEP_UP if repricing is None else None,
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
