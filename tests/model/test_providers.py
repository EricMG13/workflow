"""Mappers, effort map, classification and the key-reflection guard. No network."""

import http.client
import json
import socket
from decimal import Decimal
from typing import Any, cast

import pytest

from deploy_workflow.model.providers import (
    INCLUSIVITY,
    ErrorKind,
    KeyMissing,
    MaxOutputTooLarge,
    ProviderError,
    UnknownEffort,
    build,
    classify,
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


def test_other_openrouter_id_has_no_provider_ignore() -> None:
    other = ModelSpec("x", "openrouter", "mistralai/some-model", "high")
    assert "provider" not in _body(build(other, _request(effort="high"), KEY))


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


@pytest.mark.parametrize("key", ["", "k\r\nX-Evil: 1"])
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
    assert err.error_class == "StreamError" and "overloaded_error" in err.message
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
