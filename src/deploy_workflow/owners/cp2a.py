"""CP-2A (Downside pathway): the pure Stage 1 calculation of `docs/CP2A-OWNER-LEASE.md`.

The analyst submits judgment only (`DownsideSubmission`): the base period, the scenarios and
their shock sizes, the watch levels, an assessment and gaps. Python reads the base operands
from settled CP-1 `T4.10` facts (`BaseOperands.from_cp1`), stresses them (`stress`), finds the
break points (`break_points`) and composes the nine `T2B` tables, the `cp1_references` copies,
the claims and the own limitations (`compute`). Zero, missing and not applicable stay distinct:
a missing CP-1 operand is never 0, and a ratio is calculable only where CP-1's own ratio for the
base period is known (CP-1's twelve-month gate; a quarter is never annualised).

Arithmetic: sums and products are exact (a Decimal context that traps any rounding), and every
quotient is one division in `model/_cells.CONTEXT` (38 digits, ROUND_HALF_EVEN), so each value is
the correctly rounded rational. This module does no I/O and makes no store, host or render call;
the run-time wiring (store, journal, view, probe) is added in later stages.
"""

import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Context, Decimal, Inexact, InvalidOperation, Overflow, localcontext
from fractions import Fraction
from typing import Literal

from pydantic import Field

from deploy_vii import prose
from deploy_vii.business_context import (
    Category,
    Confidence,
    Severity,
    prohibited_issues,
    referencable,
    spelled,
)
from deploy_vii.contracts import (
    Citation,
    Claim,
    Contract,
    Fact,
    ReportTable,
    TableColumn,
    TableRow,
)
from deploy_vii.model._cells import CONTEXT

MODULE_ID = "CP-2A"
STEP_ID = "downside_pathway"
SCHEMA_VERSION = "downside-pathway/1"

DECLINE_PATTERN = r"^(0|1|0\.\d{1,4}|1\.0{1,4})$"
LEVEL_PATTERN = r"^[0-9]{1,6}(\.[0-9]{1,4})?$"
Metric = Literal["total_leverage", "net_leverage", "interest_coverage"]

# Sums and products of the short CP-1 and analyst decimals are exact; a rounding would raise.
_EXACT = Context(prec=200, traps=[Inexact, InvalidOperation, Overflow])
_ZERO = Decimal(0)


# --- the model-facing contract (judgment and references only; every field required) -----------


class Scenario(Contract):
    name: str
    ebitda_decline: str = Field(pattern=DECLINE_PATTERN)
    interest_increase: str = Field(pattern=DECLINE_PATTERN)
    category: Category
    rationale: str
    limitation: str | None


class Threshold(Contract):
    metric: Metric
    level: str = Field(pattern=LEVEL_PATTERN)
    label: str
    category: Category
    rationale: str


class Assessment(Contract):
    rationale: str
    category: Category
    confidence: Confidence
    limitation: str | None


class DownsideGap(Contract):
    """As `cp2_synthesis.SynthesisGap`, without `cp1a_refs`."""

    gap: str
    why_it_matters: str
    affected_analysis: str
    severity: Severity
    action: str


class DownsideSubmission(Contract):
    base_period: str
    scenarios: tuple[Scenario, ...] = Field(min_length=1, max_length=4)
    thresholds: tuple[Threshold, ...] = Field(max_length=3)
    assessment: Assessment
    gaps: tuple[DownsideGap, ...]


# --- base operands ------------------------------------------------------------------------------

OPERAND_METRICS = ("ebitda", "cash_interest", "fcf", "total_debt", "cash_closing")
RATIOS = ("total_leverage", "net_leverage", "interest_coverage", "fcf_to_debt")
REPORTED = {
    "total_leverage": "total_leverage_reported",
    "net_leverage": "net_leverage_reported",
    "interest_coverage": "interest_coverage_reported",
    "fcf_to_debt": "fcf_to_debt",
}
CP1_TABLE = "T4.10"


GATE_QUARTER = "CP-1 has no twelve-month basis for this period"
GATE_FY_LTM = "CP-1 reports no value for this ratio for this period"
# Round 6 P1-W (final wording).
QUARTER_REASON = (
    "Not meaningful: the base period is a single quarter, and ratios need a twelve-month base"
)
QUARTER_OUTCOME = "Not meaningful on a single-quarter base"
QUARTER_NOT_COMPARED = "Not compared: CP-2A's ratio is not meaningful on a single-quarter base"
QUARTER_LINE = (
    "Ratios are not calculated on a single-quarter base: CP-1 reads each ratio from the twelve "
    "months ending that quarter, while CP-2A's base operands are one quarter's flows."
)
PeriodKind = Literal["quarter", "fy", "ltm"]


def period_kind(period: str) -> PeriodKind:
    """The kind of a CP-1 base period, from its label (`LTM Q4 25: ...`, `FY25: ...`,
    `Q3 25: ...`); an unknown label fails closed."""
    head = period.partition(": ")[0]
    if re.fullmatch(r"LTM Q[1-4] [0-9]{2}", head):
        return "ltm"
    if re.fullmatch(r"FY[0-9]{2}", head):
        return "fy"
    if re.fullmatch(r"Q[1-4] [0-9]{2}", head):
        return "quarter"
    raise ValueError(f"Unknown CP-1 base period kind: {period}")


def _column(period: str) -> str:
    """The T4.10 column label of a view period: `LTM Q4 25: a to b` -> `LTM Q4 25 (a to b)`."""
    head, sep, span = period.partition(": ")
    if not sep:
        raise ValueError(f"Not a CP-1 period string: {period}")
    return f"{head} ({span})"


@dataclass(frozen=True)
class BaseOperands:
    """The base period's operands (None where CP-1 has no known fact; never 0 for missing).

    `gates` maps a ratio to the reason it is not calculable because CP-1 has no known ratio of its
    own for the period; `sources` maps each CP-1 metric to the fact read (lineage)."""

    period: str
    ebitda: Decimal | None
    interest: Decimal | None
    fcf: Decimal | None
    total_debt: Decimal | None
    cash: Decimal | None
    gates: Mapping[str, str]
    sources: Mapping[str, Fact]
    # Owner ruling P1 / round 6 P1-W: on a quarter base, the ratios whose CP-1 fact is known are
    # not calculated (not applicable); a ratio CP-1 does not know keeps its A6 gate.
    not_meaningful: frozenset[str] = frozenset()

    @property
    def net_debt(self) -> Decimal | None:
        if self.total_debt is None or self.cash is None:
            return None
        with localcontext(_EXACT):
            return self.total_debt - self.cash

    @classmethod
    def from_cp1(cls, cp1_facts: Iterable[Fact], *, period: str) -> "BaseOperands":
        """Exactly one `T4.10` fact per metric, labelled `<column> · <metric>`, in `period`."""
        column = _column(period)
        facts = tuple(cp1_facts)
        sources: dict[str, Fact] = {}
        for metric in (*OPERAND_METRICS, *REPORTED.values()):
            label = f"{column} · {metric}"
            found = [
                f
                for f in facts
                if f.table_id == CP1_TABLE and f.label == label and f.period == period
            ]
            if len(found) != 1:
                raise ValueError(
                    f"CP-1 needs exactly one {CP1_TABLE} fact {label!r}, found {len(found)}"
                )
            sources[metric] = found[0]

        def amount(metric: str) -> Decimal | None:
            fact = sources[metric]
            return fact.amount if fact.status == "known" else None

        cash_interest = amount("cash_interest")
        # Ruling A6: a quarter base has no twelve-month basis in CP-1; an FY or LTM base whose
        # CP-1 ratio is not known reads that CP-1 reports no value for it.
        quarter = period_kind(period) == "quarter"
        gate = GATE_QUARTER if quarter else GATE_FY_LTM
        gates = {
            ratio: f"{gate} ({sources[metric].limitation})"
            for ratio, metric in REPORTED.items()
            if amount(metric) is None
        }
        not_meaningful = frozenset(r for r in REPORTED if quarter and r not in gates)
        return cls(
            period=period,
            ebitda=amount("ebitda"),
            # Ruling A7: I = -cash_interest exactly (CP-1 stores the outflow negative); a
            # positive stored value gives I < 0, which the I <= 0 rules cover.
            interest=None if cash_interest is None else -cash_interest,
            fcf=amount("fcf"),
            total_debt=amount("total_debt"),
            cash=amount("cash_closing"),
            gates=gates,
            sources=sources,
            not_meaningful=not_meaningful,
        )


