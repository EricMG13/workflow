"""CP-L10 financial change screen: Stage 1 calculation (pure; no store, host or render call).

Python rates seven topics for their relative change between two quarters of the settled CP-1
head (lease `docs/CPL10-OWNER-LEASE.md`, oracle `cases/cpl10-owner/expected.json`, amendment 1).
Arithmetic is exact on Fractions, quantised once to Decimal (38 digits, half-even); a missing
operand is never 0.
"""

import hashlib
import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import (
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    Inexact,
    InvalidOperation,
    Rounded,
    localcontext,
)
from fractions import Fraction
from typing import Literal

from pydantic import ValidationError

from deploy_vii.business_context import Category, Confidence, Severity
from deploy_vii.contracts import (
    Citation,
    Claim,
    Contract,
    Fact,
    Hash,
    Input,
    Module,
    ReportTable,
    Run,
    TableColumn,
    TableRow,
    Text,
)
from deploy_vii.display import UnitClass, format_value
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
    Head,
    Qualification,
    StepValidation,
    inherited_limitations,
    text_sha256,
)
from deploy_vii.live.schema import exact_json, json_object, normalise
from deploy_vii.live.submission import Submitted
from deploy_vii.preparation import PreparedPack
from deploy_vii.prose import bind
from deploy_vii.prose import issues as prose_issues
from deploy_vii.readiness import shape_issues
from deploy_vii.registry import modules
from deploy_vii.report_view import fact_spelling, status_display
from deploy_workflow.owners.blank import is_blank
from deploy_workflow.owners.cp1a import probe_one_step
from deploy_workflow.workflow import WorkflowError

MODULE_ID = "CP-L10"
STEP_ID = "change_screen"
STEP_IDS = (STEP_ID,)

Materiality = Literal["Material", "Watch", "Stable", "Not assessed"]
PctStatus = Literal["known", "not_applicable", "missing"]

# Screening-policy literals (D11): stated in the CP-L10 method with an own limitation, never sourced.
MATERIAL_AT = Fraction(1, 10)
WATCH_AT = Fraction(1, 20)
_CTX = Context(prec=38, rounding=ROUND_HALF_EVEN)
_EXACT = Context(prec=200, traps=[Inexact, Rounded, InvalidOperation])  # `change`: never rounded
_CLASS_ORDER: dict[str, int] = {"Material": 0, "Watch": 1, "Not assessed": 2, "Stable": 3}
DISPOSITION: dict[str, str] = {
    "Material": "Upgrade to full module",
    "Watch": "Monitor",
    "Stable": "No action",
    "Not assessed": "Evidence needed",
}
PROHIBITED = ("recommend", "recovery", "covenant")  # CP-1A's prohibited conclusions
BAD_PAYLOAD = "(root): not a JSON object within the payload bounds"
INSUFFICIENT = "Insufficient Information"
OVERALL = "overall"  # the gap target that is not a topic
_USD, _MILLION = "USD", Decimal(1000000)
_MONEY = {"currency": _USD, "scale": _MILLION}
_DIGIT = re.compile(r"\d")


@dataclass(frozen=True)
class Quarter:
    column: str  # CP-1 T4.10 column label
    period: str  # the offered period string
    words: str  # claim spelling


QUARTERS = (
    Quarter(
        "Q1 25 (2025-01-01 to 2025-03-31)",
        "Q1 25: 2025-01-01 to 2025-03-31",
        "the first quarter of 2025",
    ),
    Quarter(
        "Q2 25 (2025-04-01 to 2025-06-30)",
        "Q2 25: 2025-04-01 to 2025-06-30",
        "the second quarter of 2025",
    ),
    Quarter(
        "Q3 25 (2025-07-01 to 2025-09-30)",
        "Q3 25: 2025-07-01 to 2025-09-30",
        "the third quarter of 2025",
    ),
    Quarter(
        "Q4 25 (2025-10-01 to 2025-12-31)",
        "Q4 25: 2025-10-01 to 2025-12-31",
        "the fourth quarter of 2025",
    ),
)
PERIODS = tuple(q.period for q in QUARTERS)


@dataclass(frozen=True)
class Topic:
    topic_id: str
    cp1_metric: str
    label: str
    unit: Literal["MILLIONS", "MULTIPLE"]
    token: str  # the unit token of a figure reference and of the view
    upgrade_module: str


TOPICS = (
    Topic("ebitda", "ebitda", "EBITDA", "MILLIONS", "US$ m", "CP-1D"),
    Topic("fcf", "fcf", "Free cash flow", "MILLIONS", "US$ m", "CP-2D"),
    Topic("cash", "cash_closing", "Cash", "MILLIONS", "US$ m", "CP-2D"),
    Topic("total_debt", "total_debt", "Total debt", "MILLIONS", "US$ m", "CP-2D"),
    Topic("net_debt", "net_debt", "Net debt", "MILLIONS", "US$ m", "CP-2D"),
    Topic("total_leverage", "total_leverage_reported", "Total leverage", "MULTIPLE", "x", "CP-2A"),
    Topic(
        "interest_coverage",
        "interest_coverage_reported",
        "Interest coverage",
        "MULTIPLE",
        "x",
        "CP-2A",
    ),
)
TOPIC_IDS = tuple(t.topic_id for t in TOPICS)
OPERAND_LABELS = tuple(f"{q.column} · {t.cp1_metric}" for t in TOPICS for q in QUARTERS)

# Column field order per table (amendment 1 F1; column labels are the product's, L3).
COLUMNS: dict[str, tuple[str, ...]] = {
    "TL10.1": (
        "subject_identity",
        "source_ref",
        "source_owner_module",
        "as_of_or_period",
        "scope_status",
        "topics_supported",
        "limitation",
    ),
    "TL10.2": (
        "from_value",
        "to_value",
        "change",
        "change_pct",
        "materiality",
        "evidence_status",
        "disposition",
        "priority_rank",
        "source_owner_modules",
        "source_refs",
        "upgrade_module_ids",
    ),
    "TL10.3": (
        "screen_item",
        "assessment",
        "evidence",
        "credit_transmission",
        "screening_implication",
        "confidence",
        "source_refs",
    ),
    "TL10.4": (
        "topic_id",
        "trigger",
        "missing_inputs",
        "decision_impact",
        "required_source",
        "target_full_module_id",
        "expected_owned_object",
        "blocking_for_full_decision",
    ),
    "TL10.5": ("material", "watch", "stable", "not_assessed"),
}
TITLES = {
    "TL10.1": "Scope and sources",
    "TL10.2": "Topic screen",
    "TL10.3": "Screen items",
    "TL10.4": "Upgrade triggers",
    "TL10.5": "Screen totals",
}

