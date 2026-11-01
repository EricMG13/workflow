"""O6 Task 1: the inventory of steps that need an owner-path prompt, and the prompt-set contract.

The inventory is the 26 steps of ``OWNER_SPECS``. The ``compose`` cases are strict xfail until
a step has a prompt; each marker comes off when its step gets one (the strict flag turns an
unexpected pass into a failure, so the marker cannot be forgotten). Task 2 gave the 12 steps that
already have a ``STEP_CONTRACTS`` text their prompt; the 14 new steps wait for Task 4's texts.
"""

import dataclasses

import pytest
from prompt_support import EXISTING, request_for

from deploy_vii.contracts import PATHWAY_MODULES, PathwayId
from deploy_vii.preparation import PreparedPack
from deploy_vii.registry import plan
from deploy_workflow import prompts
from deploy_workflow.owner_workflow import OWNER_SPECS
from deploy_workflow.prompts import NoPrompt, compose, inventory

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
def test_every_step_of_a_preset_is_in_the_inventory(preset: PathwayId) -> None:
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


def test_compose_raises_no_prompt_for_a_step_outside_the_inventory(pack: PreparedPack) -> None:
    request = dataclasses.replace(request_for("narrative", pack), step_id="no_such_step")
    with pytest.raises(NoPrompt) as caught:
        compose(request)
    assert caught.value.step_id == "no_such_step"


def test_the_public_names_are_the_ruled_ones() -> None:
    assert {"NoPrompt", "PromptRequest", "compose", "inventory", "prompt_factory"} <= set(
        dir(prompts)
    )


@pytest.mark.parametrize(
    "step_id",
    [
        s
        if s in EXISTING
        else pytest.param(
            s,
            marks=pytest.mark.xfail(
                strict=True, raises=NoPrompt, reason=f"O6 Task 4: no text for {s} yet"
            ),
        )
        for s in EXPECTED
    ],
)
def test_compose_returns_messages_for_each_inventory_step(step_id: str, pack: PreparedPack) -> None:
    messages = compose(request_for(step_id, pack))  # NoPrompt names the missing step
    assert messages
    assert messages[0].role == "system"
