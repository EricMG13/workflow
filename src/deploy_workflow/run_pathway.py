"""``run_pathway``: the entry point that joins O2's input checks to O5's model tool loop (O2 Task 3).

The order is fixed: ``check_arguments`` (writes nothing), ``stage_sources``, then ``_run_pathway``,
which creates the ``OwnerWorkflow``, drives it step by step through ``ToolLoop``, calls
``workflow.publish()`` at the publisher's stop, and hands the finished walk to ``_finish_run``
(receipt, verify, render, verify the render, ``run.json`` last).

A named fault ends the run as ``stopped``: ``StepStopped``, any ``BudgetError``, ``RecordingMissing``,
``WorkflowError``, ``NoPrompt``, ``PromptError``, ``CpDrNotAnchored``, ``BriefInvalid``, and a
``ValueError`` from prepare or from the render and its verify. ``run.json`` records the outcome and a redacted reason. Any other exception
propagates and leaves the run directory WITHOUT ``run.json``: a crashed run is detectable by that
absence. Nothing here reads the environment or the network; the live adapter reads keys only inside
its own ``complete``, and this module's text is redacted by the key pattern alone.
"""

import contextlib
import fcntl
import json
import os
import sys
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from decimal import Context, Decimal, Inexact, InvalidOperation
from pathlib import Path
from typing import Any, Protocol

from deploy_vii.contracts import PathwayId
from deploy_vii.execution import Execution
from deploy_vii.live.prompts import PromptError
from deploy_vii.preparation import PreparedPack, load_pack
from deploy_vii.registry import plan
from deploy_workflow.model.adapter import LiveAdapter, ModelAdapter, RecordingMissing
from deploy_workflow.model.budget import Budget, BudgetError
from deploy_workflow.model.loop import (
    PromptFor,
    StepStopped,
    ToolLoop,
    recorded_stop,
)
from deploy_workflow.model.pricing import money_text
from deploy_workflow.model.record import CallLog
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.turn import ModelSpec
from deploy_workflow.owner_rendering import render_owner_slice, verify_owner_rendered_slice
from deploy_workflow.owner_workflow import (
    AUDIT,
    OWNER_SPECS,
    OwnerWorkflow,
    TornAudit,
    verify_owner_run_receipt,
)
from deploy_workflow.prompts.compose import NoPrompt
from deploy_workflow.prompts.factory import UntrustedFor, prompt_factory
from deploy_workflow.prompts.tools import tools_for
from deploy_workflow.replay import (
    ReplayDiverged,
    ReplayError,
    ReplayPackChanged,
    ReplayPlan,
    ReplayRefused,
    ReplayRejected,
    check_replay,
    journal_unreplayable,
    replay_module,
)
from deploy_workflow.research import evidence
from deploy_workflow.research.contracts import BriefInvalid, CpDrNotAnchored
from deploy_workflow.research.intake import rejected_bytes
from deploy_workflow.run_inputs import (
    HTML_MEDIA,
    CaseSource,
    CheckedRun,
    RunDirInvalid,
    RunInputError,
    RunOutcome,
    StagedSourceChanged,
    check_arguments,
    stage_sources,
)
from deploy_workflow.workflow import WorkflowError

# The longest reply the loop will reserve for. The reservation is sized from this, so a larger
# value needs a larger cap; 128k is the most O5 accepts (spec section 8).
MAX_OUTPUT_TOKENS = 32_768

PromptFactory = Callable[[PreparedPack], PromptFor]


class RunDirBusy(RunInputError):
    """Another ``run_pathway`` holds this run directory's lock (single writer, R9a)."""

    code = "run_dir_busy"


class ResumeRefused(RunInputError):
    """A resume is refused before it writes: the directory is not a resumable run (N1, P3)."""

    code = "resume_refused"


class ResumeMismatch(ResumeRefused):
    """The arguments of a resume are not those the run began with (N1)."""

    code = "resume_mismatch"


class CapExists(RunInputError):
    """``cap.json`` is create-once (P2): a second create is refused."""

    code = "cap_exists"


CAP_FILE = "cap.json"
_CP_DR_LINEAGE = "LOCAL"
_EXACT_ADD = Context(prec=120, traps=[Inexact, InvalidOperation]).add


