"""Phase 8 end batch 1: Low findings of the closed Task 1, 3, 4 and 7 reviews."""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path

import chart_wiring_c as w
import pytest
import test_connect_cp1d as conn
import test_connect_cp3c as tc3
import test_method_cp1d as stage1
import test_method_cp3c as tm3
import test_owner_cp3c_pins as p3
import test_periods_currency_cp1d as t
import test_periods_currency_e2e_cp3c as a2
from test_period_basis import _calendar, _context

from deploy_vii.contracts import Fact, Input, Module
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare_source
from deploy_workflow import context as ctx
from deploy_workflow.liquidity_series import cp2d_chart_series
from deploy_workflow.owners import cp1d, cp2d, cp3c
from deploy_workflow.owners.period_basis import PeriodRefused, currency_basis, period_basis

# --- A: Task 1 r4a -------------------------------------------------------------------------------


def _without_unit(facts: list[Fact]) -> list[Fact]:
    return [fact for fact in facts if fact.field != "unit"]


@pytest.mark.parametrize("period", ["fy-2026", "q4-2026", "q3-2026"])
def test_currency_basis_refuses_a_row_with_no_unit_fact(period: str) -> None:
    """A: a T4.14 row with no `unit` fact is not skipped (the probe's `r4a` edge)."""
    with pytest.raises(PeriodRefused, match="unit is not MILLIONS"):
        currency_basis(_context(period), _without_unit(_calendar()))


def test_period_basis_refuses_a_row_with_no_unit_fact() -> None:
    with pytest.raises(PeriodRefused, match="unit is not MILLIONS"):
        period_basis(_context("fy-2026"), _without_unit(_calendar()))


# --- C: Task 3 L1 (cp1d fields compared with the key at run time) --------------------------------


def _eur_report() -> cp1d.EarningsQualityReport:
    text = json.dumps(t.SUBMISSIONS["modules"]["CP-1D@EUR"]["submission"]["earnings_quality"])
    bound = re.sub(r"\{\{FIG:([a-z_]+)\|([^}]+)\}\}", r"{t410-\1|\2}", text)
    return cp1d.earnings_quality(
        pack=t._eur_pack(),
        submission=cp1d.EarningsQualitySubmission.model_validate_json(bound),
        upstream=t._eur_upstream(),
    )


def test_eur_claims_equal_the_oracle_rows_with_limitation_and_evidence() -> None:
    result = cp1d.compute(t._eur_inputs(t._eur_basis()))
    assert stage1._claims(result) == t.ORACLE["claims"]


def test_eur_bridge_source_and_unavailable_operands_equal_the_oracle() -> None:
    result = cp1d.compute(t._eur_inputs(t._eur_basis()))
    assert result.bridge_source == cp1d.BridgeSourceRef(**t.ORACLE["bridge_source"])
    assert list(result.operands_unavailable) == t.ORACLE["operands_unavailable"]


def test_eur_report_claims_carry_the_oracle_limitation_and_evidence() -> None:
    """The report's claim text keeps its `{ref|unit}` bindings, so only the rows' limitation and
    evidence are compared with the key."""
    report = _eur_report()
    got = [
        (
            c.claim_id,
            c.limitation,
            [{**stage1._citation(e), "source_sha256": e.source_sha256} for e in c.citations],
        )
        for c in report.claims
    ]
    want = [
        (row["claim_id"], row["limitation"], row.get("evidence", [])) for row in t.ORACLE["claims"]
    ]
    assert got == want


def test_eur_report_amounts_equal_the_r3_run_oracle() -> None:
    run = t.EXPECTED["runs"]["R3"]["modules"]["CP-1D"]
    report = _eur_report()
    money = [f for f in report.facts if f.unit == "MILLIONS" and f.amount is not None]
    assert {f.currency for f in money} == {run["amount_fact_currency"]}
    own = [f for f in money if f.table_id != cp1d.CP1_REFERENCES]
    assert len(own) == run["millions_facts_checked_eur"]


# --- C: Task 3 L2 (refusals read at the validator) -----------------------------------------------


def _bound(up: cp1d.Upstream, cp1: Module) -> cp1d.Upstream:
    bound = tuple(
        Input(input_id=m.module_id, sha256=m.content_hash(), status="restricted")
        for m in (up.cp0, cp1)
    )
    return cp1d.Upstream(bound=bound, current=bound, cp0=up.cp0, cp1=cp1, cp1b=None, inherited=())


def test_validator_refuses_a_cp1_head_with_no_t414_register_as_one_line() -> None:
    up = t._eur_upstream()
    head = up.cp1.model_copy(
        update={"facts": tuple(f for f in up.cp1.facts if f.table_id != "T4.14")}
    )
    got = cp1d.validate_earnings_quality(
        pack=t._eur_pack(),
        submission=t._eur_inputs(t._eur_basis()).submission,
        upstream=_bound(up, head),
    )
    assert got == (
        "Period basis refused: run.reporting_currency EUR, but CP-1 T4.14 reports no currency",
    )


