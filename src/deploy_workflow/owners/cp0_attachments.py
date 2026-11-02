"""CP-0 attachments precheck (Phase 5 Task 3): a review may not ignore a declared attachment.

The run's context file (frozen in the pack, read through `context_facts`) declares which
attachments the user supplied. This gate refuses a CP-0 review that neither finds a declared
attachment in the pack nor names it in a `source` gap, and one that assesses no legal source of
the declared kind. It runs at submit and again in replay and in the receipt verifier (`_gate`
through `_PRECHECKS`), so a review it would refuse cannot be accepted by editing the record.

Shape and parse follow `owners/cp4.precheck`: text that is not a readiness review gets no issue
here, because the step validator refuses it as a shape error.
"""

import re

from pydantic import ValidationError

from deploy_vii.execution import Execution
from deploy_vii.live.schema import json_object
from deploy_vii.readiness import ReadinessReview
from deploy_workflow.context import ContextRefused, RunContext, context_facts

# Attachment field -> the pack source id that carries it. The ids are the frozen oracle's
# (`expected.json#attachment_ids`); `portfolio` is the id `deploy_vii/inputs/portfolio.py` uses
# for `source_id`. A consumer that changes an id re-cuts this constant and the oracle together.
ATTACHMENT_IDS: dict[str, str] = {
    "portfolio_workbook": "portfolio",
    "prior_case": "prior_case",
    "management_bridge": "bridge",
}
# The attachment rules (three attachments and the legal rule) give at most this many issues.
# `Context refused` lines are one per problem and are bounded only by `bounded_issues`.
MAX_ISSUES = 4
CONTEXT_REFUSED = "Context refused: "
LEGAL_EXECUTED_MISSING = (
    "attachments.legal_documents: 'executed' documents are declared but no source is assessed "
    "executed or filed; add a source gap naming legal_documents"
)
LEGAL_DRAFT_MISSING = (
    "attachments.legal_documents: 'draft' documents are declared but no source is assessed "
    "draft; add a source gap naming legal_documents"
)
# A gap names an id only as a whole token (`<id>` is replaced by the escaped id).
GAP_MATCH = "(?<![A-Za-z0-9_]){id}(?![A-Za-z0-9_])"
LEGAL_GAP_WORD = "legal_documents"


def absent_issue(field: str, source_id: str) -> str:
    return (
        f"attachments.{field}: source '{source_id}' is declared but not in the pack; "
        "add a source gap naming it"
    )


def _legal_issue(
    declared: str, review: ReadinessReview, ready: frozenset[str], gaps: tuple[str, ...]
) -> tuple[str, ...]:
    """The legal rule: a declared `executed` or `draft` kind needs a ready source assessed so, or a
    `source` gap naming legal_documents. `none` imposes nothing."""
    if declared == "none":
        return ()
    wanted = ("executed", "filed") if declared == "executed" else ("draft",)
    held = any(s.source_id in ready and s.authority in wanted for s in review.sources)
    if held or any(LEGAL_GAP_WORD in text for text in gaps):
        return ()
    return (LEGAL_EXECUTED_MISSING if declared == "executed" else LEGAL_DRAFT_MISSING,)


def _issues(context: RunContext, review: ReadinessReview, ready: frozenset[str]) -> tuple[str, ...]:
    gaps = tuple(g.description for g in review.gaps if g.kind == "source")
    issues: list[str] = []
    for field, source_id in ATTACHMENT_IDS.items():
        if not getattr(context.attachments, field) or source_id in ready:
            continue
        named = re.compile(GAP_MATCH.format(id=re.escape(source_id)))
        if not any(named.search(text) for text in gaps):
            issues.append(absent_issue(field, source_id))
    issues.extend(_legal_issue(context.attachments.legal_documents, review, ready, gaps))
    return tuple(issues)


def precheck(store: Execution, binding: object, stored: str) -> tuple[str, ...]:
    """The issues that refuse a CP-0 review before the journal (protocol section 4).

    `stored` is read only through the bounded `json_object` parse, then as the engine's schema;
    anything else gets no issue here. The context comes from the frozen pack, never the user's
    live file: a context the pack cannot honour refuses the review (`Context refused: ...`, one
    line per problem), and no context source imposes nothing."""
    if json_object(stored) is None:
        return ()
    try:
        review = ReadinessReview.model_validate_json(stored)
    except ValidationError:
        return ()
    pack = store.pack()
    try:
        context = context_facts(pack)
    except ContextRefused as refused:
        return tuple(CONTEXT_REFUSED + problem for problem in refused.problems)
    if context is None:
        return ()
    ready = frozenset(s.source_id for s in pack.sources if s.status == "ready")
    return _issues(context, review, ready)
