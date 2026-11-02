"""PF2: the live-run limits read their pinned key, cases/pilot-fixes/limits.json."""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from _pack import SPEC, make_rig

from deploy_workflow import run_pathway
from deploy_workflow.model import providers, transport
from deploy_workflow.model.loop import TOKEN_OVERHEAD
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
