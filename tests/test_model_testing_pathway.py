"""Pathway score from a run directory (Task 8).

Receipt-bearing directories come from a genuine G1 owner run (``test_financial_workflow``: CP-0
submitted twice, the first submission invalid, then the CP-1 gap refusal), rendered with the real
``render_owner_slice``; ``run.json`` is written by the test because the O2 offline walk cannot
settle a rendered delivery inside the fast-test budget (it stops at ``owner_render_scope``).
Stopped directories come from the O2 synthetic case through ``tests/o2_case.py``.
"""

from __future__ import annotations

import importlib
import json
import shutil
from collections.abc import Iterator, Sequence
from collections.abc import Mapping as MappingABC
from pathlib import Path
from types import MappingProxyType
from typing import Any

import o2_case
import pytest

from deploy_vii.contracts import PATHWAY_MODULES
from deploy_vii.execution import Execution
from deploy_workflow.model_testing.cases import CaseError, GoldenCase
from deploy_workflow.model_testing.mapping import Locator, Mapping, MappingEntry
from deploy_workflow.model_testing.pathway import PathwayScore, score_run
from deploy_workflow.model_testing.records import JournalError
from deploy_workflow.owner_rendering import render_owner_slice
from deploy_workflow.owner_workflow import OwnerRunReceipt, OwnerWorkflow

fw: Any = importlib.import_module("test_financial_workflow")
SHA = "a" * 40
GAP_CASE = "g1x-gap-case"
OBJECTIVE = "CP-0.run.objective"
CP1_FACT = "CP-1.revenue.total"
MODEL_FACT = "CP-MODEL.model.ebitda"


def _golden_fact(fact_id: str, status: str, value: str | None, value_type: str) -> dict[str, Any]:
    return {
        "fact_id": fact_id,
        "module": fact_id.split(".")[0],
        "status": status,
        "value": value,
        "value_type": value_type,
        "unit": None,
        "scale": "units",
        "evidence": [],
    }


def _case(case_id: str, pathway: Any, facts: Sequence[MappingABC[str, Any]]) -> GoldenCase:
    return GoldenCase(
        case_id=case_id,
        pathway=pathway,
        case_dir=Path("c"),
        context_path=Path("c/context.json"),
        golden=MappingProxyType({}),
        facts=MappingProxyType({f["fact_id"]: f for f in facts}),
        out_of_plan=MappingProxyType({}),
        financial_gold_path=Path("g.json"),
        financial_gold_sha256="0" * 64,
    )


def _entry(fact_id: str, row: str, field: str) -> MappingEntry:
    return MappingEntry(
        fact_id=fact_id,
        module=fact_id.split(".")[0],
        locator=Locator(table_id="T1", row_id=row, field=field, period=None),
    )


def _mapping(case_id: str, entries: list[MappingEntry]) -> Mapping:
    return Mapping(
        schema_version="golden-mapping/1",
        case_id=case_id,
        preparer="alice",
        reviewer="bob",
        module_commits={e.module: SHA for e in entries},
        entries=tuple(entries),
        unmapped=(),
    )


def _gap_case(model_value: str | None = None) -> tuple[GoldenCase, Mapping]:
    """CP-0 objective is known; CP-1 is refused by the run; CP-MODEL never runs. With
    ``model_value`` the CP-MODEL fact is a known number the absent module cannot supply."""
    model = (
        _golden_fact(MODEL_FACT, "missing", None, "decimal")
        if model_value is None
        else _golden_fact(MODEL_FACT, "known", model_value, "decimal")
    )
    facts = [
        _golden_fact(OBJECTIVE, "known", "Historical financial foundation", "text"),
        _golden_fact(CP1_FACT, "missing", None, "decimal"),
        model,
    ]
    entries = [
        _entry(OBJECTIVE, "run", "objective"),
        _entry(CP1_FACT, "revenue", "total"),
        _entry(MODEL_FACT, "model", "ebitda"),
    ]
    return _case(GAP_CASE, "credit_snapshot", facts), _mapping(GAP_CASE, entries)


def _write_run_json(run_dir: Path, run_id: str) -> None:
    body = {
        "case_id": GAP_CASE,
        "pathway": "credit_snapshot",
        "config_id": "sol-medium",
        "run_id": run_id,
        "mode": "offline",
        "cap_usd": "1",
        "sources": [],
        "cp_dr_invoked": False,
        "replayed_from_run": None,
        "outcome": "settled",
        "stopped_reason": None,
    }
    (run_dir / "run.json").write_text(json.dumps(body), encoding="utf-8")


