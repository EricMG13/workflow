"""CP-5 integrity review owner, Stage 1: the calculation as pure functions.

`docs/CP5-OWNER-LEASE.md` adds no CP-5 arithmetic and no new composer: the reused engine
`deploy_vii.cp5_integrity` runs the Python checks, validates the analyst's review and composes the
seventeen registers and the own limitations. This module binds the operands the engine reads into
one typed object and calls the engine without a store: the `ReviewScope` is supplied, where the
journal path builds it with `cp5_integrity.review_scope(store, attempt)`.

The one new piece is the owner view body (lease, Owner view, construction steps 2 to 6): the
engine's CONTEXT block over the bound heads, with every fact of each head except CP-1 (whose facts
`live.context.integrity_projection` trims), no citation quote, and each Python finding reduced to
its kind label and where. Reading the historical scope (step 1), registration and the probe are
added in later stages.
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast

from deploy_vii.contracts import Fact, Module
from deploy_vii.cp5_integrity import (
    KIND_LABEL,
    FactProjection,
    IntegrityReport,
    IntegritySubmission,
    ReviewScope,
    context_block,
    cp5_module,
    integrity_review,
    python_checks,
    validate_integrity,
)
from deploy_vii.live.context import integrity_projection
from deploy_workflow.workflow import WorkflowError

# The head whose facts the view trims (a promoted CP-1 holds tens of thousands of facts).
PROJECTED_MODULE = "CP-1"
# What a citation keeps in the view: its reference and its place, never its quote.
CITATION_FIELDS = ("ref", "source_id", "locator")


@dataclass(frozen=True)
class CP5Inputs:
    """Every operand the CP-5 Method reads.

    `scope` holds the prepared pack, the attempt's bound inputs (with each producer's status), the
    bound analyst heads, the blocked ancestors, the inherited limitations and any reason the scope
    cannot be reviewed (`cp5_integrity.ReviewScope`). `submission` holds the analyst judgments."""

    scope: ReviewScope
    submission: IntegritySubmission


@dataclass(frozen=True)
class CP5Result:
    """The engine's outcome: validator issues (a refused submission, `report` None) or the
    composed review (`issues` empty)."""

    issues: tuple[str, ...]
    report: IntegrityReport | None


def compute(inputs: CP5Inputs) -> CP5Result:
    """Validate and compose one CP-5 review over the supplied scope (no I/O)."""
    issues = validate_integrity(inputs.scope, inputs.submission)
    if issues:
        return CP5Result(issues=issues, report=None)
    return CP5Result(issues=(), report=integrity_review(inputs.scope, inputs.submission))


def candidate(result: CP5Result, inputs: CP5Inputs, attempt: int) -> Module:
    """The CP-5 candidate module of a composed review, bound to the attempt's inputs."""
    if result.report is None:
        raise ValueError("A refused CP-5 submission has no candidate: " + "; ".join(result.issues))
    return cp5_module(result.report, inputs.scope.inputs, attempt)


def owner_projection(scope: ReviewScope) -> FactProjection:
    """`P` of the owner view: the `integrity_projection` facts of the CP-1 head, and every fact
    of every other head (so a claim with no figure and no citation still shows its cells)."""
    trimmed = integrity_projection(scope)

    def project(head: Module) -> Sequence[Fact]:
        return trimmed(head) if head.module_id == PROJECTED_MODULE else head.facts

    return project


def view_body(scope: ReviewScope) -> tuple[str, str]:
    """(sha256, body) of the CP-5 owner view over `scope`.

    A scope that cannot be reviewed (stale or unreadable inputs) has no view: it raises
    `WorkflowError("identity_mismatch")`. The body is the CONTEXT block with the facts `P`
    projects; each claim's citations keep `ref`, `source_id` and `locator` only, each per-claim
    Python finding is cut at its first ": " (its kind, or "kind on ref"), and the top-level
    Python findings are the kind label plus where, with no detail (a citation finding's detail
    can carry a quote fragment). Compact JSON, digest over its UTF-8 bytes."""
    if scope.issues:
        raise WorkflowError("identity_mismatch")
    block = context_block(scope, facts=owner_projection(scope))
    for module in cast(list[dict[str, Any]], block["modules"]):
        for claim in module["claims"]:
            claim["citations"] = [
                {name: citation[name] for name in CITATION_FIELDS}
                for citation in claim["citations"]
            ]
            claim["python_findings"] = [mark.split(": ", 1)[0] for mark in claim["python_findings"]]
    block["python_findings"] = [
        f"{KIND_LABEL[finding.kind]}: {finding.where}" for finding in python_checks(scope).findings
    ]
    body = json.dumps(block, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(body.encode()).hexdigest(), body
