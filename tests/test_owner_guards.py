"""Part B O3+O4 Task 5 (G6): a byte cap on `read_inputs` and the journaled per-step call cap.

`read_inputs` refuses a body over `MAX_INPUT_BYTES` (bytes, not characters): nothing is retained
or counted, a `faults/` record `InputsTooLarge` names the binding, size and cap (never the body),
and the tool loop stops on it by name. A call past `MAX_CALLS` for one `(ticket, step)` keeps its
`not_permitted` refusal and journals a `CallLimit` fault. The real CP-1 `quality` read is pinned
by `tests/test_financial_workflow.py::test_quality_read_serves_narrowed_quality_scope_bound_to_
full_inputs` (P20, run, never edited); the exact-size tests here patch `_inputs`.

The worlds are the owner workflow at CP-1 `narrative` (inputs `projection`, unread) and CP-1
`source_context` (pack tools), both a second or two; the run-level tests drive the o2-synthetic
frozen answers up to `narrative`.
"""

import hashlib
import importlib
import io
import json
import logging
import os
import sys
import unicodedata
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import o2_case
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import BaseModel

from deploy_workflow import owner_workflow as owner
from deploy_workflow import run_pathway as rp
from deploy_workflow.financial_workflow import MAX_CALLS, MAX_INVOKES, MAX_LINE
from deploy_workflow.host import MAX_ARGUMENT_DEPTH
from deploy_workflow.model.record import LOOP_STOPS
from deploy_workflow.owner_workflow import (
    AUDIT,
    MAX_INPUT_BYTES,
    MAX_JSON_DEPTH,
    OwnerFault,
)
from deploy_workflow.run_inputs import stage_sources
from deploy_workflow.tools.source import SourceError, SourceTools
from deploy_workflow.workflow import WorkflowError

financial: Any = importlib.import_module("test_financial_workflow")
refusals: Any = importlib.import_module("test_owner_refusals")
g1x: Any = importlib.import_module("test_owner_g1x")
replays: Any = importlib.import_module("test_owner_replay")
cp3 = refusals.cp3  # the fixture: the G1-X fake registered as CP-3 / CP-3D

CAP = MAX_INPUT_BYTES
MARKER = "BODY-MARKER-4f1c"


def _owner_start(root: Path, gap: bool = False) -> tuple[Any, Any]:
    pack = financial.make_pack(gap)
    return owner.OwnerWorkflow.create(
        root / "store", pack, publication_directory=root / "model"
    ), pack