@contextlib.contextmanager
def _single_writer(run_dir: Path) -> Iterator[None]:
    """Hold an exclusive, non-blocking ``flock`` on ``run_dir`` itself for the whole run, fresh or
    resumed (R9a): no lock file is written, and the kernel drops the lock if the process dies.
    A second ``run_pathway`` on the directory is refused (``RunDirBusy``) before it writes."""
    # ponytail: ``flock`` is advisory; a network filesystem, or a process that never calls
    # ``run_pathway``, is not excluded (the ceiling of ``CallLog``'s lock too). Upgrade path:
    # ``OwnerWorkflow`` holds the lock for its own store, so every writer is excluded.
    fd = os.open(run_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RunDirBusy(f"{run_dir} is held by another run_pathway") from None
        yield
    finally:
        os.close(fd)  # closing releases the lock


def _create_cap(
    run_dir: Path, cap_usd: Decimal, mode: str, replayed_from_run: str | None = None
) -> None:
    """Record the run's cap and mode, create-once (P2, R18): a resume can neither raise nor lower
    the cap, nor change from offline to live or back. A rerun after repair also records the earlier
    run's id here, so a plain resume of it is refused (F1-R3); an ordinary run's file is unchanged."""
    record: dict[str, str] = {"cap_usd": money_text(cap_usd), "mode": mode}
    if replayed_from_run is not None:
        record["replayed_from_run"] = replayed_from_run
    data = (json.dumps(record) + "\n").encode()
    try:
        fd = os.open(
            run_dir / CAP_FILE,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
        )
    except FileExistsError:
        raise CapExists(f"{run_dir / CAP_FILE} already exists") from None
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    _fsync_directory(run_dir)


def _retained_identity(run_dir: Path) -> tuple[Decimal, str]:
    """The cap and mode the run began with; a missing, malformed or non-finite file is refused."""
    try:
        loaded = json.loads((run_dir / CAP_FILE).read_text())
        cap, mode = Decimal(loaded["cap_usd"]), loaded["mode"]
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError):
        raise ResumeRefused(f"{run_dir / CAP_FILE} is missing or unreadable") from None
    if not cap.is_finite() or mode not in ("live", "offline"):  # sNaN would raise on comparison
        raise ResumeRefused(f"{run_dir / CAP_FILE} is missing or unreadable")
    return cap, str(mode)


def _refuse_rerun(run_dir: Path) -> None:
    """A rerun after repair is not resumed as an ordinary run (it would drive the module it was to
    replay live): ``cap.json`` names the earlier run it replays (F1-R3). Reads only."""
    try:
        recorded = json.loads((run_dir / CAP_FILE).read_text()).get("replayed_from_run")
    except (OSError, ValueError, AttributeError):
        return  # unreadable or absent: `_check_identity` refuses it with its own reason
    if recorded is not None:
        raise ResumeRefused(f"{run_dir} is a rerun after repair of {recorded}: it is not resumed")


def _check_cap_and_mode(checked: CheckedRun, run_dir: Path) -> None:
    cap, mode = _retained_identity(run_dir)
    if cap != checked.cap_usd:
        raise ResumeMismatch("cap_usd is not the cap the run began with")
    if mode != _mode_of(checked.adapter):
        raise ResumeMismatch("the mode (live or offline) is not the one the run began with")


def _mode_of(adapter: ModelAdapter) -> str:
    return "live" if type(adapter) is LiveAdapter else "offline"


def _retained_configs(run_dir: Path, redactor: Redactor) -> tuple[set[tuple[str, ...]], set[str]]:
    """What the run recorded of itself: the (run_id, case_id, pathway) of every ``calls.jsonl``
    line and every ``config_id`` it and the reservation markers name."""
    markers = run_dir / "execution" / AUDIT / "reservations"
    identities: set[tuple[str, ...]] = set()
    configs: set[str] = set()
    for record in CallLog(run_dir, redactor).records():
        identities.add((record["run_id"], record["case_id"], record["pathway"]))
        configs.add(record["config_id"])
    if markers.is_dir():
        for path in sorted(markers.iterdir()):
            if not path.name.endswith(".settled"):
                configs.add(json.loads(path.read_text())["config_id"])
    return identities, configs


