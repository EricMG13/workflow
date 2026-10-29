"""CP-4 verifier probe on a genuine store (fix round 1, review M2).

`tests/test_source_tools.legal_history` builds real CP-0 and CP-1 heads over the legal pack (about
90 s, no CP-1 promotion run), so this file is its own: it exceeds the 60 s a fast file may take.
CP-4 is settled through the engine's own `submit_cp4_step`; the probe must then pass on the
honest head and refuse each forgery the verifier can meet. Expected values come from the oracle.
"""

import importlib
import json
from collections.abc import Iterator
from typing import Any

import pytest

from deploy_vii import cp4_legal
from deploy_vii.execution import Attempt, Execution, ExecutionSnapshot
from deploy_workflow.owners import cp4
from deploy_workflow.workflow import WorkflowError

stage1: Any = importlib.import_module("test_method_cp4")
source_tools: Any = importlib.import_module("test_source_tools")


class Settled:
    """A genuine settled CP-4 head: the store, its final snapshot and the finished attempt."""

    def __init__(self, store: Execution, snapshot: ExecutionSnapshot, attempt: Attempt) -> None:
        self.store, self.snapshot, self.attempt = store, snapshot, attempt


@pytest.fixture(scope="module")
def settled(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Settled]:
    store = source_tools.legal_history(tmp_path_factory.mktemp("legal-history"))
    first = store.begin("CP-4")
    upstream = cp4_legal.upstream_of(store, first)
    literal = json.dumps(stage1.SUBMISSIONS["positive"]["legal_covenants"])
    # Attempt 0 is rejected (the figure placeholder is unresolved); the repair is attempt 1, so a
    # probe that rebuilt the head with a constant attempt number 0 cannot pass.
    rejected = cp4_legal.submit_cp4_step(store, first.ticket_id, "legal_covenants", literal)
    assert rejected.status == "finished" and rejected.issues
    begun = store.begin("CP-4")
    assert begun.number == 1
    text = literal.replace(stage1.FIG, stage1.select_metric(store.pack(), upstream))
    cp4_legal.submit_cp4_step(store, begun.ticket_id, "legal_covenants", text)
    final = store.read()
    attempt = next(a for a in final.attempts if a.ticket_id == begun.ticket_id)
    assert attempt.status == "finished" and not attempt.issues
    yield Settled(store, final, attempt)


def _refused(settled: Settled, attempt: Attempt | None = None) -> str:
    with pytest.raises(WorkflowError) as caught:
        cp4.probe(settled.store, settled.snapshot, attempt or settled.attempt)
    return caught.value.code


def test_probe_passes_on_the_honest_head(settled: Settled) -> None:
    cp4.probe(settled.store, settled.snapshot, settled.attempt)


def test_probe_refuses_a_forged_step_status(settled: Settled) -> None:
    (step,) = settled.attempt.steps
    forged = settled.attempt.model_copy(
        update={"steps": (step.model_copy(update={"status": "invalid"}),)}
    )
    assert _refused(settled, forged) == "identity_mismatch"


def test_probe_refuses_forged_output_bytes(
    settled: Settled, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = settled.store.step_output
    monkeypatch.setattr(
        settled.store, "step_output", lambda sha: real(sha).replace("Within threshold", "Breach")
    )
    assert _refused(settled) == "identity_mismatch"


def test_probe_refuses_a_forged_head_module(
    settled: Settled, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = settled.store.head_module

    def forged(head: Any) -> Any:
        module = real(head)
        if head.module_id != "CP-4":
            return module
        return module.model_copy(update={"limitations": (*module.limitations, "forged")})

    monkeypatch.setattr(settled.store, "head_module", forged)
    assert _refused(settled) == "identity_mismatch"


def test_probe_refuses_a_forged_attempt_number(settled: Settled) -> None:
    """The rebuilt candidate carries the attempt number, so a wrong one cannot match the head.
    The engine's module validator raises `ValueError` for number 2, which
    `verify_owner_run_receipt` maps to `identity_mismatch`; number 0 is a plain mismatch."""
    assert settled.attempt.number == 1
    for number in (0, 2):
        forged = settled.attempt.model_copy(update={"number": number})
        with pytest.raises((WorkflowError, ValueError)):
            cp4.probe(settled.store, settled.snapshot, forged)
