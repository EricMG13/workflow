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
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from functools import partial
from typing import TYPE_CHECKING, Final, Literal, get_args

from deploy_vii.contracts import Citation, Contract, Fact, Identifier, Module, Source, Text
from deploy_vii.readiness import citation_issues
from deploy_workflow.research.contracts import RESERVED_PREFIX, EvidenceItem, ResearchBrief

if TYPE_CHECKING:
    from deploy_workflow.owners.cp1c import PeerRow, PeerSheet
    from deploy_workflow.owners.period_basis import PeriodBasis
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
# A peer id sits in every fact id of its rows: `TDR.4.<id>.<field>`, `TDR.5.<id>.<dimension>.<field>`
# and `TDR.6.<id>.<operand>.<field>`. The longest tail decides (TDR.5 with `definition` and
# `observation`); one id past this makes `Fact` raise after the binding write.
LONGEST_OPERAND: Final = "interest"  # a test compares it with `cp1c.OPERANDS`


def _longest_tail(prefix: str, middle: Sequence[str], columns: Sequence[str]) -> int:
    return len(prefix) + max((len(m) + 1 for m in middle), default=0) + 1 + max(map(len, columns))


PEER_ID_MAX: Final = 160 - max(
    _longest_tail("TDR.4.", (), TDR4_COLUMNS),
    _longest_tail("TDR.5.", get_args(Dimension), TDR5_COLUMNS),
    _longest_tail("TDR.6.", (LONGEST_OPERAND,), TDR6_COLUMNS),
)


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
    """The figure a quote states, read by CP-1C's own table rule (``cp1c._amount``); ``None``
    when that rule refuses it or the quote is the not-stated token."""
    from deploy_workflow.owners.cp1c import PeerTableError, _amount

    try:
        return _amount(quote)
    except PeerTableError:
        return None


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


# --- the pack as CP-1C's peer sheet (O7d D2) --------------------------------------------------------
#
# CP-1C builds its peer sheet from the bound CP-DR head's TDR.4 names and TDR.6 figures when no user
# `peers` source is held. The amounts are the head's own facts (Python read them from the quotes); the
# model-written texts the sheet shows (a peer's name, a figure's unit and currency) are checked here
# with the fence's and the table cell's own rules before they reach a CP-1C prompt, issue or view.


@dataclass(frozen=True)
class NotAdmitted:
    """A candidate peer kept off the sheet, with the reason CP-1C's view shows. ``currency`` and
    ``unit`` are the cells that decided it (``None`` when no figure was located)."""

    peer_id: str
    name: str
    currency: str | None
    unit: str | None
    reason: str


@dataclass(frozen=True)
class PackUnusable:
    """The head's TDR.4-6 facts cannot be read as a sheet; ``reason`` names no model text."""

    reason: str


class _Unusable(Exception):
    """A TDR cell the sheet cannot read (internal: ``peer_sheet`` returns it as ``PackUnusable``)."""


@dataclass(frozen=True)
class _Figure:
    operand: str
    amount: Decimal | None
    unit: str
    currency: str
    period_end: str
    citation: Citation | None


def carries_tdr6(module: Module) -> bool:
    """The head holds TDR.6 facts, so CP-1C's peers are the pack's."""
    return any(fact.table_id == "TDR.6" for fact in module.facts)


def _table(module: Module, table_id: str) -> dict[str, dict[str, Fact]]:
    rows: dict[str, dict[str, Fact]] = {}
    for fact in module.facts:
        if fact.table_id == table_id:
            rows.setdefault(fact.row_id or "", {})[fact.field or ""] = fact
    return rows


def _unsafe(where: str, text: str) -> str | None:
    """Why ``text`` may not be shown (the dossier fence's own check and the table cell rule), else
    None. The text itself is never named."""
    from deploy_workflow.prompts.fence import FenceError, data_block
    from deploy_workflow.research.dossier import breaks_a_table_cell

    try:
        data_block("CONTEXT", "dossier", text)
    except FenceError:
        return f"{where}: holds a block delimiter or a lookalike of one"
    if breaks_a_table_cell(text):
        return f"{where}: holds a line break or a |"
    return None


def _cell_text(where: str, cells: Mapping[str, Fact], field: str) -> str:
    fact = cells.get(field)
    if fact is None or fact.status != "known" or not fact.text:
        raise _Unusable(f"{where}: the {field} cell is not a stated text")
    if (why := _unsafe(f"{where} {field}", fact.text)) is not None:
        raise _Unusable(why)
    return fact.text


def _located_amount(where: str, cell: Fact | None) -> tuple[Decimal | None, Citation | None]:
    """The amount cell as (amount, its one ``ev-*`` citation); (None, None) for a ``missing`` cell."""
    if cell is None or cell.status not in ("known", "missing"):
        raise _Unusable(f"{where}: the amount cell is neither located nor missing")
    if cell.status == "missing":
        return None, None
    cites = cell.citations
    if cell.amount is None or len(cites) != 1 or not cites[0].source_id.startswith(RESERVED_PREFIX):
        raise _Unusable(f"{where}: the amount cell is not one number quoted from an ev-* item")
    return cell.amount, cites[0]


