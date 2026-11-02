"""CP-DR opt-in peer pack: TDR.4 candidate peers, TDR.5 alignment observations, TDR.6 located
figures (O7d D1a).

The model submits ``peers`` beside its answers when the locked brief asks for the pack
(``ResearchBrief.peer_pack``). A figure carries ``peer_id``, ``operand``, ``unit``, ``currency``,
``period_end`` and a citation whose quote is the figure token; it never carries an amount (a typed
``amount`` is a shape refusal, as is any field CP-1C owns: inclusion, comparability, statistics).
Python reads the amount from the quote with CP-1C's table rule and writes the facts.

``review`` imports this module for ``PeerPack`` and ``tables`` imports ``review``, so the
functions that need ``review``, ``tables`` or ``owners.cp1c`` import them when called.
"""

from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal
from functools import partial
from typing import TYPE_CHECKING, Final, Literal

from deploy_vii.contracts import Citation, Contract, Fact, Identifier, Source, Text
from deploy_vii.readiness import citation_issues
from deploy_workflow.research.contracts import RESERVED_PREFIX, EvidenceItem, ResearchBrief

if TYPE_CHECKING:
    from deploy_workflow.research.review import ReviewIssue
    from deploy_workflow.research.tables import Composed, _Table

Dimension = Literal["period", "definition", "currency", "segment"]
Unit = Literal["millions", "thousands", "units"]

TDR4_COLUMNS: Final = ("name", "basis_note", "evidence_id", "locator")
TDR5_COLUMNS: Final = ("observation", "evidence_id", "locator")
TDR6_COLUMNS: Final = (
    "amount",
    "unit",
    "currency",
    "period_end",
    "evidence_id",
    "locator",
    "quote",
)
UNIT_FACT: Final[Mapping[str, tuple[str, int]]] = {
    "millions": ("MILLIONS", 1_000_000),
    "thousands": ("THOUSANDS", 1_000),
    "units": ("UNITS", 1),
}
PACK_ROW: Final = "peers"
NOT_REQUESTED: Final = "peer pack not requested"
MISSING_PACK: Final = "peer pack requested; peers missing"
UNREADABLE: Final = "figure not readable from the quote"
AFTER_CUTOFF: Final = "period end after the cutoff"
NOT_AN_OPERAND: Final = "operand is not a CP-1C operand"
NOT_A_CANDIDATE: Final = "peer_id is not a TDR.4 candidate"
NOT_A_DATE: Final = "period_end is not a calendar date"
NOT_EVIDENCE: Final = "citation is not an accepted ev-* item"
# A peer id sits in the fact ids `TDR.6.<peer_id>.<operand>.<field>`; the longest operand and field
# decide, and one id past this makes `Fact` raise after the binding write.
_LONGEST_FACT_TAIL: Final = len("TDR.6.") + len(".interest.evidence_id")
PEER_ID_MAX: Final = 160 - _LONGEST_FACT_TAIL


class CandidatePeer(Contract):
    peer_id: Identifier
    name: Text
    basis_note: Text
    citation: Citation


class AlignmentObservation(Contract):
    peer_id: Identifier
    dimension: Dimension
    observation: Text
    citation: Citation


class LocatedFigure(Contract):
    peer_id: Identifier
    operand: Identifier
    unit: Unit
    currency: Text
    period_end: Text
    citation: Citation


class PeerPack(Contract):
    candidates: tuple[CandidatePeer, ...]
    observations: tuple[AlignmentObservation, ...]
    figures: tuple[LocatedFigure, ...]


def amount_from_quote(quote: str) -> Decimal | None:
    """The figure a quote states, by CP-1C's table rule (``cp1c.AMOUNT``, at most
    ``SHEET_DECIMALS`` decimal places); ``None`` when the quote is not exactly one such token."""
    from deploy_workflow.owners.cp1c import AMOUNT, SHEET_DECIMALS

    match = AMOUNT.fullmatch(quote)
    if match is None or len(match.group(1) or "") > SHEET_DECIMALS:
        return None
    return Decimal(quote)


def period_end_date(token: str) -> date | None:
    """``token`` as a calendar date by CP-1C's period-end form (``cp1c.PERIOD_END``), else None."""
    from deploy_workflow.owners.cp1c import PERIOD_END

    if not PERIOD_END.fullmatch(token):
        return None
    try:
        return date.fromisoformat(token)
    except ValueError:
        return None


