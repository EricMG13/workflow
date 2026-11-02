"""CP-DR research intake (O7b-1a): the user's research manifest to accepted ev-<n> items.

Pure over files the caller names: no clock (``today`` is injected), no network. A refused item gets
no id, is listed in ``research/rejected.json`` and never reaches a pack, a prompt or a dossier
body. Text is read as UTF-8; HTML is reduced to text with the stdlib parser only (R1).
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from deploy_workflow.prompts.fence import FenceError, UntrustedItem, untrusted_evidence_block
from deploy_workflow.research.contracts import (
    CutoffViolation,
    EvidenceFetchRefused,
    ResearchError,
    refuse_reserved,
)

# The plan names no per-item cap; this is the intake default, set explicitly by a caller.
MAX_ITEM_BYTES = 2_000_000
ROW_KEYS = ("path", "url", "family", "published", "locator", "tag", "source_id")
_HTML_SUFFIXES = frozenset({".html", ".htm"})
_BLOCK_TAGS = frozenset(
    {"p", "div", "br", "li", "ul", "ol", "tr", "table", "section", "article", "blockquote", "pre"}
    | {"h1", "h2", "h3", "h4", "h5", "h6", "hr", "header", "footer"}
)
_SKIPPED_TAGS = frozenset({"script", "style"})


class IntakeError(ResearchError):
    """The manifest or the intake arguments are malformed (not a per-item refusal)."""


@dataclass(frozen=True)
class ManifestRow:
    path: str | None
    url: str | None
    family: str
    published: date | None
    locator: str
    source_id: str | None


@dataclass(frozen=True)
class AcceptedItem:
    item_id: str
    path: str
    family: str
    published: date | None
    locator: str
    sha256: str
    text: str


@dataclass(frozen=True)
class RefusedItem:
    locator: str
    family: str
    published: date | None
    reason: str


@dataclass(frozen=True)
class IntakeResult:
    accepted: tuple[AcceptedItem, ...]
    refused: tuple[RefusedItem, ...]


def _text_field(row: Mapping[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise IntakeError(f"manifest row needs a non-empty {key}")
    return value


def _published(value: object) -> date | None:
    try:
        return None if value is None else date.fromisoformat(str(value))
    except ValueError as error:
        raise IntakeError(f"manifest row published {value!r} is not an ISO date") from error


def parse_rows(rows: Sequence[Mapping[str, Any]]) -> tuple[ManifestRow, ...]:
    """Validate the manifest rows; any malformed row stops intake (the user's file is wrong)."""
    parsed: list[ManifestRow] = []
    for row in rows:
        if unknown := sorted(set(row) - set(ROW_KEYS)):
            raise IntakeError(f"manifest row has unknown fields: {', '.join(unknown)}")
        if row.get("tag") != "research":
            raise IntakeError("manifest row tag must be 'research'")
        path, url = row.get("path"), row.get("url")
        if (path is None) == (url is None):
            raise IntakeError("manifest row names exactly one of path or url")
        parsed.append(
            ManifestRow(
                path=None if path is None else _text_field(row, "path"),
                url=None if url is None else _text_field(row, "url"),
                family=_text_field(row, "family"),
                published=_published(row.get("published")),
                locator=_text_field(row, "locator"),
                source_id=None if row.get("source_id") is None else str(row["source_id"]),
            )
        )
    return tuple(parsed)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skipping = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.skipping += tag in _SKIPPED_TAGS
        self.parts.append("\n" if tag in _BLOCK_TAGS else "")

    def handle_endtag(self, tag: str) -> None:
        self.skipping = max(0, self.skipping - (tag in _SKIPPED_TAGS))
        self.parts.append("\n" if tag in _BLOCK_TAGS else "")

    def handle_data(self, data: str) -> None:
        self.parts.append("" if self.skipping else data)


def html_to_text(markup: str) -> str:
    """Visible text of an HTML page: script and style dropped, block tags become line breaks."""
    extractor = _TextExtractor()
    extractor.feed(markup)
    extractor.close()
    lines = (" ".join(line.split()) for line in "".join(extractor.parts).splitlines())
    return "\n".join(line for line in lines if line)


def _refusal(row: ManifestRow, reason: str) -> RefusedItem:
    return RefusedItem(row.locator, row.family, row.published, reason)


def _date_refusal(row: ManifestRow, as_of: date, cutoff: date, today: date) -> RefusedItem | None:
    if row.published is None:
        if as_of < today:
            return _refusal(row, f"undated evidence item refused: as_of {as_of} is before today")
        return None
    if row.published > cutoff:
        return _refusal(row, str(CutoffViolation(row.locator)))
    return None


def _resolve(base_dir: Path, relative: str) -> Path:
    base = base_dir.resolve()
    target = (base / relative).resolve()
    if not target.is_relative_to(base):
        raise IntakeError(f"manifest path {relative!r} is outside the manifest directory")
    return target


def _read(row: ManifestRow, source: Path, max_bytes: int) -> str | RefusedItem:
    raw = source.read_bytes()
    if len(raw) > max_bytes:
        return _refusal(
            row, f"evidence item {row.locator} exceeds the byte cap of {max_bytes} bytes"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return _refusal(row, f"evidence item {row.locator} is not valid UTF-8")
    return html_to_text(text) if source.suffix.lower() in _HTML_SUFFIXES else text


def _fence_refusal(
    row: ManifestRow, provisional_id: str, digest: str, text: str, retrieved: str
) -> RefusedItem | None:
    """Use the O6 fence's own check; no second terminator rule lives here."""
    try:
        untrusted_evidence_block(
            [UntrustedItem(provisional_id, digest, row.locator, retrieved, text)]
        )
    except FenceError as error:
        reason = str(error).replace(f"evidence {provisional_id} ", f"evidence item {row.locator} ")
        return _refusal(row, reason)
    return None


def intake(
    rows: Sequence[ManifestRow],
    *,
    base_dir: Path,
    dest_dir: Path,
    as_of: date,
    cutoff: date,
    today: date,
    max_bytes: int = MAX_ITEM_BYTES,
) -> IntakeResult:
    """Accept or refuse each row in manifest order; accepted items are copied to ``dest_dir``.

    A wrong input raises (reserved or stray source_id, a url row while web retrieval is paused, a
    path outside ``base_dir``, cutoff after ``as_of``); item refusals are listed on the result.
    """
    if cutoff > as_of:
        raise IntakeError(f"cutoff {cutoff} is after as_of {as_of}")
    accepted: list[AcceptedItem] = []
    refused: list[RefusedItem] = []
    for row in rows:
        if row.source_id is not None:
            refuse_reserved(row.source_id)
            raise IntakeError("manifest rows take no source_id: ids are assigned as ev-<n>")
        if row.path is None:
            raise EvidenceFetchRefused("url rows need web retrieval, which is not available")
        if refusal := _date_refusal(row, as_of, cutoff, today):
            refused.append(refusal)
            continue
        text = _read(row, _resolve(base_dir, row.path), max_bytes)
        if isinstance(text, RefusedItem):
            refused.append(text)
            continue
        body = text.encode("utf-8")
        digest = hashlib.sha256(body).hexdigest()
        item_id = f"ev-{len(accepted) + 1}"
        if refusal := _fence_refusal(row, item_id, digest, text, as_of.isoformat()):
            refused.append(refusal)
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / f"{item_id}.txt").write_bytes(body)
        accepted.append(
            AcceptedItem(item_id, row.path, row.family, row.published, row.locator, digest, text)
        )
    return IntakeResult(tuple(accepted), tuple(refused))


def rejected_bytes(refused: Sequence[RefusedItem]) -> bytes:
    """``research/rejected.json``: ``[{locator, family, published, reason}]`` sorted by locator."""
    entries = [
        {
            "locator": r.locator,
            "family": r.family,
            "published": None if r.published is None else r.published.isoformat(),
            "reason": r.reason,
        }
        for r in sorted(refused, key=lambda r: r.locator)
    ]
    return (json.dumps(entries, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


def write_rejected(path: Path, refused: Sequence[RefusedItem]) -> str:
    """Write rejected.json and return its sha256."""
    data = rejected_bytes(refused)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