def _check_research(checked: CheckedRun, run_dir: Path) -> None:
    """N1 for the research arguments (reads only): the manifest, the accepted items and the refused
    items must be those staged under ``research/``; a run staged without research has none."""
    staged = run_dir / evidence.RESEARCH_DIR
    research = checked.research
    if research is None:
        if staged.exists():
            raise ResumeMismatch("the run was staged with a research manifest; none was given")
        return
    try:
        recorded = evidence.read_evidence(staged / evidence.EVIDENCE_FILE)
        manifest_sha = evidence.read_manifest_sha(staged / evidence.MANIFEST_SHA_FILE)
        rejected = (staged / evidence.REJECTED_FILE).read_bytes()
    except (OSError, ValueError):  # EvidenceRecordInvalid is a ValueError
        raise ResumeRefused(f"{staged} is missing or unreadable") from None
    wanted = [
        {k: v for k, v in row.items() if k != "retrieved"}
        for row in evidence.evidence_rows(research.accepted, "")
    ]
    if [{k: v for k, v in row.items() if k != "retrieved"} for row in recorded] != wanted:
        raise ResumeMismatch("the research items are not the staged run's")
    if rejected != rejected_bytes(research.refused):
        raise ResumeMismatch("the refused research items are not the staged run's")
    if manifest_sha != research.manifest_sha256:
        raise ResumeMismatch("the research manifest is not the staged run's")


def _check_identity(checked: CheckedRun, run_dir: Path, redactor: Redactor) -> None:
    """N1: a resume is the run it continues. Reads only: refused here, nothing has been written.
    ``run_id``, ``pathway`` and the staged sources against the retained pack, ``config_id`` against
    the retained calls and reservation markers, ``cap_usd`` against the create-once ``cap.json``."""
    if (run_dir / "run.json").exists():
        raise ResumeRefused(f"{run_dir} already holds run.json: the run is finished")
    try:
        pack = load_pack(run_dir / "pack")
    except (OSError, ValueError) as error:
        raise ResumeRefused(f"prepare: {error}") from None
    if (pack.run.run_id, pack.run.pathway) != (checked.run_id, checked.pathway):
        raise ResumeMismatch("run_id or pathway is not the staged run's")
    if {s.source_id: s.sha256 for s in pack.sources} != {
        item.source_id: item.sha256 for item in checked.files
    }:  # the same ids and the same files, no subset (R17)
        raise ResumeMismatch("the sources are not the staged run's")
    if pack.run.requested_modules != checked.request.run.requested_modules:
        raise ResumeMismatch("the requested modules (cp_dr) are not the staged run's")
    _check_research(checked, run_dir)
    _check_cap_and_mode(checked, run_dir)
    try:
        identities, configs = _retained_configs(run_dir, redactor)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ResumeRefused(f"the retained calls are unreadable: {type(error).__name__}") from None
    if identities - {(checked.run_id, checked.case_id, checked.pathway)}:
        raise ResumeMismatch("case_id is not the run's")
    if configs - {checked.model.config_id}:
        raise ResumeMismatch("config_id is not the run's")


_FAULTS = (
    StepStopped,
    BudgetError,
    RecordingMissing,
    WorkflowError,
    NoPrompt,
    PromptError,
    ReplayRefused,
    ReplayError,
    ReplayPackChanged,
    CpDrNotAnchored,  # O7-R20: a CP-DR run that is not anchored on CP-0 and CP-1 stops
    BriefInvalid,  # a locked brief that was changed is not repairable by the model
)


@dataclass(frozen=True)
class _Meta:
    """What ``run.json`` records besides the outcome."""

    checked: CheckedRun
    entries: tuple[dict[str, Any], ...]
    live: bool
    redactor: Redactor
    replayed_from: str | None = None  # the earlier run's run_id, for a rerun after repair
    untrusted_for: UntrustedFor | None = None  # CP-DR's evidence hook; used only when cp_dr


def _source_entries(
    checked: CheckedRun, sources: Sequence[CaseSource], context: Path
) -> tuple[dict[str, Any], ...]:
    """``run.json`` ``sources``: the caller's path and media type, the hash of the original bytes,
    and, for a converted HTML source, the hash of the staged (converted) bytes."""
    staged = {item.source_id: item for item in checked.files}
    entries: list[dict[str, Any]] = [
        {
            "source_id": item.source_id,
            "path": str(item.path),
            "sha256": staged[item.source_id].original_sha256,
            "media_type": item.media_type,
            "converted_sha256": staged[item.source_id].sha256
            if item.media_type == HTML_MEDIA
            else None,
        }
        for item in sources
    ]
    entries.extend(_research_entries(checked))
    entries.append(
        {
            "source_id": staged["context"].source_id,
            "path": str(context),
            "sha256": staged["context"].sha256,  # the context is staged unconverted
            "media_type": "text/plain",
            "converted_sha256": None,
        }
    )
    return tuple(entries)


