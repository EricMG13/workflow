"""CP-DR research intake (O7b-1a): the user's research manifest to accepted ev-<n> items.

Pure over files the caller names: no clock (``today`` is injected), no network. A refused item gets
no id, is listed in ``research/rejected.json`` and never reaches a pack, a prompt or a dossier
body. Text is read as UTF-8; HTML is reduced to text with the stdlib parser only (R1).
"""

import hashlib
import json
import os
import re
import stat
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any, Literal

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
from deploy_workflow.research.webfetch import FetchRecord, UrlRefused, check_url

# The per-item cap is prepare's own limit (O7-R3, O7-R3a): it bounds the raw read here and the
# converted text below, because prepare refuses any staged source over MAX_BYTES.
MAX_ITEM_BYTES = MAX_BYTES
ROW_KEYS = ("path", "url", "family", "published", "locator", "tag", "source_id")
_HTML_SUFFIXES = frozenset({".html", ".htm"})
# A media type is repeated in a refusal only when it is this plain: Content-Type is server text
# and ``|`` is a legal token character (O7-R53).
_PLAIN_MEDIA = re.compile(r"[A-Za-z0-9.+-]+/[A-Za-z0-9.+-]+")
_NO_RULING = (
    "url rows need web retrieval, which is paused: give research_ruling, a user ruling under "
    "docs/rulings with lifts: live-provider-pause, by: user, date: and a configs: line naming "
    "web-retrieval"
)

