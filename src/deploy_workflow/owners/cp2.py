"""CP-2 owner extras: the exact `read_inputs` view and the verifier probe."""

import hashlib
import json

from deploy_vii.contracts import Module
from deploy_vii.cp2_synthesis import STEP_ID, CreditSynthesisReport, _validate_step, cp2_module
from deploy_vii.execution import Attempt, Execution, ExecutionSnapshot
from deploy_vii.live.context import module_context
from deploy_workflow.owners.cp1a import probe_one_step
from deploy_workflow.workflow import WorkflowError


def view(store: Execution, attempt: Attempt) -> tuple[str, str]:
    """(sha256, body) of CP-2's one read: `module_context("credit_synthesis")` over the bound
    heads, as compact JSON (S1a lease rev 2, M4: an exact view, counted as tool use)."""
    context = module_context(store, attempt, STEP_ID)
    if context is None:
        raise WorkflowError("identity_mismatch")
    body = json.dumps(context, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(body.encode()).hexdigest(), body


def _candidate(output: str, attempt: Attempt) -> Module:
    report = CreditSynthesisReport.model_validate_json(output)
    return cp2_module(report, attempt.inputs, attempt.number)


# The validator CP-2's own entry hands `Execution.submit_step` (R4-2 invalid-step replay).
ENTRY_VALIDATOR = _validate_step


def probe(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    probe_one_step(store, snapshot, attempt, validate=_validate_step, build=_candidate)
