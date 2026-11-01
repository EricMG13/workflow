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
from decimal import Decimal
from pathlib import Path
from typing import Any, NoReturn

import o2_case
import pytest
from pydantic import BaseModel

from deploy_vii.contracts import PREFILLED_MARKER
from deploy_vii.execution import Execution
from deploy_vii.preparation import load_pack
from deploy_workflow import replay
from deploy_workflow import run_pathway as rp
from deploy_workflow.model import transport as transport_module
from deploy_workflow.model.adapter import recorded_adapter
from deploy_workflow.owner_workflow import (
    AUDIT,
    OWNER_SPECS,
    OwnerCall,
    OwnerFault,
    OwnerSubmission,
    OwnerWorkflow,
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
    return [ReplayRecord.model_validate_json(p.read_bytes()) for p in audit(run_dir, "replays")]


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


def test_a_payload_the_validator_refuses_is_rejected_and_journaled(
    tmp_path: Path, earlier_run: Path
) -> None:
    copy = copy_of(earlier_run, tmp_path)
    edit_payload(copy, lambda p: p.update(consumers=[{"consumer_id": "no-such-module"}]))
    error, run_dir = reject(tmp_path, copy)
    assert (error.module, error.step) == ("CP-0", "source_readiness") and error.issues
    (fault,) = [OwnerFault.model_validate_json(p.read_bytes()) for p in audit(run_dir, "faults")]
    assert (fault.code, fault.kind) == ("replay_rejected", "submissions")
    assert replay_records(run_dir) == []


def test_a_cp0_payload_naming_another_pack_is_rejected_not_rewritten(
    tmp_path: Path, earlier_run: Path
) -> None:
    """Only the earlier run's own pack hash is rebound: any other value reaches the validator."""
    copy = copy_of(earlier_run, tmp_path)
    edit_payload(copy, lambda p: p.update(pack_sha256="1" * 64))
    error, _ = reject(tmp_path, copy)
    assert "does not bind the current prepared pack" in " ".join(error.issues)


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
