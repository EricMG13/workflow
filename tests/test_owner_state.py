"""The public `OwnerWorkflow.state()` (Part B O3+O4 Task 2, G5a).

Expectations come from the walk the test drives, never from `state()` itself. The multi-step module
is CP-1 on the S1 `positive` pack (`s1a_runs.start` / `drive_cp0`, under a second); the refusal
world is Task 1's G1-X fake (`CP-3D`) beside `CP-1C`. Each test takes well under a second.
"""

import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from deploy_vii.execution import Execution
from deploy_workflow.workflow import WorkflowError

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")
runs: Any = importlib.import_module("s1a_runs")
refusals: Any = importlib.import_module("test_owner_refusals")
view: Any = importlib.import_module("refusal_view")
cp3 = refusals.cp3  # the fixture: the G1-X fake registered as CP-3 / CP-3D
fake = refusals.fake


def _independent(workflow: Any) -> Any:
    """`OwnerState` built from the journal and the retained audit, not from `state()`."""
    root = workflow._store.directory
    snapshot = Execution(root).read()
    heads = []
    for head in snapshot.heads:
        attempt = next(
            a
            for a in snapshot.attempts
            if a.module_id == head.module_id and a.result_sha256 == head.result_sha256
        )
        heads.append(
            owner.SettledHead(
                module_id=head.module_id,
                ticket_id=attempt.ticket_id,
                result_sha256=head.result_sha256,
                status=head.status,
            )
        )
    kept = sorted(
        (
            owner.RefusedBegin.model_validate_json(p.read_bytes())
            for p in (root / owner.AUDIT / "refused-begin").glob("*")
        ),
        key=lambda r: workflow._plan.index(r.module_id),
    )
    active = workflow.phase == "analytical"
    binding = workflow.binding
    return owner.OwnerState(
        phase=workflow.phase,
        plan=workflow._plan,
        snapshot_sha256=snapshot.content_hash(),
        module_id=binding.module_id if active else None,
        step_id=binding.step_id if active else None,
        ticket_id=binding.ticket_id if active else None,
        attempt=binding.attempt if active else None,
        inputs_required=workflow.spec.inputs != "none" if active else False,
        inputs_read=any(r.binding == binding for r in workflow._reads) if active else False,
        invokes_used=sum(c.binding == binding for c in workflow._calls) if active else 0,
        reads_used=sum(r.binding == binding for r in workflow._reads) if active else 0,
        submits_used=sum(s.binding.binding == binding for s in workflow._submissions)
        if active
        else 0,
        settled=tuple(heads),
        refusals=tuple(kept),
    )


def test_state_after_create(tmp_path: Path) -> None:
    workflow, _ = runs.start("positive", tmp_path)
    state = workflow.state()
    assert state.schema_version == "owner-state/1"
    assert (state.module_id, state.attempt) == ("CP-0", 0)
    assert state.step_id == workflow.spec.step_id == workflow.binding.step_id
    assert state.ticket_id == workflow.binding.ticket_id
    assert state.inputs_required is (workflow.spec.inputs != "none")
    assert state.inputs_read is False
    assert (state.invokes_used, state.reads_used, state.submits_used) == (0, 0, 0)
    assert state.settled == () and state.refusals == ()
    assert state.phase == workflow.phase == "analytical"
    assert state.plan == workflow._plan
    assert state.snapshot_sha256 == workflow._store.read().content_hash()


def test_counters_reset_on_the_next_step_of_a_multi_step_module(tmp_path: Path) -> None:
    workflow, pack = runs.start("positive", tmp_path)
    runs.drive_cp0(workflow, pack, "positive")
    assert workflow.state().module_id == "CP-1"
    assert "CP-0" in [h.module_id for h in workflow.state().settled]
    context = runs.literal("positive", "cp1_source_context", pack)
    runs.read_cited(workflow, context)
    runs.search(workflow, "financial", "subsequent")
    runs.search(workflow, "business", "acquisition")
    mid = workflow.state()
    assert mid.invokes_used == len(workflow._epoch_calls) > 2
    outcome = runs.submit_valid(workflow, context)
    after = workflow.state()
    assert outcome["next_step"] == after.step_id != mid.step_id
    assert after.module_id == "CP-1"
    assert (after.invokes_used, after.reads_used, after.submits_used) == (0, 0, 0)
    assert after.inputs_read is False
    assert after.inputs_required is (workflow.spec.inputs != "none")


def test_reads_and_invokes_are_counted_and_inputs_read_is_per_binding(tmp_path: Path) -> None:
    workflow, pack = runs.start("positive", tmp_path)
    runs.drive_cp0(workflow, pack, "positive")
    context = runs.literal("positive", "cp1_source_context", pack)
    runs.read_cited(workflow, context)
    runs.search(workflow, "financial", "subsequent")
    runs.search(workflow, "business", "acquisition")
    runs.submit_valid(workflow, context)
    fw = runs._fw()
    fw.financial_reads(workflow)  # the financials step needs no inputs
    assert workflow.state().inputs_required is False
    runs.submit_valid(workflow, json.dumps(fw.financials(pack)))
    assert workflow.state().inputs_required is True and workflow.state().inputs_read is False
    workflow.read_inputs()
    page = {"source_id": "financial", "first_page": 1, "last_page": 1}
    workflow.invoke("read_pages", page)  # the narrative step offers no source tool: refused,
    workflow.invoke("read_pages", page)  # yet each call is counted
    state = workflow.state()
    assert (state.reads_used, state.invokes_used, state.inputs_read) == (1, 2, True)
    assert state == _independent(workflow)


