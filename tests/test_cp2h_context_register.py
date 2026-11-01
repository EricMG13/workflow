"""Phase 4 Task 2: CP-2H's register from the context file's ratings on a fixed combined scale.

Every expected value comes from the frozen oracle `cases/cp2h-context-owner` (manifest scale table,
`expected.json` refusals and possessive pins); the terms pages are its `ratings_sources`.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from deploy_workflow.context import Rating
from deploy_workflow.owners import cp2h

CASE = Path(__file__).parents[1] / "cases/cp2h-context-owner"
MAN: dict[str, Any] = json.loads((CASE / "manifest.json").read_text())
EXP: dict[str, Any] = json.loads((CASE / "expected.json").read_text())
SCALE: dict[str, dict[str, int]] = MAN["combined_scale"]["by_agency"]
SP_SYMBOLS = list(SCALE["S&P"])


def _context(name: str) -> list[Rating]:
    rows = json.loads((CASE / name).read_text())["ratings"]
    return [Rating.model_validate(r) for r in rows]


def _rating(agency: str, rating: str, outlook: str = "Stable", as_of: str = "2025-10-02") -> Rating:
    return Rating(agency=agency, scope="issuer", rating=rating, outlook=outlook, as_of=as_of)


def _terms(variant: str) -> list[str]:
    return [p["text"] for p in MAN["ratings_sources"][variant]["pages"]]


def _refusal(case: str) -> str:
    return str(next(r for r in EXP["refusals"] if r["id"] == case)["expected_issues"][0])


def test_positive_positions() -> None:
    register = cp2h.context_register(_context("context-positive.json"))
    assert [(r.agency, r.rating, r.position) for r in register] == [
        ("S&P", "BB", 12),
        ("Moody's", "Ba3", 13),
    ]
    assert all(r.source == "context" and r.scale_line is None for r in register)
    assert [r.line for r in register] == ["0", "1"]


def test_withdrawn_has_no_position() -> None:
    register = cp2h.context_register([_rating("S&P", "BB"), _rating("Moody's", "Withdrawn")])
    assert [r.position for r in register] == [12, None]


def test_not_stated_values() -> None:
    (row,) = cp2h.context_register([_rating("S&P", "BB", outlook="", as_of="")])
    assert (row.instrument, row.outlook, row.date) == ("Not stated",) * 3
    full = cp2h.context_register(_context("context-positive.json"))[0]
    assert (full.instrument, full.outlook, full.date) == ("Not stated", "Negative", "2025-11-14")


def test_outlook_unstated_case_reads_not_stated() -> None:
    register = cp2h.context_register(_context("context-outlook-unstated.json"))
    assert "Not stated" in {r.outlook for r in register}


def test_scale_table_matches_oracle() -> None:
    assert {a: dict(t) for a, t in cp2h.COMBINED_SCALE.items()} == SCALE
    rows = MAN["combined_scale"]["rows"]
    key = {"S&P": "sp", "Moody's": "moodys", "Fitch": "fitch"}
    for agency, column in key.items():
        assert cp2h.COMBINED_SCALE[agency] == {
            r[column]: r["position"] for r in rows if r[column] is not None
        }


def test_off_scale_refused() -> None:
    with pytest.raises(cp2h.SourceIssue) as raised:
        cp2h.context_register(_context("context-off-scale.json"))
    assert str(raised.value) == _refusal("off_scale") == "Rating not on the scale: Other A"


def test_rating_off_the_agencys_scale_refused() -> None:
    with pytest.raises(cp2h.SourceIssue, match="Rating not on the scale: Moody's BB"):
        cp2h.context_register([_rating("Moody's", "BB")])


def test_agency_without_scale_refused_even_when_unrated() -> None:
    with pytest.raises(cp2h.SourceIssue) as raised:
        cp2h.context_register([_rating("Other", "Withdrawn")])
    assert str(raised.value) == "Rating not on the scale: Other Withdrawn"


def test_duplicate_agency_refused() -> None:
    with pytest.raises(cp2h.SourceIssue) as raised:
        cp2h.context_register(_context("context-duplicate-agency.json"))
    assert str(raised.value) == _refusal("duplicate_agency") == cp2h.REGISTER_NOT_FOUND


def test_duplicate_is_refused_before_off_scale() -> None:
    rows = [_rating("Other", "A"), _rating("S&P", "BB"), _rating("S&P", "BB-")]
    with pytest.raises(cp2h.SourceIssue) as raised:
        cp2h.context_register(rows)
    assert str(raised.value) == cp2h.REGISTER_NOT_FOUND


def test_empty_ratings_refused() -> None:
    with pytest.raises(cp2h.SourceIssue) as raised:
        cp2h.context_register([])
    assert str(raised.value) == _refusal("no_ratings") == cp2h.REGISTER_NOT_FOUND


def test_terms_read_beside_the_context_register() -> None:
    register = cp2h.context_register(_context("context-positive.json"))
    source = cp2h.context_ratings(register, _terms("positive"))
    assert source.register == register
    assert len(source.triggers) == 5
    assert source.register_published == cp2h.PUBLICATION_NOT_STATED
    assert source.terms_published == "2026-01-10"


@pytest.mark.parametrize(
    "pages",
    [
        [],
        ["a", "b"],
        ["a", "b", "no header here"],
        ["a", "b", f"{cp2h.TERMS_HEADER}"],
    ],
)
def test_terms_missing_refused(pages: list[str]) -> None:
    register = cp2h.context_register(_context("context-positive.json"))
    with pytest.raises(cp2h.SourceIssue) as raised:
        cp2h.context_ratings(register, pages)
    assert str(raised.value) == _refusal("no_terms") == cp2h.TERMS_NOT_FOUND


def test_terms_agency_unrated_refused() -> None:
    register = cp2h.context_register(_context("context-terms-agency-unrated.json"))
    with pytest.raises(cp2h.SourceIssue) as raised:
        cp2h.context_ratings(register, _terms("fitch_terms"))
    assert str(raised.value) == _refusal("terms_agency_unrated")


def test_terms_agency_withdrawn_refused() -> None:
    register = cp2h.context_register([_rating("S&P", "BB"), _rating("Moody's", "Withdrawn")])
    with pytest.raises(cp2h.SourceIssue, match=cp2h.TERMS_NOT_FOUND):
        cp2h.context_ratings(register, _terms("positive"))


def test_possessive() -> None:
    pins = EXP["possessive"]
    assert cp2h.possessive("S&P") == pins["S&P"] == "S&P's"
    assert cp2h.possessive("Moody's") == pins["Moody's"] == "Moody's"
    assert cp2h.possessive("Fitch") == "Fitch's"


@given(a=st.sampled_from(SP_SYMBOLS), b=st.sampled_from(SP_SYMBOLS))
def test_notches_equal_the_index_distance(a: str, b: str) -> None:
    pos = cp2h.COMBINED_SCALE["S&P"]
    assert abs(pos[a] - pos[b]) == abs(SP_SYMBOLS.index(a) - SP_SYMBOLS.index(b))
    first, second = (
        cp2h.context_register([_rating("S&P", a)])[0],
        cp2h.context_register([_rating("S&P", b)])[0],
    )
    assert first.position is not None and second.position is not None
    assert abs(first.position - second.position) == abs(SP_SYMBOLS.index(a) - SP_SYMBOLS.index(b))


def test_context_row_fails_closed_in_the_cell_builder() -> None:
    # Task 3 replaces this error with the real per-row citations and flips this test.
    register = cp2h.context_register(_context("context-positive.json"))
    source = cp2h.context_ratings(register, _terms("positive"))
    with pytest.raises(cp2h.ContextCitationsNotWired, match="register_source"):
        cp2h._agency_register(cp2h._Book("0" * 64), source)