WORDS = {
    "ebitda": "EBITDA",
    "interest": "cash interest",
    "fcf": "free cash flow",
    "total_debt": "total debt",
    "cash": "cash",
}


def _operand(base: BaseOperands, name: str) -> Decimal | None:
    value: Decimal | None = getattr(base, name)
    return value


def _missing(base: BaseOperands, needs: Sequence[str]) -> str | None:
    for name in needs:
        if _operand(base, name) is None:
            return f"Not calculable: base {WORDS[name]} is missing"
    return None


# --- the stress recipes ---------------------------------------------------------------------

NOT_POSITIVE_EBITDA = (
    "Not calculable: stressed EBITDA is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
)
NOT_POSITIVE_INTEREST = (
    "Not calculable: stressed cash interest is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
)
NOT_POSITIVE_DEBT = "Not calculable: debt is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
NO_STRESSED_FCF = "Not calculable: stressed free cash flow is missing"
NO_INTEREST_FOR_INCREASE = (
    "Not calculable: base cash interest is missing, so an interest increase cannot be applied"
)
STRESSED_FIELDS = (
    "ebitda",
    "interest",
    "fcf",
    "total_leverage",
    "net_leverage",
    "interest_coverage",
    "fcf_to_debt",
)


@dataclass(frozen=True)
class StressedRow:
    """One scenario's stressed flows and ratios; `why` holds the reason of every None."""

    ebitda: Decimal
    interest: Decimal | None
    fcf: Decimal | None
    total_leverage: Decimal | None
    net_leverage: Decimal | None
    interest_coverage: Decimal | None
    fcf_to_debt: Decimal | None
    why: Mapping[str, str]
    # the ratios whose None is not applicable (P1-W) rather than missing
    not_applicable: frozenset[str] = frozenset()


def stress(*, base: BaseOperands, decline: Decimal, increase: Decimal) -> StressedRow:
    """`E(1-s)`, `I(1+k)`, `F - E s - I k`, `D/E'`, `(D-C)/E'`, `E'/I'`, `F'/D`."""
    e, i, f, d, c = base.ebitda, base.interest, base.fcf, base.total_debt, base.cash
    if e is None:
        raise ValueError("Base EBITDA is missing: the submission is invalid (v02)")
    why: dict[str, str] = {}
    quarter: set[str] = set()
    with localcontext(_EXACT):
        e2 = e * (1 - decline)
        i2 = None if i is None else i * (1 + increase)
        f2: Decimal | None
        if f is None:
            f2 = None
            why["fcf"] = "Not calculable: base free cash flow is missing"
        elif increase != 0 and i is None:
            f2 = None
            why["fcf"] = NO_INTEREST_FOR_INCREASE
        else:
            f2 = f - e * decline - (_ZERO if increase == 0 or i is None else i * increase)
        net = None if d is None or c is None else d - c
    if i2 is None:
        why["interest"] = "Not calculable: base cash interest is missing"

    def ratio(
        name: str, num: Decimal | None, den: Decimal | None, needs: Sequence[str], zero: str
    ) -> Decimal | None:
        reason = _missing(base, needs) or (
            f"Not calculable: {base.gates[name]}" if name in base.gates else None
        )
        if reason is None and name in base.not_meaningful:
            quarter.add(name)
            reason = QUARTER_REASON
        if reason is None and (num is None or den is None):
            raise ValueError(f"{name}: an operand is missing without a reason")
        if reason is None and den is not None and den <= 0:
            reason = zero
        if reason is not None:
            why[name] = reason
            return None
        assert num is not None and den is not None
        return CONTEXT.divide(num, den)

    total = ratio("total_leverage", d, e2, ("total_debt",), NOT_POSITIVE_EBITDA)
    net_lev = ratio("net_leverage", net, e2, ("total_debt", "cash"), NOT_POSITIVE_EBITDA)
    cover = ratio("interest_coverage", e2, i2, ("interest",), NOT_POSITIVE_INTEREST)
    if f2 is None:
        why["fcf_to_debt"] = NO_STRESSED_FCF
        to_debt = None
    else:
        to_debt = ratio("fcf_to_debt", f2, d, ("total_debt",), NOT_POSITIVE_DEBT)
    return StressedRow(
        ebitda=e2,
        interest=i2,
        fcf=f2,
        total_leverage=total,
        net_leverage=net_lev,
        interest_coverage=cover,
        fcf_to_debt=to_debt,
        why=why,
        not_applicable=frozenset(quarter),
    )


# --- break points ---------------------------------------------------------------------------

REACHED = "Reached at the stated decline"
AT_BASE = "Already reached at base"
NOT_REACHED = "Not reached by a decline of up to 100%"
NOT_CALCULABLE = "Not calculable"
NET_DEBT_NOT_POSITIVE = "Net debt is not positive, so no EBITDA decline raises net leverage"
TOTAL_DEBT_NOT_POSITIVE = "Total debt is not positive, so no EBITDA decline raises total leverage"
INTEREST_NOT_POSITIVE = (
    "Not calculable: base cash interest is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
)
DENOMINATOR = "Not calculable: the denominator is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
BreakKind = Literal["fcf", "coverage", "total_leverage", "net_leverage"]


@dataclass(frozen=True)
class ThresholdSpec:
    """One analyst watch level, parsed."""

    metric: Metric
    level: Decimal
    label: str


