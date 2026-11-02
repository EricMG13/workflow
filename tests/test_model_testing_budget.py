from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, Literal

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from deploy_workflow.model.record import CallRecord
from deploy_workflow.model_testing.budget import (
    AccountExhausted,
    Runs,
    Settlement,
    UnknownCharge,
    account_spend,
    cap_for,
    load_settlements,
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
    run_id: str = "run-1",
    provider: str | None = None,
) -> CallRecord:
    config = CONFIGS[config_id]
    body: dict[str, Any] = {
        "schema_version": "model-call/1",
        "run_id": run_id,
        "case_id": "case-1",
        "pathway": "credit_snapshot",
        "module_id": "CP-1",
        "step_id": "step-1",
        "attempt": 0,
        "call_index": index,
        "config_id": config_id,
        "provider": provider or config.provider,
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


def meta(
    mode: Literal["offline", "live"] = "live", config_id: str = "sol-medium", run_id: str = "run-1"
) -> RunMeta:
    live = mode == "live"
    return RunMeta(
        case_id="case-1",
        pathway="credit_snapshot",
        config_id=config_id,
        run_id=run_id,
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
        (meta(), [call("sol-medium", "10.50")]),
        (
            meta(config_id="sol-high", run_id="run-2"),
            [call("sol-high", None, reserved="3.25", status="unknown", run_id="run-2")],
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


def test_unknown_charge_stops_configuration() -> None:
    with pytest.raises(UnknownCharge, match="sol-high") as info:
        require_budget("sol-high", runs(), Decimal(1))
    assert "run-2" in str(info.value)
    assert isinstance(info.value, AccountExhausted)
    # spend and cap still count the full reservation
    assert account_spend(runs(), "openai") == Decimal("13.75")
    # a sibling configuration on the same account is not stopped
    assert require_budget("sol-medium", runs(), Decimal(1)) == Decimal("103.25")


def test_unknown_charge_offline_does_not_stop() -> None:
    offline = (
        meta("offline", "sol-high", "run-3"),
        [call("sol-high", None, status="unknown", run_id="run-3")],
    )
    assert require_budget("sol-high", [offline], Decimal(1)) == Decimal(117)


@pytest.mark.parametrize(
    ("settled", "reserved", "status"),
    [("-50", "1", "computed"), (None, "-40", "unknown"), ("1", "-1", "computed")],
)
def test_negative_money_refused(settled: str | None, reserved: str, status: str) -> None:
    with pytest.raises(ValidationError):
        call("sol-medium", settled, reserved=reserved, status=status)
    # CallRecord refuses negatives itself; model_copy models a record that bypassed it.
    valid = call(
        "sol-medium",
        None if settled is None else str(abs(Decimal(settled))),
        reserved=str(abs(Decimal(reserved))),
        status=status,
    )
    bad = valid.model_copy(
        update={
            "settled_usd": None if settled is None else Decimal(settled),
            "reserved_usd": Decimal(reserved),
        }
    )
    batch: Runs = [(meta(), [bad])]
    with pytest.raises(ValueError, match=r"run-1.*CP-1.*step-1.*0"):
        account_spend(batch, "openai")
    with pytest.raises(ValueError, match="run-1"):
        cap_for("sol-medium", batch)


@pytest.mark.parametrize(
    ("settled", "reserved", "status", "field"),
    [
        ("-50", "1", "computed", "settled_usd"),
        (None, "-40", "unknown", "reserved_usd"),
        ("1", "-1", "computed", "reserved_usd"),
    ],
)
def test_call_record_refuses_negative_money(
    settled: str | None, reserved: str, status: str, field: str
) -> None:
    with pytest.raises(ValidationError, match=field):
        call("sol-medium", settled, reserved=reserved, status=status)


@pytest.mark.parametrize("text", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_money_refused(text: str) -> None:
    # CallRecord refuses these itself; model_construct models a record that bypassed it.
    bad = call("sol-medium", "1").model_copy(update={"settled_usd": Decimal(text)})
    batch: Runs = [(meta(), [bad])]
    with pytest.raises(ValueError, match="run-1"):
        cap_for("sol-medium", batch)


def test_result_independent_of_ambient_context() -> None:
    batch: Runs = [(meta(), [call("sol-medium", "13.7500000000000000000000000001")])]
    with localcontext() as ctx:
        ctx.prec = 100
        want = Decimal("117.00") - Decimal("13.7500000000000000000000000001")
    assert cap_for("sol-medium", batch) == want
    with localcontext() as ctx:
        ctx.prec = 2
        assert cap_for("sol-medium", [(meta(), [call("sol-medium", "13.75")])]) == Decimal("103.25")


def test_provider_mismatch_refused() -> None:
    batch: Runs = [(meta(), [call("sol-medium", "9", provider="openrouter")])]
    with pytest.raises(ValueError, match="provider"):
        account_spend(batch, "openai")


def test_run_config_mismatch_refused() -> None:
    batch: Runs = [(meta(config_id="sol-medium"), [call("deepseek-max", "9")])]
    with pytest.raises(ValueError, match="config_id"):
        account_spend(batch, "openrouter")


# ------------------------------------------------------------------ settlements (ruling 2026-11-01)


def settle(run_id: str = "run-2", call_index: int = 0, amount: str = "1.00") -> Settlement:
    return Settlement(
        run_id=run_id,
        call_index=call_index,
        settled_usd=Decimal(amount),
        by="eric",
        date="2026-11-01",
        source="provider invoice",
    )


def test_settlement_replaces_the_reservation_and_releases_the_stop() -> None:
    # run-2 holds an unknown charge reserved at 3.25; the user settled it at 1.00
    assert account_spend(runs(), "openai") == Decimal("13.75")
    assert account_spend(runs(), "openai", [settle()]) == Decimal("11.50")
    assert cap_for("sol-high", runs(), [settle()]) == Decimal("117.00") - Decimal("11.50")
    assert require_budget("sol-high", runs(), Decimal(1), [settle()]) == Decimal("105.50")
    with pytest.raises(UnknownCharge):  # without it the configuration stays stopped
        require_budget("sol-high", runs(), Decimal(1))


def test_settlement_amount_may_exceed_the_reservation() -> None:
    assert account_spend(runs(), "openai", [settle(amount="9.00")]) == Decimal("19.50")


def test_settlement_of_a_known_charge_refused() -> None:
    batch: Runs = [(meta(), [call("sol-medium", "10.50")])]
    with pytest.raises(ValueError, match=r"run run-1 call 0.*not unknown"):
        account_spend(batch, "openai", [settle("run-1", 0)])


def test_settlement_matching_no_record_refused() -> None:
    with pytest.raises(ValueError, match=r"run run-2 call 7.*no record"):
        account_spend(runs(), "openai", [settle("run-2", 7)])
    with pytest.raises(ValueError, match=r"run nope call 0"):
        cap_for("sol-high", runs(), [settle("nope", 0)])


def test_duplicate_settlement_refused() -> None:
    with pytest.raises(ValueError, match=r"run run-2 call 0.*duplicate"):
        require_budget("sol-high", runs(), Decimal(1), [settle(), settle(amount="2")])


@pytest.mark.parametrize("amount", ["-0.01", "NaN", "Infinity"])
def test_negative_or_non_finite_settlement_refused(amount: str) -> None:
    # the model refuses NaN itself; model_copy models a settlement that bypassed it
    bad = settle().model_copy(update={"settled_usd": Decimal(amount)})
    with pytest.raises(ValueError, match=r"run run-2 call 0"):
        account_spend(runs(), "openai", [bad])


def test_settlement_matching_two_records_refused() -> None:
    twin = call("sol-high", None, reserved="1", status="unknown", index=0, run_id="run-2")
    batch: Runs = [(meta(config_id="sol-high", run_id="run-2"), [twin, twin])]
    with pytest.raises(ValueError, match=r"run run-2 call 0.*2 records"):
        account_spend(batch, "openai", [settle()])


def test_offline_settled_record_does_not_count() -> None:
    offline = (
        meta("offline", "sol-high", "run-3"),
        [call("sol-high", None, reserved="5", status="unknown", run_id="run-3")],
    )
    assert account_spend([offline], "openai", [settle("run-3", 0, "4")]) == Decimal(0)


def test_load_settlements(tmp_path: Path) -> None:
    path = tmp_path / "settlements.json"
    assert load_settlements(path) == ()  # no file, no settlements
    entry = {
        "run_id": "run-2",
        "call_index": 0,
        "settled_usd": "1.00",
        "by": "eric",
        "date": "2026-11-01",
        "source": "invoice",
    }
    path.write_text(json.dumps({"schema_version": "charge-settlement/1", "entries": [entry]}))
    assert load_settlements(path) == (settle(),)


@pytest.mark.parametrize(
    "edit",
    [
        {"by": ""},
        {"source": ""},
        {"date": "11/01/2026"},
        {"settled_usd": "NaN"},
        {"extra": 1},
    ],
)
def test_load_settlements_refuses_bad_entries(tmp_path: Path, edit: dict[str, Any]) -> None:
    entry = {
        "run_id": "run-2",
        "call_index": 0,
        "settled_usd": "1.00",
        "by": "eric",
        "date": "2026-11-01",
        "source": "invoice",
        **edit,
    }
    path = tmp_path / "settlements.json"
    path.write_text(json.dumps({"schema_version": "charge-settlement/1", "entries": [entry]}))
    with pytest.raises(ValueError, match="settlements.json"):
        load_settlements(path)


def test_load_settlements_refuses_a_wrong_schema(tmp_path: Path) -> None:
    path = tmp_path / "settlements.json"
    path.write_text(json.dumps({"schema_version": "charge-settlement/2", "entries": []}))
    with pytest.raises(ValueError, match="settlements.json"):
        load_settlements(path)