def test_invalid_first_submit_keeps_the_step_and_counts_it(tmp_path: Path) -> None:
    """CP-1's financials step: an invalid first try is repaired within the same attempt, so the
    ticket and step stay and the submit is counted."""
    workflow, pack = runs.start("positive", tmp_path)
    runs.drive_cp0(workflow, pack, "positive")
    context = runs.literal("positive", "cp1_source_context", pack)
    runs.read_cited(workflow, context)
    runs.search(workflow, "financial", "subsequent")
    runs.search(workflow, "business", "acquisition")
    runs.submit_valid(workflow, context)
    runs._fw().financial_reads(workflow)
    before = workflow.state()
    assert before.submits_used == 0
    assert workflow.submit_review("{}")["status"] == "invalid"
    after = workflow.state()
    assert (after.module_id, after.step_id) == ("CP-1", before.step_id)
    assert after.ticket_id == before.ticket_id and after.submits_used == 1
    assert [h.module_id for h in after.settled] == ["CP-0"]


def test_invalid_cp0_submit_opens_a_repair_attempt_with_fresh_counters(tmp_path: Path) -> None:
    """CP-0 is one step: an invalid try settles attempt 0 and begins attempt 1 on a new ticket,
    whose counters start at 0 (the limits are per ticket and step)."""
    workflow, _ = runs.start("positive", tmp_path)
    before = workflow.state()
    assert workflow.submit_review("{}")["status"] == "invalid"
    after = workflow.state()
    assert (after.module_id, after.step_id) == ("CP-0", before.step_id)
    assert (before.attempt, after.attempt) == (0, 1)
    assert after.ticket_id != before.ticket_id and after.submits_used == 0
    assert after.settled == ()


def test_settled_module_is_listed(tmp_path: Path) -> None:
    workflow, pack = runs.start("positive", tmp_path)
    runs.drive_cp0(workflow, pack, "positive")
    state = workflow.state()
    assert [h.module_id for h in state.settled] == ["CP-0"]
    assert state.settled[0].status == "restricted"  # the S1 positive CP-0 head
    assert state == _independent(workflow)


def test_refusal_world_lists_the_refusal_with_missing_inputs(
    fake: SimpleNamespace, tmp_path: Path
) -> None:
    workflow = refusals._completed(fake, tmp_path)
    state = workflow.state()
    assert state.phase == workflow.phase == "complete"
    assert [r.module_id for r in state.refusals] == [refusals.B]
    assert state.refusals[0].missing_inputs == ("CP-1",)
    assert state.refusals[0].missing_commands == ()
    assert state.module_id is None and state.step_id is None and state.attempt is None
    assert state == _independent(workflow)


def test_consecutive_refusals_are_listed_in_walk_order(
    fake: SimpleNamespace, tmp_path: Path
) -> None:
    workflow = refusals._walk(fake, tmp_path, ("CP-0", "CP-1", refusals.A, refusals.B), refusals.A)
    got = [
        (r.module_id, list(r.missing_inputs), list(r.missing_commands))
        for r in workflow.state().refusals
    ]
    assert got == [
        (refusals.A, [], [f"Run {refusals.A}"]),
        (refusals.B, ["CP-1"], []),
    ]
    assert workflow.state() == _independent(workflow)


def test_state_on_a_sealed_workflow_returns_and_matches_the_receipt(
    fake: SimpleNamespace, tmp_path: Path
) -> None:
    workflow = refusals._completed(fake, tmp_path)
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    with pytest.raises(WorkflowError):  # sealed: the other methods refuse
        workflow.read_inputs()
    state = workflow.state()
    assert state.phase == "complete"
    assert tuple(state.settled) == receipt.heads
    assert view.of_receipt(state) == view.of_receipt(receipt)
    assert state.snapshot_sha256 == receipt.snapshot_sha256
    assert state == _independent(workflow)


def test_state_works_on_a_stale_instance(tmp_path: Path) -> None:
    """`state()` never calls `_current()`: a journal moved behind the instance's back does not
    make it raise (`open()` relies on this), while `read_inputs` would raise `stale_binding`."""
    workflow, _ = runs.start("positive", tmp_path)
    store = Execution(workflow._store.directory)
    store.interrupt(workflow.binding.ticket_id, "moved behind the instance")  # moves the journal
    with pytest.raises(WorkflowError, match="stale_binding"):
        workflow.invoke("read_pages", {"source_id": "x", "first_page": 1, "last_page": 1})
    assert workflow.state().snapshot_sha256 == workflow._store.read().content_hash()


def test_state_refuses_while_another_operation_holds_the_lock(tmp_path: Path) -> None:
    workflow, _ = runs.start("positive", tmp_path)
    with workflow._operation, pytest.raises(WorkflowError, match="not_permitted"):
        workflow.state()
    assert workflow.state().module_id == "CP-0"  # released after a refusal


def test_state_exposes_no_payload_or_body_text(tmp_path: Path) -> None:
    workflow, pack = runs.start("positive", tmp_path)
    payload = runs.literal("positive", "readiness_review", pack)
    runs.read_cited(workflow, payload)
    call_body = workflow._calls[-1].body
    runs.submit_valid(workflow, payload)
    dumped = workflow.state().model_dump_json()
    assert payload[:80] not in dumped
    assert call_body is None or str(call_body)[:80] not in dumped
    assert set(json.loads(dumped)) == set(owner.OwnerState.model_fields)


def test_state_is_a_fresh_immutable_value(tmp_path: Path) -> None:
    workflow, _ = runs.start("positive", tmp_path)
    first, second = workflow.state(), workflow.state()
    assert first == second and first is not second
    with pytest.raises(Exception):  # noqa: B017 - pydantic frozen model, any ValidationError
        first.phase = "x"
