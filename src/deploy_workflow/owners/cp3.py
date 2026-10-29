"""CP-3 relative value owner, Stage 1: the calculation as pure functions.

`docs/CP3-OWNER-LEASE.md` adds no CP-3 arithmetic and no new composer: the reused engine
`deploy_vii.cp3_relative_value` validates the submission and composes the tables, claims and own
limitations. This module binds the operands the engine reads into one typed object and calls the
engine without a store: `compute` builds the engine's `Upstream` from supplied heads instead of
`cp3_upstream(store, attempt)`.

Stage 2 connection (`docs/G1X-OWNER-CORE-PROTOCOL.md` §1-§2; CP-3 is a live-contract module, so the
core supplies only the items marked *all*): `QUALIFICATION`, `ENTRY_VALIDATOR` and `probe`. The
store adapter is the engine's own `cp3_upstream(store, attempt)`, which `_validate_step` and so
`probe` already use. CP-3 has no `view` (its step reads no `module_context`), no `RULES` (the
journal applies the product's `ToolRules`), no `precheck` and no reader: the lease names none.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

from deploy_vii.contracts import Input, Module
from deploy_vii.cp3_relative_value import (
    PROMOTED,
    RelativeValueReport,
    RelativeValueSubmission,
    Upstream,
    _validate_step,
    context_block,
    cp3_module,
    relative_value,
    validate_relative_value,
)
from deploy_vii.execution import Attempt, Execution, ExecutionSnapshot
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owners.cp1a import probe_one_step


@dataclass(frozen=True)
class CP3Inputs:
    """Every operand the CP-3 Method reads.

    `bound` is the attempt's input set (prepared-pack and the module heads, with their producer
    statuses); `current` is `execution.current_inputs` at validation, or its refusal text;
    `cp0`, `cp1`, `cp2` are the bound required heads; `optional` holds the bound heads of the read
    optional upstreams (CP-1A, CP-4) the run selects; `inherited` is what settlement will carry
    (shown in the CONTEXT block only). `submission` holds the analyst judgments."""

    pack: PreparedPack
    submission: RelativeValueSubmission
    bound: tuple[Input, ...]
    current: tuple[Input, ...] | str
    cp0: Module
    cp1: Module
    cp2: Module
    optional: Mapping[str, Module] = field(default_factory=dict)
    inherited: tuple[str, ...] = ()


@dataclass(frozen=True)
class CP3Result:
    """The engine's outcome: validator issues (a refused submission, `report` None) or the
    composed report (`issues` empty)."""

    issues: tuple[str, ...]
    report: RelativeValueReport | None


def _upstream(inputs: CP3Inputs) -> Upstream:
    return Upstream(
        bound=inputs.bound,
        current=inputs.current,
        cp0=inputs.cp0,
        cp1=inputs.cp1,
        cp2=inputs.cp2,
        optional=inputs.optional,
        inherited=inputs.inherited,
    )


def compute(inputs: CP3Inputs) -> CP3Result:
    """Validate and compose one CP-3 submission over the supplied heads (no I/O)."""
    upstream = _upstream(inputs)
    issues = validate_relative_value(inputs.pack, inputs.submission, upstream)
    if issues:
        return CP3Result(issues=issues, report=None)
    return CP3Result(issues=(), report=relative_value(inputs.pack, inputs.submission, upstream))


def context(inputs: CP3Inputs) -> dict[str, object]:
    """The CONTEXT block the `relative_value` step shows over the same operands; independent
    of the submission, so it is never coupled to (or able to hide) a validation outcome."""
    return context_block(inputs.pack, _upstream(inputs))


def candidate(result: CP3Result, inputs: CP3Inputs, attempt: int) -> Module:
    """The CP-3 candidate module of a composed result, bound to the attempt's inputs."""
    if result.report is None:
        raise ValueError("A refused CP-3 submission has no candidate: " + "; ".join(result.issues))
    return cp3_module(result.report, inputs.bound, attempt)


# The `head_of` qualification `_verify` holds a settled CP-3 head to (`_QUALIFICATION["CP-3"]`).
QUALIFICATION = PROMOTED

# The validator CP-3's own entry hands `Execution.submit_step` (R4-2 invalid-step replay).
ENTRY_VALIDATOR = _validate_step


def _candidate(output: str, attempt: Attempt) -> Module:
    report = RelativeValueReport.model_validate_json(output)
    return cp3_module(report, attempt.inputs, attempt.number)


def probe(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    """Raise `identity_mismatch` unless the settled attempt and the CP-3 head rebuild exactly:
    `_validate_step` over the bound heads, then `cp3_module` and `settle`."""
    probe_one_step(store, snapshot, attempt, validate=_validate_step, build=_candidate)
