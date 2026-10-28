"""CP-8 (decision ledger and post-mortem): validation, Decimal diff and composed result.

Stage 1 of the owner core (lease ``docs/CP8-OWNER-LEASE.md`` rev 4, oracle ``cases/cp8-owner``):
pure functions over the analyst's ``decision_ledger`` submission, the prepared pack and the
CP-0 (and, when bound, CP-6) upstream. Python parses every quoted figure and date and decides
each variance, breach, count and status in exact Decimal; the analyst supplies only verbatim
quotes and judgments. The G1-X seams (store, RULES, submit, probe, reader) come in later stages.

Wording beyond the lease and the oracle comes from LEAD's rulings
(``docs/rulings/2026-10-28-stage1.md``: round 5 "CP-8", 8-1 to 8-20; round 6c, 8-24; round 6h,
a quotation split on one side and missing on the other). A ``ValueError`` starting
"invariant:" marks a state no validated submission reaches (8-8 and 8-12 among them).
"""

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import (
    ROUND_HALF_UP,
    Context,
    Decimal,
    DivisionByZero,
    Inexact,
    InvalidOperation,
    localcontext,
)
from typing import Literal

from deploy_vii.contracts import (
    Citation,
    Claim,
    Contract,
    Fact,
    Identifier,
    ReportTable,
    Source,
    TableColumn,
    TableRow,
    Text,
)
from deploy_vii.cp6_committee import ACTION_BIASES, CONFIDENCES
from deploy_vii.display import format_date
from deploy_vii.prose import bind, issues, tokenize
from deploy_vii.quotes import normalise
from deploy_vii.readiness import citation_issues
from deploy_vii.registry import modules
from deploy_vii.report_view import fact_spelling, figure_unit

MODULE_ID = "CP-8"
STEP_ID = "decision_ledger"

DECISION_SOURCE = "prior_case"  # the Prior Case record (D5): the only decision-record source
SCOPE = ("prior_case", "update", "market_update")  # the fixed host-side scope of the step (D9)
FLAGGED = "Flagged Risk Materialized"
UNFLAGGED = "Unflagged Risk Materialized"
INSUFFICIENT = "Insufficient Information"
CONFIRMED = "Thesis Confirmed"
LABELS = (  # r14 CP-8 six-label attribution taxonomy
    CONFIRMED,
    FLAGGED,
    UNFLAGGED,
    "Right for Wrong Reason",
    "Premature / Mistimed",
    INSUFFICIENT,
)
LEVELS = ("High", "Medium", "Low")
NOT_ASSESSED = "Not assessed"
PROCESS = ("Y", "N", NOT_ASSESSED)
SIDES = ("expected", "realized")
METRICS = ("total_leverage", "interest_cover", "loan_mid")
OBS_METRICS = ("total_leverage", "interest_cover", "loan_bid", "loan_offer")
SIZE_METRICS = ("total_leverage", "interest_cover")  # the measures a downside size can name
QUOTATION = ("loan_bid", "loan_offer")
COMPARATORS = ("above", "below")
OVERALL = "overall"
MAX_LESSONS = 2
DECISIONS_REQUIRED = 3  # r14 REF_CP-8_06: at least three comparable decisions (a schema rule)
INTERIM = "Interim"
WHAT_CHANGED = "cp8.what_changed"
# The report-wide gap number is bound at render time; the oracle pins a resolved line's gap
# chip with this placeholder (expected.json cases.no_outcome cp8.what_changed.outcome.value).
GAP_PLACEHOLDER = "G#"

METRIC_NAME: Mapping[str, str] = {
    "total_leverage": "Total leverage",
    "interest_cover": "Interest cover",
    "loan_mid": "Mid level of the term loan quotation",
    "loan_bid": "Dealer bid",
    "loan_offer": "Dealer offer",
}
MEASURE_LABEL: Mapping[str, str] = {
    "total_leverage": "total leverage",
    "interest_cover": "interest cover",
}
OBS_UNIT: Mapping[str, tuple[str, int]] = {
    "total_leverage": ("MULTIPLE", 2),
    "interest_cover": ("MULTIPLE", 2),
    "loan_bid": ("decimal_fraction", 2),
    "loan_offer": ("decimal_fraction", 2),
}

Direction = Literal["Higher", "Lower", "Unchanged"]
DIRECTIONS: tuple[Direction, ...] = ("Higher", "Lower", "Unchanged")

# Every stored value is exact: any rounding, invalid operation or division by zero raises.
EXACT = Context(prec=28, rounding=ROUND_HALF_UP, traps=[Inexact, InvalidOperation, DivisionByZero])

_MONTHS = (
    *("January", "February", "March", "April", "May", "June"),
    *("July", "August", "September", "October", "November", "December"),
)
_DATE = re.compile(r"^(" + "|".join(_MONTHS) + r") ([1-9]|[12][0-9]|3[01]), ((?:19|20)[0-9]{2})$")
_FIGURE = re.compile(r"^[0-9]{1,3}\.[0-9]{2}$")  # a quoted figure or level: N.NN
_MULTIPLE = re.compile(r"[0-9]+\.[0-9]+x")
_DECIMAL = re.compile(r"[0-9]+\.[0-9]+")
_REFERENCE = re.compile(r"[{}\[\]]")
_SUBJECT = re.compile(r"default|restructuring")
_PROHIBITED = re.compile(  # r14 prohibited conclusions (lease, analyst text)
    r"(?<![A-Za-z])(?:blame|fault|should have|in hindsight|with hindsight|recommend|overweight"
    r"|underweight|buy|sell|adjust the prior)|calibrat",
    re.IGNORECASE,
)
_UNAVAILABLE = "Unavailable or changed source: "  # readiness.citation_issues' wording

LIM_RECORD = (
    "The Prior Case record is a supplied file of unknown authority; its authenticity is its hash "
    "only."
)
LIM_CLASSIFIED = (  # 8-9: a Prior Case record CP-0 classifies other than unknown
    "The Prior Case record is a supplied file classified {} by CP-0; its authenticity is its hash "
    "only."
)
UNRECORDED = (  # 8-6: the pinned limitation's fragments, in its order
    "Portfolio posture",
    "position size",
    "expected spread or return",
    "rating path",
    "holding period",
)
LIM_EXIT = "The exit trigger records no threshold, so exit discipline cannot be measured"
LIM_NO_EXIT = "No exit trigger is recorded, so exit discipline cannot be measured"  # 8-17
LIM_NO_OUTCOME = (
    "No post-decision outcome source was supplied, so no realized outcome, variance or "
    "attribution is shown"
)
LIM_INTERIM = "Realized figures are interim: no source states that the observation window is closed"
LIM_ONE_DECISION = (
    "One decision is recorded, so no calibration recommendation is possible (at least three "
    "comparable decisions are needed)"
)
LIM_NO_CP6 = "No current CP-6 decision is in this run, so the decision itself is not compared"
LIM_CP6_INSUFFICIENT = (  # 8-20
    "CP-6 states Insufficient Information, so the decision itself is not compared"
)
LIM_NOT_COMPARED = (  # 8-1
    "Measures not compared: {}; their variance and attribution are not shown."
)


def _name(metric: str) -> str:
    """``<name>`` of the rulings: the row label with its first letter lower-cased (a T7.3 bid
    or offer row names itself, round 6c (a))."""
    label = METRIC_NAME[metric]
    return label[0].lower() + label[1:]


def _listed(names: Sequence[str]) -> str:
    """Names joined with ", " and a final " and "."""
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _authority(authority: Mapping[str, str], source_id: str) -> str:
    found = authority.get(source_id)
    if found is None:  # 8-12: CP-0 writes a T3 authority for every source it assesses
        raise ValueError(f"invariant: CP-0 T3 states no authority for pack source {source_id}")
    return found


# --- submission schema (reference and judgment only) ---------------------------------------------
# Vocabulary fields are plain strings so the validator, not the shape check, names a wrong value.


class QuoteRef(Contract):
    source_id: Identifier
    locator: Text
    quote: Text


class Absence(Contract):
    quote: QuoteRef | None = None
    reason: str
    follow_up: str


class DecisionField(Contract):
    """``{text, quote}`` or ``{absence}``; the validator reports any other combination."""

    text: str | None = None
    quote: QuoteRef | None = None
    absence: Absence | None = None


class Decision(Contract):
    action_bias: DecisionField
    confidence: DecisionField
    instrument: DecisionField
    decision_date: DecisionField
    decision_maker_role: DecisionField
    posture: DecisionField
    size: DecisionField

    def fields(self) -> tuple[tuple[str, DecisionField], ...]:
        return (
            ("action_bias", self.action_bias),
            ("confidence", self.confidence),
            ("instrument", self.instrument),
            ("decision_date", self.decision_date),
            ("decision_maker_role", self.decision_maker_role),
            ("posture", self.posture),
            ("size", self.size),
        )


class ThesisField(Contract):
    """``{quote}`` (the cell text is the verbatim span) or ``{absence}``."""

    quote: QuoteRef | None = None
    absence: Absence | None = None


class SizeEntry(Contract):
    metric_id: str
    comparator: str
    level_text: str
    quote: QuoteRef


class Thesis(Contract):
    thesis: ThesisField
    greatest_uncertainty: ThesisField
    downside_paths: ThesisField
    exit_trigger: ThesisField
    expected_spread_return: ThesisField
    expected_rating_path: ThesisField
    expected_hold: ThesisField
    downside_sizes: tuple[SizeEntry, ...]

    def fields(self) -> tuple[tuple[str, ThesisField], ...]:
        return (
            ("thesis", self.thesis),
            ("greatest_uncertainty", self.greatest_uncertainty),
            ("downside_paths", self.downside_paths),
            ("exit_trigger", self.exit_trigger),
            ("expected_spread_return", self.expected_spread_return),
            ("expected_rating_path", self.expected_rating_path),
            ("expected_hold", self.expected_hold),
        )


