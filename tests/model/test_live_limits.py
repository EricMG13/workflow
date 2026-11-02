"""PF2: the live-run limits read their pinned key, cases/pilot-fixes/limits.json."""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from _pack import SPEC, make_rig

from deploy_workflow import run_pathway
from deploy_workflow.model import providers, transport
from deploy_workflow.model.loop import TOKEN_OVERHEAD, _request_bytes
from deploy_workflow.model.pricing import (
    PRICES,
    ContextTooLong,
    price_of,
    reservation_usd,
)
from deploy_workflow.model.turn import CONFIG_PROVIDERS, Message, TurnRequest

KEY_FILE = Path(__file__).parents[2] / "cases" / "pilot-fixes" / "limits.json"
SOL_REQUEST_BYTES = 705_000


def _key() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(KEY_FILE.read_text(encoding="utf-8"))
    return loaded


def test_the_output_cap_is_the_keys() -> None:
    assert run_pathway.MAX_OUTPUT_TOKENS == _key()["max_output_tokens"]


def test_the_output_cap_is_within_every_documented_maximum_and_the_providers_cap() -> None:
    key = _key()
    for config, documented in key["documented_max_output_tokens"].items():
        assert run_pathway.MAX_OUTPUT_TOKENS <= documented["value"], config
    assert providers.MAX_OUTPUT_TOKENS == key["providers_global_cap"]
    assert run_pathway.MAX_OUTPUT_TOKENS <= providers.MAX_OUTPUT_TOKENS


@pytest.mark.parametrize("config", sorted(CONFIG_PROVIDERS))
def test_the_output_reservation_per_call_is_the_keys(config: str) -> None:
    expected = Decimal(_key()["reservation_output_usd_per_call"][config])
    got = reservation_usd(price_of(config), 0, run_pathway.MAX_OUTPUT_TOKENS)
    assert got == expected


def test_the_bytes_per_token_lower_bounds_are_the_keys() -> None:
    expected = {p: Decimal(v) for p, v in _key()["bytes_per_token_lower_bound"].items()}
    assert dict(run_pathway.BYTES_PER_TOKEN_LOWER_BOUND) == expected


def test_the_bounds_name_exactly_the_providers_of_the_configurations() -> None:
    assert set(run_pathway.BYTES_PER_TOKEN_LOWER_BOUND) == set(CONFIG_PROVIDERS.values())


def _sol_request() -> TurnRequest:
    return TurnRequest(
        messages=(Message("user", "x" * SOL_REQUEST_BYTES),),
        tools=(),
        max_output_tokens=1,
        effort="medium",
    )


def test_a_705k_sol_request_bounds_under_the_context_with_the_keys_ratio_and_not_with_one(
    tmp_path: Path,
) -> None:
    ratio = Decimal(_key()["bytes_per_token_lower_bound"]["openai"])
    sol = PRICES["sol-medium"]
    assert sol.max_input_tokens is not None
    request = _sol_request()
    bounded = make_rig(tmp_path / "a", [], spec=SPEC, bytes_per_token=ratio).loop
    tokens = bounded._token_bound(request)  # no public seam computes the bound
    assert tokens <= sol.max_input_tokens
    assert tokens >= SOL_REQUEST_BYTES / ratio + TOKEN_OVERHEAD
    reservation_usd(sol, tokens, 0)  # not refused as ContextTooLong
    unbounded = make_rig(tmp_path / "b", [], spec=SPEC, bytes_per_token=Decimal(1)).loop
    with pytest.raises(ContextTooLong):
        reservation_usd(sol, unbounded._token_bound(request), 0)


def test_the_overall_timeout_is_the_keys() -> None:
    assert transport.OVERALL_S == _key()["overall_s"]


def test_only_the_configs_the_key_names_set_a_context_limit() -> None:
    """Guards the key's context claim: ContextTooLong can fire only where a price sets one."""
    limited = {c for c, price in PRICES.items() if price.max_input_tokens is not None}
    assert limited == set(_key()["context_too_long_configs"])


def _padded_sol_request(size: int) -> TurnRequest:
    """A request whose bytes as sent (``_request_bytes``) are exactly ``size``."""

    def sized(padding: int) -> TurnRequest:
        message = Message("user", "x" * padding)
        return TurnRequest(messages=(message,), tools=(), max_output_tokens=1, effort="medium")

    request = sized(size - _request_bytes(sized(0)))
    assert _request_bytes(request) == size
    return request


def test_the_boundary_request_at_the_runs_openai_bound_is_accepted_and_one_byte_more_is_not(
    tmp_path: Path,
) -> None:
    ratio = run_pathway.BYTES_PER_TOKEN_LOWER_BOUND["openai"]
    assert ratio == Decimal(_key()["bytes_per_token_lower_bound"]["openai"])
    sol = PRICES["sol-medium"]
    assert sol.max_input_tokens is not None
    largest = int((sol.max_input_tokens - TOKEN_OVERHEAD) * ratio)  # bytes whose bound just fits
    loop = make_rig(tmp_path, [], spec=SPEC, bytes_per_token=ratio).loop
    fits = loop._token_bound(_padded_sol_request(largest))
    assert fits == sol.max_input_tokens
    reservation_usd(sol, fits, 0)  # accepted
    with pytest.raises(ContextTooLong):
        reservation_usd(sol, loop._token_bound(_padded_sol_request(largest + 1)), 0)
