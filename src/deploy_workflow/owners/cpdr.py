"""CP-DR (deep research, LOCAL gap mode): agenda, content validation and composed result.

Stage 1 of the owner core (lease `docs/CPDR-OWNER-LEASE.md`, Method 1-8): pure functions over the
CP-0 gap facts, the analyst's research submission and the ready pack sources. Python owns every
count, status and share; the analyst supplies only questions, cited answers and limitations. The
G1-X seams (store, view, RULES, submit, probe) are added in later stages.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal, get_args

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
from deploy_vii.readiness import GapKind, GapSeverity, citation_issues
from deploy_vii.registry import modules
from deploy_workflow.owners.blank import is_blank

MODULE_ID = "CP-DR"
STEP_ID = "research"

MIN_QUESTIONS, MAX_QUESTIONS = 1, 4
PROHIBITED = ("recommend", "refinanc", "covenant", "recovery")
SHARE_PLACES = Decimal("0.0001")

FORMULA_COUNT = (
    "counts of the submitted questions by outcome; share = answered / total, 4 dp half-up"
)
FORMULA_STATUS = (
    "Resolved if every question is answered, Unresolved if none is, else Partially resolved"
)
FORMULA_OUTCOME = (
    "the submitted outcome of the question, accepted only when Python's checks pass "
    "(answered needs a cited answer)"
)
NA_LIMITATION = "No research question was submitted, so an answered share has no denominator."
EMPTY_LIMITATION = "No gaps identified by this supplied review; no research question was submitted."
BASE_LIMITATION = (
    "Research used the prepared local sources only; nothing outside the pack was searched."
)
# Ruling R4 (round 5): a gap text with more than one candidate consumer split settles not stated.
AMBIGUOUS_LIMITATION = "Not stated: the CP-0 gap text names its consumers ambiguously"
# Round 6e: a gap whose "affects" list is empty settles with this reason on named_consumers.
NO_CONSUMER_LIMITATION = "Not stated: the CP-0 gap names no consumer"
AFFECTS = "; affects "
_KINDS = frozenset(get_args(GapKind))
_SEVERITIES = frozenset(get_args(GapSeverity))

GapStatus = Literal["Resolved", "Partially resolved", "Unresolved"]


# --- submission schema (reference and judgment only) ----------------------------------------------


class ResearchQuestion(Contract):
    question_id: Identifier
    text: Text
    outcome: Literal["answered", "not_found"]
    answer: Text | None
    category: Literal["Documentary Fact", "Management Language", "Analyst Interpretation"] | None
    citations: tuple[Citation, ...]
    searched_sources: tuple[Identifier, ...]
    limitation: str | None


class GapResearch(Contract):
    gap_id: Identifier
    questions: tuple[ResearchQuestion, ...]


class ResearchSubmission(Contract):
    gaps: tuple[GapResearch, ...]  # empty tuple allowed (empty agenda)


# --- agenda (Method 1) ----------------------------------------------------------------------------


@dataclass(frozen=True)
class AgendaGap:
    """One CP-0 gap, parsed from its ``T5.<gap_id>.gap`` fact ``text``.

    ``description``, ``named_consumers`` and ``remediation`` are None when the text splits more
    than one way (ruling R4): they are not stated, and the full text stands for the gap.
    """

    gap_id: str
    kind_severity: str
    description: str | None
    named_consumers: tuple[str, ...] | None
    remediation: str | None
    text: str


def _consumers(segment: str, ids: frozenset[str]) -> tuple[str, ...] | None:
    """The segment as a ``", "``-list of methodology ids, or None when it is not one."""
    if not segment:
        return ()  # readiness.py joins an empty affected_modules to ""
    names = tuple(segment.split(", "))
    return names if all(name in ids for name in names) else None


def _parse_gap(gap_id: str, text: str) -> AgendaGap:
    """``<kind>/<severity>: <description>; affects <m, ...>; <remediation>`` (readiness.py:497-503).

    Ruling R4 (round 5), the fallback while Stage 1 has no reader of the structured
    ``ReadinessGap``: kind and severity come before the first ``": "``; a candidate split is any
    ``"; affects "`` whose segment up to the next ``"; "`` is a list of methodology ids. One
    candidate is used; several leave description, consumers and remediation not stated. A head
    outside the closed vocabularies, or no candidate, is not CP-0's form and raises.
    """
    head, sep, rest = text.partition(": ")
    kind, slash, severity = head.partition("/")
    if not (sep and slash) or kind not in _KINDS or severity not in _SEVERITIES:
        raise ValueError(f"CP-0 gap fact is not in the readiness form: {gap_id}")
    ids = frozenset(module.module_id for module in modules())
    splits: list[tuple[str, tuple[str, ...], str]] = []
    at = rest.find(AFFECTS)
    while at >= 0:
        segment, sep, remediation = rest[at + len(AFFECTS) :].partition("; ")
        consumers = _consumers(segment, ids) if sep else None
        if consumers is not None:
            splits.append((rest[:at], consumers, remediation))
        at = rest.find(AFFECTS, at + 1)
    if not splits:
        raise ValueError(f"CP-0 gap fact is not in the readiness form: {gap_id}")
    if len(splits) > 1:
        return AgendaGap(gap_id, head, None, None, None, text)
    ((description, consumers, remediation),) = splits
    return AgendaGap(gap_id, head, description, consumers, remediation, text)


def parse_agenda(facts: Iterable[Fact]) -> tuple[AgendaGap, ...]:
    """The research agenda from CP-0's T5 facts, in fact order.

    ``T5.review.gaps`` alone means an empty agenda; neither kind, or both, fails closed.
    """
    gaps: list[AgendaGap] = []
    no_gaps = False
    for fact in facts:
        if fact.table_id != "T5":
            continue
        if fact.status != "known" or fact.text is None:
            raise ValueError(f"CP-0 T5 fact is not known text: {fact.fact_id}")
        if fact.field == "gap":
            gaps.append(_parse_gap(fact.row_id, fact.text))
        elif (fact.row_id, fact.field) == ("review", "gaps"):
            no_gaps = True
        else:
            raise ValueError(f"Unexpected CP-0 T5 fact: {fact.fact_id}")
    if no_gaps == bool(gaps):
        raise ValueError("CP-0 carries no T5 agenda fact, or both a gap and the no-gap fact")
    return tuple(gaps)


# --- content validation (validator rules 1-7; tool-use RULES are separate) ------------------------


def _question_issues(
    question: ResearchQuestion, ready: frozenset[str], sources: tuple[Source, ...], path: str
) -> list[str]:
    """Rules 3-7 for one question; ``path`` is its ``gaps[i].questions[j]`` position (0-based)."""
    qid = question.question_id
    found: list[str] = []
    if question.outcome == "answered":
        if not (question.answer and question.category and question.citations):
            found.append(
                "an answered question needs an answer, a category and at least one citation: " + qid
            )
        if question.limitation:
            found.append(f"an answered question carries no limitation: {qid}")
    else:
        if question.answer or question.category or question.citations:
            found.append(f"a not_found question carries no answer, category or citation: {qid}")
        if not question.limitation:
            found.append(f"a not_found question states its limitation: {qid}")
    if not question.searched_sources:
        found.append(f"searched_sources must name at least one prepared source: {qid}")
    found += [
        f"searched source is not a ready prepared source: {qid} {source}"
        for source in question.searched_sources
        if source not in ready
    ]
    found += citation_issues(question.citations, sources)
    # Round 11 blank text (round 12 B10: `Cf` counts as blank): no CP-DR frame is pinned, so the
    # fallback applies. `""` keeps its existing refusal (the `Text` schema, or the not_found
    # completeness issue).
    found += [
        f"{path}.{field}: empty text"
        for field, value in (
            ("text", question.text),
            ("answer", question.answer),
            ("limitation", question.limitation),
        )
        if value and is_blank(value)
    ]
    texts = [t for t in (question.text, question.answer, question.limitation) if t]
    if any(char.isdigit() for text in texts for char in text):
        found.append(f"text must not contain a figure: {qid}")
    if any(word in text.lower() for text in texts for word in PROHIBITED):
        found.append(f"text carries a prohibited conclusion: {qid}")
    return found


def validate_research(
    *, submission: ResearchSubmission, upstream: tuple[AgendaGap, ...], pack: tuple[Source, ...]
) -> tuple[str, ...]:
    """Content issues of a submission against the CP-0 agenda (``upstream``) and the pack
    sources (``pack``).

    Order (ruling R2): rule 1 per submitted gap; rule 2 per agenda gap; then per question in
    submission order rule 3, 4, 5 per searched source in listed order, 6 per citation in order,
    the round 11 blank-text frames (text, answer, limitation), and 7. G1-X appends the de-duplicated RULES issues after these (Stage 2).
    """
    agenda_ids = {gap.gap_id for gap in upstream}
    issues: list[str] = []
    counted: dict[str, int] = {}
    for gap in submission.gaps:
        if gap.gap_id not in agenda_ids:
            issues.append(f"gap_id is not in the CP-0 agenda: {gap.gap_id}")
        elif gap.gap_id in counted:
            issues.append(f"gap_id appears twice: {gap.gap_id}")
        else:
            counted[gap.gap_id] = len(gap.questions)
    issues += [
        f"a gap takes 1 to 4 research questions: {gap.gap_id}"
        for gap in upstream
        if not MIN_QUESTIONS <= counted.get(gap.gap_id, 0) <= MAX_QUESTIONS
    ]
    ready = frozenset(source.source_id for source in pack if source.status == "ready")
    seen: set[str] = set()
    for g, gap in enumerate(submission.gaps):
        for q, question in enumerate(gap.questions):
            if question.question_id in seen:
                issues.append(f"question_id appears twice: {question.question_id}")
            seen.add(question.question_id)
            issues += _question_issues(question, ready, pack, f"gaps[{g}].questions[{q}]")
    return tuple(dict.fromkeys(issues))


# --- bookkeeping (Method 2-3, 5) ------------------------------------------------------------------


@dataclass(frozen=True)
class GapCount:
    gap_id: str
    questions: int
    answered: int
    unresolved: int
    answered_share: Decimal
    status: GapStatus


@dataclass(frozen=True)
class Bookkeeping:
    gaps: tuple[GapCount, ...]
    gaps_total: int
    gaps_resolved: int
    gaps_partial: int
    gaps_unresolved: int
    questions_total: int
    answered_total: int
    unresolved_total: int
    answered_share: Decimal | None  # None: no question, no denominator (never 0)


def _share(answered: int, total: int) -> Decimal:
    return (Decimal(answered) / Decimal(total)).quantize(SHARE_PLACES, rounding=ROUND_HALF_UP)


def _status(answered: int, total: int) -> GapStatus:
    if answered == total:
        return "Resolved"
    return "Unresolved" if answered == 0 else "Partially resolved"


def bookkeeping(*, submission: ResearchSubmission) -> Bookkeeping:
    """Counts, statuses and shares of a submission, gap by gap in submission order.

    Ruling R1: call it only on a submission ``validate_research`` returned no issue for.
    """
    gaps = []
    for gap in submission.gaps:
        total = len(gap.questions)
        if not total:
            raise ValueError(f"A gap without questions has no share: {gap.gap_id}")
        answered = sum(1 for q in gap.questions if q.outcome == "answered")
        gaps.append(
            GapCount(
                gap.gap_id,
                total,
                answered,
                total - answered,
                _share(answered, total),
                _status(answered, total),
            )
        )
    statuses = [g.status for g in gaps]
    questions = sum(g.questions for g in gaps)
    answered = sum(g.answered for g in gaps)
    return Bookkeeping(
        gaps=tuple(gaps),
        gaps_total=len(gaps),
        gaps_resolved=statuses.count("Resolved"),
        gaps_partial=statuses.count("Partially resolved"),
        gaps_unresolved=statuses.count("Unresolved"),
        questions_total=questions,
        answered_total=answered,
        unresolved_total=questions - answered,
        answered_share=_share(answered, questions) if questions else None,
    )


# --- composed result (Method 4-8) -----------------------------------------------------------------


@dataclass(frozen=True)
class CpdrInputs:
    """Every operand the Method reads: the CP-0 agenda, the analyst's submission and the as-of."""

    agenda: tuple[AgendaGap, ...]
    submission: ResearchSubmission  # analyst judgment: questions, answers, citations, limitations
    as_of: date