class ObservationEntry(Contract):
    side: str
    metric: str
    value_text: str
    as_of_text: str
    quote: QuoteRef


class OutcomeAbsence(Contract):
    reason: str
    follow_up: str


class DefaultStatement(Contract):
    as_of_text: str
    quote: QuoteRef


class MetricConfidence(Contract):
    metric_id: str
    level: str


class Attribution(Contract):
    metric_id: str
    label: str
    process_sound: str
    originating_module: str | None = None
    basis: str
    flag_quote: str | None = None


class Lesson(Contract):
    lesson: str
    metric_ids: tuple[str, ...]


class ExtraGap(Contract):
    gap: str
    missing_item: str
    why_it_matters: str
    impact_on_output: str
    follow_up: str


class Synthesis(Contract):
    text: str


class DecisionLedgerSubmission(Contract):
    decision: Decision
    thesis: Thesis
    observations: tuple[ObservationEntry, ...]
    outcome_absence: OutcomeAbsence | None
    default_restructuring: DefaultStatement | None
    confidence: tuple[MetricConfidence, ...]
    attributions: tuple[Attribution, ...]
    lessons: tuple[Lesson, ...]
    extra_gaps: tuple[ExtraGap, ...]
    synthesis: Synthesis


DECISION_OPTIONAL = ("posture", "size")
THESIS_REQUIRED = ("thesis", "greatest_uncertainty", "downside_paths")


# --- upstream ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Upstream:
    """What CP-8 reads besides its own submission and the pack."""

    as_of: date  # Run.as_of: the period of the run-level counts
    authority: Mapping[str, str]  # CP-0 T3 authority per pack source
    cp6: tuple[str, str] | None = None  # settled CP-6 T6-FINAL final_bias (action_bias, confidence)


def source_authority(facts: Iterable[Fact]) -> dict[str, str]:
    """Source id -> authority from CP-0's ``T3.<source_id>.authority`` facts."""
    out: dict[str, str] = {}
    for fact in facts:
        if (fact.table_id, fact.field) != ("T3", "authority"):
            continue
        if fact.status != "known" or fact.text is None:
            raise ValueError(f"CP-0 authority fact is not known text: {fact.fact_id}")
        if fact.row_id in out:
            raise ValueError(f"CP-0 states two authorities for {fact.row_id}")
        out[fact.row_id] = fact.text
    return out


# --- parsing helpers -------------------------------------------------------------------------------


def parse_date(text: str) -> date | None:
    """``Month D, YYYY`` as a date; ``None`` for any other text or an impossible date."""
    match = _DATE.match(text)
    if match is None:
        return None
    try:
        return date(int(match.group(3)), _MONTHS.index(match.group(1)) + 1, int(match.group(2)))
    except ValueError:  # February 30 and the like: not a date
        return None


def _date(text: str) -> date:
    parsed = parse_date(text)
    if parsed is None:
        raise ValueError(f"Not a validated date: {text}")
    return parsed


def _norm(text: str) -> str:
    """A quote as ``readiness.citation_issues`` matches it (``deploy_vii.quotes``: soft hyphens
    removed, quote marks, dashes and minus mapped, whitespace runs collapsed). Every figure,
    date, label and text read from a quote reads this form, so a figure the matcher accepts is
    the figure the page states (fix 1, M1)."""
    return normalise(text)


def _token_once(value: str, quote: str) -> bool:
    """``value`` occurs exactly once in the normalised ``quote`` as a whole number."""
    pattern = r"(?<![0-9.])" + re.escape(value) + r"(?![0-9]|\.[0-9])"
    return len(re.findall(pattern, quote)) == 1


def _labelled(metric: str, value: str, quote: str) -> bool:
    """``value`` is the first figure after the measure's label (a multiple for leverage/cover)."""
    text = _norm(quote)
    if metric in MEASURE_LABEL:
        label, figure, shown = MEASURE_LABEL[metric], _MULTIPLE, value + "x"
    else:
        label, figure, shown = ("bid " if metric == "loan_bid" else "offer "), _DECIMAL, value
    at = text.lower().find(label)
    if at < 0:
        return False
    match = figure.search(text, at + len(label))
    return match is not None and match.group(0) == shown


def _parts(metric: str) -> tuple[str, ...]:
    return QUOTATION if metric == "loan_mid" else (metric,)


def _split(as_of: Mapping[str, date]) -> tuple[date, date] | None:
    """8-7: a side's (bid, offer) dates when they differ; that side's mid is then not calculable."""
    bid, offer = as_of.get("loan_bid"), as_of.get("loan_offer")
    return None if bid is None or offer is None or bid == offer else (bid, offer)


def _compared(
    keys: Iterable[tuple[str, str]], as_of: Mapping[str, Mapping[str, date]]
) -> tuple[str, ...]:
    """Measures with an expected and a realized observation (the mid needs bid and offer, each
    side quoted on one date)."""
    have = set(keys)
    split = any(_split(as_of[side]) for side in SIDES)
    return tuple(
        m
        for m in METRICS
        if all((side, part) in have for side in SIDES for part in _parts(m))
        and not (m == "loan_mid" and split)
    )


@dataclass(frozen=True)
class RecordedSize:
    """A downside size the Prior Case record names: breached strictly beyond ``level``."""

    comparator: str
    level: Decimal

    def __post_init__(self) -> None:
        if self.comparator not in COMPARATORS:
            raise ValueError(f"Not a downside size comparator: {self.comparator}")


def breached(size: RecordedSize | None, value: Decimal | None) -> bool | None:
    """Python's breach decision; ``None`` without a size or a realized value. Equal is not."""
    if size is None or value is None:
        return None
    return value > size.level if size.comparator == "above" else value < size.level


# --- validation ------------------------------------------------------------------------------------


