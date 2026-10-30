"""OI-14 (B6): CP-1 refuses a blank scope, source, entity or review limitation.

`Text` refuses only `""`; `validate_source_context` refuses a limitation that
`deploy_vii.prose.is_blank` calls blank (whitespace, U+200B, U+2800 and the like), once per
limitation, naming the record and never echoing the text. A non-blank or absent limitation is
unchanged, and no frozen CP-1 submission under `cases/` holds a blank limitation.
"""

import copy
import importlib
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from deploy_vii.prose import is_blank
from deploy_vii.source_context import SourceContextReview, validate_source_context

fw = importlib.import_module("test_financial_workflow")

pack = fw.make_pack()
CONTEXT = json.loads(fw.context(pack))
BLANKS = (" ", "\u200b", "\u2800")
FIELDS = ("scope", "source", "entity", "review")
ROOT = Path(__file__).resolve().parent.parent


def _issues(doc: dict[str, Any]) -> tuple[str, ...]:
    review = SourceContextReview.model_validate_json(json.dumps(doc))
    return validate_source_context(pack, review)


def _holder(doc: dict[str, Any], field: str) -> tuple[dict[str, Any], str]:
    """The record of `doc` that carries `field`'s limitations, and the issue a blank one gives."""
    if field == "scope":
        scope = doc["sources"][1]["scopes"][0]
        return scope, f"Empty limitation text: {scope['scope_id']}"
    if field == "source":
        return doc["sources"][1], "Empty limitation text: financial"
    if field == "entity":
        return doc["entities"][0], "Empty limitation text: issuer"
    return doc, "Empty limitation text: review"


def _with(field: str, limitations: list[str]) -> tuple[dict[str, Any], str]:
    doc = copy.deepcopy(CONTEXT)
    holder, expected = _holder(doc, field)
    holder["limitations"] = limitations
    return doc, expected


def test_fixture_is_valid() -> None:
    assert _issues(CONTEXT) == ()


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("blank", BLANKS)
def test_blank_limitation_is_one_issue(field: str, blank: str) -> None:
    doc, expected = _with(field, [blank])
    assert _issues(doc) == (expected,)


@pytest.mark.parametrize("field", FIELDS)
def test_each_blank_limitation_counts_once(field: str) -> None:
    doc, expected = _with(field, ["Figures are unaudited.", " ", "\u2800"])
    assert _issues(doc) == (expected, expected)


@pytest.mark.parametrize("field", FIELDS)
def test_non_blank_limitation_is_unchanged(field: str) -> None:
    doc, _ = _with(field, ["Figures are unaudited."])
    assert _issues(doc) == ()


def test_absent_limitation_is_unchanged() -> None:
    doc = copy.deepcopy(CONTEXT)
    del doc["limitations"]
    del doc["sources"][1]["limitations"]
    assert _issues(doc) == ()


def test_message_does_not_echo_the_input() -> None:
    doc, _ = _with("review", ["\u200b"])
    assert all("\u200b" not in issue for issue in _issues(doc))


@pytest.mark.parametrize("index", (0, 1))
@pytest.mark.parametrize("blank", BLANKS)
def test_blank_event_scan_explanation_is_one_issue(index: int, blank: str) -> None:
    """OI-20: source 0 is unassessed, source 1 is scanned; both refuse a blank explanation."""
    doc = copy.deepcopy(CONTEXT)
    source = doc["sources"][index]
    source["event_scan_explanation"] = blank
    assert _issues(doc) == (f"Empty event scan explanation: {source['source_id']}",)


@pytest.mark.parametrize("index", (0, 1))
def test_non_blank_event_scan_explanation_is_unchanged(index: int) -> None:
    doc = copy.deepcopy(CONTEXT)
    doc["sources"][index]["event_scan_explanation"] = "No events were scanned."
    assert _issues(doc) == ()


def test_event_scan_message_does_not_echo_the_input() -> None:
    doc = copy.deepcopy(CONTEXT)
    doc["sources"][0]["event_scan_explanation"] = "\u200b"
    assert all("\u200b" not in issue for issue in _issues(doc))


def _reviews(node: object) -> Iterator[dict[str, Any]]:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "cp1_source_context" and isinstance(value, dict):
                yield value
            else:
                yield from _reviews(value)
    elif isinstance(node, list):
        for value in node:
            yield from _reviews(value)


def _limitations(review: dict[str, Any]) -> Iterator[str]:
    yield from review.get("limitations", [])
    for entity in review.get("entities", []):
        yield from entity.get("limitations", [])
    for source in review.get("sources", []):
        yield from source.get("limitations", [])
        for scope in source.get("scopes", []):
            yield from scope.get("limitations", [])


def test_frozen_cp1_submissions_hold_no_blank_limitation() -> None:
    """Parity: with no blank limitation in any frozen submission, the new rule adds no issue."""
    seen = 0
    for path in sorted((ROOT / "cases").rglob("submissions.json")):
        for review in _reviews(json.loads(path.read_text())):
            seen += 1
            blanks = [text for text in _limitations(review) if is_blank(text)]
            assert blanks == [], path
            explanations = [s.get("event_scan_explanation", "x") for s in review["sources"]]
            assert not any(is_blank(text) for text in explanations), path
    assert seen > 0
