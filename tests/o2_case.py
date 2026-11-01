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
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from deploy_vii.contracts import PathwayId
from deploy_vii.preparation import PreparedPack, load_pack
from deploy_workflow.financial_workflow import STATEMENT_HEADING
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
from deploy_workflow.owner_workflow import OwnerBinding, OwnerWorkflow, StepSpec
from deploy_workflow.run_inputs import CaseSource, RunOutcome, check_arguments, stage_sources
from deploy_workflow.run_pathway import _run_pathway

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "o2-synthetic"
CASE_ID = "o2-synthetic"
RUN_ID = "o2-synthetic-portfolio-decision"
PATHWAY: PathwayId = "portfolio_decision"
MODEL = ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium")
CAP = Decimal(5)
# Test-authored counts, not measured: offline spend is cap logic, not money (Q7).
USAGE = Usage(input_tokens=1000, output_tokens=200)
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
SEARCH_BEFORE = ("source_context",)
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


class ScriptAdapter:
    """Answers a request from the frozen payload and records the answer. ``answers`` names the
    steps it will answer; a request for any other step raises ``RecordingMissing`` (nothing was recorded for it, as
    for a recorded adapter), which O5 records as ``AdapterError`` and stops the run on. It returns no raw body (a recording is the evidence)."""

    ruling: Path | None = None

    def __init__(self, recordings: Path, answers: tuple[str, ...]) -> None:
        self.config_id = MODEL.config_id
        self._file = recordings / "o2.jsonl"
        self._answers = answers

    def complete(
        self, request: TurnRequest, *, invocation_digest: str, call_index: int, reservation_id: str
    ) -> AdapterReply:
        names = [tool.name for tool in request.tools]
        step_id = next(n for n in names if n.startswith("submit_")).removeprefix("submit_")
        if step_id not in self._answers:
            raise RecordingMissing(invocation_digest, call_index)
        read_first = "read_inputs" in names and all(m.role != "tool" for m in request.messages)
        name = "read_inputs" if read_first else f"submit_{step_id}"
        arguments = {} if read_first else load_arguments(payload_for(step_id))
        calls = [ToolCall(f"call-{invocation_digest[:12]}-{call_index}", name, arguments)]
        if step_id in SEARCH_BEFORE and not read_first and call_index == 0:
            # the frozen CP-1 context makes absence claims; the step needs the recorded searches
            searches = [
                ToolCall(
                    f"call-{invocation_digest[:12]}-{call_index}-s{n}",
                    "search_pack",
                    {"query": query, "source_id": source_id},
                )
                for n, (source_id, query) in enumerate(SEARCHES)
            ]
            calls = [*searches, *calls]
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


def author(root: Path, *, answers: tuple[str, ...]) -> Authored:
    """Drive the walk with ``ScriptAdapter`` over a fresh run directory under ``root``."""
    recordings = root / "recordings"
    recordings.mkdir(parents=True)
    empty = root / "check-recordings"
    empty.mkdir()
    checked, run_dir = _prepare(root, recorded_adapter(MODEL, empty))
    script = ScriptAdapter(recordings, answers)
    outcome = _run_pathway(checked, run_dir, script, test_prompt_for)
    return Authored(outcome, run_dir, recordings)


def replay(root: Path, recordings: Path) -> RunOutcome:
    """A second run over a fresh run directory, same ``run_id``, a plain ``recorded_adapter``."""
    adapter = recorded_adapter(MODEL, recordings)
    checked, run_dir = _prepare(root, adapter)
    return _run_pathway(checked, run_dir, adapter, test_prompt_for)


def blocker(root: Path) -> dict[str, Any]:
    """CP-1 ``financials`` on the prepared text pack: what ``extract_statements`` answers for a
    ``page:N`` locator, and the locators of the spans the step requires to be extracted."""
    empty = root / "check-recordings"
    empty.mkdir(parents=True)
    _, run_dir = _prepare(root, recorded_adapter(MODEL, empty))
    pack = load_pack(run_dir / "pack")
    workflow = OwnerWorkflow.create(
        run_dir / "execution", pack, publication_directory=run_dir / "publication"
    )
    if workflow.submit_review(payload_for("source_readiness"))["status"] != "valid":
        raise RuntimeError("the frozen CP-0 payload is not valid")
    for source_id, query in SEARCHES:
        workflow.invoke("search_pack", {"query": query, "source_id": source_id})
    context = workflow.submit_review(payload_for("source_context"))
    if context["status"] != "valid" or workflow.binding.step_id != "financials":
        raise RuntimeError("the frozen CP-1 source context did not reach financials")
    refused = workflow.invoke(
        "extract_statements", {"source_id": "financial", "locators": ["page:1"]}
    )
    heading = sorted(
        span.locator
        for source in pack.sources
        if source.source_id == "financial"
        for span in source.spans
        if STATEMENT_HEADING.search(span.text)
    )
    return {"extract_error": refused["error_code"], "heading_locators": heading}
