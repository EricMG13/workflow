"""Item 82: an absent-input reconciliation check is a stated limitation on a public filed pack.

A public case whose reconciliation check cannot be computed because an input is absent (no
difference, no conflicting term, no FX-normalised term) is a WARN gap with the item-82 prefix,
so CP-1 promotes as QA Restricted instead of Blocked. A check that computes and disagrees, a
conflicting observation and any non-public case still block. Expectations come from the rulings
(`docs/rulings/2026-10-29-stage3.md` items 75, 82, 83), not from the code under test.
"""

import importlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from deploy_vii import cp1_workflow, downstream_readiness, narrative
from deploy_vii.cp1_workflow import is_qa_blocked, qa_blocked_issue
from deploy_vii.execution import Execution
from deploy_vii.financial_reconciliation import Reconciliation, ReconciliationTerm
from deploy_vii.preparation import PreparedPack

financial: Any = importlib.import_module("test_financial_workflow")
ROOT = Path(__file__).resolve().parents[1]
PARTIAL = ROOT / "cases/czr-2026q2-earnings-update/submissions-partial.json"
PREFIX = "Absent input, stated as a limitation on a public filed pack (rulings item 82): "
SYNTHETIC_PREFIXED_GAPS = 11
CZR_PREFIXED_GAPS = 135
HEAD_LEAD = "CP-1 QA Restricted:"


