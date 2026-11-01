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
    if resumed.phase == "analytical":  # the disk oracle cannot see a submit refused unread
        oracle = state_tests._independent(resumed)
        assert resumed.state().submits_used >= oracle.submits_used
        assert resumed.state().model_copy(update={"submits_used": oracle.submits_used}) == oracle
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


def test_submit_refused_for_an_unread_step_still_counts_after_open(
    cp3: SimpleNamespace, tmp_path: Path
) -> None:
    """Task 2 review Q1: that refusal wrote no record, so a resume undercounted `submits_used`. It
    is retained now (kind `unread-submits`, outside the receipt) and rebuilt."""
    workflow, actions = _build(cp3, tmp_path, REFUSAL_ORDER, False)
    for _, act in actions:
        if act is _unread_submit:
            break
        act(workflow)
    _unread_submit(workflow)
    _unread_submit(workflow)
    assert workflow.state().submits_used == 2
    resumed = _open(tmp_path)
    assert resumed.state().submits_used == 2
    assert state_tests._independent(resumed).submits_used == 0  # the disk oracle does not see it


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


def test_kill_during_validation_resumes_by_resubmitting_the_same_payload(
    cp3: SimpleNamespace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F4 (a): the validator raises after `submit_step` wrote the pending step. The journal holds
    a pending step and the audit its payload and binding but no `submissions` record. `open()`
    rebinds the step at the snapshot before the pending write and the same payload continues; the
    receipt equals the control. The CP-0 reads were made on the killed instance, so the resumed
    submit also needs the rebuilt session to bind them."""
    control = _control(cp3, tmp_path / "control", REFUSAL_ORDER, False)
    root = tmp_path / "run"
    workflow, actions = _build(cp3, root, REFUSAL_ORDER, False)
    cp0: Any = importlib.import_module("deploy_vii.cp0_workflow")
    real = cp0._validate_review
    calls = {"n": 0}

    def once(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("probe: killed during validation")
        return real(*args, **kwargs)

    monkeypatch.setattr(cp0, "_validate_review", once)
    killed = _until_it_raises(workflow, actions, RuntimeError)
    assert actions[killed][0] == "cp0"
    (attempt,) = [a for a in workflow._store.read().attempts if a.status == "pending"]
    assert [s.status for s in attempt.steps] == ["pending"]
    assert state_tests._retained(root / "store", "submissions", owner.OwnerSubmission) == []
    epoch = list(workflow._epoch_calls)
    del workflow
    resumed = _open(root)
    assert resumed.state().stale is False
    assert list(resumed._epoch_calls) == epoch
    assert resumed._binding.snapshot_sha256 != resumed._store.read().content_hash()
    for _, act in actions[killed:]:  # resubmits the same payload, then goes on
        act(resumed)
    receipt = resumed.write_receipt(root / "receipt.json")
    assert _normal(receipt) == _normal(control)


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
    with pytest.raises(owner.TornAudit) as caught:
        _open(tmp_path)
    assert caught.value.code == "identity_mismatch"
    assert _faults(tmp_path)[0].kind == "publications"


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
