"""Price table, reservation and charge. No network, no environment."""

import ast
import inspect
import json
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from deploy_workflow.model import budget as budget_module
from deploy_workflow.model import pricing as pricing_module
from deploy_workflow.model.pricing import (
    PRICES,
    ContextTooLong,
    ModelPrice,
    NoPrice,
    Priced,
    PricingError,
    computed_usd,
    money_text,
    price_of,
    price_usage,
    refusal_values,
    reservation_usd,
)
from deploy_workflow.model.providers import parse
from deploy_workflow.model.redact import Redactor
from deploy_workflow.model.turn import CONFIG_PROVIDERS, Turn, Usage

D = Decimal

KEY_FILE = Path(__file__).parents[2] / "cases" / "pricing" / "openai-sol-cache-write.json"


def _key() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(KEY_FILE.read_text(encoding="utf-8"))
    return loaded


def _live_usage(raw_usage: dict[str, Any]) -> Usage:
    """The usage the live OpenAI adapter parses from a reply carrying ``raw_usage``."""
    reply = {
        "id": "resp_key",
        "model": "gpt-6.1-sol",
        "status": "completed",
        "output": [
            {"type": "function_call", "call_id": "c1", "name": "submit_x", "arguments": "{}"}
        ],
        "usage": raw_usage,
    }
    turn = parse("openai", 200, json.dumps(reply).encode(), {}, Redactor())
    assert isinstance(turn, Turn)
    return turn.usage


def test_reservation_uses_the_cache_write_rate_when_dearer() -> None:
    assert reservation_usd(ModelPrice(input=D(2), cache_write=D(5), output=D(8)), 1000, 100) == D(
        "0.0058"
    )
    assert reservation_usd(ModelPrice(input=D(2), cache_write=D(1), output=D(8)), 1000, 100) == D(
        "0.0028"
    )


@given(
    st.integers(0, 10_000),
    st.integers(0, 10_000),
    st.integers(0, 10_000),
    st.integers(0, 10**6),
    st.integers(0, 10**6),
)
def test_reservation_equals_exact_fraction(i: int, w: int, o: int, n_in: int, n_out: int) -> None:
    price = ModelPrice(input=D(i) / 1000, cache_write=D(w) / 1000, output=D(o) / 1000)
    expected = (n_in * Fraction(max(i, w), 1000) + n_out * Fraction(o, 1000)) / 10**6
    got = reservation_usd(price, n_in, n_out)
    assert Fraction(got) == expected


def test_table_is_the_four_configs_dated() -> None:
    assert set(PRICES) == set(CONFIG_PROVIDERS)
    assert pricing_module.PRICES_AS_OF.isoformat() == "2026-10-31"
    sol = PRICES["sol-medium"]
    key = _key()["sol"]
    rates = key["usd_per_million"]
    assert (sol.input, sol.cached_read, sol.cache_write, sol.output) == (
        D(rates["input"]),
        D(rates["cached_read"]),
        D(rates["cache_write_30m"]),
        D(rates["output"]),
    )
    assert sol.max_input_tokens == key["max_input_tokens"]
    assert PRICES["sol-high"] == sol
    opus = PRICES["opus-medium"]
    assert (opus.input, opus.cached_read, opus.output) == (D(4), D("0.2"), D(20))
    assert (opus.cache_write_5m, opus.cache_write_1h, opus.cache_write) == (D(5), D(8), D(8))
    ds = PRICES["deepseek-max"]
    assert (ds.input, ds.cached_read, ds.output) == (D("0.45"), D("0.009"), D("1.8"))


def test_unlisted_config_has_no_price() -> None:
    with pytest.raises(NoPrice):
        price_of("opus-high")
    with pytest.raises(NoPrice):
        price_usage("opus-high", Usage(input_tokens=1, output_tokens=1))


def test_sol_over_272k_input_is_refused() -> None:
    sol = PRICES["sol-medium"]
    k = _key()["reservation_at_max_input"]
    assert reservation_usd(sol, k["input_tokens"], k["max_output"]) == D(k["usd"])
    with pytest.raises(ContextTooLong):
        reservation_usd(sol, 272_001, 0)