class _Checker:
    """The validator's rules in field order; one defect, one issue, never de-duplicated."""

    def __init__(
        self, submission: DecisionLedgerSubmission, upstream: Upstream, pack: Sequence[Source]
    ) -> None:
        self.sub = submission
        self.authority = upstream.authority
        self.pack = tuple(pack)
        self.index = {source.source_id: source for source in pack}
        self.module_ids = frozenset(item.module_id for item in modules())
        down = submission.thesis.downside_paths.quote
        self.downside = "" if down is None else down.quote
        self.found: list[str] = []
        self.decision_date: date | None = None
        self.sizes: dict[str, RecordedSize | None] = {}  # None: a size reported invalid
        self.submitted: set[tuple[str, str]] = set()
        self.values: dict[tuple[str, str], Decimal] = {}
        self.as_of: dict[str, dict[str, date]] = {side: {} for side in SIDES}  # valid entries

    def run(self) -> tuple[str, ...]:
        self._decision()
        self._thesis()
        self._sizes()
        self._observations()
        self._outcome()
        compared = _compared(self.submitted, self.as_of)
        self._confidence(compared)
        self._attributions(compared)
        self._lessons(compared)
        for i, gap in enumerate(self.sub.extra_gaps):
            for field, text in (
                ("gap", gap.gap),
                ("missing_item", gap.missing_item),
                ("why_it_matters", gap.why_it_matters),
                ("impact_on_output", gap.impact_on_output),
                ("follow_up", gap.follow_up),
            ):
                self._text(f"extra_gaps[{i}].{field}", text)
        self._text("synthesis.text", self.sub.synthesis.text)
        return tuple(self.found)

    # shared rules

    def _cite(self, path: str, ref: QuoteRef, only: str | None = None) -> list[str]:
        """Pack, then the CP-8 scope, then the field's own source, then locator and quote."""
        source = self.index.get(ref.source_id)
        if source is None or source.status != "ready" or source.sha256 is None:
            return [_UNAVAILABLE + ref.source_id]  # citation_issues' own condition and wording
        if ref.source_id not in SCOPE:
            return [f"{path}: source {ref.source_id} is outside the CP-8 scope"]
        if only is not None and ref.source_id != only:
            return [f"{path}: must cite {only}"]
        citation = Citation(
            source_id=ref.source_id,
            source_sha256=source.sha256,
            locator=ref.locator,
            quote=ref.quote,
        )
        return list(citation_issues((citation,), self.pack))

    def _text(self, path: str, text: str) -> None:
        """Analyst text: non-empty, digit-free, no reference syntax, no prohibited conclusion."""
        hit = _PROHIBITED.search(text)
        if not text.strip():
            self.found.append(f"{path}: text is empty")
        elif any(char.isnumeric() for char in text):
            self.found.append(f"{path}: digits are not allowed")
        elif _REFERENCE.search(text):
            self.found.append(f"{path}: reference syntax is not allowed")
        elif hit is not None:
            self.found.append(f"{path}: prohibited conclusion: {hit.group(0).lower()}")

    def _absence(self, path: str, absence: Absence) -> None:
        self._text(f"{path}.absence.reason", absence.reason)
        self._text(f"{path}.absence.follow_up", absence.follow_up)
        if absence.quote is not None:
            self.found += self._cite(f"{path}.absence.quote", absence.quote, DECISION_SOURCE)

    # decision record and thesis

    def _decision(self) -> None:
        for name, item in self.sub.decision.fields():
            path = f"decision.{name}"
            if item.absence is not None and item.text is None:
                if name not in DECISION_OPTIONAL:
                    self.found.append(f"{path}: a required decision field cannot be absent")
                elif item.quote is not None:  # 8-10, the r29 frame
                    self.found.append(f"{path}: exactly one of quote and absence is required")
                else:
                    self._absence(path, item.absence)
            elif item.text is not None and item.absence is None:
                if item.quote is None:  # 8-10, the r32 frame
                    self.found.append(f"{path}: text and quote are given together")
                else:
                    self._decision_text(name, path, item.text, item.quote)
            else:
                self.found.append(f"{path}: exactly one of text and absence is required")

    def _decision_text(self, name: str, path: str, text: str, quote: QuoteRef) -> None:
        found = self._cite(f"{path}.quote", quote, DECISION_SOURCE)
        vocabulary = {"action_bias": ACTION_BIASES, "confidence": CONFIDENCES}.get(name)
        if found:
            self.found += found
        elif vocabulary is not None and text not in vocabulary:
            self.found.append(f"{path}: {text} is not one of {', '.join(vocabulary)}")
        elif text not in _norm(quote.quote):
            self.found.append(f"{path}: text {text} does not occur in the quote")
        elif name == "decision_date":
            self.decision_date = parse_date(text)
            if self.decision_date is None:
                self.found.append(f"{path}: text {text} is not a date (Month D, YYYY)")

    def _thesis(self) -> None:
        for name, item in self.sub.thesis.fields():
            path = f"thesis.{name}"
            if (item.quote is None) == (item.absence is None):
                self.found.append(f"{path}: exactly one of quote and absence is required")
            elif item.absence is not None:
                if name in THESIS_REQUIRED:
                    self.found.append(f"{path}: a required thesis field cannot be absent")
                else:
                    self._absence(path, item.absence)
            elif item.quote is not None:
                self.found += self._cite(f"{path}.quote", item.quote, DECISION_SOURCE)

    def _sizes(self) -> None:
        for i, size in enumerate(self.sub.thesis.downside_sizes):
            path = f"thesis.downside_sizes[{i}]"
            if size.metric_id not in SIZE_METRICS:
                self.found.append(
                    f"{path}: metric {size.metric_id} is not one of {', '.join(SIZE_METRICS)}"
                )
            elif size.metric_id in self.sizes:
                self.found.append(f"thesis.downside_sizes: {size.metric_id} appears more than once")
            else:
                self.sizes[size.metric_id] = self._size(path, size)

    def _size(self, path: str, size: SizeEntry) -> RecordedSize | None:
        if size.comparator not in COMPARATORS:
            self.found.append(
                f"{path}: comparator {size.comparator} is not one of {', '.join(COMPARATORS)}"
            )
            return None
        found = self._cite(f"{path}.quote", size.quote, DECISION_SOURCE)
        quote, level = _norm(size.quote.quote), size.level_text
        statement = f"{MEASURE_LABEL[size.metric_id]} {size.comparator} {level}x"
        if found:
            self.found += found
        elif _norm(quote) not in _norm(self.downside):
            self.found.append(f"{path}.quote: not a span of the recorded downside paths")
        elif not _FIGURE.match(level) or not _token_once(level, quote):
            self.found.append(f"{path}: level_text {level} does not occur in the quote")
        elif statement not in _norm(quote).lower():
            self.found.append(f"{path}: quote does not state {statement}")
        else:
            return RecordedSize(comparator=size.comparator, level=Decimal(level))
        return None

    # observations and outcome

    def _observations(self) -> None:
        for i, obs in enumerate(self.sub.observations):
            path = f"observations[{i}]"
            key = (obs.side, obs.metric)
            if obs.side not in SIDES:
                self.found.append(f"{path}: side {obs.side} is not expected or realized")
            elif obs.metric not in OBS_METRICS:
                self.found.append(
                    f"{path}: metric {obs.metric} is not one of {', '.join(OBS_METRICS)}"
                )
            elif key in self.submitted:
                self.found.append(
                    f"observations: ({obs.side}, {obs.metric}) appears more than once"
                )
            else:
                self.submitted.add(key)
                found = self._observation(path, obs)
                if found:
                    self.found += found
                else:
                    self.values[key] = Decimal(obs.value_text)
                    self.as_of[obs.side][obs.metric] = _date(obs.as_of_text)
        for side in SIDES:
            bid, offer = (side, "loan_bid"), (side, "loan_offer")
            if (bid in self.submitted) != (offer in self.submitted):
                self.found.append(
                    f"observations: {side} loan_bid and loan_offer must be given together"
                )
            elif (
                bid in self.values
                and offer in self.values
                and self.values[bid] > self.values[offer]
            ):
                self.found.append(f"observations: {side} bid exceeds offer")

    def _observation(self, path: str, obs: ObservationEntry) -> list[str]:
        found = self._observation_source(path, obs)
        value, quote = obs.value_text, _norm(obs.quote.quote)
        as_of = parse_date(obs.as_of_text) if obs.as_of_text in quote else None
        if found:
            return found
        if not _FIGURE.match(value) or not _token_once(value, quote):
            return [f"{path}: value_text {value} does not occur in the quote"]
        if not _labelled(obs.metric, value, quote):
            return [
                f"{path}: {obs.metric} value_text {value} is not labelled {obs.metric} in the quote"
            ]
        if as_of is None:
            return [f"{path}: as_of_text {obs.as_of_text} does not occur in the quote"]
        if (
            obs.side == "realized"
            and self.decision_date is not None
            and as_of <= self.decision_date
        ):
            return [f"{path}: realized as_of {obs.as_of_text} is not after the decision date"]
        return []

    def _observation_source(self, path: str, obs: ObservationEntry) -> list[str]:
        if obs.side == "expected":
            return self._cite(f"{path}.quote", obs.quote, DECISION_SOURCE)
        found = self._cite(f"{path}.quote", obs.quote)
        source_id = obs.quote.source_id
        if found:
            return found
        if source_id == DECISION_SOURCE:
            return [f"{path}.quote: a realized observation cannot cite {DECISION_SOURCE}"]
        want = "third_party" if obs.metric in QUOTATION else "issuer"
        have = _authority(self.authority, source_id)
        if have != want:
            article = "an" if want[0] in "aeiou" else "a"
            return [
                f"{path}: {obs.metric} needs {article} {want} source, {source_id} is {have} (CP-0 T3)"
            ]
        return []

    def _outcome(self) -> None:
        realized = any(obs.side == "realized" for obs in self.sub.observations)
        absence = self.sub.outcome_absence
        statement = self.sub.default_restructuring
        both = realized and absence is not None
        if both:
            self.found.append(
                "observations: realized observations and outcome_absence are mutually exclusive"
            )
        elif not realized and absence is None:
            self.found.append("observations: no realized observation and no outcome_absence")
        if absence is not None:
            self._text("outcome_absence.reason", absence.reason)
            self._text("outcome_absence.follow_up", absence.follow_up)
        if both:
            return  # one defect, one issue: the default statement is not judged as well
        if statement is not None and absence is not None:
            self.found.append("default_restructuring: not allowed together with outcome_absence")
        elif statement is None and realized:
            self.found.append("default_restructuring: required when a realized outcome is given")
        elif statement is not None:
            self._default(statement)

    def _default(self, statement: DefaultStatement) -> None:
        found = self._cite("default_restructuring.quote", statement.quote)
        source_id, quote, at = (
            statement.quote.source_id,
            _norm(statement.quote.quote),
            statement.as_of_text,
        )
        as_of = parse_date(at) if at in quote else None
        if not found and (have := _authority(self.authority, source_id)) != "issuer":
            found = [
                f"default_restructuring: needs an issuer source, {source_id} is {have} (CP-0 T3)"
            ]
        if found:
            self.found += found
        elif not _SUBJECT.search(_norm(quote).lower()):
            self.found.append(
                "default_restructuring.quote: does not state default or restructuring incidence"
            )
        elif as_of is None:
            self.found.append(f"default_restructuring: as_of_text {at} does not occur in the quote")
        elif self.decision_date is not None and as_of <= self.decision_date:
            self.found.append(f"default_restructuring: as_of {at} is not after the decision date")

    # judgments

    def _confidence(self, compared: tuple[str, ...]) -> None:
        given = [entry.metric_id for entry in self.sub.confidence]
        for i, entry in enumerate(self.sub.confidence):
            if entry.metric_id not in compared:
                self.found.append(f"confidence[{i}]: {entry.metric_id} is not a compared metric")
            elif given.count(entry.metric_id) > 1:  # 8-11: once per occurrence (r42)
                self.found.append(f"confidence: {entry.metric_id} appears more than once")
            elif entry.level not in LEVELS:
                self.found.append(
                    f"confidence[{i}]: {entry.level} is not one of {', '.join(LEVELS)}"
                )
        self.found += [f"confidence: no confidence for {m}" for m in compared if m not in given]

    def _attributions(self, compared: tuple[str, ...]) -> None:
        attributions = self.sub.attributions
        named = [a.metric_id for a in attributions]
        for i, item in enumerate(attributions):
            path = f"attributions[{i}]"
            if item.metric_id not in compared and item.metric_id != OVERALL:
                self.found.append(f"{path}: {item.metric_id} is not a compared metric or overall")
            elif named.count(item.metric_id) > 1:  # reported once per occurrence (r42)
                self.found.append(f"attributions: {item.metric_id} appears more than once")
            elif item.label not in LABELS:
                self.found.append(f"{path}: label {item.label} is not one of {', '.join(LABELS)}")
            else:
                self._text(f"{path}.basis", item.basis)
                self._process(path, item)
                self._flag(path, item)
                self._flag_size(path, item, compared)
                self._origin(path, item)
        self.found += [
            f"attributions: no attribution for {m}" for m in (*compared, OVERALL) if m not in named
        ]
        overall = next((a for a in attributions if a.metric_id == OVERALL), None)
        if overall is not None and not compared and overall.label != INSUFFICIENT:
            self.found.append(
                "attributions[overall]: with no compared metric the label must be Insufficient "
                "Information"
            )

    def _process(self, path: str, item: Attribution) -> None:
        label, sound = item.label, item.process_sound
        if sound not in PROCESS:
            self.found.append(f"{path}: process_sound {sound} is not one of {', '.join(PROCESS)}")
        elif label == INSUFFICIENT and sound != NOT_ASSESSED:
            self.found.append(
                f"{path}: Insufficient Information requires process_sound Not assessed"
            )
        elif label != INSUFFICIENT and sound == NOT_ASSESSED:
            self.found.append(f"{path}: {label} cannot have process_sound Not assessed")
        elif label == FLAGGED and sound != "Y":
            self.found.append(f"{path}: Flagged Risk Materialized requires process_sound Y")
        elif label == UNFLAGGED and sound != "N":
            self.found.append(f"{path}: Unflagged Risk Materialized requires process_sound N")

    def _flag(self, path: str, item: Attribution) -> None:
        if item.label != FLAGGED:
            if item.flag_quote:
                self.found.append(f"{path}: flag_quote is only for Flagged Risk Materialized")
        elif not item.flag_quote or not item.flag_quote.strip():
            self.found.append(f"{path}: Flagged Risk Materialized needs flag_quote")
        elif _norm(item.flag_quote) not in _norm(self.downside):
            self.found.append(f"{path}.flag_quote: not a span of the recorded downside paths")

    def _flag_size(self, path: str, item: Attribution, compared: tuple[str, ...]) -> None:
        """A flagged metric needs its recorded size breached; a flagged overall needs one such
        metric (not checked with nothing compared: the overall rule reports that case)."""
        if item.label != FLAGGED:
            return
        metric = item.metric_id
        if metric == OVERALL:
            if compared and not any(self._breached_flag(other) for other in self.sub.attributions):
                self.found.append(
                    f"{path}: Flagged Risk Materialized overall needs at least one flagged metric "
                    "with a breached downside size"
                )
            return
        if metric not in self.sizes:
            self.found.append(
                f"{path}: Flagged Risk Materialized needs a recorded downside size for {metric}"
            )
            return
        size, real = self.sizes[metric], self.values.get(("realized", metric))
        # an invalid size or realized observation has its own issue: no second one here
        if size is not None and real is not None and not breached(size, real):
            self.found.append(
                f"{path}: Flagged Risk Materialized needs the downside size breached, but "
                f"{metric} {real:f} is not {size.comparator} {size.level:f}x"
            )

    def _breached_flag(self, item: Attribution) -> bool:
        if item.label != FLAGGED or item.metric_id == OVERALL:
            return False
        real = self.values.get(("realized", item.metric_id))
        return breached(self.sizes.get(item.metric_id), real) is True

    def _origin(self, path: str, item: Attribution) -> None:
        module = item.originating_module
        if item.label != UNFLAGGED:
            if module:
                self.found.append(
                    f"{path}: originating_module is only for Unflagged Risk Materialized"
                )
        elif not module:
            self.found.append(f"{path}: Unflagged Risk Materialized needs originating_module")
        elif module not in self.module_ids:
            self.found.append(f"{path}: originating_module {module} is not a methodology module")

    def _lessons(self, compared: tuple[str, ...]) -> None:
        if len(self.sub.lessons) > MAX_LESSONS:
            self.found.append("lessons: at most 2 lessons")
        for i, lesson in enumerate(self.sub.lessons):
            self._text(f"lessons[{i}].lesson", lesson.lesson)
            if not lesson.metric_ids or any(m not in compared for m in lesson.metric_ids):
                self.found.append(f"lessons[{i}]: metric_ids must name compared metrics")


