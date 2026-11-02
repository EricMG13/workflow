"""Probe C: the wrong-figure attacks on CP-2D and CP-3C under a non-default basis. Each test
asserts the safe outcome (a gap or a refusal naming the cause, or the right figure); exit 0 =
every attack is held. Keys: `cases/periods-currency-owner/expected.json#period_basis/EUR`,
`#module_oracles/CP-2D@EUR`, `t414.json#contexts/R2`.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import test_connect_cp2d as c2d
import test_connect_cp3c as tc3
import test_method_cp2d as tm2
import test_method_cp3c as tm3
import test_period_basis as tpb
import test_periods_currency_e2e_cp2d as a

from deploy_workflow.owners import cp2d, cp3c
from deploy_workflow.owners.period_basis import period_basis

EUR = a.BASIS


def _two_facilities(c1: str | None, c2: str | None) -> cp2d.Cp2dInputs:
    inputs = tm2._inputs("positive")
    (f1,) = inputs.operands.facilities or ()
    f2 = replace(f1, facility_id="f2", name="Second loan")
    ops = replace(inputs.operands, facilities=(replace(f1, currency=c1), replace(f2, currency=c2)))
    return replace(inputs, operands=ops, basis=EUR)


def test_mixed_facility_currencies_never_sum_a_foreign_principal() -> None:
    r = cp2d.compute(_two_facilities("EUR", "USD"))
    b = r.bridge
    fx = "Not calculable: facility f2 is in USD, not EUR; no FX conversion is applied"
    assert isinstance(b.maturities_in_horizon, cp2d.Gap) and b.maturities_in_horizon.reason == fx
    assert isinstance(b.amortisation_in_horizon, cp2d.Gap)
    assert isinstance(b.funding_gap, cp2d.Gap)
    rows = {w.facility.facility_id: w for w in b.wall}
    assert rows["term-loan"].principal == Decimal(50)
    assert isinstance(rows["f2"].principal, cp2d.Gap) and rows["f2"].principal.reason == fx
    claims = " ".join(c.text for c in r.claims)
    assert "every facility in EUR, and one is not" in claims
    text = repr(r)
    assert "US$" not in text and "not USD" not in text
    assert "Facility f2 is denominated in USD" in " ".join(r.own_limitations)


def test_lowercase_facility_currency_is_a_gap_not_a_figure() -> None:
    r = cp2d.compute(_two_facilities("eur", "EUR"))
    lower = "Not calculable: facility term-loan is in eur, not EUR; no FX conversion is applied"
    assert isinstance(r.bridge.maturities_in_horizon, cp2d.Gap)
    assert r.bridge.maturities_in_horizon.reason == lower
    rows = {w.facility.facility_id: w for w in r.bridge.wall}
    assert isinstance(rows["term-loan"].principal, cp2d.Gap)


def _with_2025(y26: Any, old: Any) -> Any:
    """`y26` plus `old`'s facts as a 2025 year: ids prefixed, EUR, every amount x100."""
    y25 = []
    for f in old.facts:
        update: dict[str, Any] = {"fact_id": "y25:" + f.fact_id, "row_id": "y25-" + f.row_id}
        if f.currency == "USD":
            update["currency"] = "EUR"
        if f.amount is not None:
            update["amount"] = f.amount * 100
        if f.field == "currency" and f.table_id == "T4.18":
            update["text"] = "EUR"
        y25.append(f.model_copy(update=update))
    return y26.model_copy(update={"facts": (*y25, *y26.facts)})


def test_fy2026_base_over_a_two_year_cp1_binds_the_2026_figures() -> None:
    """A CP-1 that also carries 2025 rows (all amounts x100, EUR): the 2026 basis binds 2026."""
    import test_periods_currency_e2e_cp3c as a2

    y26 = a.cp1_2026("EUR")
    both = _with_2025(y26, c2d.cp1_module(tm2._operands("positive")))
    basis = period_basis(tpb._context("fy-2026", "EUR"), both.facts)
    assert basis == EUR
    sel = cp2d.select_cp1(both, basis)
    assert sel.operands == cp2d.select_cp1(y26, basis).operands
    assert sel.balance_date.isoformat() == "2026-12-31"
    run = tc3.make_pack().run
    y26c = a2.cp1_for(run)
    bothc = _with_2025(y26c, tc3.cp1_module(run))
    s3 = cp3c.select_cp1(bothc, basis)
    assert s3.operands == cp3c.select_cp1(y26c, basis).operands
    assert s3.balance_date.isoformat() == "2026-12-31"