def _issue(where: str, text: str) -> "ReviewIssue":
    from deploy_workflow.research.review import ReviewIssue

    return ReviewIssue(where, text)


def _text_issues(where: str, text: str) -> list["ReviewIssue"]:
    """The research texts' figure and banned-word rules over one analyst-written cell."""
    from deploy_workflow.research.review import BANNED_WORDS, FIGURE_ISSUE

    found = [_issue(where, f"banned word: {w}") for w in BANNED_WORDS if w in text.lower()]
    if any(char.isdigit() for char in text):
        found.append(_issue(where, FIGURE_ISSUE))
    return found


def _citation_issues(
    where: str, citation: Citation, items: set[str], sources: tuple[Source, ...]
) -> list["ReviewIssue"]:
    if not (citation.source_id.startswith(RESERVED_PREFIX) and citation.source_id in items):
        return [_issue(where, NOT_EVIDENCE)]
    return [_issue(where, text) for text in citation_issues((citation,), sources)]


def _candidate_issues(
    pack: PeerPack, items: set[str], sources: tuple[Source, ...]
) -> list["ReviewIssue"]:
    issues: list[ReviewIssue] = []
    seen: set[str] = set()
    for peer in pack.candidates:
        where = peer.peer_id
        if where in seen:
            issues.append(_issue(where, "peer_id appears twice in TDR.4"))
        seen.add(where)
        if "." in where or len(where) > PEER_ID_MAX:
            issues.append(_issue(where, f"peer_id has no dot and is at most {PEER_ID_MAX} long"))
        issues += _text_issues(where, peer.basis_note)
        issues += _citation_issues(where, peer.citation, items, sources)
    return issues


def _observation_issues(
    pack: PeerPack, items: set[str], sources: tuple[Source, ...]
) -> list["ReviewIssue"]:
    candidates = {peer.peer_id for peer in pack.candidates}
    issues: list[ReviewIssue] = []
    seen: set[str] = set()
    for obs in pack.observations:
        where = f"{obs.peer_id}.{obs.dimension}"
        if obs.peer_id not in candidates:
            issues.append(_issue(where, NOT_A_CANDIDATE))
        if where in seen:
            issues.append(_issue(where, "row appears twice in TDR.5"))
        seen.add(where)
        issues += _text_issues(where, obs.observation)
        issues += _citation_issues(where, obs.citation, items, sources)
    return issues


def _figure_issues(
    pack: PeerPack, items: set[str], sources: tuple[Source, ...]
) -> list["ReviewIssue"]:
    from deploy_workflow.owners.cp1c import OPERANDS

    operands = {key for key, _ in OPERANDS}
    candidates = {peer.peer_id for peer in pack.candidates}
    issues: list[ReviewIssue] = []
    seen: set[str] = set()
    for fig in pack.figures:
        where = f"{fig.peer_id}.{fig.operand}"
        if fig.operand not in operands:
            issues.append(_issue(where, NOT_AN_OPERAND))
        if fig.peer_id not in candidates:
            issues.append(_issue(where, NOT_A_CANDIDATE))
        if where in seen:
            issues.append(_issue(where, "row appears twice in TDR.6"))
        seen.add(where)
        if period_end_date(fig.period_end) is None:
            issues.append(_issue(where, NOT_A_DATE))
        issues += _citation_issues(where, fig.citation, items, sources)
    return issues


def peer_issues(
    pack: PeerPack | None,
    brief: ResearchBrief,
    evidence: Sequence[EvidenceItem],
    sources: Sequence[Source],
) -> tuple["ReviewIssue", ...]:
    """Every failed peer-pack check; empty when the pack holds or none is asked for and none
    comes. A figure whose quote cannot be read, or whose period ends after the cutoff, is not an
    issue: it composes as a ``missing`` cell. The read-before-cite rule is ``research_rules``."""
    if pack is None:
        return (_issue(PACK_ROW, MISSING_PACK),) if brief.peer_pack else ()
    if not brief.peer_pack:
        return (_issue(PACK_ROW, NOT_REQUESTED),)
    items = {item.item_id for item in evidence}
    held = tuple(sources)
    return tuple(
        _candidate_issues(pack, items, held)
        + _observation_issues(pack, items, held)
        + _figure_issues(pack, items, held)
    )


def _evidence_cells(table_id: str, row: str, citation: Citation) -> list[Fact]:
    from deploy_workflow.research.tables import _text

    put = partial(_text, table_id, row)
    return [
        put("evidence_id", citation.source_id, "source"),
        put("locator", citation.locator, "source"),
    ]


