"""Phase 3 Task 2: the shared context-cite interface (`deploy_workflow.context_cites`).

The interface is fixed by ruling P3-P19 (`CITED_ARRAYS`, `STALE_DAYS`, `context_text`,
`value_offsets`, `cite`) and Phase 4 builds on it. The parity test ties it to the engine's own
`cp3_relative_value._value_offsets` (which cannot import this module): same offsets, same
locators and quotes over every context file of the case `cases/cp3-context-owner`.
"""

import inspect
import json
import re
from pathlib import Path
from typing import Any

import pytest

from deploy_vii import cp3_relative_value as engine
from deploy_vii.contracts import Source, Span
from deploy_vii.preparation import SourceRequest, prepare_source
from deploy_workflow import context as context_module
from deploy_workflow import context_cites as cites

ROOT = Path(__file__).parents[1]
CASE = ROOT / "cases/cp3-context-owner"
MAN: dict[str, Any] = json.loads((CASE / "manifest.json").read_text())
NAMES = [name for name in MAN["contexts"] if name != "bad-bytes"]


def source_of(name: str) -> Source:
    request = SourceRequest(
        source_id="context",
        path=f"cases/cp3-context-owner/contexts/{name}.json",
        media_type="text/plain",
    )
    return prepare_source(request, (CASE / "contexts" / f"{name}.json").read_bytes())


def raw_source(
    text: str, media_type: str | None = "text/plain", lines: list[str] | None = None
) -> Source:
    spans = lines if lines is not None else text.split("\n")
    return Source(
        source_id="context",
        name="context",
        status="ready",
        sha256="a" * 64,
        media_type=media_type,
        spans=tuple(Span(locator=f"line:{i}", text=t) for i, t in enumerate(spans, 1)),
        extraction_status="complete",
    )


def test_constants() -> None:
    assert cites.CITED_ARRAYS == ("quotes", "deal_terms")
    assert cites.STALE_DAYS == 30
    assert engine.STALE_DAYS == cites.STALE_DAYS
    assert engine.CONTEXT_NUM == context_module.NUM
    assert engine.UNREADABLE == cites.UNREADABLE


def test_context_text_joins_the_spans_with_newlines() -> None:
    source = source_of("observed-and-talk")
    assert cites.context_text(source) == "\n".join(span.text for span in source.spans)


def test_a_non_text_source_is_refused_before_any_span_is_indexed() -> None:
    source = raw_source('{"quotes": []}', media_type="application/pdf")
    with pytest.raises(
        cites.ContextTextError, match=r"^media type is application/pdf, not text/plain$"
    ):
        cites.context_text(source)
    with pytest.raises(cites.ContextTextError, match=r"^media type is None, not text/plain$"):
        cites.context_text(raw_source("{}", media_type=None))
    with pytest.raises(cites.ContextTextError):
        cites.cite(source, "quotes[0].bid")


def test_a_span_with_a_newline_is_refused() -> None:
    source = raw_source("", lines=['{"quotes": [', '{"bid": "1"}\n]}'])
    with pytest.raises(cites.ContextTextError, match=r"^a span holds more than one line$"):
        cites.context_text(source)
    with pytest.raises(cites.ContextTextError):
        cites.cite(source, "quotes[0].bid")


def test_value_offsets_by_array_index_and_field() -> None:
    text = '{"quotes": [{"bid": "1", "n": 2}, 5, {"ask": "3"}], "deal_terms": [{"as_of": ""}], "x": [{"bid": "9"}]}'
    found = cites.value_offsets(text)
    assert found == {
        "quotes[0].bid": text.index('"1"'),
        "quotes[2].ask": text.index('"3"'),
        "deal_terms[0].as_of": text.index('""'),
    }


@pytest.mark.parametrize(
    "text",
    ["", "[]", '{"quotes": [{"bid": "1"', '{"quotes": [{"bid" "1"}]}', '{"quotes": [{1: "a"}]}'],
)
def test_value_offsets_raises_value_error_on_unparsable_text(text: str) -> None:
    with pytest.raises(ValueError):
        cites.value_offsets(text)


def test_value_offsets_ignores_a_cited_name_that_is_not_an_array() -> None:
    assert cites.value_offsets('{"quotes": 3, "deal_terms": null}') == {}


def test_a_repeated_array_is_refused() -> None:
    with pytest.raises(cites.ContextTextError, match=r"^quotes appears more than once$"):
        cites.value_offsets('{"quotes": [{"bid": "1"}], "quotes": [{"bid": "2"}]}')


def test_a_repeated_member_is_refused() -> None:
    with pytest.raises(cites.ContextTextError, match=r"^duplicate member quotes\[0\]\.bid$"):
        cites.value_offsets('{"quotes": [{"bid": "1", "bid": "2"}]}')


@pytest.mark.parametrize(
    "text",
    [
        '{"quotes": [{"bid": "1"}], }',
        '{"quotes": [{"bid": "1",}]}',
        '{"quotes": [{"bid": "1"},]}',
        '{"quotes": [{"bid": "1"}]} trailing',
        '{"quotes": [{"bid": "1"}]',
        "\ufeff{}",
    ],
)
def test_invalid_json_is_a_named_error_for_every_entry_point(text: str) -> None:
    with pytest.raises(json.JSONDecodeError):
        json.loads(text)
    with pytest.raises(cites.ContextTextError):
        cites.value_offsets(text)
    with pytest.raises(cites.ContextTextError):
        cites.cite(raw_source(text), "quotes[0].bid")


