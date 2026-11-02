"""OpenAI, Anthropic and OpenRouter mappers: one request in, one provider-neutral turn out.

``build`` makes exactly one request; ``parse`` reads one reply. Retry, resend and repair belong
to the loop. A reply that is not a usable turn comes back as a ``ProviderError`` carrying an
``ErrorKind`` that says how its charge is settled: SentChargeKnown (a 4xx error object, nothing
generated) at 0; SentChargeUsage (tokens were generated and usage is reported) from that usage,
computed, never at 0; SentChargeUnknown held and counted; NotSent nothing.
Provider facts: work/context-plan/provider-docs-2026-10-31.md and provider-docs-o5-controller.md.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
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
    CONFIG_MODELS,
    MODEL_EFFORTS,
    Message,
    ModelSpec,
    Provider,
    ProviderBlock,
    StopReason,
    ToolCall,
    Turn,
    TurnError,
    TurnRequest,
    Usage,
    dump_json,
    load_arguments,
    load_json,
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
    SENT_CHARGE_KNOWN = "SentChargeKnown"  # a 4xx error object, no usage: nothing generated, 0
    SENT_CHARGE_USAGE = "SentChargeUsage"  # tokens generated, usage reported: settle from it
    SENT_CHARGE_UNKNOWN = "SentChargeUnknown"  # held and counted


@dataclass(frozen=True)
class ProviderError:
    kind: ErrorKind
    error_class: str
    message: str
    http_status: int | None = None
    usage: Usage | None = None  # exactly when kind is SentChargeUsage
    billed_usd: Decimal | None = None  # OpenRouter usage.cost on a usage-bearing error
    reported_model: str | None = None
    request_id: str | None = None

    def __post_init__(self) -> None:
        if (self.kind is ErrorKind.SENT_CHARGE_USAGE) != (self.usage is not None):
            raise ValueError("usage is present exactly when kind is SentChargeUsage")


class _BadReply(Exception):
    """The reply body does not have the documented shape."""


class _BadArguments(Exception):
    pass


# ---------------------------------------------------------------- effort, limits, build


def effort_for(spec: ModelSpec, effort: str | None = None) -> str:
    """The provider's effort word, only for a (model, effort) pair in the §7.1 table and a
    model that is the one its configuration names."""
    word = spec.effort if effort is None else effort
    expected = CONFIG_MODELS.get(spec.config_id)
    if expected is not None and expected != spec.model:
        raise UnknownEffort(f"config {spec.config_id!r} runs {expected!r}, not {spec.model!r}")
    if word not in MODEL_EFFORTS.get(spec.model, frozenset()):
        raise UnknownEffort(f"effort {word!r} is not accepted for {spec.model!r}")
    return word


def _json_bytes(body: Mapping[str, Any]) -> bytes:
    return dump_json(body).encode("utf-8")


def _check(spec: ModelSpec, request: TurnRequest, key: str) -> str:
    if not key or not all("!" <= c <= "~" for c in key):
        raise KeyMissing("the key is empty or not printable ASCII")
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
    return dump_json(call.arguments)


# PF-R6: sent explicitly so the write tier is the 30m one the price table charges.
OPENAI_PROMPT_CACHE_OPTIONS: Mapping[str, str] = MappingProxyType({"mode": "implicit", "ttl": "30m"})


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
        "prompt_cache_options": dict(OPENAI_PROMPT_CACHE_OPTIONS),
    }


def _anthropic_body(spec: ModelSpec, request: TurnRequest, effort: str) -> dict[str, Any]:
    out: list[dict[str, Any]] = []
    for m in request.messages:
        if m.role == "user":
            out.append({"role": "user", "content": m.text})
        elif m.role == "assistant":
            blocks: list[dict[str, Any]] = [
                dict(b.data) for b in m.provider_blocks if b.provider == "anthropic"
            ]  # thinking blocks first, unchanged and in order
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
    except (ValueError, RecursionError):
        return False
    if not isinstance(data, dict) or "usage" in data:
        return False
    return isinstance(data.get("error"), dict) or data.get("type") == "error"


def classify(status: int, body: bytes) -> ErrorKind:
    """Whether the charge for a reply that is not a usable turn is known.

    A 4xx whose body is the provider's error object with no usage generated nothing (known).
    Every 5xx, other status, unparsable or empty reply is unknown (ruling B10). A reply that
    generated tokens and reports usage is SentChargeUsage, decided where the usage is read."""
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
    except (ValueError, RecursionError):
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
    message = _provider_message(text)
    reflected = redactor.text(message) != message  # e.g. a JSON-escaped key, whole once decoded
    return ProviderError(
        kind=classify(status, body),
        error_class="KeyReflected" if reflected else _http_error_class(status),
        message=_snippet(redactor, message),
        http_status=status,
    )


def error_from_transport(
    provider: Provider, exc: TransportError, redactor: Redactor
) -> Turn | ProviderError:
    """A transport failure as a classified error.

    Only a refusal before any connection is NotSent; every other failure (a watchdog or
    deadline OverallTimeout included) may have reached the provider and is SentChargeUnknown.
    An Anthropic stream cut by a timeout whose last usage event arrived is settled from it
    (a Turn or a SentChargeUsage error), not unknown."""
    if isinstance(exc, InsecureUrl):
        return ProviderError(ErrorKind.NOT_SENT, "InsecureUrl", _snippet(redactor, str(exc)))
    error_class = (
        type(exc).__name__
        if isinstance(exc, ConnectTimeout | IdleTimeout | OverallTimeout)
        else "TransportError"
    )
    if provider == "anthropic" and exc.partial:
        cut = parse(provider, 200, exc.partial, {}, redactor)
        if (
            isinstance(cut, Turn)
            or cut.kind is ErrorKind.SENT_CHARGE_USAGE
            or cut.error_class == "KeyReflected"
        ):
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

    A body or header holding a key (exact value or key shape), or a key that is whole only
    after decoding (JSON escapes, SSE deltas joined), comes back as ``KeyReflected`` with the
    redacted text, never as a turn."""
    text = body.decode("utf-8", errors="replace")
    clean = redactor.text(text)
    if clean != text or any(redactor.text(v) != v for v in headers.values()):
        kind = classify(status, body) if not 200 <= status < 300 else ErrorKind.SENT_CHARGE_UNKNOWN
        return ProviderError(
            kind, "KeyReflected", _snippet(redactor, _provider_message(clean)), status
        )
    if not 200 <= status < 300:
        return _http_error(redactor, status, body, text)
    seen: list[Any] = []  # every string a mapper decoded or joined, whatever way it exits
    try:
        if provider == "openai":
            result = _parse_openai(status, text, seen)
        elif provider == "anthropic":
            result = _parse_anthropic(status, text, redactor, seen)
        else:
            result = _parse_openrouter(status, text, seen)
    except (_BadReply, RecursionError) as error:
        detail = "reply is nested too deeply" if isinstance(error, RecursionError) else str(error)
        result = ProviderError(
            ErrorKind.SENT_CHARGE_UNKNOWN, "UnparsableReply", _snippet(redactor, detail), status
        )
    return _guard_decoded(result, status, redactor, seen)