def _check_held(row: str, citation: Citation, items: Mapping[str, EvidenceItem]) -> None:
    from deploy_workflow.research.tables import TablesInvalid

    if citation.source_id not in items:
        raise TablesInvalid(f"{row} cites {citation.source_id}, not accepted evidence")


def _tdr4(pack: PeerPack, items: Mapping[str, EvidenceItem]) -> "_Table":
    from deploy_workflow.research.tables import _Table, _text

    table = _Table("TDR.4", "Candidate peers", "peer_id", TDR4_COLUMNS)
    for peer in pack.candidates:
        _check_held(peer.peer_id, peer.citation, items)
        put = partial(_text, "TDR.4", peer.peer_id)
        table.add(
            peer.peer_id,
            [
                put("name", peer.name, "analyst_judgment", citations=(peer.citation,)),
                put("basis_note", peer.basis_note, "analyst_judgment"),
                *_evidence_cells("TDR.4", peer.peer_id, peer.citation),
            ],
        )
    return table


def _tdr5(pack: PeerPack, items: Mapping[str, EvidenceItem]) -> "_Table":
    from deploy_workflow.research.tables import _Table, _text

    table = _Table("TDR.5", "Provisional alignment observations", "peer_id.dimension", TDR5_COLUMNS)
    for obs in pack.observations:
        row = f"{obs.peer_id}.{obs.dimension}"
        _check_held(row, obs.citation, items)
        put = partial(_text, "TDR.5", row)
        table.add(
            row,
            [
                put("observation", obs.observation, "analyst_judgment", citations=(obs.citation,)),
                *_evidence_cells("TDR.5", row, obs.citation),
            ],
        )
    return table


def _amount_cell(row: str, fig: LocatedFigure, cutoff: date) -> Fact:
    """The amount: read from the quote by Python; a gap with its limitation when the period ends
    after the cutoff or the quote is not a figure the table rule reads."""
    from deploy_workflow.owners.cp1c import SHEET_DECIMALS
    from deploy_workflow.research.tables import _fact, _unsettled

    ended = period_end_date(fig.period_end)
    if ended is not None and ended > cutoff:
        return _unsettled("TDR.6", row, "amount", "missing", AFTER_CUTOFF)
    amount = amount_from_quote(fig.citation.quote)
    if amount is None:
        return _unsettled("TDR.6", row, "amount", "missing", UNREADABLE)
    unit, scale = UNIT_FACT[fig.unit]
    return _fact(
        "TDR.6",
        row,
        "amount",
        amount=amount,
        unit=unit,
        currency=fig.currency,
        scale=Decimal(scale),
        decimals=SHEET_DECIMALS,
        period=f"Twelve months to {fig.period_end}",
        status="known",
        value_class="source",
        citations=(fig.citation,),
    )


def _tdr6(pack: PeerPack, items: Mapping[str, EvidenceItem], cutoff: date) -> "_Table":
    from deploy_workflow.research.tables import TablesInvalid, _Table, _text

    table = _Table("TDR.6", "Located peer/transaction figures", "peer_id.operand", TDR6_COLUMNS)
    for fig in pack.figures:
        row = f"{fig.peer_id}.{fig.operand}"
        _check_held(row, fig.citation, items)
        if period_end_date(fig.period_end) is None:
            raise TablesInvalid(f"{row} period_end is not a calendar date")
        put = partial(_text, "TDR.6", row)
        table.add(
            row,
            [
                _amount_cell(row, fig, cutoff),
                put("unit", fig.unit, "source"),
                put("currency", fig.currency, "source"),
                put("period_end", fig.period_end, "source"),
                *_evidence_cells("TDR.6", row, fig.citation),
                put("quote", fig.citation.quote, "source"),
            ],
        )
    return table


def compose_peer_tables(
    pack: PeerPack, items: Mapping[str, EvidenceItem], cutoff: date
) -> "Composed":
    """TDR.4-6 facts and tables (no claims, no limitations); raises ``TablesInvalid``. ``cutoff``
    is ``ResearchBrief.cutoff``: a figure whose period ends after it composes as ``missing``."""
    from deploy_workflow.research.tables import Composed

    built = [_tdr4(pack, items), _tdr5(pack, items), _tdr6(pack, items, cutoff)]
    return Composed(
        facts=tuple(fact for table in built for fact in table.facts),
        tables=tuple(table.report() for table in built),
        claims=(),
        limitations=(),
    )
