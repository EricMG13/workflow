"""0d: a malformed model payload that reaches `live.schema.normalise` takes the ordinary
ill-shaped path (returned unchanged, Pydantic reports it), never a raw TypeError/RecursionError."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from deploy_vii.live.schema import MAX_NESTING, json_object, normalise, too_deep
from deploy_vii.live.submission import PART_CALL, PART_MODELS, STEPS, compose_payload
from deploy_vii.live.tools import Seen, ToolRules, cited_locators

DEEP = 200_000


class Node(BaseModel):
    """A self-referential model: the walker recurses as deep as the payload nests."""

    child: "Node | None" = None


def _nested(depth: int) -> str:
    return '{"child":' * depth + "null" + "}" * depth


def _unchanged(model: type[BaseModel], payload: str) -> None:
    assert normalise(model, payload) == (payload, ())


def test_unhashable_list_tag_is_not_determined() -> None:
    payload = '{"findings":[{"evidence":[{"kind":[]}]}]}'
    _unchanged(STEPS["narrative"].schema, payload)


def test_unhashable_dict_tag_is_not_determined() -> None:
    _unchanged(STEPS["narrative"].schema, '{"findings":[{"evidence":[{"kind":{}}]}]}')


def test_deep_nesting_is_refused_at_the_parse() -> None:
    payload = '{"note":' + "[" * DEEP + "]" * DEEP + "}"
    _unchanged(STEPS["business_context"].schema, payload)
    assert json_object(payload) is None


def test_deep_nesting_is_refused_in_the_walker() -> None:
    payload = _nested(600)  # parses (below the interpreter limit) but would recurse the walker
    _unchanged(Node, payload)
    assert json_object(payload) is None


def test_deep_payload_is_an_ordinary_validation_failure() -> None:
    try:
        Node.model_validate_json(normalise(Node, _nested(DEEP))[0])
    except ValidationError:
        return
    raise AssertionError("expected a ValidationError")


def test_nesting_at_the_limit_still_parses_and_one_past_is_refused() -> None:
    assert isinstance(json_object(_nested(MAX_NESTING)), dict)  # 64 containers deep
    assert json_object(_nested(MAX_NESTING + 1)) is None
    assert normalise(Node, _nested(10)) == (_nested(10), ())


def test_brackets_inside_strings_do_not_count_as_depth() -> None:
    payload = json.dumps({"note": "[" * 5000 + '\\"' + "{" * 5000})
    assert json_object(payload) is not None


def test_forged_narrative_is_refused_by_the_workflow(tmp_path: Path) -> None:
    """End to end on the CP-1 narrative step: invalid, not a raised exception (a fresh run each:
    two invalid replies spend the step's retries)."""
    import test_financial_workflow as t

    forgeries = (
        '{"findings":[{"evidence":[{"kind":[]}]}]}',
        '{"findings":[{"evidence":[{"kind":{}}]}]}',
        '{"findings":' + "[" * DEEP + "]" * DEEP + "}",
    )
    for index, forged in enumerate(forgeries):
        workflow, pack = t.before_financials(tmp_path / str(index))
        t.financial_reads(workflow)
        assert workflow.submit_review(json.dumps(t.financials(pack)))["status"] == "valid"
        workflow.read_inputs()
        assert workflow.submit_review(forged)["status"] == "invalid"


def test_nesting_scan_boundary() -> None:
    assert not too_deep("[" * MAX_NESTING + "]" * MAX_NESTING)
    assert too_deep("[" * (MAX_NESTING + 1) + "]" * (MAX_NESTING + 1))


def test_rules_and_compose_do_not_raise_on_deep_payloads() -> None:
    deep = '{"note":' + "[" * DEEP + "]" * DEEP + "}"
    assert cited_locators(deep) == set()
    ToolRules().issues("business_context", deep, seen=Seen(), context=None)
    assert compose_payload(None, deep).review is None  # the pack is not read


def _depth(node: object, defs: dict[str, object], stack: frozenset[str], free: list[str]) -> int:
    """Deepest container nesting a schema node admits; free-form nodes are collected in `free`."""
    if not isinstance(node, dict):
        return 0
    if "$ref" in node:
        name = node["$ref"].rsplit("/", 1)[-1]
        if name in stack:
            free.append(f"cycle {name}")
            return 10**9
        return _depth(defs[name], defs, stack | {name}, free)
    best = 0
    for key in ("anyOf", "oneOf", "allOf"):
        for branch in node.get(key, ()):
            best = max(best, _depth(branch, defs, stack, free))
    if not {"type", "anyOf", "oneOf", "allOf", "const", "enum"} & node.keys():
        free.append("untyped node")
        return 10**9
    kinds = node.get("type")
    kinds = kinds if isinstance(kinds, list) else [kinds]
    if "object" in kinds:
        if "properties" not in node or node.get("additionalProperties", True) is not False:
            free.append("open object")
            return 10**9
        inner = max((_depth(v, defs, stack, free) for v in node["properties"].values()), default=0)
        best = max(best, 1 + inner)
    if "array" in kinds:
        if "items" not in node:
            free.append("untyped array")
            return 10**9
        best = max(best, 1 + _depth(node["items"], defs, stack, free))
    return best


def test_no_live_schema_admits_nesting_past_the_bound() -> None:
    """The bound is safe only while no schema accepts a payload deeper than `MAX_NESTING`."""
    models = {f"step {k}": v.schema for k, v in STEPS.items()}
    models.update({f"part {k}": v for k, v in PART_MODELS.items()})
    models["part call"] = PART_CALL
    for name, model in models.items():
        schema = model.model_json_schema()
        free: list[str] = []
        depth = _depth(schema, schema.get("$defs", {}), frozenset(), free)
        assert not free, (name, free)
        assert depth < MAX_NESTING, (name, depth)


def _orphan_bindings(workflow: Any) -> int:
    from deploy_workflow import financial_workflow as fw

    directory = fw._audit(workflow._store, "bindings", "x").parent
    recorded = {s.binding.content_hash() for s in workflow._submissions}
    return len({p.name for p in directory.iterdir()} - recorded)


def test_source_step_refusals_leave_no_orphan_binding(tmp_path: Path) -> None:
    """CP-1 source_context (an evidence-rule step): deep nesting and a lone surrogate after null
    resolution are refused as invalid, raise nothing and leave no binding without a submission."""
    import test_financial_workflow as t

    payloads = {
        "deep": '{"sources":' + "[" * DEEP + "]" * DEEP + "}",
        "deep3000": '{"sources":' + "[" * 3000 + "]" * 3000 + "}",
        "surrogate": '{"schema_version":null,"zz":"\\ud800"}',
    }
    for label, payload in payloads.items():
        workflow, pack = t.start(tmp_path / label)
        t.read_sources(workflow)
        assert workflow.submit_review(t.readiness(pack))["status"] == "valid"
        workflow.invoke("read_pages", {"source_id": "financial", "first_page": 1, "last_page": 1})
        assert workflow.submit_review(payload)["status"] == "invalid", label
        assert _orphan_bindings(workflow) == 0, label


def test_lone_surrogate_after_null_resolution_is_left_unchanged() -> None:
    payload = '{"schema_version":null,"zz":"\\ud800"}'
    assert normalise(STEPS["source_context"].schema, payload) == (payload, ())
