"""A rerun after repair replays the retained upstream submissions (O3 Task 4, gap G4).

A repaired module and every module that consumes it, transitively, run live; every other analytical
module is replayed from the earlier run: its retained valid submissions are matched **by module and
step** (never by invocation digest: the earlier run's invocation preimages and reservation
markers are not read) and resubmitted through the new run's own ``OwnerWorkflow``, so the new run's journal, tickets,
bindings and receipt are its own and a replayed step sends no model request. The deterministic
publisher is never replayed: ``publish`` runs again.

The earlier run directory is read only. Divergence stops the run and never falls back to a live
call: a replayed ``invoke`` whose answer differs from the retained one raises ``ReplayDiverged``,
a replayed submission the validator does not accept raises ``ReplayRejected``; both journal an
``OwnerFault`` under ``faults/``.

Two retained payloads bind the earlier run and are rewritten, by the allowlist ``REBOUND_FIELDS``
alone and only while the rerun's pack equals the earlier one in everything but ``run.run_id``
(``ReplayPackChanged`` otherwise): the CP-0 readiness review's ``pack_sha256`` (the pack hash
includes ``run_id``) and the CP-1 financials' ``run_id``. Any other run-dependent value in a
retained payload makes the submission ``ReplayRejected``.
"""

import hashlib
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

from deploy_vii.contracts import Contract, Hash, Identifier, Text
from deploy_vii.execution import CONTEXT_PRODUCERS, Attempt, Execution, ExecutionSnapshot
from deploy_vii.preparation import PreparedPack, load_pack
from deploy_vii.registry import dependencies, plan
from deploy_workflow.model.turn import TurnError, dump_json, load_arguments
from deploy_workflow.owner_workflow import (
    AUDIT,
    OWNER_SPECS,
    OwnerCall,
    OwnerFault,
    OwnerSubmission,
    OwnerWorkflow,
    fill_at_binding,
)
from deploy_workflow.run_inputs import (
    CheckedRun,
    RunInputError,
    StagedSourceChanged,
    stage_sources,
)
from deploy_workflow.workflow import WorkflowError

# (module, step) -> the payload fields rewritten to the rerun's own value, each only when it holds
# the earlier run's own value. Nothing wider (ruling N1, T4-R4). The fields sit in the object at
# ``_REBOUND_HOLDER[(module, step)]`` (the CP-1 financials keep ``run_id`` in ``financial``).
REBOUND_FIELDS: Mapping[tuple[str, str], tuple[str, ...]] = MappingProxyType(
    {
        ("CP-0", "source_readiness"): ("pack_sha256",),
        ("CP-1", "financials"): ("run_id",),
    }
)
REBOUND_HOLDER: Mapping[tuple[str, str], tuple[str, ...]] = MappingProxyType(
    {("CP-0", "source_readiness"): (), ("CP-1", "financials"): ("financial",)}
)
REPLAYS = "replays"
FAULTS = "faults"


class ReplayRefused(RunInputError):
    """A rerun is refused before anything is written."""

    code = "replay_refused"


class ReplayPackChanged(ReplayRefused):
    """The rerun's pack differs from the earlier run's in more than ``run.run_id``: changed
    sources need a fresh run."""

    code = "replay_pack_changed"


class ReplayError(Exception):
    """A replay that stops the run. ``str`` is ``<module> <step>: <detail>``; ``run_pathway``
    writes it after the class name (``ReplayDiverged: CP-0 source_readiness: call``)."""

    def __init__(self, module: str, step: str, detail: str) -> None:
        super().__init__(f"{module} {step}: {detail}")
        self.module, self.step, self.detail = module, step, detail


class ReplayDiverged(ReplayError):
    """A replayed ``invoke`` answered differently from the retained call."""


class ReplayRejected(ReplayError):
    """A replayed submission was not ``valid``, or its retained evidence could not be used."""

    def __init__(self, module: str, step: str, issues: tuple[str, ...]) -> None:
        super().__init__(module, step, "; ".join(issues) or "not valid")
        self.issues = issues


class Rebound(Contract):
    path: Text
    old: Text
    new: Text


class ReplayRecord(Contract):
    """One ``replays`` audit record, per replayed step. ``earlier_payload_sha256`` and
    ``payload_sha256`` are the hashes of the payload as the earlier run and the rerun submitted it
    (equal unless ``rebound`` names a rewrite); ``snapshot_sha256`` is the rerun's snapshot after."""

    schema_version: Literal["replay/1"] = "replay/1"
    earlier_run_id: Identifier
    module_id: Identifier
    step_id: Identifier
    earlier_payload_sha256: Hash
    payload_sha256: Hash
    snapshot_sha256: Hash
    rebound: tuple[Rebound, ...] = ()