OWN_LIMITATIONS = (
    (
        "Relative-change thresholds are screening rules documented in the CP-L10 method; they "
        "are not covenant or credit tests."
    ),
    (
        "Only the two quarters named in the comparison are compared; no trend, seasonality or "
        "annual comparison is made, and the pack has no prior-year statements."
    ),
    (
        "Leverage and coverage are compared only where CP-1 carries a twelve-month basis for "
        "both quarters."
    ),
    (
        "A screen rates movement, not credit quality: no recommendation, covenant, recovery or "
        "refinancing conclusion is drawn."
    ),
    (
        "Each topic is rated on the exact change on its starting level; the percentage shown is "
        "rounded, so a shown value at a threshold can carry the lower rating."
    ),
    (
        "A small starting level inflates the relative change and a negative starting level is "
        "measured on its absolute value, so the rating reads the size of movement, not its "
        "economic meaning."
    ),
)
_INHERITED = "Inherited limitations of the CP-0 and CP-1 heads apply; see the limitations rail."
_NOT_FOR_OVERALL = "Not applicable to the overall row"


# --- submission schema (reference and judgment only; every field required) ---------------------


class Comparison(Contract):
    from_period: Text
    to_period: Text


class Assessment(Contract):
    topic_id: Text
    assessment: Text
    credit_transmission: Text
    category: Category
    confidence: Confidence


class Overall(Contract):
    rationale: Text
    category: Category
    confidence: Confidence
    limitation: Text | None


class Gap(Contract):
    gap: Text
    why_it_matters: Text
    affected_analysis: Text
    action: Text
    severity: Severity


class ChangeScreenSubmission(Contract):
    comparison: Comparison
    assessments: tuple[Assessment, ...]
    overall: Overall
    gaps: tuple[Gap, ...]


SCHEMAS: Mapping[str, type[Contract]] = {STEP_ID: ChangeScreenSubmission}


# --- inputs -------------------------------------------------------------------------------------


class UpstreamError(ValueError):
    """The bound upstream cannot be read as the screen's operands (an unbound input or operand).
    Only this is reported to the analyst as an issue; a store-integrity failure is not."""


def bind_operands(facts: Iterable[Fact]) -> dict[str, Fact]:
    """The 28 T4.10 operands by label; zero or several matches refuse (never zero, never first)."""
    found: dict[str, list[Fact]] = {}
    for fact in facts:
        if fact.table_id == "T4.10" and fact.label in OPERAND_LABELS:
            found.setdefault(fact.label, []).append(fact)
    bound: dict[str, Fact] = {}
    for label in OPERAND_LABELS:
        matches = found.get(label, [])
        if len(matches) != 1:
            raise UpstreamError(f"unbound CP-1 operand: {label} ({len(matches)} matches)")
        bound[label] = matches[0]
    return bound


@dataclass(frozen=True)
class Upstream:
    """Everything the screen reads: the settled CP-0 and CP-1 heads and the T4.10 operands."""

    issuer_name: str
    as_of: date
    cp0_status_word: str  # report_view.module_display word of the CP-0 head (amendment 1 F3)
    cp0_result_sha256: str
    cp1_status_word: str
    cp1_result_sha256: str
    cp1_facts: Mapping[str, Fact]  # '<column> · <metric>' -> CP-1 T4.10 fact
    inherited_limitations: tuple[str, ...] = ()  # CP-0 then CP-1 head limitations (the view)

    def __post_init__(self) -> None:
        for topic in TOPICS:
            scales = set()
            for quarter in QUARTERS:
                label = f"{quarter.column} · {topic.cp1_metric}"
                fact = self.cp1_facts.get(label)
                if fact is None or fact.label != label:
                    raise UpstreamError(f"unbound CP-1 operand: {label}")
                if fact.status != "known":
                    continue  # ruling (f): units and scales are checked on known operands only
                if fact.amount is None:
                    raise UpstreamError(f"CP-1 operand without an amount: {label}")
                if fact.unit != topic.unit:
                    raise UpstreamError(
                        f"CP-1 operand unit {fact.unit} is not {topic.unit}: {label}"
                    )
                scales.add(fact.scale)
            if len(scales) > 1:
                raise UpstreamError(f"CP-1 operands of {topic.topic_id} differ in scale")

    def operand(self, topic: Topic, period: str) -> Fact:
        return self.cp1_facts[f"{QUARTERS[PERIODS.index(period)].column} · {topic.cp1_metric}"]


# --- the screening rule -------------------------------------------------------------------------


def _plain(value: Decimal) -> Decimal:
    """The stored form of the exact change: zero is `0` (never `-0` or `0E+2`) and a whole number
    has no positive exponent. The value is unchanged; only its text (hash, view, reader) is."""
    if value == 0:
        return Decimal(0)
    exponent = value.as_tuple().exponent
    if isinstance(exponent, int) and exponent > 0:
        return value.quantize(Decimal(1), context=_EXACT)
    return value


def _q38(value: Fraction) -> Decimal:
    if value == 0:
        return Decimal(0)
    with localcontext(_CTX):
        return Decimal(value.numerator) / Decimal(value.denominator)


@dataclass(frozen=True)
class TopicScreen:
    materiality: Materiality
    evidence: Literal["Complete", "Missing"]
    change: Decimal | None  # closing - starting, exact (one subtraction, never rounded)
    pct_status: PctStatus
    pct: Decimal | None  # signed change / |starting|, 38 digits half-even
    pct_fraction: Fraction | None  # the exact signed quotient
    zero_base: bool

    @property
    def disposition(self) -> str:
        return DISPOSITION[self.materiality]

    @property
    def abs_pct(self) -> Fraction | None:
        return None if self.pct_fraction is None else abs(self.pct_fraction)


def screen_topic(*, start: Decimal | None, close: Decimal | None) -> TopicScreen:
    """Rate one topic. Material iff |b - a| * 10 >= |a|; Watch iff |b - a| * 20 >= |a|; exact."""
    if start is None or close is None:
        return TopicScreen("Not assessed", "Missing", None, "missing", None, None, False)
    a, b = Fraction(start), Fraction(close)
    change = b - a
    exact = _plain(_EXACT.subtract(close, start))
    if a == 0:
        rating: Materiality = "Stable" if change == 0 else "Material"
        return TopicScreen(rating, "Complete", exact, "not_applicable", None, None, True)
    if abs(change) >= abs(a) * MATERIAL_AT:
        rating = "Material"
    elif abs(change) >= abs(a) * WATCH_AT:
        rating = "Watch"
    else:
        rating = "Stable"
    signed = change / abs(a)
    return TopicScreen(rating, "Complete", exact, "known", _q38(signed), signed, False)


def rank_key(
    materiality: str, zero_base: bool, abs_pct: Fraction | None, index: int
) -> tuple[int, int, Fraction, int]:
    """Material, Watch, Not assessed, Stable; a zero-base Material first; larger |pct|; register."""
    first = 0 if zero_base and materiality == "Material" else 1
    return (_CLASS_ORDER[materiality], first, -(abs_pct or Fraction(0)), index)