def test_a_leading_bom_reads_as_the_json_modules_own_wording() -> None:
    with pytest.raises(json.JSONDecodeError) as error:
        json.loads("\ufeff{}")
    want = f"not valid JSON ({error.value.msg} at line {error.value.lineno})"
    with pytest.raises(cites.ContextTextError) as ours:
        cites.context_text(raw_source("\ufeff{}"))
    assert str(ours.value) == want


def test_the_public_surface_is_the_ruled_one() -> None:
    public = {
        n
        for n, v in vars(cites).items()
        if not n.startswith("_")
        and not inspect.ismodule(v)
        and getattr(v, "__module__", cites.__name__) == cites.__name__
    }
    public |= {"CITED_ARRAYS", "STALE_DAYS", "UNREADABLE"}
    assert public == {
        "CITED_ARRAYS",
        "STALE_DAYS",
        "UNREADABLE",
        "ContextTextError",
        "context_text",
        "value_offsets",
        "cite",
        "cite_all",
    }


def test_cite_alone_on_its_line_cites_the_member() -> None:
    source = source_of("observed-and-talk")
    citation = cites.cite(source, "quotes[0].bid")
    assert citation is not None
    assert (citation.source_id, citation.source_sha256) == ("context", source.sha256)
    assert (citation.locator, citation.quote) == ("line:30", '"bid": "98.50"')
    ask = cites.cite(source, "quotes[0].ask")
    assert ask is not None and (ask.locator, ask.quote) == ("line:31", '"ask": "99.00"')


def test_cite_unknown_path_is_a_key_error() -> None:
    with pytest.raises(KeyError):
        cites.cite(source_of("observed-and-talk"), "quotes[7].bid")
    with pytest.raises(KeyError):
        cites.cite(source_of("observed-and-talk"), "quotes[0].nope")


def test_cite_minified_anchors_on_the_row_object() -> None:
    source = source_of("minified")
    citation = cites.cite(source, "quotes[0].bid")
    assert citation is not None and citation.locator == "line:1"
    assert citation.quote.startswith('{"facility_id":"term-loan","kind":"observed","bid"')
    assert citation.quote.endswith('"bid":"98.50"')


def test_cite_returns_none_when_the_anchor_is_not_unique() -> None:
    row = (
        '{"facility_id":"a","kind":"observed","bid":"5","ask":"5","price":"","as_of":"2026-01-01"}'
    )
    source = raw_source('{"quotes":[' + row + "," + row + "]}")
    assert cites.cite(source, "quotes[0].bid") is None  # both rows collide
    assert cites.cite(source, "quotes[1].bid") is None  # every colliding row is dropped
    twice = raw_source('{"quotes":[{"facility_id":"a","bid":"5","ask":"5"}]}')
    # the anchor holds the number twice: still one unique span (CP-3D's token rule refuses it)
    anchored = cites.cite(twice, "quotes[0].ask")
    assert anchored is not None and anchored.quote == '{"facility_id":"a","bid":"5","ask":"5"'
    bid = cites.cite(twice, "quotes[0].bid")
    assert bid is not None and bid.quote == '{"facility_id":"a","bid":"5"'


def test_cite_returns_none_for_an_escaped_figure() -> None:
    source = raw_source('{"quotes":[{"bid":"9\\u0038.50"}]}')
    assert cites.cite(source, "quotes[0].bid") is None


def test_cite_returns_none_without_a_source_hash() -> None:
    source = source_of("observed-and-talk")
    assert cites.cite(source.model_copy(update={"sha256": None}), "quotes[0].bid") is None


def test_cite_all_cites_every_path_or_none() -> None:
    source = source_of("observed-and-talk")
    both = cites.cite_all(source, ("quotes[0].bid", "quotes[0].ask"))
    assert both is not None and [c.quote for c in both] == ['"bid": "98.50"', '"ask": "99.00"']
    assert cites.cite_all(source.model_copy(update={"sha256": None}), ("quotes[0].bid",)) is None
    assert cites.cite_all(source, ()) == ()
    with pytest.raises(KeyError):
        cites.cite_all(source, ("quotes[0].bid", "quotes[9].bid"))


@pytest.mark.parametrize("name", NAMES)
def test_parity_with_the_engine_over_every_context_file(name: str) -> None:
    source = source_of(name)
    text = cites.context_text(source)
    ours = cites.value_offsets(text)
    theirs = engine._value_offsets(text)
    assert ours == theirs
    assert all(text[at] == '"' for at in ours.values())
    for path in ours:
        member = engine._members(text)[path]
        engine_cite = engine._cite(source, text, member)
        mine = cites.cite(source, path)
        raw_plain = "\\" not in text[member.value_start : member.value_end]
        expected = engine_cite if raw_plain else None
        assert (mine is None) == (expected is None), path
        if mine is not None and expected is not None:
            assert (mine.locator, mine.quote) == (expected.locator, expected.quote), path
            assert mine.locator == f"line:{text.count(chr(10), 0, ours[path]) + 1}"


def test_parity_files_cover_the_manifest() -> None:
    on_disk = sorted(re.sub(r"\.json$", "", p.name) for p in (CASE / "contexts").glob("*.json"))
    assert sorted([*NAMES, "bad-bytes"]) == on_disk