def validate_ledger(
    *, submission: DecisionLedgerSubmission, upstream: Upstream, pack: Sequence[Source]
) -> tuple[str, ...]:
    """The validator's issues in rule order (the RULES tool-use issues are separate).

    Never de-duplicated: an attribution metric named twice is reported once per occurrence.
    Source, locator and quote failures carry ``readiness.citation_issues``' wording."""
    return _Checker(submission, upstream, pack).run()


# --- inputs and the Decimal diff ---------------------------------------------------------------


@dataclass(frozen=True)
class LedgerInputs:
    """Every operand ``derive`` reads, parsed by Python from the validated submission."""

    expected: Mapping[str, Decimal]  # observation metric -> quoted value (Prior Case record)
    expected_as_of: Mapping[str, date]
    realized: Mapping[str, Decimal]  # observation metric -> quoted value (later sources)
    realized_as_of: Mapping[str, date]
    decision_date: date
    downside_sizes: Mapping[str, RecordedSize]
    overall_label: str  # analyst judgment
    metric_labels: tuple[str, ...]  # analyst judgment, overall excluded
    pack_source_ids: tuple[str, ...]  # decision-record sources are counted in Python


def ledger_inputs(*, submission: DecisionLedgerSubmission, pack: Sequence[Source]) -> LedgerInputs:
    values: dict[str, dict[str, Decimal]] = {side: {} for side in SIDES}
    as_of: dict[str, dict[str, date]] = {side: {} for side in SIDES}
    for obs in submission.observations:
        values[obs.side][obs.metric] = Decimal(obs.value_text)
        as_of[obs.side][obs.metric] = _date(obs.as_of_text)
    overall = [a.label for a in submission.attributions if a.metric_id == OVERALL]
    if len(overall) != 1:
        raise ValueError("A validated submission has exactly one overall attribution")
    decision_text = submission.decision.decision_date.text
    if decision_text is None:
        raise ValueError("A validated submission states its decision date")
    return LedgerInputs(
        expected=values["expected"],
        expected_as_of=as_of["expected"],
        realized=values["realized"],
        realized_as_of=as_of["realized"],
        decision_date=_date(decision_text),
        downside_sizes={
            z.metric_id: RecordedSize(comparator=z.comparator, level=Decimal(z.level_text))
            for z in submission.thesis.downside_sizes
        },
        overall_label=overall[0],
        metric_labels=tuple(a.label for a in submission.attributions if a.metric_id != OVERALL),
        pack_source_ids=tuple(source.source_id for source in pack),
    )


@dataclass(frozen=True)
class MeasureDiff:
    expected: Decimal | None
    realized: Decimal | None
    variance: Decimal | None  # realized - expected; a zero is a known 0, never missing
    direction: Direction | None  # descriptive only
    magnitude: Decimal | None  # abs(variance), unsigned
    downside_breach: bool | None  # None without a size or a realized value


@dataclass(frozen=True)
class Derived:
    measures: Mapping[str, MeasureDiff]
    loan_mid_magnitude_bp: Decimal | None  # abs(variance) x 10000, basis points of par
    window_days: int | None
    window_end: date | None
    compared: tuple[str, ...]
    by_direction: Mapping[str, int] | None  # None with nothing compared, never 0
    labelled: int
    confirmed: int
    hit_rate: Decimal | None  # None when no decision carries a label other than Insufficient
    distribution: Mapping[str, int] | None  # None with nothing compared, never 0
    decisions_recorded: int
    decisions_required: int


def _level(metric: str, values: Mapping[str, Decimal], as_of: Mapping[str, date]) -> Decimal | None:
    """A measure's value; the quotation mid is (bid + offer) / 2 as a fraction of par, and not
    calculable from a bid and an offer quoted on different dates (8-7)."""
    if metric != "loan_mid":
        return values.get(metric)
    bid, offer = values.get("loan_bid"), values.get("loan_offer")
    if bid is None or offer is None or _split(as_of):
        return None
    return (bid + offer) / 2 / 100


def _direction(variance: Decimal) -> Direction:
    return "Higher" if variance > 0 else "Lower" if variance < 0 else "Unchanged"


def _measure(metric: str, inputs: LedgerInputs) -> MeasureDiff:
    expected = _level(metric, inputs.expected, inputs.expected_as_of)
    realized = _level(metric, inputs.realized, inputs.realized_as_of)
    variance = None if expected is None or realized is None else realized - expected
    size = inputs.downside_sizes.get(metric) if metric in SIZE_METRICS else None
    return MeasureDiff(
        expected=expected,
        realized=realized,
        variance=variance,
        direction=None if variance is None else _direction(variance),
        magnitude=None if variance is None else abs(variance),
        downside_breach=breached(size, realized),
    )


def derive(*, inputs: LedgerInputs) -> Derived:
    """Every derived value in exact Decimal; ``None`` is a value that cannot be calculated."""
    if inputs.overall_label not in LABELS:
        raise ValueError(f"Not an attribution label: {inputs.overall_label}")
    with localcontext(EXACT):
        measures = {metric: _measure(metric, inputs) for metric in METRICS}
        mid = measures["loan_mid"].magnitude
        bp = None if mid is None else Decimal(format((mid * 10000).normalize(), "f"))
        compared = tuple(m for m in METRICS if measures[m].variance is not None)
        end = max(inputs.realized_as_of.values(), default=None)
        labelled = 0 if inputs.overall_label == INSUFFICIENT else 1
        confirmed = 1 if inputs.overall_label == CONFIRMED else 0
        return Derived(
            measures=measures,
            loan_mid_magnitude_bp=bp,
            window_days=None if end is None else (end - inputs.decision_date).days,
            window_end=end,
            compared=compared,
            by_direction=(
                {d: sum(1 for m in compared if measures[m].direction == d) for d in DIRECTIONS}
                if compared
                else None
            ),
            labelled=labelled,
            confirmed=confirmed,
            hit_rate=Decimal(confirmed) / Decimal(labelled) if labelled else None,
            distribution=(
                {label: inputs.metric_labels.count(label) for label in LABELS} if compared else None
            ),
            decisions_recorded=inputs.pack_source_ids.count(DECISION_SOURCE),
            decisions_required=DECISIONS_REQUIRED,
        )


def current_decision(
    *, prior: tuple[str, str], cp6: tuple[str, str] | None
) -> tuple[Literal["known", "missing"], str]:
    """The decision line: the prior (action bias, confidence) against the settled CP-6 call."""
    if cp6 is None:
        return "missing", "CP-6 is not in this run, so no current decision is available to compare"
    bias, confidence = cp6
    if INSUFFICIENT in (bias, confidence):
        return (
            "missing",
            "CP-6 states Insufficient Information, so there is no comparable current decision",
        )
    prior_bias, prior_confidence = prior
    said_bias = (
        f"Action bias unchanged at {bias}"
        if bias == prior_bias
        else f"Action bias changed from {prior_bias} to {bias}"
    )
    said_confidence = (
        f"confidence unchanged at {confidence}"
        if confidence == prior_confidence
        else f"confidence changed from {prior_confidence} to {confidence}"
    )
    return "known", f"{said_bias}; {said_confidence}."