@dataclass(frozen=True)
class BreakPoint:
    """The EBITDA decline `s*` at which a test is reached, with cash interest held at base.

    `required_exact` is the exact rational `s*`; `required_decline` its 38-digit rounding."""

    break_id: str
    origin: Literal["Definition", "Analyst assumption"]
    test: str
    kind: BreakKind
    level: Decimal
    outcome: str
    required_exact: Fraction | None
    required_decline: Decimal | None
    ebitda_at_break: Decimal | None
    reason: str | None

    @property
    def ranked(self) -> bool:
        return self.required_decline is not None and self.outcome != NOT_REACHED


_GATE: Mapping[BreakKind, str | None] = {
    "fcf": None,
    "coverage": "interest_coverage",
    "total_leverage": "total_leverage",
    "net_leverage": "net_leverage",
}


_Head = tuple[str, Literal["Definition", "Analyst assumption"], str, BreakKind, Decimal]


def _short_circuit(base: BaseOperands, kind: BreakKind) -> tuple[str, str] | None:
    """Ruling A1: (outcome, reason) of a break no EBITDA decline can reach or measure."""
    d, i, nd = base.total_debt, base.interest, base.net_debt
    if kind == "total_leverage" and d is not None and d <= 0:
        return NOT_REACHED, TOTAL_DEBT_NOT_POSITIVE
    if kind == "net_leverage" and nd is not None and nd <= 0:
        return NOT_REACHED, NET_DEBT_NOT_POSITIVE
    if kind == "coverage" and i is not None and i <= 0:
        return NOT_CALCULABLE, INTEREST_NOT_POSITIVE
    return None


def _break(
    base: BaseOperands,
    head: _Head,
    needs: Sequence[str],
    terms: tuple[Decimal, Decimal, Decimal] | None,
) -> BreakPoint:
    """`terms` = (numerator, denominator, EBITDA at the break) when every operand is present.

    Ruling A8, order of checks: missing operands in formula order, then the CP-1 gate, then the
    short-circuits, then s*."""
    break_id, origin, test, kind, level = head

    def unsettled(outcome: str, reason: str) -> BreakPoint:
        return BreakPoint(break_id, origin, test, kind, level, outcome, None, None, None, reason)

    gate = _GATE[kind]
    reason = _missing(base, needs) or (
        f"Not calculable: {base.gates[gate]}" if gate is not None and gate in base.gates else None
    )
    if reason is not None:
        return unsettled(NOT_CALCULABLE, reason)
    if gate is not None and gate in base.not_meaningful:
        return unsettled(QUARTER_OUTCOME, QUARTER_REASON)
    if (short := _short_circuit(base, kind)) is not None:
        return unsettled(*short)
    if terms is None:
        raise ValueError(f"{break_id}: an operand is missing without a reason")
    num, den, at_break = terms
    if den <= 0:
        return unsettled(NOT_CALCULABLE, DENOMINATOR)
    exact = Fraction(num) / Fraction(den)
    outcome = AT_BASE if exact <= 0 else NOT_REACHED if exact > 1 else REACHED
    return BreakPoint(
        break_id,
        origin,
        test,
        kind,
        level,
        outcome,
        exact,
        CONTEXT.divide(num, den),
        at_break,
        None,
    )


THRESHOLD_KIND: Mapping[Metric, BreakKind] = {
    "total_leverage": "total_leverage",
    "net_leverage": "net_leverage",
    "interest_coverage": "coverage",
}


def break_points(
    *, base: BaseOperands, thresholds: Sequence[ThresholdSpec]
) -> tuple[BreakPoint, ...]:
    """b01 free cash flow at zero, b02 EBITDA equal to cash interest, b03.. the watch levels."""
    e, i, f, d = base.ebitda, base.interest, base.fcf, base.total_debt
    nd = base.net_debt
    if e is None:
        raise ValueError("Base EBITDA is missing: the submission is invalid (v02)")
    out: list[BreakPoint] = []
    with localcontext(_EXACT):
        fcf_terms = None if f is None else (f, e, e - f)
        out.append(
            _break(
                base,
                ("b01", "Definition", "Free cash flow at or below zero", "fcf", _ZERO),
                ("fcf",),
                fcf_terms,
            )
        )
        one = Decimal(1)
        floor = None if i is None or i <= 0 else (e - one * i, e, i)
        out.append(
            _break(
                base,
                ("b02", "Definition", "EBITDA no longer covers cash interest", "coverage", one),
                ("interest",),
                floor,
            )
        )
        for n, t in enumerate(thresholds, 3):
            head: _Head = (
                f"b{n:02d}",
                "Analyst assumption",
                t.label,
                THRESHOLD_KIND[t.metric],
                t.level,
            )
            lvl = t.level
            if t.metric == "total_leverage":
                terms = (
                    None if d is None or d <= 0 else (lvl * e - d, lvl * e, CONTEXT.divide(d, lvl))
                )
                out.append(_break(base, head, ("total_debt",), terms))
            elif t.metric == "net_leverage":
                net = (
                    None
                    if nd is None or nd <= 0
                    else (lvl * e - nd, lvl * e, CONTEXT.divide(nd, lvl))
                )
                out.append(_break(base, head, ("total_debt", "cash"), net))
            else:
                terms = None if i is None or i <= 0 else (e - lvl * i, e, lvl * i)
                out.append(_break(base, head, ("interest",), terms))
    return tuple(out)


def rank(points: Sequence[BreakPoint]) -> tuple[BreakPoint, ...]:
    """Reached breaks ascending by `s*`, ties in register order."""
    ranked = [(p.required_exact, n, p) for n, p in enumerate(points) if p.ranked]
    return tuple(p for _, _, p in sorted(ranked, key=lambda x: (x[0], x[1])))


_KIND_FIELD: Mapping[BreakKind, str] = {
    "fcf": "fcf",
    "coverage": "interest_coverage",
    "total_leverage": "total_leverage",
    "net_leverage": "net_leverage",
}


def crossing(point: BreakPoint, row: StressedRow) -> tuple[Decimal | None, str]:
    """A scenario's stressed metric against a break level: at or beyond it is Crossed (at or
    below for free cash flow and coverage, at or above for leverage)."""
    field = _KIND_FIELD[point.kind]
    value: Decimal | None = getattr(row, field)
    if value is None:
        return None, QUARTER_OUTCOME if field in row.not_applicable else NOT_CALCULABLE
    floor = point.kind in ("fcf", "coverage")
    beyond = value <= point.level if floor else value >= point.level
    return value, "Crossed" if beyond else "Not crossed"


# --- validation (calculation-level refusals) -----------------------------------------------

NAME_RULE = "no digit, brace or bracket is allowed in a name"
# Round 5 Names (pinned wordings).
CONTROL_RULE = "contains a line break or control character"
BASE_ROW = "Base (no stress)"
RESERVED_BASE = f"{BASE_ROW} is reserved for the unstressed row"
HIGH_ISSUE = (
    "assessment.confidence: High is not allowed: "
    "shock sizes and watch levels are uncited analyst assumptions"
)


@dataclass(frozen=True)
class Inputs:
    """Everything the calculation reads. `cp1_facts`: the bound CP-1 head's T4.10 facts the
    view offers; `offered_periods`: the view's base periods; `names`: the issuer name (digits in
    it are not figures)."""

    submission: DownsideSubmission
    cp1_facts: tuple[Fact, ...]
    offered_periods: tuple[str, ...]
    names: tuple[str, ...]


