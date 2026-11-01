"""`OwnerWorkflow.open()` resumes a killed run from the retained audit (Part B O3 Task 3a, G5b).

A kill is the first `OwnerWorkflow` abandoned (never used again) and a second built by `open()` on
the same directory. The scripted worlds are fast: CP-0, CP-1 blocked by four empty submissions
(about 0.5 s, no promotion) and the G1-X fake owner module (`CP-3D`), with the CP-MODEL stop where
`publish` refuses terminally. The one kill point that needs a published CP-MODEL (between
`publish` and the publications retain, F4 (c)) needs a real CP-1 promotion (11-26 min) and is
gated behind `RUN_PROMOTION`; its detection branch is also driven fast on a forged journal tail.

Ids: tickets and calls are `uuid4`, so two runs never share one, and the hashes that embed them
differ too. `_normal` renames every uuid and every 64-hex digest by order of first appearance
(L4) before two receipts are compared.
"""

import importlib
import io
import json
import os
import re
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from deploy_vii.execution import Attempt, Execution
from deploy_workflow.workflow import WorkflowError

owner: Any = importlib.import_module("deploy_workflow.owner_workflow")
g1x: Any = importlib.import_module("test_owner_g1x")
order_tests: Any = importlib.import_module("test_owner_order")
refusals: Any = importlib.import_module("test_owner_refusals")
financial: Any = importlib.import_module("test_financial_workflow")
runs: Any = importlib.import_module("s1a_runs")
state_tests: Any = importlib.import_module("test_owner_state")
cp3 = order_tests.cp3  # the fixture: the G1-X fake registered as CP-3 / CP-3D

A = g1x.MODULE
B = refusals.B
REFUSAL_ORDER = ("CP-0", "CP-1", B, A)
STOP_ORDER = ("CP-0", "CP-1", "CP-MODEL", A)
Action = tuple[str, Callable[[Any], None]]


# --- helpers ----------------------------------------------------------------------------------