def _research_entries(checked: CheckedRun) -> list[dict[str, Any]]:
    """One entry per accepted ``ev-<n>`` item: its manifest-relative path, always ``text/plain``."""
    if checked.research is None:
        return []
    return [
        {
            "source_id": item.item_id,
            "path": item.path,
            "sha256": item.sha256,
            "media_type": "text/plain",
            "converted_sha256": None,
        }
        for item in checked.research.accepted
    ]


def _cp_dr_keys(checked: CheckedRun) -> dict[str, Any]:
    """The ``run.json`` keys that exist only for a CP-DR run (a ``cp_dr=False`` file is unchanged).
    The brief, dossier and head hashes are null until the core that writes them records them."""
    if not checked.cp_dr or checked.research is None:
        return {}
    return {
        "cp_dr_lineage": _CP_DR_LINEAGE,
        "research_manifest_sha256": checked.research.manifest_sha256,
        "cp_dr_brief_sha256": None,
        "cp_dr_dossier_sha256": None,
        "cp_dr_head_sha256": None,
    }


def _staged_entries(checked: CheckedRun, run_dir: Path) -> tuple[dict[str, Any], ...]:
    """The entries when the caller's paths are not known (the authoring harness): the staged
    files, labelled by the media type the caller gave each (``text/html`` means converted)."""
    return tuple(
        {
            "source_id": item.source_id,
            "path": str(run_dir / "sources" / item.filename),
            "sha256": item.original_sha256,
            "media_type": item.media_type,
            "converted_sha256": item.sha256 if item.media_type == HTML_MEDIA else None,
        }
        for item in checked.files
    )


def _fsync_directory(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_run_json(run_dir: Path, meta: _Meta, outcome: str, stopped_reason: str | None) -> None:
    """Write ``run.json`` last: a temp file in ``run_dir``, fsync, ``os.replace``."""
    checked = meta.checked
    body: dict[str, Any] = {
        "case_id": checked.case_id,
        "pathway": checked.pathway,
        "config_id": checked.model.config_id,
        "run_id": checked.run_id,
        "mode": "live" if meta.live else "offline",
        "cap_usd": money_text(checked.cap_usd),
        "sources": list(meta.entries),
        "cp_dr_invoked": checked.cp_dr,
        **_cp_dr_keys(checked),
        "replayed_from_run": meta.replayed_from,
        "outcome": outcome,
        "stopped_reason": stopped_reason,
    }
    if meta.live and checked.gate is not None:
        body["ruling_path"] = str(checked.gate.path)
        body["ruling_sha256"] = checked.gate.sha256
        body["ruling_date"] = checked.gate.date.isoformat()
    data = (json.dumps(meta.redactor.json_value(body), indent=2) + "\n").encode()
    temp = run_dir / "run.json.tmp"
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, run_dir / "run.json")
    _fsync_directory(run_dir)


def _stop(run_dir: Path, meta: _Meta, reason: str, spent: Decimal) -> RunOutcome:
    """End the run as ``stopped``: the redacted reason goes to ``run.json``. Callers build
    ``reason`` inside their ``except`` and call this after leaving it, so a failure to write
    ``run.json`` is not chained to the raw fault."""
    clean = meta.redactor.text(reason)
    _write_run_json(run_dir, meta, "stopped", clean)
    return RunOutcome(meta.checked.run_id, run_dir, "stopped", clean, spent)


@dataclass(frozen=True)
class _Fault:
    """A named fault, as redacted-on-write text and the spend so far; the run then stops."""

    reason: str
    spent: Decimal


def _fault_reason(fault: Exception, redactor: Redactor) -> str:
    if isinstance(fault, StepStopped):
        return redactor.text(str(fault))
    return f"{type(fault).__name__}: {redactor.text(str(fault))}"


def _render(workflow: OwnerWorkflow, run_dir: Path, shown: Path | None) -> str | None:
    """Render and verify the delivery; the fault text of a ``ValueError``, else ``None``."""
    execution, receipt_path, delivery = (
        run_dir / "execution",
        run_dir / "owner-run.json",
        run_dir / "delivery",
    )
    try:
        render_owner_slice(execution, receipt_path, shown, delivery)
        verify_owner_rendered_slice(execution, receipt_path, shown, delivery)
    except ValueError as error:
        return f"render: {error}"
    return None