def _bad_name(text: str) -> bool:
    return any(ch.isdigit() or ch in "{}[]" for ch in text)


def _prose_issues(
    path: str, text: str, bound: Mapping[str, Fact], names: Sequence[str]
) -> list[str]:
    if not text.strip():
        return [f"{path}: empty text"]
    return [
        *(f"{path}: {issue}" for issue in prose.issues(text, bound, names=names)),
        *prohibited_issues(path, text),
    ]


def _name_issues(path: str, text: str) -> list[str]:
    """A scenario name or threshold label: not empty (M4), no digit, brace or bracket, and no
    prohibited conclusion (ruling A3)."""
    if not text.strip():
        return [f"{path}: empty text"]
    issues = []
    if any(unicodedata.category(ch) in ("Cc", "Zl", "Zp") for ch in text):
        issues.append(f"{path}: {CONTROL_RULE}")
    if _bad_name(text):
        issues.append(f"{path}: {NAME_RULE}")
    return [*issues, *prohibited_issues(path, text)]


def _scenario_issues(inputs: Inputs, bound: Mapping[str, Fact]) -> list[str]:
    issues: list[str] = []
    seen: set[str] = set()
    for n, sc in enumerate(inputs.submission.scenarios):
        path = f"scenarios[{n}]"
        issues += _name_issues(f"{path}.name", sc.name)
        if sc.name.strip() == BASE_ROW:
            issues.append(f"{path}.name: {RESERVED_BASE}")
        if sc.name.strip() and sc.name in seen:
            issues.append(f"{path}.name: duplicate scenario name: {sc.name}")
        seen.add(sc.name)
        issues += _prose_issues(f"{path}.rationale", sc.rationale, bound, inputs.names)
        if sc.limitation is not None:
            issues += _prose_issues(f"{path}.limitation", sc.limitation, bound, inputs.names)
    return issues


def _threshold_issues(inputs: Inputs, bound: Mapping[str, Fact]) -> list[str]:
    issues: list[str] = []
    seen: set[str] = set()
    for n, t in enumerate(inputs.submission.thresholds):
        path = f"thresholds[{n}]"
        if t.metric in seen:
            issues.append(f"{path}.metric: more than one threshold for {t.metric}")
        seen.add(t.metric)
        if Decimal(t.level) <= 0:
            issues.append(f"{path}.level: must be greater than zero")
        issues += _name_issues(f"{path}.label", t.label)
        issues += _prose_issues(f"{path}.rationale", t.rationale, bound, inputs.names)
    labels = [t.label for t in inputs.submission.thresholds]
    issues += [
        f"thresholds: {label} appears more than once"
        for label in dict.fromkeys(labels)
        if label.strip() and labels.count(label) > 1
    ]
    return issues


def validate(inputs: Inputs) -> tuple[str, ...]:
    """Every content issue of the submission, in the order base_period, scenarios, thresholds,
    assessment, gaps; empty when it composes. Shape issues are the schema's (Pydantic).

    Ruling A5: a base_period issue ends validation and is returned alone."""
    sub = inputs.submission
    if sub.base_period not in inputs.offered_periods:
        return (f"base_period: not an offered period: {sub.base_period}",)
    base = BaseOperands.from_cp1(inputs.cp1_facts, period=sub.base_period)
    if base.ebitda is None or base.ebitda <= 0:
        return (f"base_period: base EBITDA is missing or not positive for {sub.base_period}",)
    issues: list[str] = []
    bound = prose.bind(referencable(inputs.cp1_facts))
    issues += _scenario_issues(inputs, bound)
    issues += _threshold_issues(inputs, bound)
    a = sub.assessment
    issues += _prose_issues("assessment.rationale", a.rationale, bound, inputs.names)
    if a.confidence == "High":
        issues.append(HIGH_ISSUE)
    if a.limitation is not None:
        issues += _prose_issues("assessment.limitation", a.limitation, bound, inputs.names)
    for n, gap in enumerate(sub.gaps):
        for name in ("gap", "why_it_matters", "affected_analysis", "action"):
            path = f"gaps[{n}].{name}"
            issues += _prose_issues(path, getattr(gap, name), bound, inputs.names)
    return tuple(dict.fromkeys(issues))


# --- composition ------------------------------------------------------------------------------

TABLES = {
    "T2B.1": "Scenario register",
    "T2B.2": "Base operands",
    "T2B.3": "Stressed earnings and cash flow",
    "T2B.4": "Stressed credit metrics",
    "T2B.5": "Base reconciliation to CP-1",
    "T2B.6": "Break-point register",
    "T2B.7": "First-break ranking",
    "T2B.8": "Scenario against break points",
    "T2B.9": "Gaps ledger",
}
CP1_REFERENCES = "cp1_references"
# T2B.7 is the one table that can be empty (no break ranks), so its columns are fixed.
FIXED_COLUMNS: Mapping[str, tuple[TableColumn, ...]] = {
    "T2B.7": (
        TableColumn(field="break_point", label="Break point"),
        TableColumn(field="required_decline", label="Required EBITDA decline"),
    ),
}
UnitClass = Literal["amount", "multiple", "percent"]
_UNITS: Mapping[UnitClass, str] = {
    "amount": "MILLIONS",
    "multiple": "MULTIPLE",
    "percent": "PERCENT",
}

OPERANDS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("ebitda", "EBITDA", "ebitda", ("ebitda",)),
    ("interest", "Cash interest paid (outflow)", "cash_interest", ("cash_interest",)),
    ("fcf", "Free cash flow", "fcf", ("fcf",)),
    ("total_debt", "Total debt", "total_debt", ("total_debt",)),
    ("cash", "Cash and cash equivalents", "cash_closing", ("cash_closing",)),
    ("net_debt", "Net debt", "total_debt - cash_closing", ("total_debt", "cash_closing")),
)
RATIO_ROWS: tuple[tuple[str, str, UnitClass, str], ...] = (
    ("total_leverage", "Total leverage", "multiple", "Total debt / stressed EBITDA"),
    ("net_leverage", "Net leverage", "multiple", "(Total debt - cash) / stressed EBITDA"),
    (
        "interest_coverage",
        "Interest coverage",
        "multiple",
        "Stressed EBITDA / stressed cash interest",
    ),
    ("fcf_to_debt", "Free cash flow to debt", "percent", "Stressed free cash flow / total debt"),
)
_RATIO_LINEAGE = {
    "total_leverage": ("total_debt", "ebitda"),
    "net_leverage": ("total_debt", "cash_closing", "ebitda"),
    "interest_coverage": ("ebitda", "cash_interest"),
}
BREAK_DECLINE: Mapping[BreakKind, tuple[str, ...]] = {
    "fcf": ("fcf", "ebitda"),
    "coverage": ("ebitda", "cash_interest"),
    "total_leverage": ("total_debt", "ebitda"),
    "net_leverage": ("total_debt", "cash_closing", "ebitda"),
}
BREAK_AT: Mapping[BreakKind, tuple[str, ...]] = {
    "fcf": ("ebitda", "fcf"),
    "coverage": ("cash_interest",),
    "total_leverage": ("total_debt",),
    "net_leverage": ("total_debt", "cash_closing"),
}
DECLINE_FORMULA: Mapping[BreakKind, str] = {
    "fcf": "Free cash flow / EBITDA",
    "coverage": "(EBITDA - level x cash interest) / EBITDA",
    "total_leverage": "(level x EBITDA - total debt) / (level x EBITDA)",
    "net_leverage": "(level x EBITDA - net debt) / (level x EBITDA)",
}