# --- composed result --------------------------------------------------------------------------------

_COLUMNS: Mapping[str, tuple[tuple[str, str], ...]] = {
    "T7.1": (
        ("action_bias", "Action bias"),
        ("confidence", "Confidence"),
        ("posture", "Posture"),
        ("instrument", "Instrument"),
        ("size", "Size"),
        ("decision_date", "Decision date"),
        ("decision_maker_role", "Decision-maker role"),
        ("module_status", "Module status"),
    ),
    "T7.2": (
        ("thesis", "Thesis"),
        ("greatest_uncertainty", "Greatest uncertainty"),
        ("downside_paths", "Flagged catalysts and downside paths"),
        ("expected_spread_return", "Expected spread or return"),
        ("expected_rating_path", "Expected rating path"),
        ("expected_hold", "Expected hold"),
        ("exit_triggers", "Exit triggers"),
        ("evidence_id", "Evidence"),
    ),
    "T7.3": (
        ("metric", "Metric"),
        ("realized_value", "Realized value"),
        ("as_of", "As-of date"),
        ("source", "Source"),
        ("interim_final", "Interim or final"),
        ("evidence_id", "Evidence"),
    ),
    "T7.4": (
        ("metric", "Metric"),
        ("expected", "Expected"),
        ("realized", "Realized"),
        ("direction", "Variance direction"),
        ("magnitude", "Variance magnitude"),
        ("confidence", "Confidence"),
        ("evidence_id", "Evidence"),
    ),
    "T7.5": (
        ("variance", "Variance"),
        ("breach", "Downside size breached"),
        ("label", "Attribution label"),
        ("process_sound", "Process sound"),
        ("originating_module", "Originating module"),
        ("basis", "Basis"),
        ("evidence_id", "Evidence"),
    ),
    "T7.6": (
        ("pattern", "Pattern"),
        ("target_module", "Target module"),
        ("specific_prior", "Specific prior"),
        ("supporting_decisions", "Supporting decisions"),
        ("advisory_recommendation", "Advisory recommendation"),
        ("decisions_recorded", "Decisions recorded"),
        ("decisions_required", "Decisions required"),
    ),
    "T7.7": (("value", "Value"), ("basis", "Basis")),
    "T7.8": (
        ("gap", "Gap"),
        ("missing_item", "Missing item"),
        ("why_it_matters", "Why it matters"),
        ("impact_on_output", "Impact on output"),
        ("follow_up", "Required follow-up"),
    ),
    WHAT_CHANGED: (("value", "Value"),),
}
_TITLES: Mapping[str, tuple[str, str]] = {  # table id -> (title, row header)
    "T7.1": ("Decision record", "Decision"),
    "T7.2": ("Thesis and expectation register", "Decision"),
    "T7.3": ("Realized outcome log", "Metric"),
    "T7.4": ("Variance table", "Metric"),
    "T7.5": ("Attribution table", "Measure"),
    "T7.6": ("Calibration register (advisory)", "Gate"),
    "T7.7": ("Track-record dashboard", "Measure"),
    "T7.8": ("Gaps ledger", "Gap"),
    WHAT_CHANGED: ("What changed since the last Report", "Change"),
}
_VAR_CLAIMS = (
    ("CP-8-VAR-01", "total_leverage", "Total leverage was recorded at"),
    ("CP-8-VAR-02", "interest_cover", "Interest cover was recorded at"),
    ("CP-8-VAR-03", "loan_mid", "The mid level of the term loan quotation was recorded at"),
)
_LINES: Mapping[str, tuple[str, str]] = {  # claim id -> what-changed row (id, label)
    "CP-8-VAR-01": ("total_leverage", "Total leverage"),
    "CP-8-VAR-02": ("interest_cover", "Interest cover"),
    "CP-8-VAR-03": ("loan_mid", "Term loan quotation"),
    "CP-8-OUT-01": ("outcome", "Outcome"),
    "CP-8-ATT-01": ("attribution", "Attribution"),
}
_PROCESS_SAID: Mapping[str, str] = {
    "Y": "the process is judged sound",
    "N": "the process is judged unsound",  # 8-4
    NOT_ASSESSED: "process quality is not assessed",
}
_NOT_COMPARED: Mapping[tuple[str, ...], tuple[str, str, str]] = {  # 8-1, 8-24
    # the sides lacking a value -> (missing item, side said, follow-up)
    ("expected",): ("Expected {}", "expected", "Cite the expected {} from the Prior Case record"),
    ("realized",): (
        "Realized {}",
        "realized",
        "Supply a dated post-decision source that states {}",
    ),
    ("expected", "realized"): (
        "Expected and realized {}",
        "expected or realized",
        (
            "Cite the expected {} from the Prior Case record and supply a dated post-decision "
            "source that states it"
        ),
    ),
}
COMPARED_ONLY = "Variance and attribution are shown only for the compared measures"
_SAME_DAY_THEN: Mapping[str, str] = {  # round 6h: the missing side -> the follow-up's 2nd clause
    "realized": "supply a dated post-decision source that states the quotation",
    "expected": "cite the expected quotation from the Prior Case record",
}
_EXPECTATIONS = (  # T7.8 rows of the unrecorded expectations: (field, item, impact)
    (
        "expected_spread_return",
        "Expected spread or return",
        "Spread and return variance cannot be compared",
    ),
    ("expected_rating_path", "Expected rating path", "Rating migration cannot be compared"),
    ("expected_hold", "Expected holding period", "Holding period against plan cannot be compared"),
)
NOT_CALCULABLE = "Not calculable: needs an expected and a realized value"
NOT_MEANINGFUL = "Not meaningful: the calibration gate is not met"
NO_ORIGIN = "Not applicable: no originating process gap is named"
NO_PATH = "Not applicable: no named downside path is cited"


@dataclass(frozen=True)
class LedgerReport:
    inputs: LedgerInputs
    derived: Derived
    facts: tuple[Fact, ...]
    tables: tuple[ReportTable, ...]
    claims: tuple[Claim, ...]
    limitations: tuple[str, ...]  # own limitations; execution adds the inherited set (Stage 2)


class _Cells:
    """The facts of one result in table, row and column order; each cell is ``<table>.<row>.<field>``.

    A calculated fact carries ``calc:<fact_id>`` as its calculation id."""

    def __init__(self, sources: Mapping[str, Source]) -> None:
        self.sources = sources
        self.facts: list[Fact] = []
        self.rows: dict[str, list[tuple[str, str, list[str]]]] = {}
        self.table_id = ""

    def row(self, table_id: str, row_id: str, label: str) -> None:
        self.table_id = table_id
        self.rows.setdefault(table_id, []).append((row_id, label, []))

    def _add(self, field: str, values: dict[str, object]) -> None:
        row_id, _, ids = self.rows[self.table_id][-1]
        fact_id = f"{self.table_id}.{row_id}.{field}"
        if values.get("value_class") == "calculated":
            values["calculation_id"] = "calc:" + fact_id
        label = dict(_COLUMNS[self.table_id])[field]
        self.facts.append(
            Fact.model_validate(
                {
                    "fact_id": fact_id,
                    "label": label,
                    "table_id": self.table_id,
                    "row_id": row_id,
                    "field": field,
                    **values,
                }
            )
        )
        ids.append(fact_id)

    def citations(self, refs: Iterable[QuoteRef]) -> tuple[Citation, ...]:
        out: dict[tuple[str, str, str], Citation] = {}
        for ref in refs:
            sha = self.sources[ref.source_id].sha256
            if sha is None:
                raise ValueError(f"Cited source is not ready: {ref.source_id}")
            out.setdefault(
                (ref.source_id, ref.locator, ref.quote),
                Citation(
                    source_id=ref.source_id, source_sha256=sha, locator=ref.locator, quote=ref.quote
                ),
            )
        return tuple(out.values())

    def text(
        self,
        field: str,
        text: str,
        *,
        refs: Iterable[QuoteRef] = (),
        value_class: str | None = None,
    ) -> None:
        self._add(
            field, {"text": text, "citations": self.citations(refs), "value_class": value_class}
        )

    def number(
        self,
        field: str,
        amount: Decimal,
        unit: str,
        *,
        period: str,
        decimals: int | None = None,
        refs: Iterable[QuoteRef] = (),
        value_class: str = "calculated",
        formula: str | None = None,
    ) -> None:
        self._add(
            field,
            {
                "amount": amount,
                "unit": unit,
                "decimals": decimals,
                "period": period,
                "citations": self.citations(refs),
                "value_class": value_class,
                "formula": formula,
            },
        )

    def gap(
        self,
        field: str,
        reason: str,
        *,
        unit: str | None = None,
        refs: Iterable[QuoteRef] = (),
        not_applicable: bool = False,
    ) -> None:
        self._add(
            field,
            {
                "status": "not_applicable" if not_applicable else "missing",
                "unit": unit,
                "limitation": reason,
                "citations": self.citations(refs),
            },
        )

    def table(self, table_id: str) -> ReportTable:
        title, header = _TITLES[table_id]
        return ReportTable(
            table_id=table_id,
            title=title,
            row_header=header,
            columns=tuple(TableColumn(field=f, label=label) for f, label in _COLUMNS[table_id]),
            rows=tuple(
                TableRow(row_id=row_id, label=label, fact_ids=tuple(ids))
                for row_id, label, ids in self.rows.get(table_id, [])
            ),
        )


def _some(ref: QuoteRef | None) -> tuple[QuoteRef, ...]:
    return () if ref is None else (ref,)


