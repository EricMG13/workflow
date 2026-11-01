"""O6 Task 2: ``tools_for`` (O6-P4, P5). The tools offered are the ones the step can use."""

from typing import Any

import pytest

from deploy_vii.live.prompts import PromptError
from deploy_vii.live.schema import strict_schema
from deploy_vii.live.submission import STEPS
from deploy_vii.readiness import ReadinessReview
from deploy_workflow.owner_workflow import OWNER_SPECS, OwnerBinding, StepSpec
from deploy_workflow.prompts import inventory
from deploy_workflow.prompts.tools import model_schema, offered_schema, tools_for

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
    assert dict(submit.parameters) == offered_schema(spec)
    if spec.step_id != "source_readiness":  # O6-P5a/F1 changes CP-0's schema only
        assert offered_schema(spec) == strict_schema(model_schema(spec))


def test_p5a_the_cp0_schema_is_the_one_its_validator_parses() -> None:
    """CP-0 does not go through ``_fill``: its validator parses ``ReadinessReview``, which holds
    ``pack_sha256``; the strict submit schema must allow it and require it."""
    spec = next(s for o in OWNER_SPECS.values() for s in o.steps if s.step_id == "source_readiness")
    assert model_schema(spec) is ReadinessReview
    submit = tools_for(binding_of("source_readiness"), spec)[-1]
    assert "pack_sha256" in submit.parameters["properties"]
    assert "pack_sha256" in submit.parameters["required"]


def test_the_model_schema_is_the_live_one_for_a_live_step_else_the_spec_one() -> None:
    narrative = next(s for o in OWNER_SPECS.values() for s in o.steps if s.step_id == "narrative")
    assert model_schema(narrative) is STEPS["narrative"].schema
    research = next(s for o in OWNER_SPECS.values() for s in o.steps if s.step_id == "research")
    assert "research" not in STEPS
    assert model_schema(research) is research.schema


def test_financials_gets_the_whole_object_submit_and_extraction() -> None:
    spec = next(s for o in OWNER_SPECS.values() for s in o.steps if s.step_id == "financials")
    names = [t.name for t in tools_for(binding_of("financials"), spec)]
    assert names == ["search_pack", "read_pages", "extract_statements", "submit_financials"]


def test_a_binding_for_another_step_is_refused() -> None:
    spec = next(s for o in OWNER_SPECS.values() for s in o.steps if s.step_id == "narrative")
    with pytest.raises(PromptError, match="narrative"):
        tools_for(binding_of("quality"), spec)


def test_the_covered_steps_are_the_inventory() -> None:
    assert tuple(sorted(s.step_id for _, s in ALL)) == inventory()


def cp0_spec() -> StepSpec:
    return next(s for o in OWNER_SPECS.values() for s in o.steps if s.step_id == "source_readiness")


def nullable_props(schema: dict[str, Any]) -> list[tuple[str, str]]:
    found = []
    for owner, node in [("$", schema), *schema.get("$defs", {}).items()]:
        for name, prop in node.get("properties", {}).items():
            if {"type": "null"} in prop.get("anyOf", []):
                found.append((owner, name))
    return found


def set_first_null(node: Any, name: str) -> bool:
    if isinstance(node, dict):
        if name in node:
            node[name] = None
            return True
        return any(set_first_null(v, name) for v in node.values())
    if isinstance(node, list):
        return any(set_first_null(v, name) for v in node)
    return False


def test_f1_every_null_the_cp0_schema_admits_is_accepted_by_the_validator() -> None:
    import json

    import o2_case
    from pydantic import ValidationError

    offered = offered_schema(cp0_spec())
    payload = json.loads(o2_case.payload_for("source_readiness"))
    payload["schema_version"] = "readiness-review/1"
    admitted = nullable_props(offered)
    assert admitted  # fields that hold None (missing_source, entity, period...) stay nullable
    exercised = 0
    for _, name in admitted:
        probe = json.loads(json.dumps(payload))
        if not set_first_null(probe, name):
            continue
        exercised += 1
        try:
            ReadinessReview.model_validate_json(json.dumps(probe))
        except ValidationError as error:  # the cause named, not just the field
            raise AssertionError(f"offered schema admits null for {name}: {error}") from error
    assert exercised


@pytest.mark.parametrize(
    "owner,name",
    [
        ("ConsumerReadiness", "limitations"),
        ("SourceAssessment", "limitations"),
        ("ReadinessGap", "citations"),
        ("$", "schema_version"),
    ],
)
def test_f1_a_field_whose_annotation_cannot_hold_none_is_not_nullable(
    owner: str, name: str
) -> None:
    assert (owner, name) not in nullable_props(offered_schema(cp0_spec()))
    assert (owner, name) in nullable_props(strict_schema(ReadinessReview))  # what was removed


def test_f1_schema_version_is_pinned_to_the_literal() -> None:
    offered = offered_schema(cp0_spec())
    version = offered["properties"]["schema_version"]
    assert version["enum"] == ["readiness-review/1"] and "anyOf" not in version
    assert "schema_version" in offered["required"]
    assert "other-version/9" not in version["enum"]


def test_f1_the_other_nullable_fields_keep_their_other_types() -> None:
    offered = offered_schema(cp0_spec())
    assert offered["$defs"]["ConsumerReadiness"]["properties"]["limitations"]["type"] == "array"
    assert {"type": "string"} in offered["$defs"]["SourceAssessment"]["properties"]["entity"][
        "anyOf"
    ]


def test_a_defs_entry_that_is_not_a_model_is_a_named_error_not_a_keyerror() -> None:
    """O6 T2 Info: a CP-0 schema holding an Enum has a ``$defs`` entry no model class carries; the
    refusal names it (a ``PromptError``) instead of a bare ``KeyError``."""
    from dataclasses import replace
    from enum import Enum

    from deploy_vii.contracts import Contract

    class Colour(Enum):
        RED = "red"

    class WithEnum(Contract):
        colour: Colour = Colour.RED

    with pytest.raises(PromptError, match="Colour"):
        offered_schema(replace(cp0_spec(), schema=WithEnum))