ANALYST_SHOCKS = "Scenario shock sizes are analyst assumptions without a source citation."
WATCH_LEVELS = "Break-point watch levels are analyst assumptions, not covenants; no covenant owner is an input."
STATIC = (
    "Stress is applied to the base period's flows with debt and cash held at their reported "
    "closing balances; no forward cash build, refinancing or mitigating action is modelled."
)
HELD = (
    "Cash taxes, capital expenditure and working capital are held at the base period; "
    "no tax shield is taken."
)
LIQUIDITY = (
    "Liquidity is not tested: stressed free cash flow is not set against the cash balance or any "
    "undrawn facility and no liquidity runway is computed; the liquidity runway belongs to CP-2D."
)
COVENANT = (
    "No covenant test is applied: the watch levels are not covenant tests; "
    "covenant compliance belongs to CP-4."
)
MATURITY = (
    "No maturity or refinancing wall is stressed: debt maturities and refinancing risk belong "
    "to CP-2D and CP-3C."
)
BREAK_AT_BASE = (
    "Break points hold cash interest at the base period level (no interest increase). The break "
    "at which EBITDA no longer covers cash interest compares same-period flows but is gated like "
    "a ratio: it is Not calculable wherever CP-1 has no twelve-month basis for the base period."
)
NOT_CALC_CROSSING = (
    "A metric that is not calculable under a scenario shows Not calculable against every break "
    "point, including a break whose required decline is below that scenario's decline."
)
NO_FIRST_BREAK = "No break point is calculable, so no first break is ranked."
NO_GAPS = "None in the CP-2A submission (gaps ledger)"
GAP_FIELDS = ("id", "gap", "why_it_matters", "affected_analysis", "severity", "action")


def lineage(base: BaseOperands, metrics: Sequence[str]) -> tuple[Citation, ...]:
    """The ordered, de-duplicated citations of the CP-1 facts a calculated fact derives from;
    a known fact never derives from a CP-1 fact that is not known (fail closed)."""
    cited: list[Citation] = []
    for metric in metrics:
        source = base.sources.get(metric)
        if source is None or source.status != "known":
            raise ValueError(f"CP-2A fact would derive from CP-1 {metric}, which is not known")
        cited.extend(source.citations)
    return tuple(dict.fromkeys(cited))


def _fcf_lineage(increase: Decimal) -> tuple[str, ...]:
    return ("fcf", "ebitda", "cash_interest") if increase != 0 else ("fcf", "ebitda")


def _ratio_lineage(ratio: str, increase: Decimal) -> tuple[str, ...]:
    if ratio == "fcf_to_debt":
        return (*_fcf_lineage(increase), "total_debt")
    return _RATIO_LINEAGE[ratio]


@dataclass(frozen=True)
class Result:
    """The composed module content: facts and tables (T2B.1-T2B.9, then cp1_references), claims
    and own limitations, with the intermediate stressed rows, break register and ranking."""

    base: BaseOperands
    facts: tuple[Fact, ...]
    tables: tuple[ReportTable, ...]
    claims: tuple[Claim, ...]
    limitations: tuple[str, ...]
    stressed: Mapping[str, StressedRow]
    breaks: tuple[BreakPoint, ...]
    ranking: tuple[BreakPoint, ...]
    crossings: Mapping[str, Mapping[str, str]]


class _Composer:
    def __init__(self, base: BaseOperands) -> None:
        self.base = base
        self.facts: list[Fact] = []
        self.rows: dict[str, list[TableRow]] = {t: [] for t in TABLES}

    def text(self, table: str, row: str, field: str, label: str, value: str, judged: bool) -> None:
        self.facts.append(
            Fact(
                fact_id=f"{table}.{row}.{field}",
                label=label,
                table_id=table,
                row_id=row,
                field=field,
                text=value,
                value_class="analyst_judgment" if judged else None,
            )
        )

    def number(
        self,
        coordinate: tuple[str, str, str, str],
        value: Decimal,
        unit_class: UnitClass,
        formula: str,
        value_class: Literal["calculated", "analyst_judgment"] | None,
        derives: Sequence[str] = (),
    ) -> None:
        table, row, field, label = coordinate
        fact_id = f"{table}.{row}.{field}"
        amount = unit_class == "amount"
        calculated = value_class == "calculated"
        self.facts.append(
            Fact(
                fact_id=fact_id,
                label=label,
                table_id=table,
                row_id=row,
                field=field,
                amount=value,
                unit=_UNITS[unit_class],
                currency="USD" if amount else None,
                scale=Decimal(1000000) if amount else Decimal(1),
                decimals=2 if amount else None,
                period=self.base.period,
                citations=lineage(self.base, derives) if calculated else (),
                calculation_id=f"calc:{fact_id}" if calculated else None,
                value_class=value_class,
                formula=formula,
            )
        )

    def calc(
        self,
        coordinate: tuple[str, str, str, str],
        value: Decimal,
        unit_class: UnitClass,
        formula: str,
        derives: Sequence[str],
    ) -> None:
        self.number(coordinate, value, unit_class, formula, "calculated", derives)

    def gap(
        self,
        coordinate: tuple[str, str, str, str],
        unit_class: UnitClass,
        reason: str,
        status: Literal["missing", "not_applicable"] = "missing",
    ) -> None:
        table, row, field, label = coordinate
        self.facts.append(
            Fact(
                fact_id=f"{table}.{row}.{field}",
                label=label,
                table_id=table,
                row_id=row,
                field=field,
                status=status,
                unit=_UNITS[unit_class],
                period=self.base.period,
                limitation=reason,
            )
        )

    def register(self, table: str, row: str, label: str, fields: Sequence[str]) -> None:
        ids = tuple(f"{table}.{row}.{f}" for f in fields)
        self.rows[table].append(TableRow(row_id=row, label=label, fact_ids=ids))

    def known(self, fact_id: str) -> bool:
        return next(f for f in self.facts if f.fact_id == fact_id).status == "known"

    def ref(self, fact_id: str, token: str) -> str:
        return f"{{{fact_id}|{token}}}" if self.known(fact_id) else f"[{fact_id}]"

    def tables(self) -> list[ReportTable]:
        labels = {f.fact_id: (f.field, f.label) for f in self.facts}
        out = []
        for table, title in TABLES.items():
            rows = self.rows[table]
            if table in FIXED_COLUMNS:
                columns = FIXED_COLUMNS[table]
            elif rows:
                columns = tuple(
                    TableColumn(field=labels[fid][0], label=labels[fid][1])
                    for fid in rows[0].fact_ids
                )
            else:
                raise ValueError(f"{table} has no row to take its columns from")
            out.append(ReportTable(table_id=table, title=title, columns=columns, rows=tuple(rows)))
        return out


