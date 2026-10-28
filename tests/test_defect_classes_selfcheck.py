"""Self-check of the shared defect-class library (`tests/defect_classes.py`); no owner is used.

Each case is well-formed (its quote is on its page under `quotes.quoted`, ids are unique, a refused
case names an accepted twin with the same value), and each refused case really differs from that
twin under `quotes.quoted`: the twin's quote is not on the refused page, or the two values differ
once normalised. A refused case is also a trap: its value is a substring of its normalised quote,
so a plain substring check would accept it.
"""

from collections.abc import Sequence

import pytest
from defect_classes import (
    BLANK_CASES,
    BLANK_VALUES,
    FIGURE_CASES,
    FIGURES,
    LABEL_TEMPLATES,
    MINUS,
    NBSP,
    SOFT_HYPHEN,
    TEXT_CASES,
    BlankCase,
    QuoteCase,
    blank_failure,
    case,
    label_cases,
    quote_failure,
)

from deploy_vii.quotes import hyphen_wrapped, normalise, quoted

LABELLED = tuple(label_cases("bid", f) for f in FIGURES)
ALL: tuple[QuoteCase, ...] = (*FIGURE_CASES, *TEXT_CASES, *(c for g in LABELLED for c in g))
GROUPS: tuple[tuple[QuoteCase, ...], ...] = (FIGURE_CASES, TEXT_CASES, *LABELLED)
REFUSED = [c for c in ALL if not c.accepted]


def _group(c: QuoteCase) -> tuple[QuoteCase, ...]:
    return next(g for g in GROUPS if c in g)


def test_case_ids_are_unique() -> None:
    for group in GROUPS:
        ids = [c.case_id for c in group]
        assert len(ids) == len(set(ids)), ids


@pytest.mark.parametrize("c", ALL, ids=lambda c: c.case_id)
def test_case_is_well_formed(c: QuoteCase) -> None:
    assert c.page and c.quote and c.value and c.ruling
    assert quoted(c.quote, c.page), "the quote is on its page"
    assert (c.twin is None) == c.accepted, "a refused case, and only one, names a twin"
    assert c.kind == ("figure" if c in FIGURE_CASES else "text" if c in TEXT_CASES else "label")
    if c.kind != "text":
        assert any(ch.isdigit() for ch in c.value) and c.value == c.value.strip()


@pytest.mark.parametrize("c", REFUSED, ids=lambda c: c.case_id)
def test_refused_case_differs_from_its_accepted_twin(c: QuoteCase) -> None:
    assert c.twin is not None
    twin = case(c.twin, _group(c))
    assert twin.accepted and twin.twin is None and twin.kind == c.kind
    assert quoted(twin.quote, twin.page)
    same_page = quoted(twin.quote, c.page)
    same_value = quoted(twin.value, c.value) and quoted(c.value, twin.value)
    assert not (same_page and same_value), "refusing it would contradict its twin"


@pytest.mark.parametrize("c", REFUSED, ids=lambda c: c.case_id)
def test_refused_case_is_a_substring_trap(c: QuoteCase) -> None:
    assert quoted(c.value, c.quote)


def test_figure_twins_are_whole_unsigned_figures() -> None:
    for c in REFUSED:
        if c.kind == "figure":
            twin = case(str(c.twin), FIGURE_CASES)
            assert f" {twin.value} " in f" {normalise(twin.page)} "


def test_wrap_cases_follow_b3() -> None:
    split = case("wrap-split", TEXT_CASES)
    joined = case("wrap-joined", TEXT_CASES)
    assert hyphen_wrapped(split.quote) and "- " in normalise(split.value)
    assert not hyphen_wrapped(joined.quote) and "- " not in normalise(joined.value)
    assert split.page == joined.page and hyphen_wrapped(split.page)


def test_class_characters_are_present() -> None:
    by_defect = {d: [c for c in ALL if c.defect == d] for d in {c.defect for c in ALL}}
    assert all(SOFT_HYPHEN in c.page for c in by_defect["soft_hyphen"])
    assert all(NBSP in c.page for c in by_defect["nbsp"])
    assert all(any(ch in c.page for ch in "–—−") for c in by_defect["dashes"])
    assert {c.kind for c in by_defect["soft_hyphen"]} == {"figure", "label", "text"}
    assert {c.kind for c in by_defect["nbsp"]} == {"figure", "label", "text"}
    signs = {c.case_id for c in by_defect["signs"]}
    for f in FIGURES:
        assert {f"sign-{s}-{f}" for s in ("minus", "ascii", "en", "parens")} <= signs
        assert MINUS in case(f"sign-minus-{f}", FIGURE_CASES).page
    assert {"sign-1-december", "sign-2024-2025", "sign-95-96", "sign-s-350"} <= signs
    edges = {c.case_id for c in by_defect["edge_cut"] if not c.accepted}
    assert {"edge-prefix-25", "edge-10", "edge-minus-0.25"} <= edges
    assert {"edge-close-paren-25", "edge-open-paren-25"} <= edges


@pytest.mark.parametrize("label", ["bid", "offer", "spread", "balance of"])
@pytest.mark.parametrize("figure", FIGURES)
def test_label_cases_bind_the_label(label: str, figure: str) -> None:
    bound = label_cases(label, figure)
    assert len(bound) == len(LABEL_TEMPLATES)
    for c in bound:
        assert "{" not in c.page + c.quote + c.value and quoted(c.quote, c.page)
        assert label in normalise(c.page) and c.value == figure


def test_label_needs_two_letters_and_a_family_figure() -> None:
    with pytest.raises(ValueError):
        label_cases("x")
    with pytest.raises(ValueError):
        label_cases("bid", "0.25")


def test_blank_cases_are_whitespace_only() -> None:
    assert [c.value for c in BLANK_CASES] == list(BLANK_VALUES)
    for c in BLANK_CASES:
        assert not c.value.strip() and quoted(c.quote, c.page)


# --- the assertion helpers, against plain readers written here (no owner) ----------------------


def _naive(page: str, quote: str, value: str) -> Sequence[str]:
    """A raw substring reader: the defect class itself."""
    return () if quoted(quote, page) and value in quote else ("value does not occur in the quote",)


def _empty_frame(page: str, quote: str, value: str) -> Sequence[str]:
    return ("text: empty text",) if not value.strip() else ()


def test_quote_failure_reports_a_wrong_outcome() -> None:
    refusal = "value does not occur in the quote"
    trap = case("sign-ascii-25", FIGURE_CASES)
    message = quote_failure(trap, _naive, refusal)
    assert message is not None and message.startswith("sign-ascii-25: expected")
    assert quote_failure(case("genuine-25", FIGURE_CASES), _naive, refusal) is None
    shy = case("shy-name", TEXT_CASES)
    assert quote_failure(shy, _naive, refusal) == f"shy-name: expected accepted, got {[refusal]}"


def test_blank_failure_needs_the_frame() -> None:
    blank: BlankCase = BLANK_CASES[1]
    assert blank_failure(blank, _empty_frame, "text: empty text") is None
    message = blank_failure(blank, _naive, "text: empty text")
    assert message is not None and "expected 'text: empty text'" in message