@pytest.fixture
def owner_world(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(financial, "start", _owner_start)
    yield


def _narrative_world(root: Path) -> Any:
    """The owner workflow at CP-1 `narrative`: inputs `projection`, not yet read."""
    workflow, pack = financial.before_financials(root)
    financial.financial_reads(workflow)
    assert workflow.submit_review(json.dumps(financial.financials(pack)))["status"] == "valid"
    assert workflow.binding.step_id == "narrative" and workflow.spec.inputs == "projection"
    return workflow


def _source_context_world(root: Path) -> Any:
    """The owner workflow at CP-1 `source_context`: the pack tools are offered."""
    workflow, pack = financial.start(root)
    financial.read_sources(workflow)
    assert workflow.submit_review(financial.readiness(pack))["status"] == "valid"
    assert workflow.binding.step_id == "source_context"
    return workflow


def _body_of(size: int, marker: str = MARKER) -> str:
    return marker + "a" * (size - len(marker))


def _serve(monkeypatch: pytest.MonkeyPatch, body: str) -> None:
    """`_inputs` returns `body` (the digest is the real one of its bytes)."""
    digest = hashlib.sha256(body.encode()).hexdigest()
    monkeypatch.setattr(owner, "_inputs", lambda store, binding, spec: (digest, body))


def _audit_files(workflow: Any, kind: str) -> list[Path]:
    folder = workflow._store.directory / AUDIT / kind
    return sorted(folder.iterdir()) if folder.is_dir() else []


def _faults(workflow: Any) -> list[OwnerFault]:
    return [
        OwnerFault.model_validate_json(p.read_bytes()) for p in _audit_files(workflow, "faults")
    ]


def _dump(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")


# ------------------------------------------------------------------------- the byte cap


def test_the_cap_is_the_line_bound() -> None:
    assert MAX_INPUT_BYTES == MAX_LINE == 4_194_304


@pytest.mark.usefixtures("owner_world")
def test_a_body_of_the_cap_passes_and_one_more_byte_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    served = _narrative_world(tmp_path / "pass")
    _serve(monkeypatch, _body_of(CAP))
    read = served.read_inputs()
    assert len(read["body"].encode()) == CAP
    assert served.state().reads_used == 1 and len(_audit_files(served, "input-reads")) == 1
    assert _faults(served) == []

    refused = _narrative_world(tmp_path / "refuse")
    before = refused.state()
    _serve(monkeypatch, _body_of(CAP + 1))
    with pytest.raises(WorkflowError) as caught:
        refused.read_inputs()
    assert caught.value.code == "inputs_too_large"
    assert refused.state() == before and before.reads_used == 0
    assert _audit_files(refused, "input-reads") == []
    (fault,) = _faults(refused)
    assert (fault.code, fault.size, fault.cap) == ("InputsTooLarge", CAP + 1, CAP)
    assert fault.binding == refused.binding
    (path,) = _audit_files(refused, "faults")
    assert MARKER.encode() not in path.read_bytes()
    for stored in (refused._store.directory).rglob("*"):
        if stored.is_file() and AUDIT in stored.parts:
            assert MARKER.encode() not in stored.read_bytes(), stored


@pytest.mark.usefixtures("owner_world")
def test_at_the_read_cap_an_oversized_body_is_a_call_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The call cap is checked before the body is built: past `MAX_CALLS` reads, an oversized
    body is a `CallLimit` refusal and `_inputs` is never run."""
    workflow = _narrative_world(tmp_path)
    _serve(monkeypatch, _body_of(10))
    for _ in range(MAX_CALLS):
        workflow.read_inputs()
    computed: list[int] = []
    body = _body_of(MAX_INPUT_BYTES + 1)
    digest = hashlib.sha256(body.encode()).hexdigest()

    def served(store: Any, binding: Any, spec: Any) -> tuple[str, str]:
        computed.append(1)
        return digest, body

    monkeypatch.setattr(owner, "_inputs", served)
    with pytest.raises(WorkflowError) as caught:
        workflow.read_inputs()
    assert caught.value.code == "not_permitted" and computed == []  # the body was never built
    assert [f.code for f in _faults(workflow)] == ["CallLimit"]


# The bytes a `torn_audit` fault had before the G6 fields: `None` fields are omitted, so every
# older fault kind keeps its bytes and digest under the same `owner-fault/1`.
OLDER_FAULT_JSON = (
    '{"schema_version":"owner-fault/1","code":"torn_audit","kind":"calls","digest":"'
    + "a" * 64
    + '"}'
)
OLDER_FAULT_DIGEST = "62cb36f138cfd1e078da29eac6267982fdeb3e6dfe3296c132f9a1d86824379e"


def test_an_older_fault_keeps_its_bytes_and_digest() -> None:
    fault = OwnerFault(code="torn_audit", kind="calls", digest="a" * 64)
    assert fault.model_dump_json() == OLDER_FAULT_JSON
    assert fault.content_hash() == OLDER_FAULT_DIGEST
    assert OwnerFault.model_validate_json(OLDER_FAULT_JSON) == fault  # an old record still reads


@pytest.mark.usefixtures("owner_world")
def test_the_cap_counts_bytes_not_characters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = _narrative_world(tmp_path)
    body = "é" * (CAP // 2 + 1)
    assert len(body) <= CAP < len(body.encode())
    _serve(monkeypatch, body)
    with pytest.raises(WorkflowError) as caught:
        workflow.read_inputs()
    assert caught.value.code == "inputs_too_large"
    (fault,) = _faults(workflow)
    assert fault.size == len(body.encode())


@pytest.mark.usefixtures("owner_world")
def test_the_step_stays_open_and_unread_after_the_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = _narrative_world(tmp_path)
    with monkeypatch.context() as patch:
        _serve(patch, _body_of(CAP + 1))
        with pytest.raises(WorkflowError):
            workflow.read_inputs()
    state = workflow.state()
    assert state.inputs_required and not state.inputs_read and state.reads_used == 0
    with pytest.raises(WorkflowError) as caught:  # no read on the binding: refused, as before
        workflow.submit_review("{}")
    assert caught.value.code == "not_permitted"
    assert workflow.state() == state and _audit_files(workflow, "input-reads") == []
    assert len(_faults(workflow)) == 1
    assert workflow.read_inputs()["sequence"] == 1  # the real body is under the cap


@pytest.mark.usefixtures("owner_world")
@settings(max_examples=11, deadline=None)
@given(delta=st.integers(min_value=-5, max_value=5))
def test_the_decision_is_size_over_cap_and_a_refusal_changes_nothing(delta: int) -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as root, pytest.MonkeyPatch.context() as patch:
        patch.setattr(financial, "start", _owner_start)
        workflow = _narrative_world(Path(root))
        before = workflow.state()
        _serve(patch, _body_of(CAP + delta))
        refused = False
        try:
            workflow.read_inputs()
        except WorkflowError as error:
            assert error.code == "inputs_too_large"
            refused = True
        assert refused == (CAP + delta > CAP)
        if refused:
            assert workflow.state() == before
            assert _audit_files(workflow, "input-reads") == []
        else:
            assert workflow.state().reads_used == 1


def test_a_receipt_after_an_inputs_too_large_fault_still_verifies(
    cp3: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The faults kind is outside the compared set: the G1-X fake module's first read is refused
    over the cap, then the module is driven for real and the run's receipt verifies."""
    workflow = refusals._walk(cp3, tmp_path, refusals.ORDER)
    assert workflow.binding.module_id == refusals.A
    with monkeypatch.context() as patch:
        _serve(patch, _body_of(CAP + 1))
        with pytest.raises(WorkflowError):
            workflow.read_inputs()
    assert [f.code for f in _faults(workflow)] == ["InputsTooLarge"]
    g1x._drive(workflow)
    assert workflow.phase == "complete"
    receipt = workflow.write_receipt(tmp_path / "receipt.json")
    assert g1x._verdict(tmp_path, receipt) == "accepted"


# --------------------------------------------------------------------------- the call cap


@pytest.mark.usefixtures("owner_world")
def test_the_thirty_third_invoke_is_refused_and_journaled_with_the_binding(tmp_path: Path) -> None:
    workflow = _source_context_world(tmp_path)
    for _ in range(MAX_INVOKES):
        call = workflow.invoke("search_pack", {"query": "subsequent", "source_id": "financial"})
        assert call["status"] == "ok"
    assert _faults(workflow) == []
    retained = len(_audit_files(workflow, "calls"))
    binding = workflow.binding
    with pytest.raises(WorkflowError) as caught:
        workflow.invoke("search_pack", {"query": "subsequent", "source_id": "financial"})
    assert caught.value.code == "not_permitted"
    (fault,) = _faults(workflow)
    assert (fault.code, fault.cap, fault.call_kind) == ("CallLimit", MAX_INVOKES, "invoke")
    assert fault.binding == binding and fault.size is None
    assert workflow.state().invokes_used == MAX_INVOKES
    assert len(_audit_files(workflow, "calls")) == retained  # the refused call left no record


@pytest.mark.usefixtures("owner_world")
def test_a_source_step_holds_thirty_two_invokes_and_faults_on_the_thirty_third(
    tmp_path: Path,
) -> None:
    """Pack-tool calls have their own per-step budget (32); read_inputs and submit stay at 16."""
    workflow = _source_context_world(tmp_path)
    for _ in range(32):
        call = workflow.invoke("search_pack", {"query": "subsequent", "source_id": "financial"})
        assert call["status"] == "ok"
    assert _faults(workflow) == []
    assert workflow.state().invokes_used == 32
    with pytest.raises(WorkflowError) as caught:
        workflow.invoke("search_pack", {"query": "subsequent", "source_id": "financial"})
    assert caught.value.code == "not_permitted"
    (fault,) = _faults(workflow)
    assert (fault.code, fault.cap, fault.call_kind) == ("CallLimit", 32, "invoke")


@pytest.mark.usefixtures("owner_world")
def test_read_inputs_and_submit_still_fault_at_sixteen_with_cap_sixteen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reader = _narrative_world(tmp_path / "read")
    _serve(monkeypatch, _body_of(10))
    for _ in range(16):
        reader.read_inputs()
    with pytest.raises(WorkflowError):
        reader.read_inputs()
    (fault,) = _faults(reader)
    assert (fault.code, fault.cap, fault.call_kind) == ("CallLimit", 16, "read_inputs")

    workflow = financial.before_financials(tmp_path / "submit")[0]
    for _ in range(16):
        assert workflow.submit_review("{}")["status"] == "refused"
    with pytest.raises(WorkflowError):
        workflow.submit_review("{}")
    (fault,) = _faults(workflow)
    assert (fault.code, fault.cap, fault.call_kind) == ("CallLimit", 16, "submit_review")


@pytest.mark.usefixtures("owner_world")
def test_the_cap_binds_the_step_across_repair_epochs_and_a_new_attempt_starts_afresh(
    tmp_path: Path,
) -> None:
    """T5-R2: `_limits` is keyed `(ticket, step)`. A retry inside one attempt (a new epoch) shares
    the attempt's budget; attempt 1 of the step is a new ticket with a new budget."""
    workflow = _source_context_world(tmp_path)
    first = workflow.binding

    def reads() -> None:
        for source in ("identity", "financial"):
            page = {"source_id": source, "first_page": 1, "last_page": 1}
            assert workflow.invoke("read_pages", page)["status"] == "ok"
        search = workflow.invoke("search_pack", {"query": "subsequent", "source_id": "financial"})
        assert search["status"] == "ok"

    reads()
    assert workflow.submit_review("{}")["status"] == "invalid"  # try 2 of attempt 0: same ticket
    retry = workflow.binding  # the snapshot moved on; the ticket and attempt did not
    assert (retry.ticket_id, retry.attempt) == (first.ticket_id, first.attempt)
    assert workflow.state().invokes_used == 3
    reads()
    for _ in range(MAX_INVOKES - 6):
        workflow.invoke("search_pack", {"query": "subsequent", "source_id": "financial"})
    assert workflow.state().invokes_used == MAX_INVOKES  # both epochs drew on one budget
    at_cap = workflow.binding
    with pytest.raises(WorkflowError):
        workflow.invoke("search_pack", {"query": "subsequent", "source_id": "financial"})
    assert workflow.submit_review("{}")["status"] == "invalid"  # attempt 0 is spent
    second = workflow.binding
    assert (second.attempt, second.ticket_id != first.ticket_id) == (1, True)
    assert workflow.state().invokes_used == 0
    assert workflow.invoke("search_pack", {"query": "x", "source_id": "financial"})["status"]
    (fault,) = _faults(workflow)
    assert fault.code == "CallLimit" and fault.binding == at_cap


@pytest.mark.usefixtures("owner_world")
def test_a_read_and_a_submit_past_the_cap_are_journaled_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reader = _narrative_world(tmp_path / "read")
    _serve(monkeypatch, _body_of(10))
    for _ in range(MAX_CALLS):
        reader.read_inputs()
    with pytest.raises(WorkflowError) as caught:
        reader.read_inputs()
    assert caught.value.code == "not_permitted"
    (fault,) = _faults(reader)
    assert (fault.code, fault.call_kind) == ("CallLimit", "read_inputs")
    assert fault.binding == reader.binding

    submitter, _ = financial.before_financials(tmp_path / "submit"), None
    workflow = submitter[0]
    for _ in range(MAX_CALLS):  # a refused submit is counted against the cap
        assert workflow.submit_review("{}")["status"] == "refused"
    with pytest.raises(WorkflowError) as again:
        workflow.submit_review("{}")
    assert again.value.code == "not_permitted"
    (fault,) = _faults(workflow)
    assert (fault.code, fault.call_kind) == ("CallLimit", "submit_review")


# ----------------------------------------------------------------------- the loop's stop

NARRATIVE_ANSWERS = ("source_readiness", "source_context", "financials", "narrative")


def _oversized_narrative(monkeypatch: pytest.MonkeyPatch) -> None:
    real = owner._inputs
    body = _body_of(CAP + 1)
    digest = hashlib.sha256(body.encode()).hexdigest()

    def served(store: Any, binding: Any, spec: Any) -> tuple[str, str]:
        if spec.step_id == "narrative":
            return digest, body
        result: tuple[str, str] = real(store, binding, spec)
        return result

    monkeypatch.setattr(owner, "_inputs", served)


def test_the_loop_stops_on_an_oversized_read_by_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _oversized_narrative(monkeypatch)
    authored = o2_case.author(tmp_path, answers=NARRATIVE_ANSWERS)
    outcome, run_dir = authored.outcome, authored.run_dir
    assert outcome.outcome == "stopped"
    assert outcome.stopped_reason is not None
    assert outcome.stopped_reason.startswith("InputsTooLarge")
    assert not outcome.stopped_reason.startswith("workflow:")
    run = json.loads((run_dir / "run.json").read_text())
    assert run["outcome"] == "stopped" and run["stopped_reason"].startswith("InputsTooLarge")
    assert not (run_dir / "owner-run.json").exists()
    assert MARKER not in (run_dir / "run.json").read_text()
    records = [json.loads(line) for line in (run_dir / "calls.jsonl").read_text().splitlines()]
    assert records[-1]["error_class"] == "InputsTooLarge" and "InputsTooLarge" in LOOP_STOPS
    assert records[-1]["tool_calls"][-1]["refusal_code"] == "InputsTooLarge"
    faults = (run_dir / "execution" / AUDIT / "faults").iterdir()
    (fault,) = [OwnerFault.model_validate_json(p.read_bytes()) for p in faults]
    assert (fault.code, fault.size, fault.cap) == ("InputsTooLarge", CAP + 1, CAP)
    for stored in (run_dir / "execution").rglob("*"):
        if stored.is_file() and AUDIT in stored.parts:
            assert MARKER.encode() not in stored.read_bytes(), stored


def test_the_loop_stops_on_the_call_cap_by_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The workflow's `CallLimit` fault and the loop's own `CallLimit` stop agree: the model asks
    for one call past a kind's cap and the run stops under that name."""

    class Searcher(o2_case.ScriptAdapter):
        def _plan(self, step_id: str, reads: list[str]) -> list[tuple[str, dict[str, Any]]]:
            if step_id != "source_readiness":
                return super()._plan(step_id, reads)
            search = ("search_pack", {"query": "subsequent", "source_id": "financial"})
            return [search] * (MAX_INVOKES + 1)

    recordings = tmp_path / "recordings"
    recordings.mkdir()
    checked, run_dir = replays.checked_run(tmp_path, o2_case.RUN_ID)
    stage_sources(checked, run_dir)
    script = Searcher(recordings, ("source_readiness",), run_dir / "execution", o2_case.MODEL)
    outcome = rp._run_pathway(checked, run_dir, script, o2_case.test_prompt_for)
    assert outcome.outcome == "stopped"
    assert outcome.stopped_reason is not None and outcome.stopped_reason.startswith("CallLimit")
    assert not (run_dir / "owner-run.json").exists()


def test_a_stopped_run_with_an_inputs_too_large_fault_still_replays_its_earlier_modules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T5-R6: the faults record is outside the compared call bodies of replay (Task 4)."""
    _oversized_narrative(monkeypatch)
    authored = o2_case.author(tmp_path / "earlier", answers=NARRATIVE_ANSWERS)
    earlier = authored.run_dir
    assert authored.outcome.stopped_reason is not None
    assert authored.outcome.stopped_reason.startswith("InputsTooLarge")
    monkeypatch.undo()
    outcome, _ = replays.rerun_private(tmp_path / "rerun", earlier, frozenset({"CP-1"}))
    assert outcome.outcome == "stopped"
    assert outcome.stopped_reason is not None
    assert outcome.stopped_reason.startswith("RecordingMissing")  # CP-1 is live, CP-0 replayed
    assert {r.module_id for r in replays.replay_records(outcome.run_dir)} == {"CP-0"}
    assert len(list((earlier / "execution" / AUDIT / "faults").iterdir())) == 1


# ------------------------------------------------- G7: errors reach the journal (log and re-raise)


def _internal_faults(workflow: Any) -> list[OwnerFault]:
    return [f for f in _faults(workflow) if f.code == "InternalError"]


def _boom(*args: Any, **kwargs: Any) -> Any:
    raise RuntimeError("boom")


def _read_world(root: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setattr(financial, "start", _owner_start)
    return _narrative_world(root)


def test_read_inputs_logs_an_internal_error_then_reraises_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = _read_world(tmp_path, monkeypatch)
    monkeypatch.setattr(owner, "_inputs", _boom)
    with pytest.raises(RuntimeError, match="^boom$"):
        workflow.read_inputs()
    (fault,) = _faults(workflow)
    assert (fault.code, fault.operation, fault.error_type, fault.detail) == (
        "InternalError",
        "read_inputs",
        "RuntimeError",
        "boom",
    )
    assert workflow.state().reads_used == 0  # the lock was released: state() answers


def test_submit_review_logs_an_internal_error_then_reraises_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = _read_world(tmp_path, monkeypatch)
    read = workflow.read_inputs()
    monkeypatch.setattr(owner, "submit_model_payload", _boom)
    with pytest.raises(RuntimeError, match="^boom$"):
        workflow.submit_review(json.dumps(financial.narrative(read)))
    (fault,) = _internal_faults(workflow)
    assert (fault.operation, fault.error_type, fault.detail) == (
        "submit_review",
        "RuntimeError",
        "boom",
    )
    assert workflow.state().phase == "analytical"


def test_invoke_logs_an_internal_error_then_reraises_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(financial, "start", _owner_start)
    workflow = _source_context_world(tmp_path)
    monkeypatch.setattr(workflow._session, "invoke", _boom)
    with pytest.raises(RuntimeError, match="^boom$"):
        workflow.invoke("search_pack", {"query": "x", "source_id": "financial"})
    (fault,) = _internal_faults(workflow)
    assert (fault.operation, fault.error_type, fault.detail) == ("invoke", "RuntimeError", "boom")
    workflow.state()


def test_write_receipt_logs_an_internal_error_then_reraises_it(
    cp3: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = refusals._walk(cp3, tmp_path, refusals.ORDER)
    g1x._drive(workflow)
    assert workflow.phase == "complete"
    monkeypatch.setattr(owner, "_verify", _boom)
    with pytest.raises(RuntimeError, match="^boom$"):
        workflow.write_receipt(tmp_path / "receipt.json")
    (fault,) = _internal_faults(workflow)
    assert (fault.operation, fault.error_type, fault.detail) == (
        "write_receipt",
        "RuntimeError",
        "boom",
    )
    assert workflow.state().phase == "complete"


def test_the_fault_detail_is_bounded_and_control_characters_are_escaped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = _read_world(tmp_path, monkeypatch)

    def noisy(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("a\nb\x00c\x1b[0m" + "z" * 1000)

    monkeypatch.setattr(owner, "_inputs", noisy)
    with pytest.raises(RuntimeError):
        workflow.read_inputs()
    (fault,) = _internal_faults(workflow)
    assert fault.detail is not None and len(fault.detail) == 500
    assert fault.detail.startswith("a\\x0ab\\x00c\\x1b[0mz")
    assert all(ord(c) >= 32 and ord(c) != 127 for c in fault.detail)


def test_a_workflow_refusal_and_a_source_error_keep_their_codes_and_write_no_fault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = _read_world(tmp_path, monkeypatch)
    with pytest.raises(WorkflowError) as refused:
        workflow.submit_review("{}")  # not read yet: a precondition refusal
    assert refused.value.code == "not_permitted"

    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise SourceError("bad_arguments")

    monkeypatch.setattr(owner, "_inputs", refuse)
    with pytest.raises(SourceError) as source:
        workflow.read_inputs()
    assert source.value.code == "bad_arguments"
    assert _faults(workflow) == []


def test_a_failed_fault_write_leaves_the_original_error_and_chains_the_write_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    workflow = _read_world(tmp_path, monkeypatch)
    monkeypatch.setattr(owner, "_inputs", _boom)
    audit = workflow._store.directory / AUDIT
    (audit / "faults").mkdir(exist_ok=True)
    os.chmod(audit / "faults", 0o500)  # read-only: the fault cannot be written
    try:
        with (
            caplog.at_level(logging.ERROR, logger=owner.__name__),
            pytest.raises(RuntimeError, match="^boom$") as caught,
        ):
            workflow.read_inputs()
    finally:
        os.chmod(audit / "faults", 0o700)
    assert isinstance(caught.value.__context__, OSError)
    assert _faults(workflow) == []
    assert any("InternalError" in record.getMessage() for record in caplog.records)


def test_an_internal_value_error_in_the_gate_propagates_and_is_not_relabelled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(financial, "start", _owner_start)
    workflow, pack = financial.start(tmp_path)
    financial.read_sources(workflow)

    def gate(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("x")

    monkeypatch.setattr(owner, "_gate", gate)
    with pytest.raises(ValueError, match="^x$"):
        workflow.submit_review(financial.readiness(pack))
    (fault,) = _internal_faults(workflow)
    assert (fault.operation, fault.error_type, fault.detail) == ("submit_review", "ValueError", "x")


def test_the_transport_ends_on_an_internal_error_with_no_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(financial, "start", _owner_start)
    workflow, pack = financial.start(tmp_path)

    def gate(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("x")

    monkeypatch.setattr(owner, "_gate", gate)
    request = json.dumps({"operation": "submit_review", "payload": financial.readiness(pack)})
    out = io.StringIO()
    with pytest.raises(ValueError, match="^x$"):
        owner.serve_json_lines(
            workflow,
            io.StringIO(request + "\n" + request + "\n"),
            out,
            destination=tmp_path / "receipt.json",
            participant="external-model",
        )
    assert out.getvalue() == ""  # the participant sees end of stream, not a label
    assert [f.operation for f in _internal_faults(workflow)] == ["submit_review"]


def test_a_source_session_internal_error_receipt_is_unchanged_and_journals_a_fault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F9: `SourceSession.invoke` returns an `internal_error` receipt; the owner retains a fault."""
    monkeypatch.setattr(financial, "start", _owner_start)
    workflow = _source_context_world(tmp_path)
    monkeypatch.setattr(SourceTools, "stage", _boom)
    receipt = workflow.invoke("search_pack", {"query": "x", "source_id": "financial"})
    assert (receipt["status"], receipt["error_code"]) == ("error", "internal_error")
    assert receipt["body"] is None
    (fault,) = _internal_faults(workflow)
    assert (fault.operation, fault.error_type) == ("invoke", None)
    assert workflow.state().invokes_used == 1


# -------------------------------------------------------- the transport's request-shape table


def _nested(depth: int) -> str:
    """JSON text of an invoke request whose total nesting depth is `depth` (the request is 1)."""
    inner = "[" * (depth - 2) + "]" * (depth - 2)
    return (
        '{"operation":"invoke","tool":"no_such_tool","arguments":{"k":' + inner + "}}"
        if depth > 2
        else '{"operation":"invoke","tool":"no_such_tool","arguments":{}}'
    )


def _serve_lines(workflow: Any, root: Path, text: str) -> list[dict[str, Any]]:
    out = io.StringIO()
    owner.serve_json_lines(
        workflow,
        io.StringIO(text),
        out,
        destination=root / "receipt.json",
        participant="external-model",
    )
    return [json.loads(line) for line in out.getvalue().splitlines()]


SHAPES = {
    "invalid json": "{not json",
    "a json list": "[]",
    "a json scalar": "3",
    "payload not a str": '{"operation":"submit_review","payload":3}',
    "NaN": '{"operation":"invoke","tool":"read_pages","arguments":{"value":NaN}}',
    "an overflowing float": '{"operation":"invoke","tool":"read_pages","arguments":{"v":1e999}}',
    "a lone-surrogate payload": '{"operation":"submit_review","payload":"\\ud800"}',
    "an unknown extra key": '{"operation":"read_inputs","extra":1}',
    "a missing key": '{"operation":"invoke","tool":"read_pages"}',
    "nested past the bound": _nested(MAX_JSON_DEPTH + 1),
    "nested far past the bound": "[" * 100_000,
    "an over-length line": "x" * (MAX_LINE + 2),
}


@pytest.mark.parametrize("name", sorted(SHAPES))
def test_a_malformed_request_is_bad_arguments_in_the_transport_and_writes_no_fault(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(financial, "start", _owner_start)
    workflow, _ = financial.start(tmp_path)
    answers = _serve_lines(workflow, tmp_path, SHAPES[name] + "\n")
    assert answers == [{"status": "refused", "error_code": "bad_arguments"}]
    assert _faults(workflow) == []


def test_the_transport_answers_the_next_line_after_a_malformed_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(financial, "start", _owner_start)
    workflow, _ = financial.start(tmp_path)
    answers = _serve_lines(workflow, tmp_path, "[]\n" + '{"operation":"read_inputs"}\n')
    assert [a["error_code"] for a in answers] == ["bad_arguments", "not_permitted"]


def test_an_unknown_operation_is_still_not_permitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(financial, "start", _owner_start)
    workflow, _ = financial.start(tmp_path)
    answers = _serve_lines(workflow, tmp_path, '{"operation":"nope"}\n')
    assert answers == [{"status": "refused", "error_code": "not_permitted"}]


def test_the_depth_bound_is_exact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(financial, "start", _owner_start)
    workflow, _ = financial.start(tmp_path / "at")
    (at_bound,) = _serve_lines(workflow, tmp_path, _nested(MAX_JSON_DEPTH) + "\n")
    assert at_bound["status"] == "refused" and at_bound["error_code"] == "not_permitted"  # reached
    past_workflow, _ = financial.start(tmp_path / "past")
    (past,) = _serve_lines(past_workflow, tmp_path, _nested(MAX_JSON_DEPTH + 1) + "\n")
    assert past == {"status": "refused", "error_code": "bad_arguments"}
    assert _faults(workflow) == [] and _faults(past_workflow) == []


# ------------------------------------- H05 / item 88: the host's frames reach the host


def _host_frames() -> dict[str, str]:
    """Frames `tests/test_host_frames.py` pins: each reaches the host, which answers a retained
    receipt (a tool that is not a str, arguments that are a list, a lone surrogate in a query,
    key or tool name, and `arguments` at, one over and far over the host's depth bound)."""

    def search(arguments: str) -> str:
        return '{"operation":"invoke","tool":"search_pack","arguments":' + arguments + "}"

    def deep(levels: int) -> str:
        return search('{"query":"x","extra":' + "[" * levels + "0" + "]" * levels + "}")

    return {
        "tool not a str": '{"operation":"invoke","tool":3,"arguments":{}}',
        "arguments a list": '{"operation":"invoke","tool":"read_pages","arguments":[]}',
        "surrogate tool": '{"operation":"invoke","tool":"\\ud800","arguments":{}}',
        "surrogate query": search('{"query":"\\ud800"}'),
        "surrogate key": search('{"query":"x","\\ud800":1}'),
        "at the host bound": deep(MAX_ARGUMENT_DEPTH - 1),
        "one over the host bound": deep(MAX_ARGUMENT_DEPTH),
        "far over the host bound": deep(2 * MAX_ARGUMENT_DEPTH + 10),
    }


def test_the_parser_guard_lies_above_every_host_frame_and_below_the_parser_limit() -> None:
    deepest = max(owner._depth_of(json.loads(frame)) for frame in _host_frames().values())
    assert MAX_JSON_DEPTH == 256 and deepest < MAX_JSON_DEPTH < sys.getrecursionlimit()
    # H05's own deepest frame (210 argument levels, request depth 212) is one of them
    assert owner._depth_of(json.loads(_host_frames()["far over the host bound"])) > 200


@pytest.mark.parametrize("name", sorted(_host_frames()))
def test_a_host_frame_reaches_the_host_and_is_retained(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(financial, "start", _owner_start)
    workflow, _ = financial.start(tmp_path)
    (reply,) = _serve_lines(workflow, tmp_path, _host_frames()[name] + "\n")
    assert reply["status"] == "refused" and "call_id" in reply, reply  # a receipt, not a label
    assert len(workflow._calls) == 1 and workflow.state().invokes_used == 1
    assert len(_audit_files(workflow, "calls")) == 1 and _faults(workflow) == []


# ------------------------------------------------------------ the fault record's detail (G7)

KEY = "sk-ant-api03-" + "Q" * 40


def _raise_in_inputs(monkeypatch: pytest.MonkeyPatch, error: BaseException) -> None:
    def raiser(*args: Any, **kwargs: Any) -> Any:
        raise error

    monkeypatch.setattr(owner, "_inputs", raiser)


def _detail_of(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: BaseException) -> str:
    workflow = _read_world(tmp_path, monkeypatch)
    _raise_in_inputs(monkeypatch, error)
    with pytest.raises(type(error)):
        workflow.read_inputs()
    (fault,) = _internal_faults(workflow)
    assert fault.detail is not None
    return fault.detail


def test_a_key_in_the_error_text_is_redacted_before_the_cut(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    detail = _detail_of(tmp_path, monkeypatch, RuntimeError(f"Authorization: Bearer {KEY}"))
    assert KEY not in detail and "[redacted]" in detail
    straddling = RuntimeError(
        "z" * 489 + " " + KEY
    )  # the key starts before char 500 and ends after it
    detail = _detail_of(tmp_path / "cut", monkeypatch, straddling)
    assert "sk-ant" not in detail and detail.endswith("[redacted]")


def test_controls_separators_and_format_characters_are_escaped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    detail = _detail_of(tmp_path, monkeypatch, RuntimeError("a\x85b\x9bc\u2028d\u2029e\u202ef"))
    assert detail == "a\\x85b\\x9bc\\u2028d\\u2029e\\u202ef"
    assert all(unicodedata.category(c) not in ("Cc", "Zl", "Zp", "Cf") for c in detail)


def test_the_c0_edges_and_del_are_escaped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    detail = _detail_of(tmp_path, monkeypatch, RuntimeError("a\x1fb\x7fc\x20d"))
    assert detail == "a\\x1fb\\x7fc d"


def test_a_lone_surrogate_in_the_message_is_escaped_and_the_original_raised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = _read_world(tmp_path, monkeypatch)
    _raise_in_inputs(monkeypatch, RuntimeError("a\ud800b\udfffc"))
    with pytest.raises(RuntimeError, match="^a\ud800b\udfffc$"):
        workflow.read_inputs()
    (fault,) = _internal_faults(workflow)
    assert fault.detail == "a\\ud800b\\udfffc"


def test_the_escaping_is_injective_for_a_backslash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    newline = _detail_of(tmp_path / "one", monkeypatch, RuntimeError("a\nb"))
    literal = _detail_of(tmp_path / "two", monkeypatch, RuntimeError("a\\x0ab"))
    assert newline == "a\\x0ab" and literal == "a\\x5cx0ab" and newline != literal


def test_the_bound_is_500_after_redaction_and_escaping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    detail = _detail_of(tmp_path, monkeypatch, RuntimeError("z" * 499 + "\n" + "y" * 100))
    assert len(detail) == 500 and detail.endswith("\\")  # cut inside the escape of the newline


def test_an_error_whose_text_raises_still_leaves_its_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Odd(RuntimeError):
        def __str__(self) -> str:
            raise TypeError("no text")

    workflow = _read_world(tmp_path, monkeypatch)
    _raise_in_inputs(monkeypatch, Odd())
    with pytest.raises(Odd):
        workflow.read_inputs()
    (fault,) = _internal_faults(workflow)
    assert (fault.error_type, fault.detail) == ("Odd", "<unprintable Odd>")


def test_the_fault_is_written_before_the_reraise_under_the_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = _read_world(tmp_path, monkeypatch)
    seen: list[bool] = []
    real = owner._retain

    def retain(store: Any, kind: str, value: Any) -> None:
        if kind == "faults":
            seen.append(workflow._operation.locked())
        real(store, kind, value)

    monkeypatch.setattr(owner, "_retain", retain)
    _raise_in_inputs(monkeypatch, RuntimeError("boom"))
    with pytest.raises(RuntimeError):
        workflow.read_inputs()
    assert seen == [True] and len(_internal_faults(workflow)) == 1
    assert not workflow._operation.locked()


def test_an_internal_error_in_publish_is_journaled_and_ends_the_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`publish`'s inner catch is fail-closed; an error outside it (here `_current`) is journaled."""
    monkeypatch.setattr(financial, "start", _owner_start)
    workflow, _ = financial.start(tmp_path)
    monkeypatch.setattr(workflow, "_current", _boom)
    out = io.StringIO()
    with pytest.raises(RuntimeError):
        owner.serve_json_lines(
            workflow,
            io.StringIO('{"operation":"publish"}\n'),
            out,
            destination=tmp_path / "r.json",
            participant="p",
        )
    assert out.getvalue() == ""
    assert [(f.code, f.operation) for f in _faults(workflow)] == [("InternalError", "publish")]


def test_a_drained_line_that_is_not_utf8_is_answered_bad_arguments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(financial, "start", _owner_start)
    workflow, _ = financial.start(tmp_path)
    raw = b"x" * (MAX_LINE + 2) + b"y" * 50_000 + b"\xff\n" + b'{"operation":"nope"}\n'
    answers = _serve_lines_from(
        workflow, tmp_path, io.TextIOWrapper(io.BytesIO(raw), encoding="utf-8")
    )
    assert answers[0] == {"status": "refused", "error_code": "bad_arguments"}
    assert _faults(workflow) == []


def _serve_lines_from(workflow: Any, root: Path, reader: Any) -> list[dict[str, Any]]:
    out = io.StringIO()
    owner.serve_json_lines(
        workflow, reader, out, destination=root / "receipt.json", participant="external-model"
    )
    return [json.loads(line) for line in out.getvalue().splitlines()]


def test_fill_at_binding_maps_any_os_error_to_identity_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def denied(*args: Any, **kwargs: Any) -> Any:
        raise PermissionError("denied")

    stand_in: Any = object()  # `_hist` and `_fill` are replaced, so no store is read
    monkeypatch.setattr(owner, "_hist", lambda store, binding: stand_in)
    monkeypatch.setattr(owner, "_fill", denied)
    with pytest.raises(WorkflowError) as caught:
        owner.fill_at_binding(stand_in, stand_in, "{}")
    assert caught.value.code == "identity_mismatch"


# ----------------------------------- steps with no source session: the transport answers (T6-R12)


def _script_to_narrative(root: Path, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The JSON lines that take a fresh owner workflow to `narrative` (no source session), the
    read included: the operations of the test world, recorded as the transport would receive them."""
    lines: list[str] = []
    cls = owner.OwnerWorkflow
    real = {n: getattr(cls, n) for n in ("invoke", "read_inputs", "submit_review")}

    def invoke(self: Any, tool: Any, arguments: Any) -> Any:
        lines.append(json.dumps({"operation": "invoke", "tool": tool, "arguments": arguments}))
        return real["invoke"](self, tool, arguments)

    def read_inputs(self: Any) -> Any:
        lines.append(json.dumps({"operation": "read_inputs"}))
        return real["read_inputs"](self)

    def submit_review(self: Any, payload: Any) -> Any:
        lines.append(json.dumps({"operation": "submit_review", "payload": payload}))
        return real["submit_review"](self, payload)

    with monkeypatch.context() as patch:
        patch.setattr(cls, "invoke", invoke)
        patch.setattr(cls, "read_inputs", read_inputs)
        patch.setattr(cls, "submit_review", submit_review)
        _narrative_world(root).read_inputs()
    return lines


def _levels(count: int) -> str:
    return (
        '{"operation":"invoke","tool":"x","arguments":{"q":'
        + "[" * count
        + "0"
        + "]" * count
        + "}}"
    )


SESSIONLESS_FRAMES = {
    "tool not a str": '{"operation":"invoke","tool":3,"arguments":{}}',
    "arguments a list": '{"operation":"invoke","tool":"read_pages","arguments":[1]}',
    "surrogate tool": '{"operation":"invoke","tool":"\\ud800","arguments":{}}',
    "surrogate query": '{"operation":"invoke","tool":"search_pack","arguments":{"query":"\\ud800"}}',
    "surrogate key": '{"operation":"invoke","tool":"x","arguments":{"\\ud800":1}}',
    "deep 199": _levels(199),
    "deep 250": _levels(250),
    "one over the host bound": _levels(MAX_ARGUMENT_DEPTH),  # arguments depth host bound + 1
}


@pytest.mark.parametrize("name", sorted(SESSIONLESS_FRAMES))
def test_a_frame_the_host_would_refuse_is_refused_by_the_transport_at_a_sessionless_step(
    name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(financial, "start", _owner_start)
    script = _script_to_narrative(tmp_path / "record", monkeypatch)
    workflow, _ = _owner_start(tmp_path / "served")
    text = "".join(
        line + "\n" for line in [*script, SESSIONLESS_FRAMES[name], '{"operation":"nope"}']
    )
    answers = _serve_lines(workflow, tmp_path, text)  # an internal error would end the stream
    assert workflow.binding.step_id == "narrative" and workflow._session is None
    assert len(answers) == len(script) + 2
    assert answers[-2] == {"status": "refused", "error_code": "bad_arguments"}
    assert answers[-1]["error_code"] == "not_permitted"
    assert _internal_faults(workflow) == []


def test_a_sessionless_invoke_at_the_host_bound_still_reaches_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(financial, "start", _owner_start)
    script = _script_to_narrative(tmp_path / "record", monkeypatch)
    workflow, _ = _owner_start(tmp_path / "served")
    at_bound = _levels(MAX_ARGUMENT_DEPTH - 1)  # arguments depth equals the host bound
    answers = _serve_lines(workflow, tmp_path, "".join(line + "\n" for line in [*script, at_bound]))
    assert answers[-1]["status"] == "refused" and "call_id" in answers[-1]


def test_the_unprintable_fallback_is_logged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    class Odd(RuntimeError):
        def __str__(self) -> str:
            raise TypeError("no text")

    workflow = _read_world(tmp_path, monkeypatch)
    _raise_in_inputs(monkeypatch, Odd())
    with caplog.at_level(logging.ERROR, logger=owner.__name__), pytest.raises(Odd):
        workflow.read_inputs()
    logged = [r for r in caplog.records if r.name == owner.__name__ and "Odd" in r.getMessage()]
    assert logged and logged[0].exc_info is not None and logged[0].exc_info[0] is TypeError


def test_a_code_point_above_the_bmp_is_escaped_with_eight_digits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    detail = _detail_of(tmp_path, monkeypatch, RuntimeError("a\U000e0001b"))  # a Cf tag character
    assert detail == "a\\U000e0001b"
