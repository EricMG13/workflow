"""CP-1A owner extras: the verifier probe, and the one-step probe CP-2 shares."""

from collections.abc import Callable

from deploy_vii.business_context import (
    BusinessContextReport,
    _validate_step,
    cp1a_module,
)
from deploy_vii.contracts import Module
from deploy_vii.execution import Attempt, Execution, ExecutionSnapshot, StepValidation, settle
from deploy_vii.preparation import PreparedPack
from deploy_workflow.financial_workflow import _FrozenExecution
from deploy_workflow.workflow import WorkflowError


def probe_one_step(
    store: Execution,
    snapshot: ExecutionSnapshot,
    attempt: Attempt,
    *,
    validate: Callable[[Execution, PreparedPack, Attempt], StepValidation],
    build: Callable[[str, Attempt], Module],
) -> None:
    """Rerun a one-step module's public validator and settlement over the settled snapshot.

    The attempt has exactly one valid step; the module's own `_validate_step`, run on a frozen
    view, gives no issue and the retained output bytes; the rebuilt candidate settles back to
    exactly the finished attempt and the head's module. Nothing is written."""
    if len(attempt.steps) != 1 or attempt.steps[0].status != "valid":
        raise WorkflowError("identity_mismatch")
    step = attempt.steps[0]
    pack = store.pack(snapshot)
    outcome = validate(_FrozenExecution(store, snapshot), pack, attempt)
    if (
        outcome.issues
        or outcome.output is None
        or not outcome.retained_as(step)
        or store.step_output(step.output_sha256 or "") != outcome.output
    ):
        raise WorkflowError("identity_mismatch")
    candidate = build(outcome.output, attempt)
    finished, result = settle(
        snapshot,
        attempt,
        candidate.model_dump_json(),
        lambda supplied: () if supplied == candidate else ("Candidate differs",),
        pack=pack,
        load=store.head_module,
    )
    head = next(h for h in snapshot.heads if h.module_id == attempt.module_id)
    if finished != attempt or result != store.head_module(head):
        raise WorkflowError("identity_mismatch")


def _candidate(output: str, attempt: Attempt) -> Module:
    report = BusinessContextReport.model_validate_json(output)
    return cp1a_module(report, attempt.inputs, attempt.number)


# The validator the module's own entry hands `Execution.submit_step` (R4-2: the verifier replays
# an invalid step through it at the historical snapshot).
ENTRY_VALIDATOR = _validate_step


def probe(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    probe_one_step(store, snapshot, attempt, validate=_validate_step, build=_candidate)
