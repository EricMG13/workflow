"""CP-DR evidence record: ``research/evidence.json``, the one place a supplied item's retrieval time
lives (O7-R13), and the clock that makes it.

A leaf: it imports no host, run or loop module. ``research_clock`` is the only clock CP-DR reads;
tests replace it. The retrieval time is the intake instant in UTC to the second, recorded once at
staging and read back by the host, so a resumed run shows the value it began with.
"""

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import fields
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from deploy_workflow.research.intake import AcceptedItem
from deploy_workflow.research.webfetch import FetchRecord

RESEARCH_DIR: Final = "research"
EVIDENCE_FILE: Final = "evidence.json"
REJECTED_FILE: Final = "rejected.json"
FETCHES_FILE: Final = "fetches.json"
MANIFEST_SHA_FILE: Final = "manifest.sha256"
RULING_SHA_FILE: Final = "ruling.sha256"
_KEYS: Final = (
    "item_id",
    "family",
    "published",
    "locator",
    "sha256",
    "retrieved",
    "path",
    "origin",
    "url",
)
_FETCH_KEYS: Final = tuple(field.name for field in fields(FetchRecord))
_TIME: Final = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")


class EvidenceRecordInvalid(ValueError):
    """``evidence.json`` is missing, unreadable or not the shape the staging wrote."""


def research_clock() -> datetime:
    """The intake instant. Module-level so a test replaces it; the only clock CP-DR reads."""
    return datetime.now(UTC)