class _Composer:
    """T7.1-T7.8, the claims, the ``cp8.what_changed`` rails table and own limitations of one
    validated submission. Fails closed on every state whose wording nothing pins."""

    def __init__(
        self,
        submission: DecisionLedgerSubmission,
        inputs: LedgerInputs,
        derived: Derived,
        pack: Sequence[Source],
        upstream: Upstream,
    ) -> None:
        self.sub = submission
        self.inputs = inputs
        self.d = derived
        self.up = upstream
        self.cells = _Cells({source.source_id: source for source in pack})
        self.absent = submission.outcome_absence
        self.observed = {(o.side, o.metric): o for o in submission.observations}
        self.attributed = {a.metric_id: a for a in submission.attributions}
        self.levels = {c.metric_id: c.level for c in submission.confidence}
        self.decided = inputs.decision_date
        self.run_period = f"Run as of {upstream.as_of.isoformat()}"
        quote = submission.decision.decision_date.quote
        if quote is None:
            raise ValueError("A validated decision date has its quote")
        self.decision_quote = quote

    # helpers

    def _label(self, ref: QuoteRef) -> str:
        return f"{self.cells.sources[ref.source_id].name}, {ref.locator}"

    def _evidence(self, refs: Sequence[QuoteRef]) -> str:
        if not refs:  # T7.2 and the window always cite; T7.4 handles none itself (8-24)
            raise ValueError("invariant: an evidence cell lists at least one cited quote")
        return "; ".join(dict.fromkeys(self._label(ref) for ref in refs))

    def _not_observed(self, metric: str | None = None) -> str:
        """The gap reason of an absent realized entry: outcome_absence's, else 8-1's for a
        measure. The default and window rows exist whenever a realized observation does."""
        if self.absent is not None:
            return self.absent.reason
        if metric is None:
            raise ValueError("invariant: a realized outcome has its default and window rows")
        return f"Not stated: no realized {_name(metric)} is recorded from a post-decision source"

    def _dates(self, side: str) -> Mapping[str, date]:
        return self.inputs.expected_as_of if side == "expected" else self.inputs.realized_as_of

    def _refs(self, side: str, metric: str) -> list[QuoteRef]:
        return [
            self.observed[(side, p)].quote for p in _parts(metric) if (side, p) in self.observed
        ]

    def _as_of(self, side: str, metric: str) -> date:
        dates = {self._dates(side)[p] for p in _parts(metric)}
        if len(dates) != 1:  # derive gives no mid from a split quotation (8-7)
            raise ValueError(f"invariant: a known {side} {metric} has one as-of date")
        return dates.pop()

    def compose(self) -> LedgerReport:
        with localcontext(EXACT):
            self._decision_record()
            self._thesis_register()
            self._outcome_log()
            self._variances()
            self._attributions()
            self._calibration()
            self._dashboard()
            self._gaps()
            tables = [self.cells.table(t) for t in _TITLES if t != WHAT_CHANGED]
            claims = self._claims()
            self._what_changed(claims)
            tables.append(self.cells.table(WHAT_CHANGED))
        return LedgerReport(
            inputs=self.inputs,
            derived=self.d,
            facts=tuple(self.cells.facts),
            tables=tuple(tables),
            claims=tuple(claims),
            limitations=self._limitations(),
        )

    # T7.1, T7.2

    def _decision_cell(self, field: str, item: DecisionField) -> None:
        if item.absence is not None:
            self.cells.gap(field, item.absence.reason, refs=_some(item.absence.quote))
        elif item.text is not None and item.quote is not None:
            self.cells.text(field, item.text, refs=(item.quote,), value_class="source")
        else:
            raise ValueError(f"A validated decision field has a text or an absence: {field}")

    def _module_status(self) -> str:
        """r14 REF_CP-8_01: Completed only with no outcome absence, every measure compared and no
        Interim entry; no source type here states a closed window, so a realized entry is Interim."""
        interim = any(side == "realized" for side, _ in self.observed) or (
            self.sub.default_restructuring is not None or self.d.window_days is not None
        )
        complete = self.absent is None and self.d.compared == METRICS and not interim
        return "Completed" if complete else "Completed with Limitations"

    def _decision_record(self) -> None:
        dec, cells = self.sub.decision, self.cells
        cells.row("T7.1", "d01", "Decision")
        self._decision_cell("action_bias", dec.action_bias)
        self._decision_cell("confidence", dec.confidence)
        self._decision_cell("posture", dec.posture)
        self._decision_cell("instrument", dec.instrument)
        self._decision_cell("size", dec.size)
        cells.text(
            "decision_date",
            format_date(self.decided),
            refs=(self.decision_quote,),
            value_class="source",
        )
        self._decision_cell("decision_maker_role", dec.decision_maker_role)
        cells.text("module_status", self._module_status(), value_class="calculated")

    def _thesis_register(self) -> None:
        th, cells = self.sub.thesis, self.cells
        cells.row("T7.2", "t01", "Thesis as decided")
        for field, item in (
            ("thesis", th.thesis),
            ("greatest_uncertainty", th.greatest_uncertainty),
            ("downside_paths", th.downside_paths),
            ("expected_spread_return", th.expected_spread_return),
            ("expected_rating_path", th.expected_rating_path),
            ("expected_hold", th.expected_hold),
            ("exit_triggers", th.exit_trigger),
        ):
            if item.absence is not None:
                cells.gap(field, item.absence.reason, refs=_some(item.absence.quote))
            elif item.quote is not None:
                cells.text(field, item.quote.quote, refs=(item.quote,), value_class="source")
            else:
                raise ValueError(f"A validated thesis field has a quote or an absence: {field}")
        quoted = (th.thesis, th.greatest_uncertainty, th.downside_paths, th.exit_trigger)
        refs = [item.quote for item in quoted if item.quote is not None]
        cells.text("evidence_id", self._evidence(refs), refs=refs, value_class="calculated")

    # T7.3

    def _absent_entry(self, why: str, unit: str | None) -> None:
        cells = self.cells
        cells.gap("realized_value", why, unit=unit)
        cells.gap("as_of", why)
        cells.gap("source", why)
        cells.text("interim_final", INTERIM, value_class="calculated")
        cells.gap("evidence_id", why)

    def _quoted_entry(self, ref: QuoteRef, as_of: date) -> None:
        cells, label = self.cells, self._label(ref)
        cells.text("as_of", format_date(as_of), refs=(ref,), value_class="source")
        cells.text("source", label, refs=(ref,), value_class="source")
        cells.text("interim_final", INTERIM, value_class="calculated")
        cells.text("evidence_id", label, refs=(ref,), value_class="calculated")

    def _outcome_log(self) -> None:
        cells = self.cells
        for metric in OBS_METRICS:
            cells.row("T7.3", metric, METRIC_NAME[metric])
            cells.text("metric", METRIC_NAME[metric])
            unit, places = OBS_UNIT[metric]
            obs = self.observed.get(("realized", metric))
            if obs is None:
                self._absent_entry(self._not_observed(metric), unit)
                continue
            as_of = _date(obs.as_of_text)
            quoted = Decimal(obs.value_text)
            value = quoted if unit == "MULTIPLE" else quoted / 100
            span = "Twelve months to" if metric in SIZE_METRICS else "Quotation of"
            cells.number(
                "realized_value",
                value,
                unit,
                decimals=places,
                refs=(obs.quote,),
                value_class="source",
                period=f"{span} {as_of.isoformat()}",
            )
            self._quoted_entry(obs.quote, as_of)
        cells.row("T7.3", "default_restructuring", "Default or restructuring incidence")
        cells.text("metric", "Default or restructuring incidence")
        statement = self.sub.default_restructuring
        if statement is None:
            self._absent_entry(self._not_observed(), None)
        else:
            q = statement.quote
            cells.text("realized_value", q.quote, refs=(q,), value_class="source")
            self._quoted_entry(q, _date(statement.as_of_text))
        self._window()

    def _window(self) -> None:
        cells = self.cells
        cells.row("T7.3", "window", "Observation window")
        cells.text("metric", "Observation window since the decision")
        days, end = self.d.window_days, self.d.window_end
        if days is None or end is None:
            self._absent_entry(self._not_observed(), "days")
            return
        real = [o.quote for o in self.sub.observations if o.side == "realized"]
        refs = [self.decision_quote, *real]
        cells.number(
            "realized_value",
            Decimal(days),
            "days",
            refs=refs,
            formula="latest realized as-of date - decision date (calendar days)",
            period=f"Decision {self.decided.isoformat()} to {end.isoformat()}",
        )
        cells.text("as_of", format_date(end), refs=real, value_class="calculated")
        cells.text(
            "source",
            "Derived from the decision date and the latest realized as-of date",
            value_class="calculated",
        )
        cells.text("interim_final", INTERIM, value_class="calculated")
        cells.text("evidence_id", self._evidence(refs), refs=refs, value_class="calculated")

    # T7.4

    def _value_cell(self, side: str, metric: str, value: Decimal | None) -> None:
        unit, places = ("decimal_fraction", 3) if metric == "loan_mid" else ("MULTIPLE", 2)
        refs = self._refs(side, metric)
        split = _split(self._dates(side)) if metric == "loan_mid" else None
        if value is None:
            if split is not None:  # 8-7
                reason = (
                    f"Not calculable: the {side} bid and offer are quoted on different dates "
                    f"({split[0].isoformat()} and {split[1].isoformat()})"
                )
            elif side == "expected":  # 8-2
                reason = (
                    f"Not stated: no expected {_name(metric)} is recorded from the Prior Case "
                    "record"
                )
            else:
                reason = self._not_observed(metric)
            self.cells.gap(side, reason, unit=unit)
            return
        as_of = self._as_of(side, metric).isoformat()
        if metric == "loan_mid":
            self.cells.number(
                side,
                value,
                unit,
                decimals=places,
                refs=refs,
                formula="(bid + offer) / 2",
                period=f"Quotation of {as_of}",
            )
            return
        span = "Recorded at Approval" if side == "expected" else "Twelve months to"
        self.cells.number(
            side,
            value,
            unit,
            decimals=places,
            refs=refs,
            value_class="source",
            period=f"{span} {as_of}",
        )

    def _variance_cells(self, metric: str, refs: Sequence[QuoteRef]) -> None:
        m, cells = self.d.measures[metric], self.cells
        unit, places = ("decimal_fraction", 3) if metric == "loan_mid" else ("MULTIPLE", 2)
        if m.direction is None or m.magnitude is None:
            cells.gap("direction", NOT_CALCULABLE)
            cells.gap("magnitude", NOT_CALCULABLE, unit=unit)
            return
        cells.text("direction", m.direction, refs=refs, value_class="calculated")
        period = (
            f"Recorded at Approval {self.decided.isoformat()} to "
            f"{self._as_of('realized', metric).isoformat()}"
        )
        bp = self.d.loan_mid_magnitude_bp
        if metric != "loan_mid":
            cells.number(
                "magnitude",
                m.magnitude,
                unit,
                decimals=places,
                refs=refs,
                formula="abs(realized - expected)",
                period=period,
            )
        elif bp is not None:
            cells.number(
                "magnitude",
                bp,
                "basis_points",
                refs=refs,
                formula="abs(realized - expected) x 10000 (basis points of par)",
                period=period,
            )
        else:
            raise ValueError("A compared quotation has its basis-point magnitude")

    def _variances(self) -> None:
        cells = self.cells
        for metric in METRICS:
            m = self.d.measures[metric]
            refs = [*self._refs("expected", metric), *self._refs("realized", metric)]
            cells.row("T7.4", metric, METRIC_NAME[metric])
            cells.text("metric", METRIC_NAME[metric])
            self._value_cell("expected", metric, m.expected)
            self._value_cell("realized", metric, m.realized)
            self._variance_cells(metric, refs)
            level = self.levels.get(metric)
            if level is None:
                cells.gap("confidence", "Not assessed: the measure is not compared")
            else:
                cells.text("confidence", level, value_class="analyst_judgment")
            if refs:
                cells.text("evidence_id", self._evidence(refs), refs=refs, value_class="calculated")
            else:  # 8-24
                cells.gap("evidence_id", f"Not stated: no quote is cited for {_name(metric)}")

    # T7.5

    def _breach_cell(self, metric: str) -> None:
        cells = self.cells
        if metric == OVERALL:
            cells.gap(
                "breach",
                "Not applicable: a downside size applies to a measure, not to the decision overall",
                not_applicable=True,
            )
            return
        if metric == "loan_mid":
            cells.gap(
                "breach",
                "Not applicable: no downside size can be recorded for the quotation",
                not_applicable=True,
            )
            return
        breach = self.d.measures[metric].downside_breach
        size = next((z for z in self.sub.thesis.downside_sizes if z.metric_id == metric), None)
        if size is None:  # 8-5: missing, not not_applicable: a size could be recorded
            cells.gap(
                "breach",
                "Not calculable: the Prior Case record has no recorded downside size for "
                + _name(metric),
            )
            return
        if breach is None:
            raise ValueError(f"invariant: a compared {metric} with a size has a breach decision")
        cells.text(
            "breach",
            "Breached" if breach else "Not breached",
            refs=(size.quote, self.observed[("realized", metric)].quote),
            value_class="calculated",
        )

    def _attributions(self) -> None:
        cells = self.cells
        down = self.sub.thesis.downside_paths.quote
        for metric in (*self.d.compared, OVERALL):
            item = self.attributed[metric]
            direction = None if metric == OVERALL else self.d.measures[metric].direction
            name = "Decision overall" if direction is None else METRIC_NAME[metric]
            cells.row("T7.5", metric, name)
            variance = name if direction is None else f"{name}: {direction.lower()}"
            cells.text("variance", variance, value_class="calculated")
            self._breach_cell(metric)
            cells.text("label", item.label, value_class="analyst_judgment")
            cells.text("process_sound", item.process_sound, value_class="analyst_judgment")
            if item.originating_module:
                cells.text(
                    "originating_module", item.originating_module, value_class="analyst_judgment"
                )
            else:
                cells.gap("originating_module", NO_ORIGIN, not_applicable=True)
            cells.text("basis", item.basis, value_class="analyst_judgment")
            if item.flag_quote and down is not None:
                cells.text(
                    "evidence_id",
                    f"{self._label(down)} (named downside path)",
                    refs=(down,),
                    value_class="calculated",
                )
            else:
                cells.gap("evidence_id", NO_PATH, not_applicable=True)

    # T7.6, T7.7

    def _calibration(self) -> None:
        recorded, required = self.d.decisions_recorded, self.d.decisions_required
        if recorded != 1 or required != DECISIONS_REQUIRED:  # 8-8: unique pack ids; 0 is BLOCKED
            raise ValueError(f"invariant: the calibration gate reads one record, not {recorded}")
        cells = self.cells
        cells.row("T7.6", "gate", "Calibration gate")
        cells.text(
            "pattern",
            "No pattern assessed: the calibration gate needs at least three comparable decisions",
            value_class="calculated",
        )
        for field in (
            "target_module",
            "specific_prior",
            "supporting_decisions",
            "advisory_recommendation",
        ):
            cells.gap(field, NOT_MEANINGFUL, not_applicable=True)
        cells.number(
            "decisions_recorded",
            Decimal(recorded),
            "decisions",
            formula=(
                "count of Prior Case records in the pack (decision-record sources read by this step)"
            ),
            period=self.run_period,
        )
        cells.number(
            "decisions_required",
            Decimal(required),
            "decisions",
            formula=(
                "schema rule: the calibration gate needs at least 3 comparable decisions "
                "(r14 REF_CP-8_06 constant)"
            ),
            period=self.run_period,
        )

    def _count(self, row_id: str, label: str, count: int, basis: str) -> None:
        self.cells.row("T7.7", row_id, label)
        self.cells.number(
            "value", Decimal(count), "decisions", formula="count", period=self.run_period
        )
        self.cells.text("basis", basis)

    def _dashboard(self) -> None:
        cells, d = self.cells, self.d
        cells.row("T7.7", "hit_rate", "Hit rate")
        if d.hit_rate is None:
            cells.gap(
                "value",
                "Not calculable: no decision carries an attribution label other than "
                "Insufficient Information",
            )
        else:
            cells.number(
                "value",
                d.hit_rate,
                "decimal_fraction",
                decimals=1,
                formula=(
                    "decisions labelled Thesis Confirmed / decisions with a label other than "
                    "Insufficient Information"
                ),
                period=self.run_period,
            )
        cells.text("basis", "Over the decisions recorded in this run")
        self._count(
            "decisions_labelled",
            "Decisions with an attribution label",
            d.labelled,
            "Labels other than Insufficient Information",
        )
        self._count(
            "decisions_confirmed",
            "Decisions labelled Thesis Confirmed",
            d.confirmed,
            "Overall label of the decision",
        )
        cells.row("T7.7", "cut", "Realized against expected by pathway, sector and sponsor")
        cells.gap(
            "value",
            "Not recorded: the pathway, sector and sponsor of the prior decision are not in the "
            "Prior Case record",
        )
        cells.text("basis", "A cut needs the attributes of the decision")
        self._distribution()
        self._lessons()

    def _distribution(self) -> None:
        cells, distribution = self.cells, self.d.distribution
        if distribution is None:
            cells.row("T7.7", "distribution", "Attribution distribution")
            cells.gap(
                "value", "Not calculable: no metric was compared, so no metric attribution exists"
            )
            cells.text("basis", "Metric attributions, overall excluded")
            return
        for label in LABELS:
            slug = re.sub(r"[^a-z]+", "_", label.lower()).strip("_")
            cells.row("T7.7", f"dist_{slug}", f"Attribution: {label}")
            cells.number(
                "value",
                Decimal(distribution[label]),
                "attributions",
                formula="count of metric attributions with this label",
                period=self.run_period,
            )
            cells.text("basis", "Metric attributions, overall excluded")

    def _lessons(self) -> None:
        cells = self.cells
        if not self.sub.lessons:
            cells.row("T7.7", "lessons", "Lessons")
            cells.gap("value", "Not stated: no compared metric supports a lesson")
            cells.text("basis", "A lesson needs a compared metric")
            return
        for i, lesson in enumerate(self.sub.lessons, 1):
            cells.row("T7.7", f"lesson_{i:02d}", f"Lesson {i}")
            cells.text("value", lesson.lesson, value_class="analyst_judgment")
            names = ", ".join(METRIC_NAME[m] for m in lesson.metric_ids)
            cells.text("basis", f"Supported by {names}", value_class="calculated")

    # T7.8

    def _gap_row(
        self, row_id: str, label: str, item: str, why: str, impact: str, follow_up: str
    ) -> None:
        cells = self.cells
        cells.row("T7.8", row_id, label)
        for field, text in (
            ("gap", label),
            ("missing_item", item),
            ("why_it_matters", why),
            ("impact_on_output", impact),
            ("follow_up", follow_up),
        ):
            cells.text(field, text)

    def _not_compared(self, metric: str) -> None:
        """8-1, 8-24 and round 6c (b): one row per uncompared measure. Under outcome_absence
        the outcome row covers the realized side (6c (d)); a split side records both figures."""
        m = self.d.measures[metric]
        split = [s for s in SIDES if metric == "loan_mid" and _split(self._dates(s))]
        lacking = tuple(
            side
            for side, value in (("expected", m.expected), ("realized", m.realized))
            if value is None
            and side not in split
            and not (side == "realized" and self.absent is not None)
        )
        row_id, gap, name = (
            f"not_compared_{metric}",
            f"{METRIC_NAME[metric]} not compared",
            _name(metric),
        )
        if split and lacking:  # round 6h: one side split, the other side has no quotation
            (cut,), (absent,) = split, lacking
            self._gap_row(
                row_id,
                gap,
                f"Same-day {cut} bid and offer, and a {absent} quotation",
                f"The {cut} bid and offer are quoted on different dates and no {absent} quotation "
                "is recorded, so no mid level is calculated and its variance cannot be measured",
                COMPARED_ONLY,
                "Cite a bid and an offer quoted on the same day; " + _SAME_DAY_THEN[absent],
            )
        elif split:
            sides = _listed(split)
            self._gap_row(
                row_id,
                gap,
                f"Same-day {sides} bid and offer",
                f"The {sides} bid and offer are quoted on different dates, so no mid level is "
                "calculated and its variance cannot be measured",
                COMPARED_ONLY,
                "Cite a bid and an offer quoted on the same day",
            )
        elif lacking:
            item, said, follow_up = _NOT_COMPARED[lacking]
            self._gap_row(
                row_id,
                gap,
                item.format(name),
                f"No {said} value is recorded for {name}, so its variance cannot be measured",
                COMPARED_ONLY,
                follow_up.format(name),
            )

    def _gaps(self) -> None:
        dec, th = self.sub.decision, self.sub.thesis
        for field, decision_item in (("posture", dec.posture), ("size", dec.size)):
            a = decision_item.absence
            if a is not None:
                self._gap_row(
                    field,
                    f"Decision {field} not recorded",
                    f"Decision {field}",
                    a.reason,
                    "Portfolio-level attribution is limited",
                    a.follow_up,
                )
        unrecorded = {
            "expected_spread_return": th.expected_spread_return,
            "expected_rating_path": th.expected_rating_path,
            "expected_hold": th.expected_hold,
        }
        for field, item, impact in _EXPECTATIONS:
            a = unrecorded[field].absence
            if a is not None:
                self._gap_row(field, f"{item} not recorded", item, a.reason, impact, a.follow_up)
        for metric in METRICS:
            if metric not in self.d.compared:
                self._not_compared(metric)
        if self.absent is not None:
            self._gap_row(
                "outcome",
                "No realized outcome",
                "Realized outcomes",
                self.absent.reason,
                "Outcome log, variances and attribution are absent",
                self.absent.follow_up,
            )
        if self.up.cp6 is None or INSUFFICIENT in self.up.cp6:  # 8-20: CP-6 Insufficient
            why, follow_up = (
                ("CP-6 is not in this run", "Select CP-6 in the run")
                if self.up.cp6 is None
                else (
                    "CP-6 states Insufficient Information",
                    "Complete the CP-6 committee decision",
                )
            )
            self._gap_row(
                "current_decision",
                "No current decision to compare",
                "Current committee decision",
                why,
                "The decision line of the what-changed block is missing",
                follow_up,
            )
        self._gap_row(
            "calibration_gate",
            "Calibration gate not met",
            "Comparable decisions",
            "A single decision cannot show a pattern",
            "No calibration recommendation is produced",
            "Supply further comparable Prior Case records",
        )
        for i, gap in enumerate(self.sub.extra_gaps, 1):
            self.cells.row("T7.8", f"extra_{i:02d}", gap.gap)
            for field, text in (
                ("gap", gap.gap),
                ("missing_item", gap.missing_item),
                ("why_it_matters", gap.why_it_matters),
                ("impact_on_output", gap.impact_on_output),
                ("follow_up", gap.follow_up),
            ):
                self.cells.text(field, text, value_class="analyst_judgment")

    # claims and the what-changed rails table

    def _figure(self, facts: Mapping[str, Fact], fact_id: str) -> str:
        unit = figure_unit(facts[fact_id])
        if unit is None:
            raise ValueError(f"A figure reference needs a numeric fact: {fact_id}")
        return "{" + fact_id + "|" + unit + "}"

    def _claims(self) -> list[Claim]:
        facts = {fact.fact_id: fact for fact in self.cells.facts}
        texts: list[tuple[str, str]] = []
        for claim_id, metric, lead in _VAR_CLAIMS:
            direction = self.d.measures[metric].direction
            if metric not in self.d.compared or direction is None:
                continue
            was = self._figure(facts, f"T7.4.{metric}.expected")
            now = self._figure(facts, f"T7.4.{metric}.realized")
            if direction == "Unchanged":  # 8-3
                texts.append((claim_id, f"{lead} {was} and is now {now}, unchanged."))
                continue
            by = self._figure(facts, f"T7.4.{metric}.magnitude")
            texts.append((claim_id, f"{lead} {was} and is now {now}, {direction.lower()} by {by}."))
        if self.d.window_days is not None:
            window = self._figure(facts, "T7.3.window.realized_value")
            texts.append(
                (
                    "CP-8-WIN-01",
                    f"The latest realized observation falls {window} after the decision.",
                )
            )
        else:
            texts.append(
                (
                    "CP-8-OUT-01",
                    (
                        "No realized outcome is recorded, so the window since the decision "
                        "[T7.3.window.realized_value] and every variance are missing."
                    ),
                )
            )
        overall = self.attributed[OVERALL]
        said = _PROCESS_SAID.get(overall.process_sound)
        if said is None:  # the validator admits only PROCESS
            raise ValueError(f"invariant: an overall process judged {overall.process_sound}")
        texts.append(("CP-8-ATT-01", f"The attribution is {overall.label}; {said}."))
        recorded = self._figure(facts, "T7.6.gate.decisions_recorded")
        required = self._figure(facts, "T7.6.gate.decisions_required")
        texts.append(
            (
                "CP-8-CAL-01",
                (
                    f"The calibration gate is not met: {recorded} recorded and {required} "
                    "needed, so no recalibration is advised."
                ),
            )
        )
        texts.append(("CP-8-VIEW-01", self.sub.synthesis.text))
        bound = bind(self.cells.facts)
        for claim_id, text in texts:
            found = issues(text, bound)
            if found:
                raise ValueError(f"Claim {claim_id} does not resolve: {'; '.join(found)}")
        return [Claim(claim_id=cid, text=text, citations=()) for cid, text in texts]

    def _resolved(self, text: str) -> str:
        """Run text spelled by Python: each figure as its cell, each gap chip as ``∅ G#``."""
        facts = {fact.fact_id: fact for fact in self.cells.facts}
        gaps = {fid for fid, fact in facts.items() if fact.status != "known"}
        out: list[str] = []
        for run in tokenize(text, gaps=gaps):
            if run.kind == "text":
                out.append(run.text)
            elif run.kind == "gap":
                fact = facts[run.text]
                out.append(
                    f"∅ {GAP_PLACEHOLDER}" + (" n.m." if fact.status == "not_applicable" else "")
                )
            else:
                fact = facts[run.text]
                unit_class, _, shown = fact_spelling(fact, None)
                unit = figure_unit(fact) if unit_class == "amount" else None
                out.append(f"{shown} {unit}" if unit else shown)
        return "".join(out)

    def _what_changed(self, claims: Sequence[Claim]) -> None:
        cells, dec = self.cells, self.sub.decision
        if dec.action_bias.text is None or dec.confidence.text is None:
            raise ValueError("A validated decision states its action bias and confidence")
        kind, said = current_decision(
            prior=(dec.action_bias.text, dec.confidence.text), cp6=self.up.cp6
        )
        cells.row(WHAT_CHANGED, "decision", "Decision")
        if kind == "known":
            cells.text("value", said, value_class="calculated")
        else:
            cells.gap("value", said)
        for claim in claims:
            line = _LINES.get(claim.claim_id)
            if line is not None:
                cells.row(WHAT_CHANGED, *line)
                cells.text("value", self._resolved(claim.text), value_class="calculated")
        cells.row(WHAT_CHANGED, "summary", "Summary")
        cells.text("value", self.sub.synthesis.text, value_class="analyst_judgment")

    # own limitations

    def _limitations(self) -> tuple[str, ...]:
        authority = _authority(self.up.authority, DECISION_SOURCE)
        out = [LIM_RECORD if authority == "unknown" else LIM_CLASSIFIED.format(authority)]  # 8-9
        dec, th = self.sub.decision, self.sub.thesis
        absences = (
            dec.posture.absence,
            dec.size.absence,
            th.expected_spread_return.absence,
            th.expected_rating_path.absence,
            th.expected_hold.absence,
        )
        absent = [text for text, a in zip(UNRECORDED, absences, strict=True) if a is not None]
        if absent:  # 8-6
            listed = _listed(absent)
            verb = "is" if len(absent) == 1 else "are"
            out.append(
                f"{listed[0].upper()}{listed[1:]} {verb} not recorded in the Prior Case record"
            )
        exit_trigger = th.exit_trigger.quote
        if exit_trigger is None:  # 8-17
            out.append(LIM_NO_EXIT)
        elif re.search(r"[0-9]", _norm(exit_trigger.quote)) is None:  # 6c (f): ASCII digits
            out.append(LIM_EXIT)
        out.append(LIM_NO_OUTCOME if self.absent is not None else LIM_INTERIM)
        uncompared = [_name(m) for m in METRICS if m not in self.d.compared]
        if self.absent is None and uncompared:  # 8-1
            out.append(LIM_NOT_COMPARED.format(_listed(uncompared)))
        out.append(LIM_ONE_DECISION)
        if self.up.cp6 is None:
            out.append(LIM_NO_CP6)
        elif INSUFFICIENT in self.up.cp6:  # 8-20
            out.append(LIM_CP6_INSUFFICIENT)
        return tuple(out)


def decision_ledger(
    *, pack: Sequence[Source], submission: DecisionLedgerSubmission, upstream: Upstream
) -> LedgerReport:
    """The composed result of a submission; fails closed on any validator issue."""
    found = validate_ledger(submission=submission, upstream=upstream, pack=pack)
    if found:
        raise ValueError("A submission with validator issues does not compose: " + "; ".join(found))
    inputs = ledger_inputs(submission=submission, pack=pack)
    return _Composer(submission, inputs, derive(inputs=inputs), pack, upstream).compose()
