"""O7b-1c S2a': the brief step and research step logic (expected.json#brief, submissions.json)."""

import copy
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from deploy_vii.contracts import Input
from deploy_vii.live.tools import UNBACKED_ABSENCE, Seen
from deploy_workflow.research import brief as b
from deploy_workflow.research import contracts as c
from deploy_workflow.research import steps as s
from deploy_workflow.research.review import BANNED_WORDS, FIGURE_ISSUE

ANCHOR = c.Anchor(cp0_sha256="a" * 64, cp1_sha256="b" * 64)
DEFAULTS_ONLY = "model_tailored_defaults_only"


def submission(submissions: dict[str, Any], key: str = "model_tailored") -> s.BriefSubmission:
    rows = submissions["brief"][key]
    return s.BriefSubmission.parse({"run_id": "run-1", "questions": rows})


def edited(submissions: dict[str, Any], rows: list[dict[str, Any]]) -> s.BriefSubmission:
    return s.BriefSubmission.parse({"run_id": "run-1", "questions": rows})


def lock(tmp_path: Path, manifest: dict[str, Any], sub: s.BriefSubmission) -> c.ResearchBrief:
    return b.lock_brief(
        issuer_id=manifest["run"]["issuer_id"],
        run_id=manifest["run"]["run_id"],
        as_of=date(2026, 1, 10),
        cutoff=date(2026, 1, 10),
        context_questions=[
            (q["text"], q["focus_module"]) for q in manifest["context"]["research_questions"]
        ],
        tailored=s.tailored_of(sub),
        anchor=ANCHOR,
        path=tmp_path / "research" / "brief.json",
    )


def test_forty_tailored_lock_to_the_keyed_thirty_two(
    tmp_path: Path, manifest: dict[str, Any], submissions: dict[str, Any], expected: dict[str, Any]
) -> None:
    key = expected["brief"]["lock"]
    sub = submission(submissions)
    assert s.brief_issues(sub) == ()
    brief = lock(tmp_path, manifest, sub)
    ids = [q.question_id for q in brief.questions]
    assert ids == key["locked_ids"]
    assert not set(key["dropped_from_tail"]) & set(ids)
    assert [i for i in ids if i.startswith(b.CONTEXT_PREFIX)] == key["context_kept"]
    submitted = [q.question_id for q in sub.questions]
    assert [i for i in submitted if i not in ids] == key["dropped_from_tail"]
    kept_tailored = [i for i in ids if not i.startswith(b.CONTEXT_PREFIX)]
    assert len(kept_tailored) + len(manifest["context"]["research_questions"]) == key["locked_out"]
    assert len(submitted) + len(manifest["context"]["research_questions"]) == key["tailored_in"]
    assert ids[: len(key["context_kept"])] == key["context_kept"]


def test_defaults_only_lock_gives_the_keyed_brief(
    tmp_path: Path, manifest: dict[str, Any], submissions: dict[str, Any], expected: dict[str, Any]
) -> None:
    key = expected["brief"]
    sub = submission(submissions, DEFAULTS_ONLY)
    assert s.brief_issues(sub) == ()
    brief = lock(tmp_path, manifest, sub)
    assert [q.question_id for q in brief.questions] == key["question_ids"]
    assert [q.kind for q in brief.questions] == key["kinds"]
    assert {q.question_id: list(q.receivers) for q in brief.questions} == key["receivers"]
    assert {q.question_id: q.focus_module for q in brief.questions} == key["focus_modules"]


def test_default_constants_equal_the_key(expected: dict[str, Any]) -> None:
    key = expected["brief"]
    assert [d.question_id for d in s.DEFAULT_QUESTIONS] == key["question_ids"][2:]
    assert [d.kind for d in s.DEFAULT_QUESTIONS] == key["kinds"][2:]


def rows(submissions: dict[str, Any], key: str = DEFAULTS_ONLY) -> list[dict[str, Any]]:
    return copy.deepcopy(submissions["brief"][key])


def test_a_missing_default_is_an_issue(submissions: dict[str, Any]) -> None:
    body = rows(submissions)
    del body[2]
    assert s.brief_issues(edited(submissions, body)) == (
        "default question valuation-context is missing",
    )


def test_a_default_twice_is_an_issue(submissions: dict[str, Any]) -> None:
    body = rows(submissions)
    body.append(copy.deepcopy(body[0]))
    assert s.brief_issues(edited(submissions, body)) == (
        "default question competition appears 2 times",
    )


