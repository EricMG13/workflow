"""O3 Task 4 (G4): a rerun after repair replays the retained upstream submissions.

The earlier runs are authored from the frozen ``cases/o2-synthetic`` payloads through ``o2_case``'s
``ScriptAdapter`` (CP-0 settled, then the script ends and CP-1 stops the run on a missing recording:
the fast world, P19). The rerun repairs ``CP-1``: CP-0 is replayed, CP-1 runs live. Tests that need
the walk past CP-1 are gated by ``RUN_PROMOTION`` and written, never run here (B16, T4-R1).
Part A is the plan and the refusals, part B the replay of a module, part C the rerun through
``run_pathway``.
"""

import dataclasses
import hashlib
import http.client
import json
import os
import shutil
import socket
from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, NoReturn, cast

import o2_case
import pytest
from pydantic import BaseModel

from deploy_vii.contracts import PREFILLED_MARKER
from deploy_vii.execution import Execution
from deploy_vii.preparation import load_pack
from deploy_workflow import replay
from deploy_workflow import run_pathway as rp
from deploy_workflow.financial_workflow import _filled
from deploy_workflow.model import transport as transport_module
from deploy_workflow.model.adapter import recorded_adapter
from deploy_workflow.owner_workflow import (
    AUDIT,
    OWNER_SPECS,
    OwnerCall,
    OwnerFault,
    OwnerRunReceipt,
    OwnerSubmission,
    OwnerWorkflow,
    verify_owner_run_receipt,
)
from deploy_workflow.replay import (
    REBOUND_FIELDS,
    REBOUND_HOLDER,
    ReplayDiverged,
    ReplayPackChanged,
    ReplayRecord,
    ReplayRefused,
    ReplayRejected,
)
from deploy_workflow.run_inputs import CaseSource, RunInputError, check_arguments, stage_sources
from deploy_workflow.run_pathway import run_pathway

