"""Mappers, effort map, classification and the key-reflection guard. No network."""

import http.client
import json
import socket
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast

import pytest

from deploy_workflow.model.providers import (
    INCLUSIVITY,
    ErrorKind,
    KeyMissing,
    MaxOutputTooLarge,
    ProviderError,
    UnknownEffort,
    _openrouter_body,
    build,
    classify,
    effort_for,
    error_from_transport,
    parse,
    retry_after_seconds,
)
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.transport import IdleTimeout, InsecureUrl, TransportError
from deploy_workflow.model.turn import (
    Message,
    ModelSpec,
    Provider,
    ProviderBlock,
    ToolCall,
    ToolSpec,
    Turn,
    TurnRequest,
    Usage,
)

KEY = "sk-or-v1-TESTONLYabcdef0123456789"
SOL = ModelSpec("sol-medium", "openai", "gpt-6.1-sol", "medium")
OPUS = ModelSpec("opus-medium", "anthropic", "claude-opus-5-5", "medium")
DEEPSEEK = ModelSpec("deepseek-max", "openrouter", "deepseek/deepseek-v4.1-flash-1017", "max")
TOOLS = (ToolSpec("submit_x", "submit", {"type": "object", "properties": {}}),)


@pytest.fixture(autouse=True)
def _default_transport_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_a: object, **_k: object) -> None:
        raise AssertionError("the default network path was used in a test")

    monkeypatch.setattr(http.client, "HTTPSConnection", boom)
    monkeypatch.setattr(socket, "create_connection", boom)


def _request(max_tokens: int = 128000, effort: str = "medium") -> TurnRequest:
    return TurnRequest(
        messages=(
            Message("system", "be exact"),
            Message("user", "go"),
            Message("assistant", "", (ToolCall("c0", "read_inputs", {"k": 1}),)),
            Message("tool", "result-a", tool_call_id="c0"),
            Message("tool", "result-b", tool_call_id="c0b"),
        ),
        tools=TOOLS,
        max_output_tokens=max_tokens,
        effort=effort,
    )


def _body(req: Any) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(req.body))


# ------------------------------------------------------------------ build


def test_openai_build() -> None:
    req = build(SOL, _request(), KEY)
    body = _body(req)
    assert req.url == "https://api.openai.com/v1/responses"
    assert req.headers["Authorization"] == f"Bearer {KEY}"
    assert body["tool_choice"] == "auto"
    assert body["max_output_tokens"] == 128000
    assert body["reasoning"] == {"effort": "medium"}
    assert body["store"] is False
    assert body["instructions"] == "be exact"
    assert body["input"][-1] == {
        "type": "function_call_output",
        "call_id": "c0b",
        "output": "result-b",
    }
    assert body["input"][1]["type"] == "function_call"
    assert json.loads(body["input"][1]["arguments"]) == {"k": 1}
    assert body["tools"][0]["type"] == "function" and body["tools"][0]["name"] == "submit_x"
    assert not req.stream


def test_anthropic_build() -> None:
    req = build(OPUS, _request(), KEY)
    body = _body(req)
    assert req.url == "https://api.anthropic.com/v1/messages"
    assert req.headers["Authorization"] == f"Bearer {KEY}"
    assert req.headers["anthropic-version"] == "2026-10-21"
    assert body["tool_choice"] == {"type": "auto"}
    assert body["max_tokens"] == 128000
    assert body["stream"] is True and req.stream
    assert body["thinking"] == {"type": "adaptive"}
    assert body["output_config"] == {"effort": "medium"}
    assert body["system"] == "be exact"
    assert body["messages"][1]["content"][0] == {
        "type": "tool_use",
        "id": "c0",
        "name": "read_inputs",
        "input": {"k": 1},
    }
    results = body["messages"][2]["content"]  # both results in one user message
    assert [r["tool_use_id"] for r in results] == ["c0", "c0b"]
    assert results[0]["is_error"] is False
    assert body["tools"][0]["input_schema"] == TOOLS[0].parameters


def test_openrouter_build_deepseek_ignores_open_inference() -> None:
    req = build(DEEPSEEK, _request(effort="max"), KEY)
    body = _body(req)
    assert req.url == "https://openrouter.ai/api/v1/chat/completions"
    assert req.headers["Authorization"] == f"Bearer {KEY}"
    assert body["tool_choice"] == "auto"
    assert body["max_completion_tokens"] == 128000 and "max_tokens" not in body
    assert body["reasoning"] == {"effort": "max"}
    assert body["provider"]["ignore"] == ["open-inference"]
    assert body["messages"][-1] == {"role": "tool", "tool_call_id": "c0b", "content": "result-b"}
    assert body["messages"][2]["tool_calls"][0]["function"]["name"] == "read_inputs"
    assert body["tools"][0]["function"]["name"] == "submit_x"


