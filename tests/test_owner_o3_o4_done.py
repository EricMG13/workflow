"""O3 and O4 done-when, end to end (Part B O3+O4 Task 7): walk, resume, replay, input cap, faults.

Offline; no network. The model is the recorded adapter: ``o2_case.ScriptAdapter`` answers each
request from the frozen ``cases/o2-synthetic`` payloads and records the answer; ``use_script``
replaces ``RecordedAdapter.complete`` so that the public ``run_pathway`` gets its answers from it.

O3 (a), the walk. The pathway is ``distressed_restructuring`` and its plan is read from
``deploy_vii.contracts`` and the registry at run time (never a module list written here). The
preset has no frozen CP-0 (B21) and no pinned distressed source set: the only pinned file-source
case is ``cases/o2-synthetic``. So the sources are that case's, and CP-0 is TEST INPUT derived
from its frozen readiness review: the modules the case can answer get a ``READY_WITH_LIMITATIONS``
row (the frozen one), every other consumer a ``BLOCKED`` row (the frozen CP-8 row, module renamed),
so CP-0 omits ``Run <module>`` for them, ``Run CP-4`` included. The frozen payloads cite the
context source and the pack by hash; the context here differs from the frozen one by its pathway
word, so those two hashes are rebound to the run's own pack (``rebind``). CP-1A's frozen consumer
rows are cut to the pathway's own ``cp1a_consumers(pack)``, as CP-0's rows are derived from
``live_consumers(pack)``. Nothing else is edited.
The brief's chain (CP-2G and CP-2H settled over a refused CP-4) needs CP-2A, CP-2G and CP-2H
payloads on file sources; none is pinned, so it is not built (reported to the controller).

Fast: CP-0 grants CP-1A only (0.7 s). Slow, ``RUN_PROMOTION`` (release CI; B16): CP-0 also grants
CP-1, so CP-1 settles and CP-4 is refused by the missing command ``Run CP-4``; measured about 300 s.
The expected refusals come from the registry's ``dependencies`` and the grant set, not from the
receipt under test.

O3 (b), resume: the run is killed (``Budget.reserve`` raises a ``BaseException``, the first object
is abandoned) after module 1 and after an invalid first submit, and ``run_pathway(resume=True)``
finishes it. O3 (c), replay: a rerun's ``calls.jsonl`` and ``spent_usd`` (Task 4's offline preset).
O4: an oversized ``read_inputs`` and a patched internal error, at the workflow and at the run.
"""

import http.client
import importlib
import json
import os
import re
import socket
from collections.abc import Callable
from pathlib import Path
from typing import Any, NoReturn

import o2_case
import pytest

from deploy_vii.business_context import cp1a_consumers
from deploy_vii.contracts import PATHWAY_MODULES, PathwayId
from deploy_vii.execution import Execution, NotAuthorized
from deploy_vii.readiness import live_consumers
from deploy_vii.registry import dependencies, plan
from deploy_workflow import owner_workflow as owner
from deploy_workflow.financial_workflow import MAX_LINE
from deploy_workflow.model import transport as transport_module
from deploy_workflow.model.adapter import RecordedAdapter, recorded_adapter
from deploy_workflow.model.budget import Budget
from deploy_workflow.model.record import LOOP_STOPS
from deploy_workflow.owner_workflow import (
    AUDIT,
    BLOCKED_EDGE,
    MAX_INPUT_BYTES,
    OwnerFault,
    OwnerRunReceipt,
    OwnerWorkflow,
    verify_owner_run_receipt,
)
from deploy_workflow.run_inputs import RunOutcome, check_arguments, stage_sources
from deploy_workflow.run_pathway import _run_pathway, run_pathway
from deploy_workflow.workflow import WorkflowError

guards: Any = importlib.import_module("test_owner_guards")
replays: Any = importlib.import_module("test_owner_replay")

