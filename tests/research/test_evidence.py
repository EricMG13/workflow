"""O7b-1c S1: the evidence record and the one research clock (``research/evidence.py``)."""

import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from deploy_workflow.research import evidence as ev
from deploy_workflow.research.intake import AcceptedItem

RETRIEVED = "2026-11-02T05:40:00Z"


def accepted(expected: dict[str, Any]) -> list[AcceptedItem]:
    return [
        AcceptedItem(
            a["item_id"],
            a["path"],
            a["family"],
            None if a["published"] is None else datetime.fromisoformat(a["published"]).date(),
            a["locator"],
            a["sha256"],
            "text",
        )
        for a in expected["intake"]["accepted"]
    ]


def test_the_default_clock_is_now_in_utc() -> None:
    before = datetime.now(UTC)
    moment = ev.research_clock()
    assert moment.tzinfo is not None and moment.utcoffset() == timedelta(0)
    assert before <= moment <= datetime.now(UTC)


def test_retrieved_text_is_utc_to_the_second() -> None:
    plus_two = timezone(timedelta(hours=2))
    assert ev.retrieved_text(datetime(2026, 11, 2, 7, 40, 0, 999999, tzinfo=plus_two)) == RETRIEVED


def test_evidence_json_round_trips_sorted_by_item_id(
    tmp_path: Path, expected: dict[str, Any]
) -> None:
    items = accepted(expected)
    target = tmp_path / "evidence.json"
    data = ev.write_evidence(target, list(reversed(items)), RETRIEVED)
    assert target.read_bytes() == data
    rows = ev.read_evidence(target)
    assert [r["item_id"] for r in rows] == ["ev-1", "ev-2", "ev-3"]
    assert {r["retrieved"] for r in rows} == {RETRIEVED}
    assert [r["path"] for r in rows] == [a.path for a in items]


def test_research_retrieved_reads_no_file_without_an_evidence_source(tmp_path: Path) -> None:
    assert ev.research_retrieved(tmp_path / "execution", ["identity", "financial"]) == {}


def test_research_retrieved_maps_each_item_to_its_time(
    tmp_path: Path, expected: dict[str, Any]
) -> None:
    (tmp_path / "research").mkdir()
    ev.write_evidence(tmp_path / "research" / "evidence.json", accepted(expected), RETRIEVED)
    got = ev.research_retrieved(tmp_path / "execution", ["identity", "ev-2"])
    assert got == dict.fromkeys(("ev-1", "ev-2", "ev-3"), RETRIEVED)


@pytest.mark.parametrize("body", [None, "not json", "{}", '[{"item_id": "ev-1"}]'])
def test_a_missing_or_malformed_record_is_refused_by_name(tmp_path: Path, body: str | None) -> None:
    (tmp_path / "research").mkdir()
    if body is not None:
        (tmp_path / "research" / "evidence.json").write_text(body, encoding="utf-8")
    with pytest.raises(ev.EvidenceRecordInvalid):
        ev.research_retrieved(tmp_path / "execution", ["ev-1"])


def test_the_record_is_json_with_the_documented_keys(
    tmp_path: Path, expected: dict[str, Any]
) -> None:
    data = ev.evidence_bytes(accepted(expected), RETRIEVED)
    assert set(json.loads(data)[0]) == {
        "item_id",
        "family",
        "published",
        "locator",
        "sha256",
        "retrieved",
        "path",
    }


def _row(item_id: str = "ev-1", **over: Any) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "family": "f",
        "published": None,
        "locator": "https://x.example/a",
        "sha256": "a" * 64,
        "retrieved": RETRIEVED,
        "path": "a.txt",
        **over,
    }


@pytest.mark.parametrize(
    "rows",
    [
        [_row(retrieved=None)],
        [_row(retrieved=123)],
        [_row(retrieved="")],
        [_row(retrieved="not-a-time")],
        [_row(retrieved="2026-11-02T05:40:00Z\n")],
        [_row(retrieved="2026-13-02T05:40:00Z")],
        [_row(retrieved="2026-11-02T05:40:00.5Z")],
        [_row(sha256=7)],
        [_row(locator=None)],
        [_row(published=5)],
        [_row("ev-1"), _row("ev-1", retrieved="1999-01-01T00:00:00Z")],
    ],
)
def test_read_back_validates_values_and_ids(tmp_path: Path, rows: list[dict[str, Any]]) -> None:
    """S1 fix 1, L-1 (p04): string values, a full UTC-second time, unique item ids."""
    (tmp_path / "research").mkdir()
    (tmp_path / "research" / "evidence.json").write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(ev.EvidenceRecordInvalid):
        ev.research_retrieved(tmp_path / "execution", ["ev-1"])