def _finish_run(workflow: OwnerWorkflow, run_dir: Path, meta: _Meta, budget: Budget) -> RunOutcome:
    """After the walk: receipt, verify it, render, verify the render, then ``run.json`` last.
    A ``ValueError`` from the render or its verify is the fault ``render: <code>``; the receipt
    and any delivery already written are kept as evidence."""
    receipt_path = run_dir / "owner-run.json"
    publication = run_dir / "publication"
    shown = publication if publication.exists() else None
    receipt = workflow.write_receipt(receipt_path)
    verify_owner_run_receipt(Execution(run_dir / "execution"), receipt, publication_directory=shown)
    failure = _render(workflow, run_dir, shown)
    if failure is not None:
        return _stop(run_dir, meta, failure, budget.spent)
    _write_run_json(run_dir, meta, "settled", None)
    return RunOutcome(meta.checked.run_id, run_dir, "settled", None, budget.spent)


class _Walk(Protocol):
    """What the driver needs of the loop: drive the analytical walk to where it stops."""

    def run(self) -> object: ...


class _ReplayingLoop:
    """``run`` for a rerun after repair (G4): a replayed module is resubmitted from the earlier
    run's retained submissions, any other module is driven live one step at a time by the tool
    loop. The walk is plan-ordered, so a live module that precedes a replayed one is begun first.
    A replayed step sends no model request; divergence raises and never falls back to the loop."""

    def __init__(
        self, workflow: OwnerWorkflow, loop: ToolLoop, replay: ReplayPlan, execution: Path
    ) -> None:
        self._workflow, self._loop, self._replay, self._execution = (
            workflow,
            loop,
            replay,
            execution,
        )

    def run(self) -> None:
        while self._workflow.phase == "analytical":
            module = self._workflow.binding.module_id
            if module in self._replay.replayed:
                replay_module(
                    self._workflow, self._replay.earlier, module, execution=self._execution
                )
            else:
                self._loop.run_step()


def _drive(workflow: OwnerWorkflow, loop: _Walk, pack: PreparedPack) -> str | None:
    """Run every step. The loop returns at the publisher's stop (or when the walk ends refused);
    ``publish`` runs there once and the walk resumes after it. A refused publication that ends the
    walk is not a fault (O1 Q1); one that leaves the walk open is, and its code is returned as the
    stop reason (``publish: <code>``) so that no receipt is attempted."""
    loop.run()
    has_publisher = any(
        OWNER_SPECS[m].kind == "deterministic" for m in plan(pack.run.requested_modules)
    )
    if not has_publisher:
        return None
    return _publish_and_go_on(workflow, loop)


def _publish_and_go_on(workflow: OwnerWorkflow, loop: _Walk) -> str | None:
    """``publish`` at the publisher's stop, then the rest of the walk; the stop reason of a
    refusal that leaves the walk open, else ``None``."""
    published = workflow.publish()
    if published["next_step"] is not None:
        loop.run()
    # "complete" means the walk ended.
    elif published["status"] != "ok" and workflow.phase != "complete":
        return f"publish: {published['error_code']}"
    return None


def _drive_resumed(workflow: OwnerWorkflow, loop: _Walk) -> str | None:
    """Continue a resumed walk from where ``open()`` left it, by the phase it reports (never by
    polling ``state()``): steps while a module is active, ``publish`` once at the publisher's stop,
    nothing when the walk already ended. A publication that failed mid-cleanup is not retried."""
    if workflow.phase == "analytical":
        loop.run()
    if workflow.phase == "walked":
        if workflow._publications:  # a fresh run stopped on a refused publication: not again
            return "publish: refused by an earlier call; not published again"
        return _publish_and_go_on(workflow, loop)
    if workflow.phase == "failed":
        return "resume: the publication left the walk failed"
    return None


def _enter(run_dir: Path, pack: PreparedPack, resume: bool) -> OwnerWorkflow:
    """Create the workflow over a fresh run directory, or reopen the killed run's."""
    execution, publication = run_dir / "execution", run_dir / "publication"
    if resume:
        return OwnerWorkflow.open(execution, publication_directory=publication)
    return OwnerWorkflow.create(execution, pack, publication_directory=publication)


def _prior_spend(checked: CheckedRun, execution: Path) -> Decimal:
    """What the run's reservations already cost, for a stop before the loop's budget exists:
    zero for a run that has none."""
    if not (execution / AUDIT / "reservations").is_dir():
        return Decimal(0)
    return _spend(Budget(checked.cap_usd, execution))


