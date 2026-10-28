"""CP-4 (legal and covenants) owner core, Stage 1: the calculation (docs/CP4-OWNER-LEASE.md).

CP-4 writes no new analytical core: `cp4_legal.covenant_interpretation` composes the 31 tables
and owns every number. This module adds the lease's semantic gate (LEAD ruling Q1 = A) and a pure
`compute` that runs the gate, then the engine's validator, then its composer.

Stage 2 connects it to G1 (rulings stage2 Q3, Q4): the entry validator, the exact `step_context`
view, the verifier probe and the `precheck` hook that runs the semantic gate. `cp4_legal` reads
the bound CP-0/CP-1 heads itself (`upstream_of`), so there is no further store adapter.
"""

import hashlib
import json
import re
from dataclasses import dataclass

from pydantic import ValidationError

from deploy_vii import cp4_legal
from deploy_vii.contracts import Input, Module
from deploy_vii.execution import Attempt, Execution, ExecutionSnapshot
from deploy_vii.live.schema import json_object
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owners.cp1a import probe_one_step

# Closed list, frozen from the gap legal source (Clause 2.3) and absent from every positive legal,
# identity and financial page. Never "defined in", "as defined in" or the bare "incorporated".
MARKERS = ("has the meaning assigned in", "is not supplied with this copy")
SAME_DEFINITION = "Same definition"
_ISSUE = (
    "covenants[{index}]: metric_basis 'Same definition' is refused because the cited source text "
    "matches incorporation-by-reference markers: {markers}"
)
_WHITESPACE = re.compile(r"\s+")


def _normalise(text: str) -> str:
    return _WHITESPACE.sub(" ", text).casefold()


def _scope(pack: PreparedPack, covenant: cp4_legal.Covenant) -> tuple[str, ...]:
    """The row's cited quote texts, then the full text of each pack page it cites, each
    (source_id, locator) once. A cited page absent from the pack contributes only its quote."""
    pages = {
        (source.source_id, span.locator): span.text
        for source in pack.sources
        for span in source.spans
    }
    cited = dict.fromkeys((quote.source_id, quote.locator) for quote in covenant.citations)
    return (
        *(quote.quote for quote in covenant.citations),
        *(pages[key] for key in cited if key in pages),
    )


def markers_in_scope(pack: PreparedPack, covenant: cp4_legal.Covenant) -> tuple[str, ...]:
    """The markers matching anywhere in the covenant's scope, in list order."""
    scope = tuple(_normalise(text) for text in _scope(pack, covenant))
    return tuple(marker for marker in MARKERS if any(marker in text for text in scope))


def semantic_issues(
    *, pack: PreparedPack, submission: cp4_legal.CovenantInterpretationSubmission
) -> tuple[str, ...]:
    """One issue per covenant claiming `Same definition` whose scope matches a marker."""
    issues: list[str] = []
    for index, covenant in enumerate(submission.covenants):
        if covenant.metric_basis != SAME_DEFINITION:
            continue
        hits = markers_in_scope(pack, covenant)
        if hits:
            markers = "; ".join(f"'{marker}'" for marker in hits)
            issues.append(_ISSUE.format(index=index, markers=markers))
    return tuple(issues)


@dataclass(frozen=True)
class Cp4Inputs:
    """Every operand CP-4 reads: the pack, the analyst submission (judgment and quotes), what
    CP-4 read from the bound CP-0/CP-1 heads and the bound inputs themselves."""

    pack: PreparedPack
    submission: cp4_legal.CovenantInterpretationSubmission
    upstream: cp4_legal.Upstream
    inputs: tuple[Input, ...]


@dataclass(frozen=True)
class Cp4Result:
    """The refusal issues, or the composed report (never both)."""

    issues: tuple[str, ...]
    report: cp4_legal.CovenantInterpretationReport | None


def compute(inputs: Cp4Inputs) -> Cp4Result:
    """Gate first, then the engine's validator, then its composer."""
    gated = semantic_issues(pack=inputs.pack, submission=inputs.submission)
    if gated:
        return Cp4Result(issues=gated, report=None)
    issues = cp4_legal.validate_covenant_interpretation(
        inputs.pack, inputs.submission, inputs.upstream, inputs.inputs
    )
    if issues:
        return Cp4Result(issues=issues, report=None)
    report = cp4_legal.covenant_interpretation(
        inputs.pack, inputs.submission, inputs.upstream, inputs.inputs
    )
    return Cp4Result(issues=(), report=report)


# --- Stage 2: the plug-in parts of docs/G1X-OWNER-CORE-PROTOCOL.md section 2 ------------------

# The validator CP-4's own entry hands `Execution.submit_step` (R4-2: the verifier replays an
# invalid step through it at the historical snapshot). The signature already matches: no adapter.
ENTRY_VALIDATOR = cp4_legal._validate_step


def view(historical: Execution, attempt: Attempt) -> tuple[str, str]:
    """(sha256, body) of CP-4's one read: `cp4_legal.context_block` over the pack and the CP-0 and
    CP-1 heads `attempt` binds, as compact JSON (lease Public API, `inputs="step_context"`)."""
    block = cp4_legal.context_block(historical.pack(), cp4_legal.upstream_of(historical, attempt))
    body = json.dumps(block, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(body.encode()).hexdigest(), body


def _candidate(output: str, attempt: Attempt) -> Module:
    report = cp4_legal.CovenantInterpretationReport.model_validate_json(output)
    return cp4_legal.cp4_module(report, attempt.inputs, attempt.number)


def probe(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    """The verifier probe: the engine's `_validate_step` and settlement rebuild the head."""
    probe_one_step(store, snapshot, attempt, validate=cp4_legal._validate_step, build=_candidate)


def precheck(store: Execution, binding: object, stored: str) -> tuple[str, ...]:
    """The Q1 gate over the filled payload (protocol section 4): the `Same definition` refusals.

    The text is read only through the bounded `json_object` parse (protocol section 6), then as
    the engine's schema. Text that is not an object, or does not fit the schema, gets no issue
    here: it is the step validator's to refuse as a shape error when the journal runs it, so
    this gate never raises after the binding write and never accepts such text on its own."""
    if json_object(stored) is None:
        return ()
    try:
        submission = cp4_legal.CovenantInterpretationSubmission.model_validate_json(stored)
    except ValidationError:
        return ()
    return semantic_issues(pack=store.pack(), submission=submission)
