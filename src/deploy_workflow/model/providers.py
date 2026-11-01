"""OpenAI, Anthropic and OpenRouter mappers: one request in, one provider-neutral turn out.

``build`` makes exactly one request; ``parse`` reads one reply. Retry, resend and repair belong
to the loop. A reply that is not a usable turn comes back as a ``ProviderError`` carrying an
``ErrorKind``; an error that carries ``usage`` is settled from it (computed), otherwise by kind.
Provider facts: work/context-plan/provider-docs-2026-10-31.md and provider-docs-o5-controller.md.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, cast

from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.transport import (
    CONNECT_S,
    IDLE_S,
    OVERALL_S,
    ConnectTimeout,
    IdleTimeout,
    InsecureUrl,
    OverallTimeout,
    Request,
    TransportError,
)
from deploy_workflow.model.turn import (
    Message,
    ModelSpec,
    Provider,
    StopReason,
    ToolCall,
    Turn,
    TurnRequest,
    Usage,
)

OPENAI_URL = "https://api.openai.com/v1/responses"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
ANTHROPIC_VERSION = "2026-10-21"  # confirm before the first live call
OPENAI_STRICT_TOOLS = False  # not specified by the brief; schemas are not constrained to strict
MAX_OUTPUT_TOKENS = 131072  # spec §8 "up to 128k"; global cap (per-model limits not supplied)
OPENROUTER_IGNORE_FOR_DEEPSEEK = ["open-inference"]  # spec §8
MESSAGE_CHARS = 500
RETRY_AFTER_DEFAULT_S = 120
RETRY_AFTER_MAX_S = 300  # runner.py:608-614

# Spec §7.1 uses per model (controller ruling). A model not listed accepts the provider words.
MODEL_EFFORTS: Mapping[str, frozenset[str]] = {
    "gpt-6.1-sol": frozenset({"medium", "high"}),
    "claude-opus-5-5": frozenset({"medium"}),
    "deepseek/deepseek-v4.1-flash-1017": frozenset({"max"}),
}
PROVIDER_EFFORTS: Mapping[str, frozenset[str]] = {
    "openai": frozenset({"medium", "high", "max"}),
    "anthropic": frozenset({"medium", "high", "max"}),
    "openrouter": frozenset({"medium", "high", "max"}),
}


@dataclass(frozen=True)
class Inclusivity:
    """Whether a provider's token counts include the sub-counts (ruling F6); used by pricing."""

    input_includes_cached_read: bool | None  # None: the charge does not use token counts
    output_includes_reasoning: bool | None
    charge_from_reported_cost: bool


INCLUSIVITY: Mapping[str, Inclusivity] = {
    "openai": Inclusivity(True, True, False),
    "anthropic": Inclusivity(False, True, False),  # input excludes cache read and creation
    "openrouter": Inclusivity(None, None, True),  # charge is usage.cost only
}


class ProviderConfigError(ValueError):
    """A request refused before it is built; nothing is sent (NotSent)."""


class UnknownEffort(ProviderConfigError):
    pass


class MaxOutputTooLarge(ProviderConfigError):
    pass


class KeyMissing(ProviderConfigError):
    pass


class ErrorKind(Enum):
    NOT_SENT = "NotSent"
    SENT_CHARGE_KNOWN = "SentChargeKnown"  # nothing was generated: settles 0, computed
    SENT_CHARGE_UNKNOWN = "SentChargeUnknown"  # held and counted


@dataclass(frozen=True)
class ProviderError:
    kind: ErrorKind
    error_class: str
    message: str
    http_status: int | None = None
    usage: Usage | None = None  # present: the charge is settled from it
    billed_usd: Decimal | None = None
    reported_model: str | None = None
    request_id: str | None = None


class _BadReply(Exception):
    """The reply body does not have the documented shape."""


class _BadArguments(Exception):
    pass


# ---------------------------------------------------------------- effort, limits, build


def effort_for(spec: ModelSpec, effort: str | None = None) -> str:
    word = spec.effort if effort is None else effort
    allowed = MODEL_EFFORTS.get(spec.model, PROVIDER_EFFORTS[spec.provider])
    if word not in allowed:
        raise UnknownEffort(f"effort {word!r} is not accepted for {spec.model!r}")
    return word