def _spend(budget: Budget) -> Decimal:
    """Every charge once: the settled ones, the unknown ones and the crash-left holds."""
    return _EXACT_ADD(budget.spent, budget.reserved)


def _stopped_before_loop(
    checked: CheckedRun, execution: Path, reason: str, redactor: Redactor
) -> _Fault:
    """A stop before the loop's budget exists; the spend so far, or, if the budget itself cannot
    be read, the reason with the budget's failure appended (never a silent zero)."""
    try:
        return _Fault(reason, _prior_spend(checked, execution))
    except BudgetError as error:
        return _Fault(f"{reason}; {_fault_reason(error, redactor)}", Decimal(0))


def _opened(
    checked: CheckedRun, run_dir: Path, pack: PreparedPack, resume: bool, redactor: Redactor
) -> OwnerWorkflow | _Fault:
    """The workflow, or the fault that stops the run. A ``TornAudit`` is mapped before the generic
    ``workflow: <code>`` (P6, F6), so it never surfaces as ``workflow: identity_mismatch``."""
    execution = run_dir / "execution"
    try:
        return _enter(run_dir, pack, resume)
    except TornAudit:
        return _stopped_before_loop(checked, execution, "TornAudit", redactor)
    except WorkflowError as error:
        return _stopped_before_loop(checked, execution, f"workflow: {error.code}", redactor)


def _held(budget: Budget, resume: bool) -> _Fault | None:
    """B10: on a resume, a money stop the budget holds (R15): a reservation with no settlement
    (it may have been sent, its charge unknown), an unknown charge, an overrun. The fresh run
    would have stopped with the loop's name for it; the resumed run stops before any step (the
    model is not called, nothing is published) and every charge is counted once in the spend."""
    kind = budget.stop_kind if resume else None
    if kind is None:
        return None
    if kind == "crash_left":
        text = "RunStopped: a reservation left unsettled by a crash: " + ", ".join(budget.unsettled)
    elif kind == "overrun":
        text = "OverrunStop: the actual charge was above the reservation"
    else:
        text = "UnknownCharge: the charge of a sent call is unknown"
    return _Fault(text, _spend(budget))


def _resume_stop(budget: Budget, run_dir: Path, redactor: Redactor) -> _Fault | None:
    """Why a resumed run must not go on, from the durable state alone: a money stop (R15); a
    settled call with no record in ``calls.jsonl`` (R13), whose ``call_index`` the next call would
    reuse; the stop the last record shows (R16); a sealed receipt with no ``run.json`` (R19)."""
    held = _held(budget, True)
    if held is not None:
        return held
    records = CallLog(run_dir, redactor).records()
    sent = sum(1 for record in records if Decimal(record["reserved_usd"]) > 0)
    if len(budget.settled_calls) > sent:
        text = "UnrecordedCall: a settled call has no record in calls.jsonl"
    elif (stop := recorded_stop(records)) is not None:
        text = stop
    elif (run_dir / "execution" / AUDIT / "receipt.sha256").exists():
        text = "SealedWithoutRunRecord: the receipt is sealed and run.json was never written"
    else:
        return None
    return _Fault(text, _spend(budget))


def _drive_and_finish(
    checked: CheckedRun,
    run_dir: Path,
    adapter: ModelAdapter,
    prompt_for: PromptFactory | None,
    meta: _Meta,
    pack: PreparedPack,
    workflow: OwnerWorkflow,
    budget: Budget,
    resume: bool,
    replay: ReplayPlan | None = None,
) -> RunOutcome | _Fault:
    """The loop over the workflow, ``publish`` at the stop, then the receipt and ``run.json``.
    A rerun after repair (``replay``) replays the modules the plan names and drives the rest."""
    redactor, execution = meta.redactor, run_dir / "execution"
    try:
        if replay is not None:
            journal_unreplayable(replay, execution)
        store = Execution(execution)
        composer = (
            prompt_factory(pack, store, untrusted_for=meta.untrusted_for if checked.cp_dr else None)
            if prompt_for is None
            else prompt_for(pack)
        )
        loop = ToolLoop(
            workflow,
            adapter,
            budget,
            CallLog(run_dir, redactor),
            composer,
            tools_for,
            redactor,
            time.time,
            time.sleep,
            execution=store,
            spec=checked.model,
            case_id=checked.case_id,
            pathway=checked.pathway,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            resumed=resume,
        )
        walk: _Walk = loop if replay is None else _ReplayingLoop(workflow, loop, replay, execution)
        refused = _drive_resumed(workflow, walk) if resume else _drive(workflow, walk, pack)
        if refused is not None:
            return _Fault(refused, budget.spent)
        return _finish_run(workflow, run_dir, meta, budget)
    except _FAULTS as fault:
        return _Fault(_fault_reason(fault, redactor), budget.spent)