@dataclass(frozen=True)
class CpdrResult:
    bookkeeping: Bookkeeping
    facts: tuple[Fact, ...]
    tables: tuple[ReportTable, ...]
    claims: tuple[Claim, ...]
    limitations: tuple[str, ...]  # own limitations, before execution adds the synthetic line
    consumption_facts: tuple[str, ...]  # what a future CP-5 consumer must cite (lease D3)


TDR1_COLUMNS = (
    ("description", "description"),
    ("kind_severity", "kind/severity"),
    ("named_consumers", "named consumers"),
    ("questions", "questions"),
    ("answered", "answered"),
    ("unresolved", "unresolved"),
    ("answered_share", "answered share"),
    ("status", "status"),
)
TDR2_COLUMNS = tuple(
    (field, field) for field in ("gap", "question", "outcome", "answer", "evidence", "searched")
)
TOTAL_FIELDS = (
    "gaps_total",
    "gaps_resolved",
    "gaps_partial",
    "gaps_unresolved",
    "questions_total",
    "answered_total",
    "unresolved_total",
    "answered_share",
)
TDR3_COLUMNS = tuple((field, field.replace("_", " ")) for field in TOTAL_FIELDS)  # ruling R3
TOTAL_ROW_LABEL = "All gaps"  # ruling R3; row_kind stays the default "row"
PER_GAP_CONSUMED = ("questions", "answered", "unresolved", "answered_share", "status")


