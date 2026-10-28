"""CP-2H (Ratings migration trigger): the Stage 1 calculation, pure over typed inputs.

`docs/CP2H-OWNER-LEASE.md` (frozen, preparation revision 2) fixes the Method. Python parses one
agency rating source (register, combined scale, published trigger terms; `parse_ratings`) and
tests every trigger term against CP-2G's settled T2H.6 credit metrics: the FY2025 headroom, the
forward headroom in FY2026-FY2028 in the base and downside cases, the tightest year, the first
year a trigger is reached, the trigger counts, and the notch difference and outlook match
between the agencies. The analyst gives a migration view per agency, an overall assessment and
gaps (judgment and references only). The oracle is `cases/cp2h-owner/expected.json`.

Arithmetic: every headroom is one subtraction in `model/_cells.CONTEXT` (38 digits,
ROUND_HALF_EVEN), the correctly rounded rational; a percent metric gives percentage points by
`.scaleb(2)` in that context, never by a multiplication. Zero, missing and not applicable stay
distinct: an unstated threshold makes its dependants missing with the root reason, an unsettled
CP-2G ratio passes its own status and reason on (round 7 (f)), and a CP-2G known zero stays a
known zero. The states no frozen case reaches follow LEAD round 7
(`docs/rulings/2026-10-28-stage1.md`).

The Stage 1 core does no I/O and touches no store, host, session or renderer. The Stage 2
section at the end connects it (G1-X protocol section 2): one store adapter (`cp2h_upstream`,
then `_adapted`) for submit, probe and view, the step validator, `RULES`, the exact
`read_inputs` view and the probe. CP-2H declares no reader of its own (lease Public API).
"""

