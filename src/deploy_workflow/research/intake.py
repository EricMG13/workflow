"""CP-DR research intake (O7b-1a): the user's research manifest to accepted ev-<n> items.

Pure over files the caller names: no clock (``today`` is injected), no network. A refused item gets
no id, is listed in ``research/rejected.json`` and never reaches a pack, a prompt or a dossier
body. Text is read as UTF-8; HTML is reduced to text with the stdlib parser only (R1).
"""

import hashlib
import json
import os
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from deploy_vii.preparation import MAX_BYTES
from deploy_workflow.html_text import UndecodableHtml, convert_html
from deploy_workflow.prompts.fence import FenceError, UntrustedItem, untrusted_evidence_block
from deploy_workflow.research.contracts import (
    CutoffViolation,
    EvidenceFetchRefused,
    EvidenceItem,
    ResearchError,
    refuse_reserved,
)

# The per-item cap is prepare's own limit (O7-R3, O7-R3a): it bounds the raw read here and the
# converted text below, because prepare refuses any staged source over MAX_BYTES.
MAX_ITEM_BYTES = MAX_BYTES
ROW_KEYS = ("path", "url", "family", "published", "locator", "tag", "source_id")
_HTML_SUFFIXES = frozenset({".html", ".htm"})


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

    def evidence_item(self) -> EvidenceItem:
        return EvidenceItem(
            item_id=self.item_id,
            origin="supplied",
            sha256=self.sha256,
            locator=self.locator,
            published=self.published,
            family=self.family,
        )


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


class _ItemRefused(Exception):
    """A reason an item cannot be taken (unreadable, over the cap, NUL); becomes a listed refusal."""


def _read_capped(source: Path, cap: int) -> bytes:
    """Mirror of ``run_inputs.read_capped`` with the caller's cap: one descriptor, opened without
    blocking, ``fstat`` for a regular file (FIFO, directory, device refused), at most cap + 1 bytes."""
    try:
        fd = os.open(source, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC | os.O_NOFOLLOW)
    except (OSError, ValueError) as error:
        raise _ItemRefused(
            f"cannot be opened ({getattr(error, 'strerror', None) or error})"
        ) from None
    try:
        regular = stat.S_ISREG(os.fstat(fd).st_mode)
    except OSError as error:
        os.close(fd)
        raise _ItemRefused(f"cannot be examined ({error.strerror})") from None
    if not regular:
        os.close(fd)
        raise _ItemRefused("is not a regular file")
    try:
        with os.fdopen(fd, "rb") as handle:
            return handle.read(cap + 1)
    except OSError as error:
        raise _ItemRefused(f"cannot be read ({error.strerror})") from None


def _text(source: Path, max_bytes: int) -> str:
    """The item's text as prepare will see it, or a refusal reason."""
    raw = _read_capped(source, max_bytes)
    if len(raw) > max_bytes:
        raise _ItemRefused(f"exceeds the byte cap of {max_bytes} bytes")
    if source.suffix.lower() in _HTML_SUFFIXES:
        text = convert_html(raw).text.rstrip("\n")
    else:
        text = raw.decode("utf-8-sig")
        if "\x00" in text:
            raise _ItemRefused("holds NUL bytes, which prepare does not accept")
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise _ItemRefused(f"expands beyond {MAX_BYTES} bytes")
    return text


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


def _assess(
    row: ManifestRow,
    path: str,
    source: Path,
    item_id: str,
    dates: tuple[date, date, date],
    max_bytes: int,
) -> AcceptedItem | RefusedItem:
    as_of, cutoff, today = dates
    if refusal := _date_refusal(row, as_of, cutoff, today):
        return refusal
    try:
        text = _text(source, max_bytes)
    except (_ItemRefused, UnicodeDecodeError, UndecodableHtml) as error:
        return _refusal(row, f"evidence item {row.locator} {_why(error)}")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if refusal := _fence_refusal(row, item_id, digest, text, as_of.isoformat()):
        return refusal
    return AcceptedItem(item_id, path, row.family, row.published, row.locator, digest, text)


def _why(error: Exception) -> str:
    if isinstance(error, UnicodeDecodeError):
        return "is not valid UTF-8"
    if isinstance(error, UndecodableHtml):
        return f"is not decodable HTML ({error})"
    return str(error)


def intake(
    rows: Sequence[ManifestRow],
    *,
    base_dir: Path,
    dest_dir: Path | None,
    as_of: date,
    cutoff: date,
    today: date,
    max_bytes: int = MAX_ITEM_BYTES,
) -> IntakeResult:
    """Accept or refuse each row in manifest order; accepted items are copied to ``dest_dir``
    (``None`` assesses only and writes nothing: the text is on each ``AcceptedItem``, O7-R12).

    A wrong input raises (reserved or stray source_id, a url row while web retrieval is paused, a
    path outside ``base_dir``, cutoff after ``as_of``); item refusals are listed on the result.
    Every row is assessed before anything is copied, so a raise leaves no copy behind.
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
        source = _resolve(base_dir, row.path)
        item_id = f"ev-{len(accepted) + 1}"
        result = _assess(row, row.path, source, item_id, (as_of, cutoff, today), max_bytes)
        if isinstance(result, RefusedItem):
            refused.append(result)
        else:
            accepted.append(result)
    if dest_dir is not None:
        for item in accepted:
            dest_dir.mkdir(parents=True, exist_ok=True)
            (dest_dir / f"{item.item_id}.txt").write_bytes(item.text.encode("utf-8"))
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