@dataclass(frozen=True)
class TopicResult:
    topic: Topic
    start: Fact
    close: Fact
    screen: TopicScreen
    rank: int


def screen_pair(upstream: Upstream, from_period: str, to_period: str) -> tuple[TopicResult, ...]:
    """Every topic rated for one ordered pair, in register order, each with its rank (1 to 7)."""
    rows = []
    for topic in TOPICS:
        start = upstream.operand(topic, from_period)
        close = upstream.operand(topic, to_period)
        rows.append((topic, start, close, screen_topic(start=start.amount, close=close.amount)))
    order = sorted(
        range(len(rows)),
        key=lambda i: rank_key(rows[i][3].materiality, rows[i][3].zero_base, rows[i][3].abs_pct, i),
    )
    rank = {index: position for position, index in enumerate(order, 1)}
    return tuple(TopicResult(*row, rank=rank[i]) for i, row in enumerate(rows))


# --- display ------------------------------------------------------------------------------------


def shown_text(fact: Fact, gap_ref: str) -> str:
    """The cell text (``report_view.fact_spelling``); ``gap_ref`` is the report-wide G#."""
    return fact_spelling(fact, gap_ref)[2]


@dataclass(frozen=True)
class ViewValue:
    period: str
    status: str
    amount: Decimal | None
    shown: str  # Python's spelling of the CP-1 amount at 2 dp, never CP-1's 0 dp cell text
    limitation: str | None


@dataclass(frozen=True)
class ViewTopic:
    topic_id: str
    label: str
    cp1_metric: str
    unit: str
    values: tuple[ViewValue, ...]


@dataclass(frozen=True)
class PairScreen:
    from_period: str
    to_period: str
    topics: tuple[tuple[str, Materiality], ...]


def view_topics(upstream: Upstream, *, gap_ref: str) -> tuple[ViewTopic, ...]:
    """The four quarter values of each topic as the ``read_inputs`` view shows them."""
    out = []
    for topic in TOPICS:
        unit_class: UnitClass = "amount" if topic.unit == "MILLIONS" else "multiple"
        values = []
        for period in PERIODS:
            fact = upstream.operand(topic, period)
            shown = (
                format_value(fact.amount, unit_class, "known", decimals=2)
                if fact.status == "known"
                else shown_text(fact, gap_ref)
            )
            values.append(ViewValue(period, fact.status, fact.amount, shown, fact.limitation))
        out.append(
            ViewTopic(topic.topic_id, topic.label, topic.cp1_metric, topic.token, (*values,))
        )
    return tuple(out)


def pair_screens(upstream: Upstream) -> tuple[PairScreen, ...]:
    """Python's rating of every topic for each of the six ordered pairs of offered quarters."""
    return tuple(
        PairScreen(
            a,
            b,
            tuple((r.topic.topic_id, r.screen.materiality) for r in screen_pair(upstream, a, b)),
        )
        for i, a in enumerate(PERIODS)
        for b in PERIODS[i + 1 :]
    )


# --- composed records ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Cell:
    """One module fact plus the lineage the product Fact does not carry."""

    fact: Fact
    derives_from: tuple[str, ...] = ()
    copied_from_cp1: str | None = None


@dataclass(frozen=True)
class RowRecord:
    row_id: str
    label: str
    fact_ids: tuple[str, ...]


@dataclass(frozen=True)
class TableRecord:
    table_id: str
    title: str
    columns: tuple[str, ...]  # field order; labels are the product's (L3)
    rows: tuple[RowRecord, ...]


@dataclass(frozen=True)
class ClaimRecord:
    claim_id: str
    text: str
    refs: tuple[str, ...]
    limitation: str | None
    citations: tuple[Citation, ...]


@dataclass(frozen=True)
class ScreenResult:
    from_period: str
    to_period: str
    topics: tuple[TopicResult, ...]  # register order
    required_assessments: tuple[str, ...]
    counts: Mapping[str, int]
    cells: tuple[Cell, ...]
    tables: tuple[TableRecord, ...]
    claims: tuple[ClaimRecord, ...]
    limitations: tuple[str, ...]  # the module's own limitations
    status: Literal["restricted"] = "restricted"


def _topic_unit(topic: Topic) -> tuple[str, str | None, Decimal]:
    """The topic's unit, currency and scale: MILLIONS in USD at 1,000,000; MULTIPLE plain."""
    if topic.unit == "MILLIONS":
        return topic.unit, _USD, _MILLION
    return topic.unit, None, Decimal(1)


def _unique(citations: Iterable[Citation]) -> tuple[Citation, ...]:
    return tuple(dict.fromkeys(citations))


class _Cells:
    """Collects the cells of one table row, in column order."""

    def __init__(self, table: str, row: str, cp1: Mapping[str, Fact]) -> None:
        self.table, self.row_id, self.cp1, self.cells = table, row, cp1, list[Cell]()

    def add(self, field: str, label: str, *, derives: tuple[str, ...] = (), **kw: object) -> None:
        coordinates = {"table_id": self.table, "row_id": self.row_id, "field": field}
        if kw.get("value_class") == "calculated" and kw.get("status", "known") == "known":
            kw.setdefault("calculation_id", f"calc:{self.table}.{self.row_id}.{field}")
        if kw.get("unit") == "MILLIONS":
            kw.update(_MONEY)
        # F5 (CP-1C L3): a calculated fact cites what its derives_from cites, ordered, de-duplicated.
        cites = _unique(c for d in derives for c in self.cp1[d].citations)
        fact = Fact.model_validate(
            {
                "fact_id": f"{self.table}.{self.row_id}.{field}",
                "label": label,
                **coordinates,
                "citations": cites,
                **kw,
            }
        )
        self.cells.append(Cell(fact, derives))

    def text(
        self,
        field: str,
        label: str,
        value: str,
        vclass: str | None = None,
        derives: tuple[str, ...] = (),
    ) -> None:
        self.add(field, label, text=value, value_class=vclass, derives=derives)

    def not_applicable(self, field: str, label: str, reason: str) -> None:
        self.add(field, label, status="not_applicable", limitation=reason)

    def copied(self, field: str, label: str, cp1: Fact, topic: Topic) -> None:
        """The CP-1 value with its value_class, status, limitation, citations and calculation_id
        verbatim (lease :121); CP-1's formula is not copied (L10-c). Shown at 2 dp. A known value
        keeps CP-1's unit, currency and scale (checked against the topic at binding); a value
        that is not known takes the topic's (round 5 (f))."""
        known = cp1.status == "known"
        if known:
            unit, currency, scale = cp1.unit, cp1.currency, cp1.scale
        else:
            unit, currency, scale = _topic_unit(topic)
        fact = Fact(
            fact_id=f"{self.table}.{self.row_id}.{field}",
            label=label,
            table_id=self.table,
            row_id=self.row_id,
            field=field,
            amount=cp1.amount,
            status=cp1.status,
            unit=unit,
            currency=currency,
            scale=scale,
            decimals=2 if known and unit == "MILLIONS" else None,
            period=cp1.period,
            citations=cp1.citations,
            calculation_id=cp1.calculation_id,
            value_class=cp1.value_class,
            limitation=cp1.limitation,
        )
        self.cells.append(Cell(fact, (), cp1.label))

    def row(self, label: str) -> RowRecord:
        fields = tuple(c.fact.field for c in self.cells)
        if fields != COLUMNS[self.table]:  # one fact per column, in column order (F1)
            raise ValueError(f"{self.table}.{self.row_id} cells {fields} differ from its columns")
        return RowRecord(self.row_id, label, tuple(c.fact.fact_id for c in self.cells))


