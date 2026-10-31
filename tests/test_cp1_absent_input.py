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

from deploy_vii import canonical_audit, cp1_workflow, downstream_readiness, narrative
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
SHADOW_ID = "revenue-shadow-q2"


def _case_as(
    monkeypatch: pytest.MonkeyPatch, kind: str, *, partial: bool = True, shadow: bool = False
) -> None:
    """The synthetic financial case with `run.case_kind=kind`.

    `partial` sets segment disclosure partial. `shadow` makes a real disagreement (q2-2025 segment
    revenue 31 against revenue 30) and adds an explicit missing revenue account for q2-2025 that
    shadows the known printed income-statement line."""
    make_pack = financial.make_pack
    books = financial.financials

    def pack(gap: bool = False) -> PreparedPack:
        original = make_pack(gap)
        return PreparedPack(
            run=original.run.model_copy(update={"case_kind": kind}), sources=original.sources
        )

    def partial(prepared: PreparedPack) -> dict[str, Any]:
        document = books(prepared)
        book = document["financial"]["books"][0]
        if partial:
            book["segment_disclosure"]["status"] = "partial"
        if shadow:
            segment = next(x for x in book["segments"] if x["period_id"] == "q2-2025")
            segment["revenue"]["amount"] = "31"
            line = next(
                x
                for x in book["statement_lines"]
                if x["period_id"] == "q2-2025" and x["label"] == "Revenue"
            )
            book["accounts"].append(
                {
                    "metric_id": "revenue",
                    "period_id": "q2-2025",
                    "value": {
                        "observation_id": SHADOW_ID,
                        "status": "missing",
                        "amount": None,
                        "citations": line["value"]["citations"],
                        "reason": "Not printed in the filing",
                    },
                }
            )
        return document

    monkeypatch.setattr(financial, "make_pack", pack)
    monkeypatch.setattr(financial, "financials", partial)


class _Spy:
    """The last narrative report and the last `QualityInputs` the run built."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.report: Any = None
        self.inputs: Any = None
        self.checks: dict[str, Any] = {}
        real_reconcile = canonical_audit.reconcile_financials
        real_narrative = narrative.canonical_narrative
        real_inputs = cp1_workflow.cp1_quality_inputs

        def spy_narrative(*args: Any, **kwargs: Any) -> Any:
            self.report = real_narrative(*args, **kwargs)
            return self.report

        def spy_reconcile(*args: Any, **kwargs: Any) -> Any:
            report = real_reconcile(*args, **kwargs)
            self.checks.update({c.check_id: c for c in report.checks})
            return report

        def spy_inputs(registers: Any) -> Any:
            self.inputs = real_inputs(registers)
            return self.inputs

        monkeypatch.setattr(narrative, "canonical_narrative", spy_narrative)
        monkeypatch.setattr(downstream_readiness, "canonical_narrative", spy_narrative)
        monkeypatch.setattr(cp1_workflow, "cp1_quality_inputs", spy_inputs)
        monkeypatch.setattr(canonical_audit, "reconcile_financials", spy_reconcile)


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
    texts = {f.text for f in module.facts if f.table_id == "T4.12"}
    assert sum(PREFIX in (t or "") for t in texts) == SYNTHETIC_PREFIXED_GAPS
    for g in prefixed:
        assert f"{g.gap_id}: {g.description}" in texts
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
    identity = {k: (c.check_type, c.period_id) for k, c in spy.checks.items()}
    assert {identity[g.metric] for g in cash} == {
        ("NCF_CASH_MOVEMENT", "fy-2025"),
        ("NCF_CASH_MOVEMENT", "h1-2026"),
    }
    warned = [g for g in gaps if g.description.startswith(PREFIX)]
    assert len(warned) == CZR_PREFIXED_GAPS
    assert {g.severity for g in warned} == {"WARN"}


def test_synthetic_case_still_blocks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _case_as(monkeypatch, "synthetic")
    outcome = _promote(tmp_path)
    assert outcome["status"] != "valid"
    assert len(outcome["issues"]) == 1
    assert is_qa_blocked(outcome["issues"][0])


def test_shadowing_missing_account_keeps_the_disagreement_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M1: an explicit missing account that shadows a known printed line must not turn a real
    disagreement into an absent-input limitation."""
    _case_as(monkeypatch, "public", partial=False, shadow=True)
    spy = _Spy(monkeypatch)
    outcome = _promote(tmp_path)
    assert outcome["status"] != "valid", outcome
    assert len(outcome["issues"]) == 1
    assert is_qa_blocked(outcome["issues"][0])
    assert [g for g in spy.report.gaps if g.severity == "BLOCK"] != []
    citing = {
        k
        for k, c in spy.checks.items()
        if SHADOW_ID in {t.observation_id for t in (c.reported, *c.components)}
    }
    assert citing
    assert [g for g in spy.report.gaps if g.metric in citing and PREFIX in g.description] == []