def _stages(
    checked: CheckedRun,
    run_dir: Path,
    adapter: ModelAdapter,
    prompt_for: PromptFactory | None,
    meta: _Meta,
    resume: bool = False,
    replay: ReplayPlan | None = None,
) -> RunOutcome | _Fault:
    try:
        pack = load_pack(run_dir / "pack")
    except ValueError as error:
        return _Fault(f"prepare: {error}", Decimal(0))
    workflow = _opened(checked, run_dir, pack, resume, meta.redactor)
    if isinstance(workflow, _Fault):
        return workflow
    try:
        budget = Budget(checked.cap_usd, run_dir / "execution")
        stop = _resume_stop(budget, run_dir, meta.redactor) if resume else None
    except BudgetError as error:  # a marker the budget cannot load: a named stop, not a crash
        return _Fault(_fault_reason(error, meta.redactor), Decimal(0))
    if stop is not None:
        return stop
    return _drive_and_finish(
        checked, run_dir, adapter, prompt_for, meta, pack, workflow, budget, resume, replay
    )


def _walk(
    checked: CheckedRun,
    run_dir: Path,
    adapter: ModelAdapter,
    prompt_for: PromptFactory | None,
    meta: _Meta,
    resume: bool = False,
    replay: ReplayPlan | None = None,
) -> RunOutcome:
    result = _stages(checked, run_dir, adapter, prompt_for, meta, resume, replay)
    if isinstance(result, _Fault):
        return _stop(run_dir, meta, result.reason, result.spent)
    return result


@contextlib.contextmanager
def _redacted_stderr(redactor: Redactor) -> Iterator[None]:
    """Route stderr through the redactor; closing the stream writes (redacted) any partial line."""
    stream = redactor.redact_stream(sys.stderr)
    try:
        with contextlib.redirect_stderr(stream):
            yield
    finally:
        stream.close()


def _run_pathway(
    checked: CheckedRun,
    run_dir: Path,
    adapter: ModelAdapter,
    prompt_for: PromptFactory | None = None,
    *,
    entries: tuple[dict[str, Any], ...] | None = None,
    resume: bool = False,
    replay: ReplayPlan | None = None,
    untrusted_for: UntrustedFor | None = None,
) -> RunOutcome:
    """Run the walk over a staged ``run_dir``; ``resume`` reopens the killed run's workflow
    instead of creating one; ``replay`` (from ``check_replay``) makes it a rerun after repair. No adapter-type check here (``check_arguments``
    owns it), so the authoring harness can drive it with a test adapter. While it runs, stderr
    passes through the redactor."""
    redactor = Redactor()
    meta = _Meta(
        checked,
        _staged_entries(checked, run_dir) if entries is None else entries,
        type(adapter) is LiveAdapter,
        redactor,
        None if replay is None else replay.earlier_run_id,
        untrusted_for,
    )
    with _redacted_stderr(redactor):
        return _walk(checked, run_dir, adapter, prompt_for, meta, resume, replay)


def _stage(
    checked: CheckedRun,
    run_dir: Path,
    entries: tuple[dict[str, Any], ...],
    live: bool,
    redactor: Redactor,
) -> RunOutcome | None:
    """Stage the sources; a ``ValueError`` from prepare stops the run (``prepare: <text>``), as does a
    ``StagedSourceChanged`` (``prepare: source <id> changed``)."""
    try:
        stage_sources(checked, run_dir)
    except RunInputError:
        raise
    except StagedSourceChanged as error:
        failure = str(error)  # already reads `prepare: source <id> changed`
    except ValueError as error:
        failure = f"prepare: {error}"
    else:
        return None
    return _stop(run_dir, _Meta(checked, entries, live, redactor), failure, Decimal(0))