def test_defaults_out_of_order_are_an_issue(submissions: dict[str, Any]) -> None:
    body = rows(submissions)
    body[0], body[1] = body[1], body[0]
    assert s.brief_issues(edited(submissions, body)) == (
        "the six default questions come first, in their fixed order",
    )


def test_a_custom_before_a_default_is_an_issue(submissions: dict[str, Any]) -> None:
    body = rows(submissions, "model_tailored")
    body.insert(0, body.pop(6))
    assert s.brief_issues(edited(submissions, body)) == (
        "the six default questions come first, in their fixed order",
    )


@pytest.mark.parametrize("bad", ["Revenue fell 12 percent.", "Q3 outlook?"])
def test_a_tailored_text_with_a_digit_is_an_issue(submissions: dict[str, Any], bad: str) -> None:
    body = rows(submissions)
    body.append({"question_id": "custom-01", "text": bad, "kind": "custom"})
    assert s.brief_issues(edited(submissions, body)) == (f"custom-01: {FIGURE_ISSUE}",)


def test_a_tailored_text_with_a_banned_word_is_an_issue(submissions: dict[str, Any]) -> None:
    assert BANNED_WORDS == ("recommend",)
    body = rows(submissions)
    body[0]["text"] = "Which producers do you Recommend?"
    assert s.brief_issues(edited(submissions, body)) == ("competition: banned word: recommend",)


def test_id_and_kind_rules(submissions: dict[str, Any]) -> None:
    body = rows(submissions)
    body.append({"question_id": "ctx-9", "text": "A context lookalike.", "kind": "custom"})
    body.append({"question_id": "custom-01", "text": "One.", "kind": "context"})
    body.append({"question_id": "custom-01", "text": "Again.", "kind": "custom"})
    body.append({"question_id": "x" * (s.QUESTION_ID_MAX + 1), "text": "Long.", "kind": "custom"})
    body[1]["kind"] = "custom"
    got = s.brief_issues(edited(submissions, body))
    assert got == (
        "metric-definitions: a default question carries its own kind default_2",
        "ctx-9: a tailored question id cannot start with ctx-",
        "custom-01: a tailored question is kind custom",
        "custom-01: question_id appears twice",
        f"{'x' * (s.QUESTION_ID_MAX + 1)}: question_id is longer than {s.QUESTION_ID_MAX}",
    )


def test_the_id_bound_keeps_every_derived_fact_id_inside_identifier() -> None:
    longest = "TDR.3." + "x" * s.QUESTION_ID_MAX + ".questions_total"
    assert len(longest) == 160


def test_the_frozen_defaults_only_submission_has_no_issue(submissions: dict[str, Any]) -> None:
    assert s.brief_issues(submission(submissions, DEFAULTS_ONLY)) == ()


def test_an_id_of_exactly_the_bound_is_accepted(submissions: dict[str, Any]) -> None:
    body = rows(submissions)
    body.append({"question_id": "q" * s.QUESTION_ID_MAX, "text": "Fits.", "kind": "custom"})
    assert s.brief_issues(edited(submissions, body)) == ()


def test_a_question_id_total_is_an_issue(submissions: dict[str, Any]) -> None:
    body = rows(submissions)
    body.append({"question_id": "total", "text": "Sum row.", "kind": "custom"})
    assert s.brief_issues(edited(submissions, body)) == (
        "total: a tailored question id cannot be total",
    )


def seen_from(calls: list[dict[str, Any]]) -> Seen:
    read: set[tuple[str, str]] = set()
    searched: list[str | None] = []
    for call in calls:
        read |= {(x["source_id"], x["locator"]) for x in call.get("expect_spans", [])}
        if call["tool"] == "search_pack":
            searched.append(call["arguments"].get("source_id"))
    return Seen(read=frozenset(read), searched=tuple(searched))


def test_the_frozen_research_submission_holds_the_rules(submissions: dict[str, Any]) -> None:
    seen = seen_from(submissions["tool_calls"]["research"])
    assert s.research_rules(json.dumps(submissions["research_v1"]), seen) == ()