def test_no_float_in_money() -> None:
    with pytest.raises(PricingError):
        ModelPrice(input=2.0, cache_write=1, output=1)  # type: ignore[arg-type]
    with pytest.raises(PricingError):
        reservation_usd(PRICES["sol-high"], 1.5, 1)  # type: ignore[arg-type]
    with pytest.raises(PricingError):
        price_usage("sol-high", Usage(input_tokens=1, output_tokens=1), 0.01, offline=False)  # type: ignore[arg-type]
    for module in (pricing_module, budget_module):
        tree = ast.parse(inspect.getsource(module))
        floats = [
            n for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, float)
        ]
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == "float"]
        assert not floats and not calls


def test_openai_counts_cache_write_once() -> None:
    usage = Usage(
        input_tokens=1000,
        cached_read_tokens=400,
        cache_write_tokens=100,
        output_tokens=100,
        reasoning_tokens=60,
    )
    price = ModelPrice(input=D(2), cached_read=D("0.1"), cache_write=D(3), output=D(10))
    got = computed_usd("openai", price, usage)
    assert got == (500 * D(2) + 400 * D("0.1") + 100 * D(3) + 100 * D(10)) / 10**6


def test_openai_table_rates() -> None:
    usage = Usage(
        input_tokens=1000, cached_read_tokens=400, cache_write_tokens=0, output_tokens=100
    )
    got = price_usage("sol-high", usage)
    assert got.usd == (600 * D(2) + 400 * D("0.1") + 100 * D(10)) / 10**6  # no write: priced


def test_anthropic_inclusivity_and_ephemeral_rates() -> None:
    plain = Usage(input_tokens=600, cached_read_tokens=400, cache_write_tokens=0, output_tokens=100)
    assert (
        price_usage("opus-medium", plain).usd == (600 * D(4) + 400 * D("0.2") + 100 * D(20)) / 10**6
    )
    split = Usage(
        input_tokens=600,
        cached_read_tokens=400,
        cache_write_tokens=150,
        cache_write_5m_tokens=100,
        cache_write_1h_tokens=50,
        output_tokens=100,
    )
    assert (
        price_usage("opus-medium", split).usd
        == (600 * D(4) + 400 * D("0.2") + 100 * D(5) + 50 * D(8) + 100 * D(20)) / 10**6
    )


def test_anthropic_unpriceable_writes_are_unknown() -> None:
    base = {"input_tokens": 1, "cached_read_tokens": 0, "output_tokens": 1}
    assert price_usage("opus-medium", Usage(**base, cache_write_tokens=5)).cost_status == "unknown"
    mismatch = Usage(**base, cache_write_tokens=9, cache_write_5m_tokens=1, cache_write_1h_tokens=1)
    assert price_usage("opus-medium", mismatch).cost_status == "unknown"
    assert price_usage("opus-medium", Usage(**base)).cost_status == "unknown"


def test_openrouter_charges_billed_only() -> None:
    usage = Usage(input_tokens=1000, output_tokens=100, cached_read_tokens=0)
    unknown = price_usage("deepseek-max", usage)
    assert (unknown.usd, unknown.cost_status) == (None, "unknown")
    billed = price_usage("deepseek-max", usage, D("0.01"))
    assert (billed.usd, billed.cost_status) == (D("0.01"), "billed")


def test_recorded_turn_with_billed_usd_is_computed_offline() -> None:
    usage = Usage(input_tokens=1000, cached_read_tokens=0, output_tokens=100)
    got = price_usage("deepseek-max", usage, D("9"), offline=True)
    assert got.cost_status == "computed"
    assert got.usd == (1000 * D("0.45") + 100 * D("1.8")) / 10**6
    sol = price_usage("sol-high", usage, D("9"), offline=True)
    assert sol.cost_status == "computed" and sol.usd != D("9")


