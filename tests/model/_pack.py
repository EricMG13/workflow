"""A real pack, a real ``OwnerWorkflow`` and a scripted adapter for the O5 loop tests. No network.

The pack and the step payloads come from ``tests/test_financial_workflow.py`` (``fw``); the
workflow is the real ``OwnerWorkflow``. The scripted adapter is a test double for the *provider*:
each request answers with the next reply the test wrote, and it records what it was sent.
"""

import importlib
import itertools
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from deploy_vii.execution import Execution
from deploy_vii.preparation import PreparedPack
from deploy_workflow.model.adapter import AdapterReply, ReplyKind
from deploy_workflow.model.budget import Budget
from deploy_workflow.model.loop import ToolLoop
from deploy_workflow.model.record import CallLog
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.turn import (
    Message,
    ModelSpec,
    ToolCall,
    ToolSpec,
    Turn,
    TurnRequest,
    Usage,
    load_arguments,
)
from deploy_workflow.owner_workflow import OwnerBinding, OwnerWorkflow, StepSpec

fw: Any = importlib.import_module("tests.test_financial_workflow")

SPEC = ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium")
SECRET = "sk-or-v1-TESTONLY123456"
USAGE = Usage(input_tokens=1000, output_tokens=200)
_ids = itertools.count(1)


def owner_start(root: Path, gap: bool = False) -> tuple[OwnerWorkflow, PreparedPack]:
    """``fw.start`` for the owner workflow (what ``tests/test_owner_workflow.py`` patches in)."""
    pack = fw.make_pack(gap)
    workflow = OwnerWorkflow.create(root / "store", pack, publication_directory=root / "model")
    return workflow, pack


# ---------------------------------------------------------------- replies the tests script


def tool_call(name: str, **arguments: Any) -> ToolCall:
    return ToolCall(f"call_{next(_ids)}", name, dict(arguments))


def read_identity() -> ToolCall:
    return tool_call("read_pages", source_id="identity", first_page=1, last_page=1)


def read_financial() -> ToolCall:
    return tool_call("read_pages", source_id="financial", first_page=1, last_page=1)


def submit(step_id: str, payload: str) -> ToolCall:
    return ToolCall(f"call_{next(_ids)}", f"submit_{step_id}", load_arguments(payload))


def gap_submit() -> ToolCall:
    """The valid CP-0 review of the gap pack (needs `read_identity()` in the same epoch)."""
    return submit("source_readiness", fw.readiness(fw.make_pack(True), gap=True))


def ready_submit() -> ToolCall:
    """The valid CP-0 review of the full pack (needs both pages read in the same epoch)."""
    return submit("source_readiness", fw.readiness(fw.make_pack(False)))


def ok(
    *calls: ToolCall,
    text: str = "",
    usage: Usage = USAGE,
    raw: bytes | None = None,
    started: float | None = 100.0,
    first_byte: float | None = 100.2,
    finished: float | None = 101.0,
    billed: Decimal | None = None,
) -> AdapterReply:
    turn = Turn(text, calls, usage, "tool_use", "gpt-6.1-sol", "req-1", 200, billed)
    body = b'{"id":"req-1"}' if raw is None else raw
    return AdapterReply("ok", turn, body, 200, None, first_byte, started, finished, usage, billed)


def failed(
    kind: ReplyKind,
    error_class: str,
    status: int | None,
    *,
    usage: Usage | None = None,
    retry_after: int | None = None,
    message: str = "the provider said no",
    raw: bytes | None = None,
) -> AdapterReply:
    return AdapterReply(
        kind, None, raw, status, error_class, None, 100.0, 101.0, usage, None, retry_after, message
    )


@dataclass
class Sent:
    request: TurnRequest
    digest: str
    call_index: int
    reservation_id: str


class ScriptedAdapter:
    """Answers each ``complete`` with the next scripted reply (or raises the next scripted
    exception); an exhausted script is a test error. ``tape`` records ``complete`` for ordering."""

    def __init__(
        self,
        script: list[AdapterReply | BaseException],
        *,
        config_id: str = SPEC.config_id,
        ruling: Path | None = None,
        tape: list[str] | None = None,
    ) -> None:
        self.config_id = config_id
        self.ruling = ruling
        self.sent: list[Sent] = []
        self._script = list(script)
        self._tape = tape

    def complete(
        self, request: TurnRequest, *, invocation_digest: str, call_index: int, reservation_id: str
    ) -> AdapterReply:
        if self._tape is not None:
            self._tape.append("complete")
        self.sent.append(Sent(request, invocation_digest, call_index, reservation_id))
        if not self._script:
            raise AssertionError("the adapter script is exhausted: an unexpected request")
        item = self._script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


# ---------------------------------------------------------------- prompts and tools


def prompt_for(
    binding: OwnerBinding, spec: StepSpec, issues: tuple[str, ...]
) -> tuple[Message, ...]:
    text = f"Step {binding.step_id}, attempt {binding.attempt}."
    if issues:
        text += "\nREPAIR: " + "; ".join(issues)
    return (Message("system", "You are one step of the workflow."), Message("user", text))