class ReplayLive(Contract):
    """One ``replays`` audit record for a module that was to be replayed but runs live, and why
    (never a silent gap). Written before the module's first live step."""

    schema_version: Literal["replay-live/1"] = "replay-live/1"
    earlier_run_id: Identifier
    module_id: Identifier
    reason: Text


@dataclass(frozen=True)
class ReplayPlan:
    """``replayed`` and ``live`` are the analytical modules in plan order. ``unreplayable`` names
    each module that would have been replayed but runs live, and why (never a silent gap)."""

    earlier: Path
    earlier_run_id: str
    replayed: tuple[str, ...]
    live: tuple[str, ...]
    unreplayable: tuple[tuple[str, str], ...] = ()


# ------------------------------------------------------------------ the earlier run, read only


def _execution_of(earlier: Path) -> Execution:
    return Execution(earlier / "execution")


def _records[T: Contract](earlier: Path, kind: str, model: type[T]) -> list[T]:
    """The earlier run's retained records of ``kind``: each parses, re-serialises to its own bytes
    and is named by its own digest, or the earlier audit is torn and the rerun refused."""
    directory = earlier / "execution" / AUDIT / kind
    found: list[T] = []
    for path in sorted(directory.iterdir()) if directory.is_dir() else ():
        if path.name.startswith("."):
            continue
        raw = path.read_bytes()
        try:
            value = model.model_validate_json(raw)
        except ValueError:
            raise ReplayRefused(f"the earlier run's {kind} record {path.name} is torn") from None
        if value.model_dump_json().encode() != raw or value.content_hash() != path.name:
            raise ReplayRefused(f"the earlier run's {kind} record {path.name} is torn")
        found.append(value)
    return found


def _settled_attempt(snapshot: ExecutionSnapshot, module_id: str) -> Attempt | None:
    """The attempt that settled the module's accepted or restricted head, finished and issue-free."""
    head = next((h for h in snapshot.heads if h.module_id == module_id), None)
    if head is None or head.status not in ("accepted", "restricted"):
        return None
    attempt = next((a for a in snapshot.attempts if a.result_sha256 == head.result_sha256), None)
    if attempt is None or attempt.status != "finished" or attempt.issues:
        return None
    return attempt