def _unchecked_spec(config_id: str, provider: str, model: str, effort: str) -> ModelSpec:
    """A spec that skipped ModelSpec's own check, to test the checks in effort_for and build."""
    return cast(
        ModelSpec,
        SimpleNamespace(config_id=config_id, provider=provider, model=model, effort=effort),
    )


def test_other_openrouter_id_has_no_provider_ignore() -> None:
    other = _unchecked_spec("x", "openrouter", "mistralai/some-model", "high")
    assert "provider" not in _openrouter_body(other, _request(effort="high"), "high")
    assert "provider" in _openrouter_body(DEEPSEEK, _request(effort="max"), "max")


@pytest.mark.parametrize(
    "spec",
    [
        _unchecked_spec("sol-medium", "openai", "gpt-6.1-sol-mini", "medium"),
        _unchecked_spec("opus-medium", "anthropic", "claude-opus-5-5-20261101", "medium"),
        _unchecked_spec("x", "openrouter", "mistralai/some-model", "high"),
        _unchecked_spec("sol-medium", "openai", "claude-opus-5-5", "medium"),
    ],
)
def test_model_outside_the_section_7_1_table_or_off_its_config_is_refused(
    spec: ModelSpec,
) -> None:
    with pytest.raises(UnknownEffort):
        effort_for(spec)
    with pytest.raises(UnknownEffort):
        build(spec, _request(effort=spec.effort), KEY)


def test_max_output_over_cap_refused() -> None:
    build(SOL, _request(max_tokens=131072), KEY)
    with pytest.raises(MaxOutputTooLarge):
        build(SOL, _request(max_tokens=131073), KEY)


def test_unknown_effort_refused() -> None:
    with pytest.raises(UnknownEffort):
        build(SOL, _request(effort="extreme"), KEY)


@pytest.mark.parametrize(
    ("spec", "effort"),
    [(SOL, "max"), (OPUS, "high"), (DEEPSEEK, "medium")],
)
def test_effort_outside_the_section_7_1_uses_refused(spec: ModelSpec, effort: str) -> None:
    with pytest.raises(UnknownEffort):
        build(spec, _request(effort=effort), KEY)


def test_sol_high_is_admitted() -> None:
    build(SOL, _request(effort="high"), KEY)


@pytest.mark.parametrize("key", ["", "k\r\nX-Evil: 1", KEY + "\u200b", "has space", "k\u00e9y"])
def test_bad_key_refused_before_building(key: str) -> None:
    with pytest.raises(KeyMissing):
        build(SOL, _request(), key)


def test_mapper_stores_no_key() -> None:
    req = build(SOL, _request(), KEY)
    assert KEY not in repr(req)
    assert KEY.encode() not in req.body


# ------------------------------------------------------------------ parse


def _openai_reply(**over: Any) -> bytes:
    data: dict[str, Any] = {
        "id": "resp_1",
        "model": "gpt-6.1-sol-2026",
        "status": "completed",
        "output": [
            {"type": "reasoning", "summary": []},
            {
                "type": "function_call",
                "call_id": "c1",
                "name": "submit_x",
                "arguments": '{"a":1}',
            },
        ],
        "usage": {
            "input_tokens": 100,
            "input_tokens_details": {"cached_tokens": 40, "cache_write_tokens": 7},
            "output_tokens": 50,
            "output_tokens_details": {"reasoning_tokens": 0},
        },
    }
    data.update(over)
    return json.dumps(data).encode()


def test_openai_parse_tool_call() -> None:
    turn = parse("openai", 200, _openai_reply(), {}, Redactor())
    assert turn == Turn(
        text="",
        tool_calls=(ToolCall("c1", "submit_x", {"a": 1}),),
        usage=Usage(
            input_tokens=100,
            cached_read_tokens=40,
            cache_write_tokens=7,
            output_tokens=50,
            reasoning_tokens=0,
        ),
        stop_reason="tool_use",
        reported_model="gpt-6.1-sol-2026",
        request_id="resp_1",
        http_status=200,
        billed_usd=None,
    )


def test_openai_reasoning_absent_is_none() -> None:
    reply = _openai_reply(usage={"input_tokens": 1, "output_tokens": 2})
    turn = parse("openai", 200, reply, {}, Redactor())
    assert isinstance(turn, Turn)
    assert turn.usage.reasoning_tokens is None and turn.usage.cached_read_tokens is None


def test_openai_text_and_end() -> None:
    reply = _openai_reply(
        output=[{"type": "message", "content": [{"type": "output_text", "text": "done"}]}]
    )
    turn = parse("openai", 200, reply, {}, Redactor())
    assert isinstance(turn, Turn) and turn.text == "done" and turn.stop_reason == "end"