EARLIER_ID = o2_case.RUN_ID  # the frozen payloads bind the pack of this run id
RERUN_ID = "o2-synthetic-rerun"
PLANNED = ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-MODEL", "CP-3", "CP-5", "CP-6", "CP-8")


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("a test reached the network")

    monkeypatch.setattr(http.client, "HTTPSConnection", refuse)
    monkeypatch.setattr(http.client, "HTTPConnection", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(transport_module, "_default_connection", refuse)


# ================================================================================== part A
# the worlds, the plan and the refusals


class CallingScript(o2_case.ScriptAdapter):
    """CP-0 reads a page and searches the pack before it submits: retained calls to replay."""

    def _plan(self, step_id: str, reads: list[str]) -> list[tuple[str, dict[str, Any]]]:
        plan = super()._plan(step_id, reads)
        if step_id != "source_readiness":
            return plan
        return [
            ("read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}),
            ("search_pack", {"query": "subsequent", "source_id": "financial"}),
            *plan,
        ]


def checked_run(
    root: Path, run_id: str, sources: list[CaseSource] | None = None
) -> tuple[Any, Path]:
    """``check_arguments`` over the o2 case under ``root`` (nothing is written): the checked run
    and the run directory it would stage."""
    empty = root / "check-recordings"
    empty.mkdir(parents=True, exist_ok=True)
    run_dir = root / "run"
    checked = check_arguments(
        case_id=o2_case.CASE_ID,
        sources=o2_case.case_sources() if sources is None else sources,
        context=o2_case.CASE / "context.json",
        pathway=o2_case.PATHWAY,
        model=o2_case.MODEL,
        adapter=recorded_adapter(o2_case.MODEL, empty),
        cap_usd=o2_case.CAP,
        run_dir=run_dir,
        run_id=run_id,
    )
    return checked, run_dir


def author_earlier(
    root: Path,
    *,
    run_id: str = EARLIER_ID,
    script: type[o2_case.ScriptAdapter] = CallingScript,
    cap: Decimal | None = None,
) -> Path:
    """An earlier run: the script answers CP-0 and the run stops at the next request."""
    checked, run_dir = checked_run(root, run_id)
    if cap is not None:
        checked = dataclasses.replace(checked, cap_usd=cap)
    stage_sources(checked, run_dir)
    recordings = root / "recordings"
    recordings.mkdir()
    adapter = script(recordings, ("source_readiness",), run_dir / "execution", o2_case.MODEL)
    outcome = rp._run_pathway(checked, run_dir, adapter, o2_case.test_prompt_for)
    assert outcome.outcome == "stopped"
    return run_dir


def audit(run_dir: Path, kind: str) -> list[Path]:
    folder = run_dir / "execution" / AUDIT / kind
    return sorted(folder.iterdir()) if folder.is_dir() else []


def copy_of(earlier: Path, tmp_path: Path) -> Path:
    copy = tmp_path / "copy"
    shutil.copytree(earlier, copy)
    return copy


@pytest.fixture
def earlier_run(tmp_path: Path) -> Path:
    return author_earlier(tmp_path / "earlier")


@pytest.mark.parametrize(
    ("repaired", "replayed", "live"),
    [
        ("CP-3", ("CP-0", "CP-1", "CP-1A", "CP-2"), ("CP-3", "CP-5", "CP-6", "CP-8")),
        ("CP-2", ("CP-0", "CP-1", "CP-1A"), ("CP-2", "CP-3", "CP-5", "CP-6", "CP-8")),
        # CP-1A cites CP-1 figures though its registry edge is CP-0 only: it follows CP-1
        ("CP-1", ("CP-0",), ("CP-1", "CP-1A", "CP-2", "CP-3", "CP-5", "CP-6", "CP-8")),
        ("CP-6", ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-3", "CP-5"), ("CP-6", "CP-8")),
    ],
)
def test_live_is_the_repaired_modules_and_their_downstream(
    repaired: str,
    replayed: tuple[str, ...],
    live: tuple[str, ...],
    earlier_run: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The graph is the registry's (plus the context producer edge). The earlier run is made to
    hold every module, so only the graph decides; CP-MODEL is never replayed or listed."""
    monkeypatch.setattr(replay._Earlier, "unusable", lambda self, module: None)
    found = replay.plan_replay(earlier_run, PLANNED, frozenset({repaired}))
    assert (found.replayed, found.live, found.unreplayable) == (replayed, live, ())
    assert "CP-MODEL" not in found.replayed + found.live


def test_plan_goes_live_for_a_module_the_earlier_run_never_settled(earlier_run: Path) -> None:
    found = replay.plan_replay(earlier_run, PLANNED, frozenset({"CP-3"}))
    assert found.replayed == ("CP-0",)  # CP-1 was never settled in the earlier run
    reasons = dict(found.unreplayable)
    assert "CP-1" in reasons and "no settled, valid attempt" in reasons["CP-1"]
    assert found.live == ("CP-1", "CP-1A", "CP-2", "CP-3", "CP-5", "CP-6", "CP-8")
    assert found.earlier_run_id == EARLIER_ID
    with pytest.raises(ReplayRefused):
        replay.plan_replay(earlier_run, PLANNED, frozenset())
    with pytest.raises(ReplayRefused):
        replay.plan_replay(earlier_run, PLANNED, frozenset({"CP-MODEL"}))


@pytest.mark.parametrize(
    "case",
    [
        "no-repaired",
        "no-replay-from",
        "missing-replay-from",
        "replay-from-is-run-dir",
        "same-run-id",
        "unplanned-module",
        "publisher-module",
        "no-execution",
    ],
)
def test_check_replay_refuses_and_writes_nothing(
    case: str, tmp_path: Path, earlier_run: Path
) -> None:
    run_id = EARLIER_ID if case == "same-run-id" else RERUN_ID
    checked, run_dir = checked_run(tmp_path / "rerun", run_id)
    repaired = frozenset({"CP-1"})
    earlier: Path | None = earlier_run
    if case == "no-repaired":
        repaired = frozenset()
    elif case == "no-replay-from":
        earlier = None
    elif case == "missing-replay-from":
        earlier = tmp_path / "no-such-run"
    elif case == "replay-from-is-run-dir":
        run_dir = earlier_run
    elif case == "unplanned-module":
        repaired = frozenset({"CP-6A"})
    elif case == "publisher-module":
        repaired = frozenset({"CP-MODEL"})
    elif case == "no-execution":
        earlier = tmp_path / "bare"
        earlier.mkdir()
        (earlier / "run.json").write_text("{}")
    with pytest.raises(RunInputError):
        replay.check_replay(checked, run_dir, earlier, repaired)
    assert not (tmp_path / "rerun" / "run").exists()


def test_a_torn_call_record_refuses_the_rerun(tmp_path: Path, earlier_run: Path) -> None:
    copy = copy_of(earlier_run, tmp_path)
    path = audit(copy, "calls")[0]
    path.write_text(path.read_text() + " ")
    checked, run_dir = checked_run(tmp_path / "rerun", RERUN_ID)
    with pytest.raises(ReplayRefused, match="torn"):
        replay.check_replay(checked, run_dir, copy, frozenset({"CP-1"}))


def test_a_changed_source_set_is_refused_and_nothing_is_left_behind(
    tmp_path: Path, earlier_run: Path
) -> None:
    sources = o2_case.case_sources()
    extra = tmp_path / "extra.txt"
    extra.write_text("Another source.\n")
    changed = tmp_path / "business-changed.txt"
    changed.write_text(sources[2].path.read_text() + "One more sentence.\n")
    variants = {
        "added": [*sources, CaseSource("extra", extra, "text/plain")],
        "dropped": sources[:-1],
        "changed": [*sources[:2], CaseSource("business", changed, "text/plain"), sources[3]],
    }
    for name, edited in variants.items():
        checked, run_dir = checked_run(tmp_path / name, RERUN_ID, edited)
        with pytest.raises(ReplayPackChanged):
            replay.check_replay(checked, run_dir, earlier_run, frozenset({"CP-1"}))
        assert [p.name for p in (tmp_path / name).iterdir()] == ["check-recordings"], name
    checked, run_dir = checked_run(tmp_path / "same", RERUN_ID)
    assert replay.check_replay(checked, run_dir, earlier_run, frozenset({"CP-1"})).replayed == (
        "CP-0",
    )


PACK_FIELDS = {
    "spans": lambda s: s.model_copy(update={"spans": s.spans[:-1]}),
    "extraction_status": lambda s: s.model_copy(
        update={
            "extraction_status": "degraded" if s.extraction_status == "complete" else "complete"
        }
    ),
    "extractor": lambda s: s.model_copy(update={"extractor": "another-extractor"}),
    "limitation": lambda s: s.model_copy(update={"limitation": "a limitation"}),
    "name": lambda s: s.model_copy(update={"name": "another name"}),
    "media_type": lambda s: s.model_copy(update={"media_type": "application/pdf"}),
    "sha256": lambda s: s.model_copy(update={"sha256": "2" * 64}),
    "status": lambda s: s.model_copy(update={"status": "unreadable"}),
}


@pytest.mark.parametrize("field", list(PACK_FIELDS))
def test_every_source_field_counts_in_the_pack_comparison(field: str, earlier_run: Path) -> None:
    earlier = load_pack(earlier_run / "pack")
    renamed = earlier.model_copy(update={"run": earlier.run.model_copy(update={"run_id": "other"})})
    replay.check_same_pack(earlier, renamed)  # the run id alone is masked
    edited = PACK_FIELDS[field](earlier.sources[0])
    assert edited != earlier.sources[0]
    changed = earlier.model_copy(update={"sources": (edited, *earlier.sources[1:])})
    with pytest.raises(ReplayPackChanged):
        replay.check_same_pack(earlier, changed)


# ================================================================================== part B
# replaying a module into a new run's workflow


class TwiceScript(CallingScript):
    """CP-0 submits an invalid review first (it names another pack), then the frozen one."""

    submitted = 0

    def _plan(self, step_id: str, reads: list[str]) -> list[tuple[str, dict[str, Any]]]:
        plan = super()._plan(step_id, reads)
        if step_id != "source_readiness":
            return plan
        self.submitted += 1
        if self.submitted == 1:
            name, arguments = plan[-1]
            plan[-1] = (name, {**arguments, "pack_sha256": "0" * 64})
        return plan


def new_workflow(root: Path, run_id: str = RERUN_ID) -> tuple[OwnerWorkflow, Path]:
    """The rerun's own workflow over a freshly staged pack, at CP-0's first step."""
    checked, run_dir = checked_run(root, run_id)
    stage_sources(checked, run_dir)
    workflow = OwnerWorkflow.create(
        run_dir / "execution",
        load_pack(run_dir / "pack"),
        publication_directory=run_dir / "publication",
    )
    return workflow, run_dir


def replay_cp0(root: Path, earlier: Path) -> tuple[OwnerWorkflow, Path]:
    workflow, run_dir = new_workflow(root)
    replay.replay_module(workflow, earlier, "CP-0", execution=run_dir / "execution")
    return workflow, run_dir


def replay_records(run_dir: Path) -> list[ReplayRecord]:
    return [
        ReplayRecord.model_validate_json(p.read_bytes())
        for p in audit(run_dir, "replays")
        if json.loads(p.read_bytes())["schema_version"] == "replay/1"
    ]


def submissions(run_dir: Path) -> list[OwnerSubmission]:
    return [
        OwnerSubmission.model_validate_json(p.read_bytes()) for p in audit(run_dir, "submissions")
    ]


def tree_hash(root: Path) -> str:
    """Every path under ``root`` with its type, mode and content."""
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        stat = os.lstat(path)
        digest.update(str(path.relative_to(root)).encode() + b"\0" + oct(stat.st_mode).encode())
        if path.is_file() and not path.is_symlink():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def swap_record(run_dir: Path, kind: str, old: Any, new: Any) -> None:
    """Replace a retained record by a changed one, filed under its own new digest."""
    folder = run_dir / "execution" / AUDIT / kind
    (folder / old.content_hash()).unlink()
    (folder / new.content_hash()).write_bytes(new.model_dump_json().encode())


def edit_call_body(copy: Path) -> OwnerCall:
    """The copy's retained ``read_pages`` call now holds another body (filed under its own digest);
    the edited call."""
    calls = [OwnerCall.model_validate_json(p.read_bytes()) for p in audit(copy, "calls")]
    target = next(c for c in calls if c.tool == "read_pages")
    edited = target.model_copy(update={"body": (target.body or "") + "X"})
    swap_record(copy, "calls", target, edited)
    return edited


def edit_payload(copy: Path, change: Callable[[dict[str, Any]], None]) -> None:
    """The copy's CP-0 submission now carries an edited payload (filed under its own digest)."""
    (submission,) = submissions(copy)
    folder = copy / "execution" / AUDIT / "payloads"
    payload = json.loads((folder / submission.binding.payload_sha256).read_text())
    change(payload)
    text = json.dumps(payload)
    digest = hashlib.sha256(text.encode()).hexdigest()
    (folder / digest).write_text(text)
    moved = submission.binding.model_copy(update={"payload_sha256": digest})
    swap_record(copy, "submissions", submission, submission.model_copy(update={"binding": moved}))


def stage_and_call(root: Path, run_id: str) -> list[dict[str, Any]]:
    workflow, _ = new_workflow(root, run_id)
    return [
        workflow.invoke("read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1}),
        workflow.invoke("search_pack", {"query": "subsequent", "source_id": "financial"}),
        workflow.invoke(
            "read_pages", {"source_id": "financial", "first_page": 99, "last_page": 99}
        ),  # past the end
    ]


def test_step0_cp0_call_bodies_are_run_independent(tmp_path: Path) -> None:
    """Q4: the same CP-0 calls under two run ids differ only in the call id and the binding (which
    holds the run id and the pack hash). The body, the status, the error code and the source
    evidence are equal, so replay compares whole bodies and drops no field."""
    first = stage_and_call(tmp_path / "a", "run-a")
    second = stage_and_call(tmp_path / "b", "run-b")
    assert all(c["body"] for c in first)
    for one, other in zip(first, second, strict=True):
        assert one["binding"]["run_id"] != other["binding"]["run_id"]
        assert one["binding"]["pack_sha256"] != other["binding"]["pack_sha256"]
        differing = {key for key in one if one[key] != other[key]}
        assert differing == {"call_id", "binding"}
        assert one["body"] == other["body"] and one["source_evidence"] == other["source_evidence"]


def test_a_replayed_module_settles_in_the_new_journal_with_the_pack_hash_rebound(
    tmp_path: Path, earlier_run: Path
) -> None:
    before = tree_hash(earlier_run)
    workflow, run_dir = replay_cp0(tmp_path / "rerun", earlier_run)
    store, earlier_store = Execution(run_dir / "execution"), Execution(earlier_run / "execution")
    assert workflow.binding.module_id == "CP-1"  # CP-0 settled; the walk moved on
    assert {h.module_id: h.status for h in store.read().heads} == {"CP-0": "restricted"}
    earlier_pack, new_pack = earlier_store.read().pack_sha256, store.read().pack_sha256
    assert earlier_pack != new_pack  # the pack hash includes the run id
    (record,) = replay_records(run_dir)
    assert (record.earlier_run_id, record.module_id, record.step_id) == (
        EARLIER_ID,
        "CP-0",
        "source_readiness",
    )
    assert [(r.path, r.old, r.new) for r in record.rebound] == [
        ("pack_sha256", earlier_pack, new_pack)
    ]
    (earlier_sub,) = submissions(earlier_run)
    (sub,) = submissions(run_dir)
    assert record.earlier_payload_sha256 == earlier_sub.binding.payload_sha256
    assert record.payload_sha256 == sub.binding.payload_sha256 != record.earlier_payload_sha256
    # the snapshot the step returned: the journal's after the submit and the next module's begin
    assert record.snapshot_sha256 == store.read().content_hash()
    sent = (run_dir / "execution" / AUDIT / "payloads" / record.payload_sha256).read_text()
    assert json.loads(sent)["pack_sha256"] == new_pack
    assert tree_hash(earlier_run) == before  # the earlier run is read only


def test_the_retained_calls_are_issued_again_and_answer_alike(
    tmp_path: Path, earlier_run: Path
) -> None:
    _, run_dir = replay_cp0(tmp_path / "rerun", earlier_run)
    again = sorted(
        (OwnerCall.model_validate_json(p.read_bytes()) for p in audit(run_dir, "calls")),
        key=lambda c: c.sequence,
    )
    first = [OwnerCall.model_validate_json(p.read_bytes()) for p in audit(earlier_run, "calls")]
    key = lambda c: (c.sequence, c.tool, json.dumps(c.arguments), c.body, c.status)
    assert [c.tool for c in again] == ["read_pages", "search_pack"]
    assert sorted(map(key, again)) == sorted(map(key, first))
    assert {c.binding.run_id for c in again} == {RERUN_ID}  # the rerun's own evidence


def test_matching_is_by_module_and_step_never_by_invocation_digest(
    tmp_path: Path, earlier_run: Path
) -> None:
    """The earlier run's invocation preimages and reservation markers are deleted, and its digests
    (another run id, another prompt) match nothing in the rerun: replay never reads them."""
    copy = copy_of(earlier_run, tmp_path)
    for kind in ("invocations", "reservations"):
        shutil.rmtree(copy / "execution" / AUDIT / kind)
    _, run_dir = replay_cp0(tmp_path / "rerun", copy)
    assert [r.step_id for r in replay_records(run_dir)] == ["source_readiness"]
    text = Path(replay.__file__).read_text()
    assert "invocations" not in text and "reservations" not in text


def test_replay_works_from_execution_alone(tmp_path: Path, earlier_run: Path) -> None:
    alone = tmp_path / "alone"
    alone.mkdir()
    shutil.copytree(earlier_run / "execution", alone / "execution")
    assert {p.name for p in alone.iterdir()} == {"execution"}  # no run.json, pack or calls.jsonl
    _, run_dir = replay_cp0(tmp_path / "rerun", alone)
    assert len(replay_records(run_dir)) == 1


def test_a_step_submitted_twice_replays_only_the_valid_one(tmp_path: Path) -> None:
    earlier = author_earlier(tmp_path / "earlier", script=TwiceScript)
    assert sorted(s.disposition for s in submissions(earlier)) == ["invalid", "valid"]
    workflow, run_dir = replay_cp0(tmp_path / "rerun", earlier)
    attempts = [(a.module_id, a.number) for a in Execution(run_dir / "execution").read().attempts]
    assert attempts == [("CP-0", 0), ("CP-1", 0)]  # CP-0 settled on attempt 0
    assert [s.disposition for s in submissions(run_dir)] == ["valid"]
    assert len(replay_records(run_dir)) == 1 and workflow.binding.module_id == "CP-1"


def test_a_changed_call_body_diverges_and_is_journaled(tmp_path: Path, earlier_run: Path) -> None:
    copy = copy_of(earlier_run, tmp_path)
    edited = edit_call_body(copy)
    workflow, run_dir = new_workflow(tmp_path / "rerun")
    with pytest.raises(ReplayDiverged, match="CP-0 source_readiness: call"):
        replay.replay_module(workflow, copy, "CP-0", execution=run_dir / "execution")
    (fault,) = [OwnerFault.model_validate_json(p.read_bytes()) for p in audit(run_dir, "faults")]
    assert (fault.code, fault.kind, fault.digest) == (
        "replay_diverged",
        "calls",
        edited.content_hash(),
    )
    assert replay_records(run_dir) == [] and submissions(run_dir) == []


def reject(tmp_path: Path, copy: Path) -> tuple[ReplayRejected, Path]:
    workflow, run_dir = new_workflow(tmp_path / "rerun")
    with pytest.raises(ReplayRejected) as caught:
        replay.replay_module(workflow, copy, "CP-0", execution=run_dir / "execution")
    return caught.value, run_dir


def test_a_payload_the_rerun_validator_refuses_is_rejected_and_journaled(
    tmp_path: Path, earlier_run: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the allowlisted fields are rebound: with none, the earlier pack hash reaches the
    validator, which refuses it. (A journal-consistent earlier run, so nothing is forged.)"""
    monkeypatch.setattr(replay, "REBOUND_FIELDS", {})
    error, run_dir = reject(tmp_path, earlier_run)
    assert (error.module, error.step) == ("CP-0", "source_readiness")
    assert "does not bind the current prepared pack" in " ".join(error.issues)
    (fault,) = [OwnerFault.model_validate_json(p.read_bytes()) for p in audit(run_dir, "faults")]
    assert (fault.code, fault.kind) == ("replay_rejected", "submissions")
    assert replay_records(run_dir) == []


@pytest.mark.parametrize(
    "forge",
    [
        lambda p: p.update(pack_sha256="1" * 64),
        lambda p: p.update(objective="An objective the earlier run never settled"),
    ],
    ids=["pack-hash", "objective"],
)
def test_a_forged_valid_payload_is_refused_before_any_write(
    forge: Callable[[dict[str, Any]], None], tmp_path: Path, earlier_run: Path
) -> None:
    """F1-R1: the raw payload, filled as the journal did, must be the stored payload the earlier
    journal settled. A forged one makes the earlier run inconsistent: the rerun is refused."""
    copy = copy_of(earlier_run, tmp_path)
    edit_payload(copy, forge)
    workflow, run_dir = new_workflow(tmp_path / "rerun")
    with pytest.raises(ReplayRefused, match="CP-0 source_readiness: the retained payload"):
        replay.replay_module(workflow, copy, "CP-0", execution=run_dir / "execution")
    assert submissions(run_dir) == [] and audit(run_dir, "calls") == []
    checked, other = checked_run(tmp_path / "check", RERUN_ID)
    with pytest.raises(ReplayRefused, match="CP-0 source_readiness"):
        replay.check_replay(checked, other, copy, frozenset({"CP-1"}))


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda s: {"stored_payload_sha256": "3" * 64}, "stored payload differs"),
        (lambda s: {"step_output_sha256": "4" * 64}, "output differs"),
        (lambda s: {"binding": s.binding.model_copy(update={"call_ids": ()})}, "call ids differ"),
        (
            lambda s: {
                "binding": s.binding.model_copy(update={"call_ids": s.binding.call_ids[::-1]})
            },
            "call ids differ",
        ),
    ],
    ids=["stored", "output", "no-calls", "call-order"],
)
def test_a_submission_the_journal_does_not_bind_is_refused_naming_the_digest(
    change: Callable[[OwnerSubmission], dict[str, Any]],
    message: str,
    tmp_path: Path,
    earlier_run: Path,
) -> None:
    copy = copy_of(earlier_run, tmp_path)
    (sub,) = submissions(copy)
    swap_record(copy, "submissions", sub, sub.model_copy(update=change(sub)))
    checked, run_dir = checked_run(tmp_path / "rerun", RERUN_ID)
    with pytest.raises(ReplayRefused, match=f"CP-0 source_readiness: .*{message}"):
        replay.check_replay(checked, run_dir, copy, frozenset({"CP-1"}))
    assert not run_dir.exists()


def test_a_payload_edited_on_disk_is_rejected(tmp_path: Path, earlier_run: Path) -> None:
    copy = copy_of(earlier_run, tmp_path)
    (submission,) = submissions(copy)
    path = copy / "execution" / AUDIT / "payloads" / submission.binding.payload_sha256
    path.write_text(path.read_text() + " ")
    error, _ = reject(tmp_path, copy)
    assert error.issues == ("a retained payload does not match its digest",)


def test_replay_module_refuses_a_pack_that_is_not_the_earlier_one(
    tmp_path: Path, earlier_run: Path
) -> None:
    changed = tmp_path / "business-changed.txt"
    changed.write_text(o2_case.case_sources()[2].path.read_text() + "One more sentence.\n")
    sources = o2_case.case_sources()
    sources[2] = CaseSource("business", changed, "text/plain")
    checked, run_dir = checked_run(tmp_path / "rerun", RERUN_ID, sources)
    stage_sources(checked, run_dir)
    workflow = OwnerWorkflow.create(
        run_dir / "execution", load_pack(run_dir / "pack"), publication_directory=run_dir / "pub"
    )
    with pytest.raises(ReplayPackChanged):
        replay.replay_module(workflow, earlier_run, "CP-0", execution=run_dir / "execution")
    assert submissions(run_dir) == []  # nothing was rewritten or submitted


# Fields the probe `work/context-plan/probes/p5_replay_identity_fields.py` lists that no rewrite
# touches because their value does not depend on the run id: dates of evidence the model read, and
# the issuer and as-of date of the CP-1 review, which the equal-pack check holds equal.
RUN_INDEPENDENT: frozenset[tuple[str, str, str]] = frozenset(
    {
        ("CP-3", "relative_value", "market_evidence.as_of"),
        ("CP-3D", "market_implied", "observations.as_of_text"),
        ("CP-8", "decision_ledger", "observations.as_of_text"),
        ("CP-8", "decision_ledger", "default_restructuring.as_of_text"),
        ("CP-1", "financials", "financial.issuer_id"),
        ("CP-1", "financials", "financial.as_of"),
    }
)
IDENTITY_NAMES = ("run_id", "issuer_id", "as_of", "sha256")


def _models_in(annotation: Any) -> list[type[BaseModel]]:
    """The pydantic models an annotation names, through unions, tuples and optionals."""
    found: list[type[BaseModel]] = []
    stack = [annotation]
    while stack:
        kind = stack.pop()
        if isinstance(kind, type) and issubclass(kind, BaseModel):
            found.append(kind)
        stack.extend(getattr(kind, "__args__", ()))
    return found


def _unfilled(model: type[BaseModel], path: str, seen: frozenset[type]) -> list[str]:
    out: list[str] = []
    for name, field in model.model_fields.items():
        extra = field.json_schema_extra if isinstance(field.json_schema_extra, dict) else {}
        here = f"{path}.{name}" if path else name
        if any(n in name for n in IDENTITY_NAMES) and PREFILLED_MARKER not in extra:
            out.append(here)
        for inner in _models_in(field.annotation):
            if inner not in seen:
                out += _unfilled(inner, here, seen | {inner})
    return out


def identity_fields() -> set[tuple[str, str, str]]:
    """Every identity or hash field of a step schema that `prefill` does not set (the probe
    `work/context-plan/probes/p5_replay_identity_fields.py`, over the same schemas)."""
    return {
        (module_id, step.step_id, item)
        for module_id, spec in OWNER_SPECS.items()
        for step in spec.steps
        for item in _unfilled(step.schema, "", frozenset({step.schema}))
    }


def test_every_unfilled_identity_field_is_rebound_or_named_run_independent() -> None:
    found = identity_fields()
    rebound = {
        (module, step, ".".join((*REBOUND_HOLDER[(module, step)], name)))
        for (module, step), names in REBOUND_FIELDS.items()
        for name in names
    }
    assert rebound <= found  # an allowlisted path that no schema has any more is a stale entry
    assert found - rebound - RUN_INDEPENDENT == set()
    assert RUN_INDEPENDENT <= found  # nor is a stale name kept in the run-independent list
    assert REBOUND_FIELDS == {
        ("CP-0", "source_readiness"): ("pack_sha256",),
        ("CP-1", "financials"): ("run_id",),
    }


def test_the_cp1_financials_run_id_is_rebound_and_nothing_else() -> None:
    """The CP-1 payload names the earlier run in ``financial.run_id`` (checked against the pack's
    run). Whatever else the payload holds stays as the earlier run wrote it."""
    payload = o2_case.frozen_financials()["submission"]
    text = json.dumps(payload)
    earlier = replay._Identity("a" * 64, payload["financial"]["run_id"])
    rerun = replay._Identity("b" * 64, RERUN_ID)
    rewritten, rebound = replay._rebind("CP-1", "financials", text, earlier, rerun)
    assert [(r.path, r.old, r.new) for r in rebound] == [
        ("financial.run_id", earlier.run_id, RERUN_ID)
    ]
    expected = json.loads(text)
    expected["financial"]["run_id"] = RERUN_ID
    assert json.loads(rewritten) == expected
    other = json.dumps({**payload, "financial": {**payload["financial"], "run_id": "someone-else"}})
    assert replay._rebind("CP-1", "financials", other, earlier, rerun) == (other, ())
    assert replay._rebind("CP-2", "credit_synthesis", text, earlier, rerun) == (text, ())


# ================================================================================== part C
# the rerun through run_pathway


class CountingScript(CallingScript):
    """The script, counting the requests it was sent."""

    sent = 0

    def complete(self, request: Any, **kwargs: Any) -> Any:
        self.sent += 1
        return super().complete(request, **kwargs)


def rerun_private(
    root: Path,
    earlier: Path,
    repaired: frozenset[str] = frozenset({"CP-1"}),
    *,
    run_id: str = RERUN_ID,
    answers: tuple[str, ...] = (),
    cap: Decimal | None = None,
) -> tuple[Any, CountingScript]:
    """The rerun through the private seam, with the script as the live model."""
    checked, run_dir = checked_run(root, run_id)
    if cap is not None:
        checked = dataclasses.replace(checked, cap_usd=cap)
    plan = replay.check_replay(checked, run_dir, earlier, repaired)
    stage_sources(checked, run_dir)
    recordings = root / "recordings"
    recordings.mkdir()
    script = CountingScript(recordings, answers, run_dir / "execution", o2_case.MODEL)
    outcome = rp._run_pathway(checked, run_dir, script, o2_case.test_prompt_for, replay=plan)
    return outcome, script


def rerun_public(root: Path, earlier: Path | None, **extra: Any) -> Any:
    """The rerun through ``run_pathway`` with an empty recorded adapter (no recordings at all)."""
    checked, run_dir = checked_run(root, extra.pop("run_id", RERUN_ID))
    extra.setdefault("repaired", frozenset({"CP-1"}))
    return run_pathway(
        case_id=o2_case.CASE_ID,
        sources=extra.pop("sources", o2_case.case_sources()),
        context=o2_case.CASE / "context.json",
        pathway=o2_case.PATHWAY,
        model=o2_case.MODEL,
        adapter=checked.adapter,
        cap_usd=o2_case.CAP,
        run_dir=run_dir,
        run_id=checked.run_id,
        replay_from=earlier,
        **extra,
    )


def records_of(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / "calls.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def run_json(run_dir: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((run_dir / "run.json").read_text())
    return loaded


def spent_by_records(records: list[dict[str, Any]]) -> Decimal:
    """A settled call costs its settled charge, an unknown one its whole hold (O5)."""
    total = Decimal(0)
    for record in records:
        settled = record["settled_usd"]
        total += Decimal(record["reserved_usd"] if settled is None else settled)
    return total


def test_rerun_replays_cp0_and_runs_cp1_live(tmp_path: Path, earlier_run: Path) -> None:
    before = tree_hash(earlier_run)
    outcome, script = rerun_private(tmp_path / "rerun", earlier_run)
    run_dir = outcome.run_dir
    assert outcome.run_id == RERUN_ID and outcome.outcome == "stopped"
    assert outcome.stopped_reason is not None
    assert outcome.stopped_reason.startswith("RecordingMissing")  # CP-1 asked the model: live
    body = run_json(run_dir)
    assert body["replayed_from_run"] == EARLIER_ID and body["run_id"] == RERUN_ID
    assert run_json(earlier_run)["replayed_from_run"] is None
    heads = {h.module_id: h.status for h in Execution(run_dir / "execution").read().heads}
    assert heads == {"CP-0": "restricted"}  # CP-0 settled in the rerun's own journal
    records = records_of(run_dir)
    assert [(r["module_id"], r["step_id"]) for r in records] == [("CP-1", "source_context")]
    assert script.sent == 1  # the replayed CP-0 step sent no request
    assert len(replay_records(run_dir)) == 1
    assert tree_hash(earlier_run) == before  # the earlier run is read only


def test_rerun_calls_jsonl_holds_only_sent_calls(tmp_path: Path, earlier_run: Path) -> None:
    earlier_calls = (earlier_run / "calls.jsonl").read_bytes()
    outcome, script = rerun_private(tmp_path / "rerun", earlier_run)
    records = records_of(outcome.run_dir)
    assert len(records) == script.sent == 1
    assert all(r["module_id"] != "CP-0" for r in records)
    assert [r["call_index"] for r in records] == [0]
    assert (earlier_run / "calls.jsonl").read_bytes() == earlier_calls


def test_rerun_spend_excludes_replayed_calls(tmp_path: Path, earlier_run: Path) -> None:
    earlier_records = records_of(earlier_run)
    outcome, _ = rerun_private(tmp_path / "rerun", earlier_run)
    spent = spent_by_records(records_of(outcome.run_dir))
    assert outcome.spent_usd == spent > 0
    assert outcome.spent_usd < spent_by_records(earlier_records)  # the earlier run paid for CP-0
    cp0 = next(Decimal(r["settled_usd"]) for r in earlier_records if r["module_id"] == "CP-0")
    cp1 = next(Decimal(r["reserved_usd"]) for r in earlier_records if r["module_id"] == "CP-1")
    cap = cp1 + cp0 / 2  # admits the live request, not the replayed charge besides it
    again, _ = rerun_private(
        tmp_path / "capped", earlier_run, cap=cap, run_id="o2-synthetic-capped"
    )
    assert again.stopped_reason is not None and again.stopped_reason.startswith("RecordingMissing")
    fresh = author_earlier(
        tmp_path / "fresh", cap=cap
    )  # the same cap stops a run that pays for CP-0
    assert run_json(fresh)["stopped_reason"].startswith("BudgetExhausted")


def test_a_diverged_replay_stops_the_run_as_replay_diverged(
    tmp_path: Path, earlier_run: Path
) -> None:
    copy = copy_of(earlier_run, tmp_path)
    edit_call_body(copy)
    outcome = rerun_public(tmp_path / "rerun", copy)
    assert outcome.outcome == "stopped"
    assert (
        run_json(outcome.run_dir)["stopped_reason"] == "ReplayDiverged: CP-0 source_readiness: call"
    )
    assert [
        OwnerFault.model_validate_json(p.read_bytes()).code
        for p in audit(outcome.run_dir, "faults")
    ] == ["replay_diverged"]
    assert records_of(outcome.run_dir) == []  # no model request was sent for the module


def test_a_rejected_replay_stops_the_run_as_replay_rejected(
    tmp_path: Path, earlier_run: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(replay, "REBOUND_FIELDS", {})
    outcome = rerun_public(tmp_path / "rerun", earlier_run)
    reason = run_json(outcome.run_dir)["stopped_reason"]
    assert reason.startswith("ReplayRejected: CP-0 source_readiness: ")
    assert not reason.startswith("workflow:")
    assert records_of(outcome.run_dir) == []


@pytest.mark.parametrize(
    "case",
    [
        "no-repaired",
        "no-replay-from",
        "missing-replay-from",
        "replay-from-is-run-dir",
        "same-run-id",
        "changed-source",
    ],
)
def test_a_refused_rerun_writes_nothing(case: str, tmp_path: Path, earlier_run: Path) -> None:
    root = tmp_path / "rerun"
    extra: dict[str, Any] = {"repaired": frozenset({"CP-1"})}
    earlier: Path | None = earlier_run
    if case == "no-repaired":
        extra["repaired"] = frozenset()
    elif case == "no-replay-from":
        earlier = None
    elif case == "missing-replay-from":
        earlier = tmp_path / "no-such-run"
    elif case == "replay-from-is-run-dir":
        earlier = root / "run"
    elif case == "same-run-id":
        extra["run_id"] = EARLIER_ID
    else:
        changed = tmp_path / "business-changed.txt"
        changed.write_text(o2_case.case_sources()[2].path.read_text() + "One more sentence.\n")
        extra["sources"] = [
            *o2_case.case_sources()[:2],
            CaseSource("business", changed, "text/plain"),
            o2_case.case_sources()[3],
        ]
    with pytest.raises(RunInputError):
        rerun_public(root, earlier, **extra)
    assert not (root / "run").exists()


def test_a_rerun_asked_to_resume_is_refused_and_the_run_dir_is_untouched(
    tmp_path: Path, earlier_run: Path
) -> None:
    """A rerun is a fresh run: ``resume`` with ``replay_from`` is a ReplayRefused, on a run
    directory that exists (the refusal is not the missing directory's)."""
    first = rerun_public(tmp_path / "rerun", earlier_run)
    before = tree_hash(first.run_dir)
    with pytest.raises(ReplayRefused, match="not a resume"):
        run_pathway(
            case_id=o2_case.CASE_ID,
            sources=o2_case.case_sources(),
            context=o2_case.CASE / "context.json",
            pathway=o2_case.PATHWAY,
            model=o2_case.MODEL,
            adapter=recorded_adapter(o2_case.MODEL, tmp_path / "rerun" / "check-recordings"),
            cap_usd=o2_case.CAP,
            run_dir=first.run_dir,
            run_id=RERUN_ID,
            resume=True,
            replay_from=earlier_run,
            repaired=frozenset({"CP-1"}),
        )
    assert tree_hash(first.run_dir) == before


class Kill(BaseException):
    """The process is killed: nothing in the run catches it."""


def killed_rerun(
    tmp_path: Path, earlier: Path, monkeypatch: pytest.MonkeyPatch, where: str
) -> tuple[Path, Any]:
    root = tmp_path / "rerun"
    checked, run_dir = checked_run(root, RERUN_ID)
    if where == "invoke":

        def boom(self: Any, *args: Any, **kwargs: Any) -> Any:
            raise Kill()

        monkeypatch.setattr(OwnerWorkflow, "invoke", boom)
    else:  # after CP-0's replayed submission settled, at its replays record
        real = replay._write_record

        def after(execution: Path, kind: str, value: Any) -> None:
            if kind == replay.REPLAYS:
                raise Kill()
            real(execution, kind, value)

        monkeypatch.setattr(replay, "_write_record", after)
    with pytest.raises(Kill):
        rerun_public(root, earlier)
    monkeypatch.undo()
    return run_dir, checked


@pytest.mark.parametrize("where", ["invoke", "after-settle"])
def test_a_killed_rerun_is_not_resumed_as_an_ordinary_run(
    where: str, tmp_path: Path, earlier_run: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F1-R3: ``cap.json`` (create-once, the first record) names the earlier run; a plain resume
    is refused before any write or call, whatever the kill point."""
    run_dir, checked = killed_rerun(tmp_path, earlier_run, monkeypatch, where)
    assert json.loads((run_dir / "cap.json").read_text())["replayed_from_run"] == EARLIER_ID
    before = tree_hash(run_dir)
    with pytest.raises(rp.ResumeRefused, match="rerun after repair"):
        run_pathway(
            case_id=o2_case.CASE_ID,
            sources=o2_case.case_sources(),
            context=o2_case.CASE / "context.json",
            pathway=o2_case.PATHWAY,
            model=o2_case.MODEL,
            adapter=checked.adapter,
            cap_usd=o2_case.CAP,
            run_dir=run_dir,
            run_id=checked.run_id,
            resume=True,
        )
    assert tree_hash(run_dir) == before and not (run_dir / "run.json").exists()


@pytest.mark.parametrize("inside", ["run-dir-in-earlier", "earlier-in-run-dir"])
def test_nested_run_and_earlier_directories_are_refused(
    inside: str, tmp_path: Path, earlier_run: Path
) -> None:
    before = {str(p.relative_to(earlier_run)) for p in earlier_run.rglob("*")}
    checked, _ = checked_run(tmp_path / "chk", RERUN_ID)
    run_dir = earlier_run / "rerun" if inside == "run-dir-in-earlier" else earlier_run.parent
    with pytest.raises(ReplayRefused, match="contain one another"):
        replay.check_replay(checked, run_dir, earlier_run, frozenset({"CP-1"}))
    assert {str(p.relative_to(earlier_run)) for p in earlier_run.rglob("*")} == before


def test_a_refusal_after_the_first_write_stops_the_run_under_its_own_name(
    tmp_path: Path, earlier_run: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    copy = copy_of(earlier_run, tmp_path)
    real = replay.check_replay

    def check_then_tear(*args: Any) -> Any:
        found = real(*args)
        path = audit(copy, "calls")[0]  # torn after the check, before the replay reads it
        path.write_text(path.read_text() + " ")
        return found

    monkeypatch.setattr(rp, "check_replay", check_then_tear)
    outcome = rerun_public(tmp_path / "rerun", copy)
    assert outcome.outcome == "stopped"
    assert run_json(outcome.run_dir)["stopped_reason"].startswith("ReplayRefused: ")


def test_a_module_that_was_to_replay_but_runs_live_is_journaled_with_its_reason(
    tmp_path: Path, earlier_run: Path
) -> None:
    planned = replay.plan_replay(earlier_run, PLANNED, frozenset({"CP-3"}))
    outcome = rerun_public(tmp_path / "rerun", earlier_run, repaired=frozenset({"CP-3"}))
    live = [
        replay.ReplayLive.model_validate_json(p.read_bytes())
        for p in audit(outcome.run_dir, "replays")
        if json.loads(p.read_bytes())["schema_version"] == "replay-live/1"
    ]
    assert sorted((r.module_id, r.reason) for r in live) == sorted(planned.unreplayable)
    assert {r.earlier_run_id for r in live} == {EARLIER_ID} and live


# ---------------------------------------------------------------------------------- strength
# tests that pin the eligibility rules, the submission choice and the call comparison


def with_snapshot(monkeypatch: pytest.MonkeyPatch, change: Callable[[Any], Any]) -> None:
    """Every ``_Earlier`` reads a snapshot that ``change`` has edited (the files stay as they are)."""
    real = replay._Earlier.__init__

    def init(self: Any, path: Path) -> None:
        real(self, path)
        self.snapshot = change(self.snapshot)

    monkeypatch.setattr(replay._Earlier, "__init__", init)


def cp0_goes_live(earlier: Path) -> str:
    found = replay.plan_replay(earlier, PLANNED, frozenset({"CP-3"}))
    assert "CP-0" in found.live
    return dict(found.unreplayable)["CP-0"]


@pytest.mark.parametrize("status", ["stale", "blocked"])
def test_a_cp0_head_that_is_not_settled_goes_live(
    status: str, earlier_run: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def change(snapshot: Any) -> Any:
        heads = tuple(
            h.model_copy(update={"status": status}) if h.module_id == "CP-0" else h
            for h in snapshot.heads
        )
        return snapshot.model_copy(update={"heads": heads})

    with_snapshot(monkeypatch, change)
    assert "no settled, valid attempt" in cp0_goes_live(earlier_run)


@pytest.mark.parametrize(
    "update",
    [{"issues": ("an issue",)}, {"status": "pending"}],
    ids=["issues", "pending"],
)
def test_an_attempt_with_issues_or_still_pending_is_not_a_settled_attempt(
    update: dict[str, Any], earlier_run: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def change(snapshot: Any) -> Any:
        attempts = tuple(
            a.model_copy(update=update) if a.module_id == "CP-0" else a for a in snapshot.attempts
        )
        return snapshot.model_copy(update={"attempts": attempts})

    with_snapshot(monkeypatch, change)
    assert "no settled, valid attempt" in cp0_goes_live(earlier_run)


def test_a_module_with_a_step_the_earlier_run_never_submitted_goes_live(
    tmp_path: Path, earlier_run: Path
) -> None:
    copy = copy_of(earlier_run, tmp_path)
    (sub,) = submissions(copy)
    (copy / "execution" / AUDIT / "submissions" / sub.content_hash()).unlink()
    assert "no valid submission of step source_readiness" in cp0_goes_live(copy)


@pytest.mark.parametrize("field", ["as_of", "issuer_id", "requested_modules"])
def test_a_changed_run_field_is_refused(field: str, earlier_run: Path) -> None:
    pack = load_pack(earlier_run / "pack")
    value = {
        "as_of": pack.run.as_of - timedelta(days=1),
        "issuer_id": "another-issuer",
        "requested_modules": pack.run.requested_modules[:1],
    }[field]
    changed = pack.model_copy(update={"run": pack.run.model_copy(update={field: value})})
    with pytest.raises(ReplayPackChanged):
        replay.check_same_pack(pack, changed)


def test_a_record_filed_under_the_wrong_name_is_torn(tmp_path: Path, earlier_run: Path) -> None:
    copy = copy_of(earlier_run, tmp_path)
    path = audit(copy, "calls")[0]
    path.rename(path.with_name("f" * 64))  # its bytes are its own; its name is not its digest
    checked, run_dir = checked_run(tmp_path / "rerun", RERUN_ID)
    with pytest.raises(ReplayRefused, match="torn"):
        replay.check_replay(checked, run_dir, copy, frozenset({"CP-1"}))


def add_submission(copy: Path, **update: Any) -> None:
    """File one more submission beside the valid one, a copy changed by ``update``."""
    sub = next(s for s in submissions(copy) if s.disposition == "valid" and s.sequence == 1)
    extra = sub.model_copy(update=update)
    (copy / "execution" / AUDIT / "submissions" / extra.content_hash()).write_bytes(
        extra.model_dump_json().encode()
    )


def check(copy: Path, tmp_path: Path) -> replay.ReplayPlan:
    checked, run_dir = checked_run(tmp_path / "rerun", RERUN_ID)
    return replay.check_replay(checked, run_dir, copy, frozenset({"CP-1"}))


def test_an_invalid_or_other_ticket_submission_is_never_the_one_replayed(
    tmp_path: Path, earlier_run: Path
) -> None:
    copy = copy_of(earlier_run, tmp_path)
    (sub,) = submissions(copy)
    add_submission(
        copy, disposition="invalid", sequence=sub.sequence + 1, stored_payload_sha256="5" * 64
    )
    other = sub.binding.model_copy(
        update={"binding": sub.binding.binding.model_copy(update={"ticket_id": "another-ticket"})}
    )
    add_submission(copy, binding=other, sequence=sub.sequence + 2, stored_payload_sha256="6" * 64)
    assert check(copy, tmp_path).replayed == ("CP-0",)  # both are ignored; the real one binds


@pytest.mark.parametrize("offset", [1, -1], ids=["later", "earlier"])
def test_the_latest_valid_submission_is_the_one_replayed_and_it_must_bind(
    offset: int, tmp_path: Path, earlier_run: Path
) -> None:
    copy = copy_of(earlier_run, tmp_path)
    (sub,) = submissions(copy)
    add_submission(copy, sequence=sub.sequence + offset, stored_payload_sha256="7" * 64)
    if offset > 0:  # a later valid record that the journal does not bind is chosen, and refused
        with pytest.raises(ReplayRefused, match="stored payload differs"):
            check(copy, tmp_path)
    else:  # an earlier one is not the latest: ignored
        assert check(copy, tmp_path).replayed == ("CP-0",)


@pytest.mark.parametrize(
    "update",
    [{"status": "refused", "error_code": "not_permitted"}, {"error_code": "other_code"}],
    ids=["status", "error-code"],
)
def test_a_call_answered_with_another_status_or_code_diverges(
    update: dict[str, Any], tmp_path: Path, earlier_run: Path
) -> None:
    copy = copy_of(earlier_run, tmp_path)
    calls = [OwnerCall.model_validate_json(p.read_bytes()) for p in audit(copy, "calls")]
    target = next(c for c in calls if c.tool == "read_pages")
    swap_record(copy, "calls", target, target.model_copy(update=update))
    workflow, run_dir = new_workflow(tmp_path / "rerun")
    with pytest.raises(ReplayDiverged):
        replay.replay_module(workflow, copy, "CP-0", execution=run_dir / "execution")


def test_a_call_id_the_earlier_run_does_not_hold_is_rejected(
    tmp_path: Path, earlier_run: Path
) -> None:
    workflow, run_dir = new_workflow(tmp_path / "rerun")
    retained = replay._Earlier(earlier_run)
    (sub,) = submissions(earlier_run)
    lost = sub.model_copy(
        update={"binding": sub.binding.model_copy(update={"call_ids": ("no-such-call",)})}
    )
    with pytest.raises(ReplayRejected, match="a retained call is missing"):
        replay._replay_calls(workflow, retained, lost, run_dir / "execution")
    assert audit(run_dir, "calls") == []


def test_a_module_with_no_settled_attempt_cannot_be_replayed(
    tmp_path: Path, earlier_run: Path
) -> None:
    workflow, run_dir = new_workflow(tmp_path / "rerun")
    with pytest.raises(ReplayRejected, match="no settled valid attempt"):
        replay.replay_module(workflow, earlier_run, "CP-1", execution=run_dir / "execution")


def test_a_step_that_comes_back_after_a_valid_submission_is_rejected(
    tmp_path: Path, earlier_run: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow, run_dir = new_workflow(tmp_path / "rerun")
    steps: list[str] = []

    def stay(wf: Any, retained: Any, attempt: Any, execution: Path) -> None:
        steps.append(wf.binding.step_id)
        assert len(steps) < 4, "the replay loops on one step"

    monkeypatch.setattr(replay, "_replay_step", stay)
    with pytest.raises(ReplayRejected, match="came back"):
        replay.replay_module(workflow, earlier_run, "CP-0", execution=run_dir / "execution")
    assert steps == ["source_readiness"]


# ================================================================================== gated

promotion = pytest.mark.skipif(
    os.environ.get("RUN_PROMOTION") != "1",
    reason="the full o2 walk (CP-1 105 s, publish 72 s, receipt 107 s per run, B16); deferred to CI",
)


@promotion
def test_rerun_replays_upstream_and_runs_the_repaired_module_live(tmp_path: Path) -> None:
    """Gated, written and never run here. Earlier: the whole o2 walk. Repair CP-3 (relative value):
    CP-0, CP-1, CP-1A and CP-2 are replayed (CP-1 under the new run id), CP-MODEL is published again,
    CP-3 and its consumers CP-5 and CP-6 run live, and the receipt verifies."""
    authored = o2_case.author(tmp_path / "authoring", answers=o2_case.ALL_STEPS)
    earlier = authored.run_dir
    before = tree_hash(earlier)
    live_steps = ("relative_value", "integrity_review", "committee_challenge")
    outcome, _ = rerun_private(tmp_path / "rerun", earlier, frozenset({"CP-3"}), answers=live_steps)
    run_dir = outcome.run_dir
    assert run_json(run_dir)["replayed_from_run"] == o2_case.RUN_ID
    records = records_of(run_dir)
    assert {r["module_id"] for r in records}.isdisjoint({"CP-0", "CP-1", "CP-1A", "CP-2"})
    assert {r["module_id"] for r in records} >= {"CP-3", "CP-5", "CP-6"}
    assert {r.module_id for r in replay_records(run_dir)} == {"CP-0", "CP-1", "CP-1A", "CP-2"}
    cp1 = next(r for r in replay_records(run_dir) if r.module_id == "CP-1")
    assert [(b.path, b.old, b.new) for b in cp1.rebound] == [
        ("financial.run_id", o2_case.RUN_ID, RERUN_ID)
    ]
    receipt = OwnerRunReceipt.model_validate_json((run_dir / "owner-run.json").read_text())
    verify_owner_run_receipt(
        Execution(run_dir / "execution"), receipt, publication_directory=run_dir / "publication"
    )
    assert outcome.spent_usd == spent_by_records(records)
    assert outcome.spent_usd < authored.outcome.spent_usd
    assert tree_hash(earlier) == before


class OrderRecorder:
    """The rerun's real workflow, reporting that its step has inputs; only ``spec`` and
    ``read_inputs`` are replaced, ``invoke`` and ``submit_review`` are the real ones."""

    def __init__(self, real: OwnerWorkflow) -> None:
        self.real = real
        self.order: list[str] = []

    @property
    def binding(self) -> Any:
        return self.real.binding

    @property
    def phase(self) -> str:
        return self.real.phase

    @property
    def spec(self) -> Any:
        return dataclasses.replace(self.real.spec, inputs="projection")

    def read_inputs(self) -> dict[str, Any]:
        self.order.append("read")
        return {}

    def invoke(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.order.append("invoke")
        return self.real.invoke(tool, arguments)

    def submit_review(self, payload: str) -> dict[str, Any]:
        self.order.append("submit")
        return self.real.submit_review(payload)


def test_replay_reads_the_inputs_first_when_the_step_has_inputs(
    tmp_path: Path, earlier_run: Path
) -> None:
    real, run_dir = new_workflow(tmp_path / "rerun")
    wrapped = OrderRecorder(real)
    retained = replay._Earlier(earlier_run)
    attempt = replay._settled_attempt(retained.snapshot, "CP-0")
    assert attempt is not None
    replay._replay_step(cast(OwnerWorkflow, wrapped), retained, attempt, run_dir / "execution")
    assert wrapped.order == ["read", "invoke", "invoke", "submit"], wrapped.order
    assert {h.module_id for h in Execution(run_dir / "execution").read().heads} == {"CP-0"}


def test_the_raw_payload_check_fills_at_the_submissions_own_snapshot(
    tmp_path: Path, earlier_run: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The receipt verifier fills at the binding's historical snapshot; replay does the same, so
    a later journal state cannot change what the check accepts. The earlier store's current
    snapshot (CP-0 settled, CP-1 begun) is not the one CP-0's submission was bound at."""
    seen: list[str] = []
    real_filled = _filled

    def spy(store: Execution, binding: Any, payload: str) -> Any:
        seen.append(store.read().content_hash())
        return real_filled(store, binding, payload)

    monkeypatch.setattr("deploy_workflow.owner_workflow._filled", spy)
    retained = replay._Earlier(earlier_run)
    attempt = replay._settled_attempt(retained.snapshot, "CP-0")
    assert attempt is not None
    chosen = retained.bound_submission(attempt, "source_readiness")
    assert chosen is not None
    bound_at = chosen.binding.binding.snapshot_sha256
    assert bound_at != retained.snapshot.content_hash()  # the two states do differ
    seen.clear()
    retained._check_raw_payload(chosen, chosen.stored_payload_sha256, "CP-0")
    assert seen == [bound_at]
