"""The tools a step is offered (O6 Task 2, O6-P4 and O6-P5).

``tools_for`` replaces ``model.loop.contract_tools_for`` for the owner path: that function reads
``live.tools.tool_set`` and offers search tools to steps that cannot use them (17 of the 26) and
the parts tools to ``financials``. Here a step gets ``search_pack`` and ``read_pages`` iff its
``StepSpec`` has ``sources``, ``extract_statements`` iff it has ``extract``, and one whole-object
``submit_<step>``. ``read_inputs`` is added by the loop itself.
"""

from typing import Any, get_args

from pydantic import BaseModel

from deploy_vii.live.prompts import PromptError
from deploy_vii.live.schema import strict_schema
from deploy_vii.live.submission import STEPS
from deploy_vii.live.tools import EXTRACT, READ, SEARCH, extract_spec, submit_name, tool_specs
from deploy_vii.registry import PACK_TOOLS
from deploy_workflow.model.turn import ToolSpec
from deploy_workflow.owner_workflow import OwnerBinding, StepSpec

__all__ = ["model_schema", "offered_schema", "tool_names", "tools_for"]


def model_schema(spec: StepSpec) -> type[BaseModel]:
    """The schema the model is shown and submits against: the one the step's validator parses
    (O6-P5a). ``source_readiness`` is ``spec.schema`` (``ReadinessReview``, with ``pack_sha256``):
    CP-0 skips ``_fill`` (``financial_workflow._filled`` returns its payload unchanged and
    ``cp0_workflow`` parses it as ``ReadinessReview``), so a schema without the field could never
    pass. Any other live step is the live schema (what ``_fill`` normalises against), else the
    spec's."""
    if spec.step_id == "source_readiness":
        return spec.schema
    live = STEPS.get(spec.step_id)
    return live.schema if live is not None else spec.schema


def _models(root: type[BaseModel]) -> dict[str, type[BaseModel]]:
    """Every model reachable from ``root`` through field annotations, by class name (the name its
    ``$defs`` entry carries), at any depth."""
    found: dict[str, type[BaseModel]] = {}

    def visit(annotation: Any) -> None:
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            if annotation.__name__ not in found:
                found[annotation.__name__] = annotation
                for field in annotation.model_fields.values():
                    visit(field.annotation)
            return
        for arg in get_args(annotation):
            visit(arg)

    visit(root)
    return found


def _holds_none(annotation: Any) -> bool:
    return (
        annotation is Any
        or annotation is type(None)
        or any(_holds_none(arg) for arg in get_args(annotation))
    )


def _exact_nulls(properties: dict[str, Any], model: type[BaseModel]) -> None:
    """Remove ``null`` from each property whose annotation cannot hold ``None`` (the strict copy
    adds it to every defaulted field; the validator rejects it). One remaining branch is the
    property itself, so a defaulted ``Literal`` becomes a one-value ``enum``."""
    for name, prop in properties.items():
        options = prop.get("anyOf")
        field = model.model_fields.get(name)
        if options is None or field is None or _holds_none(field.annotation):
            continue
        kept = [o for o in options if o != {"type": "null"}]
        if len(kept) == 1:
            properties[name] = {**{k: v for k, v in prop.items() if k != "anyOf"}, **kept[0]}
        else:
            properties[name] = {**prop, "anyOf": kept}


def offered_schema(spec: StepSpec) -> dict[str, Any]:
    """The schema shown in the prompt and offered as the submit tool's parameters: one object.
    For every step but ``source_readiness`` it is the strict copy of ``model_schema``. CP-0's
    owner path sends the model's payload to ``ReadinessReview`` unchanged (it skips ``normalise``),
    so (F1) ``null`` is removed from every field that model cannot hold ``None`` in, at any depth,
    which also pins ``schema_version`` to its literal."""
    schema = strict_schema(model_schema(spec))
    if spec.step_id != "source_readiness":
        return schema
    models = _models(spec.schema)
    _exact_nulls(schema["properties"], spec.schema)
    for name, definition in schema.get("$defs", {}).items():
        _exact_nulls(definition.get("properties", {}), models[name])
    return schema


def tool_names(spec: StepSpec) -> tuple[str, ...]:
    """The names ``tools_for`` offers, in order; rule 5 of the prompt is built from this list."""
    return (
        *((SEARCH, READ) if spec.sources else ()),
        *((EXTRACT,) if spec.extract else ()),
        submit_name(spec.step_id),
    )


def tools_for(binding: OwnerBinding, spec: StepSpec) -> tuple[ToolSpec, ...]:
    if binding.step_id != spec.step_id:
        raise PromptError(f"binding is for step {binding.step_id}, spec for {spec.step_id}")
    # search_pack and read_pages are the live tools' own specs, taken by name so the owner path
    # and the live path cannot describe them differently.
    pack = {
        f["function"]["name"]: f["function"] for f in tool_specs("source_readiness", PACK_TOOLS)
    }
    functions = {
        SEARCH: pack[SEARCH],
        READ: pack[READ],
        EXTRACT: extract_spec()["function"],
        submit_name(spec.step_id): {
            "name": submit_name(spec.step_id),
            "description": (
                f"Submit the {spec.step_id} JSON object. Answers `valid`, `invalid` or `refused` "
                "with the validator's issues."
            ),
            "parameters": offered_schema(spec),
        },
    }
    return tuple(
        ToolSpec(name, functions[name]["description"], functions[name]["parameters"])
        for name in tool_names(spec)
    )
