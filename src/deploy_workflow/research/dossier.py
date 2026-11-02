"""CP-DR dossier and ``brief.json`` renderer (O7b-1b, Behaviour 9).

Pure over plain data the CP-DR head supplies (O7b-1c passes the real head): the head's tables and
facts, the locked brief, the accepted evidence list, the rejected items and the head's
``result_sha256``. Readiness is ``assign_readiness`` over the claim states, so it is never above
``RESEARCH_READY`` and the lineage is always ``LOCAL``. The dossier is the Q10 layout: LF, UTF-8,
one trailing LF; a cell is its shown string.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from deploy_workflow.research.contracts import (
    METHOD_VERSION_CPDR,
    ClaimState,
    Dossier,
    EvidenceItem,
    Lineage,
    Readiness,
    ResearchBrief,
    ResearchError,
    assign_readiness,
)
from deploy_workflow.research.intake import RefusedItem

TABLE_IDS: Final = ("TDR.1", "TDR.2", "TDR.3")
LIMITATIONS_TABLE: Final = "TDR.3"
UNDATED: Final = "undated"
LINEAGE: Final[Lineage] = "LOCAL"


class DossierInvalid(ResearchError):
    """The head's data cannot be written as the dossier layout."""


class DossierMismatch(ResearchError):
    """The rendered dossier is not the bytes the CP-DR head hashed."""


@dataclass(frozen=True)
class DossierInput:
    """What the CP-DR head hands the renderer; plain typed data, no owner object.

    ``tables`` maps ``TDR.n`` to ``{title, row_header, columns, rows: [[row_id, {column: cell}]]}``
    and every cell carries ``shown``; ``facts`` are the head's fact records (``row_id``, ``field``,
    ``status``, optional ``limitation``); ``claim_states`` is one state per brief question.
    """

    brief: ResearchBrief
    claim_states: tuple[ClaimState, ...]
    tables: Mapping[str, Mapping[str, Any]]
    facts: Sequence[Mapping[str, Any]]
    evidence: Sequence[EvidenceItem]
    rejected: Sequence[RefusedItem]
    result_sha256: str


@dataclass(frozen=True)
class RenderedDossier:
    markdown: str
    brief_json: str
    dossier_sha256: str
    brief_file_sha256: str
    readiness: Readiness
    lineage: Lineage


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _cell(where: str, value: object) -> str:
    text = str(value)
    if "|" in text or "\n" in text or "\r" in text:
        raise DossierInvalid(f"{where} cannot be written in a table cell")
    if "<<<" in text:  # CP-2 reads the dossier through fences that refuse any block opener
        raise DossierInvalid(f"{where} holds a block delimiter and cannot be shown")
    return text


def _md(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    out += ["| " + " | ".join(row) + " |" for row in rows]
    return out


def _table(table_id: str, table: Mapping[str, Any]) -> list[str]:
    columns: list[str] = list(table["columns"])
    rows: list[list[str]] = []
    for row_id, cells in table["rows"]:
        where = f"{table_id} {row_id}"
        missing = [column for column in columns if column not in cells]
        if missing:
            raise DossierInvalid(f"{where} has no cell for {', '.join(missing)}")
        rows.append(
            [_cell(where, row_id)]
            + [_cell(f"{where} {column}", cells[column]["shown"]) for column in columns]
        )
    return _md([str(table["row_header"]), *columns], rows)


def _limitations(facts: Sequence[Mapping[str, Any]]) -> list[str]:
    """L1: the limitation text of a gap is listed where the TDR.3 limitations are."""
    seen: list[str] = []
    for fact in facts:
        if fact.get("table_id") != LIMITATIONS_TABLE or not fact.get("limitation"):
            continue
        if fact["status"] != "known" or fact["field"] == "answer":
            entry = f"- {_cell(LIMITATIONS_TABLE, fact['row_id'])}: {_cell(LIMITATIONS_TABLE, fact['limitation'])}"
            if entry not in seen:
                seen.append(entry)
    return seen


def _date(value: object) -> str:
    return UNDATED if value is None else str(value)


def dossier_markdown(given: DossierInput) -> str:
    """The Markdown dossier; raises ``DossierInvalid`` for a table it cannot write."""
    absent = [table_id for table_id in TABLE_IDS if table_id not in given.tables]
    if absent:
        raise DossierInvalid(f"the head has no table {', '.join(absent)}")
    readiness = assign_readiness(given.claim_states)
    lines = [
        "# CP-DR research dossier",
        f"cp_dr_version: {METHOD_VERSION_CPDR}",
        f"cp_dr_lineage: {LINEAGE}",
        f"readiness: {readiness}",
        f"brief_sha256: {given.brief.brief_sha256}",
        "",
        "## Evidence",
        "",
    ]
    lines += _md(
        ["id", "family", "published", "sha256", "locator"],
        [
            [
                _cell(f"evidence {e.item_id}", value)
                for value in (e.item_id, e.family, _date(e.published), e.sha256, e.locator)
            ]
            for e in given.evidence
        ],
    )
    for table_id in TABLE_IDS:
        lines += ["", f"## {table_id}", ""]
        lines += _table(table_id, given.tables[table_id])
        if table_id == LIMITATIONS_TABLE and (limits := _limitations(given.facts)):
            lines += ["", "### TDR.3 limitations", "", *limits]
    lines += ["", "## Rejected items", ""]
    lines += _md(
        ["locator", "family", "published", "reason"],
        [
            [
                _cell("rejected item", value)
                for value in (r.locator, r.family, _date(r.published), r.reason)
            ]
            for r in given.rejected
        ],
    )
    return "\n".join(lines) + "\n"


def brief_json(brief: ResearchBrief) -> str:
    """The locked brief as the oracle writes it: sorted keys, indent 1, one trailing LF."""
    body = json.dumps(brief.model_dump(mode="json"), sort_keys=True, indent=1, ensure_ascii=False)
    return body + "\n"


def render_dossier(given: DossierInput) -> RenderedDossier:
    """Markdown, ``brief.json`` and the hashes. The dossier's hash must be the head's
    ``result_sha256`` (the head hashes the dossier bytes); any other value is ``DossierMismatch``."""
    markdown = dossier_markdown(given)
    digest = _sha256(markdown)
    if digest != given.result_sha256:
        raise DossierMismatch(
            f"dossier sha256 {digest} is not the head result_sha256 {given.result_sha256}"
        )
    readiness = assign_readiness(given.claim_states)
    # Validates the ceiling: a LOCAL dossier is never COMMITTEE_READY.
    Dossier(brief_sha256=given.brief.brief_sha256, lineage=LINEAGE, readiness=readiness)
    text = brief_json(given.brief)
    return RenderedDossier(
        markdown=markdown,
        brief_json=text,
        dossier_sha256=digest,
        brief_file_sha256=_sha256(text),
        readiness=readiness,
        lineage=LINEAGE,
    )