def test_openai_incomplete_is_max_tokens() -> None:
    reply = _openai_reply(
        output=[], status="incomplete", incomplete_details={"reason": "max_output_tokens"}
    )
    turn = parse("openai", 200, reply, {}, Redactor())
    assert isinstance(turn, Turn) and turn.stop_reason == "max_tokens"


def test_openai_malformed_arguments() -> None:
    reply = _openai_reply(
        output=[{"type": "function_call", "call_id": "c1", "name": "n", "arguments": "{bad"}]
    )
    err = parse("openai", 200, reply, {}, Redactor())
    assert isinstance(err, ProviderError)
    assert err.error_class == "MalformedToolArguments"
    assert err.usage is not None and err.usage.output_tokens == 50


def _sse(*events: dict[str, Any], stop: bool = True) -> bytes:
    lines = [f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events]
    if stop:
        lines.append('event: message_stop\ndata: {"type":"message_stop"}\n\n')
    return "".join(lines).encode()


START = {
    "type": "message_start",
    "message": {
        "id": "msg_1",
        "model": "claude-opus-5-5",
        "usage": {"input_tokens": 90, "output_tokens": 1},
    },
}
TOOL_BLOCK = [
    {
        "type": "content_block_start",
        "index": 0,
        "content_block": {"type": "tool_use", "id": "c1", "name": "submit_x", "input": {}},
    },
    {
        "type": "content_block_delta",
        "index": 0,
        "delta": {"type": "input_json_delta", "partial_json": '{"a":'},
    },
    {
        "type": "content_block_delta",
        "index": 0,
        "delta": {"type": "input_json_delta", "partial_json": "1}"},
    },
    {"type": "content_block_stop", "index": 0},
]
DELTA = {
    "type": "message_delta",
    "delta": {"stop_reason": "tool_use"},
    "usage": {
        "input_tokens": 90,
        "cache_creation_input_tokens": 30,
        "cache_read_input_tokens": 20,
        "cache_creation": {"ephemeral_5m_input_tokens": 10, "ephemeral_1h_input_tokens": 20},
        "output_tokens": 60,
        "output_tokens_details": {"thinking_tokens": 25},
    },
}


def test_anthropic_parse_stream_tool_call() -> None:
    body = _sse(
        {"type": "ping"},
        START,
        {"type": "content_block_start", "index": 1, "content_block": {"type": "text"}},
        {
            "type": "content_block_delta",
            "index": 1,
            "delta": {"type": "text_delta", "text": "ok"},
        },
        {"type": "content_block_stop", "index": 1},
        *TOOL_BLOCK,
        DELTA,
    )
    turn = parse("anthropic", 200, body, {}, Redactor())
    assert turn == Turn(
        text="ok",
        tool_calls=(ToolCall("c1", "submit_x", {"a": 1}),),
        usage=Usage(
            input_tokens=90,
            cached_read_tokens=20,
            cache_write_tokens=30,
            cache_write_5m_tokens=10,
            cache_write_1h_tokens=20,
            output_tokens=60,
            reasoning_tokens=25,
        ),
        stop_reason="tool_use",
        reported_model="claude-opus-5-5",
        request_id="msg_1",
        http_status=200,
        billed_usd=None,
    )


def test_anthropic_thinking_absent_is_none() -> None:
    delta = {
        "type": "message_delta",
        "delta": {"stop_reason": "end_turn"},
        "usage": {"output_tokens": 3},
    }
    turn = parse("anthropic", 200, _sse(START, delta), {}, Redactor())
    assert isinstance(turn, Turn)
    assert turn.usage.reasoning_tokens is None
    assert turn.usage.input_tokens == 90  # from message_start, kept
    assert turn.usage.cache_write_5m_tokens is None
    assert turn.stop_reason == "end"


def test_anthropic_malformed_tool_json() -> None:
    blocks = [dict(b) for b in TOOL_BLOCK]
    blocks[2] = {
        "type": "content_block_delta",
        "index": 0,
        "delta": {"type": "input_json_delta", "partial_json": "{bad"},
    }
    err = parse("anthropic", 200, _sse(START, *blocks, DELTA), {}, Redactor())
    assert isinstance(err, ProviderError) and err.error_class == "MalformedToolArguments"
    assert err.usage is not None


@pytest.mark.parametrize(
    ("reason", "error_class"),
    [
        ("refusal", "Refusal"),
        ("pause_turn", "PauseTurn"),
        ("model_context_window_exceeded", "ContextWindowExceeded"),
    ],
)
def test_anthropic_named_stop_reasons_are_errors(reason: str, error_class: str) -> None:
    delta = {
        "type": "message_delta",
        "delta": {"stop_reason": reason},
        "usage": {"output_tokens": 3},
    }
    err = parse("anthropic", 200, _sse(START, delta), {}, Redactor())
    assert isinstance(err, ProviderError) and err.error_class == error_class
    assert err.usage is not None


