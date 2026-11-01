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
from pydantic import ValidationError

from deploy_vii.execution import Execution
from deploy_workflow.workflow import WorkflowError

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")
runs: Any = importlib.import_module("s1a_runs")
refusals: Any = importlib.import_module("test_owner_refusals")
view: Any = importlib.import_module("refusal_view")
cp3 = refusals.cp3  # the fixture: the G1-X fake registered as CP-3 / CP-3D
fake = refusals.fake


def _retained(root: Path, kind: str, model: Any) -> list[Any]:
    directory = root / owner.AUDIT / kind
    return [model.model_validate_json(p.read_bytes()) for p in directory.glob("*")]


def _independent(workflow: Any) -> Any:
    """`OwnerState` built from disk only: `store.read()` and `owner-run-audit/`.

    The active ticket is the journal's one pending attempt and its step the first not yet valid
    in the module's declared chain. Counters are per `(ticket_id, step_id)` over the retained
    calls, input reads and submissions (never per full binding: its `snapshot_sha256` moves on a
    repair); `inputs_read` is a retained read of that ticket and step on the journal's current
    snapshot. `phase` and `plan` are the instance's (they are not on disk), and `stale` is False.

    A submit refused before the required read (R1a) is charged and written nowhere, so the
    oracle sees everything `state()` counts."""
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
        _retained(root, "refused-begin", owner.RefusedBegin),
        key=lambda r: workflow._plan.index(r.module_id),
    )
    pending = [a for a in snapshot.attempts if a.status == "pending"]
    common: dict[str, Any] = {
        "phase": workflow.phase,
        "plan": workflow._plan,
        "snapshot_sha256": snapshot.content_hash(),
        "stale": False,
        "settled": tuple(heads),
        "refusals": tuple(kept),
    }
    if workflow.phase != "analytical":
        assert not pending
        return owner.OwnerState(
            **common,
            module_id=None,
            step_id=None,
            ticket_id=None,
            attempt=None,
            inputs_required=False,
            inputs_read=False,
            invokes_used=0,
            reads_used=0,
            submits_used=0,
        )
    (attempt,) = pending
    steps = owner.OWNER_SPECS[attempt.module_id].steps
    spec = steps[sum(s.status == "valid" for s in attempt.steps)]
    key = (attempt.ticket_id, spec.step_id)
    reads = [
        r for r in _retained(root, "input-reads", owner.OwnerInputRead) if _of(r.binding) == key
    ]
    return owner.OwnerState(
        **common,
        module_id=attempt.module_id,
        step_id=spec.step_id,
        ticket_id=attempt.ticket_id,
        attempt=attempt.number,
        inputs_required=spec.inputs != "none",
        inputs_read=any(r.binding.snapshot_sha256 == snapshot.content_hash() for r in reads),
        invokes_used=sum(_of(c.binding) == key for c in _retained(root, "calls", owner.OwnerCall)),
        reads_used=len(reads),
        submits_used=sum(
            _of(m.binding.binding) == key
            for m in _retained(root, "submissions", owner.OwnerSubmission)
        ),
    )


def _of(binding: Any) -> tuple[str, str]:
    return binding.ticket_id, binding.step_id


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
    assert state.stale is False
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
    assert mid.stale is False and after.stale is False
    assert after == _independent(workflow)


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
    read = workflow.read_inputs()
    page = {"source_id": "financial", "first_page": 1, "last_page": 1}
    workflow.invoke("read_pages", page)  # the narrative step offers no source tool: refused,
    workflow.invoke("read_pages", page)  # yet each call is counted
    state = workflow.state()
    assert (state.reads_used, state.invokes_used, state.inputs_read) == (1, 2, True)
    assert state == _independent(workflow)
    runs.submit_valid(workflow, json.dumps(fw.narrative(read)))
    readiness = workflow.state()  # the next step requires inputs: its own read is still to come
    assert readiness.step_id != state.step_id and readiness.ticket_id == state.ticket_id
    assert readiness.inputs_required is True and readiness.inputs_read is False
    assert readiness.reads_used == 0
    workflow.read_inputs()
    assert workflow.state().inputs_read is True
    assert workflow.state() == _independent(workflow)


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
    assert after.stale is False
    assert after == _independent(workflow)  # the repair moved the binding's snapshot, not the count


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


