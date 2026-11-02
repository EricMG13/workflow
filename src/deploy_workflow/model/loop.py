"""The tool loop: drives one ``OwnerWorkflow`` with one provider request at a time (money, ordering).

Per provider request the order is: redact the outgoing request, reserve, send (``adapter.complete``,
one request), retain the raw body, redact the returned turn, validate by the workflow (tool calls,
``submit_review``), settle, append the record. Nothing unredacted is sent, and no tool call reaches
the Execution audit before the turn is redacted. The request is redacted before the reservation
only because the reservation is sized from the bytes that are sent; redaction has no side effect.

Failures split by what the charge is: ``not_sent`` releases the reservation; ``sent_known`` settles
0; ``sent_usage`` settles from the usage it reports and stops the run; ``sent_unknown``, and any
exception out of ``complete``, keep the reservation held and counted. A 5xx or a cut stream with no
usage gets the run's one retry (a new reservation naming the held one); an in-flight 402 is waited
out once. Every other failure, and any failed retry, stops the run right after its record is
written. A stop is ``StepStopped``, raised from redacted text with no chained exception.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from decimal import Decimal
from fractions import Fraction
from functools import partial
from typing import Any, Literal
from uuid import uuid4

from deploy_vii.execution import Attempt, Execution, ExecutionSnapshot
from deploy_vii.live.prompts import build
from deploy_vii.live.tools import submit_name, tool_specs
from deploy_vii.preparation import PreparedPack
from deploy_workflow.financial_workflow import MAX_CALLS, MAX_INVOKES
from deploy_workflow.model.adapter import AdapterReply, ModelAdapter
from deploy_workflow.model.budget import Budget, BudgetError, OverrunStop
from deploy_workflow.model.pricing import (
    CostStatus,
    PricingError,
    price_of,
    price_usage,
    reservation_usd,
)
from deploy_workflow.model.providers import RETRY_AFTER_DEFAULT_S, RETRY_AFTER_MAX_S
from deploy_workflow.model.record import (
    ADAPTER_ERROR,
    CallLog,
    CallRecord,
    arguments_sha256,
    invocation_preimage,
    retain_preimage,
)
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.turn import (
    Message,
    ModelSpec,
    ProviderBlock,
    ToolCall,
    ToolSpec,
    Turn,
    TurnRequest,
    Usage,
    dump_json,
)
from deploy_workflow.owner_workflow import OwnerBinding, OwnerWorkflow, StepSpec
from deploy_workflow.workflow import WorkflowError

READ_INPUTS = "read_inputs"
_RETRY_CLASSES = ("StreamCut", "IdleTimeout")
TOKEN_OVERHEAD = 64  # chat-template tokens beyond the request body (DEPLOY VII runner.py:74)
PromptFor = Callable[[OwnerBinding, StepSpec, tuple[str, ...]], tuple[Message, ...]]
ToolsFor = Callable[[OwnerBinding, StepSpec], tuple[ToolSpec, ...]]


class StepStopped(Exception):
    """The run stopped. ``reason`` is the stop's cause name: the error class of the call, or, for
    an adapter exception, the exception type (for example ``RecordingMissing``), which may differ
    from the record's ``error_class`` (``AdapterError``). ``detail`` is redacted text. Raised
    ``from None``: no raw exception is chained to it."""

    def __init__(self, reason: str, detail: str = "", *, cause: Exception | None = None) -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail
        self.cause = (
            cause  # the workflow failure the loop stopped on; never chained (``from None``)
        )


def recorded_stop(records: Sequence[Mapping[str, Any]]) -> str | None:
    """The stop a killed run had already decided, from its last durable record (R16): the record
    form of the loop's stops (``_after_reply``, ``_outcome_of``, ``_validate``), which all write
    their class and detail into the call's own record before the loop raises. Not a stop: no error,
    a first 402 (the loop waits it out and resends), and a retryable unknown charge, whose stop is
    the budget's (``Budget.stop_reason``). The text is the one ``StepStopped`` carries."""
    if not records:
        return None
    last = records[-1]
    error_class = last["error_class"]
    if error_class is None or last["cost_status"] == "unknown":
        return None
    twice_402 = (
        len(records) > 1
        and records[-2]["http_status"] == 402
        and records[-2]["invocation_digest"] == last["invocation_digest"]
    )
    if last["http_status"] == 402 and not twice_402:
        return None
    detail = last["error"] or ""
    return f"{error_class}: {detail}" if detail else str(error_class)