def _ends(r: TopicResult) -> str:
    if r.start.status != "known" and r.close.status != "known":
        return "either quarter"
    return "the starting quarter" if r.start.status != "known" else "the closing quarter"


def _cp1_limitation(r: TopicResult) -> str | None:
    """CP-1's own limitation of the missing end (the starting end when both are missing)."""
    missing = r.start if r.start.status != "known" else r.close
    return missing.limitation


def _topic_row(r: TopicResult, pair_period: str, cp1: Mapping[str, Fact]) -> _Cells:
    """TL10.2: the copied CP-1 cells, the exact change, its rating, rank and pointers."""
    t, s = r.topic, r.screen
    cells = _Cells("TL10.2", t.topic_id, cp1)
    cells.copied("from_value", f"{t.label} · Starting value", r.start, t)
    cells.copied("to_value", f"{t.label} · Closing value", r.close, t)
    derives = (r.start.label, r.close.label)
    pct_label = f"{t.label} · Change on starting level"
    if s.change is None:
        reason = (
            f"Not calculable: CP-1 carries no known value for {_ends(r)} ({_cp1_limitation(r)})"
        )
        for field, label, unit in (
            ("change", f"{t.label} · Change", t.unit),
            ("change_pct", pct_label, "PERCENT"),
        ):
            cells.add(
                field, label, status="missing", unit=unit, period=pair_period, limitation=reason
            )
    else:
        cells.add(
            "change",
            f"{t.label} · Change",
            amount=s.change,
            unit=t.unit,
            period=pair_period,
            decimals=2 if t.unit == "MILLIONS" else None,
            value_class="calculated",
            formula="closing value - starting value",
            derives=derives,
        )
        if s.pct is None:
            cells.add(
                "change_pct",
                pct_label,
                status="not_applicable",
                unit="PERCENT",
                period=pair_period,
                limitation="Not applicable: the starting value is zero",
                value_class="calculated",
            )
        else:
            cells.add(
                "change_pct",
                pct_label,
                amount=s.pct,
                unit="PERCENT",
                period=pair_period,
                value_class="calculated",
                formula="(closing value - starting value) / |starting value|",
                derives=derives,
            )
    cells.text("materiality", "Materiality", s.materiality, "calculated", derives)
    cells.text("evidence_status", "Evidence status", s.evidence, "calculated", derives)
    cells.text("disposition", "Disposition", s.disposition, "calculated", derives)
    cells.add(
        "priority_rank",
        "Priority rank",
        amount=Decimal(r.rank),
        unit="rank",
        period=pair_period,
        decimals=0,
        value_class="calculated",
        derives=derives,
        formula="Material, Watch, Not assessed, Stable; larger |change on starting level| first; "
        "register order",
    )
    cells.text("source_owner_modules", "Source owner modules", "CP-1")
    cells.text("source_refs", "Source references", f"CP-1 {r.start.label}; CP-1 {r.close.label}")
    cells.text("upgrade_module_ids", "Upgrade module ids", t.upgrade_module)
    return cells


_COUNTS: tuple[tuple[str, Materiality], ...] = (
    ("material", "Material"),
    ("watch", "Watch"),
    ("stable", "Stable"),
    ("not_assessed", "Not assessed"),
)


def _total_row(counts: Mapping[str, int], pair_period: str, cp1: Mapping[str, Fact]) -> _Cells:
    """TL10.5 screen totals: topic counts per materiality."""
    cells = _Cells("TL10.5", "total", cp1)
    for key, word in _COUNTS:
        cells.add(
            key,
            f"Topics rated {word}",
            amount=Decimal(counts[key]),
            unit="topics",
            period=pair_period,
            decimals=0,
            value_class="calculated",
            formula="count of topics by materiality",
        )
    return cells


def _scope_rows(
    upstream: Upstream, rows: tuple[TopicResult, ...], pair_period: str
) -> list[tuple[str, _Cells]]:
    """TL10.1: one row per upstream head; source_ref and scope_status are run-bound (F3)."""
    supported = ", ".join(r.topic.label for r in rows if r.screen.evidence == "Complete")
    out = []
    for rid, module, sha, word, period, topics in (
        (
            "cp0",
            "CP-0",
            upstream.cp0_result_sha256,
            upstream.cp0_status_word,
            f"as of {upstream.as_of.isoformat()}",
            "None: source readiness only",
        ),
        (
            "cp1",
            "CP-1",
            upstream.cp1_result_sha256,
            upstream.cp1_status_word,
            pair_period,
            supported,
        ),
    ):
        cells = _Cells("TL10.1", rid, upstream.cp1_facts)
        cells.text("subject_identity", "Subject identity", upstream.issuer_name)
        cells.text("source_ref", "Source reference", f"{module}:{sha}")
        cells.text("source_owner_module", "Source owner module", module)
        cells.text("as_of_or_period", "As of or period", period)
        cells.text("scope_status", "Scope status", word)
        cells.text(
            "topics_supported", "Topics supported", topics, "calculated" if rid == "cp1" else None
        )
        cells.text("limitation", "Limitation", _INHERITED)
        out.append((module, cells))
    return out


