"""O6 Task 1: the inventory of steps that need an owner-path prompt, and the prompt-set contract.

The inventory is the 26 steps of ``OWNER_SPECS``. The ``compose`` cases are strict xfail until
Tasks 2-4 give each step a prompt; each marker comes off when its step gets one (the strict flag
turns an unexpected pass into a failure, so the marker cannot be forgotten).
"""

import pytest

from deploy_vii.contracts import PATHWAY_MODULES
from deploy_vii.registry import plan
from deploy_workflow import prompts
from deploy_workflow.owner_workflow import OWNER_SPECS
from deploy_workflow.prompts import NoPrompt, PromptRequest, compose, inventory

EXPECTED = (
    "business_context",
    "change_screen",
    "committee_challenge",
    "credit_synthesis",
    "decision_ledger",
    "downside_pathway",
    "earnings_delta",
    "earnings_quality",
    "financials",
    "forward_credit_model",
    "integrity_review",
    "legal_covenants",
    "liquidity_bridge",
    "macro_fx",
    "market_implied",
    "narrative",
    "peer_benchmark",
    "quality",
    "rating_triggers",
    "readiness",
    "refinancing_risk",
    "relative_value",
    "research",
    "restructuring_fulcrum",
    "source_context",
    "source_readiness",
)


def test_inventory_is_the_26_steps_of_owner_specs() -> None:
    found = inventory()
    assert len(found) == 26
    assert found == EXPECTED
    assert list(found) == sorted(found)
    assert set(found) == {s.step_id for spec in OWNER_SPECS.values() for s in spec.steps}


@pytest.mark.parametrize("preset", sorted(PATHWAY_MODULES))
def test_every_step_of_a_preset_is_in_the_inventory(preset: str) -> None:
    steps = [
        s.step_id
        for module_id in plan(PATHWAY_MODULES[preset])
        for s in OWNER_SPECS[module_id].steps
    ]
    assert steps, preset
    assert set(steps) <= set(inventory()), sorted(set(steps) - set(inventory()))


def test_cp_model_contributes_no_step() -> None:
    assert OWNER_SPECS["CP-MODEL"].steps == ()


def test_no_prompt_is_a_distinct_exception_carrying_the_step() -> None:
    err = NoPrompt("narrative")
    assert isinstance(err, Exception)
    assert err.step == "narrative"
    assert err.step_id == "narrative"
    assert str(err) == "narrative"
    assert not issubclass(NoPrompt, (KeyError, ValueError, LookupError))


def test_compose_raises_no_prompt_for_a_step_outside_the_inventory() -> None:
    with pytest.raises(NoPrompt) as caught:
        compose(PromptRequest("no_such_step"))
    assert caught.value.step_id == "no_such_step"


def test_the_public_names_are_the_ruled_ones() -> None:
    assert {"NoPrompt", "PromptRequest", "compose", "inventory", "prompt_factory"} <= set(
        dir(prompts)
    )


@pytest.mark.parametrize(
    "step_id",
    [
        pytest.param(
            s,
            marks=pytest.mark.xfail(
                strict=True, raises=NoPrompt, reason=f"O6 Tasks 2-4: no prompt for {s} yet"
            ),
        )
        for s in EXPECTED
    ],
)
def test_compose_returns_messages_for_each_inventory_step(step_id: str) -> None:
    messages = compose(PromptRequest(step_id))  # NoPrompt names the missing step
    assert messages
    assert messages[0].role == "system"