def _json_bytes(body: Mapping[str, Any]) -> bytes:
    return json.dumps(body, separators=(",", ":")).encode("utf-8")


def _check(spec: ModelSpec, request: TurnRequest, key: str) -> str:
    if not key or any(c in key for c in "\r\n\x00"):
        raise KeyMissing("the key is empty or not a valid header value")
    if not 1 <= request.max_output_tokens <= MAX_OUTPUT_TOKENS:
        raise MaxOutputTooLarge(
            f"max_output_tokens {request.max_output_tokens} outside 1..{MAX_OUTPUT_TOKENS}"
        )
    return effort_for(spec, request.effort)


def _system_text(messages: tuple[Message, ...]) -> str:
    return "\n\n".join(m.text for m in messages if m.role == "system")


def build(spec: ModelSpec, request: TurnRequest, key: str) -> Request:
    """The one provider request. ``key`` is used only for the header; nothing stores it."""
    effort = _check(spec, request, key)
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    stream = False
    if spec.provider == "openai":
        url, body = OPENAI_URL, _openai_body(spec, request, effort)
    elif spec.provider == "anthropic":
        url, body = ANTHROPIC_URL, _anthropic_body(spec, request, effort)
        headers["anthropic-version"] = ANTHROPIC_VERSION
        headers["Accept"] = "text/event-stream"
        stream = True
    else:
        url, body = OPENROUTER_URL, _openrouter_body(spec, request, effort)
    return Request(
        url=url,
        headers=headers,
        body=_json_bytes(body),
        connect_s=CONNECT_S,
        idle_s=IDLE_S,
        overall_s=OVERALL_S,
        stream=stream,
    )


def _args_json(call: ToolCall) -> str:
    return json.dumps(call.arguments, separators=(",", ":"))


def _openai_body(spec: ModelSpec, request: TurnRequest, effort: str) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for m in request.messages:
        if m.role == "user":
            items.append({"role": "user", "content": m.text})
        elif m.role == "assistant":
            if m.text:
                items.append({"role": "assistant", "content": m.text})
            items.extend(
                {
                    "type": "function_call",
                    "call_id": c.call_id,
                    "name": c.name,
                    "arguments": _args_json(c),
                }
                for c in m.tool_calls
            )
        elif m.role == "tool":
            items.append(
                {"type": "function_call_output", "call_id": m.tool_call_id, "output": m.text}
            )
    return {
        "model": spec.model,
        "instructions": _system_text(request.messages),
        "input": items,
        "tools": [
            {
                "type": "function",
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
                "strict": OPENAI_STRICT_TOOLS,
            }
            for t in request.tools
        ],
        "tool_choice": "auto",
        "reasoning": {"effort": effort},
        "max_output_tokens": request.max_output_tokens,
        "store": False,  # controller ruling: do not retain request data at the provider
    }


def _anthropic_body(spec: ModelSpec, request: TurnRequest, effort: str) -> dict[str, Any]:
    out: list[dict[str, Any]] = []
    for m in request.messages:
        if m.role == "user":
            out.append({"role": "user", "content": m.text})
        elif m.role == "assistant":
            blocks: list[dict[str, Any]] = []
            if m.text:
                blocks.append({"type": "text", "text": m.text})
            blocks.extend(
                {"type": "tool_use", "id": c.call_id, "name": c.name, "input": c.arguments}
                for c in m.tool_calls
            )
            out.append({"role": "assistant", "content": blocks})
        elif m.role == "tool":
            result = {
                "type": "tool_result",
                "tool_use_id": m.tool_call_id,
                "content": m.text,
                "is_error": False,
            }
            previous = out[-1] if out else None
            if (
                previous is not None
                and previous["role"] == "user"
                and isinstance(previous["content"], list)
            ):
                previous["content"].append(result)  # all results of one turn in one message
            else:
                out.append({"role": "user", "content": [result]})
    return {
        "model": spec.model,
        "max_tokens": request.max_output_tokens,
        "system": _system_text(request.messages),
        "messages": out,
        "tools": [
            {"name": t.name, "description": t.description, "input_schema": t.parameters}
            for t in request.tools
        ],
        "tool_choice": {"type": "auto"},  # from the first call: forced choice is a 400 on Opus 5.5
        "stream": True,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": effort},
    }


