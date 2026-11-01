"""Provider-neutral turn types and the recording ``response`` format.

``None`` in a ``Usage`` field means the provider did not report it; it is never 0.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Any, Literal, cast

Provider = Literal["openai", "anthropic", "openrouter"]
Role = Literal["system", "user", "assistant", "tool"]
StopReason = Literal["end", "tool_use", "max_tokens", "other"]

# The four spec §7.1 configurations. pricing.PRICES asserts its keys and providers against this.
CONFIG_PROVIDERS: Mapping[str, str] = MappingProxyType(
    {
        "sol-medium": "openai",
        "sol-high": "openai",
        "opus-medium": "anthropic",
        "deepseek-max": "openrouter",
    }
)

# The model each §7.1 configuration runs (spec §7.1). effort_for refuses any other pair.
CONFIG_MODELS: Mapping[str, str] = MappingProxyType(
    {
        "sol-medium": "gpt-6.1-sol",
        "sol-high": "gpt-6.1-sol",
        "opus-medium": "claude-opus-5-5",
        "deepseek-max": "deepseek/deepseek-v4.1-flash-1017",
    }
)

_ROLES = ("system", "user", "assistant", "tool")
_STOP_REASONS = ("end", "tool_use", "max_tokens", "other")


class TurnError(ValueError):
    """A turn, spec or recording is malformed."""


def _refuse_constant(name: str) -> object:
    raise TurnError(f"{name} is not allowed in a JSON number")


def load_json(text: str) -> object:
    """Parse JSON keeping decimal digits exactly (Decimal) and refusing NaN and Infinity."""
    try:
        return json.loads(text, parse_float=Decimal, parse_constant=_refuse_constant)
    except json.JSONDecodeError as error:
        raise TurnError(f"not JSON: {error.msg}") from None


def load_arguments(text: str) -> dict[str, Any]:
    value = load_json(text)
    if not isinstance(value, dict):
        raise TurnError("tool arguments are not a JSON object")
    return value


def dump_json(value: object) -> str:
    """Compact JSON that writes a Decimal with its exact digits; refuses NaN and Infinity."""
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise TurnError("a non-finite number cannot be written")
        return str(value)
    if isinstance(value, Mapping):
        return (
            "{" + ",".join(f"{json.dumps(str(k))}:{dump_json(v)}" for k, v in value.items()) + "}"
        )
    if isinstance(value, list | tuple):
        return "[" + ",".join(dump_json(v) for v in value) + "]"
    try:
        return json.dumps(value, allow_nan=False)
    except ValueError as error:
        raise TurnError(str(error)) from None


@dataclass(frozen=True)
class ProviderBlock:
    """An opaque, provider-tagged block (Anthropic thinking) returned unchanged on the next turn."""

    provider: str
    data: dict[str, Any]


@dataclass(frozen=True)
class ModelSpec:
    config_id: str
    provider: Provider
    model: str
    effort: str

    def __post_init__(self) -> None:
        expected = CONFIG_PROVIDERS.get(self.config_id)
        if expected is not None and expected != self.provider:
            raise TurnError(
                f"config {self.config_id!r} belongs to {expected!r}, not {self.provider!r}"
            )
        if self.provider not in ("openai", "anthropic", "openrouter"):
            raise TurnError(f"unknown provider {self.provider!r}")


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: Mapping[str, Any]


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class Message:
    role: Role
    text: str
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None
    provider_blocks: tuple[ProviderBlock, ...] = ()

    def __post_init__(self) -> None:
        if self.role not in _ROLES:
            raise TurnError(f"unknown role {self.role!r}")
        if self.role == "tool" and not self.tool_call_id:
            raise TurnError("a tool message needs tool_call_id")
        if self.role != "assistant" and self.tool_calls:
            raise TurnError("only an assistant message carries tool_calls")
        if self.role != "assistant" and self.provider_blocks:
            raise TurnError("only an assistant message carries provider_blocks")


@dataclass(frozen=True)
class Usage:
    input_tokens: int | None = None
    cached_read_tokens: int | None = None
    cache_write_tokens: int | None = None
    cache_write_5m_tokens: int | None = None
    cache_write_1h_tokens: int | None = None
    output_tokens: int | None = None
    reasoning_tokens: int | None = None

    def __post_init__(self) -> None:
        for f in fields(self):
            value = getattr(self, f.name)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise TurnError(f"usage.{f.name} must be a non-negative integer or None")


@dataclass(frozen=True)
class TurnRequest:
    messages: tuple[Message, ...]
    tools: tuple[ToolSpec, ...]
    max_output_tokens: int
    effort: str


@dataclass(frozen=True)
class Turn:
    text: str
    tool_calls: tuple[ToolCall, ...]
    usage: Usage
    stop_reason: StopReason
    reported_model: str | None
    request_id: str | None
    http_status: int
    billed_usd: Decimal | None = field(default=None)
    provider_blocks: tuple[ProviderBlock, ...] = ()

    def __post_init__(self) -> None:
        if self.stop_reason not in _STOP_REASONS:
            raise TurnError(f"unknown stop_reason {self.stop_reason!r}")
        if isinstance(self.http_status, bool) or not isinstance(self.http_status, int):
            raise TurnError("http_status must be an integer")
        if self.billed_usd is not None and (not self.billed_usd.is_finite() or self.billed_usd < 0):
            raise TurnError("billed_usd must be a finite non-negative Decimal or None")


_TURN_KEYS = frozenset(
    {
        "text",
        "tool_calls",
        "usage",
        "stop_reason",
        "reported_model",
        "request_id",
        "http_status",
        "billed_usd",
        "provider_blocks",
    }
)
_USAGE_KEYS = frozenset(f.name for f in fields(Usage))
_BLOCK_KEYS = frozenset({"provider", "data"})
_CALL_KEYS = frozenset({"call_id", "name", "arguments"})


def turn_to_json(turn: Turn) -> dict[str, Any]:
    return {
        "text": turn.text,
        "tool_calls": [
            {"call_id": c.call_id, "name": c.name, "arguments": dump_json(c.arguments)}
            for c in turn.tool_calls
        ],
        "usage": {f.name: getattr(turn.usage, f.name) for f in fields(Usage)},
        "stop_reason": turn.stop_reason,
        "reported_model": turn.reported_model,
        "request_id": turn.request_id,
        "http_status": turn.http_status,
        "billed_usd": None if turn.billed_usd is None else str(turn.billed_usd),
        "provider_blocks": [{"provider": b.provider, "data": b.data} for b in turn.provider_blocks],
    }


def _exact_keys(name: str, obj: object, keys: frozenset[str]) -> Mapping[str, Any]:
    if not isinstance(obj, Mapping):
        raise TurnError(f"{name} must be an object")
    unknown = sorted(set(obj) - keys)
    missing = sorted(keys - set(obj))
    if unknown:
        raise TurnError(f"{name}: unknown keys {unknown}")
    if missing:
        raise TurnError(f"{name}: missing keys {missing}")
    return obj


def _optional_str(name: str, value: object) -> str | None:
    if value is not None and not isinstance(value, str):
        raise TurnError(f"{name} must be a string or null")
    return value


def turn_from_json(obj: object) -> Turn:
    data = _exact_keys("turn", obj, _TURN_KEYS)
    text = data["text"]
    if not isinstance(text, str):
        raise TurnError("text must be a string")
    raw_calls = data["tool_calls"]
    if not isinstance(raw_calls, list):
        raise TurnError("tool_calls must be a list")
    calls: list[ToolCall] = []
    for raw in raw_calls:
        item = _exact_keys("tool call", raw, _CALL_KEYS)
        if not (
            isinstance(item["call_id"], str)
            and isinstance(item["name"], str)
            and isinstance(item["arguments"], str)
        ):
            raise TurnError("tool call fields have the wrong types")
        calls.append(ToolCall(item["call_id"], item["name"], load_arguments(item["arguments"])))
    raw_blocks = data["provider_blocks"]
    if not isinstance(raw_blocks, list):
        raise TurnError("provider_blocks must be a list")
    blocks: list[ProviderBlock] = []
    for raw in raw_blocks:
        entry = _exact_keys("provider block", raw, _BLOCK_KEYS)
        if not (isinstance(entry["provider"], str) and isinstance(entry["data"], dict)):
            raise TurnError("provider block fields have the wrong types")
        blocks.append(ProviderBlock(entry["provider"], entry["data"]))
    usage_obj = _exact_keys("usage", data["usage"], _USAGE_KEYS)
    usage = Usage(**{k: usage_obj[k] for k in _USAGE_KEYS})
    billed_raw = data["billed_usd"]
    billed: Decimal | None = None
    if billed_raw is not None:
        if not isinstance(billed_raw, str):
            raise TurnError("billed_usd must be a decimal string or null")
        try:
            billed = Decimal(billed_raw)
        except InvalidOperation as error:
            raise TurnError("billed_usd is not a decimal string") from error
    stop = data["stop_reason"]
    status = data["http_status"]
    if not isinstance(stop, str):
        raise TurnError("stop_reason must be a string")
    return Turn(
        text=text,
        tool_calls=tuple(calls),
        usage=usage,
        stop_reason=cast(StopReason, stop),  # validated in Turn.__post_init__
        reported_model=_optional_str("reported_model", data["reported_model"]),
        request_id=_optional_str("request_id", data["request_id"]),
        http_status=status,
        billed_usd=billed,
        provider_blocks=tuple(blocks),
    )