class _Builder:
    """Collects the facts of one result; every cell is a fact ``<table>.<row>.<field>``."""

    def __init__(self, period: str) -> None:
        self.period = period
        self.facts: list[Fact] = []

    def _add(self, table: str, row: str, field: str, **values: object) -> str:
        fact_id = f"{table}.{row}.{field}"
        self.facts.append(
            Fact.model_validate(
                {
                    "fact_id": fact_id,
                    "label": field.replace("_", " "),
                    "table_id": table,
                    "row_id": row,
                    "field": field,
                    **values,
                }
            )
        )
        return fact_id

    def text(
        self,
        table: str,
        row: str,
        field: str,
        text: str,
        value_class: str | None = None,
        formula: str | None = None,
        citations: tuple[Citation, ...] = (),
    ) -> str:
        calculation = {"calculation_id": f"cpdr-{row}-{field}", "formula": formula}
        return self._add(
            table,
            row,
            field,
            text=text,
            value_class=value_class,
            citations=citations,
            **(calculation if formula else {}),
        )

    def number(self, table: str, row: str, field: str, amount: Decimal | int, unit: str) -> str:
        return self._add(
            table,
            row,
            field,
            amount=Decimal(amount),
            unit=unit,
            period=self.period,
            value_class="calculated",
            calculation_id=f"cpdr-{row}-{field}",
            formula=FORMULA_COUNT,
        )

    def missing(
        self,
        table: str,
        row: str,
        field: str,
        limitation: str,
        value_class: str | None = "analyst_judgment",
    ) -> str:
        return self._add(
            table,
            row,
            field,
            status="missing",
            limitation=limitation,
            value_class=value_class,
        )

    def not_applicable(self, table: str, row: str, field: str, unit: str) -> str:
        return self._add(
            table,
            row,
            field,
            status="not_applicable",
            unit=unit,
            period=self.period,
            value_class="calculated",
            calculation_id=f"cpdr-{row}-{field}",
            formula=FORMULA_COUNT,
            limitation=NA_LIMITATION,
        )