def _openrouter_body(spec: ModelSpec, request: TurnRequest, effort: str) -> dict[str, Any]:
    out: list[dict[str, Any]] = []
    for m in request.messages:
        if m.role == "assistant":
            entry: dict[str, Any] = {"role": "assistant", "content": m.text or None}
            if m.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": c.call_id,
                        "type": "function",
                        "function": {"name": c.name, "arguments": _args_json(c)},
                    }
                    for c in m.tool_calls
                ]
            out.append(entry)
        elif m.role == "tool":
            out.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": m.text})
        else:
            out.append({"role": m.role, "content": m.text})
    body: dict[str, Any] = {
        "model": spec.model,
        "messages": out,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in request.tools
        ],
        "tool_choice": "auto",
        "max_completion_tokens": request.max_output_tokens,
        "reasoning": {"effort": effort},
    }
    if spec.model.startswith("deepseek/"):
        body["provider"] = {"ignore": list(OPENROUTER_IGNORE_FOR_DEEPSEEK)}
    return body


# ---------------------------------------------------------------- classification


def _is_error_object(body: bytes) -> bool:
    try:
        data = json.loads(body)
    except ValueError:
        return False
    if not isinstance(data, dict) or "usage" in data:
        return False
    return isinstance(data.get("error"), dict) or data.get("type") == "error"


def classify(status: int, body: bytes) -> ErrorKind:
    """Whether the charge for a reply that is not a usable turn is known.

    A 4xx whose body is the provider's error object with no usage generated nothing (known).
    Every 5xx, other status, unparsable or empty reply is unknown (ruling B10)."""
    if 400 <= status < 500 and _is_error_object(body):
        return ErrorKind.SENT_CHARGE_KNOWN
    return ErrorKind.SENT_CHARGE_UNKNOWN


def retry_after_seconds(headers: Mapping[str, str]) -> int:
    """The wait before the loop resends an in-flight 402: ``Retry-After``, at most 300 s."""
    raw = headers.get("retry-after", "")
    try:
        value = int(raw)
    except ValueError:
        return RETRY_AFTER_DEFAULT_S
    return min(max(value, 0), RETRY_AFTER_MAX_S)


def _snippet(redactor: Redactor, text: str) -> str:
    return redactor.text(text)[:MESSAGE_CHARS]


def _provider_message(text: str) -> str:
    try:
        data = json.loads(text)
    except ValueError:
        return text
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict) and isinstance(err.get("message"), str):
            return cast(str, err["message"])
    return text


def _http_error_class(status: int) -> str:
    if status == 402:
        return "CreditExhausted402"
    if 400 <= status < 500:
        return "ProviderRejected"
    if status >= 500:
        return "ProviderServerError"
    return "UnexpectedStatus"


def _http_error(redactor: Redactor, status: int, body: bytes, text: str) -> ProviderError:
    return ProviderError(
        kind=classify(status, body),
        error_class=_http_error_class(status),
        message=_snippet(redactor, _provider_message(text)),
        http_status=status,
    )


def error_from_transport(
    provider: Provider, exc: TransportError, redactor: Redactor
) -> Turn | ProviderError:
    """A transport failure as a classified error.

    Only a refusal before any connection is NotSent; every other failure may have reached the
    provider and is SentChargeUnknown. An Anthropic stream cut by a timeout whose last usage
    event arrived is settled from it (a Turn or a usage-carrying error), not unknown."""
    if isinstance(exc, InsecureUrl):
        return ProviderError(ErrorKind.NOT_SENT, "InsecureUrl", _snippet(redactor, str(exc)))
    error_class = (
        type(exc).__name__
        if isinstance(exc, ConnectTimeout | IdleTimeout | OverallTimeout)
        else "TransportError"
    )
    if provider == "anthropic" and exc.partial:
        cut = parse(provider, 200, exc.partial, {}, redactor)
        if isinstance(cut, Turn) or cut.usage is not None:
            return cut
    return ProviderError(ErrorKind.SENT_CHARGE_UNKNOWN, error_class, _snippet(redactor, str(exc)))


# ---------------------------------------------------------------- parse