@pytest.mark.parametrize(
    ("reason", "expected"),
    [("max_tokens", "max_tokens"), ("stop_sequence", "other"), ("weird", "other")],
)
def test_anthropic_other_stop_reasons(reason: str, expected: str) -> None:
    delta = {
        "type": "message_delta",
        "delta": {"stop_reason": reason},
        "usage": {"output_tokens": 3},
    }
    turn = parse("anthropic", 200, _sse(START, delta), {}, Redactor())
    assert isinstance(turn, Turn) and turn.stop_reason == expected


def test_anthropic_cut_stream_without_usage_event_is_unknown() -> None:
    body = _sse(START, *TOOL_BLOCK[:2], stop=False)
    err = parse("anthropic", 200, body, {}, Redactor())
    assert isinstance(err, ProviderError)
    assert err.kind is ErrorKind.SENT_CHARGE_UNKNOWN and err.error_class == "StreamCut"
    assert err.usage is None


def test_anthropic_cut_stream_with_usage_event_settles_from_it() -> None:
    body = _sse(START, *TOOL_BLOCK, DELTA, stop=False)
    turn = parse("anthropic", 200, body, {}, Redactor())
    assert isinstance(turn, Turn) and turn.usage.output_tokens == 60


def test_anthropic_in_stream_error_is_unknown_charge() -> None:
    err_event = {"type": "error", "error": {"type": "overloaded_error", "message": "busy"}}
    err = parse("anthropic", 200, _sse(START, err_event, stop=False), {}, Redactor())
    assert isinstance(err, ProviderError)
    assert err.error_class == "overloaded_error" and "overloaded_error" in err.message
    assert err.kind is ErrorKind.SENT_CHARGE_UNKNOWN


def test_timeout_after_usage_event_is_settled_from_it() -> None:
    body = _sse(START, *TOOL_BLOCK, DELTA, stop=False)
    out = error_from_transport("anthropic", IdleTimeout("idle", body), Redactor())
    assert isinstance(out, Turn) and out.usage.output_tokens == 60


def _openrouter_reply(**over: Any) -> bytes:
    data: dict[str, Any] = {
        "id": "gen-1",
        "model": "deepseek/deepseek-v4.1-flash-1017",
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {"name": "submit_x", "arguments": '{"a":1}'},
                        }
                    ],
                },
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "completion_tokens_details": {"reasoning_tokens": 0},
            "prompt_tokens_details": {"cached_tokens": 10},
            "cost": 0.00123456789,
        },
    }
    data.update(over)
    return json.dumps(data).encode()


def test_openrouter_parse_tool_call_and_billed_cost() -> None:
    turn = parse("openrouter", 200, _openrouter_reply(), {}, Redactor())
    assert turn == Turn(
        text="",
        tool_calls=(ToolCall("c1", "submit_x", {"a": 1}),),
        usage=Usage(input_tokens=100, cached_read_tokens=10, output_tokens=50, reasoning_tokens=0),
        stop_reason="tool_use",
        reported_model="deepseek/deepseek-v4.1-flash-1017",
        request_id="gen-1",
        http_status=200,
        billed_usd=Decimal("0.00123456789"),
    )


def test_openrouter_malformed_arguments_and_absent_reasoning() -> None:
    bad = _openrouter_reply()
    bad = bad.replace(b'{\\"a\\":1}', b"{bad")
    err = parse("openrouter", 200, bad, {}, Redactor())
    assert isinstance(err, ProviderError) and err.error_class == "MalformedToolArguments"
    plain = _openrouter_reply(
        choices=[{"finish_reason": "stop", "message": {"content": "hi"}}],
        usage={"prompt_tokens": 1, "completion_tokens": 2},
    )
    turn = parse("openrouter", 200, plain, {}, Redactor())
    assert isinstance(turn, Turn)
    assert turn.usage.reasoning_tokens is None and turn.billed_usd is None
    assert turn.text == "hi" and turn.stop_reason == "end"


def test_inclusivity_constants() -> None:
    assert INCLUSIVITY["openai"].input_includes_cached_read is True
    assert INCLUSIVITY["openai"].output_includes_reasoning is True
    assert INCLUSIVITY["anthropic"].input_includes_cached_read is False
    assert INCLUSIVITY["anthropic"].output_includes_reasoning is True
    assert INCLUSIVITY["openrouter"].charge_from_reported_cost is True


# ------------------------------------------------------------------ classification

ERROR_OBJECT = b'{"error":{"code":400,"message":"bad"}}'


def test_5xx_is_unknown_with_or_without_error_object() -> None:
    assert classify(502, ERROR_OBJECT) is ErrorKind.SENT_CHARGE_UNKNOWN
    assert classify(502, b"") is ErrorKind.SENT_CHARGE_UNKNOWN
    err = parse("openai", 502, b"<html>bad gateway</html>", {}, Redactor())
    assert isinstance(err, ProviderError) and err.error_class == "ProviderServerError"
    assert err.kind is ErrorKind.SENT_CHARGE_UNKNOWN


