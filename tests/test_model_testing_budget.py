from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from deploy_workflow.model.record import CallRecord
from deploy_workflow.model_testing.budget import (
    AccountExhausted,
    Runs,
    account_spend,
    cap_for,
    require_budget,
)
from deploy_workflow.model_testing.configs import CONFIGS
from deploy_workflow.model_testing.records import RunMeta

NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


def call(
    config_id: str,
    settled: str | None,
    reserved: str = "1",
    status: str = "computed",
    index: int = 0,
) -> CallRecord:
    config = CONFIGS[config_id]
    body: dict[str, Any] = {
        "schema_version": "model-call/1",
        "run_id": "run-1",
        "case_id": "case-1",
        "pathway": "credit_snapshot",
        "module_id": "CP-1",
        "step_id": "step-1",
        "attempt": 0,
        "call_index": index,
        "config_id": config_id,
        "provider": config.provider,
        "requested_model": config.model,
        "reported_model": config.model,
        "requested_effort": config.effort,
        "invocation_digest": "a" * 64,
        "request_id": "req-1",
        "http_status": 200,
        "started_at": NOW,
        "first_byte_at": None,
        "finished_at": NOW,
        "input_tokens": 10,
        "cached_read_tokens": None,
        "cache_write_tokens": None,
        "output_tokens": 5,
        "reasoning_tokens": None,
        "reserved_usd": Decimal(reserved),
        "settled_usd": None if settled is None else Decimal(settled),
        "cost_status": status,
        "tool_calls": (),
        "submit_sha256": None,
        "error_class": None,
        "error": None,
    }
    return CallRecord(**body)


def meta(mode: Literal["offline", "live"] = "live", config_id: str = "sol-medium") -> RunMeta:
    live = mode == "live"
    return RunMeta(
        case_id="case-1",
        pathway="credit_snapshot",
        config_id=config_id,
        run_id="run-1",
        mode=mode,
        cap_usd=Decimal("1.50"),
        sources=(),
        cp_dr_invoked=False,
        replayed_from_run=None,
        outcome="settled",
        stopped_reason=None,
        ruling_path="r.md" if live else None,
        ruling_sha256="b" * 64 if live else None,
        ruling_date="2026-11-01" if live else None,
    )


def runs() -> list[tuple[RunMeta, list[CallRecord]]]:
    return [
        (
            meta(),
            [
                call("sol-medium", "10.50"),
                call("sol-high", None, reserved="3.25", status="unknown", index=1),
            ],
        ),
        (meta(config_id="opus-medium"), [call("opus-medium", "9.00")]),
        (meta(config_id="deepseek-max"), [call("deepseek-max", "18.40")]),
    ]


def test_spend_sums_settled_and_unknown() -> None:
    assert account_spend(runs(), "openai") == Decimal("13.75")
    assert account_spend(runs(), "anthropic") == Decimal("9.00")


def test_shared_account() -> None:
    assert cap_for("sol-high", runs()) == Decimal("117.00") - Decimal("13.75")
    assert cap_for("sol-medium", runs()) == cap_for("sol-high", runs())


def test_cap_floor_zero() -> None:
    assert cap_for("deepseek-max", runs()) == Decimal(0)


def test_require_budget_raises() -> None:
    with pytest.raises(AccountExhausted, match="deepseek-max") as info:
        require_budget("deepseek-max", runs(), Decimal("0.01"))
    assert "openrouter" in str(info.value)
    assert "0.01" in str(info.value)


def test_require_budget_returns_cap() -> None:
    assert require_budget("opus-medium", runs(), Decimal(5)) == Decimal("126.00")
    assert require_budget("deepseek-max", runs(), Decimal(0)) == Decimal(0)


def test_offline_runs_not_counted() -> None:
    offline: tuple[RunMeta, list[CallRecord]] = (meta("offline"), [call("sol-medium", "50.00")])
    assert account_spend([*runs(), offline], "openai") == Decimal("13.75")


def test_unknown_config_raises_keyerror() -> None:
    with pytest.raises(KeyError, match="nope"):
        cap_for("nope", runs())
    with pytest.raises(KeyError, match="nope"):
        require_budget("nope", runs(), Decimal(1))


def test_negative_needed_raises() -> None:
    with pytest.raises(ValueError):
        require_budget("sol-medium", runs(), Decimal(-1))


@given(
    st.lists(
        st.decimals(min_value=0, max_value=500, places=4, allow_nan=False, allow_infinity=False)
    )
)
def test_spend_is_exact_sum_and_cap_never_negative(amounts: list[Decimal]) -> None:
    records = [call("sol-medium", str(a), index=i) for i, a in enumerate(amounts)]
    batch: Runs = [(meta(), records)]
    assert account_spend(batch, "openai") == sum(amounts, Decimal(0))
    assert cap_for("sol-medium", batch) >= 0
