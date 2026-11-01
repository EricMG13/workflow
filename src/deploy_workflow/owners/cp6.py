"""CP-6 owner extras: the exact `read_inputs` view and the verifier probe.

CP-6 has a live chain with no pack sources, so it is a `model_payload` module like CP-2: the
product's own `_validate_step` is its entry validator and `PROMOTED` its qualification.
"""

import hashlib
import json

from deploy_vii.contracts import Module
from deploy_vii.cp6_committee import PROMOTED, CommitteeReport, _validate_step, cp6_module
from deploy_vii.execution import Attempt, Execution, ExecutionSnapshot
from deploy_vii.live.context import module_context
from deploy_workflow.owners.cp1a import probe_one_step
from deploy_workflow.workflow import WorkflowError

STEP_ID = "committee_challenge"
QUALIFICATION = PROMOTED


def view(store: Execution, attempt: Attempt) -> tuple[str, str]:
    """(sha256, body) of CP-6's one read: `module_context("committee_challenge")` over the bound
    heads, as compact JSON."""
    context = module_context(store, attempt, STEP_ID)
    if context is None:
        raise WorkflowError("identity_mismatch")
    body = json.dumps(context, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(body.encode()).hexdigest(), body


def _candidate(output: str, attempt: Attempt) -> Module:
    report = CommitteeReport.model_validate_json(output)
    return cp6_module(report, attempt.inputs, attempt.number)


# The validator CP-6's own entry hands `Execution.submit_step` (invalid-step replay).
ENTRY_VALIDATOR = _validate_step


def probe(store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
    probe_one_step(store, snapshot, attempt, validate=_validate_step, build=_candidate)