def _figure_refs(text: str, bound: Mapping[str, Fact]) -> list[Fact]:
    """The CP-1 facts a valid run text names by figure reference, in reading order."""
    return [
        bound[run.text]
        for run in prose.tokenize(text)
        if run.kind == "ref" and run.figure and run.text in bound
    ]


@dataclass(frozen=True)
class _Run:
    row: str
    name: str
    decline: Decimal
    increase: Decimal


def _scenarios(out: _Composer, sub: DownsideSubmission, bound: Mapping[str, Fact]) -> None:
    for n, sc in enumerate(sub.scenarios, 1):
        r = f"s{n:02d}"
        named = dict.fromkeys(f.label for f in _figure_refs(sc.rationale, bound))
        out.text("T2B.1", r, "name", "Scenario", sc.name, judged=True)
        decline = ("T2B.1", r, "ebitda_decline", "EBITDA decline")
        out.number(
            decline, Decimal(sc.ebitda_decline), "percent", "analyst input", "analyst_judgment"
        )
        increase = ("T2B.1", r, "interest_increase", "Cash interest increase")
        out.number(
            increase, Decimal(sc.interest_increase), "percent", "analyst input", "analyst_judgment"
        )
        out.text("T2B.1", r, "category", "Category", sc.category, judged=False)
        basis = "; ".join(f"CP-1 {label}" for label in named) or "No located evidence"
        out.text("T2B.1", r, "basis", "Basis", basis, judged=False)
        out.register(
            "T2B.1",
            r,
            sc.name,
            ("name", "ebitda_decline", "interest_increase", "category", "basis"),
        )


def _operands(out: _Composer) -> None:
    base = out.base
    for key, label, source, derives in OPERANDS:
        value = base.net_debt if key == "net_debt" else _operand(base, key)
        coordinate = ("T2B.2", key, "value", label)
        if value is None:
            reason = (
                "Not calculable: debt or cash is missing"
                if key == "net_debt"
                else f"Not calculable: base {WORDS[key]} is missing in CP-1 ({base.period})"
            )
            out.gap(coordinate, "amount", reason)
        else:
            formula = f"CP-1 {source}" + (", sign reversed" if key == "interest" else "")
            out.calc(coordinate, value, "amount", formula, derives)
        out.text("T2B.2", key, "source", "Source", f"CP-1 T4.10 {source} · {base.period}", False)
        out.register("T2B.2", key, label, ("value", "source"))


_FLOWS: tuple[tuple[str, str, str], ...] = (
    ("ebitda", "Stressed EBITDA", "EBITDA x (1 - decline)"),
    ("interest", "Stressed cash interest", "Cash interest x (1 + increase)"),
    (
        "fcf",
        "Stressed free cash flow",
        "Free cash flow - EBITDA x decline - cash interest x increase",
    ),
)


def _stress_rows(out: _Composer, run: _Run, row: StressedRow) -> None:
    base, r, k = out.base, run.row, run.increase
    lineage_of = {"ebitda": ("ebitda",), "interest": ("cash_interest",), "fcf": _fcf_lineage(k)}
    for key, label, formula in _FLOWS:
        value: Decimal | None = getattr(row, key)
        coordinate = ("T2B.3", r, key, label)
        if value is None:
            out.gap(coordinate, "amount", row.why[key])
        else:
            out.calc(coordinate, value, "amount", formula, lineage_of[key])
    changes = (
        ("ebitda_change", "EBITDA change", row.ebitda, base.ebitda, ("ebitda",)),
        ("fcf_change", "Free cash flow change", row.fcf, base.fcf, _fcf_lineage(k)),
    )
    for field, label, stressed, at_base, derives in changes:
        coordinate = ("T2B.3", r, field, label)
        if stressed is None or at_base is None:
            out.gap(
                coordinate, "amount", "Not calculable: the stressed or the base figure is missing"
            )
        else:
            with localcontext(_EXACT):
                change = stressed - at_base
            out.calc(coordinate, change, "amount", "Stressed minus base", derives)
    out.register("T2B.3", r, run.name, ("ebitda", "interest", "fcf", "ebitda_change", "fcf_change"))
    for ratio, label, unit_class, formula in RATIO_ROWS:
        value = getattr(row, ratio)
        coordinate = ("T2B.4", r, ratio, label)
        if value is None:
            out.gap(coordinate, unit_class, row.why[ratio], _status(row, ratio))
        else:
            out.calc(coordinate, value, unit_class, formula, _ratio_lineage(ratio, k))
    out.register("T2B.4", r, run.name, RATIOS)


def _status(row: StressedRow, name: str) -> Literal["missing", "not_applicable"]:
    """A None ratio is not applicable under P1-W, otherwise missing."""
    return "not_applicable" if name in row.not_applicable else "missing"


def _reconciliation(out: _Composer, control: StressedRow) -> None:
    base = out.base
    for ratio, label, unit_class, _ in RATIO_ROWS:
        recomputed: Decimal | None = getattr(control, ratio)
        reported = base.sources[REPORTED[ratio]]
        what = ("T2B.5", ratio, "recomputed", "Recomputed from CP-2A base operands")
        difference = ("T2B.5", ratio, "difference", "Difference")
        if recomputed is None or reported.status != "known" or reported.amount is None:
            reason = control.why.get(ratio)
            if reason is None:
                raise ValueError(f"{ratio}: recomputed but CP-1 reports no ratio (gate breached)")
            status = _status(control, ratio)
            out.gap(what, unit_class, reason, status)
            not_compared = (
                QUARTER_NOT_COMPARED
                if status == "not_applicable"
                else "Not compared: one side is not calculable"
            )
            out.gap(difference, unit_class, not_compared, status)
            out.text("T2B.5", ratio, "result", "Result", "Not compared", False)
        else:
            derives = _ratio_lineage(ratio, _ZERO)
            out.calc(what, recomputed, unit_class, "Base operands, no stress", derives)
            with localcontext(_EXACT):
                diff = recomputed - reported.amount
            formula = f"Recomputed minus CP-1 reported (cp1_references {REPORTED[ratio]})"
            out.calc(difference, diff, unit_class, formula, (*derives, REPORTED[ratio]))
            result = "Reconciled" if diff == 0 else "Differs"
            out.text("T2B.5", ratio, "result", "Result", result, False)
        out.register("T2B.5", ratio, label, ("recomputed", "difference", "result"))


def _level(
    out: _Composer, coordinate: tuple[str, str, str, str], p: BreakPoint, copy: bool
) -> None:
    """A break level: the two definitions carry no value class and no calculation; an analyst
    watch level is analyst judgment. A T2B.8 copy keeps the T2B.6 level's own class."""
    unit_class: UnitClass = "amount" if p.kind == "fcf" else "multiple"
    if p.origin == "Analyst assumption":
        formula = "From T2B.6" if copy else "analyst input"
        out.number(coordinate, p.level, unit_class, formula, "analyst_judgment")
        return
    definition = (
        "Definition: free cash flow of zero"
        if p.kind == "fcf"
        else "Definition: EBITDA equal to cash interest"
    )
    out.number(coordinate, p.level, unit_class, "From T2B.6" if copy else definition, None)