def test_submit_before_the_required_read_is_refused_and_not_counted(tmp_path: Path) -> None:
    """R1a (amends R1): a submit before the required read is a precondition refusal. It is not
    charged to the submit cap and writes nothing, so `state()` and the disk oracle agree."""
    workflow, pack = runs.start("positive", tmp_path)
    runs.drive_cp0(workflow, pack, "positive")
    context = runs.literal("positive", "cp1_source_context", pack)
    runs.read_cited(workflow, context)
    runs.search(workflow, "financial", "subsequent")
    runs.search(workflow, "business", "acquisition")
    runs.submit_valid(workflow, context)
    fw = runs._fw()
    fw.financial_reads(workflow)
    runs.submit_valid(workflow, json.dumps(fw.financials(pack)))
    assert workflow.state().inputs_required is True
    with pytest.raises(WorkflowError, match="not_permitted"):
        workflow.submit_review("{}")
    state = workflow.state()
    assert state.submits_used == 0 and state.inputs_read is False
    assert state == _independent(workflow)


def test_stale_flag_when_another_writer_interrupts_the_ticket(tmp_path: Path) -> None:
    """`state()` never calls `_current()`: a journal moved behind the instance does not make it
    raise (`open()` relies on this), while `invoke` raises `stale_binding`. The caller sees it in
    `stale`; the binding and counters are the instance's last view."""
    workflow, _ = runs.start("positive", tmp_path)
    assert workflow.state().stale is False
    store = Execution(workflow._store.directory)
    store.interrupt(workflow.binding.ticket_id, "moved behind the instance")  # moves the journal
    with pytest.raises(WorkflowError, match="stale_binding"):
        workflow.invoke("read_pages", {"source_id": "x", "first_page": 1, "last_page": 1})
    state = workflow.state()
    assert state.stale is True
    assert state.snapshot_sha256 == store.read().content_hash()
    assert state.module_id == "CP-0" and state.ticket_id == workflow.binding.ticket_id


def test_stale_flag_when_another_writer_settles_the_module(tmp_path: Path) -> None:
    workflow, pack = runs.start("positive", tmp_path)
    other = Execution(workflow._store.directory)
    owner.submit_cp0_review(
        other, workflow.binding.ticket_id, runs.literal("positive", "readiness_review", pack)
    )
    state = workflow.state()
    assert state.stale is True
    assert "CP-0" in [h.module_id for h in state.settled]  # the journal's view
    assert state.module_id == "CP-0"  # the instance's last binding, as `stale` says


def test_stale_is_false_at_each_checkpoint_of_a_walk(tmp_path: Path) -> None:
    workflow, pack = runs.start("positive", tmp_path)
    assert workflow.state().stale is False
    runs.drive_cp0(workflow, pack, "positive")
    assert workflow.state().stale is False
    assert workflow.submit_review("{}")["status"] == "invalid"  # CP-1 context: a repair
    assert workflow.state().stale is False


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
    with pytest.raises(ValidationError):  # the model is frozen
        first.phase = "x"


def test_stale_is_true_in_the_inactive_branch_at_the_cp_model_stop(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    """R3, the branch of `state()` taken when no module is active: the phase is `walked` at the
    CP-MODEL stop and another writer begins the next module (L1, Task 2 re-review)."""
    order = ("CP-0", "CP-1", "CP-MODEL", refusals.g1x.MODULE)
    workflow = refusals.order_tests._terminal_world(cp3, tmp_path, order)
    assert workflow.phase == "walked" and workflow.state().stale is False
    Execution(workflow._store.directory).begin(refusals.g1x.MODULE)  # moves the journal
    state = workflow.state()
    assert state.phase == "walked" and state.module_id is None
    assert state.stale is True
    assert state.snapshot_sha256 == Execution(workflow._store.directory).read().content_hash()
    with pytest.raises(WorkflowError, match="stale_binding"):
        workflow.publish()
