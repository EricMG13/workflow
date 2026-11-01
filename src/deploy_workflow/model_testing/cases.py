"""Golden case loader: checks a case with ``cases/goldens/check.py`` and the product's own
context loader, whose checker pins the financial gold by sha256, and keeps only in-plan facts."""

from __future__ import annotations

import importlib.util
import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from types import MappingProxyType, ModuleType
from typing import Any

from deploy_vii.contracts import PATHWAY_MODULES, PathwayId
from deploy_workflow.context import ContextRefused, load_context

_CHECK_PATH = Path(__file__).resolve().parents[3] / "cases" / "goldens" / "check.py"


class CaseError(ValueError):
    """A golden case cannot be used for scoring."""


@dataclass(frozen=True)
class GoldenCase:
    case_id: str
    pathway: PathwayId
    case_dir: Path
    context_path: Path
    facts: Mapping[str, Mapping[str, Any]]
    out_of_plan: Mapping[str, int]
    financial_gold_path: Path
    financial_gold_sha256: str


@cache
def checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("golden_case_check", _CHECK_PATH)
    if spec is None or spec.loader is None:
        raise CaseError(f"cannot load {_CHECK_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_case(case_dir: Path, corpus: Path) -> GoldenCase:
    result = checker().check_case(case_dir, corpus)
    if result.problems:
        shown = "; ".join(result.problems[:5])
        raise CaseError(
            f"check.py refused {case_dir.name} ({len(result.problems)} problems): {shown}"
        )
    golden = json.loads((case_dir / "module_golden.json").read_text(encoding="utf-8"))
    pathway = golden["pathway"]
    if pathway not in PATHWAY_MODULES:
        raise CaseError(f"{case_dir.name}: unknown pathway {pathway!r}")
    context_path = case_dir / golden["context_file"]
    try:
        load_context(context_path.read_bytes())
    except ContextRefused as exc:
        raise CaseError(
            f"{case_dir.name}: context.json refused by the product: {'; '.join(exc.problems[:5])}"
        ) from exc
    gold = golden["financial_gold"]  # check_case has verified the file against its pinned sha256
    gold_path = Path(gold["path"])
    in_plan = set(PATHWAY_MODULES[pathway])
    facts = {f["fact_id"]: f for f in golden["facts"] if f["module"] in in_plan}
    out_of_plan = Counter(f["module"] for f in golden["facts"] if f["module"] not in in_plan)
    return GoldenCase(
        case_id=golden["case_id"],
        pathway=pathway,
        case_dir=case_dir,
        context_path=context_path,
        facts=MappingProxyType(facts),
        out_of_plan=MappingProxyType(dict(out_of_plan)),
        financial_gold_path=gold_path,
        financial_gold_sha256=gold["sha256"],
    )