_ID = re.compile(r"[0-9a-f]{64}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def _normal(receipt: Any) -> str:
    """The receipt with every uuid and digest renamed by position of first appearance."""
    names: dict[str, str] = {}

    def rename(match: re.Match[str]) -> str:
        return names.setdefault(match[0], f"<{len(names)}>")

    return _ID.sub(rename, receipt.model_dump_json())


def _view(workflow: Any) -> tuple[Any, ...]:
    """Everything an instance holds that a resume must rebuild: `state()` and the private fields it
    does not show (adversary I2)."""
    return (
        workflow.state(),
        workflow.phase,
        tuple(workflow._begins),
        tuple(workflow._refusals),
        tuple(workflow._calls),
        tuple(workflow._reads),
        tuple(workflow._submissions),
        tuple(workflow._publications),
        len(workflow._publications),
        workflow._publisher_done,
        workflow._resume_after,
        workflow._model,
        workflow._refusal_kind,
        # with no module active the last epoch is history that no method reads
        tuple(workflow._epoch_calls) if workflow.phase == "analytical" else (),
        dict(+workflow._limits),
        workflow._sealed,
        workflow._current_sha256,
    )


def _pages(workflow: Any) -> None:
    for source in ("identity", "financial"):
        workflow.invoke("read_pages", {"source_id": source, "first_page": 1, "last_page": 1})


def _search(workflow: Any) -> None:
    workflow.invoke("search_pack", {"query": "subsequent", "source_id": "financial"})


def _ok(outcome: dict[str, Any]) -> None:
    assert outcome["status"] in ("valid", "invalid", "ok", "refused"), outcome


def _unread_submit(workflow: Any) -> None:
    with pytest.raises(WorkflowError) as caught:
        workflow.submit_review(g1x._sourced())
    assert caught.value.code == "not_permitted"


def _actions(pack: Any, *, publish: bool) -> list[Action]:
    """CP-0, CP-1 blocked by four empty submissions, an optional `publish`, then the fake module's
    two steps, one action per tool call so that a kill can fall between any two."""
    actions: list[Action] = [
        ("sources", lambda w: financial.read_sources(w)),
        ("cp0", lambda w: _ok(w.submit_review(refusals._review(pack)))),
    ]
    for n in range(4):
        actions += [
            (f"cp1 pages {n}", _pages),
            (f"cp1 search {n}", _search),
            (f"cp1 invalid {n}", lambda w: _ok(w.submit_review("{}"))),
        ]
    if publish:
        actions.append(("publish", lambda w: _ok(w.publish())))
    actions += [
        ("a unread submit", _unread_submit),
        ("a inputs", lambda w: w.read_inputs()),
        ("a page", g1x._read_page),
        ("a sourced", lambda w: _ok(w.submit_review(g1x._sourced()))),
        ("a viewed inputs", lambda w: w.read_inputs()),
        ("a viewed", lambda w: _ok(w.submit_review(g1x._viewed()))),
    ]
    return actions


def _build(fake: SimpleNamespace, root: Path, order: tuple[str, ...], publish: bool) -> Any:
    fake.monkeypatch.setattr(owner, "plan", lambda requested: order)
    pack = order_tests._financial_pack(B)
    workflow = owner.OwnerWorkflow.create(
        root / "store", pack, specs=owner.OWNER_SPECS, publication_directory=root / "model"
    )
    return workflow, _actions(pack, publish=publish)


def _open(root: Path) -> Any:
    return owner.OwnerWorkflow.open(
        root / "store", specs=owner.OWNER_SPECS, publication_directory=root / "model"
    )


def _control(fake: SimpleNamespace, root: Path, order: tuple[str, ...], publish: bool) -> Any:
    workflow, actions = _build(fake, root, order, publish)
    for _, act in actions:
        act(workflow)
    assert workflow.phase == "complete"
    return workflow.write_receipt(root / "receipt.json")


def _kill_and_resume(
    fake: SimpleNamespace, tmp_path: Path, order: tuple[str, ...], publish: bool, kill: int
) -> None:
    control = _control(fake, tmp_path / "control", order, publish)
    root = tmp_path / "run"
    killed, actions = _build(fake, root, order, publish)
    for _, act in actions[:kill]:
        act(killed)
    before = _view(killed)
    label = actions[kill - 1][0] if kill else "create"
    del killed  # abandoned: never used again
    resumed = _open(root)
    assert _view(resumed) == before, label
    if resumed.phase == "analytical":
        assert resumed.state() == state_tests._independent(resumed)
    for _, act in actions[kill:]:
        act(resumed)
    receipt = resumed.write_receipt(root / "receipt.json")
    owner.verify_owner_run_receipt(Execution(root / "store"), receipt)
    assert _normal(receipt) == _normal(control), label


def _points(publish: bool) -> list[Any]:
    names = [
        "create",
        *(label for label, _ in _actions(order_tests._financial_pack(B), publish=publish)),
    ]
    return [pytest.param(i, id=f"{i:02d}-{name}") for i, name in enumerate(names)]


# --- Step 0: the SourceSession spike (Q3) ------------------------------------------------------


def test_spike_a_session_rebuilt_by_replay_binds_the_same_submission(tmp_path: Path) -> None:
    """`SourceSession` keeps its calls in memory (`host.py` `_calls`), so a fresh session starts at
    sequence 0 with new call ids. Replaying the retained epoch through the public `invoke` (the
    verifier's own method) reproduces every receipt but its `call_id` and the evidence the session
    accumulates; `open()` keeps the retained ids by remapping them. The kill is after the CP-0
    reads and before the submit, and the resumed submit binds, verifies and settles."""
    workflow, pack = runs.start("positive", tmp_path)
    payload = runs.literal("positive", "readiness_review", pack)
    runs.read_cited(workflow, payload)
    assert workflow._epoch_calls
    before = _view(workflow)
    del workflow
    resumed = owner.OwnerWorkflow.open(tmp_path / "store", publication_directory=tmp_path / "model")
    assert _view(resumed) == before
    assert resumed._session is not None
    assert (
        resumed.invoke("search_pack", {"query": "financial", "source_id": "financial"})["sequence"]
        == len(before[13]) + 1
    )  # the session's sequence continues after the replayed epoch
    runs.submit_valid(resumed, payload)
    assert resumed.state().settled[0].module_id == "CP-0"


# --- control and kill points -------------------------------------------------------------------


@pytest.mark.parametrize("kill", _points(publish=False))
def test_kill_anywhere_in_the_refusal_world_resumes_to_the_control_receipt(
    cp3: SimpleNamespace, tmp_path: Path, kill: int
) -> None:
    """Every point between two actions of a world with a refusal (CP-1C refused by the blocked
    CP-1, then the fake module): after create, after the reads, after an invalid first submit,
    between the two steps of a module, after module 1 settled, after the refusal, after a submit
    refused for an unread step."""
    _kill_and_resume(cp3, tmp_path, REFUSAL_ORDER, False, kill)


@pytest.mark.parametrize("kill", _points(publish=True))
def test_kill_anywhere_in_the_cp_model_stop_world_resumes_to_the_control_receipt(
    cp3: SimpleNamespace, tmp_path: Path, kill: int
) -> None:
    """The O1 tip: the walk stops at CP-MODEL (CP-1 blocked), `publish` refuses terminally and the
    module planned after it runs. Kills fall before the stop, at the stop and after it."""
    _kill_and_resume(cp3, tmp_path, STOP_ORDER, True, kill)


def test_open_changes_nothing_on_disk_when_the_audit_is_consistent(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    workflow, actions = _build(cp3, tmp_path, REFUSAL_ORDER, False)
    for _, act in actions[:6]:
        act(workflow)
    tree = g1x._tree(tmp_path)
    _open(tmp_path)
    assert g1x._tree(tmp_path) == tree


def test_open_twice_rebuilds_the_same_instance(cp3: SimpleNamespace, tmp_path: Path) -> None:
    workflow, actions = _build(cp3, tmp_path, REFUSAL_ORDER, False)
    for _, act in actions[:10]:
        act(workflow)
    assert _view(_open(tmp_path)) == _view(_open(tmp_path)) == _view(workflow)


def test_submit_before_read_inputs_is_uncharged_and_writes_nothing(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    """R1a (adversary H1): a submit before `read_inputs` is a precondition refusal. It is not
    charged to the submit cap and writes nothing (CP-1D lease: "nothing written"), so a resume
    has nothing to rebuild and the disk oracle agrees with `state()`."""
    workflow, actions = _build(cp3, tmp_path, REFUSAL_ORDER, False)
    for _, act in actions:
        if act is _unread_submit:
            break
        act(workflow)
    before = g1x._tree(tmp_path / "store")
    _unread_submit(workflow)
    _unread_submit(workflow)
    assert g1x._tree(tmp_path / "store") == before
    assert workflow.state().submits_used == 0
    resumed = _open(tmp_path)
    assert resumed.state().submits_used == 0
    assert resumed.state() == state_tests._independent(resumed)


def test_per_step_caps_still_bind_after_open(tmp_path: Path) -> None:
    workflow, _ = runs.start("positive", tmp_path)
    page = {"source_id": "identity", "first_page": 1, "last_page": 1}
    for _ in range(owner.MAX_CALLS):
        workflow.invoke("read_pages", page)
    del workflow
    resumed = owner.OwnerWorkflow.open(tmp_path / "store", publication_directory=tmp_path / "model")
    assert resumed.state().invokes_used == owner.MAX_CALLS
    with pytest.raises(WorkflowError) as caught:
        resumed.invoke("read_pages", page)
    assert caught.value.code == "not_permitted"


# --- refusals ----------------------------------------------------------------------------------


def test_open_refuses_a_directory_with_no_current(tmp_path: Path) -> None:
    with pytest.raises(WorkflowError) as caught:
        owner.OwnerWorkflow.open(tmp_path / "absent")
    assert caught.value.code == "not_permitted"
    (tmp_path / "empty").mkdir()
    with pytest.raises(WorkflowError) as caught:
        owner.OwnerWorkflow.open(tmp_path / "empty")
    assert caught.value.code == "not_permitted"


def test_open_refuses_specs_other_than_the_plans_as_create_does(tmp_path: Path) -> None:
    runs.start("positive", tmp_path)
    forged = dict(owner.OWNER_SPECS)
    forged["CP-0"] = forged["CP-0"].__class__(
        **{**forged["CP-0"].__dict__, "kind": "deterministic"}
    )
    with pytest.raises(WorkflowError) as caught:
        owner.OwnerWorkflow.open(
            tmp_path / "store", specs=forged, publication_directory=tmp_path / "model"
        )
    assert caught.value.code == "not_permitted"
    with pytest.raises(WorkflowError) as missing_output:  # a plan with CP-MODEL needs its output
        owner.OwnerWorkflow.open(tmp_path / "store")
    assert missing_output.value.code == "not_permitted"


def test_open_refuses_an_existing_output_until_a_publication_is_recorded(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    """P12: `create` refuses an existing output directory. `open()` keeps that refusal while no
    publication is recorded, and drops it once one is (the output is then the run's own)."""
    workflow, actions = _build(cp3, tmp_path, STOP_ORDER, True)
    for _, act in actions[:12]:
        act(workflow)
    (tmp_path / "model").mkdir()
    with pytest.raises(WorkflowError) as caught:
        _open(tmp_path)
    assert caught.value.code == "not_permitted"
    (tmp_path / "model").rmdir()
    _view(_open(tmp_path))
    names = [label for label, _ in actions]
    for _, act in actions[12 : names.index("publish") + 1]:
        act(workflow)
    (tmp_path / "model").mkdir()
    assert _open(tmp_path).phase == "analytical"  # a publication is recorded: the output is allowed


def test_open_on_a_sealed_directory_is_complete_and_refuses_to_write(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    _control(cp3, tmp_path, REFUSAL_ORDER, False)
    resumed = _open(tmp_path)
    assert resumed.state().phase == "complete"
    assert resumed._sealed is True
    with pytest.raises(WorkflowError) as caught:
        resumed.write_receipt(tmp_path / "again.json")
    assert caught.value.code == "not_permitted"
    with pytest.raises(WorkflowError):
        resumed.invoke("read_pages", {"source_id": "x", "first_page": 1, "last_page": 1})


# --- F4: the journal and the audit disagree ----------------------------------------------------


def _faults(root: Path) -> list[Any]:
    found: list[Any] = state_tests._retained(root / "store", "faults", owner.OwnerFault)
    return found


def test_a_torn_audit_is_a_named_error_with_a_fault_record(tmp_path: Path) -> None:
    assert issubclass(owner.TornAudit, WorkflowError)
    runs.start("positive", tmp_path)
    store = Execution(tmp_path / "store")
    # a binding retained for a submit that never reached the journal: the stray record
    binding = owner.OwnerSubmissionBinding(
        binding=owner._owner_binding(store.read(), store.read().attempts[0], "source_readiness"),
        payload_sha256="1" * 64,
        successful_call_ids=(),
        call_ids=(),
        source_evidence=owner.SourceEvidence(),
    )
    owner._retain(store, "bindings", binding)
    with pytest.raises(owner.TornAudit) as caught:
        owner.OwnerWorkflow.open(tmp_path / "store", publication_directory=tmp_path / "model")
    assert caught.value.code == "identity_mismatch"
    (fault,) = _faults(tmp_path)
    assert (fault.code, fault.kind, fault.digest) == (
        "torn_audit",
        "bindings",
        binding.content_hash(),
    )


def test_a_transition_without_its_record_is_torn(cp3: SimpleNamespace, tmp_path: Path) -> None:
    """A gap in the middle of the chain (the begin of CP-1's ticket has no `begins` record) is not
    rebuilt: only the last transition can be."""
    workflow, actions = _build(cp3, tmp_path, REFUSAL_ORDER, False)
    for _, act in actions[:5]:
        act(workflow)
    record = workflow._begins[1]
    (tmp_path / "store" / owner.AUDIT / "begins" / record.content_hash()).unlink()
    with pytest.raises(owner.TornAudit) as caught:
        _open(tmp_path)
    assert caught.value.code == "identity_mismatch"
    assert _faults(tmp_path)[0].kind == "journal"


def test_a_record_naming_no_snapshot_of_the_chain_is_torn(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    workflow, actions = _build(cp3, tmp_path, REFUSAL_ORDER, False)
    for _, act in actions[:2]:
        act(workflow)
    forged = workflow._begins[0].model_copy(update={"snapshot_after_sha256": "2" * 64})
    owner._retain(workflow._store, "begins", forged)
    with pytest.raises(owner.TornAudit):
        _open(tmp_path)
    assert {f.kind for f in _faults(tmp_path)} == {"begins"}


def test_a_retained_record_that_is_not_its_own_digest_is_torn(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    workflow, actions = _build(cp3, tmp_path, REFUSAL_ORDER, False)
    for _, act in actions[:2]:
        act(workflow)
    path = tmp_path / "store" / owner.AUDIT / "calls" / workflow._calls[0].content_hash()
    path.write_bytes(path.read_bytes().replace(b'"ok"', b'"error"'))
    with pytest.raises(owner.TornAudit):
        _open(tmp_path)
    assert _faults(tmp_path)[0].kind == "calls"


def _until_it_raises(workflow: Any, actions: list[Action], error: type[BaseException]) -> int:
    """Run the actions until one raises `error`; its index."""
    for index, (_, act) in enumerate(actions):
        try:
            act(workflow)
        except error:
            return index
    raise AssertionError("no action raised")


def test_kill_between_store_begin_and_the_begins_retain_rebuilds_the_record(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F4 (b): CP-1's second invalid try settles attempt 0 and begins attempt 1, then the `begins`
    retain fails: the journal holds the attempt, the audit no `BeginRecord`. `open()` rebuilds it
    from the two snapshots and retains it; the run finishes and its receipt equals the control."""
    control = _control(cp3, tmp_path / "control", REFUSAL_ORDER, False)
    root = tmp_path / "run"
    workflow, actions = _build(cp3, root, REFUSAL_ORDER, False)
    real = owner._retain

    def failing(store: Any, kind: str, value: Any) -> None:
        if kind == "begins" and value.module_id == "CP-1" and value.attempt == 1:
            raise OSError("probe: killed before the begins retain")
        real(store, kind, value)

    monkeypatch.setattr(owner, "_retain", failing)
    killed = _until_it_raises(workflow, actions, OSError)
    monkeypatch.setattr(owner, "_retain", real)
    assert actions[killed][0].startswith("cp1 invalid")
    on_disk = state_tests._retained(root / "store", "begins", owner.BeginRecord)
    assert [(b.module_id, b.attempt) for b in on_disk].count(("CP-1", 1)) == 0
    assert any(a.module_id == "CP-1" and a.number == 1 for a in workflow._store.read().attempts)
    del workflow
    resumed = _open(root)
    rebuilt = state_tests._retained(root / "store", "begins", owner.BeginRecord)
    assert [(b.module_id, b.attempt) for b in rebuilt].count(("CP-1", 1)) == 1
    assert [(b.module_id, b.attempt) for b in resumed._begins][:3] == [
        ("CP-0", 0),
        ("CP-1", 0),
        ("CP-1", 1),
    ]
    for _, act in actions[killed + 1 :]:
        act(resumed)
    receipt = resumed.write_receipt(root / "receipt.json")
    assert _normal(receipt) == _normal(control)


def _window_a(
    fake: SimpleNamespace, root: Path, monkeypatch: pytest.MonkeyPatch, *, times: int = 1
) -> tuple[list[Action], int, dict[str, int]]:
    """CP-0's validator raises on its first `times` calls: the first inside `submit_review` (the
    kill), any further ones inside a later `open()`."""
    workflow, actions = _build(fake, root, REFUSAL_ORDER, False)
    cp0: Any = importlib.import_module("deploy_vii.cp0_workflow")
    real = cp0._validate_review
    calls = {"n": 0}

    def flaky(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        if calls["n"] <= times:
            raise RuntimeError("probe: killed during validation")
        return real(*args, **kwargs)

    monkeypatch.setattr(cp0, "_validate_review", flaky)
    killed = _until_it_raises(workflow, actions, RuntimeError)
    assert actions[killed][0] == "cp0"
    return actions, killed, calls


def test_kill_during_validation_is_completed_by_open_itself(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F4 (a), R5: the validator raises after `submit_step` wrote the pending step. The journal
    holds a pending step, the audit its payload and binding but no `submissions` record. `open()`
    rebinds the step, replays the epoch and resubmits the retained payload itself: validation is
    finished when it returns, no caller sees the pending binding, and the receipt equals the
    control."""
    control = _control(cp3, tmp_path / "control", REFUSAL_ORDER, False)
    root = tmp_path / "run"
    actions, killed, _ = _window_a(cp3, root, monkeypatch)
    assert state_tests._retained(root / "store", "submissions", owner.OwnerSubmission) == []
    resumed = _open(root)
    assert resumed.state().stale is False
    assert [h.module_id for h in resumed.state().settled] == ["CP-0"]
    assert len(resumed._submissions) == 1 and resumed.state().module_id == "CP-1"
    assert not [
        a for a in resumed._store.read().attempts if a.steps and a.steps[0].status == "pending"
    ]
    for _, act in actions[killed + 1 :]:
        act(resumed)
    receipt = resumed.write_receipt(root / "receipt.json")
    assert _normal(receipt) == _normal(control)


def test_open_raises_when_validation_raises_again_and_a_later_open_resumes(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "run"
    actions, killed, calls = _window_a(cp3, root, monkeypatch, times=2)
    with pytest.raises(RuntimeError):  # the second raise, inside open()
        _open(root)
    assert calls["n"] == 2
    resumed = _open(root)  # window (a) is still found; the third validation succeeds
    assert [h.module_id for h in resumed.state().settled] == ["CP-0"]
    for _, act in actions[killed + 1 :]:
        act(resumed)
    owner.verify_owner_run_receipt(
        Execution(root / "store"), resumed.write_receipt(root / "receipt.json")
    )


def test_actions_after_a_window_a_open_are_those_of_an_uninterrupted_run(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R5 (adversary P3/P4, review P6): an extra `invoke` and a different payload after `open()`
    are accepted or refused as on an uninterrupted instance, a later `open()` still works, and the
    run seals."""
    root = tmp_path / "run"
    actions, _killed, _ = _window_a(cp3, root, monkeypatch)
    resumed = _open(root)
    page = {"source_id": "identity", "first_page": 1, "last_page": 1}
    assert resumed.invoke("read_pages", page)["status"] == "ok"
    assert resumed.submit_review("{}")["status"] == "invalid"  # CP-1's first invalid try
    again = _open(root)
    assert _view(again) == _view(resumed)
    for _, act in actions[[n for n, _ in actions].index("cp1 pages 1") :]:
        act(again)
    owner.verify_owner_run_receipt(
        Execution(root / "store"), again.write_receipt(root / "receipt.json")
    )


def test_a_gate_refused_submit_after_a_window_a_open_leaves_the_run_resumable(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fake module's sourced step: the validator raises once after the pending write. After
    `open()` completed it, the viewed step takes a submit its precheck gate refuses (recorded as a
    refused submission), and a later `open()` resumes and seals."""
    root = tmp_path / "run"
    workflow, actions = _build(cp3, root, REFUSAL_ORDER, False)
    real = g1x._validate
    calls = {"n": 0}

    def once(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("probe: killed during validation")
        return real(*args, **kwargs)

    monkeypatch.setattr(g1x, "_validate", once)
    killed = _until_it_raises(workflow, actions, RuntimeError)
    assert actions[killed][0] == "a sourced"
    del workflow
    resumed = _open(root)
    assert resumed.state().step_id == g1x.VIEWED
    resumed.read_inputs()
    assert resumed.submit_review(g1x._viewed(g1x.GATE_MARK))["status"] == "refused"
    again = _open(root)
    assert again.state().submits_used == 1
    for _, act in actions[killed + 2 :]:
        act(again)
    owner.verify_owner_run_receipt(
        Execution(root / "store"), again.write_receipt(root / "receipt.json")
    )


def test_a_pending_step_with_no_retained_binding_is_torn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow, pack = runs.start("positive", tmp_path)
    payload = runs.literal("positive", "readiness_review", pack)
    runs.read_cited(workflow, payload)
    cp0: Any = importlib.import_module("deploy_vii.cp0_workflow")

    def boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("probe: killed during validation")

    monkeypatch.setattr(cp0, "_validate_review", boom)
    with pytest.raises(RuntimeError):
        workflow.submit_review(payload)
    directory = tmp_path / "store" / owner.AUDIT / "bindings"
    for path in directory.iterdir():
        path.unlink()
    with pytest.raises(owner.TornAudit):
        owner.OwnerWorkflow.open(tmp_path / "store", publication_directory=tmp_path / "model")
    assert _faults(tmp_path)[0].kind == "journal"


def test_publisher_attempt_with_no_publication_record_is_torn(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    """F4 (c), detection branch, on a forged tail (a real `publish` needs a promoted CP-1): the
    journal holds a CP-MODEL attempt and the audit no `publications` record. A second `publish`
    would double-publish and the call record cannot be rebuilt, so `open()` refuses."""
    workflow, actions = _build(cp3, tmp_path, STOP_ORDER, True)
    names = [label for label, _ in actions]
    for _, act in actions[: names.index("publish")]:
        act(workflow)
    store = workflow._store
    snapshot = store.read()
    forged = Attempt(
        ticket_id="00000000-0000-4000-8000-000000000000",
        module_id="CP-MODEL",
        inputs=(),
        number=0,
    )
    store._write(
        snapshot.model_copy(
            update={"parent": snapshot.content_hash(), "attempts": (*snapshot.attempts, forged)}
        )
    )
    # R8: a real `publish` has written its output before the retain fails
    (tmp_path / "model").mkdir()
    (tmp_path / "model" / "model.html").write_text("published")
    with pytest.raises(owner.TornAudit) as caught:
        _open(tmp_path)
    assert caught.value.code == "identity_mismatch"
    assert _faults(tmp_path)[0].kind == "publications"


# --- fix round 1: R6 epoch-bound rebuild, R7 publish cap, R10 ---------------------------------


def _prefix(
    fake: SimpleNamespace,
    root: Path,
    upto: str,
    order: tuple[str, ...] = REFUSAL_ORDER,
    publish: bool = False,
) -> tuple[Any, list[Action], int]:
    workflow, actions = _build(fake, root, order, publish)
    stop = [label for label, _ in actions].index(upto)
    for _, act in actions[:stop]:
        act(workflow)
    return workflow, actions, stop


def _swap(store: Execution, kind: str, old: Any, new: Any) -> None:
    (store.directory / owner.AUDIT / kind / old.content_hash()).unlink()
    owner._retain(store, kind, new)


def _torn_kind(root: Path) -> str:
    with pytest.raises(owner.TornAudit) as caught:
        _open(root)
    assert caught.value.code == "identity_mismatch"
    (fault,) = _faults(root)
    assert fault.kind == caught.value.kind and fault.digest == caught.value.digest
    return str(fault.kind)


def test_a_call_injected_at_a_closed_binding_is_torn_at_open(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    """R6 (adversary P8/P9): CP-0's binding is closed by its submission, which lists its calls. A
    self-consistent extra call at that binding is listed by nothing and is not in the open epoch."""
    workflow, _, _ = _prefix(cp3, tmp_path, "cp1 pages 1")
    last = [c for c in workflow._calls if c.binding.module_id == "CP-0"][-1]
    extra = last.model_copy(
        update={"call_id": "9" * 8 + "-0000-4000-8000-" + "0" * 12, "sequence": last.sequence + 1}
    )
    owner._retain(workflow._store, "calls", extra)
    del workflow
    assert _torn_kind(tmp_path) == "calls"
    assert _faults(tmp_path)[0].digest == extra.content_hash()


def test_a_changed_call_body_at_a_closed_binding_is_torn_at_open(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    workflow, _, _ = _prefix(cp3, tmp_path, "cp1 pages 1")
    call = next(c for c in workflow._calls if c.binding.module_id == "CP-0" and c.status == "ok")
    forged = call.model_copy(update={"body": "forged body"})
    _swap(workflow._store, "calls", call, forged)
    del workflow
    assert _torn_kind(tmp_path) == "calls"
    assert _faults(tmp_path)[0].digest == forged.content_hash()


def test_changed_issues_of_a_closed_submission_are_torn_at_open(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    workflow, _, _ = _prefix(cp3, tmp_path, "cp1 pages 1")
    submission = workflow._submissions[0]
    forged = submission.model_copy(update={"issues": ("forged",)})
    _swap(workflow._store, "submissions", submission, forged)
    del workflow
    assert _torn_kind(tmp_path) == "submissions"


def test_the_verifier_refuses_a_call_no_submission_lists(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    """R6: `_verify_calls_reads` replays a call at a closed binding without asking a submission to
    list it, so a self-consistent extra call (the replay reproduces its body) was accepted."""
    receipt = _control(cp3, tmp_path, REFUSAL_ORDER, False)
    last = [c for c in receipt.calls if c.binding.module_id == "CP-0"][-1]
    extra = last.model_copy(
        update={"call_id": "8" * 8 + "-0000-4000-8000-" + "0" * 12, "sequence": last.sequence + 1}
    )
    owner._retain(Execution(tmp_path / "store"), "calls", extra)
    forged = receipt.model_copy(update={"calls": (*receipt.calls, extra)})
    g1x._reseal(tmp_path, forged)
    assert g1x._verdict(tmp_path, forged) == "identity_mismatch"
    assert g1x._verdict(tmp_path, receipt) in ("identity_mismatch", "accepted")  # not under test


def test_a_gap_in_the_open_epoch_names_the_call_after_the_gap(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    """I7: the fault names the offending record, not the epoch's first call."""
    workflow, _, _ = _prefix(cp3, tmp_path, "cp1 invalid 0")
    ordered = sorted(workflow._epoch_calls, key=lambda c: c.sequence)
    assert len(ordered) >= 3
    (tmp_path / "store" / owner.AUDIT / "calls" / ordered[1].content_hash()).unlink()
    del workflow
    assert _torn_kind(tmp_path) == "calls"
    assert _faults(tmp_path)[0].digest == ordered[2].content_hash()


def test_a_second_refusal_of_one_module_names_the_duplicate(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    workflow, _, _ = _prefix(cp3, tmp_path, "a inputs")
    (kept,) = workflow._refusals
    twin = kept.model_copy(update={"reason": kept.reason + " (again)"})
    owner._retain(workflow._store, "refused-begin", twin)
    later = max(kept.content_hash(), twin.content_hash())
    del workflow
    assert _torn_kind(tmp_path) == "refused-begin"
    assert _faults(tmp_path)[0].digest == later


def test_a_refusal_of_a_module_outside_the_walk_is_torn(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    workflow, _, _ = _prefix(cp3, tmp_path, "a inputs")
    (kept,) = workflow._refusals
    owner._retain(
        workflow._store, "refused-begin", kept.model_copy(update={"module_id": "CP-MODEL"})
    )
    del workflow
    assert _torn_kind(tmp_path) == "refused-begin"


def test_a_record_that_is_not_canonical_json_is_torn(cp3: SimpleNamespace, tmp_path: Path) -> None:
    """Named by its digest and parsing, but not the bytes `_retain` writes (the verifier compares
    bytes): torn at open."""
    workflow, _, _ = _prefix(cp3, tmp_path, "cp1 pages 1")
    begin = workflow._begins[0]
    path = tmp_path / "store" / owner.AUDIT / "begins" / begin.content_hash()
    path.write_bytes(begin.model_dump_json(indent=2).encode())
    del workflow
    assert _torn_kind(tmp_path) == "begins"


def test_a_span_that_runs_backwards_is_torn(cp3: SimpleNamespace, tmp_path: Path) -> None:
    workflow, _, _ = _prefix(cp3, tmp_path, "cp1 pages 1")
    begin = workflow._begins[1]
    backwards = begin.model_copy(
        update={
            "snapshot_before_sha256": begin.snapshot_after_sha256,
            "snapshot_after_sha256": begin.snapshot_before_sha256,
        }
    )
    owner._retain(workflow._store, "begins", backwards)
    del workflow
    assert _torn_kind(tmp_path) == "begins"


def test_a_call_naming_no_snapshot_of_the_chain_is_torn(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    workflow, _, _ = _prefix(cp3, tmp_path, "cp1 pages 1")
    call = workflow._calls[0]
    foreign = call.model_copy(
        update={
            "call_id": "7" * 8 + "-0000-4000-8000-" + "0" * 12,
            "binding": call.binding.model_copy(update={"snapshot_sha256": "5" * 64}),
        }
    )
    owner._retain(workflow._store, "calls", foreign)
    del workflow
    assert _torn_kind(tmp_path) == "calls"


def test_a_missing_snapshot_file_is_torn(cp3: SimpleNamespace, tmp_path: Path) -> None:
    workflow, _, _ = _prefix(cp3, tmp_path, "cp1 pages 1")
    parent = workflow._store.read().parent
    assert parent is not None
    (tmp_path / "store" / "snapshots" / (parent + ".json")).unlink()
    del workflow
    assert _torn_kind(tmp_path) == "snapshots"


def test_two_pending_attempts_are_torn(cp3: SimpleNamespace, tmp_path: Path) -> None:
    workflow, _, _ = _prefix(cp3, tmp_path, "cp1 pages 1")
    store = workflow._store
    before = store.read()
    other = Attempt(
        ticket_id="00000000-0000-4000-8000-0000000000aa", module_id=A, inputs=(), number=0
    )
    after = before.model_copy(
        update={"parent": before.content_hash(), "attempts": (*before.attempts, other)}
    )
    store._write(after)
    owner._retain(
        store,
        "begins",
        owner.BeginRecord(
            module_id=A,
            ticket_id=other.ticket_id,
            attempt=0,
            snapshot_before_sha256=before.content_hash(),
            snapshot_after_sha256=after.content_hash(),
        ),
    )
    del workflow
    assert _torn_kind(tmp_path) == "journal"


def test_a_begin_tail_beside_a_stray_binding_is_torn(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Window (b) with a stray binding in the audit: not rebuilt, torn."""
    workflow, actions, _ = _prefix(cp3, tmp_path, "cp1 invalid 1")
    real = owner._retain

    def failing(store: Any, kind: str, value: Any) -> None:
        if kind == "begins" and value.module_id == "CP-1" and value.attempt == 1:
            raise OSError("probe")
        real(store, kind, value)

    monkeypatch.setattr(owner, "_retain", failing)
    with pytest.raises(OSError):
        actions[[n for n, _ in actions].index("cp1 invalid 1")][1](workflow)
    monkeypatch.setattr(owner, "_retain", real)
    sub = workflow._submissions[0].binding
    real(workflow._store, "bindings", sub.model_copy(update={"payload_sha256": "4" * 64}))
    del workflow
    assert _torn_kind(tmp_path) == "journal"


def _window_a_with_stray(fake: SimpleNamespace, root: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    workflow, actions = _build(fake, root, REFUSAL_ORDER, False)
    cp0: Any = importlib.import_module("deploy_vii.cp0_workflow")

    def boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("probe: killed during validation")

    monkeypatch.setattr(cp0, "_validate_review", boom)
    _until_it_raises(workflow, actions, RuntimeError)
    return workflow


def _stray(root: Path) -> Any:
    (found,) = state_tests._retained(root / "store", "bindings", owner.OwnerSubmissionBinding)
    return found


@pytest.mark.parametrize("mutation", ["snapshot", "payload", "second"])
def test_a_window_a_binding_that_does_not_match_the_pending_step_is_torn(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    workflow = _window_a_with_stray(cp3, tmp_path, monkeypatch)
    store = workflow._store
    stray = _stray(tmp_path)
    parent = workflow._begins[0].snapshot_before_sha256  # the created snapshot, not the step's
    if mutation == "snapshot":
        other = stray.model_copy(
            update={"binding": stray.binding.model_copy(update={"snapshot_sha256": parent})}
        )
        _swap(store, "bindings", stray, other)
    elif mutation == "payload":
        raw = b"{}"
        owner._put(tmp_path / "store" / owner.AUDIT / "payloads" / owner._hash(raw), raw)
        _swap(
            store, "bindings", stray, stray.model_copy(update={"payload_sha256": owner._hash(raw)})
        )
    else:
        owner._retain(store, "bindings", stray.model_copy(update={"payload_sha256": "6" * 64}))
    del workflow
    assert _torn_kind(tmp_path) == "bindings"


def test_a_pending_step_with_another_change_is_not_window_a(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = _window_a_with_stray(cp3, tmp_path, monkeypatch)
    store = workflow._store
    pending = store.read()
    attempts = tuple(
        a.model_copy(update={"issues": ("forged",)}) if a.status == "pending" else a
        for a in pending.attempts
    )
    store._write(pending.model_copy(update={"attempts": attempts}))  # same parent: a sibling tail
    del workflow
    assert _torn_kind(tmp_path) == "journal"


def test_a_published_record_without_a_publisher_head_is_torn(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    workflow, _, _ = _prefix(cp3, tmp_path, "publish", STOP_ORDER, True)
    cursor = workflow._store.read().content_hash()
    owner._retain(
        workflow._store,
        "publications",
        owner.PublicationCall(
            snapshot_before_sha256=cursor,
            snapshot_after_sha256=cursor,
            status="published",
            reason=None,
            ticket_id=None,
            files={},
        ),
    )
    del workflow
    assert _torn_kind(tmp_path) == "publications"


def _forged_failed(workflow: Any, *, finished: bool, tag: object = "") -> None:
    """A `failed` publication as `publish` records it (a patched publisher cannot begin CP-MODEL
    over a blocked CP-1): the journal gains a CP-MODEL attempt, pending or interrupted. `tag`
    varies the reason, so that each call yields a record with its own digest (L4)."""
    store = workflow._store
    before = store.read()
    reason = f"Publication did not complete: probe {tag}".rstrip()
    extra: dict[str, Any] = {
        "status": "finished",
        "interruption": reason,
        "issues": ("Interrupted: probe",),
    }
    attempt = Attempt(
        ticket_id="00000000-0000-4000-8000-0000000000bb",
        module_id="CP-MODEL",
        inputs=(),
        number=0,
        **(extra if finished else {}),
    )
    after = before.model_copy(
        update={"parent": before.content_hash(), "attempts": (*before.attempts, attempt)}
    )
    store._write(after)
    owner._retain(
        store,
        "publications",
        owner.PublicationCall(
            snapshot_before_sha256=before.content_hash(),
            snapshot_after_sha256=after.content_hash(),
            status="failed",
            reason=reason,
            ticket_id=attempt.ticket_id,
            files={},
        ),
    )


@pytest.mark.parametrize(
    ("finished", "output", "phase"),
    [(False, False, "failed"), (True, True, "failed"), (True, False, "walked")],
)
def test_a_failed_publication_is_rebuilt_with_its_phase(
    cp3: SimpleNamespace, tmp_path: Path, finished: bool, output: bool, phase: str
) -> None:
    """`publish` leaves the phase `failed` when its cleanup did not finish: a pending publisher
    attempt, or the output directory still present; otherwise the stop stays retryable."""
    workflow, _, _ = _prefix(cp3, tmp_path, "publish", STOP_ORDER, True)
    _forged_failed(workflow, finished=finished)
    if output:
        (tmp_path / "model").mkdir()
    del workflow
    resumed = _open(tmp_path)
    assert resumed.phase == phase
    assert resumed._resume_after == "CP-MODEL"
    assert [p.status for p in resumed._publications] == ["failed"]
    assert resumed._publisher_done is False


def test_publications_keep_their_order_in_the_journal_not_by_digest(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    workflow, _, _ = _prefix(cp3, tmp_path, "publish", STOP_ORDER, True)
    store = workflow._store
    cursor = store.read().content_hash()
    for n in range(100):  # a refused record whose digest sorts after the failed one's
        refused = owner.PublicationCall(
            snapshot_before_sha256=cursor,
            snapshot_after_sha256=cursor,
            status="refused",
            reason=f"Output {n} already exists; publish into a new directory",
            ticket_id=None,
            files={},
        )
        _forged_failed(workflow, finished=True, tag=n)
        (failed,) = state_tests._retained(tmp_path / "store", "publications", owner.PublicationCall)
        if refused.content_hash() > failed.content_hash():
            break
        (tmp_path / "store" / owner.AUDIT / "publications" / failed.content_hash()).unlink()
        # undo the forged tail: point the journal back
        (tmp_path / "store" / "current").write_text(cursor + "\n")
    else:
        pytest.fail("no ordering found")
    owner._retain(store, "publications", refused)
    del workflow
    resumed = _open(tmp_path)
    assert [p.status for p in resumed._publications] == ["refused", "failed"]


def test_a_kill_between_the_publish_call_record_and_the_publications_retain_still_counts(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The call record is retained first, so a call killed before its `publications` retain is
    still one of the two the cap allows."""
    monkeypatch.setattr(owner, "_terminal", lambda heads, run, publisher: False)
    workflow, _, _ = _prefix(cp3, tmp_path, "publish", STOP_ORDER, True)
    assert workflow.publish()["status"] == "refused"
    real = owner._retain

    def failing(store: Any, kind: str, value: Any) -> None:
        if kind == "publications":
            raise OSError("probe: killed before the publications retain")
        real(store, kind, value)

    monkeypatch.setattr(owner, "_retain", failing)
    with pytest.raises(OSError):
        workflow.publish()
    monkeypatch.setattr(owner, "_retain", real)
    del workflow
    resumed = _open(tmp_path)
    assert len(resumed._publications) == 2  # both calls name the one identical record
    with pytest.raises(WorkflowError) as caught:
        resumed.publish()
    assert caught.value.code == "not_permitted"


def test_publish_cap_binds_after_resume_over_identical_refusals(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R7 (both reviews' M3): two refused `publish` calls at one snapshot with one reason leave one
    `publications` file. A per-call sibling record (`publish-calls`) keeps the count, so the
    receipt lists both and a third `publish` is refused after a resume."""
    monkeypatch.setattr(owner, "_terminal", lambda heads, run, publisher: False)
    workflow, _, _ = _prefix(cp3, tmp_path, "publish", STOP_ORDER, True)
    assert workflow.publish()["status"] == workflow.publish()["status"] == "refused"
    assert len(list((tmp_path / "store" / owner.AUDIT / "publications").iterdir())) == 1
    calls = state_tests._retained(tmp_path / "store", "publish-calls", owner.PublishCall)
    assert sorted(c.sequence for c in calls) == [1, 2]
    with pytest.raises(WorkflowError):
        workflow.publish()
    before = _view(workflow)
    del workflow
    resumed = _open(tmp_path)
    assert _view(resumed) == before
    assert len(resumed._publications) == 2
    with pytest.raises(WorkflowError) as caught:
        resumed.publish()
    assert caught.value.code == "not_permitted"


def test_publish_attempts_stay_bounded_over_repeated_resumes(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(owner, "_terminal", lambda heads, run, publisher: False)
    workflow, _, _ = _prefix(cp3, tmp_path, "publish", STOP_ORDER, True)
    accepted = 0
    for _ in range(5):
        for _ in range(3):
            try:
                workflow.publish()
                accepted += 1
            except WorkflowError:
                break
        workflow = _open(tmp_path)
    assert accepted <= 2


class _Kill(BaseException):
    pass


@pytest.mark.parametrize("where", ["receipt", "seal"])
def test_a_kill_inside_write_receipt_can_be_finished_after_open(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, where: str
) -> None:
    """R10 (adversary L1): the receipt file is written before the seal, so a kill between them
    leaves a run `open()` does not treat as sealed, and a rebuilt receipt is written and sealed."""
    workflow, actions = _build(cp3, tmp_path, REFUSAL_ORDER, False)
    for _, act in actions:
        act(workflow)
    destination = tmp_path / "receipt.json"
    real = owner._put

    def put(path: Path, raw: bytes) -> None:
        if path.name == ("receipt.json" if where == "receipt" else "receipt.sha256"):
            raise _Kill()
        real(path, raw)

    monkeypatch.setattr(owner, "_put", put)
    with pytest.raises(_Kill):
        workflow.write_receipt(destination)
    monkeypatch.setattr(owner, "_put", real)
    del workflow
    resumed = _open(tmp_path)
    assert resumed.phase == "complete" and resumed._sealed is False
    receipt = resumed.write_receipt(destination)
    owner.verify_owner_run_receipt(Execution(tmp_path / "store"), receipt)
    assert _open(tmp_path)._sealed is True


def test_open_refuses_a_json_lines_run(tmp_path: Path) -> None:
    """R10 (both reviews' L2): `serve_json_lines` retains its transport and participant, and a run
    served over JSON-lines is not resumed (it would be relabelled `trusted-python`)."""
    workflow, _ = runs.start("positive", tmp_path)
    request = {
        "operation": "invoke",
        "tool": "read_pages",
        "arguments": {"source_id": "identity", "first_page": 1, "last_page": 1},
    }
    out = io.StringIO()
    owner.serve_json_lines(
        workflow,
        io.StringIO(json.dumps(request) + "\n"),
        out,
        destination=tmp_path / "receipt.json",
        participant="external-model",
    )
    assert json.loads(out.getvalue())["status"] == "ok"
    del workflow
    with pytest.raises(WorkflowError) as caught:
        owner.OwnerWorkflow.open(tmp_path / "store", publication_directory=tmp_path / "model")
    assert caught.value.code == "not_permitted"


def test_a_resumed_walked_instance_refuses_like_the_live_one(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    """R10 (adversary L3): `invoke` and `read_inputs` check the phase before they read the
    binding, which an instance with no module active does not have."""
    workflow, _, _ = _prefix(cp3, tmp_path, "publish", STOP_ORDER, True)
    assert workflow.phase == "walked"
    page = {"source_id": "financial", "first_page": 1, "last_page": 1}

    def outcome(call: Callable[[], Any]) -> str:
        try:
            call()
        except WorkflowError as error:
            return f"WorkflowError({error.code})"
        return "accepted"

    def refusals_of(w: Any) -> list[str]:
        return [
            outcome(lambda: w.invoke("read_pages", page)),
            outcome(w.read_inputs),
            outcome(lambda: w.submit_review("{}")),
        ]

    live = refusals_of(workflow)
    del workflow
    assert refusals_of(_open(tmp_path)) == live == ["WorkflowError(not_permitted)"] * 3


@pytest.mark.parametrize("entry", ["x" * 200, "subdir/", "z" * 64])
def test_a_foreign_entry_in_an_audit_kind_is_torn(
    cp3: SimpleNamespace, tmp_path: Path, entry: str
) -> None:
    """I1: a subdirectory, an over-long name or a file that is not a record is `TornAudit`, never a
    raw `ValidationError` or `IsADirectoryError`."""
    _prefix(cp3, tmp_path, "cp1 pages 1")
    calls = tmp_path / "store" / owner.AUDIT / "calls"
    if entry.endswith("/"):
        (calls / entry.rstrip("/")).mkdir()
    else:
        (calls / entry).write_bytes(b"\x00junk")
    assert _torn_kind(tmp_path) == "calls"


def test_a_dot_name_in_an_audit_kind_is_ignored_and_never_adopted(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    """I1: Finder's `.DS_Store` beside the records is not adopted by `open()` and does not stop the
    receipt from verifying."""
    workflow, actions = _build(cp3, tmp_path, REFUSAL_ORDER, False)
    for _, act in actions[:8]:
        act(workflow)
    for kind in ("calls", "begins", "submissions", "bindings", "input-reads"):
        directory = tmp_path / "store" / owner.AUDIT / kind
        directory.mkdir(exist_ok=True)
        (directory / ".DS_Store").write_bytes(b"\x00junk")
    resumed = _open(tmp_path)
    assert len(resumed._calls) == len(workflow._calls)
    for _, act in actions[8:]:
        act(resumed)
    owner.verify_owner_run_receipt(
        Execution(tmp_path / "store"), resumed.write_receipt(tmp_path / "receipt.json")
    )


# --- fix round 1: the survivors of the first mutant run (adversary M5, P17) --------------------


def test_a_record_stored_under_another_digest_is_torn(cp3: SimpleNamespace, tmp_path: Path) -> None:
    """Canonical bytes that parse, under a name that is not their digest (a copied record)."""
    workflow, _, _ = _prefix(cp3, tmp_path, "cp1 pages 1")
    begin = workflow._begins[0]
    (tmp_path / "store" / owner.AUDIT / "begins" / ("a" * 64)).write_bytes(
        begin.model_dump_json().encode()
    )
    del workflow
    assert _torn_kind(tmp_path) == "begins"


def test_a_pending_attempt_whose_steps_are_all_valid_is_torn(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CP-0's step is journaled valid and the kill falls before `finish`: the attempt is pending
    with every step valid, nothing left to resubmit. A `submissions` record covering the span (as
    if the retain had succeeded) leaves no tail, and `open()` still refuses the attempt."""
    workflow, actions = _build(cp3, tmp_path, REFUSAL_ORDER, False)
    cp0: Any = importlib.import_module("deploy_vii.cp0_workflow")
    real = cp0._validate_review
    calls = {"n": 0}

    def second_raises(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("probe: killed between the step and the settlement")
        return real(*args, **kwargs)

    monkeypatch.setattr(cp0, "_validate_review", second_raises)
    _until_it_raises(workflow, actions, RuntimeError)
    store = workflow._store
    current = store.read()
    attempt = next(a for a in current.attempts if a.status == "pending")
    step = attempt.steps[-1]
    assert step.status == "valid"
    stray = _stray(tmp_path)
    owner._retain(
        store,
        "submissions",
        owner.OwnerSubmission(
            sequence=1,
            binding=stray,
            stored_payload_sha256=step.payload_sha256,
            canonical_review_sha256=None,
            disposition="valid",
            issues=(),
            snapshot_after_sha256=current.content_hash(),
            step_sha256=step.content_hash(),
            step_output_sha256=step.output_sha256,
        ),
    )
    del workflow
    assert _torn_kind(tmp_path) == "journal"


def test_a_publish_killed_before_any_record_still_counts_against_the_cap(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The call record is written first: a refused `publish` killed before its `publications`
    retain leaves one call and no publication, and two more calls are not allowed."""
    monkeypatch.setattr(owner, "_terminal", lambda heads, run, publisher: False)
    workflow, _, _ = _prefix(cp3, tmp_path, "publish", STOP_ORDER, True)
    real = owner._retain

    def failing(store: Any, kind: str, value: Any) -> None:
        if kind == "publications":
            raise OSError("probe")
        real(store, kind, value)

    monkeypatch.setattr(owner, "_retain", failing)
    with pytest.raises(OSError):
        workflow.publish()
    monkeypatch.setattr(owner, "_retain", real)
    del workflow
    resumed = _open(tmp_path)
    assert resumed._publications == [] and resumed._publish_calls == 1
    assert resumed.publish()["status"] == "refused"
    with pytest.raises(WorkflowError) as caught:
        resumed.publish()
    assert caught.value.code == "not_permitted"


def test_m24_a_tampered_open_epoch_call_is_torn(tmp_path: Path) -> None:
    """Replay equality: a self-consistent call record whose body was changed is refused."""
    workflow, pack = runs.start("positive", tmp_path)
    runs.read_cited(workflow, runs.literal("positive", "readiness_review", pack))
    call = next(c for c in workflow._epoch_calls if c.status == "ok")
    del workflow
    _swap(Execution(tmp_path / "store"), "calls", call, call.model_copy(update={"body": "forged"}))
    with pytest.raises(owner.TornAudit) as caught:
        owner.OwnerWorkflow.open(tmp_path / "store", publication_directory=tmp_path / "model")
    assert caught.value.kind == "calls"


def test_m15_a_deleted_refused_submission_is_torn(cp3: SimpleNamespace, tmp_path: Path) -> None:
    """A gate-refused submission changes no snapshot (width 0), so the span walk cannot see it
    deleted; only the sequence check does."""
    workflow = g1x._start(tmp_path)
    workflow.read_inputs()
    g1x._read_page(workflow)
    for _ in range(2):
        assert workflow.submit_review(g1x._sourced(g1x.GATE_MARK))["status"] == "refused"
    assert workflow.state().submits_used == 2
    first = next(s for s in workflow._submissions if s.disposition == "refused")
    del workflow
    (tmp_path / "store" / owner.AUDIT / "submissions" / first.content_hash()).unlink()
    with pytest.raises(owner.TornAudit) as caught:
        owner.OwnerWorkflow.open(tmp_path / "store", specs=owner.OWNER_SPECS)
    assert caught.value.kind == "submissions"


def test_m25_kill_before_the_repair_begin_resumes_with_the_repair(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Killed after CP-1 attempt 0 settled invalid and its submission was retained, before
    `store.begin` of the repair: `open()` begins the repair, as the live walk would."""
    control = _control(cp3, tmp_path / "control", REFUSAL_ORDER, False)
    root = tmp_path / "run"
    workflow, actions = _build(cp3, root, REFUSAL_ORDER, False)
    index = [n for n, _ in actions].index("cp1 invalid 1")
    for _, act in actions[:index]:
        act(workflow)

    def begin(self: Any, module_id: str) -> Any:
        raise _Kill()

    real = Execution.begin
    monkeypatch.setattr(Execution, "begin", begin)
    with pytest.raises(_Kill):
        actions[index][1](workflow)
    monkeypatch.setattr(Execution, "begin", real)
    assert not any(a.status == "pending" for a in Execution(root / "store").read().attempts)
    del workflow
    resumed = _open(root)
    assert (resumed.state().module_id, resumed.state().attempt) == ("CP-1", 1)
    for _, act in actions[index + 1 :]:
        act(resumed)
    assert _normal(resumed.write_receipt(root / "receipt.json")) == _normal(control)


def test_m39_kill_between_create_and_the_first_begin_begins_cp0(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def killed(self: Any, module_id: str) -> bool:
        raise _Kill()

    with monkeypatch.context() as patch:
        patch.setattr(owner.OwnerWorkflow, "_begin", killed)
        with pytest.raises(_Kill):
            owner.OwnerWorkflow.create(
                tmp_path / "store",
                runs.make_pack("positive"),
                publication_directory=tmp_path / "model",
            )
    assert Execution(tmp_path / "store").read().attempts == ()
    resumed = owner.OwnerWorkflow.open(tmp_path / "store", publication_directory=tmp_path / "model")
    state = resumed.state()
    assert (state.phase, state.module_id, state.attempt) == ("analytical", "CP-0", 0)


def test_m11_a_forged_begin_tail_is_torn_and_retains_nothing(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    """At the CP-MODEL stop a snapshot that adds an attempt `begin` would not produce (wrong
    inputs) is not window (b): torn, and no `BeginRecord` is written."""
    workflow, _, _ = _prefix(cp3, tmp_path, "publish", STOP_ORDER, True)
    store = workflow._store
    snapshot = store.read()
    forged = Attempt(
        ticket_id="00000000-0000-4000-8000-0000000000cc", module_id=A, inputs=(), number=0
    )
    store._write(
        snapshot.model_copy(
            update={"parent": snapshot.content_hash(), "attempts": (*snapshot.attempts, forged)}
        )
    )
    names = sorted(p.name for p in (tmp_path / "store" / owner.AUDIT / "begins").iterdir())
    del workflow
    assert _torn_kind(tmp_path) == "journal"
    assert sorted(p.name for p in (tmp_path / "store" / owner.AUDIT / "begins").iterdir()) == names


@pytest.mark.parametrize("run", range(4))
def test_m16_m36_two_refusals_at_one_snapshot_rebuild_kind_and_order(
    cp3: SimpleNamespace, tmp_path: Path, run: int
) -> None:
    """A not authorised (first), then B blocked, both at one snapshot: `open()` keeps the first
    refusal's kind and the plan order (ties in snapshot position are broken by digest, random per
    run)."""
    order = ("CP-0", "CP-1", refusals.A, refusals.B)
    workflow = refusals._walk(cp3, tmp_path, order, refusals.A)
    live = (workflow._refusal_kind, workflow._refusal_code(), tuple(workflow._refusals))
    assert live[0] == "not_authorized"
    del workflow
    resumed = _open(tmp_path)
    assert (resumed._refusal_kind, resumed._refusal_code(), tuple(resumed._refusals)) == live


promotion = pytest.mark.skipif(
    os.environ.get("RUN_PROMOTION") != "1", reason="real CP-1 promotion, 11-26 min; deferred"
)


@promotion
def test_kill_between_publish_and_the_publications_retain_is_torn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F4 (c), real: the S1a closed run is driven to CP-MODEL, `publish` journals and writes the
    output, and the `publications` retain fails. `open()` raises `TornAudit` and writes a
    `faults/` record naming `publications`."""
    workflow, pack = runs.promoted("positive", tmp_path)
    runs.drive_cp1a(workflow, pack, "positive")
    outcome = runs.drive_cp2(workflow, "positive", runs.read_cp2(workflow))
    assert outcome["status"] == "valid"
    real = owner._retain

    def failing(store: Any, kind: str, value: Any) -> None:
        if kind == "publications":
            raise OSError("probe: killed before the publications retain")
        real(store, kind, value)

    monkeypatch.setattr(owner, "_retain", failing)
    with pytest.raises(OSError):
        workflow.publish()
    monkeypatch.setattr(owner, "_retain", real)
    with pytest.raises(owner.TornAudit):
        owner.OwnerWorkflow.open(tmp_path / "store", publication_directory=tmp_path / "model")
    assert _faults(tmp_path)[0].kind == "publications"


# --- 3a re-review Lows (L1 to L4) and I3 --------------------------------------------------------


def _store_tree(root: Path) -> dict[str, bytes]:
    """The store's files but the `faults/` records, which a refused `open()` writes by design."""
    return {
        k: v for k, v in g1x._tree(root / "store").items() if f"/{owner.AUDIT}/faults/" not in k
    }


def test_p18_gap_in_a_session_less_open_epoch_is_torn(cp3: SimpleNamespace, tmp_path: Path) -> None:
    workflow, _, _ = _prefix(cp3, tmp_path, "a viewed")
    assert workflow.state().step_id == g1x.VIEWED and workflow._session is None
    page = {"source_id": "financial", "first_page": 1, "last_page": 1}
    first = workflow.invoke("read_pages", page)
    workflow.invoke("read_pages", page)
    del workflow
    (
        tmp_path
        / "store"
        / owner.AUDIT
        / "calls"
        / owner._parse(owner.OwnerCall, first).content_hash()
    ).unlink()
    with pytest.raises(owner.TornAudit) as caught:
        _open(tmp_path)
    assert caught.value.kind == "calls"


def _forge_cp0_call(root: Path) -> None:
    store = Execution(root / "store")
    calls = [
        c for c in owner._load(store, "calls", owner.OwnerCall) if c.binding.module_id == "CP-0"
    ]
    call = next(c for c in calls if c.status == "ok")
    _swap(store, "calls", call, call.model_copy(update={"body": "forged body"}))


def test_p19a_window_a_open_refuses_a_forged_closed_call_before_resubmitting(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """L2: the closed-record checks run before the resubmit, so a refused `open()` writes nothing
    but its fault record (the store tree, `faults/` aside, is equal before and after)."""
    workflow, actions = _build(cp3, tmp_path, REFUSAL_ORDER, False)
    real = g1x._validate
    calls = {"n": 0}

    def once(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("probe: killed during validation")
        return real(*args, **kwargs)

    monkeypatch.setattr(g1x, "_validate", once)
    assert actions[_until_it_raises(workflow, actions, RuntimeError)][0] == "a sourced"
    del workflow
    _forge_cp0_call(tmp_path)
    before = _store_tree(tmp_path)
    with pytest.raises(owner.TornAudit):
        _open(tmp_path)
    assert _store_tree(tmp_path) == before


def test_p19b_continue_walk_open_refuses_a_forged_closed_call_before_beginning(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow, actions = _build(cp3, tmp_path, REFUSAL_ORDER, False)
    actions[0][1](workflow)  # sources

    def begin(self: Any, module_id: str) -> Any:
        raise _Kill()

    monkeypatch.setattr(Execution, "begin", begin)
    with pytest.raises(_Kill):
        actions[1][1](workflow)  # cp0: submission retained, CP-1 begin killed
    monkeypatch.undo()
    del workflow
    _forge_cp0_call(tmp_path)
    before = _store_tree(tmp_path)
    with pytest.raises(owner.TornAudit):
        _open(tmp_path)
    assert _store_tree(tmp_path) == before


def test_p20_changed_body_of_a_closed_read_is_torn_at_open(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    workflow, _, _ = _prefix(cp3, tmp_path, "a viewed")
    read = next(r for r in workflow._reads if r.binding.step_id == g1x.SOURCED)
    del workflow
    _swap(
        Execution(tmp_path / "store"),
        "input-reads",
        read,
        read.model_copy(update={"body": read.body + " "}),
    )
    assert _torn_kind(tmp_path) == "input-reads"


def test_p20b_injected_open_epoch_read_with_a_wrong_body_is_torn_at_open(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    """A first read at the active step with a body `read_inputs` never returns would mark the
    inputs read and pass the submit precondition; `open()` refuses it."""
    workflow, _, _ = _prefix(cp3, tmp_path, "a inputs")
    assert workflow.state().inputs_required and not workflow.state().inputs_read
    binding = workflow._binding
    del workflow
    forged = owner.OwnerInputRead(
        binding=binding, sequence=1, inputs_sha256="0" * 64, body="forged"
    )
    owner._retain(Execution(tmp_path / "store"), "input-reads", forged)
    assert _torn_kind(tmp_path) == "input-reads"


def test_a_read_at_a_step_whose_inputs_are_none_is_torn_at_open(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    workflow, _, _ = _prefix(cp3, tmp_path, "cp1 pages 1")
    assert workflow._spec.inputs == "none"
    binding = workflow._binding
    del workflow
    forged = owner.OwnerInputRead(binding=binding, sequence=1, inputs_sha256="0" * 64, body="x")
    owner._retain(Execution(tmp_path / "store"), "input-reads", forged)
    assert _torn_kind(tmp_path) == "input-reads"


def test_x03_a_gap_in_a_steps_reads_is_torn(cp3: SimpleNamespace, tmp_path: Path) -> None:
    workflow, _, _ = _prefix(cp3, tmp_path, "a page")
    workflow.read_inputs()  # a second read of the sourced step
    first = next(r for r in workflow._reads if r.binding.step_id == g1x.SOURCED and r.sequence == 1)
    del workflow
    (tmp_path / "store" / owner.AUDIT / "input-reads" / first.content_hash()).unlink()
    assert _torn_kind(tmp_path) == "input-reads"


def test_x08_a_gap_in_the_publish_calls_is_torn(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(owner, "_terminal", lambda heads, run, publisher: False)
    workflow, _, _ = _prefix(cp3, tmp_path, "publish", STOP_ORDER, True)
    workflow.publish()
    workflow.publish()
    del workflow
    store = tmp_path / "store" / owner.AUDIT / "publish-calls"
    calls = [owner.PublishCall.model_validate_json(p.read_bytes()) for p in store.iterdir()]
    first = next(c for c in calls if c.sequence == 1)
    (store / first.content_hash()).unlink()
    assert _torn_kind(tmp_path) == "publish-calls"


def test_x09_a_refused_submission_whose_payload_passes_the_gate_is_torn(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    workflow, _, _ = _prefix(cp3, tmp_path, "a sourced")
    assert workflow.submit_review(g1x._sourced(g1x.GATE_MARK))["status"] == "refused"
    refused = next(s for s in workflow._submissions if s.disposition == "refused")
    store = workflow._store
    passing = owner._fill(store, workflow._binding, g1x._sourced())[0]
    owner._put(owner._audit(store, "payloads", owner._hash(passing.encode())), passing.encode())
    del workflow
    _swap(
        store,
        "submissions",
        refused,
        refused.model_copy(
            update={"stored_payload_sha256": owner._hash(passing.encode()), "issues": ()}
        ),
    )
    assert _torn_kind(tmp_path) == "submissions"


def test_x11_call_ids_out_of_order_are_torn(cp3: SimpleNamespace, tmp_path: Path) -> None:
    workflow, _, _ = _prefix(cp3, tmp_path, "cp1 pages 1")
    submission = workflow._submissions[0]  # CP-0, two or more listed calls
    ids = submission.binding.call_ids
    assert len(ids) >= 2
    del workflow
    swapped = submission.binding.model_copy(update={"call_ids": (ids[1], ids[0], *ids[2:])})
    _swap(
        Execution(tmp_path / "store"),
        "submissions",
        submission,
        submission.model_copy(update={"binding": swapped}),
    )
    (tmp_path / "store" / owner.AUDIT / "bindings" / submission.binding.content_hash()).unlink()
    owner._retain(Execution(tmp_path / "store"), "bindings", swapped)
    assert _torn_kind(tmp_path) == "submissions"


def test_x12_a_changed_step_output_of_a_submission_is_torn(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    workflow, _, _ = _prefix(cp3, tmp_path, "cp1 pages 1")
    submission = workflow._submissions[0]
    del workflow
    _swap(
        Execution(tmp_path / "store"),
        "submissions",
        submission,
        submission.model_copy(update={"step_output_sha256": "0" * 64}),
    )
    assert _torn_kind(tmp_path) == "submissions"


def test_x13_changed_issues_of_an_invalid_submission_are_torn(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    workflow, _, _ = _prefix(cp3, tmp_path, "cp1 pages 1")
    invalid = next(s for s in workflow._submissions if s.disposition == "invalid")
    del workflow
    _swap(
        Execution(tmp_path / "store"),
        "submissions",
        invalid,
        invalid.model_copy(update={"issues": ("forged issue",)}),
    )
    assert _torn_kind(tmp_path) == "submissions"


def test_x02_a_changed_error_code_of_a_closed_session_less_call_is_torn(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    workflow, actions, stop = _prefix(cp3, tmp_path, "a viewed")
    assert workflow._session is None
    call = owner._parse(
        owner.OwnerCall,
        workflow.invoke("read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}),
    )
    actions[stop][1](workflow)  # the viewed submit closes the binding (it lists the call)
    del workflow
    _swap(
        Execution(tmp_path / "store"),
        "calls",
        call,
        call.model_copy(update={"error_code": "bad_arguments"}),
    )
    assert _torn_kind(tmp_path) == "calls"


def test_a_resubmit_that_is_valid_is_kept_as_resumed_submission(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """I3 (R12): window (a)'s resubmit result is on the instance, the object `submit_review`
    returned; an `open()` that resubmitted nothing holds `None`."""
    _window_a(cp3, tmp_path, monkeypatch)
    resumed = _open(tmp_path)
    outcome = resumed.resumed_submission
    assert outcome is not None and outcome["status"] == "valid" and outcome["issues"] == []
    assert outcome["step_id"] == "source_readiness"
    assert _open(tmp_path).resumed_submission is None  # nothing pending now


def test_a_resubmit_that_is_invalid_keeps_its_issues_for_the_repair_prompt(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow, actions = _build(cp3, tmp_path, REFUSAL_ORDER, False)
    stop = [label for label, _ in actions].index("a sourced")
    for _, act in actions[:stop]:
        act(workflow)
    real = g1x._validate
    calls = {"n": 0}

    def once(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("probe: killed during validation")
        return real(*args, **kwargs)

    monkeypatch.setattr(g1x, "_validate", once)
    with pytest.raises(RuntimeError):
        workflow.submit_review(g1x._sourced(g1x.INVALID_MARK))
    del workflow
    resumed = _open(tmp_path)
    outcome = resumed.resumed_submission
    assert outcome is not None and outcome["status"] == "invalid"
    assert outcome["issues"] == [g1x.VALIDATOR_ISSUE]
    assert resumed.state().step_id == g1x.SOURCED  # the same step is re-activated for the repair
