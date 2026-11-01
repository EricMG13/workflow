from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from deploy_workflow.model_testing.cases import CaseError, load_case
from deploy_workflow.model_testing.configs import CASES

ROOT = Path(__file__).resolve().parents[1]
GOLDENS = ROOT / "cases" / "goldens"
CORPUS = Path("/Users/ericguei/Documents/Deploy Workflow/artifacts/public-corpus/v1")

pytestmark = pytest.mark.skipif(
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


def test_loads_every_golden() -> None:
    for d in CASES.values():
        c = load_case(GOLDENS / d, CORPUS)
        assert c.facts and c.context_path.name == "context.json"
        assert c.financial_gold_path.is_file()


def test_copied_case_loads(tmp_path: Path) -> None:
    c = load_case(_copy_case(tmp_path, "shc-earnings-update"), CORPUS)
    assert c.pathway == "earnings_update"


def test_refuses_changed_financial_gold(tmp_path: Path) -> None:
    case = _copy_case(tmp_path, "shc-earnings-update")
    with (tmp_path / "financial_gold.json").open("ab") as f:
        f.write(b" ")
    with pytest.raises(CaseError, match=r"financial_gold.*sha256"):
        load_case(case, CORPUS)


def test_refuses_failing_checker(tmp_path: Path) -> None:
    case = _copy_case(tmp_path, "shc-earnings-update")
    p = case / "module_golden.json"
    golden = json.loads(p.read_text())
    evidence = golden["facts"][0]["evidence"][0]
    evidence["quote"] = evidence["quote"] + " not in the filing"
    p.write_text(json.dumps(golden))
    with pytest.raises(CaseError, match=r"check\.py"):
        load_case(case, CORPUS)


def test_refuses_context_the_product_refuses(tmp_path: Path) -> None:
    case = _copy_case(tmp_path, "tdg-credit-snapshot")
    p = case / "context.json"
    text = p.read_text()
    assert '"issuer_id": "tdg"' in text
    p.write_text(text.replace('"issuer_id": "tdg"', '"issuer_id": "-tdg"'))
    with pytest.raises(CaseError, match=r"context\.json"):
        load_case(case, CORPUS)


def test_natl_cp4_out_of_plan() -> None:
    c = load_case(GOLDENS / "natl-portfolio-decision", CORPUS)
    assert c.out_of_plan == {"CP-4": 51}
    assert not any(f["module"] == "CP-4" for f in c.facts.values())


def test_other_cases_have_nothing_out_of_plan() -> None:
    for d in CASES.values():
        if d != "natl-portfolio-decision":
            assert load_case(GOLDENS / d, CORPUS).out_of_plan == {}