def test_4xx_error_object_is_known() -> None:
    assert classify(400, ERROR_OBJECT) is ErrorKind.SENT_CHARGE_KNOWN
    anthropic = b'{"type":"error","error":{"type":"invalid_request_error","message":"x"}}'
    assert classify(400, anthropic) is ErrorKind.SENT_CHARGE_KNOWN


def test_4xx_unparsable_or_with_usage_is_unknown() -> None:
    assert classify(400, b"not json") is ErrorKind.SENT_CHARGE_UNKNOWN
    assert (
        classify(400, b'{"error":{},"usage":{"output_tokens":1}}') is ErrorKind.SENT_CHARGE_UNKNOWN
    )


def test_402_is_credit_exhausted_and_known() -> None:
    err = parse("openrouter", 402, ERROR_OBJECT, {"retry-after": "30"}, Redactor())
    assert isinstance(err, ProviderError)
    assert err.error_class == "CreditExhausted402" and err.kind is ErrorKind.SENT_CHARGE_KNOWN
    assert err.http_status == 402


def test_empty_200_body_is_unknown() -> None:
    providers: tuple[Provider, ...] = ("openai", "anthropic", "openrouter")
    for provider in providers:
        err = parse(provider, 200, b"", {}, Redactor())
        assert isinstance(err, ProviderError)
        assert err.kind is ErrorKind.SENT_CHARGE_UNKNOWN and err.error_class == "UnparsableReply"


def test_timeout_is_unknown_and_https_refusal_is_not_sent() -> None:
    timeout = error_from_transport("openai", IdleTimeout("idle"), Redactor())
    assert isinstance(timeout, ProviderError) and timeout.kind is ErrorKind.SENT_CHARGE_UNKNOWN
    assert timeout.error_class == "IdleTimeout"
    other = error_from_transport("openai", TransportError("network error: OSError"), Redactor())
    assert isinstance(other, ProviderError) and other.kind is ErrorKind.SENT_CHARGE_UNKNOWN
    refused = error_from_transport("openai", InsecureUrl("only https"), Redactor())
    assert isinstance(refused, ProviderError) and refused.kind is ErrorKind.NOT_SENT


def test_retry_after_is_capped_and_defaulted() -> None:
    assert retry_after_seconds({"retry-after": "30"}) == 30
    assert retry_after_seconds({"retry-after": "9999"}) == 300
    assert retry_after_seconds({}) == 120
    assert retry_after_seconds({"retry-after": "soon"}) == 120


# ------------------------------------------------------------------ key reflection


def test_key_in_error_body_is_redacted_and_flagged() -> None:
    body = json.dumps({"error": {"message": f"invalid key {KEY} given"}}).encode()
    err = parse("openai", 401, body, {}, Redactor([KEY]))
    assert isinstance(err, ProviderError) and err.error_class == "KeyReflected"
    assert KEY not in err.message and "[redacted]" in err.message
    assert KEY not in repr(err)


def test_exact_non_pattern_key_in_a_200_body_is_flagged() -> None:
    secret = "plain-secret-value-123"
    err = parse("openai", 200, _openai_reply(model=secret), {}, Redactor([secret]))
    assert isinstance(err, ProviderError) and err.error_class == "KeyReflected"
    assert secret not in repr(err)
    assert err.kind is ErrorKind.SENT_CHARGE_UNKNOWN


def test_key_in_a_header_is_flagged() -> None:
    err = parse("openai", 429, ERROR_OBJECT, {"x-echo": f"Bearer {KEY}"}, Redactor([KEY]))
    assert isinstance(err, ProviderError) and err.error_class == "KeyReflected"
    assert KEY not in repr(err)


def test_key_shape_is_flagged_by_a_regex_only_redactor() -> None:
    err = parse("openai", 401, KEY.encode(), {}, Redactor())
    assert isinstance(err, ProviderError) and err.error_class == "KeyReflected"


# ------------------------------------------------------------------ fix round 1


def _usage_kinds(err: object) -> ProviderError:
    assert isinstance(err, ProviderError)
    assert err.kind is ErrorKind.SENT_CHARGE_USAGE
    assert err.usage is not None
    return err


def test_error_kind_has_usage_member_and_invariants() -> None:
    assert ErrorKind.SENT_CHARGE_USAGE.value == "SentChargeUsage"
    with pytest.raises(ValueError):
        ProviderError(ErrorKind.SENT_CHARGE_USAGE, "x", "m")
    with pytest.raises(ValueError):
        ProviderError(ErrorKind.SENT_CHARGE_KNOWN, "x", "m", usage=Usage(output_tokens=1))