def _item_rows(
    rows: tuple[TopicResult, ...], sub: ChangeScreenSubmission, cp1: Mapping[str, Fact]
) -> list[tuple[str, _Cells]]:
    """TL10.3: one row per assessed topic (register order), then the overall row (F1)."""
    analyst = {a.topic_id: a for a in sub.assessments}
    out = []
    for r in rows:
        a = analyst.get(r.topic.topic_id)
        if a is None:
            continue
        tid = r.topic.topic_id
        cells = _Cells("TL10.3", tid, cp1)
        refs = (r.start.label, r.close.label)
        cells.text("screen_item", "Screen item", r.topic.label)
        cells.text("assessment", "Assessment", a.assessment, "analyst_judgment")
        evidence = ", ".join(
            f"TL10.2.{tid}.{f}" for f in ("from_value", "to_value", "change", "change_pct")
        )
        cells.text("evidence", "Evidence", evidence)
        cells.text(
            "credit_transmission", "Credit transmission", a.credit_transmission, "analyst_judgment"
        )
        cells.text(
            "screening_implication",
            "Screening implication",
            r.screen.disposition,
            "calculated",
            refs,
        )
        cells.text("confidence", "Confidence", a.confidence, "analyst_judgment")
        cells.text(
            "source_refs", "Source references", f"CP-1 {r.start.label}; CP-1 {r.close.label}"
        )
        out.append((r.topic.label, cells))
    overall = _Cells("TL10.3", "overall", cp1)
    overall.text("screen_item", "Screen item", "Overall")
    overall.text("assessment", "Assessment", sub.overall.rationale, "analyst_judgment")
    overall.not_applicable("evidence", "Evidence", _NOT_FOR_OVERALL)
    overall.not_applicable("credit_transmission", "Credit transmission", _NOT_FOR_OVERALL)
    overall.not_applicable("screening_implication", "Screening implication", _NOT_FOR_OVERALL)
    overall.text("confidence", "Confidence", sub.overall.confidence, "analyst_judgment")
    overall.not_applicable("source_refs", "Source references", _NOT_FOR_OVERALL)
    out.append(("Overall", overall))
    return out


_TRIGGER = {
    "Material": "Relative change at or above the Material threshold",
    "Watch": "Relative change at or above the Watch threshold",
    "Not assessed": "Change not calculable from CP-1 facts",
}


def _trigger_rows(
    rows: tuple[TopicResult, ...], sub: ChangeScreenSubmission, cp1: Mapping[str, Fact]
) -> list[tuple[str, _Cells]]:
    """TL10.4: every topic not rated Stable, register order."""
    analyst = {a.topic_id: a for a in sub.assessments}
    titles = {m.module_id: m.title for m in modules()}
    out = []
    for r in rows:
        if r.screen.materiality == "Stable":
            continue
        tid, complete = r.topic.topic_id, r.screen.evidence == "Complete"
        cells = _Cells("TL10.4", tid, cp1)
        cells.text("topic_id", "Topic", tid)
        cells.text("trigger", "Trigger", _TRIGGER[r.screen.materiality], "calculated")
        missing = "None" if complete else "A CP-1 value for each quarter compared"
        cells.text("missing_inputs", "Missing inputs", missing, "calculated")
        a = analyst.get(tid)
        if a is not None:
            cells.text(
                "decision_impact", "Decision impact", a.credit_transmission, "analyst_judgment"
            )
        else:
            cells.add(
                "decision_impact",
                "Decision impact",
                status="missing",
                limitation="No assessment: the change is not calculable from CP-1 facts",
            )
        source = (
            "Settled CP-1 head (available)"
            if complete
            else f"A CP-1 known value for each quarter compared (CP-1: {_cp1_limitation(r)})"
        )
        cells.text("required_source", "Required source", source, "calculated")
        cells.text("target_full_module_id", "Target full module", r.topic.upgrade_module)
        cells.text("expected_owned_object", "Expected owned object", titles[r.topic.upgrade_module])
        blocking = "Yes" if r.screen.materiality == "Material" else "No"
        cells.text(
            "blocking_for_full_decision", "Blocking for full decision", blocking, "calculated"
        )
        out.append((r.topic.label, cells))
    return out


def _claim(
    claim_id: str,
    text: str,
    refs: tuple[str, ...],
    limitation: str | None,
    facts: Mapping[str, Fact],
) -> ClaimRecord:
    """F5: citations are the referenced facts' citations, first-reference order, de-duplicated."""
    cites = _unique(c for ref in refs for c in facts[ref.split("|")[0]].citations)
    return ClaimRecord(claim_id, text, refs, limitation, cites)


def _claims(
    rows: tuple[TopicResult, ...],
    sub: ChangeScreenSubmission,
    span: str,
    facts: Mapping[str, Fact],
) -> list[ClaimRecord]:
    out = []
    for r in rows:
        base, u = f"TL10.2.{r.topic.topic_id}", r.topic.token
        if r.screen.change is None:
            text = (
                f"{r.topic.label}: the change {span} cannot be screened; [{base}.change] is not "
                f"calculable because CP-1 carries no known value for {_ends(r)}."
            )
            out.append(_claim(base, text, (f"{base}.change",), None, facts))
            continue
        refs = [f"{base}.from_value|{u}", f"{base}.to_value|{u}", f"{base}.change|{u}"]
        if r.screen.pct_status == "known":
            refs.append(f"{base}.change_pct|%")
            tail = f" or {{{base}.change_pct|%}} of the starting level"
        else:
            tail = " from a zero starting level"
        text = (
            f"{r.topic.label} moved from {{{base}.from_value|{u}}} to {{{base}.to_value|{u}}} "
            f"{span}, a change of {{{base}.change|{u}}}{tail}; the screen rates it "
            f"{r.screen.materiality}."
        )
        out.append(_claim(base, text, tuple(refs), None, facts))
    totals = tuple(f"TL10.5.total.{key}|topics" for key, _ in _COUNTS)
    m, w, s, n = (f"{{{ref}}}" for ref in totals)
    summary = (
        f"Of seven screened topics, {m} rate Material, {w} Watch, {s} Stable and {n} cannot be "
        f"assessed {span}."
    )
    out.append(_claim("TL10.2.summary", summary, totals, None, facts))
    analyst = {a.topic_id: a for a in sub.assessments}
    for r in rows:
        a = analyst.get(r.topic.topic_id)
        if a is not None:
            out.append(_claim(f"TL10.3.{r.topic.topic_id}", a.assessment, (), None, facts))
    ov = sub.overall
    out.append(_claim("TL10.3.overall", ov.rationale, (), ov.limitation, facts))
    return out


def _limitations(rows: tuple[TopicResult, ...], sub: ChangeScreenSubmission) -> tuple[str, ...]:
    own = list(OWN_LIMITATIONS)
    own += [
        f"Not screened: {r.topic.label} (CP-1 has no known value for {_ends(r)})."
        for r in rows
        if r.screen.evidence == "Missing"
    ]
    own += [f"Gap ({g.severity}): {g.gap}" for g in sub.gaps]
    return tuple(own)


@dataclass(frozen=True)
class _Composed:
    rows: tuple[TopicResult, ...]
    counts: dict[str, int]
    tables: tuple[tuple[str, list[tuple[str, _Cells]]], ...]  # (table id, [(row label, cells)])
    span: str

    @property
    def cells(self) -> tuple[Cell, ...]:
        return tuple(c for _, rows in self.tables for _, group in rows for c in group.cells)


