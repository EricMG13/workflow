"""Shared fixtures for the O6 prompt tests: the o2-synthetic pack and hand-built requests."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import o2_case

from deploy_vii.live.prompts import STEP_CONTRACTS
from deploy_vii.preparation import PreparedPack, load_pack
from deploy_workflow.context import RunContext, context_facts, load_context
from deploy_workflow.model.adapter import recorded_adapter
from deploy_workflow.owner_workflow import OWNER_SPECS, StepSpec
from deploy_workflow.prompts import PromptRequest

EXISTING = tuple(sorted(STEP_CONTRACTS))
CP3_MODULE_CONTEXT = {
    "market_evidence_sources": ["market"],
    "cp1_facilities": [{"facility_id": "tlb-2031", "label": "Term loan B"}],
    "cp2_rows": [{"row_id": "cp2.row.1", "text": "CP2-ROW-MARKER"}],
    "cp1_facts": [{"ref": "fact-1", "label": "Revenue", "shown": "120"}],
}


def make_pack(root: Path) -> PreparedPack:
    (root / "recordings").mkdir(parents=True)
    _, run_dir = o2_case._prepare(
        root / "prepared", recorded_adapter(o2_case.MODEL, root / "recordings")
    )
    return load_pack(run_dir / "pack")


def spec_of(step_id: str) -> StepSpec:
    return next(s for o in OWNER_SPECS.values() for s in o.steps if s.step_id == step_id)


def module_of(step_id: str) -> str:
    return next(m for m, o in OWNER_SPECS.items() if any(s.step_id == step_id for s in o.steps))


def request_for(
    step_id: str,
    pack: PreparedPack,
    *,
    context: RunContext | None | str = "from-pack",
    module_context: Mapping[str, object] | None = None,
    **fields: object,
) -> PromptRequest:
    spec = spec_of(step_id)
    if module_context is None and step_id == "relative_value":
        module_context = CP3_MODULE_CONTEXT
    base: dict[str, object] = {
        "step_id": step_id,
        "spec": spec,
        "pack": pack,
        "module_id": module_of(step_id),
        "context": context_facts(pack) if context == "from-pack" else context,
        "module_context": module_context,
        "readable": None,
    }
    return PromptRequest(**{**base, **fields})  # type: ignore[arg-type]


def sentinel_context(
    pack: PreparedPack, sentinel: str = "SENTINEL"
) -> tuple[RunContext, list[str]]:
    """The frozen o2 context with a sentinel written into every string leaf that the form's value
    rules accept (one leaf at a time, built with ``load_context``). Returns the context and the
    sentinel strings that took, except the research questions (a whitelisted field) and the
    two identity fields the run itself carries."""
    from deploy_workflow.context import ContextRefused

    raw = json.loads(
        (o2_case.ROOT / "cases" / "context" / "primary-full.json").read_text(encoding="utf-8")
    )
    kept: list[str] = []
    skip = {("identity", "issuer_name"), ("identity", "issuer_id")}

    def leaves(node: object, path: tuple[object, ...]) -> list[tuple[object, ...]]:
        if isinstance(node, dict):
            return [p for k, v in node.items() for p in leaves(v, (*path, k))]
        if isinstance(node, list):
            return [p for i, v in enumerate(node) for p in leaves(v, (*path, i))]
        return [path] if isinstance(node, str) else []

    def put(doc: object, path: tuple[object, ...], value: str) -> None:
        for step in path[:-1]:
            doc = doc[step]  # type: ignore[index]
        doc[path[-1]] = value  # type: ignore[index]

    for path in leaves(raw, ()):
        if path[0] in ("research_questions", "schema") or path[:2] in skip:
            continue
        probe = json.loads(json.dumps(raw))
        text = f"{sentinel}-{len(kept)}"
        put(probe, path, text)
        try:
            load_context(json.dumps(probe).encode())
        except ContextRefused:
            continue
        put(raw, path, text)
        kept.append(text)
    for n, path in enumerate(
        p for p in leaves(raw, ()) if p[0] == "assumptions" and p[-1] != "rationale"
    ):
        probe = json.loads(json.dumps(raw))
        number = f"{11 + n}.37"  # a distinctive pinned value, unlike any figure the pack prints
        put(probe, path, number)
        try:
            load_context(json.dumps(probe).encode())
        except ContextRefused:
            continue
        put(raw, path, number)
        kept.append(number)
    return load_context(json.dumps(raw).encode()), kept


def context_with(questions: list[dict[str, str]]) -> RunContext:
    raw: Any = json.loads((o2_case.CASE / "context.json").read_text(encoding="utf-8"))
    raw["research_questions"] = questions
    return load_context(json.dumps(raw).encode())
