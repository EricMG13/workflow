"""O6 Task 2: ``tools_for`` (O6-P4, P5). The tools offered are the ones the step can use."""

import pytest

from deploy_vii.live.schema import strict_schema
from deploy_vii.live.submission import STEPS
from deploy_workflow.owner_workflow import OWNER_SPECS, OwnerBinding, StepSpec
from deploy_workflow.prompts import inventory
from deploy_workflow.prompts.tools import model_schema, tools_for

ALL = [(m, s) for m, o in OWNER_SPECS.items() for s in o.steps]


def binding_of(step_id: str) -> OwnerBinding:
    # tools_for reads only the step id of the binding
    return OwnerBinding.model_construct(step_id=step_id)


@pytest.mark.parametrize("module_id,spec", ALL, ids=[s.step_id for _, s in ALL])
def test_tools_follow_the_spec_flags(module_id: str, spec: StepSpec) -> None:
    names = [t.name for t in tools_for(binding_of(spec.step_id), spec)]
    expected = [
        *(["search_pack", "read_pages"] if spec.sources else []),
        *(["extract_statements"] if spec.extract else []),
        f"submit_{spec.step_id}",
    ]
    assert names == expected


@pytest.mark.parametrize("module_id,spec", ALL, ids=[s.step_id for _, s in ALL])
def test_no_step_is_offered_a_part_tool(module_id: str, spec: StepSpec) -> None:
    assert not [t for t in tools_for(binding_of(spec.step_id), spec) if t.name.endswith("_part")]


@pytest.mark.parametrize("module_id,spec", ALL, ids=[s.step_id for _, s in ALL])
def test_the_submit_tool_carries_the_strict_model_schema(module_id: str, spec: StepSpec) -> None:
    submit = tools_for(binding_of(spec.step_id), spec)[-1]
    assert dict(submit.parameters) == strict_schema(model_schema(spec))


def test_the_model_schema_is_the_live_one_for_a_live_step_else_the_spec_one() -> None:
    readiness = next(
        s for o in OWNER_SPECS.values() for s in o.steps if s.step_id == "source_readiness"
    )
    assert model_schema(readiness) is STEPS["source_readiness"].schema
    assert model_schema(readiness) is not readiness.schema  # the spec adds pack_sha256 (O6-P5)
    research = next(s for o in OWNER_SPECS.values() for s in o.steps if s.step_id == "research")
    assert "research" not in STEPS
    assert model_schema(research) is research.schema


def test_financials_gets_the_whole_object_submit_and_extraction() -> None:
    spec = next(s for o in OWNER_SPECS.values() for s in o.steps if s.step_id == "financials")
    names = [t.name for t in tools_for(binding_of("financials"), spec)]
    assert names == ["search_pack", "read_pages", "extract_statements", "submit_financials"]


def test_a_binding_for_another_step_is_refused() -> None:
    spec = next(s for o in OWNER_SPECS.values() for s in o.steps if s.step_id == "narrative")
    with pytest.raises(ValueError, match="narrative"):
        tools_for(binding_of("quality"), spec)


def test_the_covered_steps_are_the_inventory() -> None:
    assert tuple(sorted(s.step_id for _, s in ALL)) == inventory()