# (url, hosts the manifest names) -> (record, retained raw body, Content-Type as sent).
Fetcher = Callable[[str, frozenset[str]], tuple[FetchRecord, bytes | None, str | None]]


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
    path: str | None
    family: str
    published: date | None
    locator: str
    sha256: str
    text: str
    origin: Literal["supplied", "web"] = "supplied"
    url: str | None = None

    def evidence_item(self) -> EvidenceItem:
        return EvidenceItem(
            item_id=self.item_id,
            origin=self.origin,
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
    fetches: tuple[FetchRecord, ...] = ()


def _text_field(row: Mapping[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise IntakeError(f"manifest row needs a non-empty {key}")
    return value


def _locator_text(row: Mapping[str, Any]) -> str:
    """The row's locator, which the dossier shows in a table cell and a fence header: a text the
    cell rule or the block-opener rule refuses is refused here, before any fetch (S3 I-3). The
    reason names no locator text."""
    from deploy_workflow.research.dossier import breaks_a_table_cell  # dossier imports this module

    text = _text_field(row, "locator")
    if breaks_a_table_cell(text):
        raise IntakeError(
            "manifest row locator contains a pipe character, a line feed or a carriage return, "
            "which a dossier table cell cannot hold"
        )
    if "<<<" in text:
        raise IntakeError("manifest row locator contains <<<, which a dossier block cannot show")
    return text


def _published(value: object) -> date | None:
    try:
        return None if value is None else date.fromisoformat(str(value))
    except ValueError as error:
        raise IntakeError(f"manifest row published {value!r} is not an ISO date") from error


def _check_url(url: str) -> None:
    """A url row's static shape; a wrong one is the user's file being wrong (O7b-2 D4)."""
    try:
        check_url(url)
    except UrlRefused as refusal:
        raise IntakeError(str(refusal)) from None


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
        url_text = None if url is None else _text_field(row, "url")
        if url_text is not None:
            _check_url(url_text)
        parsed.append(
            ManifestRow(
                path=None if path is None else _text_field(row, "path"),
                url=url_text,
                family=_text_field(row, "family"),
                published=_published(row.get("published")),
                locator=_locator_text(row),
                source_id=None if row.get("source_id") is None else str(row["source_id"]),
            )
        )
    return tuple(parsed)


def _refusal(row: ManifestRow, reason: str) -> RefusedItem:
    return RefusedItem(row.locator, row.family, row.published, reason)


def effective_cutoff(as_of: date, context_cutoff: str) -> date:
    """The research cutoff: ``min(as_of, run.cutoff)``; an absent context cutoff is the as-of date
    (O7b-2 D9, OD5; the context reader already refuses a later one)."""
    if context_cutoff == "":
        return as_of
    return min(as_of, date.fromisoformat(context_cutoff))


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


def _decode(raw: bytes, html: bool) -> str:
    """The item's text as prepare will see it, or a refusal reason."""
    if html:
        text = convert_html(raw).text.rstrip("\n")
    else:
        text = raw.decode("utf-8-sig")
        if "\x00" in text:
            raise _ItemRefused("holds NUL bytes, which prepare does not accept")
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise _ItemRefused(f"expands beyond {MAX_BYTES} bytes")
    return text


def _text(source: Path, max_bytes: int) -> str:
    raw = _read_capped(source, max_bytes)
    if len(raw) > max_bytes:
        raise _ItemRefused(f"exceeds the byte cap of {max_bytes} bytes")
    return _decode(raw, source.suffix.lower() in _HTML_SUFFIXES)


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


class _Unsupported(Exception):
    """A response whose Content-Type intake does not read; the message is the listed reason."""


def _utf8_only(params: Sequence[str]) -> bool:
    for param in params:
        name, _, value = param.partition("=")
        if name.strip().lower() == "charset" and value.strip().strip('"').lower() != "utf-8":
            return False
    return True


def _is_html(url: str, media: str | None) -> bool:
    """True for ``text/html``, False for ``text/plain`` (no charset, or utf-8); else raises
    ``_Unsupported``. Only the header decides (D7), and it is repeated in the reason only when it
    is plain (O7-R53), so a server cannot put a ``|``, a line break or ``<<<`` into a reason."""
    kind, *params = (media or "").split(";")
    kind = kind.strip().lower()
    if kind == "text/html":
        return True
    if kind == "text/plain":
        if _utf8_only(params):
            return False
        raise _Unsupported(f"{url} returned text/plain in an unsupported charset")
    if _PLAIN_MEDIA.fullmatch(kind):
        raise _Unsupported(f"{url} returned unsupported media type {kind}")
    raise _Unsupported(f"{url} returned an unsupported media type")


def _refused_after_fetch(
    row: ManifestRow, record: FetchRecord, reason: str
) -> tuple[RefusedItem, FetchRecord]:
    return _refusal(row, reason), replace(record, reason=reason)


def _assess_web(
    row: ManifestRow,
    url: str,
    item_id: str,
    dates: tuple[date, date, date],
    limits: tuple[int, str],
    fetch: Fetcher,
    hosts: frozenset[str],
) -> tuple[AcceptedItem | RefusedItem, FetchRecord | None]:
    """A url row: its own manifest-date refusals first, with no fetch and no record (O7-R48 L3);
    then the locator against the fence header rule (same, no fetch); then the fetch, the media
    type, a located date that can only refuse (D6), and the same text checks as a supplied item.
    The result and the record of the attempt (``item_id`` or ``reason`` set on it)."""
    as_of, cutoff, today = dates
    max_bytes, retrieved = limits
    if refusal := _date_refusal(row, as_of, cutoff, today):
        return refusal, None
    # The header fields (the locator among them) need only the row: a locator the fence refuses
    # can never admit the item, so no request is made for it and no record is written.
    if refusal := _fence_refusal(row, item_id, "0" * 64, "x", retrieved):
        return refusal, None
    record, body, media = fetch(url, hosts)
    if record.reason is not None:
        return _refusal(row, record.reason), record
    if body is None:
        raise IntakeError(f"the fetcher returned neither a body nor a reason for {url}")
    try:
        html = _is_html(url, media)
    except _Unsupported as error:
        return _refused_after_fetch(row, record, str(error))
    located = (
        None if record.published_located is None else date.fromisoformat(record.published_located)
    )
    if located is not None and located > cutoff:
        return _refused_after_fetch(
            row,
            record,
            f"evidence item {row.locator} has a located publication date {located} "
            f"after the cutoff {cutoff}",
        )
    try:
        if len(body) > max_bytes:
            raise _ItemRefused(f"exceeds the byte cap of {max_bytes} bytes")
        text = _decode(body, html)
    except (_ItemRefused, UnicodeDecodeError, UndecodableHtml) as error:
        return _refused_after_fetch(row, record, f"evidence item {row.locator} {_why(error)}")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if refusal := _fence_refusal(row, item_id, digest, text, retrieved):
        return _refused_after_fetch(row, record, refusal.reason)
    item = AcceptedItem(
        item_id, None, row.family, row.published, row.locator, digest, text, "web", url
    )
    return item, replace(record, item_id=item_id)


def _assess_row(
    row: ManifestRow,
    item_id: str,
    dates: tuple[date, date, date],
    limits: tuple[int, str],
    base_dir: Path,
    web: tuple[Fetcher | None, frozenset[str]],
) -> tuple[AcceptedItem | RefusedItem, FetchRecord | None]:
    """One row's result and, for a url row that was fetched, the record of the attempt."""
    if row.url is not None:
        fetch, hosts = web
        if fetch is None:
            raise EvidenceFetchRefused(_NO_RULING)
        return _assess_web(row, row.url, item_id, dates, limits, fetch, hosts)
    if row.path is None:
        raise IntakeError("manifest row names exactly one of path or url")
    source = _resolve(base_dir, row.path)
    return _assess(row, row.path, source, item_id, dates, limits[0]), None


def intake(
    rows: Sequence[ManifestRow],
    *,
    base_dir: Path,
    dest_dir: Path | None,
    as_of: date,
    cutoff: date,
    today: date,
    max_bytes: int = MAX_ITEM_BYTES,
    fetch: Fetcher | None = None,
    retrieved: str | None = None,
) -> IntakeResult:
    """Accept or refuse each row in manifest order; accepted items are copied to ``dest_dir``
    (``None`` assesses only and writes nothing: the text is on each ``AcceptedItem``, O7-R12).

    A url row is fetched through ``fetch`` (``None`` raises ``EvidenceFetchRefused`` naming the
    ruling the run needs); every attempted fetch is on ``IntakeResult.fetches``. ``retrieved`` is
    the fence's retrieval time for the check (default: the as-of date). A wrong input raises
    (reserved or stray source_id, a url row without a fetcher, a path outside ``base_dir``, cutoff
    after ``as_of``); item refusals are listed on the result. Every row is assessed before
    anything is copied, so a raise leaves no copy behind.
    """
    if cutoff > as_of:
        raise IntakeError(f"cutoff {cutoff} is after as_of {as_of}")
    hosts = frozenset(check_url(row.url).host for row in rows if row.url is not None)
    limits = (max_bytes, as_of.isoformat() if retrieved is None else retrieved)
    accepted: list[AcceptedItem] = []
    refused: list[RefusedItem] = []
    fetches: list[FetchRecord] = []
    for row in rows:
        if row.source_id is not None:
            refuse_reserved(row.source_id)
            raise IntakeError("manifest rows take no source_id: ids are assigned as ev-<n>")
        result, record = _assess_row(
            row, f"ev-{len(accepted) + 1}", (as_of, cutoff, today), limits, base_dir, (fetch, hosts)
        )
        if record is not None:
            fetches.append(record)
        if isinstance(result, RefusedItem):
            refused.append(result)
        else:
            accepted.append(result)
    if dest_dir is not None:
        for item in accepted:
            dest_dir.mkdir(parents=True, exist_ok=True)
            (dest_dir / f"{item.item_id}.txt").write_bytes(item.text.encode("utf-8"))
    return IntakeResult(tuple(accepted), tuple(refused), tuple(fetches))


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