import hashlib
import json
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import Field, TypeAdapter, ValidationError

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
    Contract,
    Fact,
    Hash,
    Input,
    InputStatus,
    Module,
    ReportTable,
    Run,
    RunText,
    Source,
    TableColumn,
    TableRow,
    Text,
)
from deploy_vii.contracts import Claim as ModuleClaim
from deploy_vii.execution import (
    Attempt,
    Execution,
    ExecutionSnapshot,
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
from deploy_vii.live.tools import Seen, unread_citation_issues
from deploy_vii.model._cells import CONTEXT
from deploy_vii.preparation import PreparedPack
from deploy_vii.readiness import citation_issues, shape_issues
from deploy_vii.report_view import fact_spelling, figure_unit
from deploy_workflow.owners.blank import is_blank
from deploy_workflow.owners.cp1a import probe_one_step
from deploy_workflow.owners.cp2g import cp2g_reader

MODULE_ID = "CP-2H"
STEP_ID = "rating_triggers"
SCHEMA_VERSION = "rating-triggers/1"
RATINGS_SOURCE_ID = "ratings"

# --- periods (fixed by the lease: CP-2G's twelve-month base and its three forecast years) -----
LTM_COLUMN = "LTM Q4 25 (2025-01-01 to 2025-12-31)"
LTM_PERIOD = "LTM Q4 25: 2025-01-01 to 2025-12-31"
BASE_YEAR = 2025
YEARS = (BASE_YEAR + 1, BASE_YEAR + 2, BASE_YEAR + 3)
FY = tuple(f"FY{y}" for y in YEARS)
FY_PERIOD = tuple(f"FY{y}: {y}-01-01 to {y}-12-31" for y in YEARS)
FY_SPAN = f"{FY[0]}-{FY[-1]}: {YEARS[0]}-01-01 to {YEARS[-1]}-12-31"
NOT_REACHED = f"Not reached by {FY[-1]}"
NOT_CALCULABLE = "Not calculable"
CASES = ("base", "down")
CASE_LABEL = {"base": "Base", "down": "Downside"}
CASE_ROWS = {"base": ("b26", "b27", "b28"), "down": ("d26", "d27", "d28")}
CP2G_ROWS = ("a25", *CASE_ROWS["base"], *CASE_ROWS["down"])
_ROW_PERIOD = {"a25": LTM_PERIOD} | {
    row: FY_PERIOD[k] for rows in CASE_ROWS.values() for k, row in enumerate(rows)
}

# --- the submission schema (lease "Submission schema"; reference and judgment only) -----------

View = Literal["Downgrade pressure", "Stable", "Upgrade potential", "Not assessable"]


class AgencyView(Contract):
    agency: str
    view: View
    category: Category
    confidence: Confidence
    rationale: str
    evidence: tuple[Citation, ...] = Field(min_length=1)
    limitation: str | None


class Overall(Contract):
    rationale: str
    category: Category
    confidence: Confidence
    limitation: str | None


class SynthesisGap(Contract):
    """As the CP-2G `SynthesisGap`."""

    gap: str
    why_it_matters: str
    affected_analysis: str
    severity: Severity
    action: str


class TriggerSubmission(Contract):
    views: tuple[AgencyView, ...] = Field(min_length=1)
    overall: Overall
    gaps: tuple[SynthesisGap, ...]


# --- outcomes that are not issues ---------------------------------------------------------------


class SourceIssue(ValueError):
    """An agency source the parse rule cannot read: the attempt's single issue (s01, s02;
    round 7 items 2, 3, 6, 8 and (h))."""


REGISTER_NOT_FOUND = "Rating register not found"
SCALE_NOT_FOUND = "Rating scale not found"
TERMS_NOT_FOUND = "Trigger terms not found"


# --- the agency source (manifest.json synthetic_source.parse_rule) ----------------------------

REGISTER_HEADER = "Agency  Instrument  Rating  Outlook  Date"
SCALE_HEADER = "Position  Alder Ratings  Brook Credit"
TERMS_HEADER = "Agency  Direction  Metric  Comparison  Threshold"
UNRATED = ("Withdrawn", "Not rated")
THRESHOLD_NOT_STATED = "Not stated"
Comparison = Literal["Above", "Below"]
Direction = Literal["Downgrade", "Upgrade"]
UnitKind = Literal["multiple", "percent"]
_FIELDS = re.compile(r"\s{2,}")
# The manifest parse rule: `N.NNx` (multiple) or `N.N%` (percent); any other form is refused
# (round 7 item 8; questions.md Q1).
_THRESHOLD = re.compile(r"[0-9]+\.[0-9]{2}x|[0-9]+\.[0-9]%")
_ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_PUBLISHED = re.compile(rf"Published ({'|'.join(_MONTHS)}) ([0-9]{{1,2}}), ([0-9]{{4}})\.")


@dataclass(frozen=True)
class Metric:
    """A source metric label's CP-2G T2H.6 field, unit class and CP-1 reported ratio."""

    field: str
    unit_class: UnitKind
    cp1_metric: str


METRICS: Mapping[str, Metric] = {
    "Total debt to EBITDA": Metric("total_leverage", "multiple", "total_leverage_reported"),
    "Net debt to EBITDA": Metric("net_leverage", "multiple", "net_leverage_reported"),
    "EBITDA to cash interest": Metric(
        "interest_coverage", "multiple", "interest_coverage_reported"
    ),
    "Free cash flow to total debt": Metric("fcf_to_debt", "percent", "fcf_to_debt"),
}
CP2G_FIELDS = tuple(m.field for m in METRICS.values())
CP1_METRICS = tuple(m.cp1_metric for m in METRICS.values())
_FIELD_UNIT = {
    m.field: "PERCENT" if m.unit_class == "percent" else "MULTIPLE" for m in METRICS.values()
}


@dataclass(frozen=True)
class RegisterRow:
    agency: str
    instrument: str
    rating: str
    outlook: str
    date: str
    position: int | None  # None: Withdrawn or Not rated (no position on the scale)
    line: str  # the page:1 register line
    scale_line: str | None  # the page:2 scale line that states the position


@dataclass(frozen=True)
class TriggerTerm:
    agency: str
    direction: Direction
    metric: str
    comparison: Comparison
    threshold_text: str
    threshold: Decimal | None  # a multiple, or a percent stored as a fraction; None: not stated
    line: str  # the page:3 terms line


@dataclass(frozen=True)
class RatingsSource:
    register: tuple[RegisterRow, ...]
    triggers: tuple[TriggerTerm, ...]
    register_published: str  # page:1's `Published ...` date (ISO), or a `PUBLICATION_*` state
    terms_published: str  # the same for page:3


def _fields(line: str) -> list[str]:
    return _FIELDS.split(line.strip())


@dataclass(frozen=True)
class _Rows:
    rows: list[tuple[str, list[str]]]
    # a line of two or more fields that is not the block's width (round 11 B2), or one after the
    # block's end (round 12 B8)
    breached: bool

    @property
    def empty(self) -> bool:
        """No row and no breach: reads as no header (s01, s02, round 7 item 3)."""
        return not self.rows and not self.breached


def _block(text: str, header: str, width: int) -> _Rows | None:
    """The lines of exactly `width` fields after the header line, up to a line of zero or one
    field (or the page end); a line of two or more fields of another count breaches the block
    (round 11 B2), and so does any later line of two or more fields on the page once the block
    has ended (round 12 B8), even right after the header. None without the header."""
    lines = text.split("\n")
    if header not in lines:
        return None
    rows: list[tuple[str, list[str]]] = []
    rest = lines[lines.index(header) + 1 :]
    for n, line in enumerate(rest):
        fields = _fields(line)
        if len(fields) != width:
            after = any(len(_fields(later)) > 1 for later in rest[n + 1 :])
            return _Rows(rows, breached=len(fields) > 1 or after)
        rows.append((line, fields))
    return _Rows(rows, breached=False)


PUBLICATION_NOT_STATED, PUBLICATION_UNCLEAR = "not stated", "unclear"


def _published(text: str) -> str:
    """The ISO date of the page's one `Published <Month D, YYYY>.` line; none is `not stated`,
    several or a date not on the calendar `unclear` (round 7 item 7, the D1 precedent)."""
    found = [m for line in text.split("\n") if (m := _PUBLISHED.fullmatch(line))]
    if not found:
        return PUBLICATION_NOT_STATED
    if len(found) > 1:
        return PUBLICATION_UNCLEAR
    month, day, year = found[0].groups()
    try:
        return date(int(year), _MONTHS.index(month) + 1, int(day)).isoformat()
    except ValueError:  # the month is valid by the pattern: a day off the month, or year 0
        return PUBLICATION_UNCLEAR


def exact_text(value: Decimal) -> str:
    """Canonical exact decimal: plain notation, no trailing zeros, unsigned zero."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def _canonical(value: Decimal) -> Decimal:
    return Decimal(exact_text(value))


def _calendar_date(text: str) -> bool:
    if not _ISO_DATE.fullmatch(text):
        return False
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True


def _scale(rows: list[tuple[str, list[str]]]) -> dict[str, dict[str, tuple[int, str]]]:
    """Each row a whole-number position (each position on one row) and one symbol per agency,
    each symbol once; any breach is `Rating scale not found` (round 7 item 8)."""
    agencies = _fields(SCALE_HEADER)[1:]
    positions: dict[str, dict[str, tuple[int, str]]] = {a: {} for a in agencies}
    seen: set[int] = set()
    for line, (position, *symbols) in rows:
        if not re.fullmatch(r"[0-9]+", position) or int(position) in seen:
            raise SourceIssue(SCALE_NOT_FOUND)
        seen.add(int(position))
        for agency, symbol in zip(agencies, symbols, strict=True):
            if symbol in positions[agency]:
                raise SourceIssue(SCALE_NOT_FOUND)
            positions[agency][symbol] = (int(position), line)
    return positions


def _register(
    rows: list[tuple[str, list[str]]], positions: Mapping[str, Mapping[str, tuple[int, str]]]
) -> tuple[RegisterRow, ...]:
    """Each row a calendar ISO date and an agency once (else `Rating register not found`,
    round 7 item 8); a rating that is neither unrated nor on the agency's scale is refused."""
    out: list[RegisterRow] = []
    for line, (agency, instrument, rating, outlook, dated) in rows:
        if not _calendar_date(dated) or any(r.agency == agency for r in out):
            raise SourceIssue(REGISTER_NOT_FOUND)
        if rating in UNRATED:
            out.append(RegisterRow(agency, instrument, rating, outlook, dated, None, line, None))
            continue
        placed = positions.get(agency, {}).get(rating)
        if placed is None:
            raise SourceIssue(clipped(("Rating not on the scale: ", agency, " ", rating)))
        position, scale_line = placed
        out.append(
            RegisterRow(agency, instrument, rating, outlook, dated, position, line, scale_line)
        )
    return tuple(out)


def _threshold(text: str, metric: Metric) -> Decimal | None:
    if text == THRESHOLD_NOT_STATED:
        return None
    if not _THRESHOLD.fullmatch(text) or (text[-1] == "x") != (metric.unit_class == "multiple"):
        raise SourceIssue(TERMS_NOT_FOUND)
    value = Decimal(text[:-1])
    if metric.unit_class == "percent":  # an exact exponent shift, no context rounds (Q2)
        sign, digits, exponent = value.as_tuple()
        value = Decimal((sign, digits, int(exponent) - 2))
    return _canonical(value)


def _terms(rows: list[tuple[str, list[str]]]) -> tuple[TriggerTerm, ...]:
    """Each row a known direction, metric, comparison and a threshold fitting the metric's
    unit, each (agency, direction, metric, comparison) once; a breach is `Trigger terms not
    found` (round 7 item 8), an unknown metric its own pinned text."""
    out: list[TriggerTerm] = []
    for line, (agency, direction, metric, comparison, threshold) in rows:
        if direction not in ("Downgrade", "Upgrade") or comparison not in ("Above", "Below"):
            raise SourceIssue(TERMS_NOT_FOUND)
        known = METRICS.get(metric)
        if known is None:
            raise SourceIssue(clipped(("Unrecognised trigger metric: ", metric)))
        term = TriggerTerm(
            agency=agency,
            direction="Downgrade" if direction == "Downgrade" else "Upgrade",
            metric=metric,
            comparison="Above" if comparison == "Above" else "Below",
            threshold_text=threshold,
            threshold=_threshold(threshold, known),
            line=line,
        )
        key = (agency, term.direction, metric, term.comparison)
        if any((t.agency, t.direction, t.metric, t.comparison) == key for t in out):
            raise SourceIssue(TERMS_NOT_FOUND)
        out.append(term)
    return tuple(out)


def _rows(block: _Rows, breach: str) -> list[tuple[str, list[str]]]:
    """A block's rows at its rows step; a breached block is invalid (round 11 B2, round 12 B8)."""
    if block.breached:
        raise SourceIssue(breach)
    return block.rows


def parse_ratings(pages: Sequence[str]) -> RatingsSource:
    """The parse rule: page:1 register, page:2 scale, page:3 trigger terms, each after its exact
    header line (consecutive lines of five, three and five fields split on two or more spaces).

    Every breach raises `SourceIssue` with one pinned text, the first in the round 7 item 8
    order: the register, scale and terms headers (an empty block reads as no header), the scale
    rows, the register rows, the terms rows (each with its block's breach, round 11 B2), then
    the agency rule (items 6 and (h)): every trigger agency is a rated register agency. An
    absent page reads as empty.
    """
    page = [pages[n] if n < len(pages) else "" for n in range(3)]
    register_block = _block(page[0], REGISTER_HEADER, 5)
    if register_block is None or register_block.empty:
        raise SourceIssue(REGISTER_NOT_FOUND)
    scale_block = _block(page[1], SCALE_HEADER, 3)
    if scale_block is None or scale_block.empty:
        raise SourceIssue(SCALE_NOT_FOUND)
    terms_block = _block(page[2], TERMS_HEADER, 5)
    if terms_block is None or terms_block.empty:
        raise SourceIssue(TERMS_NOT_FOUND)
    scale = _scale(_rows(scale_block, SCALE_NOT_FOUND))
    register = _register(_rows(register_block, REGISTER_NOT_FOUND), scale)
    triggers = _terms(_rows(terms_block, TERMS_NOT_FOUND))
    rated = {r.agency for r in register if r.position is not None}
    if any(t.agency not in rated for t in triggers):
        raise SourceIssue(TERMS_NOT_FOUND)
    return RatingsSource(
        register=register,
        triggers=triggers,
        register_published=_published(page[0]),
        terms_published=_published(page[2]),
    )


# --- arithmetic (lease "Decimal composer") ------------------------------------------------------


def headroom(
    *, comparison: Comparison, metric: Decimal, threshold: Decimal, unit_class: UnitKind
) -> Decimal:
    """Distance to the trigger: threshold - metric ("Above"), metric - threshold ("Below"); one
    subtraction in the 38-digit half-even context. A percent metric gives percentage points by
    `.scaleb(2)` in that context."""
    if comparison == "Above":
        raw = CONTEXT.subtract(threshold, metric)
    else:
        raw = CONTEXT.subtract(metric, threshold)
    return raw.scaleb(2, CONTEXT) if unit_class == "percent" else raw


def is_reached(*, comparison: Comparison, metric: Decimal, threshold: Decimal) -> bool:
    """Strict: metric > threshold ("Above"), metric < threshold ("Below"); equal is not reached."""
    return metric > threshold if comparison == "Above" else metric < threshold


def first_year(*, hits: Sequence[bool | None]) -> str:
    """The first forecast year a trigger is reached; a year not calculable (None) before it makes
    the answer unknowable; none reached and all calculable is `Not reached by FY2028`."""
    unknown = False
    for year, hit in zip(FY, hits, strict=True):
        if hit is None:
            unknown = True
        elif hit:
            return NOT_CALCULABLE if unknown else year
    return NOT_CALCULABLE if unknown else NOT_REACHED


# --- inputs ----------------------------------------------------------------------------------


def select_cp1(facts: Iterable[Fact]) -> dict[str, Fact]:
    """The four CP-1 reported ratios (manifest `cp1_fact_selection_rule`): the unique T4.10 fact
    labelled `LTM Q4 25 (...) · <metric>`; zero or several fail."""
    facts = tuple(facts)
    out: dict[str, Fact] = {}
    for metric in CP1_METRICS:
        label = f"{LTM_COLUMN} · {metric}"
        found = [f for f in facts if f.table_id == "T4.10" and f.label == label]
        if len(found) != 1:
            raise ValueError(f"CP-1 T4.10 needs exactly one fact labelled {label}")
        out[metric] = found[0]
    return out


@dataclass(frozen=True)
class Cp2gMetrics:
    """CP-2G's settled T2H.6 credit metrics: rows a25, b26-b28, d26-d28 x the four ratios (28
    facts, canonical order)."""

    facts: tuple[Fact, ...]

    def __post_init__(self) -> None:
        ids = [f"T2H.6.{row}.{field}" for row in CP2G_ROWS for field in CP2G_FIELDS]
        if [f.fact_id for f in self.facts] != ids:
            raise ValueError("CP-2G metrics must be the 28 T2H.6 facts in row and field order")
        for fact in self.facts:
            if fact.unit != _FIELD_UNIT[fact.field] or fact.period != _ROW_PERIOD[fact.row_id]:
                raise ValueError(f"CP-2G fact {fact.fact_id} has an unexpected unit or period")
            if fact.status not in ("known", "missing", "not_applicable"):
                raise ValueError(f"CP-2G fact {fact.fact_id} is {fact.status}")

    @classmethod
    def select(cls, facts: Iterable[Fact]) -> "Cp2gMetrics":
        """The 28 facts by literal id from a CP-2G head's facts; exactly one each."""
        facts = tuple(facts)
        chosen: list[Fact] = []
        for row in CP2G_ROWS:
            for field in CP2G_FIELDS:
                fact_id = f"T2H.6.{row}.{field}"
                found = [f for f in facts if f.fact_id == fact_id]
                if len(found) != 1:
                    raise ValueError(f"CP-2G head needs exactly one fact {fact_id}")
                chosen.append(found[0])
        return cls(facts=tuple(chosen))

    def fact(self, row: str, field: str) -> Fact:
        return self.facts[CP2G_ROWS.index(row) * len(CP2G_FIELDS) + CP2G_FIELDS.index(field)]


@dataclass(frozen=True)
class TriggerUpstream:
    """What the attempt binds: its inputs and the current ones (or the refusal text), CP-1's
    four reported ratios and CP-2G's 28 metrics. Every upstream status is its bound Input's
    (round 7 item 1, B5)."""

    bound: tuple[Input, ...]
    current: tuple[Input, ...] | str
    cp1_facts: tuple[Fact, ...]
    cp2g: Cp2gMetrics

    def __post_init__(self) -> None:
        select_cp1(self.cp1_facts)

    def status(self, input_id: str) -> InputStatus | None:
        """The bound Input's status; None when it is not bound."""
        return next((i.status for i in self.bound if i.input_id == input_id), None)

    def required_status(self, input_id: str) -> InputStatus:
        status = self.status(input_id)
        if status is None:
            raise ValueError(f"CP-2H: {input_id} is not bound")
        return status

    @property
    def cp1d_status(self) -> InputStatus | None:
        """The bound CP-1D Input's status; None when CP-1D is not bound (optional, never read)."""
        return self.status("CP-1D")


@dataclass(frozen=True)
class PackScope:
    """The part of the prepared pack the Method reads: the host-scope sources (the agency source
    has id `ratings`) and the issuer name (its digits are not figures)."""

    sources: tuple[Source, ...]
    names: tuple[str, ...]


@dataclass(frozen=True)
class TriggerInputs:
    pack: PackScope
    upstream: TriggerUpstream
    submission: TriggerSubmission


# --- outputs ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class Cell:
    """One table cell: the product Fact it settles as, its lineage and its display spelling."""

    fact: Fact
    derives_from: tuple[str, ...]
    shown: str | None  # report_view.fact_spelling of a known fact; None while unsettled

    def record(self) -> dict[str, object]:
        """Every field in the oracle's cell notation (`expected.json cell_notation`)."""
        f = self.fact
        return {
            "fact_id": f.fact_id,
            "table_id": f.table_id,
            "row_id": f.row_id,
            "field": f.field,
            "label": f.label,
            "status": f.status,
            "text": f.text,
            "unit": f.unit,
            "period": f.period,
            "amount_exact": None if f.amount is None else exact_text(f.amount),
            "shown": self.shown,
            "decimals": f.decimals,
            "value_class": f.value_class,
            "formula": f.formula,
            "calculation_id": f.calculation_id,
            "derives_from": list(self.derives_from),
            "citations": [c.model_dump() for c in f.citations],
            "limitation": f.limitation,
        }


@dataclass(frozen=True)
class Cp1Reference:
    """A `cp1_references` row: a CP-1 reported ratio named in prose or compared in T2R.4."""

    row_id: str
    figure: str | None  # the metric when a prose figure names it
    fact: Fact  # the CP-1 fact, verbatim

    @property
    def label(self) -> str:
        return f"{self.fact.label} · {self.fact.period}"


@dataclass(frozen=True)
class Cp2gReference:
    """A `cp2g_references` row: a CP-2G T2H.6 fact the trigger tests read, verbatim."""

    row_id: str
    fact: Fact


@dataclass(frozen=True)
class ClaimDraft:
    """A claim: run text with `{fact_id|unit}` figures and `[fact_id]` chips."""

    claim_id: str
    text: str
    limitation: str | None
    citations: tuple[Citation, ...]  # the analyst's evidence; () for a Python template
    cp1_references: tuple[str, ...]  # CP-1 fact ids the text names as figures


@dataclass(frozen=True)
class CaseOutcome:
    headroom: tuple[Decimal | None, ...]  # FY2026-FY2028
    hits: tuple[bool | None, ...]
    first: str


@dataclass(frozen=True)
class TriggerOutcome:
    row: str
    fy25_headroom: Decimal | None
    fy25_reached: bool | None
    base: CaseOutcome
    down: CaseOutcome


@dataclass(frozen=True)
class TriggerReport:
    source: RatingsSource
    cells: tuple[Cell, ...]
    tables: tuple[ReportTable, ...]
    cp1_references: tuple[Cp1Reference, ...]
    cp2g_references: tuple[Cp2gReference, ...]
    claims: tuple[ClaimDraft, ...]
    own_limitations: tuple[str, ...]
    outcomes: tuple[TriggerOutcome, ...]
    totals: Mapping[str, tuple[str, ...]]  # trigger rows per count of T2R.9

    @property
    def facts(self) -> tuple[Fact, ...]:
        return tuple(c.fact for c in self.cells)


TABLES = {
    "T2R.1": "Upstream register",
    "T2R.2": "Agency rating register",
    "T2R.3": "Published trigger terms",
    "T2R.4": "Current trigger headroom",
    "T2R.5": "Forward trigger headroom",
    "T2R.6": "Trigger timing",
    "T2R.7": "Migration assessment",
    "T2R.8": "Agency divergence",
    "T2R.9": "Trigger summary",
    "T2R.10": "Gaps ledger",
}
# The two non-methodology module tables (the `cp1_references` precedent): id, title, row header.
CP1_REFERENCES = (
    "cp1_references",
    "CP-1 facts referenced in CP-2H text and compared in T2R.4",
    "CP-1 fact",
)
CP2G_REFERENCES = (
    "cp2g_references",
    "CP-2G facts read by CP-2H (T2H.6 credit metrics)",
    "CP-2G fact",
)
FORECAST_LIMITATION = (
    "Forward headroom rests on CP-2G's forecast, which uses analyst-assumed drivers"
)
THRESHOLD_NS = "Not calculable: the trigger threshold is not stated in the agency source"
THRESHOLD_UNSTATED = "The trigger threshold is not stated in the agency source"
_UNITS = {"multiple": "MULTIPLE", "percent": "PERCENT"}
NOTCH_UNIT, POSITION_UNIT, COUNT_UNIT = "notches", "scale position", "triggers"
# The tables that may have zero rows (round 7 items 4, 5; the CP-2A T2B.7 precedent).
FIXED_COLUMNS: Mapping[str, tuple[TableColumn, ...]] = {
    "T2R.8": (
        TableColumn(field="first_agency", label="First agency"),
        TableColumn(field="second_agency", label="Second agency"),
        TableColumn(field="notches", label="Notches apart"),
        TableColumn(field="lower_rated", label="Lower rated"),
        TableColumn(field="outlook_match", label="Outlooks"),
    ),
    "T2R.10": (
        TableColumn(field="id", label="Gap id"),
        TableColumn(field="gap", label="Gap"),
        TableColumn(field="why_it_matters", label="Why it matters"),
        TableColumn(field="affected_analysis", label="Affected analysis"),
        TableColumn(field="severity", label="Severity"),
        TableColumn(field="action", label="Action"),
    ),
}
Status = Literal["known", "missing", "not_applicable"]


class _Book:
    """The module's cells in table, row and field order, and each table's rows."""

    def __init__(self, sha256: str) -> None:
        self.sha256 = sha256
        self.cells: list[Cell] = []
        self.by_id: dict[str, Cell] = {}
        self.rows: dict[str, list[TableRow]] = {t: [] for t in TABLES}

    def cite(self, locator: str, quote: str) -> Citation:
        return Citation(
            source_id=RATINGS_SOURCE_ID, source_sha256=self.sha256, locator=locator, quote=quote
        )

    def _add(self, fact: Fact, derives: Sequence[str]) -> None:
        if fact.fact_id in self.by_id:
            raise ValueError(f"CP-2H: duplicate fact {fact.fact_id}")
        shown = fact_spelling(fact, None)[2] if fact.status == "known" else None
        cell = Cell(fact=fact, derives_from=tuple(derives), shown=shown)
        self.cells.append(cell)
        self.by_id[fact.fact_id] = cell

    def lineage(self, derives: Sequence[str], own: Sequence[Citation] = ()) -> tuple[Citation, ...]:
        """Own citations, then those of each own derived fact, ordered and de-duplicated; the
        `cp1:`/`cp2g:` facts' citations are appended at run time. A known fact never derives
        from an unsettled fact."""
        out = list(own)
        for ref in derives:
            if ref.startswith(("cp1:", "cp2g:")):
                continue
            cell = self.by_id[ref]
            if cell.fact.status != "known":
                raise ValueError(f"CP-2H: a known fact derives from the unsettled fact {ref}")
            out += cell.fact.citations
        return tuple(dict.fromkeys(out))

    def number(
        self,
        at: tuple[str, str, str],
        label: str,
        value: Decimal,
        unit: str,
        formula: str,
        *,
        period: str,
        source: bool = False,
        derives: Sequence[str] = (),
        citations: Sequence[Citation] = (),
    ) -> None:
        table, row, field = at
        fact_id = f"{table}.{row}.{field}"
        derives = () if source else tuple(derives)
        fact = Fact(
            fact_id=fact_id,
            label=label,
            table_id=table,
            row_id=row,
            field=field,
            amount=_canonical(value),
            unit=_UNITS.get(unit, unit),
            period=period,
            citations=self.lineage(derives, citations),
            calculation_id=None if source else f"calc:{fact_id}",
            value_class="source" if source else "calculated",
            formula=formula,
        )
        self._add(fact, derives)

    def unsettled(
        self,
        at: tuple[str, str, str],
        label: str,
        unit: str,
        reason: str,
        *,
        period: str,
        status: Literal["missing", "not_applicable"] = "missing",
    ) -> None:
        """A numeric cell that is not known; it carries its settled twin's unit."""
        table, row, field = at
        fact = Fact(
            fact_id=f"{table}.{row}.{field}",
            label=label,
            table_id=table,
            row_id=row,
            field=field,
            status=status,
            unit=_UNITS.get(unit, unit),
            period=period,
            limitation=reason,
        )
        self._add(fact, ())

    def text(
        self,
        at: tuple[str, str, str],
        label: str,
        value: str,
        *,
        value_class: Literal["source", "analyst_judgment"] | None = None,
        derives: Sequence[str] = (),
        citations: Sequence[Citation] = (),
    ) -> None:
        table, row, field = at
        fact = Fact(
            fact_id=f"{table}.{row}.{field}",
            label=label,
            table_id=table,
            row_id=row,
            field=field,
            text=value,
            value_class=value_class,
            citations=self.lineage(derives, citations),
        )
        self._add(fact, derives)

    def missing_text(
        self,
        at: tuple[str, str, str],
        label: str,
        reason: str,
        *,
        status: Literal["missing", "not_applicable"] = "missing",
    ) -> None:
        """A text cell that cannot be settled: unsettled with its root reason, never a text."""
        table, row, field = at
        fact = Fact(
            fact_id=f"{table}.{row}.{field}",
            label=label,
            table_id=table,
            row_id=row,
            field=field,
            status=status,
            limitation=reason,
        )
        self._add(fact, ())

    def row(self, table: str, row_id: str, label: str, fields: Sequence[str]) -> None:
        ids = tuple(f"{table}.{row_id}.{f}" for f in fields)
        for fact_id in ids:
            if fact_id not in self.by_id:
                raise ValueError(f"CP-2H: row {table}.{row_id} names no fact {fact_id}")
        self.rows[table].append(TableRow(row_id=row_id, label=label, fact_ids=ids))

    def status(self, fact_id: str) -> str:
        return self.by_id[fact_id].fact.status

    def ref(self, fact_id: str, token: str) -> str:
        return (
            "{" + fact_id + "|" + token + "}" if self.status(fact_id) == "known" else f"[{fact_id}]"
        )

    def tables(self) -> tuple[ReportTable, ...]:
        out: list[ReportTable] = []
        for table, title in TABLES.items():
            rows = self.rows[table]
            if table in FIXED_COLUMNS:
                columns = FIXED_COLUMNS[table]
            elif rows:
                first = [self.by_id[fact_id].fact for fact_id in rows[0].fact_ids]
                columns = tuple(TableColumn(field=f.field, label=f.label) for f in first)
            else:
                raise ValueError(f"CP-2H: {table} has no row to take its columns from")
            out.append(ReportTable(table_id=table, title=title, columns=columns, rows=tuple(rows)))
        return tuple(out)


# --- composition -------------------------------------------------------------------------------


def _upstream_register(b: _Book, up: TriggerUpstream) -> None:
    rows = (
        (
            "u_cp1",
            "CP-1",
            up.required_status("CP-1"),
            f"Base period {LTM_PERIOD}",
            "T4.10 reported leverage, coverage and free cash flow to debt",
            "Inherits CP-1's own limitations.",
        ),
        (
            "u_cp2g",
            "CP-2G",
            up.required_status("CP-2G"),
            f"Forecast {FY[0]}-{FY[-1]} on the base period {LTM_PERIOD}",
            "T2H.6 credit metrics for the FY2025 actual, base case and downside case",
            "Forecast on analyst-assumed drivers.",
        ),
        (
            "u_cp1d",
            "CP-1D",
            up.cp1d_status or "not part of this run",  # round 7 item 1: the bound status
            "Not applicable",
            "Nothing read",
            "CP-1D (earnings quality) is an optional input that this version never reads.",
        ),
    )
    for row, *values in rows:
        names = ("module", "status", "basis", "read", "limitation")
        labels = ("Module", "Status", "Basis", "Read", "Limitation")
        for name, label, value in zip(names, labels, values, strict=True):
            b.text(("T2R.1", row, name), label, value)
        b.row("T2R.1", row, values[0], names)


def _agency_register(b: _Book, source: RatingsSource) -> dict[str, str]:
    """T2R.2 source facts; the row id of each agency."""
    rows: dict[str, str] = {}
    for n, r in enumerate(source.register, 1):
        row = f"r{n:02d}"
        rows[r.agency] = row
        line = (b.cite("page:1", r.line),)
        for name, label, value in (
            ("agency", "Agency", r.agency),
            ("instrument", "Instrument", r.instrument),
            ("rating", "Rating", r.rating),
            ("outlook", "Outlook", r.outlook),
            ("date", "Rating date", r.date),
        ):
            b.text(("T2R.2", row, name), label, value, value_class="source", citations=line)
        at, label, period = (
            ("T2R.2", row, "position"),
            "Position on the combined scale",
            f"Rating dated {r.date}",
        )
        if r.position is None or r.scale_line is None:
            reason = (
                f"{r.agency}'s rating is {r.rating.lower()}, so it has no position on the scale"
            )
            b.unsettled(at, label, POSITION_UNIT, reason, period=period, status="not_applicable")
        else:
            b.number(
                at,
                label,
                Decimal(r.position),
                POSITION_UNIT,
                "scale position stated in the source mapping",
                period=period,
                source=True,
                citations=(b.cite("page:2", r.scale_line),),
            )
        b.row(
            "T2R.2",
            row,
            r.agency,
            ("agency", "instrument", "rating", "outlook", "date", "position"),
        )
    return rows


_UNDATED = (PUBLICATION_NOT_STATED, PUBLICATION_UNCLEAR)


def _terms_period(source: RatingsSource) -> str:
    published = source.terms_published
    if published in _UNDATED:  # round 7 item 7
        return f"Terms publication date {published}, tested at each fiscal year end"
    return f"Terms published {published}, tested at each fiscal year end"


def _trigger_terms(b: _Book, source: RatingsSource) -> list[tuple[str, TriggerTerm]]:
    period = _terms_period(source)
    out: list[tuple[str, TriggerTerm]] = []
    for n, t in enumerate(source.triggers, 1):
        row = f"t{n:02d}"
        line = (b.cite("page:3", t.line),)
        for name, label, value in (
            ("agency", "Agency", t.agency),
            ("direction", "Direction", t.direction),
            ("metric", "Metric", t.metric),
            ("comparison", "Comparison", t.comparison),
        ):
            b.text(("T2R.3", row, name), label, value, value_class="source", citations=line)
        unit = METRICS[t.metric].unit_class
        at = ("T2R.3", row, "threshold")
        if t.threshold is None:
            b.unsettled(at, "Threshold", unit, THRESHOLD_UNSTATED, period=period)
        else:
            b.number(
                at,
                "Threshold",
                t.threshold,
                unit,
                "threshold stated in the agency source",
                period=period,
                source=True,
                citations=line,
            )
        b.row(
            "T2R.3",
            row,
            _trigger_label(t),
            ("agency", "direction", "metric", "comparison", "threshold"),
        )
        out.append((row, t))
    return out


def _trigger_label(t: TriggerTerm) -> str:
    return f"{t.agency} {t.direction.lower()}: {t.metric}"


def _copy_status(fact: Fact) -> Literal["missing", "not_applicable"]:
    """An unsettled upstream copy keeps the upstream status (ruling G-decisions, L10-c)."""
    if fact.status == "not_applicable":
        return "not_applicable"
    if fact.status == "missing":
        return "missing"
    raise ValueError(f"CP-2H: CP-2G fact {fact.fact_id} is {fact.status}")


def _reason(fact: Fact) -> str:
    if not fact.limitation:
        raise ValueError(f"CP-2H: unsettled CP-2G fact {fact.fact_id} has no limitation")
    return fact.limitation


@dataclass(frozen=True)
class _Test:
    """One trigger term read against the CP-2G metric it names."""

    row: str
    term: TriggerTerm
    metric: Metric

    @property
    def threshold_id(self) -> str:
        return f"T2R.3.{self.row}.threshold"

    @property
    def unit(self) -> str:
        return "pp" if self.metric.unit_class == "percent" else "multiple"

    @property
    def formula(self) -> str:
        base = "(threshold - metric)" if self.term.comparison == "Above" else "(metric - threshold)"
        return base + (" x 100, percentage points" if self.metric.unit_class == "percent" else "")

    def reason(self, fact: Fact) -> tuple[str, Literal["missing", "not_applicable"]] | None:
        """Why the headroom on this CP-2G fact is not calculable, and the status it takes:
        threshold first (missing); else the CP-2G fact's own reason and status (round 7 (f))."""
        if self.term.threshold is None:
            return THRESHOLD_NS, "missing"
        return None if fact.status == "known" else (_reason(fact), _copy_status(fact))

    def headroom(self, fact: Fact) -> tuple[Decimal, bool]:
        threshold, value = self.term.threshold, fact.amount
        if threshold is None or value is None:
            raise ValueError(f"CP-2H: {self.row} has no threshold or metric to test")
        comparison = self.term.comparison
        return (
            headroom(
                comparison=comparison,
                metric=value,
                threshold=threshold,
                unit_class=self.metric.unit_class,
            ),
            is_reached(comparison=comparison, metric=value, threshold=threshold),
        )


def _current(b: _Book, up: TriggerUpstream, test: _Test) -> tuple[Decimal | None, bool | None]:
    """T2R.4: the FY2025 actual (an own copy of CP-2G a25), headroom, status and CP-1 check."""
    row, field = test.row, test.metric.field
    at = ("T2R.4", row)
    actual_id = f"T2R.4.{row}.actual"
    a25 = up.cp2g.fact("a25", field)
    b.text((*at, "metric"), "Metric", test.term.metric, derives=(f"T2R.3.{row}.metric",))
    if a25.status == "known" and a25.amount is not None:
        b.number(
            (*at, "actual"),
            "FY2025 actual",
            a25.amount,
            test.metric.unit_class,
            f"Copy of CP-2G {a25.fact_id}",
            period=LTM_PERIOD,
            derives=(f"cp2g:{a25.fact_id}",),
        )
    else:
        b.unsettled(
            (*at, "actual"),
            "FY2025 actual",
            test.metric.unit_class,
            _reason(a25),
            period=LTM_PERIOD,
            status=_copy_status(a25),
        )
    unsettled = test.reason(a25)
    value: Decimal | None = None
    reached: bool | None = None
    if unsettled is None:
        value, reached = test.headroom(a25)
        derives = (actual_id, test.threshold_id)
        b.number(
            (*at, "headroom"),
            "Headroom to the trigger",
            value,
            test.unit,
            test.formula,
            period=LTM_PERIOD,
            derives=derives,
        )
        b.text((*at, "status"), "Status", "Reached" if reached else "Not reached", derives=derives)
    else:
        reason, status = unsettled
        b.unsettled(
            (*at, "headroom"),
            "Headroom to the trigger",
            test.unit,
            reason,
            period=LTM_PERIOD,
            status=status,
        )
        b.missing_text((*at, "status"), "Status", reason, status=status)
    cp1 = select_cp1(up.cp1_facts)[test.metric.cp1_metric]
    if a25.status == "known" and cp1.status == "known" and cp1.amount is not None:
        check = "Reconciled to CP-1" if a25.amount == cp1.amount else "Differs from CP-1"
        b.text((*at, "check"), "Check", check, derives=(actual_id, f"cp1:{test.metric.cp1_metric}"))
    else:
        b.text((*at, "check"), "Check", "Not compared")
    b.row(
        "T2R.4", row, _trigger_label(test.term), ("metric", "actual", "headroom", "status", "check")
    )
    return value, reached


def _forward(b: _Book, up: TriggerUpstream, test: _Test, case: str) -> CaseOutcome:
    """T2R.5: one case's three yearly headrooms, the tightest and its year."""
    rid = f"{test.row}_{case}"
    values: list[Decimal | None] = []
    hits: list[bool | None] = []
    whys: list[tuple[str, Literal["missing", "not_applicable"]]] = []
    for k, row in enumerate(CASE_ROWS[case]):
        fact = up.cp2g.fact(row, test.metric.field)
        at = ("T2R.5", rid, f"y{k + 1}")
        why = test.reason(fact)
        value: Decimal | None = None
        hit: bool | None = None
        if why is None:
            value, hit = test.headroom(fact)
            derives = (f"cp2g:{fact.fact_id}", test.threshold_id)
            b.number(
                at, FY[k], value, test.unit, test.formula, period=FY_PERIOD[k], derives=derives
            )
        else:
            b.unsettled(at, FY[k], test.unit, why[0], period=FY_PERIOD[k], status=why[1])
            whys.append(why)
        values.append(value)
        hits.append(hit)
    years = tuple(f"T2R.5.{rid}.y{k + 1}" for k in range(3))
    known = [v for v in values if v is not None]
    if len(known) == len(values):
        tight = min(known)
        b.number(
            ("T2R.5", rid, "tightest"),
            "Tightest headroom",
            tight,
            test.unit,
            "lowest of the three forecast years",
            period=FY_SPAN,
            derives=years,
        )
        b.text(
            ("T2R.5", rid, "tightest_year"), "Tightest year", FY[known.index(tight)], derives=years
        )
    else:  # the first unsettled year's reason and status (round 7 (f))
        why_t, status = whys[0]
        b.unsettled(
            ("T2R.5", rid, "tightest"),
            "Tightest headroom",
            test.unit,
            why_t,
            period=FY_SPAN,
            status=status,
        )
        b.missing_text(("T2R.5", rid, "tightest_year"), "Tightest year", why_t, status=status)
    b.row(
        "T2R.5",
        rid,
        f"{test.term.agency} {test.term.metric}, {CASE_LABEL[case].lower()} case",
        ("y1", "y2", "y3", "tightest", "tightest_year"),
    )
    return CaseOutcome(headroom=tuple(values), hits=tuple(hits), first=first_year(hits=hits))


def _timing(
    b: _Book, up: TriggerUpstream, test: _Test, outcomes: Mapping[str, CaseOutcome]
) -> None:
    """T2R.6: the trigger and the first year reached in each case."""
    row, t = test.row, test.term
    desc = f"{_trigger_label(t)} {t.comparison.lower()} its threshold"
    b.text(
        ("T2R.6", row, "trigger"),
        "Trigger",
        desc,
        derives=tuple(f"T2R.3.{row}.{f}" for f in ("agency", "direction", "metric", "comparison")),
    )
    for case in CASES:
        at, label = (
            ("T2R.6", row, f"{case}_first"),
            f"First year reached, {CASE_LABEL[case].lower()} case",
        )
        facts = [up.cp2g.fact(r, test.metric.field) for r in CASE_ROWS[case]]
        outcome = outcomes[case]
        if outcome.first != NOT_CALCULABLE:
            derives = (test.threshold_id, *(f"cp2g:{f.fact_id}" for f in facts))
            b.text(at, label, outcome.first, derives=derives)
            continue
        unknown = next(f for f, h in zip(facts, outcome.hits, strict=True) if h is None)
        why = test.reason(unknown)
        if why is None:
            raise ValueError(f"CP-2H: {at} is not calculable without a reason")
        b.missing_text(at, label, why[0])  # stays missing, whatever the year's status (round 7 (f))
    b.row("T2R.6", row, desc, ("trigger", "base_first", "down_first"))


def _divergence(b: _Book, source: RatingsSource, rows: Mapping[str, str]) -> list[str]:
    """T2R.8: every pair of register agencies (none for a one-agency register, round 7 item 4);
    the pair row ids."""
    published = source.register_published
    if published in _UNDATED:  # round 7 item 7
        period = f"As of the rating register, publication date {published}"
    else:
        period = f"As of {published}"
    register = source.register
    pairs = [
        (register[i], register[j])
        for i in range(len(register))
        for j in range(i + 1, len(register))
    ]
    out: list[str] = []
    for n, (ra, rb) in enumerate(pairs, 1):
        row, ia, ib = f"p{n:02d}", rows[ra.agency], rows[rb.agency]
        at = ("T2R.8", row)
        b.text((*at, "first_agency"), "First agency", ra.agency, derives=(f"T2R.2.{ia}.agency",))
        b.text((*at, "second_agency"), "Second agency", rb.agency, derives=(f"T2R.2.{ib}.agency",))
        if ra.position is None or rb.position is None:
            who = ra if ra.position is None else rb
            why = f"{who.agency}'s rating is {who.rating.lower()}, so no notch comparison is made"
            b.unsettled(
                (*at, "notches"),
                "Notches apart",
                NOTCH_UNIT,
                why,
                period=period,
                status="not_applicable",
            )
            b.missing_text((*at, "lower_rated"), "Lower rated", why, status="not_applicable")
            b.missing_text((*at, "outlook_match"), "Outlooks", why, status="not_applicable")
        else:
            positions = (f"T2R.2.{ia}.position", f"T2R.2.{ib}.position")
            b.number(
                (*at, "notches"),
                "Notches apart",
                Decimal(abs(ra.position - rb.position)),
                NOTCH_UNIT,
                "absolute difference of the two positions on the combined scale",
                period=period,
                derives=positions,
            )
            if ra.position == rb.position:
                lower = "Same rating"
            else:
                lower = ra.agency if ra.position > rb.position else rb.agency
            b.text(
                (*at, "lower_rated"),
                "Lower rated",
                lower,
                derives=(*positions, f"T2R.2.{ia}.agency", f"T2R.2.{ib}.agency"),
            )
            b.text(
                (*at, "outlook_match"),
                "Outlooks",
                "Same" if ra.outlook == rb.outlook else "Different",
                derives=(f"T2R.2.{ia}.outlook", f"T2R.2.{ib}.outlook"),
            )
        b.row(
            "T2R.8",
            row,
            f"{ra.agency} and {rb.agency}",
            ("first_agency", "second_agency", "notches", "lower_rated", "outlook_match"),
        )
        out.append(row)
    return out


_COUNTS = (
    ("downgrade_base", "Downgrade", "base", "Downgrade triggers reached, base case"),
    ("downgrade_down", "Downgrade", "down", "Downgrade triggers reached, downside case"),
    ("upgrade_base", "Upgrade", "base", "Upgrade triggers reached, base case"),
    ("upgrade_down", "Upgrade", "down", "Upgrade triggers reached, downside case"),
)


def _summary(
    b: _Book, tests: Sequence[_Test], outcomes: Mapping[str, TriggerOutcome]
) -> dict[str, tuple[str, ...]]:
    """T2R.9, one totals row: triggers tested, reached counts and not-calculable counts."""

    def case_of(o: TriggerOutcome, case: str) -> CaseOutcome:
        return o.base if case == "base" else o.down

    totals: dict[str, tuple[str, ...]] = {}
    at = ("T2R.9", "total")
    b.number(
        (*at, "triggers"),
        "Triggers tested",
        Decimal(len(tests)),
        COUNT_UNIT,
        "count of published trigger terms",
        period=FY_SPAN,
        derives=tuple(f"T2R.3.{t.row}.direction" for t in tests),
    )
    for key, direction, case, label in _COUNTS:
        rows = tuple(
            t.row
            for t in tests
            if t.term.direction == direction and case_of(outcomes[t.row], case).first in FY
        )
        totals[key] = rows
        b.number(
            (*at, key),
            label,
            Decimal(len(rows)),
            COUNT_UNIT,
            "count of triggers with a first year reached",
            period=FY_SPAN,
            derives=tuple(f"T2R.6.{r}.{case}_first" for r in rows),
        )
    for case in CASES:
        rows = tuple(t.row for t in tests if case_of(outcomes[t.row], case).first == NOT_CALCULABLE)
        totals[f"not_calculable_{case}"] = rows
        lab = CASE_LABEL[case].lower()
        b.number(
            (*at, f"not_calculable_{case}"),
            f"Triggers not calculable, {lab} case",
            Decimal(len(rows)),
            COUNT_UNIT,
            f"count of triggers whose {lab}-case first-year result is missing",
            period=FY_SPAN,
            derives=tuple(f"T2R.3.{r}.direction" for r in rows),
        )
    b.row(
        "T2R.9",
        "total",
        "All triggers",
        (
            "triggers",
            "downgrade_base",
            "downgrade_down",
            "upgrade_base",
            "upgrade_down",
            "not_calculable_base",
            "not_calculable_down",
        ),
    )
    return totals


@dataclass(frozen=True)
class _Mechanics:
    """Everything that follows from the agency source and the upstream facts alone."""

    tests: tuple[_Test, ...]
    outcomes: tuple[TriggerOutcome, ...]
    agency_rows: Mapping[str, str]
    pairs: tuple[str, ...]
    totals: Mapping[str, tuple[str, ...]]


def _migration(b: _Book, views: Sequence[AgencyView], agency_rows: Mapping[str, str]) -> None:
    """T2R.7: the analyst's view and confidence per agency, register order."""
    for n, v in enumerate(views, 1):
        row = f"a{n:02d}"
        b.text(
            ("T2R.7", row, "agency"),
            "Agency",
            v.agency,
            derives=(f"T2R.2.{agency_rows[v.agency]}.agency",),
        )
        b.text(("T2R.7", row, "view"), "Migration view", v.view, value_class="analyst_judgment")
        b.text(
            ("T2R.7", row, "confidence"), "Confidence", v.confidence, value_class="analyst_judgment"
        )
        b.row("T2R.7", row, v.agency, ("agency", "view", "confidence"))


def _gaps(b: _Book, gaps: Sequence[SynthesisGap]) -> None:
    for n, g in enumerate(gaps, 1):
        row = f"g{n:02d}"
        b.text(("T2R.10", row, "id"), "Gap id", f"CP-2H-GAP-{n:03d}")
        for name, label in (
            ("gap", "Gap"),
            ("why_it_matters", "Why it matters"),
            ("affected_analysis", "Affected analysis"),
        ):
            b.text(("T2R.10", row, name), label, getattr(g, name), value_class="analyst_judgment")
        b.text(("T2R.10", row, "severity"), "Severity", g.severity)
        b.text(("T2R.10", row, "action"), "Action", g.action, value_class="analyst_judgment")
        b.row(
            "T2R.10",
            row,
            f"Gap {n}",
            ("id", "gap", "why_it_matters", "affected_analysis", "severity", "action"),
        )


def _compose(
    ratings: Source,
    source: RatingsSource,
    up: TriggerUpstream,
    submission: TriggerSubmission | None,
) -> tuple[_Book, _Mechanics]:
    """All tables in fact order (T2R.1-T2R.3, then T2R.4-T2R.6 per trigger, T2R.7-T2R.10).
    Without a submission the analyst tables T2R.7 and T2R.10 are left out (validation)."""
    if ratings.sha256 is None:
        raise ValueError("CP-2H: the ratings source has no sha256")
    b = _Book(ratings.sha256)
    _upstream_register(b, up)
    agency_rows = _agency_register(b, source)
    tests = tuple(_Test(row, t, METRICS[t.metric]) for row, t in _trigger_terms(b, source))
    outcomes: dict[str, TriggerOutcome] = {}
    for test in tests:
        fy25, reached = _current(b, up, test)
        cases = {case: _forward(b, up, test, case) for case in CASES}
        _timing(b, up, test, cases)
        outcomes[test.row] = TriggerOutcome(test.row, fy25, reached, cases["base"], cases["down"])
    if submission is not None:
        _migration(b, _register_order(submission.views, source), agency_rows)
    pairs = tuple(_divergence(b, source, agency_rows))
    totals = _summary(b, tests, outcomes)
    if submission is not None:
        _gaps(b, submission.gaps)
    mechanics = _Mechanics(tests, tuple(outcomes.values()), agency_rows, pairs, totals)
    return b, mechanics


def _register_order(views: Sequence[AgencyView], source: RatingsSource) -> list[AgencyView]:
    """The views of a valid submission in register order (expected.json id_rules: T2R.7)."""
    by_agency = {v.agency: v for v in views}
    return [by_agency[r.agency] for r in source.register]


# --- validation (lease "Refusals") ----------------------------------------------------------------

HIGH = "High is not allowed: forward headroom rests on analyst-assumed drivers"
CORE_PHRASES: Mapping[str, tuple[str, ...]] = {
    "rating call": (
        "will be downgraded",
        "will be upgraded",
        "will downgrade",
        "will upgrade",
        "is certain to be",
        "our rating",
        "we rate",
        "shadow rating",
        "implied rating",
    ),
    "probability weighting": (
        "probability-weighted",
        "probability weighted",
        "weighted by probability",
        "expected value",
        "likelihood-weighted",
    ),
}


def phrase_issues(path: str, text: str) -> tuple[str, ...]:
    """The phrase guard (not a semantic check): CP-1A's default prohibited kinds, then the
    core-local rating-call and probability-weighting phrases, case-insensitive, each quoted as
    listed (as `prohibited_issues` quotes)."""
    low = text.lower()
    core = (
        f'{path}: prohibited conclusion ({kind}): "{phrase}"'
        for kind, phrases in CORE_PHRASES.items()
        for phrase in phrases
        if phrase in low
    )
    return (*prohibited_issues(path, text), *core)


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


def _prose(
    path: str,
    text: str,
    bound: Mapping[str, Fact],
    names: Sequence[str],
    *,
    claim: bool = False,
) -> list[str]:
    """A rationale or gap field: run text against the bound facts, then the phrase guard. A
    `prose.issues` line can quote the analyst's text, so it is clipped (protocol section 6).
    `claim`: the text becomes `Claim.text`, so when `prose.issues` passes it, it is also checked
    as `RunText`."""
    if is_blank(text):
        return [f"{path}: empty text"]
    found = prose.issues(text, bound, names=names)
    issues = [clipped((path, ": ", issue)) for issue in found]
    if claim and not found:
        issues += _run_text_issues(path, text)
    return [*issues, *phrase_issues(path, text)]


def _limitation(path: str, text: str | None, names: Sequence[str]) -> list[str]:
    """A view or overall limitation (plain text, `Claim.limitation`): no reference resolves in
    it, so a figure or reference is refused; then the phrase guard (round 7 (d), CP-2A A3)."""
    if text is None:
        return []
    if is_blank(text):  # round 11 B3, round 12 B10: a blank limitation is not a limitation
        return [f"{path}: empty text"]
    return [
        *(clipped((path, ": ", x)) for x in prose.check(text, refs=(), gaps=(), names=names)),
        *phrase_issues(path, text),
    ]


def _view_issues(
    sub: TriggerSubmission, source: RatingsSource, bound: Mapping[str, Fact], pack: PackScope
) -> list[str]:
    """Views in register order (unknown agencies last, each by submission index): the agency,
    the confidence rule, the rationale, the evidence, the limitation; then each register agency
    without a view."""
    order = {r.agency: n for n, r in enumerate(source.register)}
    ranked = sorted(
        enumerate(sub.views), key=lambda iv: (order.get(iv[1].agency, len(order)), iv[0])
    )
    issues: list[str] = []
    seen: set[str] = set()
    for i, v in ranked:
        path = f"views[{i}]"
        if v.agency not in order:
            issues.append(
                clipped((path, ".agency: not an agency in the rating register: ", v.agency))
            )
        elif v.agency in seen:
            issues.append(clipped((path, ".agency: duplicate agency ", v.agency)))
        seen.add(v.agency)
        if v.confidence == "High":
            issues.append(f"{path}.confidence: {HIGH}")
        issues += _prose(f"{path}.rationale", v.rationale, bound, pack.names, claim=True)
        for j, citation in enumerate(v.evidence):
            where = f"{path}.evidence[{j}]"
            if is_blank(citation.quote):  # round 13 addendum 3: before the page-occurrence check
                issues.append(f"{where}.quote: empty text")
                continue
            issues += (
                clipped((where, ": ", x)) for x in citation_issues((citation,), pack.sources)
            )
        issues += _limitation(f"{path}.limitation", v.limitation, pack.names)
    issues += (
        clipped(("views: no view for agency ", r.agency))
        for r in source.register
        if r.agency not in seen
    )
    return issues


def _overall_issues(
    sub: TriggerSubmission, bound: Mapping[str, Fact], names: Sequence[str]
) -> list[str]:
    o = sub.overall
    issues = _prose("overall.rationale", o.rationale, bound, names, claim=True)
    if o.confidence == "High":
        issues.append(f"overall.confidence: {HIGH}")
    return issues + _limitation("overall.limitation", o.limitation, names)


def _gap_issues(
    sub: TriggerSubmission, bound: Mapping[str, Fact], names: Sequence[str]
) -> list[str]:
    issues: list[str] = []
    for i, g in enumerate(sub.gaps):
        for name in ("gap", "why_it_matters", "affected_analysis", "action"):
            issues += _prose(f"gaps[{i}].{name}", getattr(g, name), bound, names)
    return issues


def stale_issues(*, bound: Sequence[Input], current: Sequence[Input] | str) -> tuple[str, ...]:
    """Every bound upstream that changed, in the `cp2_synthesis._stale_issues` form."""
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


def ratings_source(pack: PackScope) -> Source:
    """The pack's agency source. Absent, missing or unreadable is `Rating register not found`,
    its hash and spans unread (round 7 item 2, 1D-x/Y2). Two of them, or a ready one without a
    hash, cannot happen (preparation, contracts) and stay invariant raises."""
    found = [s for s in pack.sources if s.source_id == RATINGS_SOURCE_ID]
    if len(found) > 1:
        raise ValueError("CP-2H: more than one ratings source in the pack")
    if not found or found[0].status != "ready":
        raise SourceIssue(REGISTER_NOT_FOUND)
    if found[0].sha256 is None:
        raise ValueError("CP-2H: the ready ratings source has no sha256")
    return found[0]


def source_pages(source: Source) -> tuple[str, str, str]:
    """The texts of page:1-page:3 by locator; an absent page reads as empty."""
    spans = {span.locator: span.text for span in source.spans}
    return (spans.get("page:1", ""), spans.get("page:2", ""), spans.get("page:3", ""))


def _bound(book: _Book, up: TriggerUpstream) -> dict[str, Fact]:
    """What prose may reference: the module's own non-analyst facts and CP-1's reported ratios
    (analyst cells are not bound, ruling P2)."""
    cp1 = referencable(select_cp1(up.cp1_facts).values())
    return prose.bind((*(c.fact for c in book.cells), *cp1))


def validate(inputs: TriggerInputs) -> tuple[str, ...]:
    """Every calculation-level issue of a parsed submission; empty when it composes.

    Stale upstream issues are returned alone (ruling G-decisions), then an agency source that
    is not ready or does not parse alone (s01, s02; round 7 items 2-8), then the content issues
    in the order views, overall, gaps (round 7 (a)). Shape issues come from `payload_issues`.
    Tool-use rules (cited page read) are Stage 2.
    """
    up, sub = inputs.upstream, inputs.submission
    stale = stale_issues(bound=up.bound, current=up.current)
    if stale:
        return stale
    try:
        ratings = ratings_source(inputs.pack)
        source = parse_ratings(source_pages(ratings))
    except SourceIssue as issue:
        return (str(issue),)
    book, _ = _compose(ratings, source, up, None)
    bound = _bound(book, up)
    names = inputs.pack.names
    issues = [
        *_view_issues(sub, source, bound, inputs.pack),
        *_overall_issues(sub, bound, names),
        *_gap_issues(sub, bound, names),
    ]
    return tuple(dict.fromkeys(issues))


def _parsed(payload: str) -> tuple[TriggerSubmission | None, tuple[str, ...]]:
    """The submission, or its shape issues (protocol section 6: model text is read only through
    `json_object`). The schema validates the bounded document's exact re-serialisation, never the
    raw text; text `json_object` refuses keeps Pydantic's own shape issue (the frozen r06 frame),
    and is refused even if Pydantic would parse it."""
    document = json_object(payload)
    try:
        if document is None:
            TriggerSubmission.model_validate_json(payload)  # for its shape issue only
            return None, ("(root): not a bounded JSON object",)
        return TriggerSubmission.model_validate_json(exact_json(document)), ()
    except ValidationError as error:
        return None, shape_issues(error)


def payload_issues(payload: str, *, pack: PackScope, upstream: TriggerUpstream) -> tuple[str, ...]:
    """Shape issues alone (a payload that does not parse gets no content check), else the
    calculation-level issues of `validate`."""
    submission, shape = _parsed(payload)
    if submission is None:
        return shape
    return validate(TriggerInputs(pack=pack, upstream=upstream, submission=submission))


# --- claims, references, own limitations -----------------------------------------------------------


def _figures(text: str, cp1_ids: Iterable[str]) -> tuple[str, ...]:
    ids = set(cp1_ids)
    return tuple(run.text for run in prose.tokenize(text) if run.figure and run.text in ids)


def _claims(
    b: _Book,
    mechanics: _Mechanics,
    views: Sequence[AgencyView],
    overall: Overall,
    cp1_ids: Iterable[str],
) -> tuple[ClaimDraft, ...]:
    cp1_ids = tuple(cp1_ids)
    out = [
        ClaimDraft(
            f"T2R.7.a{n:02d}", v.rationale, v.limitation, v.evidence, _figures(v.rationale, cp1_ids)
        )
        for n, v in enumerate(views, 1)
    ]
    out.append(
        ClaimDraft(
            "T2R.7.overall",
            overall.rationale,
            overall.limitation,
            (),
            _figures(overall.rationale, cp1_ids),
        )
    )
    for test in mechanics.tests:
        t = test.term
        token = "pp" if test.metric.unit_class == "percent" else "x"
        text = (
            f"{t.agency} {t.direction.lower()} trigger on {t.metric}: FY{BASE_YEAR} headroom is "
            f"{b.ref(f'T2R.4.{test.row}.headroom', token)}."
        )
        out.append(ClaimDraft(f"T2R.4.{test.row}", text, None, (), ()))
    for case in CASES:
        lab, total = CASE_LABEL[case].lower(), "T2R.9.total"
        text = (
            f"In the {lab} case, downgrade triggers reached by {FY[-1]}: "
            f"{b.ref(f'{total}.downgrade_{case}', COUNT_UNIT)}; upgrade triggers reached: "
            f"{b.ref(f'{total}.upgrade_{case}', COUNT_UNIT)}; triggers not calculable: "
            f"{b.ref(f'{total}.not_calculable_{case}', COUNT_UNIT)}."
        )
        out.append(ClaimDraft(f"T2R.6.{case}", text, FORECAST_LIMITATION, (), ()))
    for row in mechanics.pairs:
        fact_id = f"T2R.8.{row}.notches"
        if b.status(fact_id) == "known":
            text = f"The two agencies' ratings are {b.ref(fact_id, NOTCH_UNIT)} apart on the combined scale."
        else:
            text = f"The agencies' ratings cannot be compared: {b.ref(fact_id, NOTCH_UNIT)}."
        out.append(ClaimDraft(f"T2R.8.{row}", text, None, (), ()))
    return tuple(out)


def _cp1_references(
    up: TriggerUpstream, tests: Sequence[_Test], texts: Sequence[str]
) -> tuple[Cp1Reference, ...]:
    """CP-1 ratios named as figures in prose (reading order), then those T2R.4 compares."""
    cp1 = select_cp1(up.cp1_facts)
    metric_of = {f.fact_id: m for m, f in cp1.items()}
    named = [metric_of[fid] for text in texts for fid in _figures(text, metric_of)]
    metrics = dict.fromkeys([*named, *(t.metric.cp1_metric for t in tests)])
    return tuple(
        Cp1Reference(f"ref{n:02d}", m if m in named else None, cp1[m])
        for n, m in enumerate(metrics, 1)
    )


def _cp2g_references(up: TriggerUpstream, tests: Sequence[_Test]) -> tuple[Cp2gReference, ...]:
    fields = {t.metric.field for t in tests}
    read = [f for f in up.cp2g.facts if f.field in fields]
    return tuple(Cp2gReference(f"ref{n:02d}", f) for n, f in enumerate(read, 1))


_FIXED_LIMITATIONS = (
    (
        "Agency ratings, outlooks, scale mappings and trigger terms are read from one synthetic "
        "source naming fictional agencies; no real agency report is an input."
    ),
    (
        "Trigger terms are tested at each fiscal year end on CP-2G's reported-basis ratios; "
        "agency-adjusted definitions and any condition that a breach be sustained are not "
        "modelled."
    ),
    (
        "A trigger is reached only on a strict comparison: a metric equal to its threshold has "
        "not reached it and shows zero headroom."
    ),
    (
        "Headroom is the distance still to travel: for an upgrade trigger it is the distance to "
        "the level that would meet the term, and a reached upgrade trigger is not a rating change."
    ),
    (
        "Forward headroom is only as reliable as the CP-2G forecast, which uses analyst-assumed "
        "drivers."
    ),
    (
        "The migration view is the analyst's judgment on the published terms and the CP-2G path; "
        "no probability is computed, no rating is assigned and no agency action is predicted."
    ),
    (
        "The notch difference is measured on the source's combined scale; outlook weighting and "
        "sub-notch differences are not modelled."
    ),
    (
        "CP-1D (earnings quality) is not part of this run, so no earnings-quality adjustment is "
        "applied to the reported ratios."
    ),
)
CP1D_BOUND_LINE = (  # round 7 item 1 (the G-6 frame): replaces _FIXED_LIMITATIONS[7]
    "CP-1D (earnings quality) is bound but not read in this version, so no earnings-quality "
    "adjustment is applied to the reported ratios."
)
NOT_CALCULABLE_LINE = (
    "A trigger whose metric is not calculable in a forecast year is missing, with the reason, "
    "when no earlier year has reached it."
)


def _own_limitations(
    source: RatingsSource, up: TriggerUpstream, mechanics: _Mechanics, gaps: Sequence[SynthesisGap]
) -> tuple[str, ...]:
    out = list(_FIXED_LIMITATIONS)
    if up.cp1d_status is not None:
        out[7] = CP1D_BOUND_LINE
    out += (
        f"The trigger threshold is not stated for {_trigger_label(t)}: its headroom and timing are "
        "Not calculable."
        for t in source.triggers
        if t.threshold is None
    )
    out += (
        f"{r.agency}'s rating is {r.rating.lower()}: no notch comparison is made and no trigger "
        "terms are published."
        for r in source.register
        if r.position is None
    )
    if len(source.register) == 1:  # round 7 item 4
        out.append(
            f"Only {source.register[0].agency} is in the rating register, so no notch "
            "comparison is made."
        )
    if any(NOT_CALCULABLE in (o.base.first, o.down.first) for o in mechanics.outcomes):
        out.append(NOT_CALCULABLE_LINE)
    out += (f"Gap ({g.severity}): {g.gap}" for g in gaps)
    return tuple(dict.fromkeys(out))


# --- the calculation -------------------------------------------------------------------------------


def compute(inputs: TriggerInputs) -> TriggerReport:
    """The lease's tables, references, claims and own limitations of one valid submission;
    raises ValueError on any issue."""
    issues = validate(inputs)
    if issues:
        raise ValueError("; ".join(bounded_issues(issues)))
    up, sub = inputs.upstream, inputs.submission
    ratings = ratings_source(inputs.pack)
    source = parse_ratings(source_pages(ratings))
    book, mechanics = _compose(ratings, source, up, sub)
    views = _register_order(sub.views, source)
    cp1_ids = tuple(f.fact_id for f in select_cp1(up.cp1_facts).values())
    texts = [
        *(v.rationale for v in views),
        sub.overall.rationale,
        *(
            getattr(g, k)
            for g in sub.gaps
            for k in ("gap", "why_it_matters", "affected_analysis", "action")
        ),
    ]
    return TriggerReport(
        source=source,
        cells=tuple(book.cells),
        tables=book.tables(),
        cp1_references=_cp1_references(up, mechanics.tests, texts),
        cp2g_references=_cp2g_references(up, mechanics.tests),
        claims=_claims(book, mechanics, views, sub.overall, cp1_ids),
        own_limitations=_own_limitations(source, up, mechanics, sub.gaps),
        outcomes=mechanics.outcomes,
        totals=mechanics.totals,
    )


# =============================================================================================
# Stage 2: the connection (docs/CP2H-OWNER-LEASE.md Public API; docs/G1X-OWNER-CORE-PROTOCOL.md).
# Everything above is the Stage 1 calculation; what follows reads the store and journals.
# =============================================================================================

STEP_IDS = (STEP_ID,)
QUALIFICATION = Qualification(implementation="implemented")
SCHEMAS: Mapping[str, type[Contract]] = {STEP_ID: TriggerSubmission}
SUBMISSION_INPUT = STEP_ID.replace("_", "-") + "-submission"
# The fixed H1 mapping (`host._OWNER_SCOPES[("CP-2H", "rating_triggers")]`, lease :36): identity,
# financial and ratings; a held source stays in scope in pack order.
SCOPE = frozenset({"identity", "financial", RATINGS_SOURCE_ID})
CP1, CP2G = "CP-1", "CP-2G"


@dataclass(frozen=True)
class Upstream:
    """What one CP-2H attempt binds, read once from the journal (`cp2h_upstream`).

    `bound` is the attempt's input set; `current` is `execution.current_inputs` now, or its
    refusal text; `cp1` the facts of the bound CP-1 head; `cp2g` the 28 T2H.6 facts selected by
    literal id (`Cp2gMetrics.select`) from `owners.cp2g.cp2g_reader` over the bound CP-2G head
    (rulings stage2 Q6: the consumer selects into its own Stage 1 type); `inherited` what
    settlement will carry from the bound heads (`execution.inherited_limitations`)."""

    bound: tuple[Input, ...]
    current: tuple[Input, ...] | str
    cp1: tuple[Fact, ...]
    cp2g: Cp2gMetrics
    inherited: tuple[str, ...] = ()

    def status(self, input_id: str) -> InputStatus | None:
        return next((item.status for item in self.bound if item.input_id == input_id), None)


def _bound_module(store: Execution, attempt: Attempt, module_id: str) -> Module:
    item = next((i for i in attempt.inputs if i.input_id == module_id), None)
    if item is None:
        raise ValueError(f"The CP-2H attempt binds no {module_id} input")
    module = store.result(item.sha256)
    if module.module_id != module_id:
        raise ValueError(f"The CP-2H attempt's {module_id} input is a {module.module_id} module")
    return module


def cp2h_upstream(*, store: Execution, attempt: Attempt) -> Upstream:
    """The bound CP-1 and CP-2G heads, the current input set and the inherited limitations. The
    CP-2G facts are read through `cp2g_reader` on the head of the bound blob (its hash is the
    bound Input's), so a later CP-2G head is never read in its place. A refusal of
    `current_inputs` (an upstream gone stale, unrun or blocked, or CP-0 no longer authorizing
    CP-2H) is kept as text: the validator reports it as a staleness issue. A bound input whose
    blob is another module's raises."""
    snapshot = store.read()
    current: tuple[Input, ...] | str
    try:
        current = current_inputs(snapshot, MODULE_ID)
    except ValueError as error:  # NotAuthorized included: reported, never passed as current
        current = str(error)
    cp1 = _bound_module(store, attempt, CP1)
    head = cp2g_reader(store, head_of(_bound_module(store, attempt, CP2G)))
    return Upstream(
        bound=attempt.inputs,
        current=current,
        cp1=cp1.facts,
        cp2g=Cp2gMetrics.select(head.facts),
        inherited=inherited_limitations(snapshot, attempt, (), store.head_module),
    )


def _adapted(pack: PreparedPack, upstream: Upstream) -> tuple[PackScope, TriggerUpstream]:
    """The one store adapter: the host-scope sources in pack order and the issuer name, and the
    bound inputs, the CP-1 head's four selected reported ratios (`select_cp1`, in the head's
    order) and the CP-2G metrics, as the Stage 1 types the core reads. Submit, probe and view
    reach the core only through this."""
    chosen = {f.fact_id for f in select_cp1(upstream.cp1).values()}
    scope = PackScope(
        sources=tuple(s for s in pack.sources if s.source_id in SCOPE),
        names=(pack.run.issuer_name,),
    )
    trigger = TriggerUpstream(
        bound=upstream.bound,
        current=upstream.current,
        cp1_facts=tuple(f for f in upstream.cp1 if f.fact_id in chosen),
        cp2g=upstream.cp2g,
    )
    return scope, trigger


def _inputs(pack: PreparedPack, submission: TriggerSubmission, upstream: Upstream) -> TriggerInputs:
    scope, trigger = _adapted(pack, upstream)
    return TriggerInputs(pack=scope, upstream=trigger, submission=submission)


def validate_triggers(
    *, pack: PreparedPack, submission: TriggerSubmission, upstream: Upstream
) -> tuple[str, ...]:
    """Every issue of `submission` over the bound `upstream` (`validate`): staleness alone when a
    bound upstream changed, then an agency source that does not parse alone, else the content
    issues in their pinned order; empty when it composes."""
    return validate(_inputs(pack, submission, upstream))


class RatingTriggersReport(Contract):
    """The retained step output (the lease's `TriggerReport`; Stage 1 keeps that name for the
    pure composer's result): the composed content bound to the pack and the submission."""

    schema_version: Literal["rating-triggers/1"] = "rating-triggers/1"
    run: Run
    pack_sha256: Hash
    submission_sha256: Hash
    tables: tuple[ReportTable, ...]
    facts: tuple[Fact, ...]
    claims: tuple[ModuleClaim, ...]
    limitations: tuple[Text, ...]


_UPSTREAM_REF = ("cp1:", "cp2g:")
_VALUE_COLUMN = (TableColumn(field="value", label="Value"),)


def _with_upstream_citations(
    cells: Sequence[Cell], upstream: Mapping[str, Fact]
) -> tuple[Fact, ...]:
    """`expected.json cell_notation`: the citations of the `cp1:` and `cp2g:` facts a fact derives
    from, directly or through its own derived facts, are appended at run time after its own
    (frozen) citations. The appended part follows the derived-fact rule (rulings stage2 round 3
    item 3): one Citation per cited (source, page) not already cited, the first upstream quote on
    that page in `derives_from` order. A lineage entry that names no fact fails closed."""
    by_id = {c.fact.fact_id: c for c in cells}
    done: dict[str, tuple[Citation, ...]] = {}

    def appended(fact_id: str) -> tuple[Citation, ...]:
        if fact_id not in done:
            found: list[Citation] = []
            for ref in by_id[fact_id].derives_from:
                if ref.startswith(_UPSTREAM_REF):
                    if ref not in upstream:
                        raise ValueError(f"CP-2H: lineage {ref} names no bound upstream fact")
                    found += upstream[ref].citations
                elif ref in by_id:
                    found += appended(ref)
                else:
                    raise ValueError(f"CP-2H: lineage {ref} names no fact of the module")
            done[fact_id] = tuple(found)
        return done[fact_id]

    out: list[Fact] = []
    for cell in cells:
        pages = {(c.source_id, c.locator) for c in cell.fact.citations}
        extra: list[Citation] = []
        for citation in appended(cell.fact.fact_id):
            if (citation.source_id, citation.locator) not in pages:
                pages.add((citation.source_id, citation.locator))
                extra.append(citation)
        cites = (*cell.fact.citations, *extra)
        out.append(cell.fact.model_copy(update={"citations": cites}) if extra else cell.fact)
    return tuple(out)


def _moved(fact: Fact, table_id: str, row_id: str) -> Fact:
    """An upstream fact verbatim under its own id, placed in a reference table's cell: only the
    table, row and field coordinates change."""
    return fact.model_copy(update={"table_id": table_id, "row_id": row_id, "field": "value"})


def _reference_table(
    spec: tuple[str, str, str], rows: Sequence[tuple[str, str, str]]
) -> ReportTable:
    table_id, title, header = spec
    return ReportTable(
        table_id=table_id,
        title=title,
        columns=_VALUE_COLUMN,
        rows=tuple(TableRow(row_id=r, label=label, fact_ids=(fid,)) for r, label, fid in rows),
        row_header=header,
    )


def rating_triggers(
    *, pack: PreparedPack, submission: TriggerSubmission, upstream: Upstream
) -> RatingTriggersReport:
    """The composed report of a valid submission; raises ValueError on any issue."""
    issues = validate_triggers(pack=pack, submission=submission, upstream=upstream)
    if issues:
        raise ValueError("; ".join(bounded_issues(issues)))
    inputs = _inputs(pack, submission, upstream)
    result = compute(inputs)
    up = inputs.upstream
    lineage = {f"cp1:{m}": f for m, f in select_cp1(up.cp1_facts).items()}
    lineage |= {f"cp2g:{f.fact_id}": f for f in up.cp2g.facts}
    cp1_rows = [(r.row_id, r.label, r.fact.fact_id) for r in result.cp1_references]
    cp2g_rows = [(r.row_id, r.fact.label, r.fact.fact_id) for r in result.cp2g_references]
    return RatingTriggersReport(
        run=pack.run,
        pack_sha256=pack.content_hash(),
        submission_sha256=submission.content_hash(),
        tables=(
            *result.tables,
            _reference_table(CP1_REFERENCES, cp1_rows),
            _reference_table(CP2G_REFERENCES, cp2g_rows),
        ),
        facts=(
            *_with_upstream_citations(result.cells, lineage),
            *(_moved(r.fact, CP1_REFERENCES[0], r.row_id) for r in result.cp1_references),
            *(_moved(r.fact, CP2G_REFERENCES[0], r.row_id) for r in result.cp2g_references),
        ),
        claims=tuple(
            ModuleClaim(
                claim_id=c.claim_id, text=c.text, citations=c.citations, limitation=c.limitation
            )
            for c in result.claims
        ),
        limitations=result.own_limitations,
    )


def cp2h_module(report: RatingTriggersReport, *, inputs: Sequence[Input], attempt: int) -> Module:
    """The CP-2H candidate: the report's tables and claims bound to `inputs`, then the
    submission's content hash (the owner-only settled tail, protocol section 2 `SCHEMAS`)."""
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


# --- the exact `read_inputs` view (lease Tool use; manifest.json tool_use.view_tree_draft) -----


def _parsed_source(scope: PackScope) -> tuple[Source | None, RatingsSource | None]:
    """The ready agency source and its parse; None for an absent or unready source, and a parse
    of None for a source the parse rule refuses (the validator reports either)."""
    try:
        ratings = ratings_source(scope)
    except SourceIssue:
        return None, None
    try:
        return ratings, parse_ratings(source_pages(ratings))
    except SourceIssue:
        return ratings, None


def _metric_cell(fact: Fact) -> dict[str, object]:
    known = fact.status == "known"
    return {
        "ref": fact.fact_id,
        "shown": fact_spelling(fact, None)[2] if known else None,
        "status": fact.status,
        "limitation": fact.limitation,
    }


def context_block(*, pack: PreparedPack, upstream: Upstream) -> dict[str, object]:
    """What `read_inputs` returns, all Python's (lease Tool use, the draft key tree): the
    upstream statuses, the agency register and the published trigger terms as the parse rule
    reads them (terms, never a quote), each threshold as the fact a reference may name, the 28
    CP-2G metrics, the CP-1 reported ratios a reference may name and the limitations settlement
    will inherit. No quote, citation or record key at any depth."""
    scope, trigger = _adapted(pack, upstream)
    ratings, source = _parsed_source(scope)
    thresholds: dict[str, Cell] = {}
    if ratings is not None and source is not None:
        book, _ = _compose(ratings, source, trigger, None)
        thresholds = {
            c.fact.row_id: c
            for c in book.cells
            if (c.fact.table_id, c.fact.field) == ("T2R.3", "threshold")
        }
    register = () if source is None else source.register
    triggers = () if source is None else source.triggers

    def threshold(row: str) -> dict[str, object]:
        fact = thresholds[row].fact
        known = fact.status == "known"
        return {
            "ref": fact.fact_id if known else None,
            "shown": thresholds[row].shown if known else None,
            "status": fact.status,
        }

    cp1 = referencable(select_cp1(trigger.cp1_facts).values())
    return {
        "upstream": [
            {"module_id": item.input_id, "status": item.status}
            for item in upstream.bound
            if item.input_id.startswith("CP-")
        ],
        "register": {
            "state": "absent" if ratings is None else "present",
            "source_id": None if ratings is None else ratings.source_id,
            "pages": [] if ratings is None else [span.locator for span in ratings.spans],
            "agencies": [
                {
                    "row": f"r{n:02d}",
                    "agency": r.agency,
                    "rating": r.rating,
                    "outlook": r.outlook,
                    "date": r.date,
                    "position": r.position,
                }
                for n, r in enumerate(register, 1)
            ],
        },
        "triggers": [
            {
                "row": f"t{n:02d}",
                "agency": t.agency,
                "direction": t.direction,
                "metric": t.metric,
                "comparison": t.comparison,
                "threshold": threshold(f"t{n:02d}"),
            }
            for n, t in enumerate(triggers, 1)
        ],
        "cp2g": {
            "status": upstream.status(CP2G),
            "rows": [
                {
                    "row": row,
                    "metrics": {f: _metric_cell(upstream.cp2g.fact(row, f)) for f in CP2G_FIELDS},
                }
                for row in CP2G_ROWS
            ],
        },
        "cp1_facts": [
            {
                "ref": f.fact_id,
                "label": f.label,
                "period": f.period,
                "unit": figure_unit(f) or f.unit,
                "shown": spelled(f),
            }
            for f in cp1
        ],
        "inherited_limitations": list(upstream.inherited),
    }


def view(historical: Execution, attempt: Attempt) -> tuple[str, str]:
    """(sha256, body) of the one `read_inputs` record, as compact JSON (S1a lease rev 2, M4)."""
    upstream = cp2h_upstream(store=historical, attempt=attempt)
    block = context_block(pack=historical.pack(), upstream=upstream)
    body = json.dumps(block, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(body.encode()).hexdigest(), body


# --- the tool-use rule, the validator, submit and the verifier probe ---------------------------


def RULES(text: str, seen: Seen) -> tuple[str, ...]:
    """The tool-use evidence rule (protocol section 2): every cited page was returned by
    `read_pages` in the step. The schema holds no absence marker, so the product's cited-page
    rule (`live.tools.unread_citation_issues`, bounded and sorted) is the only one; it adds
    nothing else (lease Public API)."""
    return unread_citation_issues(text, seen)


def _validate_step(store: Execution, pack: PreparedPack, attempt: Attempt) -> StepValidation:
    """The step validator `submit` hands the journal and the verifier replays (its last step is
    the one under validation)."""
    submission, shape = _parsed(store.payload(attempt.steps[-1].payload_sha256))
    if submission is None:
        return StepValidation(issues=shape)
    upstream = cp2h_upstream(store=store, attempt=attempt)
    issues = validate_triggers(pack=pack, submission=submission, upstream=upstream)
    if issues:
        return StepValidation(issues=issues)
    report = rating_triggers(pack=pack, submission=submission, upstream=upstream)
    return StepValidation(output=report.model_dump_json())


ENTRY_VALIDATOR = _validate_step


def _candidate(output: str, attempt: Attempt) -> Module:
    return cp2h_module(
        RatingTriggersReport.model_validate_json(output),
        inputs=attempt.inputs,
        attempt=attempt.number,
    )


def _with_rules(
    validate: Callable[[PreparedPack, Attempt], StepValidation],
    rules: Callable[[str], tuple[str, ...]],
    payload: str,
) -> Callable[[PreparedPack, Attempt], StepValidation]:
    """`validate`, then the tool-use rule issues of the retained payload appended (as
    `live.submission._with_rules` composes them, which the verifier replays)."""

    def run(pack: PreparedPack, attempt: Attempt) -> StepValidation:
        outcome = validate(pack, attempt)
        found = rules(payload)
        if not found:
            return outcome
        return StepValidation(
            output=outcome.output, issues=tuple(dict.fromkeys((*outcome.issues, *found)))
        )

    return run


def submit(
    store: Execution,
    ticket_id: str,
    step_id: str,
    payload: str,
    rules: Callable[[str], tuple[str, ...]] | None,
) -> Submitted:
    """Journal the one `rating_triggers` step (null resolution through `SCHEMAS`, the rule issues
    appended) and, when it is valid, settle CP-2H with the Python candidate. An invalid step
    finishes the attempt rejected (blocked on the repair): there is no within-attempt repair."""
    if step_id != STEP_ID:
        raise ValueError(f"CP-2H has one step, {STEP_ID}")
    normal, resolved = normalise(TriggerSubmission, payload)

    def validate(pack: PreparedPack, current: Attempt) -> StepValidation:
        return _validate_step(store, pack, current)

    checked: Callable[[PreparedPack, Attempt], StepValidation] = validate
    if rules is not None and rules(normal):
        checked = _with_rules(validate, rules, normal)
    attempt = store.submit_step(ticket_id, MODULE_ID, STEP_IDS, step_id, normal, checked)
    if (
        attempt.status == "pending"
        and len(attempt.steps) == 1
        and attempt.steps[0].status == "valid"
    ):
        outcome = _validate_step(store, store.pack(), attempt)
        if outcome.issues or not outcome.retained_as(attempt.steps[0]):
            raise ValueError("Retained CP-2H output differs from trusted validation")
        candidate = _candidate(outcome.output or "", attempt)
        attempt = store.finish(
            ticket_id,
            candidate.model_dump_json(),
            lambda supplied: () if supplied == candidate else ("CP-2H candidate differs",),
            qualification=QUALIFICATION,
        )
    return Submitted(attempt, normal, resolved, (), (), None)


def probe(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    """Rerun the step validator and settlement over the settled snapshot (nothing is written);
    `WorkflowError("identity_mismatch")` unless the head rebuilds exactly (lease Public API)."""
    probe_one_step(store, snapshot, attempt, validate=_validate_step, build=_candidate)
