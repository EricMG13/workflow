"""Turn types and the recording response format. No network, no environment."""

import json
from decimal import Decimal

import pytest

from deploy_workflow.model.turn import (
    CONFIG_MODELS,
    CONFIG_PROVIDERS,
    Message,
    ModelSpec,
    Provider,
    ProviderBlock,
    ToolCall,
    Turn,
    TurnError,
    Usage,
    load_json,
    turn_from_json,
    turn_to_json,
)


def _turn(text: str = "hi", status: int = 200) -> Turn:
    return Turn(
        text=text,
        tool_calls=(ToolCall("c1", "submit_x", {"a": 1}),),
        usage=Usage(input_tokens=10, output_tokens=5, reasoning_tokens=0),
        stop_reason="tool_use",
        reported_model="m",
        request_id="r1",
        http_status=status,
        billed_usd=Decimal("0.0012"),
    )


def test_config_providers_are_the_four_section_7_1_ids() -> None:
    assert dict(CONFIG_PROVIDERS) == {
        "sol-medium": "openai",
        "sol-high": "openai",
        "opus-medium": "anthropic",
        "deepseek-max": "openrouter",
    }


def test_spec_refuses_provider_that_disagrees_with_config() -> None:
    ModelSpec("opus-medium", "anthropic", "claude-opus-5-5", "medium")
    with pytest.raises(TurnError):
        ModelSpec("opus-medium", "openai", "claude-opus-5-5", "medium")


def test_unreported_usage_is_none_not_zero() -> None:
    assert Usage().reasoning_tokens is None
    assert Usage(reasoning_tokens=0).reasoning_tokens == 0


def test_negative_count_refused() -> None:
    with pytest.raises(TurnError):
        Usage(input_tokens=-1)


def test_tool_message_needs_call_id() -> None:
    with pytest.raises(TurnError):
        Message("tool", "result")


def test_round_trip() -> None:
    turn = _turn()
    wire = turn_to_json(turn)
    assert wire["billed_usd"] == "0.0012"
    assert turn_from_json(wire) == turn


def test_missing_http_status_refused() -> None:
    wire = turn_to_json(_turn())
    del wire["http_status"]
    with pytest.raises(TurnError, match="http_status"):
        turn_from_json(wire)


def test_unknown_key_refused() -> None:
    wire = turn_to_json(_turn())
    wire["extra"] = 1
    with pytest.raises(TurnError, match="extra"):
        turn_from_json(wire)


def test_negative_count_in_recording_refused() -> None:
    wire = turn_to_json(_turn())
    wire["usage"]["output_tokens"] = -3
    with pytest.raises(TurnError):
        turn_from_json(wire)


def test_unknown_usage_key_refused() -> None:
    wire = turn_to_json(_turn())
    wire["usage"]["bogus"] = 1
    with pytest.raises(TurnError, match="bogus"):
        turn_from_json(wire)


def test_config_models_cover_the_same_four_ids() -> None:
    assert dict(CONFIG_MODELS) == {
        "sol-medium": "gpt-6.1-sol",
        "sol-high": "gpt-6.1-sol",
        "opus-medium": "claude-opus-5-5",
        "deepseek-max": "deepseek/deepseek-v4.1-flash-1017",
    }
    assert set(CONFIG_MODELS) == set(CONFIG_PROVIDERS)


def test_decimal_tool_arguments_round_trip_losslessly() -> None:
    args = {"a": Decimal("2.50"), "b": Decimal("12345678901234567.89"), "n": [Decimal("0.1"), 3]}
    turn = Turn("", (ToolCall("c1", "n", args),), Usage(), "tool_use", None, None, 200, None)
    wire = json.loads(json.dumps(turn_to_json(turn)))
    assert wire["tool_calls"][0]["arguments"] == '{"a":2.50,"b":12345678901234567.89,"n":[0.1,3]}'
    back = turn_from_json(wire)
    assert back == turn
    assert str(back.tool_calls[0].arguments["a"]) == "2.50"
    assert str(back.tool_calls[0].arguments["b"]) == "12345678901234567.89"


@pytest.mark.parametrize("text", ['{"a":NaN}', '{"a":Infinity}', '{"a":-Infinity}', "[1]", "{bad"])
def test_recording_with_bad_arguments_refused(text: str) -> None:
    wire = turn_to_json(_turn())
    wire["tool_calls"][0]["arguments"] = text
    with pytest.raises(TurnError):
        turn_from_json(wire)


def test_provider_blocks_round_trip_in_order() -> None:
    blocks = (
        ProviderBlock("anthropic", {"type": "thinking", "thinking": "a", "signature": "s1"}),
        ProviderBlock("anthropic", {"type": "redacted_thinking", "data": "xyz"}),
    )
    turn = Turn("", (), Usage(), "end", None, None, 200, None, blocks)
    wire = json.loads(json.dumps(turn_to_json(turn)))
    assert [b["data"]["type"] for b in wire["provider_blocks"]] == ["thinking", "redacted_thinking"]
    assert turn_from_json(wire) == turn


def test_provider_blocks_key_is_required_and_exact() -> None:
    wire = turn_to_json(_turn())
    del wire["provider_blocks"]
    with pytest.raises(TurnError, match="provider_blocks"):
        turn_from_json(wire)
    wire = turn_to_json(_turn())
    wire["provider_blocks"] = [{"provider": "anthropic", "data": {}, "extra": 1}]
    with pytest.raises(TurnError, match="extra"):
        turn_from_json(wire)


def test_only_assistant_message_carries_provider_blocks() -> None:
    block = ProviderBlock("anthropic", {"type": "thinking", "thinking": "", "signature": ""})
    Message("assistant", "", provider_blocks=(block,))
    with pytest.raises(TurnError):
        Message("user", "x", provider_blocks=(block,))


@pytest.mark.parametrize(
    ("config", "provider", "model", "effort"),
    [
        ("sol-medium", "openai", "gpt-6.1-sol-mini", "medium"),
        ("sol-medium", "openai", "gpt-6.1-sol", "max"),
        ("opus-medium", "anthropic", "claude-opus-5-5", "high"),
        ("sol-medium", "openai", "claude-opus-5-5", "medium"),
        ("x", "openrouter", "mistralai/some-model", "high"),
    ],
)
def test_spec_refuses_pair_outside_the_section_7_1_table(
    config: str, provider: Provider, model: str, effort: str
) -> None:
    with pytest.raises(TurnError):
        ModelSpec(config, provider, model, effort)


def test_spec_accepts_the_section_7_1_pairs() -> None:
    ModelSpec("sol-high", "openai", "gpt-6.1-sol", "high")
    ModelSpec("deepseek-max", "openrouter", "deepseek/deepseek-v4.1-flash-1017", "max")


def test_load_json_maps_deep_nesting_to_turn_error() -> None:
    with pytest.raises(TurnError):
        load_json("[" * 100_000)
