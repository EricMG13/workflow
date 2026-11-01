"""Tests for the stdlib HTML to line converter (O2 Task 1, R1)."""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from deploy_workflow import html_text
from deploy_workflow.html_text import UndecodableHtml, convert_html

REPO = Path(__file__).resolve().parents[1]
CORPUS = Path("/Users/ericguei/Documents/Deploy Workflow/artifacts/public-corpus/v1")
# Quotes not inside one line for the chosen rule (no div), measured in the task-1 note.
RECORDED_MISSES = 83


def _check_py() -> Any:
    spec = importlib.util.spec_from_file_location("golden_check", REPO / "cases/goldens/check.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _text(html: str) -> str:
    return convert_html(html.encode("utf-8")).text


def test_table_rows_are_lines() -> None:
    html = (
        "<html><body><table><tr><td>Revenue</td><td>1,234</td></tr>"
        "<tr><td>Cost</td><td>(5)</td></tr></table></body></html>"
    )
    assert _text(html) == "Revenue 1,234\nCost (5)\n"


def test_inline_spans_do_not_split_a_number() -> None:
    html = "<p><span>(</span>1,234<span>)</span></p>"
    assert _text(html) == "(1,234)\n"


def test_skipped_and_hidden_elements_dropped() -> None:
    html = (
        "<head><title>T</title></head><body>x<script>y</script><style>z</style>"
        '<div style="display: none">h</div>w</body>'
    )
    assert _text(html) == "x w\n"


def test_ix_header_dropped() -> None:
    assert _text("<ix:header>H</ix:header><p>A</p><p>B</p>") == "A\nB\n"


def test_unclosed_head_ends_at_body() -> None:
    assert _text("<head><title>T</title><body><p>A</p></body>") == "A\n"


def test_empty_paragraphs_dropped() -> None:
    assert _text("<p>A</p><p>  \u200b </p><p>B</p>") == "A\nB\n"


def test_no_visible_text_is_empty_string() -> None:
    assert _text("<html><head><title>T</title></head><body></body></html>") == ""


def test_characters_that_split_lines_are_normalised() -> None:
    result = convert_html("<p>a b\x0bc\x85d</p>".encode()).text
    assert result == "a b c d\n"
    assert len(result.splitlines()) == 1


def test_entities_unescaped() -> None:
    assert _text("<p>A &amp; B&nbsp;C</p>") == "A & B C\n"


def test_line_count_matches_text() -> None:
    converted = convert_html(b"<p>A</p><p>B</p><p>C</p>")
    assert converted.line_count == 3
    assert converted.encoding == "utf-8"


def test_utf8_and_bom() -> None:
    assert convert_html("<p>café</p>".encode()).text == "café\n"
    bom = convert_html(b"\xef\xbb\xbf<p>x</p>")
    assert bom.text == "x\n"
    assert bom.encoding == "utf-8-sig"


def test_declared_windows_1252() -> None:
    converted = convert_html(b'<meta charset="windows-1252"><p>caf\xe9</p>')
    assert converted.text == "café\n"
    assert converted.encoding == "windows-1252"


def test_declared_via_xml_declaration() -> None:
    converted = convert_html(b'<?xml version="1.0" encoding="iso-8859-1"?><p>caf\xe9</p>')
    assert converted.text == "café\n"
    assert converted.encoding == "iso-8859-1"


def test_undeclared_invalid_utf8_refused() -> None:
    with pytest.raises(UndecodableHtml):
        convert_html(b"<p>caf\xe9</p>")


def test_other_declared_charset_refused() -> None:
    with pytest.raises(UndecodableHtml):
        convert_html(b'<meta charset="shift_jis"><p>\x82\xa0</p>')


def test_unknown_charset_name_refused() -> None:
    with pytest.raises(UndecodableHtml):
        convert_html(b'<meta charset="no-such-codec"><p>x\xe9</p>')


def test_declared_charset_that_does_not_decode_refused() -> None:
    with pytest.raises(UndecodableHtml):
        convert_html(b'<meta charset="ascii"><p>caf\xe9</p>')


def test_nul_refused() -> None:
    with pytest.raises(UndecodableHtml):
        convert_html(b"<p>a\x00b</p>")


def test_constants_match_check_py() -> None:
    check = _check_py()
    assert html_text.VOID == check.VOID
    assert html_text.SKIP == check.SKIP
    assert html_text.BLOCK == check.BLOCK
    assert html_text.ZERO_WIDTH_CHARS == "\u200b‌‍⁠﻿"
    assert html_text.LINE_TAGS <= check.BLOCK


FIXTURES = [
    "<table><tr><td>Revenue</td><td>1,234</td></tr><tr><td>Cost</td><td>(5)</td></tr></table>",
    "<p><span>(</span>1,234<span>)</span></p>",
    (
        "<head><title>T</title></head><body>x<script>y</script><style>z</style>"
        '<div style="display: none">h</div>w</body>'
    ),
    "<ix:header>H</ix:header><p>A</p><p>B</p>",
    "<p>A</p><p>  \u200b </p><p>B</p>",
    "<p>a b\x0bc\x85d</p><br/><ul><li>one</li><li>two &amp; three</li></ul>",
]


@pytest.mark.parametrize("html", FIXTURES)
def test_equivalent_to_check_py_visible_text(html: str) -> None:
    check = _check_py()
    lines = _text(html).splitlines()
    assert check.normalise(" ".join(lines)) == check.visible_text(html)


_TAGS = st.sampled_from(["p", "div", "tr", "td", "span", "table", "li", "br", "b", "script"])
_TEXT = st.text(alphabet=st.sampled_from(list("ab 1(),\n\t\x0b\x85\u200b  ")), max_size=8)


@st.composite
def _html(draw: st.DrawFn, depth: int = 0) -> str:
    parts: list[str] = []
    for _ in range(draw(st.integers(0, 4))):
        if depth < 3 and draw(st.booleans()):
            tag = draw(_TAGS)
            parts.append(f"<{tag}>{draw(_html(depth + 1))}</{tag}>")
        else:
            parts.append(draw(_TEXT))
    return "".join(parts)


@settings(max_examples=200, deadline=None)
@given(_html())
def test_no_hidden_splits_and_clean_lines(html: str) -> None:
    text = _text(html)
    lines = text.splitlines()
    assert lines == (text.split("\n")[:-1] if text else [])
    assert all(line and line == line.strip() for line in lines)


def test_corpus_goldens_decode_and_recorded_misses() -> None:
    if not CORPUS.is_dir():
        pytest.skip("public corpus directory absent (artifacts/public-corpus/v1)")
    check = _check_py()
    total = 0
    misses = 0
    for case in sorted((REPO / "cases/goldens").iterdir()):
        golden = case / "module_golden.json"
        if not golden.is_file():
            continue
        data = json.loads(golden.read_text())
        converted: dict[str, list[str]] = {}
        for source in data["sources"]:
            path = CORPUS / source["file"]
            if path.suffix.lower() == ".pdf" or not path.is_file():
                continue
            if path.suffix.lower() not in {".htm", ".html"}:
                continue
            converted[source["source_id"]] = convert_html(path.read_bytes()).text.splitlines()
        for fact in data["facts"]:
            for evidence in fact["evidence"]:
                lines = converted.get(evidence["source_id"])
                if lines is None:
                    continue
                total += 1
                quote = check.normalise(evidence["quote"])
                if not any(quote in line for line in lines):
                    misses += 1
    assert total > 0
    assert misses == RECORDED_MISSES


def test_div_is_a_space_not_a_line_break() -> None:
    assert _text("<div>A</div><div>B</div>") == "A B\n"


def test_void_tag_is_not_pushed_so_it_cannot_hide_text() -> None:
    assert _text('<p>a<img style="display:none">b</p>') == "ab\n"


def test_self_closing_br_breaks_a_line() -> None:
    assert _text("a<br/>b") == "a\nb\n"


def test_text_after_a_closed_paragraph_is_its_own_line() -> None:
    assert _text("<p>A</p>B") == "A\nB\n"


def test_charset_sniff_stops_at_4096_bytes() -> None:
    inside = b"<!--" + b"x" * 4000 + b'--><meta charset="windows-1252"><p>caf\xe9</p>'
    assert len(inside.split(b"<meta")[0]) < 4096
    assert convert_html(inside).encoding == "windows-1252"
    outside = b"<!--" + b"x" * 4100 + b'--><meta charset="windows-1252"><p>caf\xe9</p>'
    with pytest.raises(UndecodableHtml):
        convert_html(outside)


def _best_time(count: int) -> float:
    raw = b"<p>Revenue <b>1,234</b> rose" * count
    best = float("inf")
    for _ in range(3):
        started = time.monotonic()
        converted = convert_html(raw)
        best = min(best, time.monotonic() - started)
        assert converted.line_count == count
    return best


def test_many_unclosed_paragraphs_convert_in_linear_time() -> None:
    # Doubling the input must not much more than double the time (quadratic would be about 4x).
    assert _best_time(40000) / _best_time(20000) < 3


def test_mismatched_end_tag_pops_to_the_match_not_just_the_top() -> None:
    # Pins the stack semantics: the end tag closes everything above its match (pop-top-only
    # and count=1 mutants of handle_endtag leave the hidden div open and swallow the x).
    assert _text('<div style="display:none"><span>h</div>x') == "x\n"
    assert _text('<div style="display:none"><div>h</div></div>x') == "x\n"