def test_a_none_found_item_with_no_search_is_one_absence_issue(
    submissions: dict[str, Any],
) -> None:
    seen = seen_from(submissions["tool_calls"]["research"])
    sub = copy.deepcopy(submissions["research_v1"])
    entry = next(a for a in sub["answers"] if a["question_id"] == "regulation")["contrary"][0]
    entry["searched"] = ["ev-1", "ev-4"]
    got = s.research_rules(json.dumps(sub), seen)
    assert len(got) == 1
    assert got[0].startswith(UNBACKED_ABSENCE) and "regulation" in got[0] and "ev-4" in got[0]
    assert "none_found" in got[0]


def test_a_not_found_answer_item_with_no_search_is_an_absence_issue(
    submissions: dict[str, Any],
) -> None:
    sub = copy.deepcopy(submissions["research_v1"])
    seen = seen_from(submissions["tool_calls"]["research"])
    answer = next(a for a in sub["answers"] if a["question_id"] == "valuation-context")
    answer["searched"] = ["ev-1", "ev-4"]
    got = s.research_rules(json.dumps(sub), seen)
    assert len(got) == 1 and "valuation-context" in got[0] and "ev-4" in got[0]


def test_no_search_at_all_flags_every_absence_item(submissions: dict[str, Any]) -> None:
    got = s.research_rules(json.dumps(submissions["research_v1"]), Seen())
    assert got and all(line.startswith(UNBACKED_ABSENCE) for line in got)


def test_an_unread_page_is_flagged(submissions: dict[str, Any]) -> None:
    sub = copy.deepcopy(submissions["research_v1"])
    seen = seen_from(submissions["tool_calls"]["research"])
    sub["answers"][0]["claims"][0]["citations"][0]["locator"] = "page:3"
    got = s.research_rules(json.dumps(sub), seen)
    assert got and "ev-2 page:3" in got[0]


def test_a_payload_that_is_not_an_object_has_no_rule_issues() -> None:
    assert s.research_rules("[1]", Seen()) == ()
    assert s.research_rules("not json", Seen()) == ()


def test_candidate_inputs_append_the_brief_and_submission_hashes() -> None:
    base = (Input(input_id="CP-0", sha256="1" * 64),)
    got = s.candidate_inputs(base, brief_sha256="2" * 64, submission_sha256="3" * 64)
    assert got == (
        *base,
        Input(input_id="research-brief", sha256="2" * 64),
        Input(input_id="research-submission", sha256="3" * 64),
    )


def test_the_brief_view_names_the_defaults_the_context_and_the_limits(
    manifest: dict[str, Any], expected: dict[str, Any]
) -> None:
    ctx = [(q["text"], q["focus_module"]) for q in manifest["context"]["research_questions"]]
    body = json.loads(
        s.brief_view_body(
            context_questions=ctx, as_of=date(2026, 1, 10), cutoff=date(2026, 1, 10), sources=("a",)
        )
    )
    key = expected["brief"]
    assert [d["question_id"] for d in body["default_questions"]] == key["question_ids"][2:]
    assert [d["kind"] for d in body["default_questions"]] == key["kinds"][2:]
    assert [q["question_id"] for q in body["context_questions"]] == key["question_ids"][:2]
    assert [q["focus_module"] for q in body["context_questions"]] == ["CP-1C", "CP-2"]
    assert body["limits"] == {"max_questions": c.MAX_QUESTIONS}
    assert (body["as_of"], body["cutoff"], body["sources"]) == ("2026-01-10", "2026-01-10", ["a"])


def test_the_research_view_serves_the_locked_brief_and_the_evidence_list(
    tmp_path: Path, manifest: dict[str, Any], submissions: dict[str, Any], expected: dict[str, Any]
) -> None:
    brief = lock(tmp_path, manifest, submission(submissions, DEFAULTS_ONLY))
    item = c.EvidenceItem(
        item_id="ev-1",
        origin="supplied",
        sha256="4" * 64,
        locator="notes.txt",
        published=date(2025, 12, 1),
        family="trade-press",
    )
    body = json.loads(
        s.research_view_body(brief=brief, evidence=(item,), source_ids=("ev-1", "pack-1"))
    )
    assert [q["question_id"] for q in body["questions"]] == expected["brief"]["question_ids"]
    assert body["brief_sha256"] == brief.brief_sha256
    assert body["evidence"] == [
        {
            "item_id": "ev-1",
            "family": "trade-press",
            "published": "2025-12-01",
            "locator": "notes.txt",
        }
    ]
    assert body["sources"] == ["ev-1", "pack-1"]