def tools_for(binding: OwnerBinding, spec: StepSpec) -> tuple[ToolSpec, ...]:
    empty: dict[str, Any] = {"type": "object", "properties": {}}
    return (
        ToolSpec("search_pack", "search", empty),
        ToolSpec("read_pages", "read", empty),
        ToolSpec(f"submit_{binding.step_id}", "submit", empty),
    )


# ---------------------------------------------------------------- the rig


class TapedWorkflow:
    """The real ``OwnerWorkflow`` behind recording shims; ``fail_submit`` makes submit raise."""

    def __init__(
        self, real: OwnerWorkflow, tape: list[str], fail_submit: BaseException | None = None
    ) -> None:
        self._real, self._tape, self._fail = real, tape, fail_submit

    @property
    def binding(self) -> OwnerBinding:
        return self._real.binding

    @property
    def spec(self) -> StepSpec:
        return self._real.spec

    def invoke(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self._tape.append("workflow.invoke")
        return self._real.invoke(name, arguments)

    def read_inputs(self) -> dict[str, Any]:
        self._tape.append("workflow.read_inputs")
        return self._real.read_inputs()

    def submit_review(self, payload: str) -> dict[str, Any]:
        self._tape.append("workflow.submit_review")
        if self._fail is not None:
            raise self._fail
        return self._real.submit_review(payload)


class TapedBudget:
    """The real ``Budget`` behind recording shims."""

    def __init__(self, real: Budget, tape: list[str]) -> None:
        self._real, self._tape = real, tape

    def reserve(self, *args: Any, **kwargs: Any) -> None:
        self._tape.append("reserve")
        self._real.reserve(*args, **kwargs)

    def settle(self, *args: Any, **kwargs: Any) -> None:
        self._tape.append("settle")
        self._real.settle(*args, **kwargs)

    def release(self, *args: Any, **kwargs: Any) -> None:
        self._tape.append("release")
        self._real.release(*args, **kwargs)


class TapedLog:
    """The real ``CallLog`` behind recording shims."""

    def __init__(self, real: CallLog, tape: list[str]) -> None:
        self._real, self._tape = real, tape

    def write_raw(self, *args: Any, **kwargs: Any) -> Path:
        self._tape.append("write_raw")
        return self._real.write_raw(*args, **kwargs)

    def append(self, record: Any) -> None:
        self._tape.append("append")
        self._real.append(record)

    def next_call_index(self, *args: Any) -> int:
        return self._real.next_call_index(*args)


@dataclass
class Rig:
    root: Path
    workflow: OwnerWorkflow
    pack: PreparedPack
    execution: Execution
    budget: Budget
    log: CallLog
    adapter: Any
    loop: ToolLoop
    tape: list[str]
    sleeps: list[float] = field(default_factory=list)

    @property
    def run_dir(self) -> Path:
        return self.root / "run"

    def records(self) -> list[dict[str, Any]]:
        return self.log.records()


def make_rig(
    root: Path,
    script: list[AdapterReply | BaseException],
    *,
    gap: bool = True,
    cap: str = "1",
    max_output: int = 4000,
    bytes_per_token: Decimal = Decimal(1),
    redactor: Redactor | None = None,
    adapter: Any = None,
    spec: ModelSpec = SPEC,
    fail_submit: BaseException | None = None,
    taped: bool = False,
    workflow: OwnerWorkflow | None = None,
    pack: PreparedPack | None = None,
    prompts: Callable[..., tuple[Message, ...]] = prompt_for,
    tools: Callable[..., tuple[ToolSpec, ...]] = tools_for,
) -> Rig:
    """A real pack and ``OwnerWorkflow`` (the gap pack stops after CP-0), the real budget and call
    log, and a scripted adapter. ``taped`` puts recording shims around every effect."""
    if workflow is None or pack is None:
        workflow, pack = owner_start(root, gap)
    execution = Execution(root / "store")
    tape: list[str] = []
    redactor = Redactor() if redactor is None else redactor
    real_budget = Budget(Decimal(cap), root / "store")
    real_log = CallLog(root / "run", redactor)
    scripted = (
        adapter
        if adapter is not None
        else ScriptedAdapter(script, config_id=spec.config_id, tape=tape if taped else None)
    )
    sleeps: list[float] = []
    loop = ToolLoop(
        TapedWorkflow(workflow, tape, fail_submit) if (taped or fail_submit) else workflow,  # type: ignore[arg-type]
        scripted,
        TapedBudget(real_budget, tape) if taped else real_budget,  # type: ignore[arg-type]
        TapedLog(real_log, tape) if taped else real_log,  # type: ignore[arg-type]
        prompts,
        tools,
        redactor,
        lambda: 100.0,
        sleeps.append,
        execution=execution,
        spec=spec,
        case_id="case-1",
        pathway="owner",
        max_output_tokens=max_output,
        bytes_per_token=bytes_per_token,
    )
    return Rig(root, workflow, pack, execution, real_budget, real_log, scripted, loop, tape, sleeps)