class _Earlier:
    """The earlier run's snapshot and the records replay reads: calls and submissions."""

    def __init__(self, earlier: Path) -> None:
        self.directory = earlier
        self.store = _execution_of(earlier)
        try:
            self.snapshot = self.store.read()
        except (OSError, ValueError):
            raise ReplayRefused(f"{earlier} holds no readable retained execution/") from None
        self.calls = {c.call_id: c for c in _records(earlier, "calls", OwnerCall)}
        self.submissions = _records(earlier, "submissions", OwnerSubmission)

    def valid_submission(self, ticket_id: str, step_id: str) -> OwnerSubmission | None:
        """The latest valid submission of the step on the ticket, matched by module and step."""
        found = [
            s
            for s in self.submissions
            if s.disposition == "valid"
            and (s.binding.binding.ticket_id, s.binding.binding.step_id) == (ticket_id, step_id)
        ]
        return max(found, key=lambda s: s.sequence, default=None)

    def bound_submission(self, attempt: Attempt, step_id: str) -> OwnerSubmission | None:
        """The valid submission of the step, bound to the journal: its stored payload and output
        are the digests the settled attempt's step holds, its raw payload fills to that stored
        payload, and its call ids are the calls retained at its binding. A record that disagrees
        means the earlier run is inconsistent and the rerun is refused (``ReplayRefused``)."""
        chosen = self.valid_submission(attempt.ticket_id, step_id)
        step = next((s for s in attempt.steps if s.step_id == step_id), None)
        if chosen is None or step is None:
            return None
        where = f"{attempt.module_id} {step_id}"
        if chosen.stored_payload_sha256 != step.payload_sha256:
            raise ReplayRefused(
                f"{where}: the retained submission's stored payload differs from the journal's"
            )
        if chosen.step_output_sha256 != step.output_sha256:
            raise ReplayRefused(
                f"{where}: the retained submission's output differs from the journal's"
            )
        self._check_raw_payload(chosen, step.payload_sha256, where)
        if chosen.binding.call_ids != self._call_ids_at(chosen):
            raise ReplayRefused(
                f"{where}: the retained submission's call ids differ from the retained calls"
            )
        return chosen

    def _check_raw_payload(self, chosen: OwnerSubmission, journal_sha: str, where: str) -> None:
        """The retained raw payload, filled by the journal's own rules at the submission's binding,
        is the stored payload the journal settled. (A raw payload that cannot be read is left to
        ``payload``, which rejects it when the step is replayed.)"""
        binding = chosen.binding.binding
        try:
            raw = self.payload(chosen.binding.payload_sha256, binding.module_id, binding.step_id)
        except ReplayRejected:
            return
        try:
            stored = fill_at_binding(self.store, binding, raw)[0]
        except (ValueError, WorkflowError):
            raise ReplayRefused(
                f"{where}: the retained payload cannot be filled as the journal did"
            ) from None
        if _sha256(stored.encode()) != journal_sha:
            raise ReplayRefused(f"{where}: the retained payload is not the one the journal settled")

    def _call_ids_at(self, submission: OwnerSubmission) -> tuple[str, ...]:
        """The ids of the calls retained at the submission's own binding, in sequence order."""
        calls = [c for c in self.calls.values() if c.binding == submission.binding.binding]
        return tuple(c.call_id for c in sorted(calls, key=lambda c: c.sequence))

    def payload(self, digest: str, module: str, step: str) -> str:
        path = self.directory / "execution" / AUDIT / "payloads" / digest
        try:
            raw = path.read_bytes()
        except OSError:
            raise ReplayRejected(module, step, ("a retained payload is missing",)) from None
        if _sha256(raw) != digest:
            raise ReplayRejected(module, step, ("a retained payload does not match its digest",))
        return raw.decode("utf-8")

    def unusable(self, module_id: str) -> str | None:
        """Why the module cannot be replayed from this run, or None."""
        attempt = _settled_attempt(self.snapshot, module_id)
        if attempt is None:
            return "the earlier run holds no settled, valid attempt of it"
        for step in OWNER_SPECS[module_id].steps:
            if self.valid_submission(attempt.ticket_id, step.step_id) is None:
                return f"the earlier run holds no valid submission of step {step.step_id}"
        for step in OWNER_SPECS[module_id].steps:
            self.bound_submission(attempt, step.step_id)
        return None


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


# ------------------------------------------------------------------ planning


def _edges(planned: tuple[str, ...]) -> dict[str, set[str]]:
    """The registry's producer edges of the planned modules, plus the context producers the
    journal binds as lineage (CP-1A cites CP-1 figures though its registry edge is CP-0 only)."""
    graph = dependencies(planned)
    for consumer, producers in CONTEXT_PRODUCERS.items():
        if consumer in graph:
            graph[consumer] |= {p for p in producers if p in graph}
    return graph


def plan_replay(earlier: Path, plan: tuple[str, ...], repaired: frozenset[str]) -> ReplayPlan:
    """Which modules replay and which run live. ``earlier`` is the earlier run directory and
    ``plan`` the planned modules in order. ``live = repaired | downstream(repaired)``; every other
    analytical module replays, unless the earlier run holds no settled valid attempt with a valid
    submission of each step, in which case it and its consumers run live and the plan says why."""
    return _plan(_Earlier(earlier), plan, repaired)


def _live_modules(
    retained: _Earlier, planned: tuple[str, ...], repaired: frozenset[str]
) -> tuple[set[str], list[tuple[str, str]]]:
    """The modules that run live (the republished publisher included, so that its consumers
    follow) and why each one the earlier run could not supply does."""
    graph = _edges(planned)
    live: set[str] = set()
    why: list[tuple[str, str]] = []
    for module in planned:
        if module in repaired or graph[module] & live:
            live.add(module)
        elif OWNER_SPECS[module].kind == "analytical":
            reason = retained.unusable(module)
            if reason is not None:
                live.add(module)
                why.append((module, reason))
    return live, why


def _plan(retained: _Earlier, planned: tuple[str, ...], repaired: frozenset[str]) -> ReplayPlan:
    analytical = [m for m in planned if OWNER_SPECS[m].kind == "analytical"]
    if not repaired or not repaired <= set(analytical):
        raise ReplayRefused("repaired must be a non-empty set of planned analytical modules")
    live, why = _live_modules(retained, planned, repaired)
    return ReplayPlan(
        retained.directory,
        retained.snapshot.run.run_id,
        tuple(m for m in analytical if m not in live),
        tuple(m for m in analytical if m in live),
        tuple(why),
    )


