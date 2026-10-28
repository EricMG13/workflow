"""The one blank-text predicate (LEAD round 12 B10): whitespace or Unicode format (`Cf`) only."""

import unicodedata

import pytest
from hypothesis import given
from hypothesis import strategies as st

from deploy_workflow.owners.blank import is_blank

ZWSP = "\u200b"  # ZERO WIDTH SPACE
BOM = "\ufeff"  # ZERO WIDTH NO-BREAK SPACE (byte order mark)
SOFT_HYPHEN = "\u00ad"
WORD_JOINER = "\u2060"


@pytest.mark.parametrize(
    "text",
    ["", " ", "   ", "\n", "\t ", "\u00a0", ZWSP, BOM, SOFT_HYPHEN, WORD_JOINER, f" {ZWSP}\n"],
)
def test_blank(text: str) -> None:
    assert is_blank(text)


@pytest.mark.parametrize("text", [f"a{ZWSP}", "a", f"{BOM}0", f" {SOFT_HYPHEN}-", "\u200c x"])
def test_not_blank(text: str) -> None:
    assert not is_blank(text)


def test_format_characters_are_not_stripped() -> None:
    """The class B10 closes: `str.strip()` keeps these characters, so `not x.strip()` misses
    them."""
    for ch in (ZWSP, BOM, SOFT_HYPHEN, WORD_JOINER):
        assert unicodedata.category(ch) == "Cf" and ch.strip() == ch
        assert is_blank(ch)


def test_empty_is_blank_as_strip_reads_it() -> None:
    assert is_blank("") == (not "".strip())


_BLANK_CHARS = st.sampled_from([" ", "\n", "\t", "\r", "\u00a0", "\u2009", ZWSP, BOM, SOFT_HYPHEN])


@given(st.text(), st.text())
def test_blank_concatenates(a: str, b: str) -> None:
    assert is_blank(a + b) == (is_blank(a) and is_blank(b))


@given(st.lists(_BLANK_CHARS))
def test_any_run_of_blank_characters_is_blank(chars: list[str]) -> None:
    assert is_blank("".join(chars))


@given(st.text(min_size=1))
def test_agrees_with_strip_on_text_without_format_characters(text: str) -> None:
    if not any(unicodedata.category(ch) == "Cf" for ch in text):
        assert is_blank(text) == (not text.strip())
