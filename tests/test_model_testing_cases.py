from __future__ import annotations

import json
import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest

from deploy_vii.contracts import PATHWAY_MODULES, Citation, Fact, Module
from deploy_workflow.model_testing.cases import (
    CaseError,
    GoldenCase,
    financial_gold_facts,
    load_case,
)
from deploy_workflow.model_testing.configs import CASES
from deploy_workflow.model_testing.mapping import Locator, Mapping, MappingEntry
from deploy_workflow.model_testing.scoring import score_module

ROOT = Path(__file__).resolve().parents[1]
GOLDENS = ROOT / "cases" / "goldens"
CORPUS = Path("/Users/ericguei/Documents/Deploy Workflow/artifacts/public-corpus/v1")

FIXTURE = ROOT / "tests" / "fixtures" / "model_testing" / "financial_gold_small.json"

needs_corpus = pytest.mark.skipif(
    not CORPUS.is_dir(), reason="public corpus v1 is not on this machine"
)


def _copy_case(tmp_path: Path, name: str) -> Path:
    """Copy a case and its financial gold; point the copied golden at the copied gold."""
    case = tmp_path / name
    shutil.copytree(GOLDENS / name, case)
    golden_path = case / "module_golden.json"
    golden = json.loads(golden_path.read_text())
    gold_copy = tmp_path / "financial_gold.json"
    shutil.copyfile(golden["financial_gold"]["path"], gold_copy)
    golden["financial_gold"]["path"] = str(gold_copy)
    golden_path.write_text(json.dumps(golden))
    return case


@needs_corpus
def test_loads_every_golden() -> None:
    for d in CASES.values():
        c = load_case(GOLDENS / d, CORPUS)
        assert c.facts and c.context_path.name == "context.json"
        assert c.financial_gold_path.is_file()


@needs_corpus
def test_copied_case_loads(tmp_path: Path) -> None:
    c = load_case(_copy_case(tmp_path, "shc-earnings-update"), CORPUS)
    assert c.pathway == "earnings_update"


@needs_corpus
def test_refuses_changed_financial_gold(tmp_path: Path) -> None:
    case = _copy_case(tmp_path, "shc-earnings-update")
    with (tmp_path / "financial_gold.json").open("ab") as f:
        f.write(b" ")
    with pytest.raises(CaseError, match=r"financial_gold.*sha256"):
        load_case(case, CORPUS)


@needs_corpus
def test_refuses_failing_checker(tmp_path: Path) -> None:
    case = _copy_case(tmp_path, "shc-earnings-update")
    p = case / "module_golden.json"
    golden = json.loads(p.read_text())
    evidence = golden["facts"][0]["evidence"][0]
    evidence["quote"] = evidence["quote"] + " not in the filing"
    p.write_text(json.dumps(golden))
    with pytest.raises(CaseError, match=r"check\.py"):
        load_case(case, CORPUS)


@needs_corpus
def test_refuses_context_the_product_refuses(tmp_path: Path) -> None:
    case = _copy_case(tmp_path, "tdg-credit-snapshot")
    p = case / "context.json"
    text = p.read_text()
    assert '"issuer_id": "tdg"' in text
    p.write_text(text.replace('"issuer_id": "tdg"', '"issuer_id": "-tdg"'))
    with pytest.raises(CaseError, match=r"context\.json"):
        load_case(case, CORPUS)


@needs_corpus
def test_natl_cp4_out_of_plan() -> None:
    c = load_case(GOLDENS / "natl-portfolio-decision", CORPUS)
    assert c.out_of_plan == {"CP-4": 51}
    assert not any(f["module"] == "CP-4" for f in c.facts.values())


@needs_corpus
def test_other_cases_have_nothing_out_of_plan() -> None:
    for d in CASES.values():
        if d != "natl-portfolio-decision":
            assert load_case(GOLDENS / d, CORPUS).out_of_plan == {}


def _fixture_facts() -> dict[str, dict[str, Any]]:
    return financial_gold_facts(json.loads(FIXTURE.read_text(encoding="utf-8")))


def _gold_ids(gold_path: Path) -> list[str]:
    facts = json.loads(gold_path.read_text(encoding="utf-8"))["facts"]
    return [f.get("fact_id", f.get("stable_fact_id")) for f in facts]


@needs_corpus
def test_financial_gold_facts_loaded(tmp_path: Path) -> None:
    case = _copy_case(tmp_path, "shc-earnings-update")
    c = load_case(case, CORPUS)
    ids = _gold_ids(c.financial_gold_path)
    assert ids and len(set(ids)) == len(ids)
    loaded = [fid for fid, f in c.facts.items() if f["topic"] == "financial_gold"]
    assert sorted(loaded) == sorted(f"CP-1.fin.{i}" for i in ids)
    assert all(c.facts[fid]["module"] == "CP-1" for fid in loaded)


@needs_corpus
def test_financial_gold_out_of_plan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Every real pathway plans CP-1, so take it out of the plan the loader sees.
    plans = {k: tuple(m for m in v if m != "CP-1") for k, v in PATHWAY_MODULES.items()}
    monkeypatch.setattr("deploy_workflow.model_testing.cases.PATHWAY_MODULES", plans)
    c = load_case(_copy_case(tmp_path, "shc-earnings-update"), CORPUS)
    ids = _gold_ids(c.financial_gold_path)
    assert c.out_of_plan == {"CP-1": len(ids)}
    assert not any(f["module"] == "CP-1" for f in c.facts.values())


