"""CP-DR research submission and its Python checks (O7b-1b, Behaviour 7).

The model supplies, per brief question, claims with citations, contrary evidence, an uncertainty
and an answer state. Python decides whether the submission holds (OD6): citations resolve against
the held sources, every answered claim has contrary evidence and an uncertainty, two items of one
family never count as independent, ``not_found`` is ``missing`` with a limitation, and the text
holds no figure and no banned word. The owner step and the model call are O7b-1c.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Any, Final, Literal, Self

from pydantic import Field

from deploy_vii.contracts import Citation, Contract, Identifier, Source, Text
from deploy_vii.readiness import citation_issues
from deploy_workflow.research.contracts import (
    RESERVED_PREFIX,
    ClaimState,
    EvidenceItem,
    ResearchBrief,
)

AnswerState = Literal["answered", "partly", "not_found"]
# OD11/L3: the owners/cpdr.py PROHIBITED list minus covenant, recovery and refinanc; nothing added.
BANNED_WORDS: Final = ("recommend",)
FIGURE_ISSUE: Final = "text must not contain a figure"


class Claim(Contract):
    claim_id: Identifier
    text: Text
    citations: tuple[Citation, ...]
    independent_items: tuple[Identifier, ...]


class CitedContrary(Contract):
    kind: Literal["cited"]
    item: Identifier
    citation: Citation
    limitation: str | None
    text: Text


class NoneFound(Contract):
    kind: Literal["none_found"]
    searched: tuple[Identifier, ...]
    limitation: Text


Contrary = Annotated[CitedContrary | NoneFound, Field(discriminator="kind")]


class Answer(Contract):
    question_id: Identifier
    answer_state: AnswerState
    claims: tuple[Claim, ...]
    contrary: tuple[Contrary, ...]
    uncertainty: str | None
    searched: tuple[Identifier, ...] = ()
    limitation: str | None


class ResearchSubmission(Contract):
    run_id: Identifier
    answers: tuple[Answer, ...]

    @classmethod
    def parse(cls, body: Mapping[str, Any]) -> Self:
        """From a JSON body: lists become tuples (the contracts are strict)."""
        return cls.model_validate(body, strict=False)


@dataclass(frozen=True)
class ReviewIssue:
    """One failed check; ``text`` is the frozen wording, ``question_id`` says where."""

    question_id: str
    text: str

    def __str__(self) -> str:
        return f"{self.question_id}: {self.text}"


@dataclass(frozen=True)
class Counts:
    questions_total: int
    answered: int
    partly: int
    not_found: int
    contrary_items: int


def question_state(answer: Answer) -> ClaimState:
    """Q9: not_found and partly are ``missing``; a cited contrary entry is ``contrary``."""
    if answer.answer_state != "answered":
        return "missing"
    if any(isinstance(entry, CitedContrary) for entry in answer.contrary):
        return "contrary"
    return "supported"


def claim_states(submission: ResearchSubmission, brief: ResearchBrief) -> tuple[ClaimState, ...]:
    """One state per brief question, in brief order; a question never answered is ``blocked``."""
    by_id = {answer.question_id: answer for answer in submission.answers}
    return tuple(
        question_state(by_id[q.question_id]) if q.question_id in by_id else "blocked"
        for q in brief.questions
    )


def answer_counts(submission: ResearchSubmission) -> Counts:
    answers = submission.answers
    return Counts(
        questions_total=len(answers),
        answered=sum(a.answer_state == "answered" for a in answers),
        partly=sum(a.answer_state == "partly" for a in answers),
        not_found=sum(a.answer_state == "not_found" for a in answers),
        contrary_items=sum(isinstance(c, CitedContrary) for a in answers for c in a.contrary),
    )


def _texts(answer: Answer) -> list[str]:
    """Analyst-written prose of an answer; quotes are source text and are not held to the rules."""
    found = [claim.text for claim in answer.claims]
    found += [answer.uncertainty or "", answer.limitation or ""]
    for entry in answer.contrary:
        found.append(entry.limitation or "")
        if isinstance(entry, CitedContrary):
            found.append(entry.text)
    return [text for text in found if text]


def _language_issues(answer: Answer) -> list[ReviewIssue]:
    qid = answer.question_id
    texts = _texts(answer)
    issues = [
        ReviewIssue(qid, f"banned word: {word}")
        for word in BANNED_WORDS
        if any(word in text.lower() for text in texts)
    ]
    if any(char.isdigit() for text in texts for char in text):
        issues.append(ReviewIssue(qid, FIGURE_ISSUE))
    return issues


def _independent_list_issues(qid: str, claim: Claim) -> list[ReviewIssue]:
    """O7-R7: the list is distinct and names ``ev-*`` items only (pack sources have no family)."""
    issues = []
    if len(set(claim.independent_items)) != len(claim.independent_items):
        issues.append(ReviewIssue(qid, f"independent items of {claim.claim_id} repeat an item"))
    issues += [
        ReviewIssue(qid, f"independent item {item} of {claim.claim_id} is not an ev-* item")
        for item in dict.fromkeys(claim.independent_items)
        if not item.startswith(RESERVED_PREFIX)
    ]
    return issues


def _independence_issues(answer: Answer, family_of: Mapping[str, str]) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    for claim in answer.claims:
        cited = {citation.source_id for citation in claim.citations}
        issues += [
            ReviewIssue(
                answer.question_id,
                f"independent item {item} is not cited by {claim.claim_id}",
            )
            for item in claim.independent_items
            if item not in cited
        ]
        items = claim.independent_items
        issues += _independent_list_issues(answer.question_id, claim)
        if len(set(items)) != len(items):
            continue
        for i, first in enumerate(items):
            for second in items[i + 1 :]:
                family = family_of.get(first)
                if family is not None and family == family_of.get(second):
                    issues.append(
                        ReviewIssue(
                            answer.question_id,
                            f"families not independent: {first} and {second} share family {family}",
                        )
                    )
    return issues


def _completeness_issues(answer: Answer) -> list[ReviewIssue]:
    qid = answer.question_id
    if answer.answer_state == "not_found":
        issues = []
        if answer.claims:
            issues.append(ReviewIssue(qid, "a not_found question carries no claim"))
        if not (answer.limitation and answer.limitation.strip()):
            issues.append(ReviewIssue(qid, "a not_found question states its limitation"))
        if not answer.searched:
            issues.append(ReviewIssue(qid, "a not_found question names the items searched"))
        return issues
    issues = []
    if not answer.claims:
        issues.append(ReviewIssue(qid, f"a {answer.answer_state} question needs a claim"))
    issues += [
        ReviewIssue(qid, f"claim {claim.claim_id} needs a citation")
        for claim in answer.claims
        if not claim.citations
    ]
    if not answer.contrary:
        issues.append(ReviewIssue(qid, "an answered claim needs contrary evidence or none found"))
    if not (answer.uncertainty and answer.uncertainty.strip()):
        issues.append(ReviewIssue(qid, "an answered claim needs an uncertainty"))
    if answer.answer_state == "partly" and not (answer.limitation and answer.limitation.strip()):
        issues.append(ReviewIssue(qid, "a partly question states its limitation"))
    return issues


def _citation_issues(answer: Answer, sources: tuple[Source, ...]) -> list[ReviewIssue]:
    cited = [c for claim in answer.claims for c in claim.citations]
    cited += [c.citation for c in answer.contrary if isinstance(c, CitedContrary)]
    held = {source.source_id for source in sources}
    issues = [
        ReviewIssue(answer.question_id, text) for text in citation_issues(tuple(cited), sources)
    ]
    for entry in answer.contrary:
        if isinstance(entry, CitedContrary) and entry.item != entry.citation.source_id:
            issues.append(
                ReviewIssue(answer.question_id, f"contrary item {entry.item} is not its citation")
            )
        if isinstance(entry, NoneFound) and not entry.searched:
            issues.append(
                ReviewIssue(answer.question_id, "a none_found contrary names the items searched")
            )
        if isinstance(entry, NoneFound):
            issues += [
                ReviewIssue(answer.question_id, f"searched item {item} is not a held source")
                for item in entry.searched
                if item not in held
            ]
    issues += [
        ReviewIssue(answer.question_id, f"searched item {item} is not a held source")
        for item in answer.searched
        if item not in held
    ]
    return issues


def _owner_of(submission: ResearchSubmission, claim_id: str) -> str:
    """The question that holds the last use of ``claim_id`` (the repeat, not the first)."""
    return [
        a.question_id for a in submission.answers if any(c.claim_id == claim_id for c in a.claims)
    ][-1]


def research_issues(
    *,
    submission: ResearchSubmission,
    brief: ResearchBrief,
    evidence: Sequence[EvidenceItem],
    sources: Sequence[Source],
) -> tuple[ReviewIssue, ...]:
    """Every failed check of ``submission`` against the locked brief, the accepted evidence and the
    held sources (``ev-*`` and pack). Empty when the submission holds; never raises for content."""
    family_of = {item.item_id: item.family for item in evidence}
    held = tuple(sources)
    issues: list[ReviewIssue] = []
    wanted = [q.question_id for q in brief.questions]
    seen: set[str] = set()
    for answer in submission.answers:
        qid = answer.question_id
        if qid not in wanted:
            issues.append(ReviewIssue(qid, "question is not in the locked brief"))
        elif qid in seen:
            issues.append(ReviewIssue(qid, "question_id appears twice"))
        seen.add(qid)
        issues += _completeness_issues(answer)
        issues += _citation_issues(answer, held)
        issues += _independence_issues(answer, family_of)
        issues += _language_issues(answer)
    claim_ids = [claim.claim_id for answer in submission.answers for claim in answer.claims]
    issues += [
        ReviewIssue(_owner_of(submission, claim_id), f"claim_id {claim_id} appears twice")
        for claim_id in dict.fromkeys(claim_ids)
        if claim_ids.count(claim_id) > 1
    ]
    issues += [
        ReviewIssue(qid, "brief question has no answer") for qid in wanted if qid not in seen
    ]
    return tuple(issues)