def _masked(pack: PreparedPack) -> dict[str, Any]:
    document: dict[str, Any] = pack.model_dump(mode="json")
    document["run"]["run_id"] = ""
    return document


def check_same_pack(earlier: PreparedPack, rerun: PreparedPack) -> None:
    """The two packs are equal in everything but ``run.run_id`` (every ``Source`` field counts)."""
    if _masked(earlier) != _masked(rerun):
        raise ReplayPackChanged(
            "the sources or the run differ from the earlier run's: use a fresh run"
        )


def _staged_pack(checked: CheckedRun) -> PreparedPack | None:
    """The rerun's pack, built in a temporary directory that is removed before this returns; None
    when preparation fails (the real staging fails the same way and stops the run with its own
    ``prepare:`` reason, so there is nothing to compare)."""
    with tempfile.TemporaryDirectory(prefix="rerun-pack-") as scratch:
        probe = Path(scratch) / "run"
        try:
            stage_sources(checked, probe)
        except (ValueError, StagedSourceChanged):
            return None
        return load_pack(probe / "pack")


def check_replay(
    checked: CheckedRun, run_dir: Path, replay_from: Path | None, repaired: frozenset[str]
) -> ReplayPlan:
    """Every refusal of a rerun, before anything is written in ``run_dir``: the arguments, the
    earlier run directory, the run id, the repaired set and the pack."""
    if replay_from is None or not repaired:
        raise ReplayRefused("a rerun needs replay_from and a non-empty repaired set, together")
    if not (replay_from / "execution").is_dir():
        raise ReplayRefused(f"{replay_from} holds no retained execution/")
    here, there = run_dir.resolve(), replay_from.resolve()
    if here == there or here in there.parents or there in here.parents:
        raise ReplayRefused("the run directory and the earlier run directory contain one another")
    retained = _Earlier(replay_from)
    if retained.snapshot.run.run_id == checked.run_id:
        raise ReplayRefused("the rerun needs a run_id other than the earlier run's")
    planned = plan(checked.request.run.requested_modules)
    found = _plan(retained, planned, repaired)
    rerun = _staged_pack(checked)
    if rerun is not None:
        check_same_pack(retained.store.pack(retained.snapshot), rerun)
    return found


# ------------------------------------------------------------------ replaying a module


def _write_record(execution: Path, kind: str, value: Contract) -> None:
    """Retain ``value`` under ``owner-run-audit/<kind>/<its digest>``, create-once."""
    path = execution / AUDIT / kind / value.content_hash()
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = value.model_dump_json().encode()
    try:
        with path.open("xb") as stream:
            stream.write(raw)
    except FileExistsError:
        if path.read_bytes() != raw:
            raise ReplayRefused(f"{path} exists with other bytes") from None


def _fault(execution: Path, code: str, kind: str, digest: str) -> None:
    _write_record(execution, FAULTS, OwnerFault(code=code, kind=kind, digest=digest))


@dataclass(frozen=True)
class _Identity:
    pack_sha256: str
    run_id: str

    @classmethod
    def of(cls, store: Execution) -> "_Identity":
        snapshot = store.read()
        return cls(snapshot.pack_sha256, snapshot.run.run_id)


def _rebind(
    module: str, step: str, text: str, earlier: _Identity, rerun: _Identity
) -> tuple[str, tuple[Rebound, ...]]:
    """``text`` with each allowlisted field that holds the earlier run's own value set to the
    rerun's; the text unchanged, and no record, when none does."""
    fields = REBOUND_FIELDS.get((module, step))
    if fields is None:
        return text, ()
    try:
        document = load_arguments(text)
    except TurnError:
        return text, ()  # not an object: the validator refuses it
    holder: Any = document
    for key in REBOUND_HOLDER[(module, step)]:
        holder = holder.get(key) if isinstance(holder, dict) else None
    if not isinstance(holder, dict):
        return text, ()
    changes: list[Rebound] = []
    for name in fields:
        old, new = getattr(earlier, name), getattr(rerun, name)
        if holder.get(name) == old and old != new:
            holder[name] = new
            path = ".".join((*REBOUND_HOLDER[(module, step)], name))
            changes.append(Rebound(path=path, old=old, new=new))
    return (dump_json(document), tuple(changes)) if changes else (text, ())


