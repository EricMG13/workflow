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

import hashlib
import importlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import s1a_runs as s1

from deploy_vii.contracts import PathwayId
from deploy_vii.execution import Execution
from deploy_vii.preparation import PreparedPack
from deploy_workflow.model.adapter import (
    AdapterReply,
    ModelAdapter,
    RecordingMissing,
    recorded_adapter,
)
from deploy_workflow.model.loop import PromptFor
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
# opus-medium (spec 7.1; effort medium is the only one its row allows) has no listed input limit in
# pricing.py, so run_pathway's own token bound applies unchanged. SOL_MODEL is the pinned limitation.
MODEL = ModelSpec("opus-medium", "anthropic", "claude-opus-5-5", "medium")
SOL_MODEL = ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium")
# Test-authored cap: the opus-medium reservations for the CP-1 requests (each sized from the request
# bytes at one byte per token) need it; offline spend is cap logic, not money (Q7).
CAP = Decimal(100)
# Test-authored counts, not measured: offline spend is cap logic, not money (Q7).
USAGE = Usage(input_tokens=1000, cached_read_tokens=0, cache_write_tokens=0, output_tokens=200)
STARTED, FINISHED = 1_000.0, 1_001.0
SOURCE_IDS = ("identity", "financial", "business", "market")
# Step id -> the key of the frozen payload under ``positive``. ``relative_value``,
# ``integrity_review`` and ``committee_challenge`` carry ``{{FIG:}}`` markers bound at run time.
# CP-1 financials has a frozen payload in ``cases/o2-synthetic/cp1-financials.json``.
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


_WHOLE_FIG = re.compile(r'"\{\{FIG:([a-z0-9_]+)\}\}"')


def bind_text(text: str, bound: dict[str, tuple[str, str]]) -> str:
    """Bind ``{{FIG:name}}``: a whole JSON string (an ``upstream_ref``) becomes the bare CP-2 fact
    id (cases/cp5-owner note: "a CP-2 fact_id"); a marker inside prose becomes ``{fact_id|unit}``
    as ``s1a_runs.bind_figures`` writes it. An unknown name stays and fails closed."""

    def whole(match: re.Match[str]) -> str:
        name = match[1]
        return match[0] if name not in bound else json.dumps(bound[name][0])

    return s1.bind_figures(_WHOLE_FIG.sub(whole, text), bound)


class ScriptAdapter:
    """Answers a request from the frozen payloads and records the answer. ``answers`` names the
    steps it will answer; a request for any other step raises ``RecordingMissing`` (nothing was
    recorded for it, as for a recorded adapter), which O5 records as ``AdapterError`` and stops
    the run on. It returns no raw body (a recording is the evidence). ``execution`` is the run's
    execution store, read for the CP-1 facts the figures bind to."""

    ruling: Path | None = None

    def __init__(
        self, recordings: Path, answers: tuple[str, ...], execution: Path, model: ModelSpec
    ) -> None:
        self.config_id = model.config_id
        self._model = model
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
        if "{{FIG:" in text:
            bound = _figure_bindings(Execution(self._execution), text)
            if step_id == "credit_synthesis":  # cross-checked against the step's own read body
                cp2 = {e["ref"]: e for e in json.loads(reads[0])["cp1_facts"]}
                figures = frozen_submissions()["figures"]
                for name, (fact_id, unit) in bound.items():
                    entry = cp2.get(fact_id)
                    if (
                        entry is None
                        or entry["unit"] != unit
                        or entry["shown"] != figures[name]["spelled"]
                    ):
                        raise RuntimeError(f"FIG {name}: {fact_id} is not offered with {unit}")
            text = bind_text(text, bound)
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
            "",
            tuple(calls),
            USAGE,
            "tool_use",
            self._model.model,
            f"o2-{invocation_digest[:12]}",
            200,
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


def _prepare(root: Path, adapter: ModelAdapter, model: ModelSpec = MODEL) -> tuple[Any, Path]:
    run_dir = root / "run"
    root.mkdir(parents=True, exist_ok=True)
    checked = check_arguments(
        case_id=CASE_ID,
        sources=case_sources(),
        context=CASE / "context.json",
        pathway=PATHWAY,
        model=model,
        adapter=adapter,
        cap_usd=CAP,
        run_dir=run_dir,
        run_id=RUN_ID,
    )
    stage_sources(checked, run_dir)
    return checked, run_dir


def author(root: Path, *, answers: tuple[str, ...], model: ModelSpec = MODEL) -> Authored:
    """Drive the walk with ``ScriptAdapter`` over a fresh run directory under ``root``."""
    recordings = root / "recordings"
    recordings.mkdir(parents=True)
    empty = root / "check-recordings"
    empty.mkdir()
    checked, run_dir = _prepare(root, recorded_adapter(model, empty), model)
    script = ScriptAdapter(recordings, answers, run_dir / "execution", model)
    outcome = _run_pathway(checked, run_dir, script, test_prompt_for)
    return Authored(outcome, run_dir, recordings)


def replay(root: Path, recordings: Path, *, model: ModelSpec = MODEL) -> RunOutcome:
    """A second run over a fresh run directory, same ``run_id``, a plain ``recorded_adapter``."""
    adapter = recorded_adapter(model, recordings)
    checked, run_dir = _prepare(root, adapter, model)
    return _run_pathway(checked, run_dir, adapter, test_prompt_for)