def retrieved_text(moment: datetime) -> str:
    """UTC to the second, as the fence header accepts it: ``2026-11-02T05:40:00Z``."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def evidence_rows(accepted: Sequence[AcceptedItem], retrieved: str) -> list[dict[str, Any]]:
    """The records, sorted by ``item_id``: ``{item_id, family, published, locator, sha256,
    retrieved, path, origin, url}`` (a supplied item has a ``path`` and no ``url``; a web item the
    reverse)."""
    return [
        {
            "item_id": item.item_id,
            "family": item.family,
            "published": None if item.published is None else item.published.isoformat(),
            "locator": item.locator,
            "sha256": item.sha256,
            "retrieved": retrieved,
            "path": item.path,
            "origin": item.origin,
            "url": item.url,
        }
        for item in sorted(accepted, key=lambda item: int(item.item_id.removeprefix("ev-")))
    ]


def evidence_bytes(accepted: Sequence[AcceptedItem], retrieved: str) -> bytes:
    rows = evidence_rows(accepted, retrieved)
    return (json.dumps(rows, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


def write_evidence(path: Path, accepted: Sequence[AcceptedItem], retrieved: str) -> bytes:
    """Write ``evidence.json`` (the directory exists) and return its bytes."""
    data = evidence_bytes(accepted, retrieved)
    path.write_bytes(data)
    return data


def _valid_time(value: object) -> bool:
    if not isinstance(value, str) or not _TIME.fullmatch(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return True


def _located(row: Mapping[str, Any]) -> bool:
    """A supplied row names a path and no url; a web row a url and no path (O7b-2 D10)."""
    if row["origin"] == "supplied":
        return isinstance(row["path"], str) and row["url"] is None
    if row["origin"] == "web":
        return row["path"] is None and isinstance(row["url"], str)
    return False


def _valid_row(row: object) -> bool:
    if not isinstance(row, dict) or set(row) != set(_KEYS):
        return False
    texts = all(isinstance(row[k], str) for k in _KEYS if k not in ("published", "path", "url"))
    return (
        texts
        and _located(row)
        and (row["published"] is None or isinstance(row["published"], str))
        and _valid_time(row["retrieved"])
    )


def read_evidence(path: Path) -> tuple[Mapping[str, Any], ...]:
    """The records of ``evidence.json``; any other shape raises ``EvidenceRecordInvalid``: every
    value a string (``published`` may be null; ``path`` xor ``url`` is the string, by ``origin``),
    ``retrieved`` a full UTC-second time, and unique ``item_id``s."""
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError) as error:
        raise EvidenceRecordInvalid(f"{path.name} cannot be read") from error
    if not isinstance(rows, list) or not all(_valid_row(row) for row in rows):
        raise EvidenceRecordInvalid(f"{path.name} is not a list of evidence records")
    if len({row["item_id"] for row in rows}) != len(rows):
        raise EvidenceRecordInvalid(f"{path.name} repeats an item_id")
    return tuple(rows)


def fetches_bytes(records: Sequence[FetchRecord]) -> bytes:
    """``research/fetches.json``: one entry per attempted fetch, in manifest order."""
    entries = [{name: getattr(record, name) for name in _FETCH_KEYS} for record in records]
    return (json.dumps(entries, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


def write_fetches(path: Path, records: Sequence[FetchRecord]) -> bytes:
    """Write ``fetches.json`` (the directory exists) and return its bytes."""
    data = fetches_bytes(records)
    path.write_bytes(data)
    return data


def _text_or_none(value: object) -> bool:
    return value is None or isinstance(value, str)


def _int_or_none(value: object) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool))


def _valid_fetch(entry: object) -> bool:
    if not isinstance(entry, dict) or set(entry) != set(_FETCH_KEYS):
        return False
    hops = entry["hops"]
    return (
        isinstance(entry["url"], str)
        and isinstance(hops, int)
        and not isinstance(hops, bool)
        and _int_or_none(entry["status"])
        and _int_or_none(entry["bytes"])
        and all(
            _text_or_none(entry[k])
            for k in ("resolved_ip", "sha256", "published_located", "published_source")
        )
        and _text_or_none(entry["item_id"])
        and _text_or_none(entry["reason"])
    )


def read_fetches(path: Path) -> tuple[FetchRecord, ...]:
    """The records of ``fetches.json``; any other shape raises ``EvidenceRecordInvalid``."""
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError) as error:
        raise EvidenceRecordInvalid(f"{path.name} cannot be read") from error
    if not isinstance(entries, list) or not all(_valid_fetch(entry) for entry in entries):
        raise EvidenceRecordInvalid(f"{path.name} is not a list of fetch records")
    return tuple(FetchRecord(**entry) for entry in entries)


def write_manifest_sha(path: Path, digest: str) -> None:
    """Record the research manifest's sha256 at staging (``research/manifest.sha256``)."""
    path.write_text(digest + "\n", encoding="ascii")


def read_manifest_sha(path: Path) -> str:
    try:
        return path.read_text(encoding="ascii").strip()
    except (OSError, ValueError) as error:
        raise EvidenceRecordInvalid(f"{path.name} cannot be read") from error


def research_retrieved(execution_directory: Path, source_ids: Iterable[str]) -> dict[str, str]:
    """The ``ev-*`` retrieval times for ``SourceTools``: ``{}`` when no source id is an ``ev-*``
    (no file is read), else each record's time from ``<run>/research/evidence.json``, where the
    run directory is the parent of the execution directory. An absent record is simply absent:
    the caller decides what a missing time means."""
    if not any(source_id.startswith("ev-") for source_id in source_ids):
        return {}
    rows = read_evidence(execution_directory.parent / RESEARCH_DIR / EVIDENCE_FILE)
    return {str(row["item_id"]): str(row["retrieved"]) for row in rows}


def research_hashes(execution_directory: Path, source_ids: Iterable[str]) -> dict[str, str]:
    """The recorded sha256 of each ``ev-*`` item (``{}`` when no source id is an ``ev-*``), read
    from the same record as ``research_retrieved``."""
    if not any(source_id.startswith("ev-") for source_id in source_ids):
        return {}
    rows = read_evidence(execution_directory.parent / RESEARCH_DIR / EVIDENCE_FILE)
    return {str(row["item_id"]): str(row["sha256"]) for row in rows}