@pytest.fixture(scope="module")
def gap_run(tmp_path_factory: pytest.TempPathFactory) -> Path:
    run_dir = tmp_path_factory.mktemp("pathway") / "run"
    run_dir.mkdir()
    pack = fw.make_pack(True)
    workflow = OwnerWorkflow.create(
        run_dir / "execution", pack, publication_directory=run_dir / "publication"
    )
    fw.read_sources(workflow, gap=True)
    bad = json.loads(fw.readiness(pack, gap=True))
    bad["objective"] = ""
    assert workflow.submit_review(json.dumps(bad))["status"] == "invalid"
    fw.read_sources(workflow, gap=True)  # a repair attempt reads again
    assert workflow.submit_review(fw.readiness(pack, gap=True))["status"] == "valid"
    assert workflow.publish()["status"] == "refused"
    receipt = workflow.write_receipt(run_dir / "owner-run.json")
    render_owner_slice(
        run_dir / "execution", run_dir / "owner-run.json", None, run_dir / "delivery"
    )
    _write_run_json(run_dir, receipt.run.run_id)
    return run_dir


@pytest.fixture
def gap_copy(gap_run: Path, tmp_path: Path) -> Path:
    target = tmp_path / "run"
    shutil.copytree(gap_run, target)
    return target


def _tree(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()
    }


def test_scores_plan_order(gap_run: Path) -> None:
    case, mapping = _gap_case()
    before = _tree(gap_run)
    score = score_run(gap_run, case, mapping)
    assert isinstance(score, PathwayScore)
    assert [m.module_id for m in score.modules] == ["CP-0", "CP-1", "CP-MODEL"]
    assert [m.head_status for m in score.modules] == ["restricted", "refused", "absent"]
    cp0 = score.modules[0]
    assert [(f.fact_id, f.outcome) for f in cp0.facts] == [(OBJECTIVE, "match")]
    assert score.modules[1].facts[0].outcome == "gap_ok"
    assert score.rendered is True
    assert all(m.passed for m in score.modules)
    assert score.passed is True
    assert (score.run_id, score.case_id, score.pathway) == (
        "slice-cp1-model-gap",
        GAP_CASE,
        "credit_snapshot",
    )
    assert _tree(gap_run) == before  # the framework writes nothing


def test_retry_uses_settled_head_only(gap_run: Path) -> None:
    store = Execution(gap_run / "execution")
    snapshot = store.read()
    cp0 = [a for a in snapshot.attempts if a.module_id == "CP-0"]
    assert [a.number for a in cp0] == [0, 1] and len(snapshot.heads) == 1
    receipt = OwnerRunReceipt.model_validate_json((gap_run / "owner-run.json").read_text())
    assert [h.ticket_id for h in receipt.heads] == [cp0[1].ticket_id]
    case, mapping = _gap_case()
    score = score_run(gap_run, case, mapping)
    observed = score.modules[0].facts[0].observed
    assert observed == store.result(receipt.heads[0].result_sha256).facts[0].text
    assert observed == "Historical financial foundation"  # the repaired attempt, not the first
    assert [m.module_id for m in score.modules].count("CP-0") == 1