# ---------------------------------------------------------------- repair scoping (runner port)


@dataclass(frozen=True)
class RepairPrompt:
    """What a repair prompt carries (DEPLOY VII ``live/runner.py`` ``RepairPrompt``)."""

    issues: tuple[str, ...]
    scope: Literal["failing-step", "none", "module"]
    failing_step: str | None

    def to_record(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "failing_step": self.failing_step,
            "issue_count": len(self.issues),
        }


def repair_prompt(snapshot: ExecutionSnapshot, attempt: Attempt, step_id: str) -> RepairPrompt:
    """The failing step's validator issues, on that step's prompt only.

    Within an attempt first: a step whose first try this attempt rejected gets that try's issues
    (``Attempt.step_repairs``). Otherwise, on a repair ticket, the previous attempt's last invalid
    step is the failing step: its issues go to the same step, the other steps get none. When no
    step failed validation (an interruption) the module issues are carried on every step."""
    own = next((item for item in attempt.step_repairs if item.step_id == step_id), None)
    if own is not None:
        return RepairPrompt(own.issues, "failing-step", step_id)
    if attempt.repair_of is None:
        return RepairPrompt((), "none", None)
    previous = next(item for item in snapshot.attempts if item.ticket_id == attempt.repair_of)
    failed = next((item for item in reversed(previous.steps) if item.status == "invalid"), None)
    if failed is None:
        return RepairPrompt(attempt.repair_issues, "module", None)
    if failed.step_id != step_id:
        return RepairPrompt((), "none", failed.step_id)
    return RepairPrompt(failed.issues, "failing-step", failed.step_id)


# ---------------------------------------------------------------- redaction of what crosses


def redacted_request(redactor: Redactor, request: TurnRequest) -> TurnRequest:
    """The request with every string, tool argument and schema redacted."""

    def call(item: ToolCall) -> ToolCall:
        return ToolCall(
            redactor.text(item.call_id),
            redactor.text(item.name),
            redactor.json_value(item.arguments),
        )

    def message(item: Message) -> Message:
        return Message(
            item.role,
            redactor.text(item.text),
            tuple(call(c) for c in item.tool_calls),
            None if item.tool_call_id is None else redactor.text(item.tool_call_id),
            tuple(
                ProviderBlock(redactor.text(b.provider), redactor.json_value(b.data))
                for b in item.provider_blocks
            ),
        )

    return TurnRequest(
        tuple(message(m) for m in request.messages),
        tuple(
            ToolSpec(
                redactor.text(t.name),
                redactor.text(t.description),
                redactor.json_value(t.parameters),
            )
            for t in request.tools
        ),
        request.max_output_tokens,
        request.effort,
    )


def redacted_turn(redactor: Redactor, turn: Turn) -> Turn:
    """The returned turn with every string and tool argument redacted, before any tool runs."""
    if any(not c.call_id for c in turn.tool_calls):
        raise ValueError("a tool call has an empty call id")
    return replace(
        turn,
        text=redactor.text(turn.text),
        tool_calls=tuple(
            ToolCall(
                redactor.text(c.call_id), redactor.text(c.name), redactor.json_value(c.arguments)
            )
            for c in turn.tool_calls
        ),
        reported_model=None if turn.reported_model is None else redactor.text(turn.reported_model),
        request_id=None if turn.request_id is None else redactor.text(turn.request_id),
        provider_blocks=tuple(
            ProviderBlock(redactor.text(b.provider), redactor.json_value(b.data))
            for b in turn.provider_blocks
        ),
    )


def _request_bytes(request: TurnRequest) -> int:
    """Bytes of the request as sent: an upper bound on its input tokens (a token is a byte or more)."""
    body = {
        "messages": [
            {
                "role": m.role,
                "text": m.text,
                "tool_calls": [
                    {"id": c.call_id, "name": c.name, "arguments": c.arguments}
                    for c in m.tool_calls
                ],
                "tool_call_id": m.tool_call_id,
                "provider_blocks": [
                    {"provider": b.provider, "data": b.data} for b in m.provider_blocks
                ],
            }
            for m in request.messages
        ],
        "tools": [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in request.tools
        ],
    }
    return len(dump_json(body).encode())


# ---------------------------------------------------------------- default prompt and tools