def _compose(upstream: Upstream, sub: ChangeScreenSubmission) -> _Composed:
    """Every table of the module for the submitted (offered, ordered) pair."""
    a, b = sub.comparison.from_period, sub.comparison.to_period
    rows = screen_pair(upstream, a, b)
    pair_period = f"{a} -> {b}"
    cp1 = upstream.cp1_facts
    counts = {key: sum(1 for r in rows if r.screen.materiality == word) for key, word in _COUNTS}
    words = {q.period: q.words for q in QUARTERS}
    tables = (
        ("TL10.1", _scope_rows(upstream, rows, pair_period)),
        ("TL10.2", [(r.topic.label, _topic_row(r, pair_period, cp1)) for r in rows]),
        ("TL10.3", _item_rows(rows, sub, cp1)),
        ("TL10.4", _trigger_rows(rows, sub, cp1)),
        ("TL10.5", [("Total", _total_row(counts, pair_period, cp1))]),
    )
    return _Composed(rows, counts, tables, f"between {words[a]} and {words[b]}")


# --- validation (one stated order) and composition --------------------------------------------


def _parse(
    submission: str | bytes | Mapping[str, object],
) -> ChangeScreenSubmission | tuple[str, ...]:
    """Model text is read only through the bounded parse (`json_object`, protocol section 6): a
    payload that is not a storable JSON object within the nesting bound is a shape issue."""
    if isinstance(submission, Mapping):
        text: str | None = exact_json(dict(submission))
    elif isinstance(submission, bytes):
        try:
            text = submission.decode()
        except UnicodeDecodeError:
            text = None
    else:
        text = submission
    document = None if text is None else json_object(text)
    if document is None:
        return (BAD_PAYLOAD,)
    try:
        return ChangeScreenSubmission.model_validate_json(exact_json(document))
    except ValidationError as error:
        return shape_issues(error)


def _comparison_issues(comparison: Comparison) -> list[str]:
    issues = [
        f"comparison.{name}: not an offered period"
        for name, period in (
            ("from_period", comparison.from_period),
            ("to_period", comparison.to_period),
        )
        if period not in PERIODS
    ]
    if not issues and PERIODS.index(comparison.to_period) <= PERIODS.index(comparison.from_period):
        issues.append("comparison: to_period must come after from_period")
    return issues


def _confidence_issues(path: str, confidence: str, category: str) -> list[str]:
    """High is refused for every confidence; then confidence is Insufficient Information iff the
    category is (L2 order; ruling (e) applies the pairing to assessments as to the overall)."""
    issues = [f"{path}.confidence: High is not allowed in a screen"] if confidence == "High" else []
    if (confidence == INSUFFICIENT) != (category == INSUFFICIENT):
        issues.append(
            f"{path}.confidence: must be Insufficient Information exactly when the category is"
        )
    return issues


def _assessment_issues(sub: ChangeScreenSubmission, rated: Mapping[str, Materiality]) -> list[str]:
    """Step (3): per assessment unknown topic, not assessable, repeated, confidence; then missing."""
    issues: list[str] = []
    seen: set[str] = set()
    for i, a in enumerate(sub.assessments):
        path = f"assessments[{i}]"
        if a.topic_id not in rated:
            issues.append(f"{path}.topic_id: unknown topic: {a.topic_id}")
        elif rated[a.topic_id] not in ("Material", "Watch"):
            issues.append(
                f"{path}.topic_id: not assessable: {a.topic_id} is rated {rated[a.topic_id]}"
            )
        elif a.topic_id in seen:
            issues.append(f"{path}.topic_id: repeated: {a.topic_id}")
        seen.add(a.topic_id)
        issues += _confidence_issues(path, a.confidence, a.category)
    issues += [
        f"assessments: missing assessment for {tid} ({rating})"
        for tid, rating in rated.items()
        if rating in ("Material", "Watch") and tid not in seen
    ]
    return issues


def _text_issues(sub: ChangeScreenSubmission, bound: Mapping[str, Fact], issuer: str) -> list[str]:
    """Step (4): the settlement prose path (`prose.issues`, L10-a) against the module's bound
    facts, then prohibited words (substring match, the v1 limit of L10-b), then empty text."""
    texts = [
        (f"assessments[{i}].{field}", getattr(a, field))
        for i, a in enumerate(sub.assessments)
        for field in ("assessment", "credit_transmission")
    ]
    texts.append(("overall.rationale", sub.overall.rationale))
    issues: list[str] = []
    for path, text in texts:
        issues += [f"{path}: {i}" for i in prose_issues(text, bound, names=(issuer,))]
        issues += [f"{path}: prohibited conclusion: {w}" for w in PROHIBITED if w in text.lower()]
        if is_blank(text):
            issues.append(f"{path}: empty")
    return issues


def _overall_issues(overall: Overall) -> list[str]:
    """Step (5), in the L2 order: High, pairing, limitation required, limitation forbidden, then
    empty text (round 11 blank text, in the module's pinned frame `<path>: empty`)."""
    issues = _confidence_issues("overall", overall.confidence, overall.category)
    insufficient = overall.category == INSUFFICIENT
    if insufficient and overall.limitation is None:
        issues.append(
            "overall.limitation: an Insufficient Information overall states its limitation"
        )
    if not insufficient and overall.limitation is not None:  # keyed on the category (L1)
        issues.append(
            "overall.limitation: only an Insufficient Information overall carries a limitation"
        )
    if overall.limitation is not None and is_blank(overall.limitation):
        issues.append("overall.limitation: empty")
    return issues


def _gap_issues(gaps: tuple[Gap, ...]) -> list[str]:
    """Step (6), per gap in order: topic, missing item, empty why and action (round 11 blank
    text, the module's frame `<path>: empty`), digits (field order), repeat."""
    issues: list[str] = []
    seen: set[tuple[str, str]] = set()
    for i, g in enumerate(gaps):
        path = f"gaps[{i}]"
        if g.affected_analysis not in (*TOPIC_IDS, OVERALL):
            issues.append(f"{path}.affected_analysis: must name a topic of the view or overall")
        if is_blank(g.gap):
            issues.append(f"{path}.gap: empty")
        for field in ("why_it_matters", "action"):
            if is_blank(getattr(g, field)):
                issues.append(f"{path}.{field}: empty")
        for field in ("gap", "why_it_matters", "affected_analysis", "action"):
            if _DIGIT.search(getattr(g, field)):
                issues.append(f"{path}.{field}: must not contain a digit")
        key = (g.affected_analysis, g.gap)
        if key in seen:
            issues.append(f"{path}: repeated gap")
        seen.add(key)
    return issues


