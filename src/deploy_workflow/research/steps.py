"""CP-DR brief step and research step logic (O7b-1c S2a', Behaviours 6 and 7).

Store-free: pure over the submissions, the locked brief, the accepted evidence list and the
session's ``Seen``. The owner core (S2b) calls these; nothing here reads a store, a host or an
owner. Python checks the brief (the six defaults once each and in order, the language rules, the
id bound) before ``lock_brief`` orders, bounds and hashes it, and checks the research step's
evidence rules (absence needs a recorded search, a cited page needs a read).
"""

import json
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any, Final, NamedTuple, Self

from deploy_vii.contracts import Contract, Identifier, Input, Text
from deploy_vii.execution import listed_issues
from deploy_vii.live.schema import json_object
from deploy_vii.live.tools import UNBACKED_ABSENCE, Seen, unread_citation_issues
from deploy_workflow.research.brief import CONTEXT_PREFIX, TailoredQuestion
from deploy_workflow.research.contracts import (
    MAX_QUESTIONS,
    EvidenceItem,
    QuestionKind,
    ResearchBrief,
)
from deploy_workflow.research.review import Answer, _language_issues
from deploy_workflow.research.tables import TDR1_COLUMNS, TDR3_COLUMNS

IDENTIFIER_MAX: Final = 160  # `contracts.Identifier` max_length
# A question id sits in the fact ids `TDR.1.<id>.<field>` and `TDR.3.<id>.<field>` (tables.py): the
# longest field decides, and one id past this makes `Fact` raise after the binding write.
QUESTION_ID_MAX: Final = IDENTIFIER_MAX - max(
    *(len("TDR.1.") + len(f".{field}") for field in TDR1_COLUMNS),
    *(len("TDR.3.") + len(f".{field}") for field in TDR3_COLUMNS),
)
RESEARCH_BRIEF_INPUT: Final = "research-brief"
RESEARCH_SUBMISSION_INPUT: Final = "research-submission"
DEFAULTS_FIRST: Final = "the six default questions come first, in their fixed order"


class DefaultQuestion(NamedTuple):
    question_id: str
    kind: QuestionKind


# The six default questions (O7-R3; the base texts live in methods/cpdr.md): ids and kinds are
# written once here, and a test compares them with cases/cpdr-research-owner/expected.json#brief.
DEFAULT_QUESTIONS: Final = (
    DefaultQuestion("competition", "default_1"),
    DefaultQuestion("metric-definitions", "default_2"),
    DefaultQuestion("valuation-context", "default_3"),
    DefaultQuestion("market-demand", "default_4"),
    DefaultQuestion("industry-structure", "default_5"),
    DefaultQuestion("regulation", "default_6"),
)
_DEFAULT_KIND: Final = dict(DEFAULT_QUESTIONS)


class BriefQuestion(Contract):
    question_id: Identifier
    text: Text
    kind: QuestionKind


class BriefSubmission(Contract):
    run_id: Identifier
    questions: tuple[BriefQuestion, ...]

    @classmethod
    def parse(cls, body: Mapping[str, Any]) -> Self:
        """From a JSON body: lists become tuples (the contracts are strict)."""
        return cls.model_validate(body, strict=False)


def _default_issues(ids: Sequence[str]) -> list[str]:
    """Each default once; with all present once, the defaults lead the brief in fixed order."""
    issues = []
    for default_id, _ in DEFAULT_QUESTIONS:
        count = ids.count(default_id)
        if count == 0:
            issues.append(f"default question {default_id} is missing")
        elif count > 1:
            issues.append(f"default question {default_id} appears {count} times")
    wanted = [default_id for default_id, _ in DEFAULT_QUESTIONS]
    if not issues and list(ids[: len(wanted)]) != wanted:
        issues.append(DEFAULTS_FIRST)
    return issues


def _kind_issues(question: BriefQuestion) -> list[str]:
    qid = question.question_id
    if qid in _DEFAULT_KIND:
        if question.kind != _DEFAULT_KIND[qid]:
            return [f"{qid}: a default question carries its own kind {_DEFAULT_KIND[qid]}"]
        return []
    if question.kind != "custom":
        return [f"{qid}: a tailored question is kind custom"]
    return []


def _id_issues(question: BriefQuestion, seen: set[str]) -> list[str]:
    qid = question.question_id
    if qid in _DEFAULT_KIND:
        return []  # a repeated default is reported once, by `_default_issues`
    issues = []
    if qid.startswith(CONTEXT_PREFIX):
        issues.append(f"{qid}: a tailored question id cannot start with {CONTEXT_PREFIX}")
    if qid in seen:
        issues.append(f"{qid}: question_id appears twice")
    if len(qid) > QUESTION_ID_MAX:
        issues.append(f"{qid}: question_id is longer than {QUESTION_ID_MAX}")
    return issues


def _language(question: BriefQuestion) -> list[str]:
    """O7-R18: the review's banned-word and digit checks, run by the review's own function over
    the question text (carried as the uncertainty of a throwaway answer)."""
    probe = Answer(
        question_id=question.question_id,
        answer_state="answered",
        claims=(),
        contrary=(),
        uncertainty=question.text,
        limitation=None,
    )
    return [str(issue) for issue in _language_issues(probe)]