def _same_answer(call: OwnerCall, got: dict[str, Any]) -> bool:
    """The retained call and the replayed one agree: the body (evidence text included), the status
    and the error code. The call id, sequence and binding are the rerun's own."""
    return (got["body"], got["status"], got["error_code"]) == (
        call.body,
        call.status,
        call.error_code,
    )


def _replay_calls(
    workflow: OwnerWorkflow, retained: _Earlier, submission: OwnerSubmission, execution: Path
) -> None:
    binding = submission.binding.binding
    module, step = binding.module_id, binding.step_id
    for call_id in submission.binding.call_ids:
        call = retained.calls.get(call_id)
        if call is None:
            raise ReplayRejected(module, step, ("a retained call is missing",))
        got = workflow.invoke(call.tool, dict(call.arguments))
        if not _same_answer(call, got):
            _fault(execution, "replay_diverged", "calls", call.content_hash())
            raise ReplayDiverged(module, step, "call")


def _replay_step(
    workflow: OwnerWorkflow, retained: _Earlier, attempt: Attempt, execution: Path
) -> None:
    binding = workflow.binding
    module, step = binding.module_id, binding.step_id
    submission = retained.bound_submission(attempt, step)
    if submission is None:
        raise ReplayRejected(module, step, ("the earlier run holds no valid submission",))
    earlier_sha = submission.binding.payload_sha256
    payload = retained.payload(earlier_sha, module, step)
    if workflow.spec.inputs != "none":
        workflow.read_inputs()  # the body may embed the new run_id: recorded, never compared
    _replay_calls(workflow, retained, submission, execution)
    text, rebound = _rebind(
        module, step, payload, _Identity.of(retained.store), _Identity.of(Execution(execution))
    )
    result = workflow.submit_review(text)
    if result["status"] != "valid":
        _fault(execution, "replay_rejected", "submissions", submission.content_hash())
        raise ReplayRejected(module, step, tuple(result["issues"]))
    _write_record(
        execution,
        REPLAYS,
        ReplayRecord(
            earlier_run_id=retained.snapshot.run.run_id,
            module_id=module,
            step_id=step,
            earlier_payload_sha256=earlier_sha,
            payload_sha256=_sha256(text.encode()),
            snapshot_sha256=result["snapshot_sha256"],
            rebound=rebound,
        ),
    )


def journal_unreplayable(plan: ReplayPlan, execution: Path) -> None:
    """Record each module that was to be replayed but runs live, with the reason, before any
    live step (``replays/``, beside the records of the replayed steps)."""
    for module_id, reason in plan.unreplayable:
        _write_record(
            execution,
            REPLAYS,
            ReplayLive(earlier_run_id=plan.earlier_run_id, module_id=module_id, reason=reason),
        )


def replay_module(
    workflow: OwnerWorkflow, earlier: Path, module_id: str, *, execution: Path
) -> None:
    """Replay the active module's steps from the earlier run directory ``earlier``, in order,
    until the module settles. ``execution`` is the new run's execution directory (where the
    ``replays`` and ``faults`` records go). The caller has checked the pack (``check_replay``)."""
    retained = _Earlier(earlier)
    check_same_pack(retained.store.pack(retained.snapshot), Execution(execution).pack())
    attempt = _settled_attempt(retained.snapshot, module_id)
    if attempt is None:
        raise ReplayRejected(module_id, "-", ("the earlier run holds no settled valid attempt",))
    for planned in OWNER_SPECS[module_id].steps:  # every step bound to the journal before a write
        retained.bound_submission(attempt, planned.step_id)
    seen: set[str] = set()
    while workflow.phase == "analytical" and workflow.binding.module_id == module_id:
        step = workflow.binding.step_id
        if step in seen:
            raise ReplayRejected(module_id, step, ("the step came back after a valid submission",))
        seen.add(step)
        _replay_step(workflow, retained, attempt, execution)


__all__ = [
    "REBOUND_FIELDS",
    "REBOUND_HOLDER",
    "Rebound",
    "ReplayDiverged",
    "ReplayError",
    "ReplayLive",
    "ReplayPackChanged",
    "ReplayPlan",
    "ReplayRecord",
    "ReplayRefused",
    "ReplayRejected",
    "check_replay",
    "check_same_pack",
    "journal_unreplayable",
    "plan_replay",
    "replay_module",
]