def validate_screen(
    *, submission: str | bytes | Mapping[str, object], upstream: Upstream
) -> tuple[str, ...]:
    """Issues in the lease's order: shape (alone); comparison (ends); assessments; text;
    overall; gaps."""
    sub = _parse(submission)
    if isinstance(sub, tuple):
        return sub
    issues = _comparison_issues(sub.comparison)
    if issues:
        return tuple(issues)
    composed = _compose(upstream, sub)
    rated = {r.topic.topic_id: r.screen.materiality for r in composed.rows}
    issues += _assessment_issues(sub, rated)
    # Step (4) binds every Python-built fact of the module for this pair (not the analyst's).
    python = (c.fact for c in composed.cells if c.fact.value_class != "analyst_judgment")
    issues += _text_issues(sub, bind(python), upstream.issuer_name)
    issues += _overall_issues(sub.overall)
    issues += _gap_issues(sub.gaps)
    return tuple(issues)


def change_screen(
    *, submission: str | bytes | Mapping[str, object], upstream: Upstream
) -> ScreenResult:
    """The composed screen for a valid submission; raises ValueError listing every issue."""
    issues = validate_screen(submission=submission, upstream=upstream)
    if issues:
        raise ValueError("; ".join(issues))
    sub = _parse(submission)
    assert not isinstance(sub, tuple)  # validated above
    composed = _compose(upstream, sub)
    cells = composed.cells
    facts = {c.fact.fact_id: c.fact for c in cells}
    return ScreenResult(
        from_period=sub.comparison.from_period,
        to_period=sub.comparison.to_period,
        topics=composed.rows,
        required_assessments=tuple(
            r.topic.topic_id for r in composed.rows if r.screen.materiality in ("Material", "Watch")
        ),
        counts=composed.counts,
        cells=cells,
        tables=tuple(
            TableRecord(
                table_id,
                TITLES[table_id],
                COLUMNS[table_id],
                tuple(group.row(label) for label, group in rows),
            )
            for table_id, rows in composed.tables
        ),
        claims=tuple(_claims(composed.rows, sub, composed.span, facts)),
        limitations=_limitations(composed.rows, sub),
    )


# --- Stage 2: the G1-X plug-in parts (docs/G1X-OWNER-CORE-PROTOCOL.md section 2) ----------------

QUALIFICATION = Qualification(implementation="implemented")
CP0, CP1 = "CP-0", "CP-1"
SUBMISSION_INPUT = STEP_ID.replace("_", "-") + "-submission"
_SYNTHETIC = "Synthetic case; not real issuer qualification"  # execution.settle's own text
_VIEW_GAP = "G0"  # a valid gap id the view spells with, shown as the unbound `G#`
SCREEN_RULES = (
    "Python rates each of the seven topics for the change between the two quarters you choose. "
    "A topic is Material when the absolute change is at least one tenth of the absolute starting "
    "value, Watch when it is at least one twentieth, otherwise Stable; the rating uses the exact "
    "values, not the rounded percentage. A zero starting value with a change is Material. A "
    "topic with a missing value at either end is Not assessed. Ranks run Material, Watch, Not "
    "assessed, Stable, larger relative change first. Write exactly one assessment for each topic "
    "rated Material or Watch in `pair_screens` for your pair, none for any other. Confidence is "
    "Medium or Low, never High. Write no figure, no reference and no recommendation, recovery or "
    "covenant conclusion."
)


class ScreenReport(Contract):
    """What the validated step retains: the composed module body, bound to the run and pack."""

    schema_version: Literal["change-screen/1"] = "change-screen/1"
    run: Run
    pack_sha256: Hash
    submission_sha256: Hash
    tables: tuple[ReportTable, ...]
    facts: tuple[Fact, ...]
    claims: tuple[Claim, ...]
    limitations: tuple[Text, ...]


def _bound(store: Execution, attempt: Attempt, module_id: str) -> tuple[Input, Module]:
    item = next((i for i in attempt.inputs if i.input_id == module_id), None)
    if item is None:
        raise UpstreamError(f"The CP-L10 attempt binds no {module_id} input")
    return item, store.result(item.sha256)


def cpl10_upstream(store: Execution, attempt: Attempt) -> Upstream:
    """The CP-0 and CP-1 heads `attempt` binds, read from the store: the run identity, each
    head's status word and result hash, the 28 CP-1 T4.10 operands (zero or several matches
    refuse) and the limitations the settled module will inherit."""
    snapshot = store.read()
    cp0, cp1 = (_bound(store, attempt, m) for m in (CP0, CP1))
    own = (*OWN_LIMITATIONS, *((_SYNTHETIC,) if snapshot.run.case_kind == "synthetic" else ()))
    return Upstream(
        issuer_name=snapshot.run.issuer_name,
        as_of=snapshot.run.as_of,
        cp0_status_word=status_display(cp0[0].status)[1],
        cp0_result_sha256=cp0[0].sha256,
        cp1_status_word=status_display(cp1[0].status)[1],
        cp1_result_sha256=cp1[0].sha256,
        cp1_facts=bind_operands(cp1[1].facts),
        inherited_limitations=inherited_limitations(snapshot, attempt, own, store.head_module),
    )


def _plain_text(amount: Decimal | None) -> str | None:
    """CP-1's canonical exact decimal: no trailing zeros, no exponent (`17.50` reads `17.5`)."""
    return None if amount is None else format(amount.normalize(_EXACT), "f")


def context_block(*, upstream: Upstream) -> dict[str, object]:
    """The exact `read_inputs` view (lease D2): upstream statuses, the four quarters, each topic's
    values as Python spells them, Python's rating of every offered pair, the rules and the
    inherited limitations. No quote, citation or record."""
    topics = [
        {
            "topic_id": t.topic_id,
            "label": t.label,
            "cp1_metric": t.cp1_metric,
            "unit": t.unit,
            "values": [
                {
                    "period": v.period,
                    "status": v.status,
                    "amount_exact": _plain_text(v.amount),
                    "shown": v.shown.replace(_VIEW_GAP, "G#"),
                    "limitation": v.limitation,
                }
                for v in t.values
            ],
        }
        for t in view_topics(upstream, gap_ref=_VIEW_GAP)
    ]
    return {
        "upstream": [
            {"module_id": CP0, "status": upstream.cp0_status_word},
            {"module_id": CP1, "status": upstream.cp1_status_word},
        ],
        "periods": [{"period": q.period, "column": q.column} for q in QUARTERS],
        "topics": topics,
        "pair_screens": [
            {
                "from_period": p.from_period,
                "to_period": p.to_period,
                "topics": [{"topic_id": i, "materiality": m} for i, m in p.topics],
            }
            for p in pair_screens(upstream)
        ],
        "rules": SCREEN_RULES,
        "inherited_limitations": list(upstream.inherited_limitations),
    }