def _guard_decoded(
    result: Turn | ProviderError, status: int, redactor: Redactor, seen: list[Any]
) -> Turn | ProviderError:
    """Run the redactor over what the mapper decoded and over the outcome: a key can be whole
    only here, and a mapper's early exit must not drop the strings it had already joined."""
    try:
        reflected = redactor.json_value(seen) != seen
    except RecursionError:
        # fail closed: data too deep for the redactor cannot be shown clean, so it counts as
        # reflected (the reply is withheld, never passed on unchecked).
        reflected = True
    if isinstance(result, ProviderError):
        if reflected or any(
            redactor.text(v) != v
            for v in (result.message, result.reported_model, result.request_id)
            if v
        ):
            return ProviderError(
                result.kind,
                "KeyReflected",
                _snippet(redactor, result.message),
                result.http_status,
                result.usage,
                result.billed_usd,
            )
        return result
    blocks = [{"provider": b.provider, "data": b.data} for b in result.provider_blocks]
    calls = [{"id": c.call_id, "name": c.name, "args": c.arguments} for c in result.tool_calls]
    payload = [result.text, result.reported_model, result.request_id, blocks, calls]
    if reflected or redactor.json_value(payload) != payload:
        return ProviderError(
            ErrorKind.SENT_CHARGE_UNKNOWN,
            "KeyReflected",
            _snippet(redactor, result.text),
            status,
        )
    return result


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