@needs_corpus
def test_financial_gold_sha_still_checked(tmp_path: Path) -> None:
    case = _copy_case(tmp_path, "tdg-credit-snapshot")
    with (tmp_path / "financial_gold.json").open("ab") as f:
        f.write(b" ")
    with pytest.raises(CaseError, match=r"financial_gold.*sha256"):
        load_case(case, CORPUS)


def test_financial_gold_fixture_conversion() -> None:
    facts = _fixture_facts()
    assert sorted(facts) == [
        "CP-1.fin.BGS:FY2024Q2:revenue",
        "CP-1.fin.NATL:FY2025Q1:adjusted_EBITDA",
        "CP-1.fin.TDG:CFO:FY2024Q2",
        "CP-1.fin.TDG:principal:FY2024Q2",
    ]
    cfo = facts["CP-1.fin.TDG:CFO:FY2024Q2"]
    assert cfo == {
        "fact_id": "CP-1.fin.TDG:CFO:FY2024Q2",
        "module": "CP-1",
        "topic": "financial_gold",
        "subject": "CFO",
        "field": "CFO",
        "period_end": "2024-03-30",
        "status": "known",
        "value": "229",
        "value_type": "decimal",
        "unit": "USD",
        "scale": "millions",
        "evidence": [],
        "derivation": None,
        "gap_reason": None,
    }
    # unit_scale (3 here) is the source display scale; it must not move the magnitude.
    bgs = facts["CP-1.fin.BGS:FY2024Q2:revenue"]
    assert (bgs["value"], bgs["scale"]) == ("461.073", "millions")


def test_financial_gold_refuses_unreadable_unit() -> None:
    gold = json.loads(FIXTURE.read_text(encoding="utf-8"))
    gold["facts"][0]["canonical_unit"] = "dollars"
    with pytest.raises(CaseError, match="cannot read unit"):
        financial_gold_facts(gold)
    gold = json.loads(FIXTURE.read_text(encoding="utf-8"))
    gold["facts"][1]["stable_fact_id"] = "TDG:CFO:FY2024Q2"
    with pytest.raises(CaseError, match="repeats"):
        financial_gold_facts(gold)


def _case_of(facts: dict[str, dict[str, Any]]) -> GoldenCase:
    return GoldenCase(
        case_id="small",
        pathway="credit_snapshot",
        case_dir=FIXTURE.parent,
        context_path=FIXTURE.parent / "context.json",
        facts=MappingProxyType(facts),
        out_of_plan=MappingProxyType({}),
        financial_gold_path=FIXTURE,
        financial_gold_sha256="0" * 64,
    )


def _score_one(fid: str, **fact_kw: Any) -> str:
    """Outcome of one CP-1 fact scored through a real mapping entry."""
    case = _case_of(_fixture_facts())
    loc = Locator(table_id="t", row_id="r", field="f", period="2024-03-30")
    entry = MappingEntry(fact_id=fid, module="CP-1", locator=loc)
    cite = Citation(source_id="s", source_sha256="b" * 64, locator="p1", quote="q")
    fact = Fact(
        fact_id="f-r",
        label="x",
        table_id="t",
        row_id="r",
        field="f",
        period="2024-03-30",
        citations=(cite,),
        **fact_kw,
    )
    module = Module(
        run_id="r", issuer_id="i", as_of=date(2025, 1, 1), module_id="CP-1", facts=(fact,)
    )
    mapping = Mapping(
        schema_version="golden-mapping/1",
        case_id="small",
        preparer="alice",
        reviewer="bob",
        module_commits={"CP-1": "a" * 40},
        entries=(entry,),
        unmapped=(),
    )
    score = score_module(module, "CP-1", "accepted", case, mapping, frozenset())
    only = [f for f in score.facts if f.fact_id == fid]
    return only[0].outcome


def test_financial_gold_units_scale() -> None:
    fid = "CP-1.fin.TDG:CFO:FY2024Q2"
    assert _score_one(fid, amount=Decimal(229000000), scale=Decimal(1), unit="USD") == "match"
    assert _score_one(fid, amount=Decimal(229), scale=Decimal(1000000), unit="USD") == "match"
    assert _score_one(fid, amount=Decimal(229), scale=Decimal(1), unit="USD") == "mismatch"
    bgs = "CP-1.fin.BGS:FY2024Q2:revenue"  # unit_scale 3 must not make this thousands
    assert _score_one(bgs, amount=Decimal("461.073"), scale=Decimal(1000000), unit="USD") == "match"


def test_financial_gold_status_carried() -> None:
    facts = _fixture_facts()
    assert facts["CP-1.fin.TDG:principal:FY2024Q2"]["status"] == "missing"
    assert facts["CP-1.fin.TDG:principal:FY2024Q2"]["value"] is None
    assert facts["CP-1.fin.TDG:principal:FY2024Q2"]["gap_reason"] == (
        "not in the limited source corpus"
    )
    conflict = facts["CP-1.fin.NATL:FY2025Q1:adjusted_EBITDA"]
    assert conflict["status"] == "conflicting"
    assert [e["printed"] for e in conflict["evidence"]] == ["175 million", "172 million"]
    fid = "CP-1.fin.TDG:principal:FY2024Q2"
    assert _score_one(fid, status="missing", limitation="n/a") == "gap_ok"
    nat = "CP-1.fin.NATL:FY2025Q1:adjusted_EBITDA"
    both = {"amount": Decimal(175), "scale": Decimal(1000000), "unit": "USD", "limitation": "x"}
    assert _score_one(nat, **both) == "conflict_ok"