PATHWAY: PathwayId = "distressed_restructuring"
FROZEN_PATHWAY = '"pathway": "portfolio_decision"'
CP1_STEPS = ("source_context", "financials", "narrative", "readiness", "quality")
_PROMOTION = pytest.mark.skipif(
    os.environ.get("RUN_PROMOTION") != "1",
    reason="CP-0, CP-1 and CP-1A with the sealed receipt run about 300 s; deferred to release CI (B16)",
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("a test reached the network")

    monkeypatch.setattr(http.client, "HTTPSConnection", refuse)
    monkeypatch.setattr(http.client, "HTTPConnection", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(transport_module, "_default_connection", refuse)


# ================================================================================ the world


def rebind(value: Any, context_sha: str, pack_sha: str) -> Any:
    """``value`` with the ``context`` citations' source hash and every ``pack_sha256`` set to this
    run's own (the frozen payloads cite the frozen context and its pack)."""
    if isinstance(value, dict):
        out = {k: rebind(v, context_sha, pack_sha) for k, v in value.items()}
        if out.get("source_id") == "context" and "source_sha256" in out:
            out["source_sha256"] = context_sha
        if "pack_sha256" in out:
            out["pack_sha256"] = pack_sha
        return out
    if isinstance(value, list):
        return [rebind(item, context_sha, pack_sha) for item in value]
    return value


class DistressedScript(o2_case.ScriptAdapter):
    """The frozen o2 answers on the distressed pathway. ``granted`` are the modules CP-0 lets run;
    ``invalid_first`` makes the first CP-0 request this script answers an invalid payload; the
    next one is the valid review (the repair). The count is the script's own, so it does not
    depend on the prompt composer."""

    granted: frozenset[str] = frozenset()
    invalid_first = False
    _cp0_answered = 0

    def _plan(self, step_id: str, reads: list[str]) -> list[tuple[str, dict[str, Any]]]:
        pack = Execution(self._execution).pack()
        context_sha = next(s.sha256 for s in pack.sources if s.source_id == "context")
        assert context_sha is not None
        if step_id == "source_readiness":
            self._cp0_answered += 1
            if self.invalid_first and self._cp0_answered == 1:
                return [("submit_source_readiness", {})]
            calls = self._readiness(pack)
        elif step_id == "business_context":
            calls = self._business_context(super()._plan(step_id, reads), pack)
        else:
            calls = super()._plan(step_id, reads)
        return [(name, rebind(args, context_sha, pack.content_hash())) for name, args in calls]

    @staticmethod
    def _business_context(
        calls: list[tuple[str, dict[str, Any]]], pack: Any
    ) -> list[tuple[str, dict[str, Any]]]:
        """The frozen CP-1A review with its consumer rows cut to this pathway's consumers."""
        keep = set(cp1a_consumers(pack))
        out = []
        for name, arguments in calls:
            if name == "submit_business_context":
                rows = [c for c in arguments["consumers"] if c["module_id"] in keep]
                assert {c["module_id"] for c in rows} == keep
                arguments = {**arguments, "consumers": rows}
            out.append((name, arguments))
        return out

    def _readiness(self, pack: Any) -> list[tuple[str, dict[str, Any]]]:
        review = o2_case.frozen_submissions()["positive"]["readiness_review"]
        rows = {row["module_id"]: row for row in review["consumers"]}
        blocked = rows["CP-8"]
        assert blocked["readiness"] == "BLOCKED"
        consumers = []
        for module in live_consumers(pack):
            row = rows[module] if module in self.granted else {**blocked, "module_id": module}
            consumers.append(row)
        gaps = [g for g in review["gaps"] if set(g["affected_modules"]) <= {"CP-0"}]
        edited = {**review, "consumers": consumers, "gaps": gaps}
        return [("submit_source_readiness", edited)]


def distressed_context(root: Path) -> Path:
    """The o2 context with its pathway word changed (the one edit; ``check_arguments`` compares it
    with the pathway argument)."""
    text = (o2_case.CASE / "context.json").read_text(encoding="utf-8")
    assert text.count(FROZEN_PATHWAY) == 1
    path = root / "context.json"
    path.write_text(text.replace(FROZEN_PATHWAY, f'"pathway": "{PATHWAY}"'), encoding="utf-8")
    return path


def run_args(root: Path, *, run_id: str = o2_case.RUN_ID) -> dict[str, Any]:
    """The ``run_pathway`` arguments of the distressed run under ``root``; its recordings directory
    is ``root/recordings`` (the genuine recorded adapter reads nothing: the script answers)."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "recordings").mkdir()
    return {
        "case_id": o2_case.CASE_ID,
        "sources": o2_case.case_sources(),
        "context": distressed_context(root),
        "pathway": PATHWAY,
        "model": o2_case.MODEL,
        "adapter": recorded_adapter(o2_case.MODEL, root / "recordings"),
        "cap_usd": o2_case.CAP,
        "run_dir": root / "run",
        "run_id": run_id,
    }


def script_for(
    args: dict[str, Any], granted: tuple[str, ...], answers: tuple[str, ...], **flags: Any
) -> DistressedScript:
    script = DistressedScript(
        args["run_dir"].parent / "recordings",
        answers,
        args["run_dir"] / "execution",
        o2_case.MODEL,
    )
    script.granted = frozenset(granted)
    for name, value in flags.items():
        setattr(script, name, value)
    return script


def use_script(monkeypatch: pytest.MonkeyPatch, script: DistressedScript) -> None:
    """The genuine ``RecordedAdapter`` answers through the script, which records what it said."""

    def complete(self: object, request: Any, **kwargs: Any) -> Any:
        return script.complete(request, **kwargs)

    monkeypatch.setattr(RecordedAdapter, "complete", complete)


def walk(root: Path, granted: tuple[str, ...], answers: tuple[str, ...]) -> tuple[RunOutcome, Path]:
    """Check, stage and walk the distressed run through the private seam with the script."""
    args = run_args(root)
    checked = check_arguments(**args)
    stage_sources(checked, args["run_dir"])
    script = script_for(args, granted, answers)
    outcome = _run_pathway(checked, args["run_dir"], script, o2_case.test_prompt_for)
    return outcome, args["run_dir"]


def receipt_of(run_dir: Path) -> OwnerRunReceipt:
    return OwnerRunReceipt.model_validate_json((run_dir / "owner-run.json").read_text())


def run_json(run_dir: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((run_dir / "run.json").read_text())
    return loaded


# ====================================================================== O3 (a): the walk


def expected_refusals(
    requested: tuple[str, ...], settled: set[str]
) -> dict[str, tuple[tuple[str, ...], tuple[str, ...]]]:
    """Per unsettled planned module the ``(missing_inputs, missing_commands)`` the brief names: the
    registry's upstream modules with no settled head, in plan order; when every upstream is settled,
    CP-0's missing ``Run <module>``. From the registry and the grant set only."""
    order = plan(requested)
    upstream = dependencies(requested)
    out: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}
    for module in order:
        if module in settled:
            continue
        missing = tuple(item for item in order if item in upstream[module] and item not in settled)
        out[module] = (missing, ()) if missing else ((), (f"Run {module}",))
    return out


def assert_usable_heads(run_dir: Path, modules: set[str]) -> None:
    """Each module's head is a usable settle (accepted or restricted), and each module but CP-0
    was begun exactly once: a blocked head or a repaired begin is not a settle after a refusal."""
    receipt = receipt_of(run_dir)
    status = {h.module_id: h.status for h in Execution(run_dir / "execution").read().heads}
    for module in modules:
        assert status[module] in ("accepted", "restricted"), (module, status[module])
        if module != "CP-0":
            assert [b.module_id for b in receipt.begins].count(module) == 1, module


def assert_the_walk(run_dir: Path, outcome: RunOutcome, granted: tuple[str, ...]) -> None:
    """The brief's observable result for a CP-0 that grants ``granted`` (plus CP-0 itself)."""
    requested = PATHWAY_MODULES[PATHWAY]
    order = plan(requested)
    settled = {"CP-0", *granted}
    assert settled <= set(order)
    receipt = receipt_of(run_dir)
    assert receipt.plan == order
    # the walk continued past every refusal: each granted module has its head, later ones included
    assert [h.module_id for h in receipt.heads] == [m for m in order if m in settled]
    expected = expected_refusals(requested, settled)
    assert [r.module_id for r in receipt.refusals] == list(expected)
    assert "CP-4" in expected and "CP-5" in expected
    for refusal in receipt.refusals:
        inputs, commands = expected[refusal.module_id]
        assert (refusal.missing_inputs, refusal.missing_commands) == (inputs, commands)
        if commands:
            assert refusal.reason == str(NotAuthorized(refusal.module_id, ()))
        else:
            assert refusal.reason == BLOCKED_EDGE
    # a refusal inside CP-5's fan-in refuses CP-5 too, naming every refused module it consumes
    cp5 = next(r for r in receipt.refusals if r.module_id == "CP-5")
    assert set(cp5.missing_inputs) >= {m for m in expected if m != "CP-5"}
    assert_usable_heads(run_dir, settled)
    # the receipt verifies against the retained store, and the run ends stopped at the render
    verify_owner_run_receipt(Execution(run_dir / "execution"), receipt)
    assert outcome.outcome == "stopped"
    assert outcome.stopped_reason is not None
    assert outcome.stopped_reason.startswith("render: owner_render_")
    body = run_json(run_dir)
    assert (body["outcome"], body["stopped_reason"]) == ("stopped", outcome.stopped_reason)
    assert not (run_dir / "delivery").exists()  # O3 adds no render behaviour: nothing is rendered


def test_the_walk_continues_past_a_refusal_and_the_receipt_verifies(tmp_path: Path) -> None:
    """CP-0 omits ``Run CP-1`` and every later command but CP-1A's. CP-1 is refused, the walk goes
    on, CP-1A (which needs only CP-0) settles after it, and the rest are refused with named
    missing inputs, CP-4 among them and CP-5 by its fan-in."""
    outcome, run_dir = walk(tmp_path, ("CP-1A",), ("source_readiness", "business_context"))
    assert_the_walk(run_dir, outcome, ("CP-1A",))
    receipt = receipt_of(run_dir)
    cp1 = next(r for r in receipt.refusals if r.module_id == "CP-1")
    assert (cp1.missing_inputs, cp1.missing_commands) == ((), ("Run CP-1",))  # named, not blank
    cp4 = next(r for r in receipt.refusals if r.module_id == "CP-4")
    assert cp4.missing_inputs == ("CP-1",) and cp4.missing_commands == ()
    # one refusal per module, none for a module that settled
    assert len({r.module_id for r in receipt.refusals}) == len(receipt.refusals) > 1


def test_the_recorded_cp0_is_not_refused_by_the_attachments_precheck(tmp_path: Path) -> None:
    """The CP-0 of this world settles (the precheck of Phase 5 Task 3 accepts it): its head is
    ``restricted`` and carries ``Run CP-1A`` and no ``Run CP-4``."""
    _, run_dir = walk(tmp_path, ("CP-1A",), ("source_readiness",))
    head = next(h for h in Execution(run_dir / "execution").read().heads if h.module_id == "CP-0")
    assert head.status == "restricted"
    commands = {c.row_id: c.text for c in head.commands if c.text != "DO NOT RUN"}
    assert commands == {"CP-1A": "Run CP-1A"}
    assert "CP-4" not in commands


@_PROMOTION
def test_the_walk_past_cp4_with_cp1_settled(tmp_path: Path) -> None:
    """Slow: CP-1 settles, so CP-4 is refused by the missing command (``Run CP-4``) and not by CP-1;
    CP-1A settles; CP-4C and CP-5 are refused naming the modules they lack; the receipt verifies."""
    granted = ("CP-1", "CP-1A")
    outcome, run_dir = walk(tmp_path, granted, ("source_readiness", *CP1_STEPS, "business_context"))
    assert_the_walk(run_dir, outcome, granted)
    receipt = receipt_of(run_dir)
    by_module = {r.module_id: r for r in receipt.refusals}
    assert (by_module["CP-4"].missing_inputs, by_module["CP-4"].missing_commands) == (
        (),
        ("Run CP-4",),
    )
    assert "CP-4" in by_module["CP-4C"].missing_inputs
    assert (
        "CP-4" in by_module["CP-5"].missing_inputs and "CP-4C" in by_module["CP-5"].missing_inputs
    )


# =================================================================== O3 (b): kill and resume


class Kill(BaseException):
    """A process killed: not an Exception, so nothing in the run catches it."""


def kill_at_reserve(monkeypatch: pytest.MonkeyPatch, nth: int) -> Callable[[], None]:
    """The process dies as the nth reservation of the run is about to be made; the returned
    function lifts the kill."""
    real = Budget.reserve
    seen = [0]

    def reserve(self: Budget, *a: Any, **k: Any) -> None:
        seen[0] += 1
        if seen[0] == nth:
            raise Kill()
        real(self, *a, **k)

    monkeypatch.setattr(Budget, "reserve", reserve)
    return lambda: monkeypatch.setattr(Budget, "reserve", real)


def remember_instances(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[str, OwnerWorkflow, owner.OwnerState]]:
    """Every ``OwnerWorkflow`` ``create``d or ``open``ed from now on: how it was built, the
    instance, and its ``state()`` at the moment it was returned (before anything drives it)."""
    made: list[tuple[str, OwnerWorkflow, owner.OwnerState]] = []
    for name in ("create", "open"):
        real = getattr(OwnerWorkflow, name)

        def build(*a: Any, _real: Any = real, _name: str = name, **k: Any) -> OwnerWorkflow:
            workflow: OwnerWorkflow = _real(*a, **k)
            made.append((_name, workflow, workflow.state()))
            return workflow

        monkeypatch.setattr(OwnerWorkflow, name, staticmethod(build))
    return made


def records_of(run_dir: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (run_dir / "calls.jsonl").read_text().splitlines()]


def assert_call_indexes_run_from_zero(records: list[dict[str, Any]]) -> None:
    """Within each ``(module, step, attempt)`` the call indexes are 0..n-1 in order, so a resume
    that re-sent a call (a repeated index) or skipped one (a gap) is seen even when each attempt
    has a digest of its own."""
    groups: dict[tuple[str, str, int], list[int]] = {}
    for r in records:
        groups.setdefault((r["module_id"], r["step_id"], r["attempt"]), []).append(r["call_index"])
    for key, indexes in groups.items():
        assert indexes == list(range(len(indexes))), (key, indexes)


def control_receipt(root: Path, monkeypatch: pytest.MonkeyPatch, **flags: Any) -> OwnerRunReceipt:
    """The same run, never killed, for the resumed receipt to equal."""
    args = run_args(root)
    script = script_for(args, ("CP-1A",), ("source_readiness", "business_context"), **flags)
    use_script(monkeypatch, script)
    outcome = run_pathway(**args)
    assert outcome.stopped_reason is not None
    assert outcome.stopped_reason.startswith("render: owner_render_")
    assert_usable_heads(args["run_dir"], {"CP-0", "CP-1A"})
    return receipt_of(args["run_dir"])


_ID = re.compile(r"[0-9a-f]{64}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def normal(receipt: OwnerRunReceipt) -> str:
    """The receipt with every uuid and digest renamed by order of first appearance."""
    names: dict[str, str] = {}
    return _ID.sub(lambda m: names.setdefault(m[0], f"<{len(names)}>"), receipt.model_dump_json())


@pytest.mark.parametrize(
    ("label", "flags", "where"),
    [
        ("after module 1", {}, ("CP-1A", 0)),  # CP-0 settled, CP-1A's first attempt not begun
        ("after an invalid first submit", {"invalid_first": True}, ("CP-0", 1)),  # a repair is due
    ],
)
def test_a_killed_run_resumes_to_the_uninterrupted_receipt(
    label: str,
    flags: dict[str, Any],
    where: tuple[str, int],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    control = control_receipt(tmp_path / "control", monkeypatch, **flags)
    # the killed run: the second reservation (CP-1A's request, or the repair of the invalid
    # first submit) is never made
    args = run_args(tmp_path / "killed")
    script = script_for(args, ("CP-1A",), ("source_readiness", "business_context"), **flags)
    use_script(monkeypatch, script)
    made = remember_instances(monkeypatch)
    lift = kill_at_reserve(monkeypatch, 2)
    with pytest.raises(Kill):
        run_pathway(**args)
    lift()
    run_dir: Path = args["run_dir"]
    assert not (run_dir / "run.json").exists(), label
    (kind, killed, _) = made[-1]
    assert kind == "create"
    before = killed.state()  # the abandoned object, as the kill left it
    sent_before = records_of(run_dir)
    assert len(sent_before) == 1
    # the kill fell where the label says: CP-1A's step open, an invalid first submit counted
    assert (before.module_id, before.attempt) == where, label
    del killed  # abandoned: never used again
    # the resume, with the same recordings: state() agrees at the moment of open
    del made[:]
    outcome = run_pathway(**args, resume=True)
    assert [kind for kind, _, _ in made] == ["open"], label
    assert made[0][2] == before, label
    assert outcome.stopped_reason is not None
    assert outcome.stopped_reason.startswith("render: owner_render_"), label
    receipt = receipt_of(run_dir)
    verify_owner_run_receipt(Execution(run_dir / "execution"), receipt)
    assert normal(receipt) == normal(control), label
    assert_usable_heads(run_dir, {"CP-0", "CP-1A"})  # the repaired CP-0 and CP-1A both settled
    # the finished directory reopens to the state the resumed instance ended in
    reopened = OwnerWorkflow.open(run_dir / "execution", publication_directory=None)
    assert reopened.state() == made[0][1].state(), label
    # calls.jsonl: the first record survives unrewritten and no (digest, call_index) repeats
    records = records_of(run_dir)
    assert records[0] == sent_before[0]
    keys = [(r["invocation_digest"], r["call_index"]) for r in records]
    assert len(keys) == len(set(keys)), label
    assert_call_indexes_run_from_zero(records)


def test_the_state_before_the_kill_is_the_state_after_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The comparison above, pinned unconditionally: a kill after module 1 leaves CP-1A's step
    open, and the instance ``open`` builds shows exactly the killed instance's ``state()``."""
    args = run_args(tmp_path)
    script = script_for(args, ("CP-1A",), ("source_readiness", "business_context"))
    use_script(monkeypatch, script)
    made = remember_instances(monkeypatch)
    lift = kill_at_reserve(monkeypatch, 2)
    with pytest.raises(Kill):
        run_pathway(**args)
    lift()
    before = made[-1][1].state()
    assert before.phase == "analytical" and before.module_id == "CP-1A"
    del made[:]
    run_pathway(**args, resume=True)
    assert made[0][0] == "open" and made[0][2] == before
    reopened = OwnerWorkflow.open(args["run_dir"] / "execution", publication_directory=None)
    assert [h.module_id for h in reopened.state().settled] == ["CP-0", "CP-1A"]
    assert before.settled == reopened.state().settled[:1]


# ======================================================================== O3 (c): replay


def test_a_rerun_holds_only_its_sent_calls_and_its_spend_excludes_replayed_calls(
    tmp_path: Path,
) -> None:
    earlier = replays.author_earlier(tmp_path / "earlier")
    earlier_records = replays.records_of(earlier)
    outcome, script = replays.rerun_private(tmp_path / "rerun", earlier)
    records = replays.records_of(outcome.run_dir)
    assert len(records) == script.sent == 1  # holds only the calls it sent
    assert {r["module_id"] for r in earlier_records} >= {"CP-0"}
    assert all(r["module_id"] != "CP-0" for r in records)  # the replayed module sent nothing
    keys = [(r["invocation_digest"], r["call_index"]) for r in records]
    assert len(keys) == len(set(keys))
    assert_call_indexes_run_from_zero(records)
    spent = replays.spent_by_records(records)
    assert outcome.spent_usd == spent > 0  # exactly what its own records cost
    assert replays.run_json(outcome.run_dir)["replayed_from_run"] == replays.EARLIER_ID


# ===================================================================== O4 (a): the input cap


def test_the_cap_is_the_line_bound() -> None:
    assert MAX_INPUT_BYTES == MAX_LINE


@pytest.mark.usefixtures("owner_world")
def test_an_oversized_read_inputs_is_inputs_too_large_and_a_fault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = guards._narrative_world(tmp_path)
    before = workflow.state()
    guards._serve(monkeypatch, guards._body_of(MAX_INPUT_BYTES + 1))
    with pytest.raises(WorkflowError) as caught:
        workflow.read_inputs()
    assert caught.value.code == "inputs_too_large"
    assert workflow.state() == before  # nothing was counted or retained
    (fault,) = guards._faults(workflow)
    assert (fault.code, fault.size, fault.cap) == (
        "InputsTooLarge",
        MAX_INPUT_BYTES + 1,
        MAX_INPUT_BYTES,
    )
    assert fault.binding == workflow.binding


@pytest.fixture
def owner_world(monkeypatch: pytest.MonkeyPatch) -> None:
    """The financial slice's ``start`` builds the owner workflow (as ``test_owner_guards`` does)."""
    monkeypatch.setattr(guards.financial, "start", guards._owner_start)


def test_an_oversized_read_stops_the_run_as_inputs_too_large(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    guards._oversized_narrative(monkeypatch)
    authored = o2_case.author(tmp_path, answers=guards.NARRATIVE_ANSWERS)
    run_dir = authored.run_dir
    assert authored.outcome.outcome == "stopped"
    body = run_json(run_dir)
    assert body["outcome"] == "stopped"
    assert "InputsTooLarge" in LOOP_STOPS
    # the loop's name, then its detail: ``StepStopped`` carries ``<name>: <detail>``
    name, _, detail = body["stopped_reason"].partition(": ")
    assert name == "InputsTooLarge" and detail == "WorkflowError: inputs_too_large"
    (fault_path,) = (run_dir / "execution" / AUDIT / "faults").iterdir()
    fault = OwnerFault.model_validate_json(fault_path.read_bytes())
    assert (fault.code, fault.size, fault.cap) == (
        "InputsTooLarge",
        MAX_INPUT_BYTES + 1,
        MAX_INPUT_BYTES,
    )
    assert guards.MARKER not in (run_dir / "run.json").read_text()  # the body is nowhere


# ===================================================================== O4 (b): internal error


def test_a_patched_internal_error_is_journaled_and_names_its_type_in_the_stop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Through the run, the tool loop is the caller: it catches the failure of a tool call, which
    O5 documents and logs, and stops the run naming the exception's type. The record is written
    first; the exception itself reaching a caller is the next test."""
    monkeypatch.setattr(owner, "_inputs", guards._boom)
    authored = o2_case.author(tmp_path, answers=guards.NARRATIVE_ANSWERS)
    run_dir = authored.run_dir
    assert authored.outcome.outcome == "stopped"
    reason = run_json(run_dir)["stopped_reason"]
    assert reason == authored.outcome.stopped_reason == "WorkflowError: RuntimeError: boom"
    paths = list((run_dir / "execution" / AUDIT / "faults").iterdir())
    faults = [OwnerFault.model_validate_json(p.read_bytes()) for p in paths]
    (fault,) = [f for f in faults if f.code == "InternalError"]
    assert (fault.operation, fault.error_type, fault.detail) == (
        "read_inputs",
        "RuntimeError",
        "boom",
    )
    assert not (run_dir / "owner-run.json").exists()


def test_an_internal_error_at_the_workflow_reaches_the_caller_with_its_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workflow = guards._read_world(tmp_path, monkeypatch)
    monkeypatch.setattr(owner, "_inputs", guards._boom)
    with pytest.raises(RuntimeError, match="^boom$"):
        workflow.read_inputs()
    (fault,) = guards._internal_faults(workflow)
    assert fault.error_type == "RuntimeError" and fault.operation == "read_inputs"