def _table(
    table_id: str,
    title: str,
    row_header: str,
    columns: tuple[tuple[str, str], ...],
    rows: list[tuple[str, tuple[str, ...]]],
    row_label: str | None = None,
) -> ReportTable:
    """A declared table; each row is labelled from its id unless ``row_label`` names it."""
    return ReportTable(
        table_id=table_id,
        title=title,
        row_header=row_header,
        columns=tuple(TableColumn(field=f, label=label) for f, label in columns),
        rows=tuple(
            TableRow(row_id=r, label=row_label or _row_label(r), fact_ids=ids) for r, ids in rows
        ),
    )


def _row_label(row_id: str) -> str:
    """Ruling R5: the row id with "-" and "_" as spaces and its first letter upper-cased."""
    words = row_id.replace("-", " ").replace("_", " ")
    return words[:1].upper() + words[1:]


def _agenda_cells(build: _Builder, gap: AgendaGap) -> tuple[str, str, str]:
    """TDR.1 description, kind/severity and named consumers of one agenda gap."""
    row = gap.gap_id
    if gap.description is None or gap.named_consumers is None:  # ruling R4: split ambiguous
        description = build.missing("TDR.1", row, "description", AMBIGUOUS_LIMITATION, None)
        kind_severity = build.text("TDR.1", row, "kind_severity", gap.kind_severity)
        consumers = build.missing("TDR.1", row, "named_consumers", AMBIGUOUS_LIMITATION, None)
        return description, kind_severity, consumers
    # facts are added in column order (the result's fact order)
    description = build.text("TDR.1", row, "description", gap.description)
    kind_severity = build.text("TDR.1", row, "kind_severity", gap.kind_severity)
    if gap.named_consumers:
        consumers = build.text("TDR.1", row, "named_consumers", ", ".join(gap.named_consumers))
    else:  # round 6e: a gap naming no consumer settles not stated, with no own line
        consumers = build.missing("TDR.1", row, "named_consumers", NO_CONSUMER_LIMITATION, None)
    return description, kind_severity, consumers