def test_partial_usage_is_unknown_not_partial() -> None:
    assert (
        price_usage("sol-high", Usage(input_tokens=1000, output_tokens=None)).cost_status
        == "unknown"
    )
    assert (
        price_usage("sol-high", Usage(input_tokens=None, output_tokens=5)).cost_status == "unknown"
    )
    only_out = Usage(input_tokens=None, output_tokens=5, cached_read_tokens=0)
    assert price_usage("opus-medium", only_out).cost_status == "unknown"


def test_error_reply_usage_is_charged_like_a_200() -> None:
    got = price_usage("sol-medium", Usage(input_tokens=1000, output_tokens=90000))
    assert got.cost_status == "computed"
    assert got.usd == (1000 * D(2) + 90000 * D(10)) / 10**6


def test_inconsistent_inclusive_counts_are_unknown() -> None:
    bad = Usage(input_tokens=10, cached_read_tokens=8, cache_write_tokens=8, output_tokens=1)
    assert price_usage("sol-medium", bad).cost_status == "unknown"


def test_money_text_and_refusal_values() -> None:
    assert money_text(D("1E-7")) == "0.0000001"
    assert money_text(D("1E+3")) == "1000"
    assert refusal_values() == (D(0), D(0), "computed")
    with pytest.raises(PricingError):
        money_text(D("NaN"))


def test_sol_usage_over_272k_input_is_unknown_not_standard_rate() -> None:
    at_limit = Usage(input_tokens=272_000, cached_read_tokens=0, output_tokens=10)
    assert price_usage("sol-medium", at_limit).cost_status == "computed"
    over = Usage(input_tokens=272_001, cached_read_tokens=0, output_tokens=10)
    assert price_usage("sol-high", over) == Priced(None, "unknown")
    assert price_usage("sol-high", over, offline=True) == Priced(None, "unknown")


def test_negative_amounts_are_refused() -> None:
    with pytest.raises(PricingError):
        ModelPrice(input=D(-1), cache_write=D(1), output=D(1))
    with pytest.raises(PricingError):
        price_usage("deepseek-max", Usage(input_tokens=1, output_tokens=1), D(-1))


def test_offline_openrouter_cache_write_is_unknown() -> None:
    usage = Usage(input_tokens=100, cached_read_tokens=0, cache_write_tokens=10, output_tokens=1)
    assert price_usage("deepseek-max", usage, offline=True) == Priced(None, "unknown")
    clean = Usage(input_tokens=100, cached_read_tokens=0, cache_write_tokens=0, output_tokens=1)
    assert price_usage("deepseek-max", clean, offline=True).cost_status == "computed"


def test_an_unlisted_cache_write_rate_still_makes_the_charge_unknown() -> None:
    """The fail-closed branch: a price with ``cache_write_listed=False`` never charges a write."""
    unlisted = ModelPrice(
        input=D(2), cached_read=D("0.1"), cache_write=D(2), output=D(10), cache_write_listed=False
    )
    written = Usage(input_tokens=10_000, cache_write_tokens=8_000, output_tokens=100)
    assert computed_usd("openai", unlisted, written) is None
    none_written = Usage(input_tokens=10_000, cache_write_tokens=0, output_tokens=100)
    assert computed_usd("openai", unlisted, none_written) is not None


def test_sol_reservation_uses_the_listed_write_rate_when_dearer_than_input() -> None:
    rates = _key()["sol"]["usd_per_million"]
    write = D(rates["cache_write_30m"])
    assert reservation_usd(PRICES["sol-medium"], 1000, 0) == write * 1000 / 10**6


@pytest.mark.parametrize("config", ["sol-medium", "sol-high"])
def test_pilot_sol_replies_that_write_cache_are_priced_at_the_documented_rates(
    config: str,
) -> None:
    charges = _key()["pilot_charges"]
    assert charges
    for entry in charges:
        got = price_usage(config, _live_usage(entry["raw_usage"]))
        assert (got.usd, got.cost_status) == (D(entry["usd"]), entry["cost_status"])
