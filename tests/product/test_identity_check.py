"""Borrower-name check against the frozen oracle ``cases/context-identity-periods``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from deploy_workflow.context import RunContext, load_context
from deploy_workflow.identity_check import compare

ROOT = Path(__file__).resolve().parents[2] / "cases" / "context-identity-periods"
ORACLE = json.loads((ROOT / "expected.json").read_text(encoding="utf-8"))["identity_check"]
CASES = ORACLE["cases"]
BORROWER = ("Northbridge Holdings LLC", ("borrower",))


def _ctx(name: str) -> RunContext:
    return load_context((ROOT / "contexts" / f"{name}.json").read_bytes())


def _expect(key: str, name: str, entities: list[tuple[str, tuple[str, ...]]]) -> None:
    got = compare(_ctx(name), entities)
    want = CASES[key]
    assert (got.outcome, list(got.gaps), list(got.found)) == (
        want["outcome"],
        want["gaps"],
        want["found"],
    )


def test_match() -> None:
    _expect("ctx-b-match@B", "ctx-b-match", [BORROWER])


def test_punctuation_matches() -> None:
    _expect("ctx-b-punct@B", "ctx-b-punct", [BORROWER])


def test_mismatch_gap_text_and_found() -> None:
    _expect("ctx-b-mismatch@B", "ctx-b-mismatch", [BORROWER])
    assert len(compare(_ctx("ctx-b-mismatch"), [BORROWER]).gaps) == 1


def test_empty_borrower_name_is_not_supplied_but_lists_found() -> None:
    _expect("ctx-research@B", "ctx-research", [BORROWER])
    empty = compare(_ctx("ctx-research"), [BORROWER])
    assert (empty.outcome, list(empty.gaps)) == (
        ORACLE["empty_borrower_name"]["outcome"],
        ORACLE["empty_borrower_name"]["gaps"],
    )


@pytest.mark.parametrize("name", ["   ", " . ", "-,", "\t"])
def test_name_that_folds_to_nothing_is_not_supplied(name: str) -> None:
    ctx = _ctx("ctx-b-match")
    blank = ctx.model_copy(
        update={"identity": ctx.identity.model_copy(update={"borrower_name": name})}
    )
    got = compare(blank, [BORROWER])
    assert (got.outcome, list(got.gaps)) == (
        ORACLE["empty_borrower_name"]["outcome"],
        ORACLE["empty_borrower_name"]["gaps"],
    )
    assert list(got.found) == CASES["ctx-b-match@B"]["found"]


def test_no_borrower_role_row_is_not_supplied() -> None:
    _expect("ctx-match@E", "ctx-match", [("Acme plc", ("issuer",))])


def test_two_scope_rows_of_one_entity_are_listed_once() -> None:
    got = compare(_ctx("ctx-b-match"), [BORROWER, BORROWER])
    assert got.found == tuple(CASES["ctx-b-match@B"]["found"])


def test_joined_role_string_is_split() -> None:
    got = compare(_ctx("ctx-b-match"), [("Northbridge Holdings LLC", ("issuer; borrower",))])
    assert got.outcome == "match"


def test_context_borrower_is_reported() -> None:
    assert compare(_ctx("ctx-b-mismatch"), [BORROWER]).context_borrower == (
        "Southbridge Holdings LLC"
    )


@settings(max_examples=60)
@given(
    st.lists(
        st.tuples(st.booleans(), st.sampled_from(["", " ", ".", ",", "-"])),
        min_size=len("Northbridge Holdings LLC"),
        max_size=len("Northbridge Holdings LLC"),
    )
)
def test_invariant_under_case_and_punctuation(noise: list[tuple[bool, str]]) -> None:
    name = "".join(
        (c.upper() if up else c.lower()) + sep
        for c, (up, sep) in zip("Northbridge Holdings LLC".replace(" ", ""), noise, strict=False)
    )
    ctx = _ctx("ctx-b-match")
    varied = ctx.model_copy(
        update={"identity": ctx.identity.model_copy(update={"borrower_name": name})}
    )
    assert compare(varied, [BORROWER]).outcome == "match"
