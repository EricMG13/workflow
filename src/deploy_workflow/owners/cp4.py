"""CP-4 (legal and covenants) owner core, Stage 1: the calculation (docs/CP4-OWNER-LEASE.md).

CP-4 writes no new analytical core: `cp4_legal.covenant_interpretation` composes the 31 tables
and owns every number. This module adds the lease's semantic gate (LEAD ruling Q1 = A) and a pure
`compute` that runs the gate, then the engine's validator, then its composer. Connection
(`cp4_upstream` over the bound heads), `view`, `probe` and the core `precheck` hook are later
stages and are not here.
"""

import re
from dataclasses import dataclass

from deploy_vii import cp4_legal
from deploy_vii.contracts import Input
from deploy_vii.preparation import PreparedPack

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