def _case_as(monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    """The synthetic financial case with `run.case_kind=kind` and segment disclosure partial."""
    make_pack = financial.make_pack
    books = financial.financials

    def pack(gap: bool = False) -> PreparedPack:
        original = make_pack(gap)
        return PreparedPack(
            run=original.run.model_copy(update={"case_kind": kind}), sources=original.sources
        )

    def partial(prepared: PreparedPack) -> dict[str, Any]:
        document = books(prepared)
        document["financial"]["books"][0]["segment_disclosure"]["status"] = "partial"
        return document

    monkeypatch.setattr(financial, "make_pack", pack)
    monkeypatch.setattr(financial, "financials", partial)


class _Spy:
    """The last narrative report and the last `QualityInputs` the run built."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.report: Any = None
        self.inputs: Any = None
        real_narrative = narrative.canonical_narrative
        real_inputs = cp1_workflow.cp1_quality_inputs

        def spy_narrative(*args: Any, **kwargs: Any) -> Any:
            self.report = real_narrative(*args, **kwargs)
            return self.report

        def spy_inputs(registers: Any) -> Any:
            self.inputs = real_inputs(registers)
            return self.inputs

        monkeypatch.setattr(narrative, "canonical_narrative", spy_narrative)
        monkeypatch.setattr(downstream_readiness, "canonical_narrative", spy_narrative)
        monkeypatch.setattr(cp1_workflow, "cp1_quality_inputs", spy_inputs)


def _promote(root: Path) -> dict[str, Any]:
    workflow, raw_qa, _score = financial.quality_ready_case(root)
    return workflow.submit_review(json.dumps(raw_qa))


def _handoff(root: Path) -> Any:
    store = Execution(root / "store")
    attempt = next(a for a in store.read().attempts if a.module_id == "CP-1")
    return cp1_workflow.CP1Handoff.model_validate_json(
        store.step_output(attempt.steps[-1].output_sha256)
    )


def test_public_absent_input_is_a_limitation_not_a_qa_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _case_as(monkeypatch, "public")
    spy = _Spy(monkeypatch)
    outcome = _promote(tmp_path)
    assert outcome["status"] == "valid", outcome
    confidence = _handoff(tmp_path).quality.confidence
    assert confidence.qa_status == "Restricted"
    assert confidence.confidence_score <= 59
    prefixed = [g for g in spy.report.gaps if g.description.startswith(PREFIX)]
    assert len(prefixed) == SYNTHETIC_PREFIXED_GAPS
    assert {g.severity for g in prefixed} == {"WARN"}
    store = Execution(tmp_path / "store")
    head = next(h for h in store.read().heads if h.module_id == "CP-1")
    module = store.head_module(head)
    cells = [f for f in module.facts if f.table_id == "T4.12" and (f.text or "").startswith(PREFIX)]
    assert len(cells) == SYNTHETIC_PREFIXED_GAPS
    assert module.limitations[0].startswith(HEAD_LEAD)


def test_downgrade_restricts_not_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _case_as(monkeypatch, "public")
    spy = _Spy(monkeypatch)
    outcome = _promote(tmp_path)
    assert outcome["status"] == "valid", outcome
    assert spy.report.status == "restricted"
    assert [g for g in spy.report.gaps if g.severity == "BLOCK"] == []
    assert spy.inputs.module_status == "restricted"
    assert _handoff(tmp_path).quality.confidence.qa_status != "Passed"


def test_public_disagreeing_cash_check_still_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    czr_runs = importlib.import_module("czr_runs")
    spy = _Spy(monkeypatch)
    with pytest.raises(RuntimeError) as raised:
        czr_runs.czr_closed(tmp_path, PARTIAL)
    assert qa_blocked_issue(39, "Insufficient Information") in str(raised.value)
    gaps = spy.report.gaps
    blocking = [g for g in gaps if g.severity == "BLOCK"]
    assert len(blocking) == 3
    gates = [g for g in blocking if g.origin == "calculation_gate"]
    cash = [g for g in blocking if g.origin != "calculation_gate"]
    assert len(gates) == 1
    assert len(cash) == 2
    assert all("NCF_CASH_MOVEMENT" in g.model_dump_json() for g in cash)
    assert sum("fy-2025" in g.model_dump_json() for g in cash) == 1
    assert sum("h1-2026" in g.model_dump_json() for g in cash) == 1
    warned = [g for g in gaps if g.description.startswith(PREFIX)]
    assert len(warned) == CZR_PREFIXED_GAPS
    assert {g.severity for g in warned} == {"WARN"}


def test_synthetic_case_still_blocks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _case_as(monkeypatch, "synthetic")
    outcome = _promote(tmp_path)
    assert outcome["status"] != "valid"
    assert len(outcome["issues"]) == 1
    assert is_qa_blocked(outcome["issues"][0])


def _term(
    label: str, amount: str | None, observation_id: str, *, normalization: Any = None
) -> ReconciliationTerm:
    return ReconciliationTerm.model_construct(
        label=label,
        observation_id=observation_id,
        original_amount=None if amount is None else Decimal(amount),
        amount=None if amount is None else Decimal(amount),
        coefficient=1,
        reason="not supplied" if amount is None else None,
        citations=(),
        normalization=normalization,
    )


def _check(
    *, status: str = "BLOCK", difference: str | None = None, normalization: Any = None
) -> Reconciliation:
    return Reconciliation.model_construct(
        check_id="chk-1",
        period_id="fy-2025",
        reported=_term("Reported total", "10", "obs-reported", normalization=normalization),
        components=(_term("Component A", None, "obs-a"), _term("Component B", "4", "obs-b")),
        difference=None if difference is None else Decimal(difference),
        status=status,
        explanation="Check cannot be computed",
    )


def test_absent_input_limitation_refuses_non_absent_cases() -> None:
    from deploy_vii.canonical_audit import ABSENT_INPUT_PREFIX, absent_input_limitation

    assert ABSENT_INPUT_PREFIX == PREFIX
    nothing: frozenset[str] = frozenset()

    def helper(
        check: Reconciliation, *, public: bool = True, conflicting: frozenset[str] = nothing
    ) -> str | None:
        return absent_input_limitation(check, public=public, conflicting=conflicting)

    assert helper(_check(difference="3")) is None
    assert helper(_check(), conflicting=frozenset({"obs-b"})) is None
    assert helper(_check(normalization="fx")) is None
    assert helper(_check(), public=False) is None
    assert helper(_check(status="WARN")) is None
    text = helper(_check())
    assert text is not None
    assert text.startswith(PREFIX + "Check cannot be computed")
    assert "Component A (not supplied)" in text
