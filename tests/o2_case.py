"""The O2 synthetic case: authoring and replaying recordings through ``_run_pathway`` (O2 Task 5).

Test-only. ``ScriptAdapter`` answers a request from the frozen ``cases/o2-synthetic`` payload for the
step and appends ``{"invocation_digest", "call_index", "response"}`` to a recordings file; it is
never passed to ``run_pathway`` (whose exact-type check refuses it) but to the private
``_run_pathway`` after ``check_arguments`` (with a plain ``recorded_adapter`` of the same config)
and ``stage_sources``. The replay is a second ``_run_pathway`` over a fresh run directory with the
same ``run_id`` (the pack hash includes it) and a plain ``recorded_adapter`` over that file.

``usage`` counts are test-authored constants: offline spend is not money (Q7). ``test_prompt_for``
is a TEST composer: it proves orchestration, not the prompts (O6), and recordings made with it stop
matching once O6 changes the prompt (the invocation digest includes the prompt hash).
"""

import contextlib
import hashlib
import importlib
import json
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from functools import partial
from pathlib import Path
from typing import Any
from unittest import mock

import s1a_runs as s1

from deploy_vii.contracts import PathwayId
from deploy_vii.execution import Execution
from deploy_vii.preparation import PreparedPack
from deploy_workflow import run_pathway as run_pathway_module
from deploy_workflow.model.adapter import (
    AdapterReply,
    ModelAdapter,
    RecordingMissing,
    recorded_adapter,
)
from deploy_workflow.model.loop import PromptFor, ToolLoop
from deploy_workflow.model.turn import (
    Message,
    ModelSpec,
    ToolCall,
    Turn,
    TurnRequest,
    Usage,
    dump_json,
    load_arguments,
    turn_to_json,
)
from deploy_workflow.owner_workflow import OwnerBinding, StepSpec
from deploy_workflow.run_inputs import CaseSource, RunOutcome, check_arguments, stage_sources
from deploy_workflow.run_pathway import _run_pathway

fw: Any = importlib.import_module("test_financial_workflow")
ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "o2-synthetic"
CASE_ID = "o2-synthetic"
RUN_ID = "o2-synthetic-portfolio-decision"
PATHWAY: PathwayId = "portfolio_decision"
MODEL = ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium")
CAP = Decimal(5)
# Test-authored counts, not measured: offline spend is cap logic, not money (Q7).
USAGE = Usage(input_tokens=1000, output_tokens=200)
# A TEST-authored lower bound on bytes per token, for the walk past CP-1 narrative: run_pathway
# builds its ToolLoop with the sound default of 1, which sizes the narrative step's second request
# (the 669 KB read body) above the model's listed context (ContextTooLong, pinned by a test).
TEST_BYTES_PER_TOKEN = Decimal(4)
STARTED, FINISHED = 1_000.0, 1_001.0
SOURCE_IDS = ("identity", "financial", "business", "market")
# Step id -> the key of the frozen payload under ``positive``. Only a step whose frozen payload
# needs no run-time binding is listed: ``credit_synthesis`` carries ``{{FIG:name}}`` references that
# need the settled CP-1 facts, and CP-1's later steps (financials, narrative, readiness, quality)
# have no payload in this oracle at all.
FROZEN_STEP = {
    "source_readiness": "readiness_review",
    "source_context": "cp1_source_context",
    "business_context": "business_context",
    "relative_value": "relative_value",
    "integrity_review": "integrity_review",
    "committee_challenge": "committee_challenge",
}
_SECTION = {**FROZEN_STEP, "credit_synthesis": "credit_synthesis"}
SEARCHES = (("financial", "subsequent"), ("business", "acquisition"))


def frozen_submissions() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((CASE / "submissions.json").read_text(encoding="utf-8"))
    return loaded


def payload_for(step_id: str) -> str:
    """The frozen payload of ``step_id`` as JSON text; ``KeyError`` when the oracle holds none."""
    return json.dumps(frozen_submissions()["positive"][FROZEN_STEP[step_id]])


def check_pins() -> None:
    """The oracle files are the ones ``cases/PINS.json`` pins; a drifted or missing file raises."""
    pins: dict[str, str] = json.loads((ROOT / "cases" / "PINS.json").read_text(encoding="utf-8"))
    for key, digest in pins.items():
        if key.startswith("cases/o2-synthetic/") and not key.endswith("build.py"):
            found = hashlib.sha256((ROOT / key).read_bytes()).hexdigest()
            if found != digest:
                raise RuntimeError(f"oracle drift: {key}")