def parse(
    provider: Provider,
    status: int,
    body: bytes,
    headers: Mapping[str, str],
    redactor: Redactor,
) -> Turn | ProviderError:
    """One reply as a turn or a classified error.

    A body or header holding a key (exact value or key shape) is redacted and returned as
    ``KeyReflected`` without being parsed; its text is the redacted text."""
    text = body.decode("utf-8", errors="replace")
    clean = redactor.text(text)
    if clean != text or any(redactor.text(v) != v for v in headers.values()):
        kind = classify(status, body) if not 200 <= status < 300 else ErrorKind.SENT_CHARGE_UNKNOWN
        return ProviderError(
            kind, "KeyReflected", _snippet(redactor, _provider_message(clean)), status
        )
    if not 200 <= status < 300:
        return _http_error(redactor, status, body, text)
    try:
        if provider == "openai":
            return _parse_openai(status, text)
        if provider == "anthropic":
            return _parse_anthropic(status, text, redactor)
        return _parse_openrouter(status, text)
    except _BadReply as error:
        return ProviderError(
            ErrorKind.SENT_CHARGE_UNKNOWN, "UnparsableReply", _snippet(redactor, str(error)), status
        )


def _count(data: Mapping[str, Any] | None, key: str) -> int | None:
    if data is None or key not in data or data[key] is None:
        return None
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise _BadReply(f"usage field {key} is not a non-negative integer")
    return value