def view(historical: Execution, attempt: Attempt) -> tuple[str, str]:
    """(sha256, body) of CP-L10's one read, as compact JSON (protocol section 2). An upstream the
    adapter cannot bind is an identity failure of the read, never a partial view."""
    try:
        upstream = cpl10_upstream(historical, attempt)
    except UpstreamError as error:
        raise WorkflowError("identity_mismatch") from error
    body = json.dumps(
        context_block(upstream=upstream), ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(body.encode()).hexdigest(), body


def _label(field: str) -> str:
    return field.replace("_", " ").capitalize()


def screen_report(
    *, submission: str, upstream: Upstream, run: Run, pack_sha256: str
) -> ScreenReport:
    """The composed report of a valid submission (raises ValueError listing every issue)."""
    result = change_screen(submission=submission, upstream=upstream)
    parsed = _parse(submission)
    assert not isinstance(parsed, tuple)  # change_screen validated it
    return ScreenReport(
        run=run,
        pack_sha256=pack_sha256,
        submission_sha256=parsed.content_hash(),
        tables=tuple(
            ReportTable(
                table_id=t.table_id,
                title=t.title,
                columns=tuple(TableColumn(field=f, label=_label(f)) for f in t.columns),
                rows=tuple(
                    TableRow(row_id=r.row_id, label=r.label, fact_ids=r.fact_ids) for r in t.rows
                ),
            )
            for t in result.tables
        ),
        facts=tuple(c.fact for c in result.cells),
        claims=tuple(
            Claim(claim_id=c.claim_id, text=c.text, citations=c.citations, limitation=c.limitation)
            for c in result.claims
        ),
        limitations=result.limitations,
    )


def cpl10_module(report: ScreenReport, *, inputs: tuple[Input, ...], attempt: int) -> Module:
    """The candidate: the report's body bound to `inputs` plus the submission digest (the tail)."""
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


def _validate_step(store: Execution, pack: PreparedPack, attempt: Attempt) -> StepValidation:
    """The step validator the entry hands `Execution.submit_step` and the verifier replays. An
    upstream the adapter cannot bind is returned as an issue, so the step settles invalid instead
    of staying pending."""
    payload = store.payload(attempt.steps[0].payload_sha256)
    parsed = _parse(payload)
    if isinstance(parsed, tuple):
        return StepValidation(issues=parsed)
    try:
        upstream = cpl10_upstream(store, attempt)
    except UpstreamError as error:  # an integrity failure of the store is not caught here
        return StepValidation(issues=(f"CP-L10: {error}",))
    issues = validate_screen(submission=payload, upstream=upstream)
    if issues:
        return StepValidation(issues=issues)
    report = screen_report(
        submission=payload, upstream=upstream, run=pack.run, pack_sha256=pack.content_hash()
    )
    return StepValidation(output=report.model_dump_json())


ENTRY_VALIDATOR = _validate_step


def _candidate(output: str, attempt: Attempt) -> Module:
    return cpl10_module(
        ScreenReport.model_validate_json(output), inputs=attempt.inputs, attempt=attempt.number
    )


def submit(
    store: Execution,
    ticket_id: str,
    step_id: str,
    payload: str,
    rules: Callable[[str], tuple[str, ...]] | None,
) -> Submitted:
    """Journal the one `change_screen` step and, when it is valid, settle CP-L10 with the Python
    candidate (as `cp2_synthesis.submit_cp2_step`). An invalid step finishes the attempt."""
    if step_id != STEP_ID:
        raise ValueError(f"CP-L10 has one step, {STEP_ID}")
    if rules is not None:
        raise ValueError("CP-L10 has no tool-loop rules")
    normalised, resolved = normalise(ChangeScreenSubmission, payload)
    attempt = next((a for a in store.read().attempts if a.ticket_id == ticket_id), None)
    if attempt is None or attempt.module_id != MODULE_ID or attempt.status != "pending":
        raise ValueError("Ticket is absent, finished or belongs to another module")
    if attempt.steps and attempt.steps[0].payload_sha256 != text_sha256(normalised):
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
    if attempt.status != "finished":
        outcome = _validate_step(store, store.pack(), attempt)
        if outcome.issues or outcome.output is None or not outcome.retained_as(attempt.steps[0]):
            raise ValueError("Retained CP-L10 output differs from trusted validation")
        candidate = _candidate(outcome.output, attempt)
        attempt = store.finish(
            ticket_id,
            candidate.model_dump_json(),
            lambda supplied: () if supplied == candidate else ("CP-L10 candidate differs",),
            qualification=QUALIFICATION,
        )
    return Submitted(attempt, normalised, resolved, (), (), None)


def probe(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    """The verifier's rebuild: raises `identity_mismatch` unless the settled attempt and head are
    exactly what the validator and `cpl10_module` produce (protocol section 2)."""
    probe_one_step(store, snapshot, attempt, validate=_validate_step, build=_candidate)


# --- D3 (OPEN): the reader pins what a consumer reads; no consumer core exists ------------------


@dataclass(frozen=True)
class TopicRead:
    topic_id: str
    materiality: str
    evidence: str
    disposition: str
    rank: int
    change: Decimal | None


@dataclass(frozen=True)
class Cpl10Head:
    status: str
    result_sha256: str
    topics: tuple[TopicRead, ...]
    counts: Mapping[str, int]


def cpl10_reader(store: Execution, head: Head) -> Cpl10Head:
    """What a consumer reads of a settled CP-L10 head (lease D3, expected.consumption): status,
    per topic id, materiality, evidence, disposition, rank and change, and the counts, all read
    from the settled facts. Consumption is OPEN: no consumer core reads this yet."""
    if head.module_id != MODULE_ID:
        raise ValueError(f"{head.module_id} is not a CP-L10 head")
    module = store.head_module(head)
    if module.status == "blocked":  # a blocked head carries no tables: status and hash only
        return Cpl10Head(module.status, head.result_sha256, (), {})
    facts = {f.fact_id: f for f in module.facts}

    def fact(table: str, row: str, field: str) -> Fact:
        found = facts.get(f"{table}.{row}.{field}")
        if found is None:
            raise ValueError(f"CP-L10 head lacks {table}.{row}.{field}")
        return found

    def text(row: str, field: str) -> str:
        value = fact("TL10.2", row, field).text
        if value is None:
            raise ValueError(f"CP-L10 fact TL10.2.{row}.{field} has no text")
        return value

    def number(table: str, row: str, field: str) -> Decimal:
        value = fact(table, row, field).amount
        if value is None:
            raise ValueError(f"CP-L10 fact {table}.{row}.{field} has no amount")
        return value

    topics = tuple(
        TopicRead(
            topic_id=t,
            materiality=text(t, "materiality"),
            evidence=text(t, "evidence_status"),
            disposition=text(t, "disposition"),
            rank=int(number("TL10.2", t, "priority_rank")),
            change=fact("TL10.2", t, "change").amount,
        )
        for t in TOPIC_IDS
    )
    counts = {key: int(number("TL10.5", "total", key)) for key, _ in _COUNTS}
    return Cpl10Head(module.status, head.result_sha256, topics, counts)
