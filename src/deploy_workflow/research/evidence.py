"""CP-DR evidence record: ``research/evidence.json``, the one place a supplied item's retrieval time
lives (O7-R13), and the clock that makes it.

A leaf: it imports no host, run or loop module. ``research_clock`` is the only clock CP-DR reads;
tests replace it. The retrieval time is the intake instant in UTC to the second, recorded once at
staging and read back by the host, so a resumed run shows the value it began with.
"""

import json
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from deploy_workflow.research.intake import AcceptedItem

RESEARCH_DIR: Final = "research"
EVIDENCE_FILE: Final = "evidence.json"
REJECTED_FILE: Final = "rejected.json"
_KEYS: Final = ("item_id", "family", "published", "locator", "sha256", "retrieved", "path")


class EvidenceRecordInvalid(ValueError):
    """``evidence.json`` is missing, unreadable or not the shape the staging wrote."""


def research_clock() -> datetime:
    """The intake instant. Module-level so a test replaces it; the only clock CP-DR reads."""
    return datetime.now(UTC)


def retrieved_text(moment: datetime) -> str:
    """UTC to the second, as the fence header accepts it: ``2026-11-02T05:40:00Z``."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def evidence_bytes(accepted: Sequence[AcceptedItem], retrieved: str) -> bytes:
    """``[{item_id, family, published, locator, sha256, retrieved, path}]`` sorted by ``item_id``."""
    rows = [
        {
            "item_id": item.item_id,
            "family": item.family,
            "published": None if item.published is None else item.published.isoformat(),
            "locator": item.locator,
            "sha256": item.sha256,
            "retrieved": retrieved,
            "path": item.path,
        }
        for item in sorted(accepted, key=lambda item: int(item.item_id.removeprefix("ev-")))
    ]
    return (json.dumps(rows, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


def write_evidence(path: Path, accepted: Sequence[AcceptedItem], retrieved: str) -> bytes:
    """Write ``evidence.json`` (the directory exists) and return its bytes."""
    data = evidence_bytes(accepted, retrieved)
    path.write_bytes(data)
    return data


def read_evidence(path: Path) -> tuple[Mapping[str, Any], ...]:
    """The records of ``evidence.json``; any other shape raises ``EvidenceRecordInvalid``."""
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise EvidenceRecordInvalid(f"{path.name} cannot be read") from error
    if not isinstance(rows, list) or not all(
        isinstance(row, dict) and set(row) == set(_KEYS) for row in rows
    ):
        raise EvidenceRecordInvalid(f"{path.name} is not a list of evidence records")
    return tuple(rows)


def research_retrieved(execution_directory: Path, source_ids: Iterable[str]) -> dict[str, str]:
    """The ``ev-*`` retrieval times for ``SourceTools``: ``{}`` when no source id is an ``ev-*``
    (no file is read), else each record's time from ``<run>/research/evidence.json``, where the
    run directory is the parent of the execution directory. An absent record is simply absent:
    the caller decides what a missing time means."""
    if not any(source_id.startswith("ev-") for source_id in source_ids):
        return {}
    rows = read_evidence(execution_directory.parent / RESEARCH_DIR / EVIDENCE_FILE)
    return {str(row["item_id"]): str(row["retrieved"]) for row in rows}