def _object(text: str) -> dict[str, Any]:
    try:
        data = load_json(text)
    except TurnError:
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
        return load_arguments(raw or "{}")
    except TurnError:
        raise _BadArguments("arguments are not a JSON object") from None


def _str_or_none(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _id(item: Mapping[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value:
        raise _BadReply(f"a tool call has no {key}")
    return value


def _usage_error(
    error_class: str,
    message: str,
    status: int,
    usage: Usage,
    model: str | None,
    rid: str | None,
    billed: Decimal | None = None,
) -> ProviderError:
    """Tokens were generated: SentChargeUsage when usage was reported, else unknown."""
    reported = any(getattr(usage, f) is not None for f in usage.__dataclass_fields__)
    return ProviderError(
        ErrorKind.SENT_CHARGE_USAGE if reported else ErrorKind.SENT_CHARGE_UNKNOWN,
        error_class,
        message,
        status,
        usage if reported else None,
        billed,
        model,
        rid,
    )


def _malformed(
    status: int, usage: Usage, model: str | None, rid: str | None, billed: Decimal | None = None
) -> ProviderError:
    return _usage_error(
        "MalformedToolArguments",
        "a tool call's arguments are not a JSON object",
        status,
        usage,
        model,
        rid,
        billed,
    )


# OpenAI Responses


def _parse_openai(status: int, text: str, seen: list[Any]) -> Turn | ProviderError:
    data: dict[str, Any] = {}
    texts: list[str] = []
    try:
        data = _object(text)
        return _openai_outcome(status, data, texts, seen)
    finally:
        seen.extend([data, "".join(texts)])


def _openai_outcome(
    status: int, data: dict[str, Any], texts: list[str], seen: list[Any]
) -> Turn | ProviderError:
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
    calls: list[ToolCall] = []
    for item in output:
        kind = item.get("type") if isinstance(item, dict) else None
        if kind == "function_call":
            call_id, name = _id(item, "call_id"), _id(item, "name")
            try:
                args = _arguments(item.get("arguments"))
                seen.append(args)
            except _BadArguments:
                return _malformed(status, usage, model, rid)
            calls.append(ToolCall(call_id, name, args))
        elif kind == "message":
            content = item.get("content")
            if content is None:
                content = []
            if not isinstance(content, list):
                raise _BadReply("message content is not a list")
            for part in content:
                if isinstance(part, dict) and part.get("type") == "refusal":
                    return _usage_error("Refusal", "the model refused", status, usage, model, rid)
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

_LINE_BREAK = re.compile(r"\r\n|\r|\n")  # SSE lines end at LF, CR or CRLF only
_ERROR_TYPE = re.compile(r"[A-Za-z0-9_]{1,64}")


_TERMINAL_EVENTS = ("message_stop", "error")
_SIMPLE_ESCAPES = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}


def _open_string(data: str) -> str:
    """The decoded content of the JSON string left open at the end of ``data`` (a stream cut
    inside an event), without a partial escape; "" when no string is open. Field-agnostic."""
    start, i = -1, 0
    while i < len(data):
        if data[i] == "\\" and start >= 0:
            i += 6 if data[i + 1 : i + 2] == "u" else 2
            continue
        if data[i] == '"':
            start = -1 if start >= 0 else i + 1
        i += 1
    if start < 0:
        return ""
    raw, out, i = data[start:], [], 0
    while i < len(raw):
        if raw[i] != "\\":
            out.append(raw[i])
            i += 1
        elif raw[i + 1 : i + 2] in _SIMPLE_ESCAPES:
            out.append(_SIMPLE_ESCAPES[raw[i + 1]])
            i += 2
        elif raw[i + 1 : i + 2] == "u" and len(raw) >= i + 6 and _is_hex(raw[i + 2 : i + 6]):
            out.append(chr(int(raw[i + 2 : i + 6], 16)))
            i += 6
        elif i + 1 >= len(raw) or (raw[i + 1] == "u" and len(raw) < i + 6):
            break  # an escape cut in half: nothing of it is decoded
        else:
            out.append(raw[i])  # not a JSON escape: keep the text, a reader may still see it
            i += 1
    return "".join(out)


def _is_hex(text: str) -> bool:
    return len(text) == 4 and all(c in "0123456789abcdefABCDEF" for c in text)


def _sse_events(text: str, events: list[dict[str, Any]], after: list[Any]) -> str | None:
    """Decode the stream into ``events`` (up to and including the terminal event) and ``after``
    (everything decoded past it, kept only so it can be checked for a key). The caller passes
    the lists in, so events decoded before a ``_BadReply`` survive it. Returns None for a
    stream that ends on an event boundary, else the open string of the event the stream was
    cut inside (``after`` takes that one when it lies past the terminal event)."""
    data: list[str] = []

    def flush(final: bool) -> str | None:
        if not data:
            return None
        joined = "\n".join(data)
        data.clear()
        terminal = bool(events) and events[-1].get("type") in _TERMINAL_EVENTS
        try:
            event = load_json(joined)
        except TurnError:
            if final:
                return _open_string(joined)
            if terminal:
                return None  # past the terminal event nothing is meaning, only text to check
            raise _BadReply("an event's data is not JSON") from None
        if not isinstance(event, dict):
            if terminal:
                after.append(event)
                return None
            raise _BadReply("an event's data is not a JSON object")
        (after if terminal else events).append(event)
        return None

    for line in _LINE_BREAK.split(text):
        if not line:
            flush(final=False)
            continue
        name, _, value = line.partition(":")
        if name == "data":
            data.append(value.removeprefix(" "))
    cut = flush(final=True)  # a cut stream may end inside an event
    if cut is not None and events and events[-1].get("type") in _TERMINAL_EVENTS:
        after.append(cut)
        return None
    return cut


def _joined_deltas(events: list[Any]) -> list[str]:
    """Each delta field joined in order per content block: a key split across events past the
    terminal event, which no block holds, is still whole here."""
    joined: dict[str, str] = {}
    for event in events:
        delta = event.get("delta") if isinstance(event, dict) else None
        if isinstance(delta, dict):
            for field, value in delta.items():
                if field != "type" and isinstance(value, str):
                    slot = f"{event.get('index')!r}/{delta.get('type')!r}/{field}"
                    joined[slot] = joined.get(slot, "") + value
    return list(joined.values())


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
_THINKING_TYPES = ("thinking", "redacted_thinking")


def _anthropic_usage(raw: Mapping[str, Any]) -> Usage:
    creation = _sub(raw, "cache_creation")
    five = _count(creation, "ephemeral_5m_input_tokens")
    hour = _count(creation, "ephemeral_1h_input_tokens")
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


def _in_stream_error(
    event: Mapping[str, Any], status: int, message: Mapping[str, Any], redactor: Redactor
) -> ProviderError:
    err = event.get("error")
    err = err if isinstance(err, dict) else {}
    kind = err.get("type")
    error_class = kind if isinstance(kind, str) and _ERROR_TYPE.fullmatch(kind) else "StreamError"
    return ProviderError(
        ErrorKind.SENT_CHARGE_UNKNOWN,  # tokens may have been generated: the charge stays unknown
        redactor.text(error_class),
        _snippet(redactor, f"{err.get('type', 'error')}: {err.get('message', '')}"),
        status,
        reported_model=_str_or_none(message.get("model")),
        request_id=_str_or_none(message.get("id")),
    )


def _anthropic_text(blocks: Mapping[int, Mapping[str, Any]]) -> str:
    return "".join(
        str(blocks[index].get("text", ""))
        for index in sorted(blocks)
        if blocks[index].get("type") == "text"
    )


def _parse_anthropic(
    status: int, text: str, redactor: Redactor, seen: list[Any]
) -> Turn | ProviderError:
    events: list[dict[str, Any]] = []
    after: list[Any] = []
    blocks: dict[int, dict[str, Any]] = {}
    partial: dict[int, str] = {}
    cut: str | None = None
    try:
        cut = _sse_events(text, events, after)
        return _anthropic_outcome(status, events, cut, blocks, partial, redactor, seen)
    finally:
        seen.extend([events, after, _joined_deltas([*events, *after]), blocks, partial, cut])
        seen.append(_anthropic_text(blocks))
        if cut is not None:  # the open string of the cut event continues every string so far
            strings = [v for b in blocks.values() for v in b.values() if isinstance(v, str)]
            seen.extend(s + cut for s in [*strings, *partial.values()])


def _anthropic_outcome(
    status: int,
    events: list[dict[str, Any]],
    cut: str | None,
    blocks: dict[int, dict[str, Any]],
    partial: dict[int, str],
    redactor: Redactor,
    seen: list[Any],
) -> Turn | ProviderError:
    if not events and cut is None:
        raise _BadReply("no events in the stream")
    message: dict[str, Any] = {}
    usage_raw: dict[str, Any] = {}
    stop_reason: str | None = None
    saw_delta = False
    for event in events:
        kind, index = event.get("type"), event.get("index")
        if kind == "error":
            return _in_stream_error(event, status, message, redactor)
        if kind == "message_start" and isinstance(event.get("message"), dict):
            message = dict(event["message"])
            usage_raw.update(_sub(message, "usage") or {})
        elif kind == "content_block_start" and isinstance(index, int):
            block = event.get("content_block")
            if not isinstance(block, dict) or index in blocks:
                raise _BadReply(f"content block {index} starts twice or without a block")
            blocks[index] = dict(block)
            if block.get("type") == "tool_use":
                partial[index] = ""
        elif kind == "content_block_delta" and isinstance(index, int):
            delta = event.get("delta")
            if index not in blocks or not isinstance(delta, dict):
                raise _BadReply(f"delta for content block {index}, which has not started")
            dtype = delta.get("type")
            if dtype == "input_json_delta" and index in partial:
                partial[index] += str(delta.get("partial_json", ""))
            elif dtype in ("text_delta", "thinking_delta", "signature_delta"):
                field = {"text_delta": "text", "thinking_delta": "thinking"}.get(
                    str(dtype), "signature"
                )
                blocks[index][field] = str(blocks[index].get(field) or "") + str(
                    delta.get(field, "")
                )
        elif kind == "content_block_stop" and isinstance(index, int):
            if index not in blocks:
                raise _BadReply(f"stop for content block {index}, which has not started")
            if index in partial:
                blocks[index]["input_json"] = partial.pop(index) or "{}"
        elif kind == "message_delta":
            delta = event.get("delta")
            if isinstance(delta, dict):
                stop_reason = _str_or_none(delta.get("stop_reason")) or stop_reason
            usage_raw.update(_sub(event, "usage") or {})  # cumulative
            saw_delta = True
    if cut is not None:
        raise _BadReply("an event's data is not JSON")
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
        return _usage_error(
            "StreamCut", "the stream ended inside a tool call", status, usage, model, rid
        )
    if stop_reason in _ANTHROPIC_NAMED_ERRORS:
        return _usage_error(
            _ANTHROPIC_NAMED_ERRORS[cast(str, stop_reason)],
            f"stop_reason {stop_reason}",
            status,
            usage,
            model,
            rid,
        )
    calls: list[ToolCall] = []
    provider_blocks: list[ProviderBlock] = []
    for index in sorted(blocks):
        block = blocks[index]
        if block.get("type") in _THINKING_TYPES:
            provider_blocks.append(ProviderBlock("anthropic", dict(block)))
        elif block.get("type") == "tool_use":
            call_id, name = _id(block, "id"), _id(block, "name")
            try:
                args = _arguments(block.get("input_json", "{}"))
                seen.append(args)
            except _BadArguments:
                return _malformed(status, usage, model, rid)
            calls.append(ToolCall(call_id, name, args))
    stop: StopReason = _ANTHROPIC_STOP.get(stop_reason or "", "other")
    return Turn(
        _anthropic_text(blocks),
        tuple(calls),
        usage,
        stop,
        model,
        rid,
        status,
        None,
        tuple(provider_blocks),
    )


# OpenRouter chat completions

_OPENROUTER_STOP: Mapping[str, StopReason] = {
    "stop": "end",
    "tool_calls": "tool_use",
    "length": "max_tokens",
}


def _parse_openrouter(status: int, text: str, seen: list[Any]) -> Turn | ProviderError:
    data = _object(text)
    seen.append(data)  # nothing below changes it; the guard checks the whole decoded reply
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
        if isinstance(cost_raw, bool) or not isinstance(cost_raw, int | Decimal):
            raise _BadReply("usage.cost is not a number")
        billed = Decimal(cost_raw)
        if not billed.is_finite() or billed < 0:
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
        call_id, name = _id(item, "id"), _id(fn, "name")
        try:
            args = _arguments(fn.get("arguments"))
            seen.append(args)
        except _BadArguments:
            return _malformed(status, usage, model, rid, billed)
        calls.append(ToolCall(call_id, name, args))
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