def run_pathway(
    *,
    case_id: str,
    sources: Sequence[CaseSource],
    context: Path,
    pathway: PathwayId,
    model: ModelSpec,
    adapter: ModelAdapter,
    cap_usd: Decimal,
    run_dir: Path,
    run_id: str,
    cp_dr: bool = False,
    research_manifest: Path | None = None,
    resume: bool = False,
    replay_from: Path | None = None,
    repaired: frozenset[str] = frozenset(),
) -> RunOutcome:
    """Check, stage, run, with stderr redacted throughout. A refused argument raises and writes
    nothing; a named fault after the first write returns a ``stopped`` outcome with ``run.json``.
    ``resume=True`` continues a killed run in its existing ``run_dir`` (it must hold no
    ``run.json``): nothing is staged, and the identity checks (N1) raise before anything is
    written. The directory's ``flock`` is held for the whole run, fresh or resumed (R9a).
    Any other exception propagates and leaves ``run_dir`` without ``run.json``, with one
    exception of O5's: a failure inside a model tool call is caught by the loop and stops the run
    as a named ``StepStopped``.
    ``replay_from`` (an earlier run directory) with a non-empty ``repaired`` set of planned analytical
    modules makes a rerun after repair (G4): ``repaired`` and the modules downstream of it run live,
    every other analytical module is replayed from the earlier run's retained submissions (no model
    request), and the deterministic publisher runs again. It needs a new ``run_id`` and the earlier
    run's pack in everything but ``run_id``; every refusal comes before anything is written.
    ``run.json.replayed_from_run`` is the earlier ``run_id``. A rerun is a fresh run: not a resume.
    ``cp_dr=True`` takes a ``research_manifest`` (and a manifest takes ``cp_dr=True``); intake runs
    in ``check_arguments``, so a refused manifest raises before anything is written, and the staged
    run holds ``research/evidence.json`` and ``research/rejected.json``."""
    redactor = Redactor()
    with _redacted_stderr(redactor):
        checked = check_arguments(
            case_id=case_id,
            sources=sources,
            context=context,
            pathway=pathway,
            model=model,
            adapter=adapter,
            cap_usd=cap_usd,
            run_dir=run_dir,
            run_id=run_id,
            cp_dr=cp_dr,
            research_manifest=research_manifest,
            resume=resume,
        )
        entries = _source_entries(checked, sources, context)
        replay = _checked_replay(checked, run_dir, resume, replay_from, repaired)
        if resume:
            return _resume_pathway(checked, run_dir, adapter, entries, redactor)
        staged = _stage(checked, run_dir, entries, type(adapter) is LiveAdapter, redactor)
        if staged is not None:
            return staged
        # The directory was created by the exclusive mkdir above, so two fresh runs never share one;
        # the lock follows at once, before the first record of the run (the cap) is written.
        with _single_writer(run_dir):
            _create_cap(
                run_dir,
                checked.cap_usd,
                _mode_of(adapter),
                None if replay is None else replay.earlier_run_id,
            )
            return _run_pathway(checked, run_dir, adapter, entries=entries, replay=replay)


def _checked_replay(
    checked: CheckedRun,
    run_dir: Path,
    resume: bool,
    replay_from: Path | None,
    repaired: frozenset[str],
) -> ReplayPlan | None:
    """The rerun's plan, or None for an ordinary run; every refusal of a rerun is raised here,
    before anything is written."""
    if replay_from is None and not repaired:
        return None
    if resume:
        raise ReplayRefused("a rerun after repair is a fresh run, not a resume")
    return check_replay(checked, run_dir, replay_from, repaired)


def _resume_pathway(
    checked: CheckedRun,
    run_dir: Path,
    adapter: ModelAdapter,
    entries: tuple[dict[str, Any], ...],
    redactor: Redactor,
) -> RunOutcome:
    """Continue the killed run in ``run_dir`` (G5, N1, P3): refused, writing nothing, unless the
    directory exists, holds no ``run.json`` and was begun with these arguments; no staging."""
    if not run_dir.is_dir():
        raise RunDirInvalid(f"{run_dir} is not an existing run directory")
    with _single_writer(run_dir):
        _refuse_rerun(run_dir)
        _check_identity(checked, run_dir, redactor)
        return _run_pathway(checked, run_dir, adapter, entries=entries, resume=True)


__all__ = [
    "CapExists",
    "NoPrompt",
    "ReplayDiverged",
    "ReplayPackChanged",
    "ReplayRefused",
    "ReplayRejected",
    "ResumeMismatch",
    "ResumeRefused",
    "RunDirBusy",
    "run_pathway",
]