def test_validator_refuses_a_blank_base_usd_run_over_a_2026_head_at_selection() -> None:
    up = t._eur_upstream()
    document = json.loads(json.dumps(t.R3))
    document["run"].update(
        run_type="research", current_period="", prior_period="", reporting_currency="USD"
    )
    request = SourceRequest(source_id="context", path="context.json", media_type="text/plain")
    pack = PreparedPack(
        run=t._eur_pack().run,
        sources=(*t._eur_sources(), prepare_source(request, json.dumps(document).encode())),
    )
    got = cp1d.validate_earnings_quality(
        pack=pack, submission=t._eur_inputs(t._eur_basis()).submission, upstream=up
    )
    assert len(got) == 1
    assert got[0].startswith("CP-1 operands unavailable: ") and "0 facts" in got[0]


# --- D: Task 3 L1-view (the view carries the L1 currency refusal as context_issue, P8-R5) --------


def test_view_carries_the_cp1_amount_currency_refusal_as_context_issue() -> None:
    cp1 = conn._cp1_module()
    eur = cp1.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"currency": "EUR"}) if f.currency == "USD" else f
                for f in cp1.facts
            )
        }
    )
    pack, upstream = conn._pack("positive"), conn._upstream(eur)
    issues, report = cp1d._checked(pack, conn._submission("positive", eur), upstream)
    block = cp1d.context_block(pack=pack, upstream=upstream)
    assert report is None and len(issues) == 1
    assert block["context_issue"] == issues[0]
    assert block["cp1_facts"] == []


# --- E: Task 4 (cp3c `_lines` on a refused context over a 2026 CP-1) ------------------------------

CONTEXT_LINE = "Context refused: run.pathway"


def _refused_2026(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[PreparedPack, cp3c.RefinancingRiskSubmission, cp3c.Upstream]:
    """A CP-3C attempt settled under a USD fy-2026 run, read under a context that refuses."""
    usd = _context("fy-2026", "USD")
    monkeypatch.setattr(cp2d, "context_facts", lambda pack: usd)
    store, _ = tc3.make_store(
        tmp_path / "s", "positive", cp1=a2.cp1_for(tc3.make_pack().run, "USD")
    )
    upstream = tc3.upstream_of(store, store.begin("CP-3C"))
    names = dict(cp3c.select(upstream, cp2d.run_basis(store.pack(), upstream.cp1)).refs)
    payload = tc3.bound_payload(tm3.SUBMISSIONS["cp3c"]["positive"], names)
    submission = cp3c.RefinancingRiskSubmission.model_validate_json(json.dumps(payload))
    monkeypatch.setattr(cp2d, "context_facts", ctx.context_facts)
    other = p3._pack(tmp_path / "other", "context-credit_snapshot.json")
    return other, submission, upstream


def test_cp3c_validator_on_a_refused_context_over_a_2026_cp1_is_one_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack, submission, upstream = _refused_2026(tmp_path, monkeypatch)
    lines = cp3c._lines(pack, submission, upstream)
    assert len(lines) == 1 and lines[0].startswith(CONTEXT_LINE), lines


def test_cp3c_refused_context_over_a_2026_cp1_keeps_the_stale_or_provenance_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack, submission, upstream = _refused_2026(tmp_path, monkeypatch)
    stale = dataclasses.replace(upstream, current=())
    lines = cp3c._lines(pack, submission, stale)
    kept = cp3c._upstream_issues(stale)
    assert kept and len(lines) == len(kept) + 1, lines
    assert lines[: len(kept)] == kept and lines[-1].startswith(CONTEXT_LINE), lines
    assert len(cp3c._lines(pack, submission, upstream)) == 1


# --- F: Task 7 L5 (an all-unsettled CR.2 frame takes the run's currency) --------------------------

_BRIDGE = {"T2E.2.r01", "T2E.3.r05", "T2E.3.r06", "T2E.3.r07", "T2E.3.r08"}


@pytest.mark.parametrize(("currency", "axis"), [("EUR", "EUR m"), ("USD", "US$ m")])
def test_an_all_unsettled_cr2_frame_takes_the_run_currency(currency: str, axis: str) -> None:
    module = w.module_of(w.cp2d_view("positive"), "CP-2D")
    facts = []
    for fact in module.facts:
        if fact.currency == "USD":
            fact = fact.model_copy(update={"currency": currency})
        if fact.fact_id in _BRIDGE:
            fact = fact.model_copy(
                update={"status": "missing", "amount": None, "currency": None, "limitation": "w"}
            )
        facts.append(fact)
    (record,) = cp2d_chart_series(module.model_copy(update={"facts": tuple(facts)}))
    assert record.kind == "na" and record.axis_label == axis