def _evidence(citations: tuple[Citation, ...]) -> str:
    return "; ".join(dict.fromkeys(f"{c.source_id} {c.locator}" for c in citations))


def _gap_rows(
    build: _Builder, inputs: CpdrInputs, counts: tuple[GapCount, ...]
) -> list[tuple[str, tuple[str, ...]]]:
    """TDR.1 rows in agenda order, CP-0's T5 order (ruling C4)."""
    by_gap = {count.gap_id: count for count in counts}
    rows: list[tuple[str, tuple[str, ...]]] = []
    for gap in inputs.agenda:
        count = by_gap[gap.gap_id]  # compose checked the submission against the agenda
        row = gap.gap_id
        rows.append(
            (
                row,
                (
                    *_agenda_cells(build, gap),
                    build.number("TDR.1", row, "questions", count.questions, "questions"),
                    build.number("TDR.1", row, "answered", count.answered, "questions"),
                    build.number("TDR.1", row, "unresolved", count.unresolved, "questions"),
                    build.number(
                        "TDR.1", row, "answered_share", count.answered_share, "decimal_fraction"
                    ),
                    build.text("TDR.1", row, "status", count.status, "calculated", FORMULA_STATUS),
                ),
            )
        )
    return rows


def _question_row(build: _Builder, gap_id: str, q: ResearchQuestion) -> tuple[str, ...]:
    """One TDR.2 row; facts are added in column order (the result's fact order)."""
    row = q.question_id
    answered = q.outcome == "answered"
    ids = [
        build.text("TDR.2", row, "gap", gap_id),
        build.text("TDR.2", row, "question", q.text, "analyst_judgment"),
        build.text(
            "TDR.2",
            row,
            "outcome",
            "Answered" if answered else "Not found",
            "calculated",
            FORMULA_OUTCOME,
        ),
    ]
    if answered:
        if q.answer is None:
            raise ValueError(f"An answered question has no answer: {row}")
        ids += [
            build.text("TDR.2", row, "answer", q.answer, "analyst_judgment", None, q.citations),
            build.text("TDR.2", row, "evidence", _evidence(q.citations), None, None, q.citations),
        ]
    else:
        if not q.limitation:
            raise ValueError(f"A not_found question has no limitation: {row}")
        ids += [
            build.missing("TDR.2", row, "answer", q.limitation),
            build.missing("TDR.2", row, "evidence", q.limitation),
        ]
    ids.append(build.text("TDR.2", row, "searched", ", ".join(q.searched_sources)))
    return tuple(ids)


def _total_row(build: _Builder, bk: Bookkeeping) -> tuple[str, ...]:
    ids = []
    for field in TOTAL_FIELDS:
        if field == "answered_share":
            share = bk.answered_share
            ids.append(
                build.not_applicable("TDR.3", "total", field, "decimal_fraction")
                if share is None
                else build.number("TDR.3", "total", field, share, "decimal_fraction")
            )
        else:
            unit = "gaps" if field.startswith("gaps") else "questions"
            ids.append(build.number("TDR.3", "total", field, getattr(bk, field), unit))
    return tuple(ids)