def test_tampered_delivery_not_rendered(gap_copy: Path) -> None:
    case, mapping = _gap_case()
    report = gap_copy / "delivery" / "report.html"
    raw = bytearray(report.read_bytes())
    raw[len(raw) // 2] ^= 0x01
    report.write_bytes(bytes(raw))
    score = score_run(gap_copy, case, mapping)
    assert score.rendered is False
    assert all(m.passed for m in score.modules)
    assert score.passed is False


def test_missing_delivery_not_rendered(gap_copy: Path) -> None:
    case, mapping = _gap_case()
    shutil.rmtree(gap_copy / "delivery")
    score = score_run(gap_copy, case, mapping)
    assert score.rendered is False and score.passed is False


def test_refused_module_without_named_inputs_fails(gap_run: Path) -> None:
    """CP-1 is refused by the run; a known golden fact there is not excused by a refusal that
    names nothing, so the module fails and so does the run (CP-MODEL is judgment: never fails)."""
    facts = [_golden_fact(CP1_FACT, "known", "5", "decimal")]
    case = _case(GAP_CASE, "credit_snapshot", facts)
    mapping = _mapping(GAP_CASE, [_entry(CP1_FACT, "revenue", "total")])
    score = score_run(gap_run, case, mapping)
    cp1 = score.modules[1]
    assert (cp1.module_id, cp1.head_status) == ("CP-1", "refused")
    assert [f.outcome for f in cp1.facts] == ["missing_in_output"]
    assert cp1.passed is False and score.passed is False and score.rendered is True


def test_refusal_names_flow_to_the_module(gap_run: Path) -> None:
    case, mapping = _gap_case()
    plain = score_run(gap_run, case, mapping)
    assert plain.modules[1].facts[0].observed is None
    named = score_run(gap_run, case, mapping, refusals={"CP-1": ("financial source",)})
    assert named.modules[1].facts[0].observed == "refused: financial source"
    assert named.passed is True


def test_reads_outcome_and_mode_from_run_json(gap_copy: Path) -> None:
    case, mapping = _gap_case()
    body = json.loads((gap_copy / "run.json").read_text())
    body.update(
        outcome="stopped",
        stopped_reason="BudgetExhausted: cap",
        config_id="opus-medium",
        run_id="copied-run-id",
    )
    (gap_copy / "run.json").write_text(json.dumps(body))
    score = score_run(gap_copy, case, mapping)
    assert score.outcome == "stopped" and score.stopped_reason == "BudgetExhausted: cap"
    assert score.mode == "offline" and score.ruling_sha256 is None
    assert score.config_id == "opus-medium" and score.run_id == "copied-run-id"
    assert score.passed is False  # stopped, whatever the modules scored
    assert all(m.passed for m in score.modules)


def test_live_ruling_copied(gap_copy: Path) -> None:
    case, mapping = _gap_case()
    body = json.loads((gap_copy / "run.json").read_text())
    body.update(mode="live", ruling_path="r.md", ruling_sha256="c" * 64, ruling_date="2026-11-01")
    (gap_copy / "run.json").write_text(json.dumps(body))
    score = score_run(gap_copy, case, mapping)
    assert score.mode == "live" and score.ruling_sha256 == "c" * 64


def test_unreadable_run_json_is_a_journal_error(tmp_path: Path) -> None:
    case, mapping = _gap_case()
    with pytest.raises(JournalError):
        score_run(tmp_path, case, mapping)


def test_case_mismatch_refused(gap_run: Path) -> None:
    case, mapping = _gap_case()
    wrong_id = _case("other-case", "credit_snapshot", list(case.facts.values()))
    with pytest.raises(CaseError, match="is case"):
        score_run(gap_run, wrong_id, mapping)
    wrong_path = _case(GAP_CASE, "portfolio_decision", list(case.facts.values()))
    with pytest.raises(CaseError, match="is pathway"):
        score_run(gap_run, wrong_path, mapping)


# ------------------------------------------------------------------ stopped runs (O2 synthetic)


@pytest.fixture(scope="module")
def stopped_run(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    root = tmp_path_factory.mktemp("o2-stopped")
    authored = o2_case.author(root / "authoring", answers=("source_readiness",))
    assert authored.outcome.outcome == "stopped"
    replayed = o2_case.replay(root / "replay", authored.recordings)
    assert replayed.stopped_reason is not None
    assert replayed.stopped_reason.startswith("RecordingMissing")
    yield replayed.run_dir


def _o2_case() -> tuple[GoldenCase, Mapping]:
    fact = _golden_fact("CP-1.revenue.total", "missing", None, "decimal")
    case = _case(o2_case.CASE_ID, o2_case.PATHWAY, [fact])
    return case, _mapping(o2_case.CASE_ID, [_entry(fact["fact_id"], "revenue", "total")])


def test_stopped_run_without_receipt(stopped_run: Path) -> None:
    assert not (stopped_run / "owner-run.json").exists()
    case, mapping = _o2_case()
    score = score_run(stopped_run, case, mapping)
    expected = PATHWAY_MODULES["portfolio_decision"]
    assert tuple(m.module_id for m in score.modules) == expected
    assert all(m.head_status == "absent" for m in score.modules)
    assert score.outcome == "stopped"
    assert score.stopped_reason is not None and score.stopped_reason.startswith("RecordingMissing")
    assert score.rendered is False and score.passed is False
    assert score.run_id == o2_case.RUN_ID and score.config_id == "opus-medium"
    assert score.mode == "offline" and score.ruling_sha256 is None


def test_absent_module_fails(stopped_run: Path) -> None:
    fact = _golden_fact("CP-1.revenue.total", "known", "5", "decimal")
    case = _case(o2_case.CASE_ID, o2_case.PATHWAY, [fact])
    mapping = _mapping(o2_case.CASE_ID, [_entry(fact["fact_id"], "revenue", "total")])
    score = score_run(stopped_run, case, mapping)
    cp1 = next(m for m in score.modules if m.module_id == "CP-1")
    assert cp1.head_status == "absent"
    assert [f.outcome for f in cp1.facts] == ["missing_in_output"]
    assert cp1.passed is False


def test_stopped_run_case_mismatch(stopped_run: Path) -> None:
    case, mapping = _o2_case()
    wrong = _case("not-o2", o2_case.PATHWAY, list(case.facts.values()))
    with pytest.raises(CaseError):
        score_run(stopped_run, wrong, mapping)