def test_usage_bearing_errors_are_sent_charge_usage() -> None:
    bad = _openai_reply(
        output=[{"type": "function_call", "call_id": "c", "name": "n", "arguments": "{bad"}]
    )
    assert _usage_kinds(parse("openai", 200, bad, {}, Redactor())).usage == Usage(
        input_tokens=100,
        cached_read_tokens=40,
        cache_write_tokens=7,
        output_tokens=50,
        reasoning_tokens=0,
    )
    for reason in ("refusal", "pause_turn", "model_context_window_exceeded"):
        delta = {
            "type": "message_delta",
            "delta": {"stop_reason": reason},
            "usage": {"output_tokens": 3},
        }
        _usage_kinds(parse("anthropic", 200, _sse(START, delta), {}, Redactor()))
    cut = _sse(START, *TOOL_BLOCK[:2], DELTA, stop=False)
    err = _usage_kinds(parse("anthropic", 200, cut, {}, Redactor()))
    assert err.error_class == "StreamCut"


def test_openai_refusal_part_is_a_usage_error() -> None:
    reply = _openai_reply(
        output=[{"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}]
    )
    err = _usage_kinds(parse("openai", 200, reply, {}, Redactor()))
    assert err.error_class == "Refusal"


def test_openrouter_malformed_arguments_keeps_cost() -> None:
    bad = _openrouter_reply().replace(b'{\\"a\\":1}', b"{bad")
    err = _usage_kinds(parse("openrouter", 200, bad, {}, Redactor()))
    assert err.error_class == "MalformedToolArguments"
    assert err.billed_usd == Decimal("0.00123456789")


def test_tool_arguments_keep_decimal_digits_and_refuse_nan() -> None:
    args = '{"a":2.50,"b":12345678901234567.89}'
    reply = _openai_reply(
        output=[{"type": "function_call", "call_id": "c", "name": "n", "arguments": args}]
    )
    turn = parse("openai", 200, reply, {}, Redactor())
    assert isinstance(turn, Turn)
    assert str(turn.tool_calls[0].arguments["a"]) == "2.50"
    assert str(turn.tool_calls[0].arguments["b"]) == "12345678901234567.89"
    nan = _openai_reply(
        output=[{"type": "function_call", "call_id": "c", "name": "n", "arguments": '{"d":NaN}'}]
    )
    err = parse("openai", 200, nan, {}, Redactor())
    assert isinstance(err, ProviderError) and err.error_class == "MalformedToolArguments"


def test_decimal_arguments_are_resent_exactly() -> None:
    from decimal import Decimal as D

    request = TurnRequest(
        (Message("user", "go"), Message("assistant", "", (ToolCall("c", "n", {"a": D("2.50")}),))),
        (),
        100,
        "medium",
    )
    assert b'"input":{"a":2.50}' in build(OPUS, request, KEY).body


def test_missing_call_id_or_name_is_unparsable() -> None:
    reply = _openai_reply(output=[{"type": "function_call", "arguments": "{}", "name": "n"}])
    err = parse("openai", 200, reply, {}, Redactor())
    assert isinstance(err, ProviderError) and err.error_class == "UnparsableReply"


def test_in_stream_error_class_is_the_error_type() -> None:
    event = {"type": "error", "error": {"type": "overloaded_error", "message": "busy"}}
    err = parse("anthropic", 200, _sse(START, event, stop=False), {}, Redactor())
    assert isinstance(err, ProviderError)
    assert err.error_class == "overloaded_error" and err.kind is ErrorKind.SENT_CHARGE_UNKNOWN


def test_sse_splits_on_newline_and_carriage_return_only() -> None:
    text = {
        "type": "content_block_delta",
        "index": 0,
        "delta": {"type": "text_delta", "text": "a\u2028b\x85c"},
    }
    body = (
        _sse(
            START,
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}},
            text,
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn"},
                "usage": {"output_tokens": 3},
            },
        )
        .replace(b"\\u2028", "\u2028".encode())
        .replace(b"\\u0085", "\x85".encode())
    )
    turn = parse("anthropic", 200, body, {}, Redactor())
    assert isinstance(turn, Turn) and turn.text == "a\u2028b\x85c"


def test_deeply_nested_reply_is_unparsable() -> None:
    providers: tuple[Provider, ...] = ("openai", "openrouter", "anthropic")
    for provider in providers:
        err = parse(provider, 200, b"[" * 200_000, {}, Redactor())
        assert isinstance(err, ProviderError) and err.error_class == "UnparsableReply"
    assert classify(400, b"[" * 200_000) is ErrorKind.SENT_CHARGE_UNKNOWN