def brief_issues(submission: BriefSubmission) -> tuple[str, ...]:
    """Every failed brief check, in a fixed order; empty when ``lock_brief`` may run.

    ``lock_brief`` still refuses what it checks itself (kind ``context``, bad receivers); the
    issues here are the ones the model repairs, so each is a journaled invalid step.
    """
    questions = submission.questions
    issues = _default_issues([q.question_id for q in questions])
    seen: set[str] = set()
    for question in questions:
        issues += _kind_issues(question)
        issues += _id_issues(question, seen)
        issues += _language(question)
        seen.add(question.question_id)
    return tuple(issues)


def tailored_of(submission: BriefSubmission) -> tuple[TailoredQuestion, ...]:
    return tuple(TailoredQuestion(q.question_id, q.text, q.kind) for q in submission.questions)


def _compact(body: Mapping[str, object]) -> str:
    return json.dumps(body, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def brief_view_body(
    *,
    context_questions: Sequence[tuple[str, str]],
    as_of: date,
    cutoff: date,
    sources: Sequence[str],
) -> str:
    """The brief step's ``read_inputs`` body as compact JSON: the fixed defaults, the run's
    context questions (ids as ``lock_brief`` assigns them), the bound and the held sources."""
    return _compact(
        {
            "default_questions": [
                {"question_id": qid, "kind": kind} for qid, kind in DEFAULT_QUESTIONS
            ],
            "context_questions": [
                {"question_id": f"{CONTEXT_PREFIX}{i}", "text": text, "focus_module": focus}
                for i, (text, focus) in enumerate(context_questions, 1)
            ],
            "limits": {"max_questions": MAX_QUESTIONS},
            "as_of": as_of.isoformat(),
            "cutoff": cutoff.isoformat(),
            "sources": list(sources),
        }
    )


def research_view_body(
    *, brief: ResearchBrief, evidence: Sequence[EvidenceItem], source_ids: Sequence[str]
) -> str:
    """The research step's ``read_inputs`` body: the locked brief's questions, the accepted
    evidence list (no text; the model reads it through the tools) and the held source ids."""
    return _compact(
        {
            "brief_sha256": brief.brief_sha256,
            "questions": [
                {
                    "question_id": q.question_id,
                    "text": q.text,
                    "kind": q.kind,
                    "receivers": list(q.receivers),
                    "focus_module": q.focus_module,
                }
                for q in brief.questions
            ],
            "evidence": [
                {
                    "item_id": item.item_id,
                    "family": item.family,
                    "published": None if item.published is None else item.published.isoformat(),
                    "locator": item.locator,
                }
                for item in evidence
            ],
            "sources": list(source_ids),
        }
    )


def _searched_lists(answer: Mapping[str, object]) -> list[tuple[str, object]]:
    """The ``(where, searched)`` lists of one answer: its own and each ``none_found`` entry's."""
    found: list[tuple[str, object]] = [("searched", answer.get("searched"))]
    contrary = answer.get("contrary")
    for entry in contrary if isinstance(contrary, list) else ():
        if isinstance(entry, dict) and entry.get("kind") == "none_found":
            found.append(("none_found", entry.get("searched")))
    return found


def _absent_in(answer: object, seen: Seen) -> set[tuple[str, str, str]]:
    qid = answer.get("question_id") if isinstance(answer, dict) else None
    if not isinstance(answer, dict) or not isinstance(qid, str):
        return set()
    return {
        (qid, where, item)
        for where, items in _searched_lists(answer)
        for item in (items if isinstance(items, list) else ())
        if isinstance(item, str) and not seen.searched_source(item)
    }


def _absent(document: Mapping[str, object], seen: Seen) -> list[str]:
    """Every ``<question_id> <where> <item>`` whose searched item has no recorded search, once
    each. Reads only what has the expected JSON shape; the schema reports the rest."""
    answers = document.get("answers")
    found: set[tuple[str, str, str]] = set()
    for answer in answers if isinstance(answers, list) else ():
        found |= _absent_in(answer, seen)
    return [" ".join(parts) for parts in sorted(found)]


def research_rules(text: str, seen: Seen) -> tuple[str, ...]:
    """The research step's evidence rules over the payload text and ``Seen``: absence first (every
    searched item of an answer or a ``none_found`` entry needs a recorded ``search_pack``), then
    unread page citations, each sorted. A payload that is not a JSON object has no rule issues;
    the schema check reports it."""
    document = json_object(text)
    absent = [] if document is None else _absent(document, seen)
    return (
        *listed_issues(
            absent,
            lambda line: (
                UNBACKED_ABSENCE,
                ": ",
                line,
                "; search_pack that source before claiming it is not found",
            ),
            lambda count: f"{UNBACKED_ABSENCE}: {count} further absence claims not listed",
        ),
        *unread_citation_issues(text, seen),
    )


def candidate_inputs(
    attempt_inputs: Sequence[Input], *, brief_sha256: str, submission_sha256: str
) -> tuple[Input, ...]:
    """The CP-DR head's inputs: the attempt's, then the locked brief and the research submission."""
    return (
        *attempt_inputs,
        Input(input_id=RESEARCH_BRIEF_INPUT, sha256=brief_sha256),
        Input(input_id=RESEARCH_SUBMISSION_INPUT, sha256=submission_sha256),
    )