def _sub(data: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if data is None or data.get(key) is None:
        return None
    value = data[key]
    if not isinstance(value, dict):
        raise _BadReply(f"{key} is not an object")
    return value


def _object(text: str, *, parse_float: Any = None) -> dict[str, Any]:
    try:
        data = json.loads(text, parse_float=parse_float)
    except ValueError:
        raise _BadReply("reply is not JSON") from None
    if not isinstance(data, dict):
        raise _BadReply("reply is not a JSON object")
    return data


def _arguments(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        raise _BadArguments("arguments are not a string")
    try:
        value = json.loads(raw or "{}")
    except ValueError:
        raise _BadArguments("arguments are not JSON") from None
    if not isinstance(value, dict):
        raise _BadArguments("arguments are not a JSON object")
    return value


def _str_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _malformed(status: int, usage: Usage, model: str | None, rid: str | None) -> ProviderError:
    return ProviderError(
        ErrorKind.SENT_CHARGE_KNOWN,
        "MalformedToolArguments",
        "a tool call's arguments are not a JSON object",
        status,
        usage,
        reported_model=model,
        request_id=rid,
    )


# OpenAI Responses


def _parse_openai(status: int, text: str) -> Turn | ProviderError:
    data = _object(text)
    raw_usage = _sub(data, "usage")
    in_details = _sub(raw_usage, "input_tokens_details")
    out_details = _sub(raw_usage, "output_tokens_details")
    usage = Usage(
        input_tokens=_count(raw_usage, "input_tokens"),
        cached_read_tokens=_count(in_details, "cached_tokens"),
        cache_write_tokens=_count(in_details, "cache_write_tokens"),
        output_tokens=_count(raw_usage, "output_tokens"),
        reasoning_tokens=_count(out_details, "reasoning_tokens"),
    )
    model, rid = _str_or_none(data.get("model")), _str_or_none(data.get("id"))
    if data.get("error"):
        return ProviderError(
            ErrorKind.SENT_CHARGE_UNKNOWN,
            "ResponseError",
            "the response carries an error object",
            status,
            reported_model=model,
            request_id=rid,
        )
    output = data.get("output")
    if not isinstance(output, list):
        raise _BadReply("output is not a list")
    texts: list[str] = []
    calls: list[ToolCall] = []
    for item in output:
        kind = item.get("type") if isinstance(item, dict) else None
        if kind == "function_call":
            try:
                args = _arguments(item.get("arguments"))
            except _BadArguments:
                return _malformed(status, usage, model, rid)
            calls.append(ToolCall(str(item.get("call_id")), str(item.get("name")), args))
        elif kind == "message":
            for part in item.get("content") or []:
                if isinstance(part, dict) and part.get("type") == "output_text":
                    texts.append(str(part.get("text", "")))
    incomplete = _sub(data, "incomplete_details")
    state = data.get("status")
    stop: StopReason
    if calls:
        stop = "tool_use"
    elif state == "completed":
        stop = "end"
    elif state == "incomplete" and incomplete and incomplete.get("reason") == "max_output_tokens":
        stop = "max_tokens"
    else:
        stop = "other"
    return Turn("".join(texts), tuple(calls), usage, stop, model, rid, status, None)


# Anthropic Messages (SSE)


def _sse_events(text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    data: list[str] = []

    def flush() -> None:
        if not data:
            return
        try:
            event = json.loads("\n".join(data))
        except ValueError:
            raise _BadReply("an event's data is not JSON") from None
        data.clear()
        if not isinstance(event, dict):
            raise _BadReply("an event's data is not a JSON object")
        events.append(event)

    for line in text.splitlines():
        if not line:
            flush()
            if events and events[-1].get("type") in ("message_stop", "error"):
                break
            continue
        name, _, value = line.partition(":")
        if name == "data":
            data.append(value.removeprefix(" "))
    flush()  # a cut stream may end inside an event
    return events


_ANTHROPIC_STOP: Mapping[str, StopReason] = {
    "end_turn": "end",
    "tool_use": "tool_use",
    "max_tokens": "max_tokens",
}
_ANTHROPIC_NAMED_ERRORS: Mapping[str, str] = {
    "refusal": "Refusal",
    "pause_turn": "PauseTurn",
    "model_context_window_exceeded": "ContextWindowExceeded",
}


def _anthropic_usage(raw: Mapping[str, Any]) -> Usage:
    creation = _sub(raw, "cache_creation")
    five, hour = (
        _count(creation, "ephemeral_5m_input_tokens"),
        _count(creation, "ephemeral_1h_input_tokens"),
    )
    written = _count(raw, "cache_creation_input_tokens")
    if written is None and five is not None and hour is not None:
        written = five + hour
    return Usage(
        input_tokens=_count(raw, "input_tokens"),
        cached_read_tokens=_count(raw, "cache_read_input_tokens"),
        cache_write_tokens=written,
        cache_write_5m_tokens=five,
        cache_write_1h_tokens=hour,
        output_tokens=_count(raw, "output_tokens"),
        reasoning_tokens=_count(_sub(raw, "output_tokens_details"), "thinking_tokens"),
    )


def _parse_anthropic(status: int, text: str, redactor: Redactor) -> Turn | ProviderError:
    events = _sse_events(text)
    if not events:
        raise _BadReply("no events in the stream")
    message: dict[str, Any] = {}
    blocks: dict[int, dict[str, Any]] = {}
    partial: dict[int, list[str]] = {}
    usage_raw: dict[str, Any] = {}
    stop_reason: str | None = None
    saw_delta = False
    for event in events:
        kind, index = event.get("type"), event.get("index")
        if kind == "error":
            err = event.get("error")
            err = err if isinstance(err, dict) else {}
            return ProviderError(
                ErrorKind.SENT_CHARGE_UNKNOWN,
                "StreamError",
                _snippet(redactor, f"{err.get('type', 'error')}: {err.get('message', '')}"),
                status,
                reported_model=_str_or_none(message.get("model")),
                request_id=_str_or_none(message.get("id")),
            )
        if kind == "message_start" and isinstance(event.get("message"), dict):
            message = dict(event["message"])
            usage_raw.update(_sub(message, "usage") or {})
        elif kind == "content_block_start" and isinstance(index, int):
            block = event.get("content_block")
            if not isinstance(block, dict) or index in blocks:
                raise _BadReply(f"content block {index} starts twice or without a block")
            blocks[index] = dict(block)
            if block.get("type") == "tool_use":
                partial[index] = []
        elif kind == "content_block_delta" and isinstance(index, int):
            delta = event.get("delta")
            if index not in blocks or not isinstance(delta, dict):
                raise _BadReply(f"delta for content block {index}, which has not started")
            dtype = delta.get("type")
            if dtype == "input_json_delta" and index in partial:
                partial[index].append(str(delta.get("partial_json", "")))
            elif dtype == "text_delta":
                blocks[index]["text"] = str(blocks[index].get("text") or "") + str(
                    delta.get("text", "")
                )
        elif kind == "content_block_stop" and isinstance(index, int):
            if index not in blocks:
                raise _BadReply(f"stop for content block {index}, which has not started")
            if index in partial:
                blocks[index]["input_json"] = "".join(partial.pop(index)) or "{}"
        elif kind == "message_delta":
            delta = event.get("delta")
            if isinstance(delta, dict):
                stop_reason = _str_or_none(delta.get("stop_reason")) or stop_reason
            usage_raw.update(_sub(event, "usage") or {})  # cumulative
            saw_delta = True
    model, rid = _str_or_none(message.get("model")), _str_or_none(message.get("id"))
    if not saw_delta:
        return ProviderError(
            ErrorKind.SENT_CHARGE_UNKNOWN,
            "StreamCut",
            "the stream ended before any usage event",
            status,
            reported_model=model,
            request_id=rid,
        )
    usage = _anthropic_usage(usage_raw)
    if partial:
        return ProviderError(
            ErrorKind.SENT_CHARGE_KNOWN,
            "StreamCut",
            "the stream ended inside a tool call",
            status,
            usage,
            reported_model=model,
            request_id=rid,
        )
    if stop_reason in _ANTHROPIC_NAMED_ERRORS:
        return ProviderError(
            ErrorKind.SENT_CHARGE_KNOWN,
            _ANTHROPIC_NAMED_ERRORS[cast(str, stop_reason)],
            f"stop_reason {stop_reason}",
            status,
            usage,
            reported_model=model,
            request_id=rid,
        )
    texts: list[str] = []
    calls: list[ToolCall] = []
    for index in sorted(blocks):
        block = blocks[index]
        if block.get("type") == "text":
            texts.append(str(block.get("text", "")))
        elif block.get("type") == "tool_use":
            try:
                args = _arguments(block.get("input_json", "{}"))
            except _BadArguments:
                return _malformed(status, usage, model, rid)
            calls.append(ToolCall(str(block.get("id")), str(block.get("name")), args))
    stop: StopReason = _ANTHROPIC_STOP.get(stop_reason or "", "other")
    return Turn("".join(texts), tuple(calls), usage, stop, model, rid, status, None)


# OpenRouter chat completions

_OPENROUTER_STOP: Mapping[str, StopReason] = {
    "stop": "end",
    "tool_calls": "tool_use",
    "length": "max_tokens",
}


def _parse_openrouter(status: int, text: str) -> Turn | ProviderError:
    data = _object(text, parse_float=Decimal)
    model, rid = _str_or_none(data.get("model")), _str_or_none(data.get("id"))
    if data.get("error"):
        return ProviderError(
            ErrorKind.SENT_CHARGE_UNKNOWN,
            "ResponseError",
            "the response carries an error object",
            status,
            reported_model=model,
            request_id=rid,
        )
    raw_usage = _sub(data, "usage")
    cost_raw = None if raw_usage is None else raw_usage.get("cost")
    billed: Decimal | None = None
    if cost_raw is not None:
        try:
            billed = Decimal(str(cost_raw))
        except InvalidOperation:
            raise _BadReply("usage.cost is not a number") from None
        if isinstance(cost_raw, bool) or not billed.is_finite() or billed < 0:
            raise _BadReply("usage.cost is not a non-negative number")
    usage = Usage(
        input_tokens=_count(raw_usage, "prompt_tokens"),
        cached_read_tokens=_count(_sub(raw_usage, "prompt_tokens_details"), "cached_tokens"),
        cache_write_tokens=_count(_sub(raw_usage, "prompt_tokens_details"), "cache_write_tokens"),
        output_tokens=_count(raw_usage, "completion_tokens"),
        reasoning_tokens=_count(_sub(raw_usage, "completion_tokens_details"), "reasoning_tokens"),
    )
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise _BadReply("choices is empty")
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict):
        raise _BadReply("choice has no message")
    calls: list[ToolCall] = []
    for item in message.get("tool_calls") or []:
        fn = item.get("function") if isinstance(item, dict) else None
        if not isinstance(fn, dict):
            raise _BadReply("a tool call has no function")
        try:
            args = _arguments(fn.get("arguments"))
        except _BadArguments:
            return _malformed(status, usage, model, rid)
        calls.append(ToolCall(str(item.get("id")), str(fn.get("name")), args))
    content = message.get("content")
    stop = _OPENROUTER_STOP.get(str(choice.get("finish_reason")), "other")
    if calls and stop == "end":
        stop = "tool_use"
    return Turn(
        content if isinstance(content, str) else "",
        tuple(calls),
        usage,
        stop,
        model,
        rid,
        status,
        billed,
    )
