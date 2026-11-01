"""Shared fixtures for the CP-2H context-ratings tests (a support module, not a test module):
the oracle's files, and the prepared packs and scopes built from them."""

import copy
import json
from pathlib import Path
from typing import Any

import test_method_cp2h as stage1

from deploy_vii.contracts import Run, Source
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare_source
from deploy_workflow.owners import cp2h

ROOT = Path(__file__).parents[1]
CASE = ROOT / "cases/cp2h-context-owner"
MAN: dict[str, Any] = json.loads((CASE / "manifest.json").read_text())
EXP: dict[str, Any] = json.loads((CASE / "expected.json").read_text())
SUB: dict[str, Any] = json.loads((CASE / "submissions.json").read_text())
CASES = ("positive", "gap", "outlook_unstated", "minified")
REFUSALS: dict[str, dict[str, Any]] = {r["id"]: r for r in EXP["refusals"]}


def expected(case: str) -> dict[str, Any]:
    """The oracle's case with a `same_as` case's replacements applied (the FP05 cell path is the
    renderer's, not this module's)."""
    found: dict[str, Any] = EXP["cases"][case]
    if "same_as" not in found:
        return found
    base: dict[str, Any] = copy.deepcopy(EXP["cases"][found["same_as"]])
    for path, value in found["replaces"].items():
        if "[" in path:
            continue
        *head, last = path.split(".")
        node = base
        for key in head:
            node = node[key]
        node[last] = _merged(node[last], value) if last in ("facts", "claims") else value
    return base


def _merged(base: list[dict[str, Any]], changed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """`base` with each record of `changed` in place of the one with its fact or claim id."""
    key = "fact_id" if "fact_id" in base[0] else "claim_id"
    new = {r[key]: r for r in changed}
    assert set(new) <= {r[key] for r in base}
    return [new.get(r[key], r) for r in base]


def context_bytes(name: str) -> bytes:
    return (CASE / name).read_bytes()


def context_source(name: str, raw: bytes | None = None) -> Source:
    request = SourceRequest(
        source_id="context", path=f"cases/cp2h-context-owner/{name}", media_type="text/plain"
    )
    return prepare_source(request, context_bytes(name) if raw is None else raw)


def ratings_source(variant: str) -> Source:
    v = MAN["ratings_sources"][variant]
    return stage1._source("ratings", MAN["ratings_sources"]["name"], v["pages"], v["sha256"])


def run_of(case: str) -> Run:
    return Run.model_validate_json(json.dumps(MAN["cases"][case]["run"]))


def frozen_sources() -> tuple[Source, ...]:
    return tuple(
        stage1._source(s["source_id"], s["name"], s["pages"], s["sha256"])
        for s in stage1.FINANCIAL["sources"]
    )


def prepared(
    case: str = "positive",
    *,
    context: Source | None = None,
    variant: str | None = "from case",
) -> PreparedPack:
    spec = MAN["cases"][case]
    chosen = spec["ratings_source"] if variant == "from case" else variant
    ratings = () if chosen is None else (ratings_source(chosen),)
    held = context_source(spec["context"]) if context is None else context
    return PreparedPack(run=run_of(case), sources=(*frozen_sources(), *ratings, held))


def scope_of(pack: PreparedPack) -> cp2h.PackScope:
    """What `_adapted` builds from a prepared pack (the host scope, the issuer name, the context)."""
    context, refusal = cp2h._context_of(pack)
    return cp2h.PackScope(
        sources=tuple(s for s in pack.sources if s.source_id in cp2h.SCOPE),
        names=(pack.run.issuer_name,),
        context=context,
        context_refusal=refusal,
    )


def scope(case: str = "positive", **kwargs: Any) -> cp2h.PackScope:
    return scope_of(prepared(case, **kwargs))


def inputs(case: str, pack: cp2h.PackScope | None = None) -> cp2h.TriggerInputs:
    cp2g_case = expected(case)["cp2g_head"]["case"]
    stream = stage1.upstream(cp2g_case)
    body = stage1.bind(SUB["cases"][case]["rating_triggers"], stage1.fig_ids(stream.cp1_facts))
    return cp2h.TriggerInputs(
        pack=scope(case) if pack is None else pack,
        upstream=stream,
        submission=cp2h.TriggerSubmission.model_validate_json(json.dumps(body)),
    )
