"""Golden case loader: checks a case with ``cases/goldens/check.py`` and the product's own
context loader, whose checker pins the financial gold by sha256, and keeps only in-plan facts."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
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


_SCALE_WORD = {"thousands": "thousand", "millions": "million", "billions": "billion"}


def _gold_unit(fact: Mapping[str, Any]) -> tuple[str, str]:
    """(unit, scale) in the vocabulary of module_golden.json from ``canonical_unit``
    ("USD millions") and ``currency``. ``unit_scale`` is deliberately not read (it does not
    track the magnitude: NATL has 3 beside iXBRL scale 6); magnitude comes from
    ``canonical_unit``."""
    canonical = str(fact.get("canonical_unit"))
    currency = fact.get("currency")
    parts = canonical.split()
    scale_names = tuple(checker().SCALE_EXP)
    if len(parts) != 2 or parts[0] != currency or parts[1] not in scale_names:
        raise CaseError(f"financial_gold {_gold_id(fact)}: cannot read unit {canonical!r}")
    return parts[0], parts[1]


def _gold_id(fact: Mapping[str, Any]) -> str:
    """The metric fact id: ``fact_id`` (SHC, TDG) or ``stable_fact_id`` (BGS, IHRT, LTH, NATL)."""
    fid = fact.get("fact_id", fact.get("stable_fact_id"))
    if not isinstance(fid, str) or not fid:
        raise CaseError("financial_gold fact has neither fact_id nor stable_fact_id")
    return fid


def _gold_evidence(fact: Mapping[str, Any], unit: str, scale: str) -> list[dict[str, Any]]:
    """One evidence item per conflicting version that a source printed (its evidence names a
    source id and a quote), ``printed`` = its canonical value with the scale word, which is what
    the scorer's printed-value check reads. A derived version (empty evidence, such as H1 less
    Q2) was never printed and gives none, so only a printed value can reach ``conflict_ok``."""
    versions = (fact.get("source_evidence") or {}).get("conflicting_versions") or ()
    word = _SCALE_WORD.get(scale)
    out: list[dict[str, Any]] = []
    for ver in versions:
        if ver.get("value") is None:
            continue
        ev = ver.get("evidence") or {}
        if not (ev.get("original_source_id") and ev.get("small_quote")):
            continue
        out.append(
            {
                "source_id": ev.get("original_source_id"),
                "locator": str(ver.get("version")),
                "quote": ev.get("small_quote") or "",
                "printed": f"{ver['value']} {word}" if word else str(ver["value"]),
            }
        )
    return out


def financial_gold_facts(
    gold: Mapping[str, Any], name: str = "financial_gold"
) -> dict[str, dict[str, Any]]:
    """CP-1 golden facts, keyed ``CP-1.fin.<financial fact id>``, from a financial_gold file.
    ``name`` (the file path) is shown in refusals."""

    def need(item: Any, key: str, where: str) -> Any:
        if not isinstance(item, Mapping) or key not in item:
            raise CaseError(f"{name}: {where} lacks {key!r}")
        return item[key]

    periods = need(gold, "periods", "file")
    facts = need(gold, "facts", "file")
    if not isinstance(periods, list) or not isinstance(facts, list):
        raise CaseError(f"{name}: 'periods' and 'facts' must be lists")
    ends = {need(p, "period_id", "a period"): p.get("end") for p in periods}
    out: dict[str, dict[str, Any]] = {}
    for fact in facts:
        fin_id = _gold_id(fact)
        for key in ("metric", "period_id", "status", "value"):
            need(fact, key, f"fact {fin_id}")
        fid = f"CP-1.fin.{fin_id}"
        if fid in out:
            raise CaseError(f"financial_gold repeats fact id {fin_id}")
        value = fact["value"]
        if value is not None:
            try:
                Decimal(value)
            except (InvalidOperation, TypeError) as exc:
                raise CaseError(
                    f"financial_gold {fin_id}: value {value!r} is not a number"
                ) from exc
        if fact["period_id"] not in ends:
            raise CaseError(
                f"{name}: fact {fin_id} names period_id {fact['period_id']!r} not in 'periods'"
            )
        unit, scale = _gold_unit(fact)
        out[fid] = {
            "fact_id": fid,
            "module": "CP-1",
            "topic": "financial_gold",
            "subject": fact["metric"],
            "field": fact["metric"],
            "period_end": ends[fact["period_id"]],
            "status": fact["status"],
            "value": value,
            "value_type": "decimal",
            "unit": unit,
            "scale": scale,
            "evidence": _gold_evidence(fact, unit, scale),
            "derivation": None,
            "gap_reason": fact.get("gap_reason"),
        }
    return out


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
    gold_bytes = gold_path.read_bytes()
    if hashlib.sha256(gold_bytes).hexdigest() != gold["sha256"]:
        raise CaseError(f"{case_dir.name}: financial_gold changed after the check: sha256")
    fin = financial_gold_facts(json.loads(gold_bytes), str(gold_path))
    if "CP-1" in in_plan:
        clash = sorted(set(fin) & set(facts))
        if clash:
            raise CaseError(f"{case_dir.name}: fact id {clash[0]} is in both golden files")
        facts.update(fin)
    else:
        out_of_plan["CP-1"] += len(fin)
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