def _renamed_rows() -> list[dict[str, Any]]:
    out = []
    for row in a.ROWS:
        row = {k: dict(v) for k, v in row.items()}
        pid = row["period_id"]["text"]
        row["period_id"]["text"] = {"q4-2026": "Q4-FY26", "fy-2026": "FY26"}.get(pid, pid)
        out.append(row)
    return out


def test_q4_fy26_ids_bind_and_label_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = _renamed_rows()
    basis = period_basis(tpb._context("fy-2026", "EUR"), tpb._oracle_facts(rows))
    assert basis.schedule_period == "Q4-FY26"
    cp1 = a.cp1_2026(
        "EUR", basis=basis, rows=rows, periods={"q4-2025": "Q4-FY26", "fy-2025": "FY26"}
    )
    _, _, module = a._compose(tmp_path, monkeypatch, cp1)
    facts = {f.fact_id: f for f in module.facts}
    oracle = a.ORACLE["tables"]
    for table_id in ("T2E.2", "T2E.4"):
        for _, cells in oracle[table_id]["rows"]:
            for cell in cells if isinstance(cells, list) else [cells]:
                got = facts[cell["fact_id"]]
                want_period = (cell.get("period") or "").replace("q4-2026", "Q4-FY26")
                if cell.get("amount") is not None:
                    assert tm2._num_equal(got.amount, cell["amount"]), cell["fact_id"]
                    assert got.period == want_period, cell["fact_id"]


def test_blank_eur_base_is_an_issue_at_both_validators(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blank_eur = tpb._context("", "EUR")
    monkeypatch.setattr(cp2d, "context_facts", lambda pack: blank_eur)
    store, attempt = c2d.make_upstream(tmp_path / "2d", "positive")
    sub = cp2d.LiquidityBridgeSubmission.model_validate_json(c2d._literal("positive"))
    issues = cp2d.validate_liquidity_bridge(
        pack=store.pack(), submission=sub, upstream=cp2d.cp2d_upstream(store=store, attempt=attempt)
    )
    assert any(i.startswith("Period basis refused: run.current_period is blank") for i in issues)
    with pytest.raises(ValueError, match="Period basis refused"):
        cp2d.liquidity_bridge(
            pack=store.pack(),
            submission=sub,
            upstream=cp2d.cp2d_upstream(store=store, attempt=attempt),
        )
    monkeypatch.setattr(cp2d, "context_facts", lambda pack: None)
    store3, pack3, att3 = tc3.seed(tmp_path / "3c")
    sub3 = tc3.submission_of(store3, att3)
    monkeypatch.setattr(cp2d, "context_facts", lambda pack: blank_eur)
    lines = cp3c._lines(pack3, sub3, tc3.upstream_of(store3, att3))
    assert lines and lines[0].startswith("Period basis refused: run.current_period is blank"), lines


def test_cp2d_basis_eur_with_usd_statement_facts_refuses() -> None:
    cp1 = a.cp1_2026("EUR")
    flipped = cp1.model_copy(
        update={
            "facts": tuple(
                f.model_copy(update={"currency": "USD"}) if f.table_id == "T4.6" else f
                for f in cp1.facts
            )
        }
    )
    with pytest.raises(ValueError, match="is not in EUR millions"):
        cp2d.select_cp1(flipped, EUR)


def test_cp3c_one_fact_in_another_currency_refuses() -> None:
    inputs = tm3._inputs("positive")
    euro = tc3._every_millions_fact(inputs, lambda f: replace(f, currency="EUR"))
    cp1 = replace(
        euro.cp1,
        cash_closing=replace(euro.cp1.cash_closing, currency="EUR"),
        adjusted_ebitda=replace(euro.cp1.adjusted_ebitda, currency="USD"),
        facilities=tuple(replace(t, currency="EUR") for t in euro.cp1.facilities),
    )
    with pytest.raises(ValueError, match="currency"):
        cp3c.compute(replace(euro, cp1=cp1, currency="EUR", basis=EUR))