def _figures(module: Module, candidates: set[str]) -> dict[str, list[_Figure]]:
    from deploy_workflow.owners.cp1c import OPERANDS

    operands = {key for key, _ in OPERANDS}
    found: dict[str, list[_Figure]] = {}
    for row, cells in _table(module, "TDR.6").items():
        peer_id, _, operand = row.rpartition(".")
        where = f"TDR.6 {row}"
        if peer_id not in candidates or operand not in operands:
            raise _Unusable(f"{where}: not a TDR.4 peer's CP-1C operand")
        amount, citation = _located_amount(where, cells.get("amount"))
        period_end = _cell_text(where, cells, "period_end")
        if period_end_date(period_end) is None:
            raise _Unusable(f"{where}: period_end is not a calendar date")
        found.setdefault(peer_id, []).append(
            _Figure(
                operand,
                amount,
                _cell_text(where, cells, "unit"),
                _cell_text(where, cells, "currency"),
                period_end,
                citation,
            )
        )
    return found


def _candidates(module: Module) -> list[tuple[str, str]]:
    """(peer_id, name) in TDR.4 order; two peers with one name are unusable (CP-1C assesses a peer
    by its name)."""
    names: list[tuple[str, str]] = []
    for peer_id, cells in _table(module, "TDR.4").items():
        names.append((peer_id, _cell_text(f"TDR.4 {peer_id}", cells, "name")))
    if len({name for _, name in names}) != len(names):
        raise _Unusable("TDR.4: two peers share one name")
    return names


def _refusal(peer_id: str, name: str, fig: _Figure, why: str) -> NotAdmitted:
    return NotAdmitted(peer_id, name, fig.currency, fig.unit, why)


def _basis_refusal(
    peer_id: str, name: str, figures: Sequence[_Figure], currency: str
) -> NotAdmitted | None:
    """The first figure not in the run's currency, or not in millions, as the reason."""
    for fig in figures:
        if fig.currency != currency:
            return _refusal(
                peer_id, name, fig, f"currency {fig.currency} is not the run's {currency}"
            )
        if fig.unit != "millions":
            return _refusal(peer_id, name, fig, f"unit {fig.unit} is not millions")
    return None


def _admit(
    peer_id: str, name: str, figures: Sequence[_Figure], currency: str
) -> "PeerRow | NotAdmitted":
    """One sheet row, or why the peer is kept off: no figure located, a figure in another currency
    or unit, or located figures that end on different dates."""
    from deploy_workflow.owners.cp1c import OPERANDS, PeerRow

    if not figures:
        return NotAdmitted(peer_id, name, None, None, "no figure is located")
    if (refused := _basis_refusal(peer_id, name, figures, currency)) is not None:
        return refused
    known = [fig for fig in figures if fig.amount is not None and fig.citation is not None]
    ends = {fig.period_end for fig in known}
    if len(ends) != 1:
        why = (
            "no figure amount is located"
            if not known
            else "the located figures end on different dates"
        )
        return NotAdmitted(peer_id, name, figures[0].currency, figures[0].unit, why)
    amounts: dict[str, Decimal | None] = {key: None for key, _ in OPERANDS}
    cites: dict[str, Citation] = {}
    for fig in known:
        amounts[fig.operand] = fig.amount
        if fig.citation is not None:
            cites[fig.operand] = fig.citation
    first = next(iter(cites.values()))
    return PeerRow(name, ends.pop(), amounts, first.quote, None, cites)


def _sheet(module: Module, basis: "PeriodBasis") -> "PeerSheet":
    from deploy_workflow.owners.cp1c import PeerRow, PeerSheet

    named = _candidates(module)
    figures = _figures(module, {peer_id for peer_id, _ in named})
    admitted = [_admit(i, name, figures.get(i, ()), basis.currency) for i, name in named]
    rows = tuple(a for a in admitted if isinstance(a, PeerRow))
    refused = tuple(a for a in admitted if isinstance(a, NotAdmitted))
    unit, scale = UNIT_FACT["millions"]
    return PeerSheet(
        module.content_hash(), basis.currency, unit, Decimal(scale), None, rows, refused
    )


def peer_sheet(module: Module, basis: "PeriodBasis") -> "PeerSheet | PackUnusable":
    """The peer sheet of a CP-DR head's TDR.4 names and TDR.6 located figures, or why the pack is
    unusable. A row is a TDR.4 peer whose figures are all in the run's currency (``basis.currency``)
    and in millions, whose located amounts end on one date; its amounts are the head's own facts
    (``None`` where a cell is ``missing``). The sheet has no issuer row. Another peer is listed in
    ``not_admitted`` with its reason. Every model-written text it carries (a name, a unit, a currency)
    passed the dossier fence and the table cell rule first."""
    try:
        return _sheet(module, basis)
    except _Unusable as error:
        return PackUnusable(str(error))
