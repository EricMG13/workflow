"""Probe A: CP-2D end to end under an fy-2026 EUR run (R6), compared with the frozen key
`cases/periods-currency-owner/expected.json#module_oracles/CP-2D@EUR/expected` and the R6
forbidden tokens (`#runs/R6/modules/CP-2D/forbidden_tokens`).

The CP-1 is the frozen Stage 1 positive case re-written as CP-1 would write it for the shifted
pack: bindings from the 2026 basis, every money fact EUR, the pinned T4.14 rows of
`t414.json#contexts/R2`, T4.18 rows at q4-2026/fy-2026 with maturities shifted one year. The
context is supplied by patching `cp2d.context_facts` (the context->basis link is Task 1's,
tested there). Exit 0 = the composed module equals the key.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import test_connect_cp2d as c2d
import test_method_cp2d as tm
import test_period_basis as tpb

from deploy_vii.contracts import Module
from deploy_workflow.owners import cp2d
from deploy_workflow.owners.period_basis import period_basis

CASE = Path(c2d.__file__).resolve().parents[1] / "cases" / "periods-currency-owner"
KEY = json.loads((CASE / "expected.json").read_text(encoding="utf-8"))
ORACLE: dict[str, Any] = KEY["module_oracles"]["CP-2D@EUR"]["expected"]
R6 = KEY["runs"]["R6"]["modules"]["CP-2D"]
ROWS = json.loads((CASE / "t414.json").read_text(encoding="utf-8"))["contexts"]["R2"]["rows"]
CURRENCY = "EUR"
CONTEXT = tpb._context("fy-2026", CURRENCY)
BASIS = period_basis(CONTEXT, tpb._oracle_facts(ROWS))
PERIODS = {"q4-2025": "q4-2026", "fy-2025": "fy-2026"}


def _shift(day: date | None) -> date | None:
    return None if day is None else day.replace(year=day.year + 1)


def cp1_2026(
    currency: str = "EUR",
    facility_currency: str | None = None,
    basis: Any = None,
    rows: Any = None,
    periods: Any = None,
) -> Module:
    basis = basis or BASIS
    rows_in = rows or ROWS
    periods = periods or PERIODS
    ops = tm._operands("positive")
    facilities = tuple(
        replace(f, currency=facility_currency or currency, maturity_date=_shift(f.maturity_date))
        for f in ops.facilities or ()
    )
    ops = replace(ops, facilities=facilities)
    saved = cp2d.FACT_BINDINGS
    cp2d.FACT_BINDINGS = cp2d.fact_bindings(basis)  # c2d._cp1_fact reads the module attribute
    try:
        module = c2d.cp1_module(ops)
    finally:
        cp2d.FACT_BINDINGS = saved
    facts = []
    for f in module.facts:
        if f.table_id == "T4.14":
            continue
        update: dict[str, Any] = {}
        if f.currency == "USD" and f.table_id != "T4.18":
            update["currency"] = currency
        if f.table_id == "T4.18":
            update["period"] = periods[str(f.period)]
            update["row_id"] = f.row_id.replace("2025", "2026") + "-" + periods[str(f.period)]
        facts.append(f.model_copy(update=update))
    rows = tpb._oracle_facts(rows_in)
    if currency != "EUR":
        rows = [
            r.model_copy(update={"text": currency}) if r.field == "currency" else r for r in rows
        ]
    facts += rows
    return module.model_copy(update={"facts": tuple(facts)})


def _compose(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cp1: Module) -> Any:
    monkeypatch.setattr(cp2d, "context_facts", lambda pack: CONTEXT)
    store = c2d.make_store(tmp_path, cp1)
    attempt = store.begin("CP-2D")
    submission = cp2d.LiquidityBridgeSubmission.model_validate_json(c2d._literal("positive"))
    upstream = cp2d.cp2d_upstream(store=store, attempt=attempt)
    issues = cp2d.validate_liquidity_bridge(
        pack=store.pack(), submission=submission, upstream=upstream
    )
    assert issues == (), issues
    report = cp2d.liquidity_bridge(pack=store.pack(), submission=submission, upstream=upstream)
    module = cp2d.cp2d_module(report=report, inputs=attempt.inputs, attempt=attempt.number)
    return store, attempt, module


def test_cp2d_eur_2026_equals_the_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _store, _attempt, module = _compose(tmp_path, monkeypatch, cp1_2026())
    facts = {f.fact_id: f for f in module.facts}
    for table_id, table in ORACLE["tables"].items():
        got = next(t for t in module.tables if t.table_id == table_id)
        assert got.title == table["title"] and got.row_header == table["row_header"], table_id
        assert [c.label for c in got.columns] == table["columns"], table_id
        assert [r.label for r in got.rows] == [r[0] for r in table["rows"]], table_id
        for row, (_, cells) in zip(got.rows, table["rows"], strict=True):
            for fact_id, cell in zip(
                row.fact_ids, cells if isinstance(cells, list) else [cells], strict=True
            ):
                assert fact_id == cell["fact_id"]
                c2d._assert_fact(facts[fact_id], cell, "positive")
                if cell.get("period") is not None:
                    assert facts[fact_id].period == cell["period"], fact_id
    assert list(module.limitations) == ORACLE["own_limitations"]
    assert [c.text for c in module.claims] == [c["template"] for c in ORACLE["claims"]]
    for table_id, key in (("T2E.6", "T2E.6_rows"), ("T2E.7", "T2E.7_rows")):
        rows = next(t for t in module.tables if t.table_id == table_id).rows
        assert [(r.label, facts[r.fact_ids[0]].text) for r in rows] == [
            tuple(w) for w in ORACLE[key]
        ]
    money = [f for f in module.facts if f.unit == "MILLIONS"]
    assert money and {f.currency for f in money} == {CURRENCY}
    dumped = module.model_dump_json()
    for token in R6["forbidden_tokens"]:
        assert token not in dumped, token
    for token in R6["required_tokens"]:
        assert token in dumped, token


def test_cp2d_eur_2026_view_names_the_run_unit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, attempt, _ = _compose(tmp_path, monkeypatch, cp1_2026())
    body = json.loads(cp2d.view(store, attempt)[1])
    assert (
        body["bounds"]["minimum_cash"] == "decimal >= 0 in EUR m, or null with minimum_cash_absence"
    )
    for token in R6["forbidden_tokens"]:
        assert token not in json.dumps(body, ensure_ascii=False), token
    periods = {e["name"]: e["period"] for e in body["cp1_facts"]}
    bindings = KEY["runs"]["R6"]["modules"]["CP-2D"]["bindings"]
    assert periods["cash_bs"] == bindings["T4.6"]
    assert periods["cfo"] == bindings["T4.5"]
    assert periods["cash_closing"] == bindings["T4.10"]


def test_cp2d_r4_mismatch_is_an_entry_validator_issue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R4: a USD CP-1 under a EUR run: refused at the entry validator with the key's text."""
    want = KEY["runs"]["R4"]["modules"]["CP-2D"]["issue_contains"]
    monkeypatch.setattr(cp2d, "context_facts", lambda pack: CONTEXT)
    store = c2d.make_store(tmp_path, cp1_2026("USD"))
    attempt = store.begin("CP-2D")
    submission = cp2d.LiquidityBridgeSubmission.model_validate_json(c2d._literal("positive"))
    upstream = cp2d.cp2d_upstream(store=store, attempt=attempt)
    issues = cp2d.validate_liquidity_bridge(
        pack=store.pack(), submission=submission, upstream=upstream
    )
    assert any(want in i for i in issues), issues