def case_sources() -> list[CaseSource]:
    return [CaseSource(name, CASE / f"{name}.txt", "text/plain") for name in SOURCE_IDS]


def test_prompt_for(pack: PreparedPack) -> PromptFor:
    """TEST composer (a ``PromptFactory``): a short fixed prompt per step and attempt. It is not
    the prompt of any live run; O6 supplies those."""

    def prompt_for(
        binding: OwnerBinding, spec: StepSpec, issues: tuple[str, ...]
    ) -> tuple[Message, ...]:
        text = f"TEST COMPOSER. Run {pack.run.run_id}, step {binding.step_id}, attempt {binding.attempt}."
        if issues:
            text += "\nREPAIR: " + "; ".join(issues)
        return (Message("system", "TEST COMPOSER: orchestration only."), Message("user", text))

    return prompt_for


# The steps the script answers, in walk order. Their payloads are the frozen ones, the frozen CP-1
# financials, or computed at run time from the step's read inputs exactly as ``s1a_runs.drive_cp1``
# does (narrative, readiness, quality) and as the frozen drivers bind ``{{FIG:name}}`` (CP-2, CP-3).
ALL_STEPS = (
    "source_readiness",
    "source_context",
    "financials",
    "narrative",
    "readiness",
    "quality",
    "business_context",
    "credit_synthesis",
    "relative_value",
    "integrity_review",
    "committee_challenge",
)
# Steps whose first request is a read_inputs call; the submit follows in the next request.
READ_FIRST = (
    "narrative",
    "readiness",
    "quality",
    "credit_synthesis",
    "integrity_review",
    "committee_challenge",
)
BUSINESS_SEARCH = ("business", "not disclosed")  # tests/s1a_runs.py drive_cp1a


def frozen_financials() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((CASE / "cp1-financials.json").read_text(encoding="utf-8"))
    return loaded


def _figure_bindings(store: Execution, text: str) -> dict[str, tuple[str, str]]:
    """name -> (fact_id, unit_token): each figure the text names, selected from the settled CP-1
    head as ``s1a_runs.fig_bindings`` does, with the oracle's unit token."""
    figures = frozen_submissions()["figures"]
    head = next(h for h in store.read().heads if h.module_id == "CP-1")
    facts = store.head_module(head).facts
    return {
        name: (s1.figure_fact(facts, name).fact_id, figures[name]["unit_token"])
        for name in s1.figure_names(text)
    }


class ScriptAdapter:
    """Answers a request from the frozen payloads and records the answer. ``answers`` names the
    steps it will answer; a request for any other step raises ``RecordingMissing`` (nothing was
    recorded for it, as for a recorded adapter), which O5 records as ``AdapterError`` and stops
    the run on. It returns no raw body (a recording is the evidence). ``execution`` is the run's
    execution store, read for the CP-1 facts the figures bind to."""

    ruling: Path | None = None

    def __init__(self, recordings: Path, answers: tuple[str, ...], execution: Path) -> None:
        self.config_id = MODEL.config_id
        self._file = recordings / "o2.jsonl"
        self._answers = answers
        self._execution = execution
        self._narrative_read = ""

    def _plan(self, step_id: str, reads: list[str]) -> list[tuple[str, dict[str, Any]]]:
        """The tool calls of this request, from the step and what its read_inputs returned."""
        submit = f"submit_{step_id}"
        if step_id in READ_FIRST and not reads:
            return [("read_inputs", {})]
        if step_id == "source_context":
            searches = [("search_pack", {"query": q, "source_id": i}) for i, q in SEARCHES]
            return [*searches, (submit, load_arguments(payload_for(step_id)))]
        if step_id == "financials":
            frozen = frozen_financials()
            calls = [(item["tool"], dict(item["arguments"])) for item in frozen["tool_calls"]]
            return [*calls, (submit, dict(frozen["submission"]))]
        if step_id == "narrative":
            self._narrative_read = reads[0]
            return [(submit, load_arguments(json.dumps(fw.narrative({"body": reads[0]}))))]
        if step_id == "readiness":
            return [(submit, {"consumers": []})]
        if step_id == "quality":
            review = s1._credit_quality_review({"body": self._narrative_read}, json.loads(reads[0]))
            return [(submit, load_arguments(review))]
        if step_id == "business_context":
            source_id, query = BUSINESS_SEARCH
            search = ("search_pack", {"query": query, "source_id": source_id})
            return [search, (submit, load_arguments(payload_for(step_id)))]
        # credit_synthesis carries {{FIG:name}}; relative_value is frozen with the same markers
        text = json.dumps(frozen_submissions()["positive"][_SECTION[step_id]])
        if step_id in ("credit_synthesis", "relative_value"):
            bound = _figure_bindings(Execution(self._execution), text)
            if step_id == "credit_synthesis":  # cross-checked against the step's own read body
                cp2 = {e["ref"]: e for e in json.loads(reads[0])["cp1_facts"]}
                for name, (fact_id, unit) in bound.items():
                    entry = cp2.get(fact_id)
                    if entry is None or entry["unit"] != unit:
                        raise RuntimeError(f"FIG {name}: {fact_id} is not offered with {unit}")
            text = s1.bind_figures(text, bound)
        return [(submit, load_arguments(text))]

    def complete(
        self, request: TurnRequest, *, invocation_digest: str, call_index: int, reservation_id: str
    ) -> AdapterReply:
        names = [tool.name for tool in request.tools]
        # financials also offers submit_financials_part, listed before the step's own submit tool
        step_id = [n for n in names if n.startswith("submit_")][-1].removeprefix("submit_")
        if step_id not in self._answers:
            raise RecordingMissing(invocation_digest, call_index)
        reads = [m.text for m in request.messages if m.role == "tool"]
        calls = [
            ToolCall(f"call-{invocation_digest[:12]}-{call_index}-{n}", name, arguments)
            for n, (name, arguments) in enumerate(self._plan(step_id, reads))
        ]
        turn = Turn(
            "", tuple(calls), USAGE, "tool_use", MODEL.model, f"o2-{invocation_digest[:12]}", 200
        )
        line = {
            "invocation_digest": invocation_digest,
            "call_index": call_index,
            "response": turn_to_json(turn),
        }
        with self._file.open("a", encoding="utf-8") as handle:
            handle.write(dump_json(line) + "\n")
        return AdapterReply("ok", turn, None, 200, None, None, STARTED, FINISHED, USAGE, None)


