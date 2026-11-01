"""Turn types and the recording response format. No network, no environment."""

from decimal import Decimal

import pytest

from deploy_workflow.model.turn import (
    CONFIG_PROVIDERS,
    Message,
    ModelSpec,
    ToolCall,
    Turn,
    TurnError,
    Usage,
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
