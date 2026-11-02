"""O7b-1b Behaviour 7: research submission checks (expected.json#refusals/research, #cases)."""

import copy
from typing import Any

import pytest
from cpdr_o7b1b_support import brief, evidence, sources
from hypothesis import given
from hypothesis import strategies as st

from deploy_workflow.research import contracts as c
from deploy_workflow.research import review as r


def check(
    submission: dict[str, Any],
    manifest: dict[str, Any],
    expected: dict[str, Any],
    case: str = "positive",
) -> tuple[r.ReviewIssue, ...]:
    return r.research_issues(
        submission=r.ResearchSubmission.parse(submission),
        brief=brief(expected, case),
        evidence=evidence(expected),
        sources=sources(manifest),
    )


def answer(sub: dict[str, Any], qid: str) -> dict[str, Any]:
    found: dict[str, Any] = next(a for a in sub["answers"] if a["question_id"] == qid)
    return found


@pytest.mark.parametrize(("sub_key", "case"), [("research_v1", "positive"), ("research_v2", "v2")])
def test_frozen_submissions_hold_and_give_the_keyed_states(
    sub_key: str,
    case: str,
    manifest: dict[str, Any],
    submissions: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    key = expected["cases"][case]
    sub = submissions[sub_key]
    assert check(sub, manifest, expected, case) == ()
    parsed = r.ResearchSubmission.parse(sub)
    states = r.claim_states(parsed, brief(expected, case))
    assert list(states) == key["claim_state_list"]
    assert dict(zip(key["claim_states"], states, strict=True)) == key["claim_states"]
    assert c.assign_readiness(states) == key["readiness"]
    got = r.answer_counts(parsed)
    assert {k: str(v) for k, v in got.__dict__.items()} == key["counts"]


def test_not_found_is_missing_with_a_limitation_never_zero(
    submissions: dict[str, Any], expected: dict[str, Any], manifest: dict[str, Any]
) -> None:
    sub = copy.deepcopy(submissions["research_v1"])
    nf = answer(sub, "valuation-context")
    assert nf["answer_state"] == "not_found"
    assert r.question_state(r.Answer.model_validate(nf, strict=False)) == "missing"
    nf["limitation"] = None
    issues = check(sub, manifest, expected)
    assert [i.question_id for i in issues] == ["valuation-context"]
    assert "limitation" in issues[0].text


def test_families_not_independent_text_is_the_key(
    submissions: dict[str, Any], expected: dict[str, Any], manifest: dict[str, Any]
) -> None:
    key = expected["refusals"]["research"]["families_not_independent"]
    assert key["input"] == "submissions.json#refusal_inputs.independence"
    bad = submissions["refusal_inputs"]["independence"]
    issues = check(bad, manifest, expected)
    assert [i.text for i in issues] == [key["text"]]


def test_banned_word_refused_and_the_released_words_accepted(
    submissions: dict[str, Any], expected: dict[str, Any], manifest: dict[str, Any]
) -> None:
    key = expected["refusals"]["research"]["banned_word"]
    sub = copy.deepcopy(submissions["research_v1"])
    answer(sub, "market-demand")["uncertainty"] = key["accepted"]
    assert check(sub, manifest, expected) == ()
    answer(sub, "market-demand")["uncertainty"] = key["refused"]
    issues = check(sub, manifest, expected)
    assert [(i.question_id, i.text) for i in issues] == [("market-demand", key["refused_text"])]
    assert r.BANNED_WORDS == ("recommend",)


def test_the_digit_rule_stays(
    submissions: dict[str, Any], expected: dict[str, Any], manifest: dict[str, Any]
) -> None:
    sub = copy.deepcopy(submissions["research_v1"])
    answer(sub, "regulation")["uncertainty"] = "About 12 operators are reached."
    assert [i.text for i in check(sub, manifest, expected)] == [r.FIGURE_ISSUE]


def test_answered_claim_needs_contrary_and_uncertainty(
    submissions: dict[str, Any], expected: dict[str, Any], manifest: dict[str, Any]
) -> None:
    sub = copy.deepcopy(submissions["research_v1"])
    answer(sub, "regulation")["contrary"] = []
    answer(sub, "ctx-1")["uncertainty"] = None
    issues = check(sub, manifest, expected)
    assert {(i.question_id, "contrary" in i.text or "uncertainty" in i.text) for i in issues} == {
        ("regulation", True),
        ("ctx-1", True),
    }


def test_citations_must_resolve(
    submissions: dict[str, Any], expected: dict[str, Any], manifest: dict[str, Any]
) -> None:
    sub = copy.deepcopy(submissions["research_v1"])
    answer(sub, "ctx-1")["claims"][0]["citations"][0]["quote"] = "Not in the item at all."
    answer(sub, "ctx-2")["claims"][0]["citations"][0]["source_id"] = "ev-9"
    issues = check(sub, manifest, expected)
    assert sorted(i.question_id for i in issues) == ["ctx-1", "ctx-2"]
    assert all("mismatch" in i.text or "Unavailable" in i.text for i in issues)


def test_brief_coverage_is_checked(
    submissions: dict[str, Any], expected: dict[str, Any], manifest: dict[str, Any]
) -> None:
    sub = copy.deepcopy(submissions["research_v1"])
    sub["answers"] = sub["answers"][1:]
    assert [(i.question_id, i.text) for i in check(sub, manifest, expected)] == [
        ("ctx-1", "brief question has no answer")
    ]


STATES: tuple[c.ClaimState, ...] = ("supported", "contrary", "missing", "blocked")


def test_readiness_vectors_are_the_keys(expected: dict[str, Any]) -> None:
    for vector in expected["readiness"]["vectors"]:
        assert c.assign_readiness(vector["states"]) == vector["expected"], vector["name"]


@given(st.lists(st.sampled_from(STATES), max_size=8))
def test_readiness_property(states: list[c.ClaimState]) -> None:
    got = c.assign_readiness(states)
    assert got != "COMMITTEE_READY"
    if not states or "blocked" in states:
        assert got == "BLOCKED"
    elif "contrary" in states or "missing" in states:
        assert got == "RESEARCH_READY_WITH_LIMITATIONS"
    else:
        assert got == "RESEARCH_READY"