@dataclass(frozen=True)
class Authored:
    outcome: RunOutcome
    run_dir: Path
    recordings: Path


def stage(root: Path) -> tuple[Any, Path]:
    """Check and stage the case under ``root`` with an empty recorded adapter; no model is called."""
    empty = root / "check-recordings"
    empty.mkdir(parents=True)
    return _prepare(root, recorded_adapter(MODEL, empty))


def _prepare(root: Path, adapter: ModelAdapter) -> tuple[Any, Path]:
    run_dir = root / "run"
    root.mkdir(parents=True, exist_ok=True)
    checked = check_arguments(
        case_id=CASE_ID,
        sources=case_sources(),
        context=CASE / "context.json",
        pathway=PATHWAY,
        model=MODEL,
        adapter=adapter,
        cap_usd=CAP,
        run_dir=run_dir,
        run_id=RUN_ID,
    )
    stage_sources(checked, run_dir)
    return checked, run_dir


@contextlib.contextmanager
def loop_bound(bytes_per_token: Decimal | None) -> Iterator[None]:
    """Run with ``run_pathway``'s ToolLoop given ``bytes_per_token`` (None: its own default)."""
    if bytes_per_token is None:
        yield
        return
    with mock.patch.object(
        run_pathway_module, "ToolLoop", partial(ToolLoop, bytes_per_token=bytes_per_token)
    ):
        yield


def author(
    root: Path, *, answers: tuple[str, ...], bytes_per_token: Decimal | None = None
) -> Authored:
    """Drive the walk with ``ScriptAdapter`` over a fresh run directory under ``root``."""
    recordings = root / "recordings"
    recordings.mkdir(parents=True)
    empty = root / "check-recordings"
    empty.mkdir()
    checked, run_dir = _prepare(root, recorded_adapter(MODEL, empty))
    script = ScriptAdapter(recordings, answers, run_dir / "execution")
    with loop_bound(bytes_per_token):
        outcome = _run_pathway(checked, run_dir, script, test_prompt_for)
    return Authored(outcome, run_dir, recordings)


def replay(root: Path, recordings: Path, *, bytes_per_token: Decimal | None = None) -> RunOutcome:
    """A second run over a fresh run directory, same ``run_id``, a plain ``recorded_adapter``."""
    adapter = recorded_adapter(MODEL, recordings)
    checked, run_dir = _prepare(root, adapter)
    with loop_bound(bytes_per_token):
        return _run_pathway(checked, run_dir, adapter, test_prompt_for)