def _period_term(label: str, amount: str | None, observation_ids: tuple[str, ...]) -> Any:
    from deploy_vii.period_reconciliation import PeriodTerm

    return PeriodTerm.model_construct(
        label=label,
        value_id=None,
        amount=None if amount is None else Decimal(amount),
        coefficient=1,
        observation_ids=observation_ids,
        citations=(),
        reason="not supplied" if amount is None else None,
    )


def _period_check() -> Any:
    from deploy_vii.period_reconciliation import PeriodCheck

    return PeriodCheck.model_construct(
        check_id="pc-1",
        construction_id="c-1",
        reported=_period_term("Reported total", "10", ("obs-reported",)),
        components=(
            _period_term("Component A", None, ("obs-a",)),
            _period_term("Component B", "4", ("obs-b",)),
        ),
        difference=None,
        status="BLOCK",
        explanation="Reported value or independent components are unavailable",
    )


def test_child_difference_blocker_is_not_an_absent_input() -> None:
    """L1: a parent whose blocker quotes a child's computed difference (as
    `financial_reconciliation.py:486` builds it) stays BLOCK."""
    from deploy_vii.canonical_audit import absent_input_limitation

    child = "Difference exceeds reporting-precision tolerance; unresolved"
    check = _check().model_copy(update={"explanation": f"cfs-ncfo: {child}"})
    none: frozenset[str] = frozenset()
    result = absent_input_limitation(
        check, public=True, conflicting=none, shadowed=none, normalised=none
    )
    assert result is None


def test_period_term_with_fx_normalised_id_is_not_an_absent_input() -> None:
    """L2: the period hop sees FX normalisation through the ids that feed it."""
    from deploy_vii.canonical_audit import absent_input_limitation

    check = _period_check()
    kwargs: dict[str, Any] = {"public": True, "conflicting": frozenset(), "shadowed": frozenset()}
    assert absent_input_limitation(check, normalised=frozenset({"obs-a"}), **kwargs) is None
    text = absent_input_limitation(check, normalised=frozenset({"obs-other"}), **kwargs)
    assert text is not None
    assert text.startswith(PREFIX)


def test_shadowed_account_id_is_not_an_absent_input() -> None:
    """M1 unit: a term citing a shadowed explicit account id stays BLOCK at both hops."""
    from deploy_vii.canonical_audit import absent_input_limitation

    kwargs: dict[str, Any] = {
        "public": True,
        "conflicting": frozenset(),
        "normalised": frozenset(),
        "shadowed": frozenset({"obs-b"}),
    }
    assert absent_input_limitation(_check(), **kwargs) is None
    assert absent_input_limitation(_period_check(), **kwargs) is None
    kwargs["shadowed"] = frozenset({"obs-elsewhere"})
    assert absent_input_limitation(_check(), **kwargs) is not None
    assert absent_input_limitation(_period_check(), **kwargs) is not None


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