def _ref(field: str, unit: str) -> str:
    return "{TDR.3.total." + field + "|" + unit + "}"


def _summary(bk: Bookkeeping) -> str:
    if bk.answered_share is None:
        return (
            f"Research covered {_ref('questions_total', 'questions')} because the supplied "
            f"readiness review identified {_ref('gaps_total', 'gaps')}."
        )
    return (
        f"Research covered {_ref('questions_total', 'questions')}; local sources answered "
        f"{_ref('answered_total', 'questions')} ({_ref('answered_share', '%')}) and "
        f"{_ref('unresolved_total', 'questions')} remain unresolved."
    )


def compose(inputs: CpdrInputs) -> CpdrResult:
    """Facts, tables TDR.1-TDR.3, claims and own limitations of a validated submission.

    Fails closed when the submission does not address the agenda gap for gap (validator rules
    1-2 should have refused it): an agenda gap missing, a gap outside the agenda, or a repeat.
    """
    submitted = [gap.gap_id for gap in inputs.submission.gaps]
    agenda_ids = [gap.gap_id for gap in inputs.agenda]
    for gap_id in agenda_ids:
        if gap_id not in submitted:
            raise ValueError(f"Agenda gap is missing from the submission: {gap_id}")
    for gap_id in submitted:
        if gap_id not in agenda_ids:
            raise ValueError(f"Submitted gap is not in the CP-0 agenda: {gap_id}")
    if len(set(submitted)) != len(submitted):
        raise ValueError("A gap appears twice in the submission")
    bk = bookkeeping(submission=inputs.submission)
    build = _Builder(inputs.as_of.isoformat())
    # ruling C4 (rounds 6b and 6e): every per-gap sequence (TDR.1, TDR.2, claims, "Unresolved:"
    # lines, consumption facts) follows agenda order, with submission order inside a gap
    asked = {gap.gap_id: gap.questions for gap in inputs.submission.gaps}
    questions = [(gap.gap_id, q) for gap in inputs.agenda for q in asked[gap.gap_id]]
    tables: list[ReportTable] = []
    if inputs.agenda:  # an empty agenda emits neither TDR.1 nor TDR.2 (Method 5)
        gap_rows = _gap_rows(build, inputs, bk.gaps)
        question_rows = [(q.question_id, _question_row(build, g, q)) for g, q in questions]
        tables += [
            _table("TDR.1", "Research agenda and gap status", "Gap", TDR1_COLUMNS, gap_rows),
            _table(
                "TDR.2",
                "Research questions and cited answers",
                "Question",
                TDR2_COLUMNS,
                question_rows,
            ),
        ]
    total = _total_row(build, bk)
    tables.append(
        _table(
            "TDR.3",
            "Research coverage totals",
            "Total",
            TDR3_COLUMNS,
            [("total", total)],
            row_label=TOTAL_ROW_LABEL,  # ruling R3
        )
    )

    unresolved = [q for _, q in questions if q.outcome == "not_found"]
    limitations = [BASE_LIMITATION]
    limitations += [  # ruling R4; placed after the base line, in agenda order (not pinned)
        f"CP-0 gap {gap.gap_id} cannot be split into description, consumers and remediation; "
        "its full text is the gap."
        for gap in inputs.agenda
        if gap.description is None
    ]
    if not inputs.agenda:
        limitations.append(EMPTY_LIMITATION)
    limitations += [f"Unresolved: {q.text} {q.limitation}" for q in unresolved]

    claims = [Claim(claim_id="CPDR-SUM-01", text=_summary(bk), citations=())]
    claims += [
        Claim(claim_id=f"CPDR-ANS-{q.question_id}", text=q.answer, citations=q.citations)
        for _, q in questions
        if q.outcome == "answered" and q.answer is not None
    ]
    consumed = (
        *(f"TDR.1.{g.gap_id}.{field}" for g in inputs.agenda for field in PER_GAP_CONSUMED),
        *(f"TDR.3.total.{field}" for field in TOTAL_FIELDS),
        *(f"TDR.2.{q.question_id}.answer" for q in unresolved),
    )
    return CpdrResult(
        bookkeeping=bk,
        facts=tuple(build.facts),
        tables=tuple(tables),
        claims=tuple(claims),
        limitations=tuple(limitations),
        consumption_facts=consumed,
    )