THINK_EVENTS = [
    {
        "type": "content_block_start",
        "index": 0,
        "content_block": {"type": "thinking", "thinking": "", "signature": ""},
    },
    {
        "type": "content_block_delta",
        "index": 0,
        "delta": {"type": "thinking_delta", "thinking": "hm"},
    },
    {
        "type": "content_block_delta",
        "index": 0,
        "delta": {"type": "thinking_delta", "thinking": "m"},
    },
    {
        "type": "content_block_delta",
        "index": 0,
        "delta": {"type": "signature_delta", "signature": "SIG=="},
    },
    {"type": "content_block_stop", "index": 0},
    {
        "type": "content_block_start",
        "index": 1,
        "content_block": {"type": "redacted_thinking", "data": "OPAQUE"},
    },
    {"type": "content_block_stop", "index": 1},
]
THINK = (
    ProviderBlock("anthropic", {"type": "thinking", "thinking": "hmm", "signature": "SIG=="}),
    ProviderBlock("anthropic", {"type": "redacted_thinking", "data": "OPAQUE"}),
)


def test_anthropic_thinking_blocks_are_captured_in_order() -> None:
    shifted = [{**e, "index": 2} for e in TOOL_BLOCK]
    body = _sse(START, *THINK_EVENTS, *shifted, DELTA)
    turn = parse("anthropic", 200, body, {}, Redactor())
    assert isinstance(turn, Turn) and turn.provider_blocks == THINK
    assert turn.tool_calls == (ToolCall("c1", "submit_x", {"a": 1}),)


def test_anthropic_resends_thinking_blocks_unchanged_before_tool_use() -> None:
    request = TurnRequest(
        (
            Message("user", "go"),
            Message("assistant", "words", (ToolCall("c1", "n", {"a": 1}),), provider_blocks=THINK),
            Message("tool", "r", tool_call_id="c1"),
        ),
        TOOLS,
        100,
        "medium",
    )
    content = _body(build(OPUS, request, KEY))["messages"][1]["content"]
    assert content[0] == THINK[0].data and content[1] == THINK[1].data
    assert [b["type"] for b in content[2:]] == ["text", "tool_use"]


def test_other_providers_ignore_provider_blocks() -> None:
    request = TurnRequest(
        (Message("user", "go"), Message("assistant", "words", provider_blocks=THINK)),
        TOOLS,
        100,
        "medium",
    )
    assert "SIG==" not in build(SOL, request, KEY).body.decode()
    assert "SIG==" not in build(DEEPSEEK, replace_effort(request), KEY).body.decode()


def replace_effort(request: TurnRequest) -> TurnRequest:
    return TurnRequest(request.messages, request.tools, request.max_output_tokens, "max")


def test_key_split_across_deltas_or_escaped_is_flagged() -> None:
    red = Redactor([KEY])
    split = _sse(
        START,
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}},
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": KEY[:4]},
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": KEY[4:]},
        },
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn"},
            "usage": {"output_tokens": 3},
        },
    )
    err = parse("anthropic", 200, split, {}, red)
    assert isinstance(err, ProviderError) and err.error_class == "KeyReflected"
    assert KEY not in repr(err)
    escaped = json.dumps({"error": {"message": KEY}}).replace("sk-", "\\u0073k-").encode()
    assert KEY.encode() not in escaped
    err = parse("openai", 401, escaped, {}, red)
    assert isinstance(err, ProviderError) and err.error_class == "KeyReflected"
    assert KEY not in repr(err)
    think = _sse(
        START,
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "thinking", "thinking": ""},
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "thinking_delta", "thinking": KEY[:5]},
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "thinking_delta", "thinking": KEY[5:]},
        },
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn"},
            "usage": {"output_tokens": 3},
        },
    )
    err = parse("anthropic", 200, think, {}, red)
    assert isinstance(err, ProviderError) and err.error_class == "KeyReflected"


# ------------------------------------------------------------ fix 3: every exit guards what it decoded

ANT = "sk-ant-" + "W" * 40  # test-only
_TEXT_START = {"type": "content_block_start", "index": 0, "content_block": {"type": "text"}}
_SIG_START = {
    "type": "content_block_start",
    "index": 0,
    "content_block": {"type": "thinking", "thinking": "", "signature": ""},
}
_ERROR_EVENT = {"type": "error", "error": {"type": "overloaded_error", "message": "busy"}}
_END_DELTA = {
    "type": "message_delta",
    "delta": {"stop_reason": "end_turn"},
    "usage": {"output_tokens": 3},
}
_STOP_0 = {"type": "content_block_stop", "index": 0}


def _delta(kind: str, field: str, value: str) -> dict[str, Any]:
    return {"type": "content_block_delta", "index": 0, "delta": {"type": kind, field: value}}


def _text_split(key: str = KEY, at: int = 4) -> list[dict[str, Any]]:
    return [
        START,
        _TEXT_START,
        _delta("text_delta", "text", key[:at]),
        _delta("text_delta", "text", key[at:]),
    ]


