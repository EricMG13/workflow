"""O7b-1b Behaviour 7: research submission checks (expected.json#refusals/research, #cases)."""

import copy
from typing import Any

import pytest
from cpdr_o7b1b_support import brief, evidence, sources
from hypothesis import given
from hypothesis import strategies as st

from deploy_workflow.research import contracts as c
from deploy_workflow.research import review as r
from deploy_workflow.research import tables


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


def edit_answer(sub: dict[str, Any], qid: str, **fields: Any) -> dict[str, Any]:
    out = copy.deepcopy(sub)
    answer(out, qid).update(fields)
    return out


def texts(sub: dict[str, Any], manifest: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    return [i.text for i in check(sub, manifest, expected)]


def test_none_found_contrary_must_name_an_item_searched(
    submissions: dict[str, Any], manifest: dict[str, Any], expected: dict[str, Any]
) -> None:
    # Every none_found of the key's cases names its search (checked, not assumed).
    for name in ("research_v1", "research_v2"):
        for a in submissions[name]["answers"]:
            assert all(c["searched"] for c in a["contrary"] if c["kind"] == "none_found")
    empty = [{"kind": "none_found", "searched": [], "limitation": "Only supplied items."}]
    sub = edit_answer(submissions["research_v1"], "regulation", contrary=empty)
    assert texts(sub, manifest, expected) == ["a none_found contrary names the items searched"]


def test_none_found_search_must_name_held_items(
    submissions: dict[str, Any], manifest: dict[str, Any], expected: dict[str, Any]
) -> None:
    sub = copy.deepcopy(submissions["research_v1"])
    answer(sub, "regulation")["contrary"][0]["searched"] = ["ev-9"]
    assert texts(sub, manifest, expected) == ["searched item ev-9 is not a held source"]


def test_not_found_rules_each_refuse_alone(
    submissions: dict[str, Any], manifest: dict[str, Any], expected: dict[str, Any]
) -> None:
    base = submissions["research_v1"]
    claims = copy.deepcopy(answer(base, "ctx-1")["claims"])
    cases = {
        "a not_found question names the items searched": {"searched": []},
        "a not_found question carries no claim": {"claims": claims},
        "searched item ev-9 is not a held source": {"searched": ["ev-1", "ev-9"]},
    }
    for want, fields in cases.items():
        sub = edit_answer(base, "valuation-context", **fields)
        assert want in texts(sub, manifest, expected), want


def test_partly_needs_its_limitation(
    submissions: dict[str, Any], manifest: dict[str, Any], expected: dict[str, Any]
) -> None:
    sub = edit_answer(submissions["research_v2"], "valuation-context", limitation=None)
    assert texts(sub, manifest, expected) == ["a partly question states its limitation"]


def test_claim_needs_a_citation(
    submissions: dict[str, Any], manifest: dict[str, Any], expected: dict[str, Any]
) -> None:
    sub = copy.deepcopy(submissions["research_v1"])
    answer(sub, "regulation")["claims"][0]["citations"] = []
    assert texts(sub, manifest, expected) == ["claim regulation.c1 needs a citation"]


def test_cited_contrary_item_is_its_citation(
    submissions: dict[str, Any], manifest: dict[str, Any], expected: dict[str, Any]
) -> None:
    sub = copy.deepcopy(submissions["research_v1"])
    answer(sub, "market-demand")["contrary"][0]["item"] = "ev-1"
    assert texts(sub, manifest, expected) == ["contrary item ev-1 is not its citation"]


def test_independent_item_must_be_cited(
    submissions: dict[str, Any], manifest: dict[str, Any], expected: dict[str, Any]
) -> None:
    sub = copy.deepcopy(submissions["research_v1"])
    answer(sub, "competition")["claims"][0]["independent_items"] = ["ev-1", "ev-2"]
    answer(sub, "competition")["claims"][0]["citations"].pop()
    got = texts(sub, manifest, expected)
    assert "independent item ev-2 is not cited by competition.c1" in got


def test_independent_items_are_distinct_and_ev_only(
    submissions: dict[str, Any], manifest: dict[str, Any], expected: dict[str, Any]
) -> None:
    key = expected["refusals"]["research"]["families_not_independent"]["text"]
    sub = copy.deepcopy(submissions["research_v1"])
    claim = answer(sub, "competition")["claims"][0]
    claim["independent_items"] = ["ev-1", "ev-1"]
    got = texts(sub, manifest, expected)
    assert got == ["independent items of competition.c1 repeat an item"]
    assert not any("share family" in t or key in t for t in got)
    claim["independent_items"] = ["ev-1", "identity"]
    claim["citations"].append(
        {"source_id": "identity", "source_sha256": "a" * 64, "locator": "page:1", "quote": "x"}
    )
    got = texts(sub, manifest, expected)
    assert "independent item identity of competition.c1 is not an ev-* item" in got
    assert not any("share family" in t for t in got)


def test_claim_id_is_unique_across_the_submission(
    submissions: dict[str, Any], manifest: dict[str, Any], expected: dict[str, Any]
) -> None:
    sub = copy.deepcopy(submissions["research_v1"])
    answer(sub, "regulation")["claims"][0]["claim_id"] = "ctx-1.c1"
    assert [(i.question_id, i.text) for i in check(sub, manifest, expected)] == [
        ("regulation", "claim_id ctx-1.c1 appears twice")
    ]


def test_question_not_in_brief_and_repeated_answer(
    submissions: dict[str, Any], manifest: dict[str, Any], expected: dict[str, Any]
) -> None:
    sub = copy.deepcopy(submissions["research_v1"])
    answer(sub, "regulation")["question_id"] = "invented"
    got = texts(sub, manifest, expected)
    assert "question is not in the locked brief" in got
    again = copy.deepcopy(submissions["research_v1"])
    again["answers"].append(copy.deepcopy(answer(again, "ctx-1")))
    assert "question_id appears twice" in texts(again, manifest, expected)


def test_unanswered_brief_question_is_blocked(
    submissions: dict[str, Any], expected: dict[str, Any]
) -> None:
    sub = copy.deepcopy(submissions["research_v1"])
    sub["answers"] = sub["answers"][1:]
    states = r.claim_states(r.ResearchSubmission.parse(sub), brief(expected))
    assert states[0] == "blocked" and c.assign_readiness(states) == "BLOCKED"


def test_every_prose_field_is_held_to_the_language_rules(
    submissions: dict[str, Any], manifest: dict[str, Any], expected: dict[str, Any]
) -> None:
    word = expected["refusals"]["research"]["banned_word"]["refused_text"]
    base = submissions["research_v1"]

    def contrary_limitation(sub: dict[str, Any], text: str) -> None:
        answer(sub, "regulation")["contrary"][0]["limitation"] = text

    def cited_text(sub: dict[str, Any], text: str) -> None:
        answer(sub, "market-demand")["contrary"][0]["text"] = text

    def not_found_limitation(sub: dict[str, Any], text: str) -> None:
        answer(sub, "valuation-context")["limitation"] = text

    for edit in (contrary_limitation, cited_text, not_found_limitation):
        for bad, issue in ((word, word), ("About 12 of them.", r.FIGURE_ISSUE)):
            sub = copy.deepcopy(base)
            edit(sub, bad)
            want = "banned word: recommend" if bad == word else issue
            assert want in texts(sub, manifest, expected), (edit.__name__, bad)


def test_none_found_limitation_is_not_blank(
    submissions: dict[str, Any], manifest: dict[str, Any], expected: dict[str, Any]
) -> None:
    # O7-R23 (a): the same frame and refusal as a not_found question's blank limitation.
    for blank in (" ", "\n\t "):
        entry = [{"kind": "none_found", "searched": ["ev-1"], "limitation": blank}]
        sub = edit_answer(submissions["research_v1"], "regulation", contrary=entry)
        assert texts(sub, manifest, expected) == ["a none_found contrary states its limitation"]


def test_claim_id_bound_is_derived_from_the_tdr2_columns() -> None:
    assert r._TDR2_FIELDS == tables.TDR2_COLUMNS
    longest = "TDR.2." + "c" * r.CLAIM_ID_MAX + ".evidence_id"
    assert len(longest) == r.IDENTIFIER_MAX


def test_claim_id_at_the_bound_holds_and_one_past_is_a_research_issue(
    submissions: dict[str, Any], manifest: dict[str, Any], expected: dict[str, Any]
) -> None:
    sub = copy.deepcopy(submissions["research_v1"])
    claim = answer(sub, "competition")["claims"][0]
    claim["claim_id"] = "c" * r.CLAIM_ID_MAX
    assert texts(sub, manifest, expected) == []
    assert all(
        len(f"TDR.2.{claim['claim_id']}.{f}") <= r.IDENTIFIER_MAX for f in tables.TDR2_COLUMNS
    )
    claim["claim_id"] = "c" * (r.CLAIM_ID_MAX + 1)
    assert texts(sub, manifest, expected) == [
        f"claim_id {claim['claim_id']} is longer than {r.CLAIM_ID_MAX}"
    ]
    assert any(
        len(f"TDR.2.{claim['claim_id']}.{f}") > r.IDENTIFIER_MAX for f in tables.TDR2_COLUMNS
    )
