"""A rerun after repair replays the retained upstream submissions (O3 Task 4, gap G4): the plan.

A repaired module and every module that consumes it, transitively, run live; every other analytical
module is replayed from the earlier run. ``plan_replay`` decides which, from the registry graph and
the earlier run's retained, settled attempts (a module the earlier run cannot supply runs live, with
the reason); ``check_replay`` is every refusal of a rerun before anything is written, including the
pack check: the rerun's pack must equal the earlier one in everything but ``run.run_id``
(``ReplayPackChanged`` otherwise). The earlier run directory is read only.
"""

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from deploy_vii.contracts import Contract
from deploy_vii.execution import CONTEXT_PRODUCERS, Attempt, Execution, ExecutionSnapshot
from deploy_vii.preparation import PreparedPack, load_pack
from deploy_vii.registry import dependencies, plan
from deploy_workflow.owner_workflow import AUDIT, OWNER_SPECS, OwnerCall, OwnerSubmission
from deploy_workflow.run_inputs import (
    CheckedRun,
    RunInputError,
    StagedSourceChanged,
    stage_sources,
)


class ReplayRefused(RunInputError):
    """A rerun is refused before anything is written."""

    code = "replay_refused"


class ReplayPackChanged(ReplayRefused):
    """The rerun's pack differs from the earlier run's in more than ``run.run_id``: changed
    sources need a fresh run."""

    code = "replay_pack_changed"


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

    def unusable(self, module_id: str) -> str | None:
        """Why the module cannot be replayed from this run, or None."""
        attempt = _settled_attempt(self.snapshot, module_id)
        if attempt is None:
            return "the earlier run holds no settled, valid attempt of it"
        for step in OWNER_SPECS[module_id].steps:
            if self.valid_submission(attempt.ticket_id, step.step_id) is None:
                return f"the earlier run holds no valid submission of step {step.step_id}"
        return None


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
    if replay_from.resolve() == run_dir.resolve():
        raise ReplayRefused("replay_from is the new run directory")
    retained = _Earlier(replay_from)
    if retained.snapshot.run.run_id == checked.run_id:
        raise ReplayRefused("the rerun needs a run_id other than the earlier run's")
    planned = plan(checked.request.run.requested_modules)
    found = _plan(retained, planned, repaired)
    rerun = _staged_pack(checked)
    if rerun is not None:
        check_same_pack(retained.store.pack(retained.snapshot), rerun)
    return found


__all__ = [
    "ReplayPackChanged",
    "ReplayPlan",
    "ReplayRefused",
    "check_replay",
    "check_same_pack",
    "plan_replay",
]