def _keyreflected(body: bytes, red: Redactor, provider: Provider = "anthropic") -> ProviderError:
    err = parse(provider, 200, body, {}, red)
    assert isinstance(err, ProviderError), err
    assert err.error_class == "KeyReflected", err
    assert KEY not in repr(err) and ANT not in repr(err)
    return err


def test_split_key_then_error_event_is_key_reflected() -> None:
    _keyreflected(_sse(*_text_split(), _ERROR_EVENT, stop=False), Redactor([KEY]))


def test_split_key_then_stream_cut_is_key_reflected() -> None:
    _keyreflected(_sse(*_text_split(), _STOP_0), Redactor([KEY]))


def test_split_key_then_refusal_keeps_kind_and_usage() -> None:
    refusal = {**_END_DELTA, "delta": {"stop_reason": "refusal"}}
    err = _keyreflected(_sse(*_text_split(), _STOP_0, refusal), Redactor([KEY]))
    assert err.kind is ErrorKind.SENT_CHARGE_USAGE
    assert err.usage is not None and err.usage.output_tokens == 3


def test_split_signature_then_error_event_is_key_reflected() -> None:
    events: list[dict[str, Any]] = [
        START,
        _SIG_START,
        _delta("signature_delta", "signature", KEY[:5]),
        _delta("signature_delta", "signature", KEY[5:]),
        _ERROR_EVENT,
    ]
    _keyreflected(_sse(*events, stop=False), Redactor([KEY]))


def test_split_key_with_w_in_the_second_fragment_then_error_event() -> None:
    events = [*_text_split(ANT, 5), _ERROR_EVENT]
    _keyreflected(_sse(*events, stop=False), Redactor())


def test_escaped_key_in_one_delta_then_error_event() -> None:
    body = _sse(START, _TEXT_START, _delta("text_delta", "text", ANT), _ERROR_EVENT, stop=False)
    escaped = body.replace(b"sk-ant", b"\\u0073k-ant")
    assert ANT.encode() not in escaped
    _keyreflected(escaped, Redactor())


def test_key_cut_mid_event_is_joined_with_the_open_string() -> None:
    head = _sse(START, _TEXT_START, _delta("text_delta", "text", ANT[:5]), stop=False)
    tail = (
        b"event: content_block_delta\n"
        b'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"'
        + ANT[5:].encode()
    )
    _keyreflected(head + tail, Redactor())


def test_key_split_across_events_after_message_stop() -> None:
    events: list[dict[str, Any]] = [
        START,
        _TEXT_START,
        _STOP_0,
        _END_DELTA,
        {"type": "message_stop"},
        _delta("text_delta", "text", ANT[:5]),
        _delta("text_delta", "text", ANT[5:]),
    ]
    _keyreflected(_sse(*events, stop=False), Redactor())


def test_openai_split_output_text_then_refusal_keeps_kind_and_usage() -> None:
    def message(*parts: dict[str, Any]) -> dict[str, Any]:
        return {"type": "message", "content": list(parts)}

    reply = _openai_reply(
        output=[
            message(
                {"type": "output_text", "text": KEY[:5]},
                {"type": "output_text", "text": KEY[5:]},
                {"type": "refusal", "refusal": "no"},
            )
        ]
    )
    err = _keyreflected(reply, Redactor([KEY]), "openai")
    assert err.kind is ErrorKind.SENT_CHARGE_USAGE and err.usage is not None


@pytest.mark.parametrize("settled", [False, True], ids=["before-usage", "after-usage"])
def test_idle_partial_with_a_split_key_is_key_reflected(settled: bool) -> None:
    events = [*_text_split(), _STOP_0, *([_END_DELTA] if settled else [])]
    cut = IdleTimeout("idle", _sse(*events, stop=False))
    err = error_from_transport("anthropic", cut, Redactor([KEY]))
    assert isinstance(err, ProviderError) and err.error_class == "KeyReflected"
    assert KEY not in repr(err)


def test_clean_streams_still_parse_and_keep_their_class() -> None:
    clean = _sse(
        START,
        _TEXT_START,
        _delta("text_delta", "text", "hel"),
        _delta("text_delta", "text", "lo"),
        _delta("text_delta", "text", "café"),
        _STOP_0,
        _SIG_START | {"index": 1},
        {**_delta("signature_delta", "signature", "abcDEF"), "index": 1},
        {**_delta("signature_delta", "signature", "123=="), "index": 1},
        {"type": "content_block_stop", "index": 1},
        _END_DELTA,
    )
    turn = parse("anthropic", 200, clean, {}, Redactor([KEY]))
    assert isinstance(turn, Turn) and turn.text == "hellocafé"
    err = parse("anthropic", 200, _sse(START, _ERROR_EVENT, stop=False), {}, Redactor([KEY]))
    assert isinstance(err, ProviderError) and err.error_class == "overloaded_error"