def _breaks(out: _Composer, points: Sequence[BreakPoint]) -> None:
    for p in points:
        r = p.break_id
        out.text("T2B.6", r, "origin", "Origin", p.origin, p.origin == "Analyst assumption")
        out.text("T2B.6", r, "test", "Test", p.test, False)
        _level(out, ("T2B.6", r, "level", "Level"), p, copy=False)
        decline = ("T2B.6", r, "required_decline", "Required EBITDA decline")
        at_break = ("T2B.6", r, "ebitda_at_break", "EBITDA at the break")
        if p.ranked:
            assert p.required_decline is not None and p.ebitda_at_break is not None
            formula = DECLINE_FORMULA[p.kind]
            out.calc(decline, p.required_decline, "percent", formula, BREAK_DECLINE[p.kind])
            at_formula = "EBITDA x (1 - required decline)"
            out.calc(at_break, p.ebitda_at_break, "amount", at_formula, BREAK_AT[p.kind])
        elif p.outcome in (NOT_REACHED, QUARTER_OUTCOME):
            why = p.reason or "No decline up to 100% reaches the level"
            out.gap(decline, "percent", why, status="not_applicable")
            out.gap(at_break, "amount", why, status="not_applicable")
        else:
            reason = p.reason or NOT_CALCULABLE
            out.gap(decline, "percent", reason)
            out.gap(at_break, "amount", reason)
        out.text("T2B.6", r, "outcome", "Outcome", p.outcome, False)
        fields = ("origin", "test", "level", "required_decline", "ebitda_at_break", "outcome")
        out.register("T2B.6", r, p.test, fields)


def _ranking(out: _Composer, ranked: Sequence[BreakPoint]) -> None:
    for n, p in enumerate(ranked, 1):
        r = f"r{n:02d}"
        assert p.required_decline is not None
        out.text("T2B.7", r, "break_point", FIXED_COLUMNS["T2B.7"][0].label, p.test, False)
        coordinate = ("T2B.7", r, "required_decline", FIXED_COLUMNS["T2B.7"][1].label)
        formula = f"= T2B.6.{p.break_id}.required_decline"
        out.calc(coordinate, p.required_decline, "percent", formula, BREAK_DECLINE[p.kind])
        out.register("T2B.7", r, f"Rank {n}", ("break_point", "required_decline"))


def _crossings(
    out: _Composer,
    runs: Sequence[_Run],
    stressed: Mapping[str, StressedRow],
    points: Sequence[BreakPoint],
) -> tuple[dict[str, dict[str, str]], bool]:
    """T2B.8; also whether a metric is not calculable against a break that has an `s*`."""
    crossings: dict[str, dict[str, str]] = {p.break_id: {} for p in points}
    unreached = False
    for run in runs:
        row = stressed[run.row]
        for p in points:
            r = f"{run.row}-{p.break_id}"
            value, result = crossing(p, row)
            unit_class: UnitClass = "amount" if p.kind == "fcf" else "multiple"
            coordinate = ("T2B.8", r, "stressed_value", "Stressed value")
            if value is None:
                field = _KIND_FIELD[p.kind]
                reason = row.why.get(field, NOT_CALCULABLE)
                out.gap(coordinate, unit_class, reason, _status(row, field))
                unreached = unreached or p.required_exact is not None
            else:
                derives = (
                    _fcf_lineage(run.increase)
                    if p.kind == "fcf"
                    else _ratio_lineage(_KIND_FIELD[p.kind], run.increase)
                )
                out.calc(coordinate, value, unit_class, "From T2B.3 or T2B.4", derives)
            _level(out, ("T2B.8", r, "level", "Level"), p, copy=True)
            out.text("T2B.8", r, "result", "Result", result, False)
            crossings[p.break_id][run.row] = result
            out.register(
                "T2B.8", r, f"{run.name} · {p.test}", ("stressed_value", "level", "result")
            )
    return crossings, unreached


def _gaps(
    out: _Composer, sub: DownsideSubmission, limits: list[str], bound: Mapping[str, Fact]
) -> None:
    for n, g in enumerate(sub.gaps, 1):
        r = f"g{n:02d}"
        out.text("T2B.9", r, "id", "Gap id", f"CP-2A-GAP-{n:03d}", False)
        gap = _spelled(g.gap, bound)
        out.text("T2B.9", r, "gap", "Gap", gap, True)
        why = _spelled(g.why_it_matters, bound)
        out.text("T2B.9", r, "why_it_matters", "Why it matters", why, True)
        affected = _spelled(g.affected_analysis, bound)
        out.text("T2B.9", r, "affected_analysis", "Affected analysis", affected, True)
        out.text("T2B.9", r, "severity", "Severity", g.severity, False)
        out.text("T2B.9", r, "action", "Action", _spelled(g.action, bound), True)
        out.register("T2B.9", r, f"Gap {n}", GAP_FIELDS)
        limits.append(f"Gap ({g.severity}): {gap}")
    if not sub.gaps:
        for field in GAP_FIELDS:
            out.facts.append(
                Fact(
                    fact_id=f"T2B.9.none.{field}",
                    label=field,
                    table_id="T2B.9",
                    row_id="none",
                    field=field,
                    status="not_applicable",
                    limitation=NO_GAPS,
                )
            )
        out.register("T2B.9", "none", "None", GAP_FIELDS)


def _references(
    sub: DownsideSubmission, bound: Mapping[str, Fact], base: BaseOperands
) -> tuple[list[Fact], ReportTable]:
    """The CP-1 facts the prose names (reading order), then the four reported ratios, each once,
    copied verbatim under their own fact ids."""
    a = sub.assessment
    texts = [
        # ruling A3: a limitation's figures follow its row's rationale
        *(text for sc in sub.scenarios for text in (sc.rationale, sc.limitation) if text),
        *(t.rationale for t in sub.thresholds),
        *(text for text in (a.rationale, a.limitation) if text),
        *(
            text
            for g in sub.gaps
            for text in (g.gap, g.why_it_matters, g.affected_analysis, g.action)
        ),
    ]
    named = [f for text in texts for f in _figure_refs(text, bound)]
    ordered = {f.fact_id: f for f in (*named, *(base.sources[m] for m in REPORTED.values()))}
    copies = [
        fact.model_copy(
            update={"table_id": CP1_REFERENCES, "row_id": f"ref{n:02d}", "field": "value"}
        )
        for n, fact in enumerate(ordered.values(), 1)
    ]
    table = ReportTable(
        table_id=CP1_REFERENCES,
        title="CP-1 facts referenced in CP-2A text",
        columns=(TableColumn(field="value", label="Value"),),
        rows=tuple(
            TableRow(
                row_id=f.row_id,
                label=f"{f.label} · {f.period}" if f.period else f.label,
                fact_ids=(f.fact_id,),
            )
            for f in copies
        ),
        row_header="CP-1 fact",
    )
    return copies, table