def read_inputs_tool() -> ToolSpec:
    return ToolSpec(
        READ_INPUTS,
        "The step's inputs as Python prepared them. Read them before you submit.",
        {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    )


def contract_prompt_for(pack: PreparedPack) -> PromptFor:
    """Opening messages from ``live.prompts.build`` for a step that has a ``STEP_CONTRACTS`` entry;
    any other step raises ``PromptError`` (the caller supplies its own ``prompt_for``)."""

    def prompt_for(
        binding: OwnerBinding, spec: StepSpec, issues: tuple[str, ...]
    ) -> tuple[Message, ...]:
        built = build(
            binding.step_id,
            pack,
            (),
            spec.schema,
            repair_issues=issues,
            submit_tool=submit_name(binding.step_id),
        )
        return tuple(Message("system" if m.role == "system" else "user", m.content) for m in built)

    return prompt_for


def contract_tools_for(binding: OwnerBinding, spec: StepSpec) -> tuple[ToolSpec, ...]:
    """The step's tools from ``live.tools.tool_specs``."""
    return tuple(
        ToolSpec(f["function"]["name"], f["function"]["description"], f["function"]["parameters"])
        for f in tool_specs(binding.step_id)
    )


# ---------------------------------------------------------------- the loop


@dataclass(frozen=True)
class _Ctx:
    binding: OwnerBinding
    digest: str


@dataclass
class _Validated:
    """What validating one turn by the workflow produced."""

    messages: list[Message] = field(default_factory=list)
    records: list[dict[str, Any]] = field(default_factory=list)
    outcome: dict[str, Any] | None = None
    submit_sha256: str | None = None
    stop: tuple[str, str] | None = None  # (error class, redacted detail)
    cause: Exception | None = None  # the workflow failure behind ``stop``, when it was one


@dataclass
class _Attempt:
    """One provider request, finished: its record is written."""

    turn: Turn | None = None
    validated: _Validated | None = None
    stop: tuple[str, str] | None = None
    cause: Exception | None = None
    again: Literal["402", "retry"] | None = None
    held: str | None = None  # the call id kept held by an unknown charge
    wait: int = 0
    error_class: str | None = None


def _dt(seconds: float | None) -> datetime | None:
    return None if seconds is None else datetime.fromtimestamp(seconds, UTC)


class ToolLoop:
    """One loop per run. Its digests, retry flag and call counts live in memory, so a restarted
    run builds a new ToolLoop; ``resumed=True`` seeds the active step's counts and invocation
    digest from the workflow's retained state and ``calls.jsonl`` (O3 Task 3b). The retry flag is
    not seeded: the budget refuses a second retry from its markers (``RetryUsed``)."""

    def __init__(
        self,
        workflow: OwnerWorkflow,
        adapter: ModelAdapter,
        budget: Budget,
        log: CallLog,
        prompt_for: PromptFor,
        tools_for: ToolsFor,
        redactor: Redactor,
        clock: Callable[[], float],
        sleep: Callable[[float], None],
        *,
        execution: Execution,
        spec: ModelSpec,
        case_id: str,
        pathway: str,
        max_output_tokens: int,
        bytes_per_token: Decimal = Decimal(1),
        resumed: bool = False,
    ) -> None:
        if adapter.config_id != spec.config_id:
            raise ValueError("the adapter and the model spec name different configurations")
        self._workflow, self._adapter, self._budget, self._log = workflow, adapter, budget, log
        self._prompt_for, self._tools_for = prompt_for, tools_for
        self._redactor, self._clock, self._sleep = redactor, clock, sleep
        self._execution, self._spec = execution, spec
        self._case_id, self._pathway, self._max_output = case_id, pathway, max_output_tokens
        if not bytes_per_token.is_finite() or bytes_per_token <= 0:
            raise ValueError("bytes_per_token must be a positive finite amount")
        self._bytes_per_token = bytes_per_token
        self._digests: dict[tuple[str, str], str] = {}
        self._counts: Counter[tuple[str, str, str]] = Counter()
        self._retry_used = False
        self._first_issues: tuple[str, ...] = ()
        self._wait_402_first = False  # a resumed step whose last record is its first 402
        self._seed(resumed)

    def _seed(self, resumed: bool) -> None:
        """Take over a run another process began. One ``state()`` read, here and nowhere else in
        the loop: the active step's used counts (so the caps still bind) and, from
        ``calls.jsonl``, the invocation digest its earlier calls were sent under (so a resumed
        step keeps its digest and ``call_index`` continues from the file). The issues of a
        resubmission ``open()`` made go into the first prompt of the step it re-activated."""
        if not resumed:
            return
        state = self._workflow.state()
        if state.step_id is None:  # the walk is at a stop: no step to take over
            return
        binding = self._workflow.binding
        key = (binding.ticket_id, binding.step_id)
        for kind, used in (
            ("invoke", state.invokes_used),
            (READ_INPUTS, state.reads_used),
            ("submit_review", state.submits_used),
        ):
            self._counts[(*key, kind)] = used
        digests = {
            r["invocation_digest"]
            for r in self._log.records()
            if (r["module_id"], r["step_id"], r["attempt"])
            == (binding.module_id, binding.step_id, binding.attempt)
        }
        if len(digests) > 1:
            raise ValueError("calls.jsonl holds more than one invocation digest for the step")
        if digests:
            self._digests[key] = digests.pop()
        self._wait_402_first = self._last_was_first_402(binding)
        resubmitted = self._workflow.resumed_submission
        if resubmitted is not None and resubmitted["status"] == "invalid":
            self._first_issues = tuple(resubmitted["issues"])

    def _last_was_first_402(self, binding: OwnerBinding) -> bool:
        """The step's last record is a 402 (``recorded_stop`` already stopped a second one): the
        killed process was in the Retry-After wait, so this request counts as resent once (L8)."""
        mine = [
            r
            for r in self._log.records()
            if (r["module_id"], r["step_id"], r["attempt"])
            == (binding.module_id, binding.step_id, binding.attempt)
        ]
        return bool(mine) and mine[-1]["http_status"] == 402

    # -- the run ---------------------------------------------------------------------

    def run(self) -> tuple[dict[str, Any], ...]:
        """Drive the workflow until its walk ends; return each step's submit outcome. A stop
        raises ``StepStopped``."""
        outcomes: list[dict[str, Any]] = []
        while True:
            outcome = self.run_step()
            outcomes.append(outcome)
            if outcome["next_step"] is None:
                return tuple(outcomes)

    def run_step(self) -> dict[str, Any]:
        """Drive the workflow's active step to a submit the workflow did not refuse and return its
        outcome (``next_step`` is None when the walk has left the analytical phase). The public
        one-step driver: a caller that interleaves other work between steps (a rerun's replay of
        retained modules) calls this where ``run`` would drive to the walk's end. A stop raises
        ``StepStopped``."""
        return self._step()

    def _step(self) -> dict[str, Any]:
        """One conversation: the opening prompt for the current step, then requests until a
        submit the workflow did not refuse."""
        binding, spec = self._workflow.binding, self._workflow.spec
        snapshot = self._execution.read()
        attempt = next(a for a in snapshot.attempts if a.ticket_id == binding.ticket_id)
        issues = self._issues(snapshot, attempt, binding.step_id)
        opening = self._prompt_for(binding, spec, issues)
        tools = self._tools_for(binding, spec)
        if spec.inputs != "none" and all(t.name != READ_INPUTS for t in tools):
            tools = (*tools, read_inputs_tool())
        ctx = _Ctx(binding, self._digest(binding, opening))
        history = list(opening)
        while True:
            request = TurnRequest(tuple(history), tools, self._max_output, self._spec.effort)
            done = self._request(ctx, request)
            assert done.turn is not None and done.validated is not None
            history.append(
                Message(
                    "assistant", done.turn.text, done.turn.tool_calls,
                    provider_blocks=done.turn.provider_blocks,
                )
            )  # fmt: skip
            history.extend(done.validated.messages)
            outcome = done.validated.outcome
            if outcome is not None and outcome["status"] != "refused":
                return outcome

    def _issues(
        self, snapshot: ExecutionSnapshot, attempt: Attempt, step_id: str
    ) -> tuple[str, ...]:
        """The issues for the step's opening prompt: the journal's repair issues, or on a resumed
        run's first step those of the resubmission ``open()`` made (I3), once."""
        issues, self._first_issues = self._first_issues, ()
        return issues or repair_prompt(snapshot, attempt, step_id).issues

    def _digest(self, binding: OwnerBinding, opening: tuple[Message, ...]) -> str:
        """The invocation digest of (step, attempt): computed and retained once, from the first
        opening prompt; a repair within the attempt keeps it, a new attempt has its own."""
        key = (binding.ticket_id, binding.step_id)
        if key not in self._digests:
            prompt = dump_json([{"role": m.role, "text": m.text} for m in opening])
            self._digests[key] = retain_preimage(
                self._execution,
                invocation_preimage(
                    run_id=binding.run_id,
                    module_id=binding.module_id,
                    step_id=binding.step_id,
                    attempt=binding.attempt,
                    upstream_hashes=[i.sha256 for i in binding.inputs],
                    prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
                ),
            )
        return self._digests[key]

    # -- one logical request: the 402 wait and the one retry ---------------------------

    def _wait_out_killed_402(self) -> bool:
        """True once a resumed step whose last record is a first 402 has waited: that request is
        then resent once already, so a second 402 stops. The record keeps no Retry-After; the
        wait is the default."""
        if not self._wait_402_first:
            return False
        self._wait_402_first = False
        self._sleep(RETRY_AFTER_DEFAULT_S)
        return True

    def _request(self, ctx: _Ctx, request: TurnRequest) -> _Attempt:
        outgoing = redacted_request(self._redactor, request)
        resent_402 = self._wait_out_killed_402()
        retry_of: str | None = None
        while True:
            done = self._attempt(ctx, outgoing, retry_of)
            if retry_of is not None and done.stop is None and done.turn is None:
                done.stop = (done.error_class or "RetryFailed", "the retry failed")  # Q8
            if done.stop is None and done.again == "402":
                if resent_402:
                    done.stop = ("CreditExhausted", "the provider refused for credit twice")
                else:
                    resent_402 = True
                    self._sleep(done.wait)
                    continue
            if done.stop is None and done.again == "retry":
                retry_of, self._retry_used = done.held, True
                continue
            if done.stop is not None:
                raise StepStopped(
                    self._redactor.text(done.stop[0]), done.stop[1], cause=done.cause
                ) from None
            return done

    # -- one provider request ----------------------------------------------------------

    def _attempt(self, ctx: _Ctx, request: TurnRequest, retry_of: str | None) -> _Attempt:
        binding = ctx.binding
        index = self._log.next_call_index(binding.module_id, binding.step_id, binding.attempt)
        call_id = f"call-{uuid4().hex}"
        config = self._spec.config_id
        started = self._clock()
        try:
            reserved = reservation_usd(
                price_of(config), self._token_bound(request), self._max_output
            )
            self._budget.reserve(call_id, reserved, retry_of=retry_of, config_id=config)
        except (BudgetError, PricingError) as error:
            return self._refused(ctx, index, started, type(error).__name__, str(error))
        reply, failure = _caught(
            lambda: self._adapter.complete(
                request, invocation_digest=ctx.digest, call_index=index, reservation_id=call_id
            )
        )
        if reply is None or failure is not None:
            # An exception out of complete may follow a send: the charge is unknown, so the hold
            # is kept and counted, never released; the run stops once the record is written. The
            # record's class is the fixed AdapterError; the exception type is in the error text.
            name = type(failure).__name__
            self._budget.settle(call_id, None)
            self._append(
                ctx, index, started, None, None, reserved, None, "unknown",
                error_class=ADAPTER_ERROR,
                error=self._redactor.exception(failure or RuntimeError(name)),
            )  # fmt: skip
            return _Attempt(stop=(name, self._redactor.text(str(failure))))
        return self._after_reply(ctx, index, call_id, started, reserved, reply, retry_of)

    def _token_bound(self, request: TurnRequest) -> int:
        """Upper bound on the request's input tokens: ceil(bytes / a lower bound on bytes per
        token) plus the template overhead. The default bound of 1 is always sound (a token is at
        least a byte) and, for a long prompt, far above the truth; pass a measured lower bound
        to reserve closer to the cost. Exact rational arithmetic, as DEPLOY VII's reservation."""
        size = Fraction(_request_bytes(request)) / Fraction(self._bytes_per_token)
        return math.ceil(size) + TOKEN_OVERHEAD

    def _refused(
        self, ctx: _Ctx, index: int, started: float, error_class: str, error: str
    ) -> _Attempt:
        record = CallRecord.refused(
            self._redactor,
            error_class=error_class,
            error=error,
            **self._identity(ctx, index),
            started_at=_dt(started),
        )
        self._log.append(record)
        return _Attempt(stop=(error_class, self._redactor.text(error)))

    def _identity(self, ctx: _Ctx, index: int) -> dict[str, Any]:
        b = ctx.binding
        return {
            "run_id": b.run_id,
            "case_id": self._case_id,
            "pathway": self._pathway,
            "module_id": b.module_id,
            "step_id": b.step_id,
            "attempt": b.attempt,
            "call_index": index,
            "config_id": self._spec.config_id,
            "provider": self._spec.provider,
            "requested_model": self._spec.model,
            "requested_effort": self._spec.effort,
            "invocation_digest": ctx.digest,
        }

    def _append(
        self,
        ctx: _Ctx,
        index: int,
        started: float,
        reply: AdapterReply | None,
        usage: Usage | None,
        reserved: Decimal,
        settled: Decimal | None,
        status: CostStatus,
        *,
        turn: Turn | None = None,
        validated: _Validated | None = None,
        error_class: str | None = None,
        error: str | None = None,
    ) -> None:
        shown = turn if turn is not None else (None if reply is None else reply.turn)
        values: dict[str, Any] = {
            **self._identity(ctx, index),
            "schema_version": "model-call/1",
            "reported_model": None if shown is None else shown.reported_model,
            "request_id": None if shown is None else shown.request_id,
            "http_status": None if reply is None else reply.http_status,
            "started_at": _dt(
                started if reply is None or reply.started_at is None else reply.started_at
            ),
            "first_byte_at": None if reply is None else _dt(reply.first_byte_at),
            "finished_at": _dt(
                self._clock() if reply is None or reply.finished_at is None else reply.finished_at
            ),
            "input_tokens": None if usage is None else usage.input_tokens,
            "cached_read_tokens": None if usage is None else usage.cached_read_tokens,
            "cache_write_tokens": None if usage is None else usage.cache_write_tokens,
            "output_tokens": None if usage is None else usage.output_tokens,
            "reasoning_tokens": None if usage is None else usage.reasoning_tokens,
            "reserved_usd": reserved,
            "settled_usd": settled,
            "cost_status": status,
            "tool_calls": [] if validated is None else validated.records,
            "submit_sha256": None if validated is None else validated.submit_sha256,
            "error_class": error_class,
            "error": error,
        }
        self._log.append(CallRecord.build(self._redactor, **values))

    def _after_reply(
        self,
        ctx: _Ctx,
        index: int,
        call_id: str,
        started: float,
        reserved: Decimal,
        reply: AdapterReply,
        retry_of: str | None,
    ) -> _Attempt:
        if reply.kind == "not_sent":
            self._budget.release(call_id)  # nothing reached the provider: the hold is freed
            self._refuse_record(ctx, index, started, reply)
            return _Attempt(
                stop=(reply.error_class or "NotSent", self._redactor.text(reply.message or ""))
            )
        error_class, message = reply.error_class, reply.message
        stop: tuple[str, str] | None = None
        cause: Exception | None = None
        raw_failure = self._retain_raw(ctx, index, reply)
        turn: Turn | None = None
        validated: _Validated | None = None
        failure = raw_failure
        if reply.kind == "ok" and reply.turn is not None and raw_failure is None:
            handled, failure = _caught(partial(self._handle, reply.turn))
            if handled is not None:
                turn, validated = handled
                stop, cause = validated.stop, validated.cause
        usage = reply.usage if reply.usage is not None or reply.turn is None else reply.turn.usage
        settled, status, retryable, overrun = self._settle(call_id, reply, usage)
        if failure is not None:  # the raw write or the handling itself failed: settled, recorded
            # After an ok reply this is a loop stop (record.LOOP_STOPS) so the run still exports.
            error_class = (
                "BadTurn" if reply.kind == "ok" else (reply.error_class or type(failure).__name__)
            )  # a non-ok reply keeps the provider's class; the failure's type stays in ``message``
            message = self._redactor.exception(failure)
            stop = (error_class, self._named(failure))
        elif stop is not None:
            error_class, message = stop
        self._append(
            ctx, index, started, reply, usage, reserved, settled, status,
            turn=turn, validated=validated, error_class=error_class, error=message,
        )  # fmt: skip
        done = _Attempt(turn=turn, validated=validated, held=call_id, error_class=error_class)
        if stop is None:
            stop = self._outcome_of(reply, done, retry_of, retryable, settled, overrun)
        done.stop, done.cause = stop, cause
        return done

    def _handle(self, returned: Turn) -> tuple[Turn, _Validated]:
        """Redact the returned turn, then validate it by the workflow (never the other way)."""
        turn = redacted_turn(self._redactor, returned)
        return turn, self._validate(turn)

    def _retain_raw(self, ctx: _Ctx, index: int, reply: AdapterReply) -> Exception | None:
        """Archive the redacted raw body before anything validates the reply. A failed write is
        returned, not raised: the call is still settled and recorded, then the run stops."""
        if reply.raw is None:  # a recorded adapter holds no provider body
            return None
        _, failure = _caught(
            lambda: self._log.write_raw(
                ctx.digest, index, reply.raw or b"", error_class=reply.error_class
            )
        )
        return failure

    def _settle(
        self, call_id: str, reply: AdapterReply, usage: Usage | None
    ) -> tuple[Decimal | None, CostStatus, bool, bool]:
        """Settle the hold with the charge of what was sent: (settled, cost status, retryable,
        overrun). A charge that cannot be known keeps the whole hold."""
        retryable = False
        settled: Decimal | None
        status: CostStatus
        if reply.kind == "sent_known":
            settled, status = Decimal(0), "computed"
        elif reply.kind == "sent_unknown":
            settled, status, retryable = None, "unknown", _retryable(reply)
        else:
            assert usage is not None
            priced = price_usage(
                self._spec.config_id, usage, reply.billed_usd, offline=self._adapter.ruling is None
            )
            settled, status = priced.usd, priced.cost_status
        if settled is None:
            self._budget.settle(call_id, None, retryable=retryable)
            return None, "unknown", retryable, False
        try:
            self._budget.settle(call_id, settled)
        except OverrunStop:
            return settled, status, False, True  # recorded in full by the budget; the run stops
        return settled, status, False, False

    def _outcome_of(
        self,
        reply: AdapterReply,
        done: _Attempt,
        retry_of: str | None,
        retryable: bool,
        settled: Decimal | None,
        overrun: bool,
    ) -> tuple[str, str] | None:
        """The stop after a settled, recorded call, or None; ``done.again`` names a resend."""
        error_class = reply.error_class or reply.kind
        detail = self._redactor.text(reply.message or "")
        if reply.error_class == "KeyReflected":  # never resent, whatever the status (R9)
            return error_class, detail
        if reply.kind == "sent_usage":
            return error_class, detail
        if reply.kind == "sent_known":
            if reply.http_status == 402:
                wait = RETRY_AFTER_DEFAULT_S if reply.retry_after is None else reply.retry_after
                done.again, done.wait = "402", min(wait, RETRY_AFTER_MAX_S)
                return None
            return error_class, detail
        if reply.kind == "sent_unknown":
            if retryable and retry_of is None and not self._retry_used:
                done.again = "retry"
                return None
            return error_class, detail
        if settled is None:
            return "UnknownCharge", "the charge of a sent call is unknown"
        if overrun:
            return "OverrunStop", "the actual charge was above the reservation"
        return None

    def _refuse_record(self, ctx: _Ctx, index: int, started: float, reply: AdapterReply) -> None:
        record = CallRecord.refused(
            self._redactor,
            error_class=reply.error_class or "NotSent",
            error=reply.message or "",
            **self._identity(ctx, index),
            started_at=_dt(started if reply.started_at is None else reply.started_at),
            finished_at=_dt(reply.finished_at),
        )
        self._log.append(record)

    # -- validate by the workflow ------------------------------------------------------

    def _validate(self, turn: Turn) -> _Validated:
        out = _Validated()
        if not turn.tool_calls:
            out.stop = ("NoSubmit", "the reply carried neither a tool call nor a submit")
            return out
        stepped = False
        for call in turn.tool_calls:
            sha = arguments_sha256(call.arguments)
            record: dict[str, Any] = {
                "name": call.name,
                "arguments_sha256": sha,
                "result_bytes": None,
                "refusal_code": None,
            }
            out.records.append(record)
            if stepped:  # the step moved on: this call was addressed to the one before
                record["refusal_code"] = "not_executed"
                out.messages.append(self._tool_message(call, "refused: the step changed"))
                continue
            binding = self._workflow.binding
            kind = self._kind(call.name, binding)
            key = (binding.ticket_id, binding.step_id, kind)
            result, failure = _caught(partial(self._call, call, kind))
            returned = True
            if isinstance(failure, WorkflowError) and failure.code == "not_permitted":
                limit = MAX_INVOKES if kind == "invoke" else MAX_CALLS
                if self._counts[key] >= limit:  # one call past the kind's per-step limit
                    record["refusal_code"] = "CallLimit"
                    out.stop = ("CallLimit", f"more than {limit} {kind} calls in one step")
                    return out
                # any other not_permitted is a refusal the model sees (F14)
                refused = dump_json({"status": "refused", "error_code": "not_permitted"})
                if kind == "submit_review":  # the workflow counted this submit before refusing it
                    self._counts[key] += 1
                result, failure, returned = (refused, "not_permitted", None), None, False
            if failure is not None or result is None:
                # Whatever the workflow raised is one loop stop (record.LOOP_STOPS); the original
                # type name and the redacted message go in the detail.
                stop_class = _stop_class(failure)
                record["refusal_code"] = stop_class
                out.stop = (stop_class, self._named(failure))
                out.cause = failure
                return out
            content, refusal, outcome = result
            if returned:
                self._counts[key] += 1
            record["result_bytes"] = len(content.encode())
            record["refusal_code"] = refusal
            out.messages.append(self._tool_message(call, content))
            if kind == "submit_review":
                out.submit_sha256 = hashlib.sha256(dump_json(call.arguments).encode()).hexdigest()
                out.outcome = outcome
                stepped = outcome is not None and outcome["status"] != "refused"
        return out

    def _named(self, failure: BaseException | None) -> str:
        """The original exception type and its redacted message."""
        return f"{type(failure).__name__}: {self._redactor.text(str(failure))}"

    def _kind(self, name: str, binding: OwnerBinding) -> str:
        if name == READ_INPUTS:
            return "read_inputs"
        return "submit_review" if name == f"submit_{binding.step_id}" else "invoke"

    def _call(self, call: ToolCall, kind: str) -> tuple[str, str | None, dict[str, Any] | None]:
        """(content for the model, refusal code, submit outcome) of one dispatched call."""
        if kind == "read_inputs":
            read = self._workflow.read_inputs()
            return str(read["body"]), None, None
        if kind == "submit_review":
            result = self._workflow.submit_review(dump_json(call.arguments))
            code = result["refusal"] or ("refused" if result["status"] == "refused" else None)
            shown = {k: result[k] for k in ("status", "issues", "step_id", "next_step", "refusal")}
            return dump_json(shown), code, result
        received = self._workflow.invoke(call.name, call.arguments)
        if received["status"] == "ok":
            return str(received["body"] or ""), None, None
        shown = {"status": received["status"], "error_code": received["error_code"]}
        return dump_json(shown), received["error_code"], None

    @staticmethod
    def _tool_message(call: ToolCall, content: str) -> Message:
        return Message("tool", content, tool_call_id=call.call_id)


def _stop_class(failure: BaseException | None) -> str:
    """The loop stop (``record.LOOP_STOPS``) a failure of the workflow is: a ``read_inputs`` body
    over the byte cap (G6, P8) is named ``InputsTooLarge``; any other failure is ``WorkflowError``."""
    if isinstance(failure, WorkflowError) and failure.code == "inputs_too_large":
        return "InputsTooLarge"
    return "WorkflowError"


def _caught[T](action: Callable[[], T]) -> tuple[T | None, Exception | None]:
    """Run ``action``; return its value, or the exception it raised. The loop's one catch-all:
    a failure here is never dropped. The caller records its class and redacted text, settles the
    call, and stops the run (``StepStopped``), so nothing fails open."""
    try:
        return action(), None
    except Exception as error:  # noqa: BLE001 - returned to the caller, which records and stops
        return None, error


def _retryable(reply: AdapterReply) -> bool:
    """A 5xx, or a cut stream or idle timeout with no usage; a key-reflecting reply never (R9)."""
    if reply.error_class == "KeyReflected":
        return False
    if reply.http_status is not None and 500 <= reply.http_status <= 599:
        return True
    return reply.error_class in _RETRY_CLASSES and reply.usage is None


__all__ = [
    "READ_INPUTS",
    "RepairPrompt",
    "StepStopped",
    "ToolLoop",
    "contract_prompt_for",
    "contract_tools_for",
    "read_inputs_tool",
    "recorded_stop",
    "redacted_request",
    "redacted_turn",
    "repair_prompt",
]
