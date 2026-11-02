"""CP-DR TDR.1-3 composition and the dossier input (O7b-1c S2a, Behaviour 10).

Pure over data: the locked brief, the reviewed submission, the accepted evidence list, Python's
counts and claim states. ``compose`` writes the head's facts, report tables, claims and
limitations; ``dossier_input`` adapts them for the 1b renderer. A fact is the only place a value
lives: a table cell is a reference to a fact, and the dossier's shown string is derived from it.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from functools import partial
from typing import Any, Final

from deploy_vii.contracts import Citation, Fact, ReportTable, TableColumn, TableRow
from deploy_vii.contracts import Claim as ModuleClaim
from deploy_workflow.research.contracts import (
    RESERVED_PREFIX,
    ClaimState,
    EvidenceItem,
    ResearchBrief,
    ResearchError,
)
from deploy_workflow.research.dossier import UNDATED, DossierInput
from deploy_workflow.research.intake import RefusedItem
from deploy_workflow.research.review import (
    Answer,
    CitedContrary,
    Claim,
    Counts,
    ResearchSubmission,
)

GAP_SHOWN: Final = "∅ G#"
NOT_APPLICABLE_SHOWN: Final = "not applicable"
PACK_LIMITATION: Final = "A pack source carries no publication date or family."
FOCUS_LIMITATION: Final = "A default question carries no focus module."
LOCAL_LIMITATION: Final = (
    "This research is LOCAL: it rests on the supplied evidence items and is not a full CP-OS run."
)
FORMULA_COUNT: Final = "count over the question row; the total row is the sum of the question rows"
FORMULA_STATE: Final = (
    "the submitted answer_state of the question, accepted only when Python's checks pass"
)
FORMULA_JOIN: Final = (
    "Python composition from the settled brief, the submission and the intake record"
)
TOTAL_ROW: Final = "total"

TDR1_COLUMNS: Final = ("text", "kind", "receivers", "focus_module")
TDR2_COLUMNS: Final = ("question_id", "claim", "evidence_id", "locator", "published", "family")
TDR3_TEXT_COLUMNS: Final = ("answer_state", "answer", "contrary", "uncertainty", "downstream_use")
TDR3_COUNTS: Final = (
    ("questions_total", "questions"),
    ("answered", "questions"),
    ("partly", "questions"),
    ("not_found", "questions"),
    ("contrary_items", "items"),
)
TDR3_COLUMNS: Final = (*TDR3_TEXT_COLUMNS, *(name for name, _ in TDR3_COUNTS))
DOWNSTREAM: Final[Mapping[ClaimState, str]] = {
    "supported": ": passed as answered",
    "contrary": ": passed as answered with the contrary item flagged",
    "missing": ": passed as a gap, not filled",
}
PARTLY_DOWNSTREAM: Final = ": passed as partly answered with its limitation"


class TablesInvalid(ResearchError):
    """The submission, brief or counts cannot be composed into TDR.1-3."""


@dataclass(frozen=True)
class Composed:
    facts: tuple[Fact, ...]
    tables: tuple[ReportTable, ...]
    claims: tuple[ModuleClaim, ...]
    limitations: tuple[str, ...]


def _label(field: str) -> str:
    return field.replace("_", " ")


def _fact(table_id: str, row_id: str, field: str, **fields: Any) -> Fact:
    return Fact(
        fact_id=f"{table_id}.{row_id}.{field}",
        table_id=table_id,
        row_id=row_id,
        field=field,
        label=_label(field),
        **{key: value for key, value in fields.items() if value is not None},
    )


def _text(
    table_id: str,
    row_id: str,
    field: str,
    text: str,
    value_class: str | None = None,
    *,
    calc: bool = False,
    formula: str = FORMULA_JOIN,
    citations: Sequence[Citation] = (),
    limitation: str | None = None,
) -> Fact:
    calculation = (f"cpdr-{row_id}-{field}", formula) if calc else (None, None)
    return _fact(
        table_id,
        row_id,
        field,
        text=text,
        status="known",
        value_class=value_class,
        calculation_id=calculation[0],
        formula=calculation[1],
        citations=tuple(citations),
        limitation=limitation,
    )


def _count(table_id: str, row_id: str, field: str, number: int, unit: str, period: str) -> Fact:
    return _fact(
        table_id,
        row_id,
        field,
        amount=Decimal(number),
        unit=unit,
        period=period,
        value_class="calculated",
        status="known",
        formula=FORMULA_COUNT,
        calculation_id=f"cpdr-{row_id}-{field}",
    )


def _unsettled(table_id: str, row_id: str, field: str, status: str, limitation: str) -> Fact:
    """A gap (``missing``, analyst's judgment) or a ``not_applicable`` cell (source)."""
    value_class = "analyst_judgment" if status == "missing" else "source"
    return _fact(
        table_id, row_id, field, status=status, limitation=limitation, value_class=value_class
    )


class _Table:
    def __init__(self, table_id: str, title: str, row_header: str, columns: Sequence[str]) -> None:
        self.table_id = table_id
        self.title = title
        self.row_header = row_header
        self.columns = tuple(columns)
        self.facts: list[Fact] = []
        self.rows: list[TableRow] = []

    def add(self, row_id: str, cells: Sequence[Fact]) -> None:
        if tuple(cell.field for cell in cells) != self.columns:
            raise TablesInvalid(f"{self.table_id} {row_id} does not fill every column in order")
        self.facts += cells
        self.rows.append(
            TableRow(
                row_id=row_id,
                label=row_id,
                fact_ids=tuple(cell.fact_id for cell in cells),
                row_kind="total" if row_id == TOTAL_ROW else "row",
            )
        )

    def report(self) -> ReportTable:
        return ReportTable(
            table_id=self.table_id,
            title=self.title,
            row_header=self.row_header,
            columns=tuple(TableColumn(field=name, label=_label(name)) for name in self.columns),
            rows=tuple(self.rows),
        )


def _tdr1(brief: ResearchBrief) -> _Table:
    table = _Table("TDR.1", "Locked questions and recipients", "question_id", TDR1_COLUMNS)
    for q in brief.questions:
        row = q.question_id
        put = partial(_text, "TDR.1", row)
        focus = (
            put("focus_module", q.focus_module)
            if q.focus_module
            else _unsettled("TDR.1", row, "focus_module", "not_applicable", FOCUS_LIMITATION)
        )
        table.add(
            row,
            [
                put("text", q.text),
                put("kind", q.kind),
                put("receivers", ", ".join(q.receivers)),
                focus,
            ],
        )
    return table


def _published(item: EvidenceItem) -> str:
    return UNDATED if item.published is None else item.published.isoformat()


def _check_cited(
    claim_id: str, citations: Sequence[Citation], items: Mapping[str, EvidenceItem]
) -> None:
    """An ``ev-*`` citation must be an accepted item; any other id is a pack source (O7-R24), whose
    being held is review's check."""
    unknown = [
        c.source_id
        for c in citations
        if c.source_id.casefold().startswith(RESERVED_PREFIX) and c.source_id not in items
    ]
    if unknown:
        raise TablesInvalid(f"claim {claim_id} cites {', '.join(unknown)}, not accepted evidence")


def _evidence_cells(row: str, claim: Claim, items: Mapping[str, EvidenceItem]) -> list[Fact]:
    """evidence_id, locator, published, family, "; "-joined in citation order. A pack position holds
    the not-applicable string; a claim citing only pack sources has no date or family at all, and
    those two cells are ``not_applicable`` facts (O7-R24, O7-R24a)."""
    cited = [(items.get(c.source_id), c) for c in claim.citations]
    put = partial(_text, "TDR.2", row)
    joined = "; ".join
    cells = [
        put("evidence_id", joined(c.source_id for _, c in cited), "source"),
        put("locator", joined(i.locator if i else c.locator for i, c in cited), "source"),
    ]
    if all(i is None for i, _ in cited):
        return cells + [
            _unsettled("TDR.2", row, f, "not_applicable", PACK_LIMITATION)
            for f in ("published", "family")
        ]
    return cells + [
        put(
            "published",
            joined(_published(i) if i else NOT_APPLICABLE_SHOWN for i, _ in cited),
            "source",
        ),
        put("family", joined(i.family if i else NOT_APPLICABLE_SHOWN for i, _ in cited), "source"),
    ]


def _tdr2(answers: Sequence[Answer], items: Mapping[str, EvidenceItem]) -> _Table:
    table = _Table("TDR.2", "Claims and located evidence", "claim_id", TDR2_COLUMNS)
    for answer in answers:
        for claim in answer.claims:
            row = claim.claim_id
            _check_cited(row, claim.citations, items)
            put = partial(_text, "TDR.2", row)
            table.add(
                row,
                [
                    put("question_id", answer.question_id),
                    put("claim", claim.text, "analyst_judgment", citations=claim.citations),
                    *_evidence_cells(row, claim, items),
                ],
            )
    return table


def _contrary_text(answer: Answer) -> str:
    return "; ".join(
        f"{entry.item}: {entry.text}"
        if isinstance(entry, CitedContrary)
        else "none found in " + ", ".join(entry.searched)
        for entry in answer.contrary
    )


def _answer_cells(answer: Answer) -> list[Fact]:
    """The answer, contrary and uncertainty cells; a question with no claim shows a gap."""
    row = answer.question_id
    if not answer.claims:
        if not answer.limitation:
            raise TablesInvalid(f"{row} has no claim and no limitation")
        return [
            _unsettled("TDR.3", row, f, "missing", answer.limitation)
            for f in ("answer", "contrary", "uncertainty")
        ]
    if not answer.uncertainty:
        raise TablesInvalid(f"{row} has a claim and no uncertainty")
    cited = [e for e in answer.contrary if isinstance(e, CitedContrary)]
    put = partial(_text, "TDR.3", row)
    return [
        put(
            "answer",
            " ".join(c.text for c in answer.claims),
            "analyst_judgment",
            citations=[x for c in answer.claims for x in c.citations],
            limitation=answer.limitation if answer.answer_state == "partly" else None,
        ),
        put(
            "contrary",
            _contrary_text(answer),
            "analyst_judgment",
            citations=[e.citation for e in cited],
            limitation=" ".join(e.limitation for e in answer.contrary if e.limitation) or None,
        ),
        put("uncertainty", answer.uncertainty, "analyst_judgment"),
    ]


def _row_counts(answer: Answer) -> dict[str, int]:
    return {
        "questions_total": 1,
        "answered": int(answer.answer_state == "answered"),
        "partly": int(answer.answer_state == "partly"),
        "not_found": int(answer.answer_state == "not_found"),
        "contrary_items": sum(isinstance(e, CitedContrary) for e in answer.contrary),
    }


def _downstream(receivers: Sequence[str], answer: Answer, state: ClaimState) -> str:
    use = PARTLY_DOWNSTREAM if answer.answer_state == "partly" else DOWNSTREAM[state]
    return ", ".join(receivers) + use


def _count_cells(row: str, counts: Mapping[str, int], period: str) -> list[Fact]:
    return [_count("TDR.3", row, name, counts[name], unit, period) for name, unit in TDR3_COUNTS]


def _question_row(
    answer: Answer, receivers: Sequence[str], state: ClaimState, period: str
) -> tuple[list[Fact], dict[str, int]]:
    row = answer.question_id
    counts = _row_counts(answer)
    put = partial(_text, "TDR.3", row)
    cells = [
        put("answer_state", answer.answer_state, "calculated", calc=True, formula=FORMULA_STATE),
        *_answer_cells(answer),
        put("downstream_use", _downstream(receivers, answer, state), "calculated", calc=True),
        *_count_cells(row, counts, period),
    ]
    return cells, counts


def _plural(number: int, noun: str) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def _uncertainty_total(counts: Counts, missing: Sequence[str], partly: Sequence[str]) -> str:
    parts = []
    if missing:
        n, verb = _plural(counts.not_found, "question"), "has" if counts.not_found == 1 else "have"
        parts.append(f"{n} {verb} no located answer: {', '.join(missing)}")
    if partly:
        n, verb = _plural(counts.partly, "question"), "is" if counts.partly == 1 else "are"
        parts.append(f"{n} {verb} partly answered: {', '.join(partly)}")
    return "; ".join(parts) or "every question has a located answer"


def _total_cells(
    counts: Counts,
    answers: Sequence[Answer],
    received: Mapping[str, list[int]],
    period: str,
) -> list[Fact]:
    cited_items = [e.item for a in answers for e in a.contrary if isinstance(e, CitedContrary)]
    texts = {
        "answer_state": (
            f"answered {counts.answered}; partly {counts.partly}; not found {counts.not_found}"
        ),
        "answer": (
            f"{sum(bool(a.claims) for a in answers)} of {counts.questions_total} "
            "questions carry a located claim"
        ),
        "contrary": (
            f"{_plural(counts.contrary_items, 'contrary item')} cited: " + ", ".join(cited_items)
            if cited_items
            else "no contrary item cited"
        ),
        "uncertainty": _uncertainty_total(
            counts,
            [a.question_id for a in answers if a.answer_state == "not_found"],
            [a.question_id for a in answers if a.answer_state == "partly"],
        ),
        "downstream_use": "; ".join(
            f"{receiver} receives {done} of {total} answered questions"
            for receiver, (total, done) in received.items()
        ),
    }
    cells = [
        _text("TDR.3", TOTAL_ROW, f, texts[f], "calculated", calc=True) for f in TDR3_TEXT_COLUMNS
    ]
    totals = {name: getattr(counts, name) for name, _ in TDR3_COUNTS}
    return cells + _count_cells(TOTAL_ROW, totals, period)


def _tdr3(
    brief: ResearchBrief,
    answers: Sequence[Answer],
    states: Sequence[ClaimState],
    counts: Counts,
    period: str,
) -> _Table:
    table = _Table(
        "TDR.3",
        "Answers, contrary evidence, uncertainty and downstream use",
        "question_id",
        TDR3_COLUMNS,
    )
    sums = dict.fromkeys((name for name, _ in TDR3_COUNTS), 0)
    received: dict[str, list[int]] = {"CP-1C": [0, 0], "CP-2": [0, 0]}
    for question, answer, state in zip(brief.questions, answers, states, strict=True):
        cells, row_counts = _question_row(answer, question.receivers, state, period)
        table.add(answer.question_id, cells)
        for name, number in row_counts.items():
            sums[name] += number
        for receiver in question.receivers:
            received[receiver][0] += 1
            received[receiver][1] += row_counts["answered"]
    if sums != {name: getattr(counts, name) for name in sums}:
        raise TablesInvalid("the counts differ from the sum of the question rows")
    table.add(TOTAL_ROW, _total_cells(counts, answers, received, period))
    return table


def _ref(field: str, unit: str) -> str:
    return "{" + f"TDR.3.{TOTAL_ROW}.{field}|{unit}" + "}"


def _claims() -> tuple[ModuleClaim, ...]:
    """Python's counts, quoted from the total row by reference; no figure is typed."""
    return (
        ModuleClaim(
            claim_id="cpdr-answer-counts",
            text=(
                f"Of {_ref('questions_total', 'questions')} locked questions, "
                f"{_ref('answered', 'questions')} are answered, "
                f"{_ref('partly', 'questions')} partly answered and "
                f"{_ref('not_found', 'questions')} not found, with contrary evidence cited in "
                f"{_ref('contrary_items', 'items')}."
            ),
            citations=(),
        ),
    )


def _limitations(answers: Sequence[Answer]) -> tuple[str, ...]:
    own = [f"{a.question_id}: {a.limitation}" for a in answers if a.limitation]
    return tuple(dict.fromkeys([LOCAL_LIMITATION, *own]))


def _states_by_question(
    brief: ResearchBrief, claim_states: Sequence[ClaimState]
) -> tuple[ClaimState, ...]:
    if len(claim_states) != len(brief.questions):
        raise TablesInvalid("claim states are not one per brief question")
    if "blocked" in claim_states:
        raise TablesInvalid("a blocked question cannot be composed into the tables")
    return tuple(claim_states)


def _answers_in_brief_order(brief: ResearchBrief, submission: ResearchSubmission) -> list[Answer]:
    by_id = {a.question_id: a for a in submission.answers}
    wanted = [q.question_id for q in brief.questions]
    if len(by_id) != len(submission.answers) or set(by_id) != set(wanted):
        raise TablesInvalid("the submission does not answer exactly the locked questions")
    if TOTAL_ROW in wanted:
        raise TablesInvalid(f"a question cannot be named {TOTAL_ROW}")
    return [by_id[qid] for qid in wanted]


def compose(
    brief: ResearchBrief,
    submission: ResearchSubmission,
    evidence: Sequence[EvidenceItem],
    counts: Counts,
    claim_states: Sequence[ClaimState],
    period: str,
) -> Composed:
    """TDR.1-3 facts and tables, the count claims and the limitations; raises ``TablesInvalid``."""
    answers = _answers_in_brief_order(brief, submission)
    states = _states_by_question(brief, claim_states)
    items = {item.item_id: item for item in evidence}
    built = [_tdr1(brief), _tdr2(answers, items), _tdr3(brief, answers, states, counts, period)]
    return Composed(
        facts=tuple(fact for table in built for fact in table.facts),
        tables=tuple(table.report() for table in built),
        claims=_claims(),
        limitations=_limitations(answers),
    )


def _shown(fact: Fact) -> tuple[str, str]:
    """(shown string, cell state) of one fact; a gap and a not-applicable cell are named."""
    if fact.status == "missing":
        return GAP_SHOWN, "gap"
    if fact.status == "not_applicable":
        return NOT_APPLICABLE_SHOWN, "not_applicable"
    if fact.status != "known":
        raise TablesInvalid(f"fact {fact.fact_id} is {fact.status} and cannot be shown")
    if fact.amount is not None:
        return f"{fact.amount} {fact.unit}", "known"
    return str(fact.text), "known"


def _view(table: ReportTable, by_id: Mapping[str, Fact]) -> dict[str, Any]:
    fields = [column.field for column in table.columns]
    rows = []
    for row in table.rows:
        cells = {}
        for field, fact_id in zip(fields, row.fact_ids, strict=True):
            shown, state = _shown(by_id[fact_id])
            cells[field] = {"fact": fact_id, "shown": shown, "state": state}
        rows.append([row.row_id, cells])
    return {"title": table.title, "row_header": table.row_header, "columns": fields, "rows": rows}


FACT_RECORD: Final = {"table_id", "row_id", "field", "status", "limitation"}


def dossier_input(
    composed: Composed,
    brief: ResearchBrief,
    claim_states: Sequence[ClaimState],
    evidence: Sequence[EvidenceItem],
    rejected: Sequence[RefusedItem],
    head_sha256: str,
) -> DossierInput:
    """What the 1b renderer takes. ``head_sha256`` is the CP-DR head's hash, recorded and not
    compared (O7-R10); the tables carry each cell's shown string, derived from its fact."""
    by_id = {fact.fact_id: fact for fact in composed.facts}
    return DossierInput(
        brief=brief,
        claim_states=tuple(claim_states),
        tables={table.table_id: _view(table, by_id) for table in composed.tables},
        facts=[fact.model_dump(include=FACT_RECORD) for fact in composed.facts],
        evidence=tuple(evidence),
        rejected=tuple(rejected),
        result_sha256=head_sha256,
    )