def _spelled(text: str, bound: Mapping[str, Fact]) -> str:
    """Round 5 limitation refs, round 9 choice 5: stored text (a limitation, a T2B.9 gap
    text, a `Gap (…)` own line) spells each `{ref|unit}` as rendered (the shown value plus
    unit, `business_context.spelled`), never as raw braces. Validated text holds only figure
    references to known CP-1 facts, so the raise is an invariant."""
    parts = []
    for run in prose.tokenize(text):
        if run.kind == "text":
            parts.append(run.text)
        elif run.figure and run.text in bound:
            parts.append(spelled(bound[run.text]))
        else:
            raise ValueError(f"Stored text reference {run.text} does not name a known CP-1 figure")
    return "".join(parts)


def _first_claim(out: _Composer, ranked: Sequence[BreakPoint]) -> str:
    """T2B.7.first; ruling A2 when the first-ranked break is already reached at base."""
    first = ranked[0]
    if first.outcome != AT_BASE:
        return (
            f"The first test reached is {first.test} at an EBITDA decline of "
            f"{out.ref('T2B.7.r01.required_decline', '%')}."
        )
    text = (
        f"The first test reached is {first.test}, already reached at base before any EBITDA "
        "decline."
    )
    by_decline = [(n, p) for n, p in enumerate(ranked, 1) if p.outcome == REACHED]
    if by_decline:
        n, p = by_decline[0]
        text += (
            f" The first test reached by a decline is {p.test} at an EBITDA decline of "
            f"{out.ref(f'T2B.7.r{n:02d}.required_decline', '%')}."
        )
    return text


def _claims(
    out: _Composer,
    sub: DownsideSubmission,
    runs: Sequence[_Run],
    ranked: Sequence[BreakPoint],
    bound: Mapping[str, Fact],
) -> list[Claim]:
    claims = [
        Claim(
            claim_id=f"T2B.1.{run.row}",
            text=sc.rationale,
            citations=(),
            limitation=None if sc.limitation is None else _spelled(sc.limitation, bound),
        )
        for run, sc in zip(runs, sub.scenarios, strict=True)
    ]
    for run in runs:
        r = run.row
        text = (
            f"Under the {run.name} scenario, stressed EBITDA is {out.ref(f'T2B.3.{r}.ebitda', 'US$ m')} "
            f"against {out.ref('T2B.3.s00.ebitda', 'US$ m')} at base, free cash flow is "
            f"{out.ref(f'T2B.3.{r}.fcf', 'US$ m')}, net leverage is "
            f"{out.ref(f'T2B.4.{r}.net_leverage', 'x')} and interest coverage is "
            f"{out.ref(f'T2B.4.{r}.interest_coverage', 'x')}."
        )
        claims.append(Claim(claim_id=f"T2B.4.{r}", text=text, citations=()))
    if ranked:
        claims.append(Claim(claim_id="T2B.7.first", text=_first_claim(out, ranked), citations=()))
    a = sub.assessment
    limitation = None if a.limitation is None else _spelled(a.limitation, bound)
    claims.append(
        Claim(claim_id="T2B.1.assessment", text=a.rationale, citations=(), limitation=limitation)
    )
    return claims


def _limitations(
    sub: DownsideSubmission,
    base: BaseOperands,
    stressed: Mapping[str, StressedRow],
    points: Sequence[BreakPoint],
    unreached: bool,
) -> list[str]:
    limits = [ANALYST_SHOCKS]
    if sub.thresholds:
        limits.append(WATCH_LEVELS)
    limits += [STATIC, HELD, LIQUIDITY, COVENANT, MATURITY, BREAK_AT_BASE]
    if unreached:
        limits.append(NOT_CALC_CROSSING)
    # Ruling A2: one line per break already reached at base, in register order.
    limits += [
        f"{p.test} is already reached at the base period, before any EBITDA decline."
        for p in points
        if p.outcome == AT_BASE
    ]
    for name in ("ebitda", "interest", "fcf", "total_debt", "cash"):
        if _operand(base, name) is None:
            limits.append(
                f"Base {WORDS[name]} is not available in CP-1 for {base.period}: "
                "every figure that needs it is Not calculable."
            )
    # The CP-1 gate line, once per gate reason a cell actually shows; ruling A6 omits it on an
    # FY or LTM base.
    shown = {reason for row in stressed.values() for reason in row.why.values()}
    quarter = period_kind(base.period) == "quarter"
    for ratio in RATIOS if quarter else ():
        gate = base.gates.get(ratio)
        if gate is not None and f"Not calculable: {gate}" in shown:
            line = (
                f"Twelve-month ratios are not calculable on the base period {base.period}: {gate}"
            )
            if line not in limits:
                limits.append(line)
    # P1-W: once when any cell shows the single-quarter reason; beside A6's line on a mixed base.
    if any(row.not_applicable for row in stressed.values()) or any(
        p.outcome == QUARTER_OUTCOME for p in points
    ):
        limits.append(QUARTER_LINE)
    return limits


def compute(inputs: Inputs) -> Result:
    """The composed CP-2A content of a valid submission; raises ValueError on any issue."""
    issues = validate(inputs)
    if issues:
        raise ValueError("; ".join(issues))
    sub = inputs.submission
    base = BaseOperands.from_cp1(inputs.cp1_facts, period=sub.base_period)
    bound = prose.bind(referencable(inputs.cp1_facts))
    out = _Composer(base)
    runs = [_Run("s00", BASE_ROW, _ZERO, _ZERO)] + [
        _Run(f"s{n:02d}", sc.name, Decimal(sc.ebitda_decline), Decimal(sc.interest_increase))
        for n, sc in enumerate(sub.scenarios, 1)
    ]
    _scenarios(out, sub, bound)
    _operands(out)
    stressed = {
        run.row: stress(base=base, decline=run.decline, increase=run.increase) for run in runs
    }
    for run in runs:
        _stress_rows(out, run, stressed[run.row])
    _reconciliation(out, stressed["s00"])
    specs = tuple(ThresholdSpec(t.metric, Decimal(t.level), t.label) for t in sub.thresholds)
    points = break_points(base=base, thresholds=specs)
    _breaks(out, points)
    ranked = rank(points)
    _ranking(out, ranked)
    crossings, unreached = _crossings(out, runs[1:], stressed, points)
    limits = _limitations(sub, base, stressed, points, unreached)
    _gaps(out, sub, limits, bound)
    claims = _claims(out, sub, runs[1:], ranked, bound)
    if not ranked:
        limits.append(NO_FIRST_BREAK)
    copies, references = _references(sub, bound, base)
    return Result(
        base=base,
        facts=(*out.facts, *copies),
        tables=(*out.tables(), references),
        claims=tuple(claims),
        limitations=tuple(limits),
        stressed=stressed,
        breaks=points,
        ranking=ranked,
        crossings=crossings,
    )
