"""CP-L10 financial change screen: Stage 1 calculation (pure; no store, host or render call).

Python rates seven topics for their relative change between two quarters of the settled CP-1
head (lease `docs/CPL10-OWNER-LEASE.md`, oracle `cases/cpl10-owner/expected.json`, amendment 1).
Arithmetic is exact on Fractions, quantised once to Decimal (38 digits, half-even); a missing
operand is never 0.
"""

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from fractions import Fraction
from typing import Literal

from pydantic import ValidationError

from deploy_vii.business_context import Category, Confidence, Severity
from deploy_vii.contracts import Citation, Contract, Fact, Text
from deploy_vii.display import UnitClass, format_value
from deploy_vii.prose import bind
from deploy_vii.prose import issues as prose_issues
from deploy_vii.readiness import shape_issues
from deploy_vii.registry import modules
from deploy_vii.report_view import fact_spelling

MODULE_ID = "CP-L10"
STEP_ID = "change_screen"
STEP_IDS = (STEP_ID,)

Materiality = Literal["Material", "Watch", "Stable", "Not assessed"]
PctStatus = Literal["known", "not_applicable", "missing"]

# Screening-policy literals (D11): stated in the CP-L10 method with an own limitation, never sourced.
MATERIAL_AT = Fraction(1, 10)
WATCH_AT = Fraction(1, 20)
_CTX = Context(prec=38, rounding=ROUND_HALF_EVEN)
_CLASS_ORDER: dict[str, int] = {"Material": 0, "Watch": 1, "Not assessed": 2, "Stable": 3}
DISPOSITION: dict[str, str] = {
    "Material": "Upgrade to full module",
    "Watch": "Monitor",
    "Stable": "No action",
    "Not assessed": "Evidence needed",
}
PROHIBITED = ("recommend", "recovery", "covenant")  # CP-1A's prohibited conclusions
INSUFFICIENT = "Insufficient Information"
OVERALL = "overall"  # the gap target that is not a topic
_MONEY = {"currency": "USD", "scale": Decimal(1000000)}
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
            raise ValueError(f"unbound CP-1 operand: {label} ({len(matches)} matches)")
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

    def __post_init__(self) -> None:
        for topic in TOPICS:
            scales = set()
            for quarter in QUARTERS:
                label = f"{quarter.column} · {topic.cp1_metric}"
                fact = self.cp1_facts.get(label)
                if fact is None or fact.label != label:
                    raise ValueError(f"unbound CP-1 operand: {label}")
                if fact.status != "known":
                    continue  # ruling (f): units and scales are checked on known operands only
                if fact.amount is None:
                    raise ValueError(f"CP-1 operand without an amount: {label}")
                if fact.unit != topic.unit:
                    raise ValueError(f"CP-1 operand unit {fact.unit} is not {topic.unit}: {label}")
                scales.add(fact.scale)
            if len(scales) > 1:
                raise ValueError(f"CP-1 operands of {topic.topic_id} differ in scale")

    def operand(self, topic: Topic, period: str) -> Fact:
        return self.cp1_facts[f"{QUARTERS[PERIODS.index(period)].column} · {topic.cp1_metric}"]


# --- the screening rule -------------------------------------------------------------------------


def _q38(value: Fraction) -> Decimal:
    if value == 0:
        return Decimal(0)
    with localcontext(_CTX):
        return Decimal(value.numerator) / Decimal(value.denominator)


@dataclass(frozen=True)
class TopicScreen:
    materiality: Materiality
    evidence: Literal["Complete", "Missing"]
    change: Decimal | None  # closing - starting, exact (one subtraction)
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
    if a == 0:
        rating: Materiality = "Stable" if change == 0 else "Material"
        return TopicScreen(rating, "Complete", _q38(change), "not_applicable", None, None, True)
    if abs(change) >= abs(a) * MATERIAL_AT:
        rating = "Material"
    elif abs(change) >= abs(a) * WATCH_AT:
        rating = "Watch"
    else:
        rating = "Stable"
    signed = change / abs(a)
    return TopicScreen(rating, "Complete", _q38(change), "known", _q38(signed), signed, False)


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

    def copied(self, field: str, label: str, cp1: Fact, twin: Fact) -> None:
        """The CP-1 value with its value_class, status, limitation, citations and calculation_id
        verbatim (lease :121); CP-1's formula is not copied (L10-c). Shown at 2 dp. An unsettled
        fact without a unit takes the unit (with its currency and scale) of the other end of the
        pair (ruling (f))."""
        known_money = cp1.status == "known" and cp1.unit == "MILLIONS"
        unit_of = twin if cp1.status != "known" and cp1.unit is None else cp1
        fact = Fact(
            fact_id=f"{self.table}.{self.row_id}.{field}",
            label=label,
            table_id=self.table,
            row_id=self.row_id,
            field=field,
            amount=cp1.amount,
            status=cp1.status,
            unit=unit_of.unit,
            currency=unit_of.currency,
            scale=unit_of.scale,
            decimals=2 if known_money else None,
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
    cells.copied("from_value", f"{t.label} · Starting value", r.start, r.close)
    cells.copied("to_value", f"{t.label} · Closing value", r.close, r.start)
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
    raw = json.dumps(submission) if isinstance(submission, Mapping) else submission
    try:
        return ChangeScreenSubmission.model_validate_json(raw)
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
        if not text.strip():
            issues.append(f"{path}: empty")
    return issues


def _overall_issues(overall: Overall) -> list[str]:
    """Step (5), in the L2 order: High, pairing, limitation required, limitation forbidden."""
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
    return issues


def _gap_issues(gaps: tuple[Gap, ...]) -> list[str]:
    """Step (6), per gap in order: topic, missing item, digits (field order), repeat."""
    issues: list[str] = []
    seen: set[tuple[str, str]] = set()
    for i, g in enumerate(gaps):
        path = f"gaps[{i}]"
        if g.affected_analysis not in (*TOPIC_IDS, OVERALL):
            issues.append(f"{path}.affected_analysis: must name a topic of the view or overall")
        if not g.gap.strip():
            issues.append(f"{path}.gap: empty")
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
