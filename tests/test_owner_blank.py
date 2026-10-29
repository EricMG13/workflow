"""The one blank-text predicate (LEAD round 12 B10, extended by round 13 addendum 3): whitespace,
controls, Unicode format characters and the other invisible code points only."""

import unicodedata

import pytest
from hypothesis import given
from hypothesis import strategies as st

from deploy_vii.contracts import Citation
from deploy_workflow.owners.blank import is_blank, one_per_page

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
    if not any(unicodedata.category(ch) in {"Cc", "Cf"} or ch in _BEYOND_CF for ch in text):
        assert is_blank(text) == (not text.strip())


# Stage 2 close release (round 13 addendum 3, B10 beyond Cf): Cc controls, the default-ignorable
# code points outside Cf, and U+2800 are blank too.
_BEYOND_CF = (
    ["\x00", "\x01", "\x07", "\x1b", "\x7f", "\x80", "\x9f"]
    + ["͏", "ᅟ", "ᅠ", "឴", "឵", "ㅤ", "ﾠ", "⠀"]
    + [chr(c) for c in range(0x180B, 0x1810)]
    + [chr(c) for c in range(0xFE00, 0xFE10)]
    + [chr(c) for c in range(0xE0100, 0xE01F0)]
)


@pytest.mark.parametrize("ch", _BEYOND_CF, ids=lambda ch: f"U+{ord(ch):04X}")
def test_blank_beyond_format_characters(ch: str) -> None:
    assert is_blank(ch)
    assert is_blank(f" {ch}{ZWSP}\n")


@pytest.mark.parametrize(
    "text",
    ["⠁", "ᅞ", "ᅡ", "᠊", "᠐", "﷿", "︐", "f", "\U000e01f0"],
)
def test_neighbours_of_the_extended_set_are_not_blank(text: str) -> None:
    """The extension is exact: the code point before or after each range stays visible."""
    assert not is_blank(text)
    assert not is_blank(f" {text}")


def test_one_visible_character_among_the_extended_set_is_not_blank() -> None:
    assert not is_blank("⠀a\x00")


def test_one_per_page_keeps_the_first_quote_of_each_source_page_in_input_order() -> None:
    first = Citation(source_id="bridge", source_sha256="a" * 64, locator="page:1", quote="first")
    again = first.model_copy(update={"quote": "second"})
    other_page = first.model_copy(update={"locator": "page:2", "quote": "other"})
    other_source = first.model_copy(update={"source_id": "plan", "quote": "plan"})
    assert one_per_page([first, other_page, again, other_source]) == (
        first,
        other_page,
        other_source,
    )
    assert one_per_page(()) == ()
