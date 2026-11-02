"""Probe A2: CP-3C end to end under an fy-2026 EUR run (R6) over a CP-2D settled by the real
core under the same run, compared with the frozen key
`cases/periods-currency-owner/expected.json#module_oracles/CP-3C@EUR/expected` and the R6
forbidden tokens. Same CP-1 construction as test_periods_currency_e2e_cp2d.py, plus the two CP-3C
T4.10 metrics and the T4.18 ranking terms (as `test_connect_cp3c.cp1_module`). Exit 0 = equal.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest
import test_connect_cp2d as c2d
import test_connect_cp3c as tc3
import test_method_cp3c as tm3
import test_period_basis as tpb
import test_periods_currency_e2e_cp2d as a

from deploy_vii.contracts import Fact, Module, Run
from deploy_workflow.owners import cp2d, cp3c
from deploy_workflow.owners.period_basis import period_basis

ORACLE: dict[str, Any] = a.KEY["module_oracles"]["CP-3C@EUR"]["expected"]
R6 = a.KEY["runs"]["R6"]["modules"]["CP-3C"]
AS_OF = "2027-01-10"  # expected.json#runs/R6 as_of per the plan run table


def _t410(name: str, amount: Decimal, currency: str) -> Fact:
    return Fact(
        fact_id=f"cp1:{name}",
        label=f"{a.BASIS.ltm_column} · {name}",
        table_id="T4.10",
        row_id="row-" + name,
        field="value",
        amount=amount,
        unit="MILLIONS",
        currency=currency,
        scale=Decimal(1000000),
        period=a.BASIS.ltm_period,
        citations=(c2d.CITATION,),
        calculation_id=f"calc:{name}",
        value_class="calculated",
    )


def cp1_for(run: Run, currency: str = "EUR") -> Module:
    saved = c2d.PACK
    c2d.PACK = (
        c2d.PACK.model_copy(update={"run": run}) if hasattr(c2d.PACK, "model_copy") else saved
    )
    try:
        base = a.cp1_2026(currency)
    finally:
        c2d.PACK = saved
    base = base.model_copy(
        update={"run_id": run.run_id, "issuer_id": run.issuer_id, "as_of": run.as_of}
    )
    facts = [
        f.model_copy(update={"value_class": "calculated"}) if f.table_id == "T4.10" else f
        for f in base.facts
    ]
    facts += [
        _t410("adjusted_ebitda", Decimal("30.0"), currency),
        _t410("cash_interest", Decimal("-5.00"), currency),
    ]
    for key in [f for f in base.facts if f.table_id == "T4.18" and f.field == "facility_id"]:
        for field, text in tc3.TERMS.items():
            facts.append(
                Fact(
                    fact_id=f"cp1:{key.row_id}:{field}",
                    label=field,
                    table_id="T4.18",
                    row_id=key.row_id,
                    field=field,
                    text=text,
                    period=key.period,
                    citations=(c2d.CITATION,),
                    value_class="source",
                )
            )
    return base.model_copy(update={"facts": tuple(facts)})


def _compose(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, currency: str = "EUR") -> Any:
    monkeypatch.setattr(cp2d, "context_facts", lambda pack: a.CONTEXT)
    pack = tc3.make_pack(as_of=AS_OF)  # R6 runs as of 2027-01-10 (the step-up period)
    store, pack = tc3.make_store(tmp_path, "positive", cp1=cp1_for(pack.run, currency), as_of=AS_OF)
    attempt = store.begin("CP-3C")
    upstream = tc3.upstream_of(store, attempt)
    return store, pack, attempt, upstream


def _submission(upstream: Any) -> cp3c.RefinancingRiskSubmission:
    names = dict(cp3c.select(upstream, a.BASIS).refs)
    payload = tc3.bound_payload(tm3.SUBMISSIONS["cp3c"]["positive"], names)
    return cp3c.RefinancingRiskSubmission.model_validate_json(json.dumps(payload))


def test_cp3c_eur_2026_equals_the_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _store, pack, attempt, upstream = _compose(tmp_path, monkeypatch)
    submission = _submission(upstream)
    assert cp3c._lines(pack, submission, upstream) == ()
    report = cp3c.refinancing_risk(pack=pack, submission=submission, upstream=upstream)
    module = cp3c.cp3c_module(report=report, inputs=attempt.inputs, attempt=attempt.number)
    facts = {f.fact_id: f for f in module.facts}
    titles = tm3.EXPECTED["cp3c_module"]["table_titles"]
    tables = {t.table_id: t for t in module.tables}
    for table_id, table in ORACLE["tables"].items():
        got = tables[table_id]
        assert (got.title, got.row_header) == (
            table.get("title", titles[table_id]),
            table["row_header"],
        )
        assert [c.label for c in got.columns] == table["columns"], table_id
        assert [r.label for r in got.rows] == [label for label, _ in table["rows"]], table_id
    for fact_id, cell in tm3._cells(ORACLE["tables"]).items():
        fact = facts[fact_id]
        assert (tc3._STATE[fact.status], tc3._shown(fact), fact.value_class) == (
            cell["state"],
            cell["shown"],
            cell["value_class"],
        ), fact_id
        assert (fact.unit, fact.currency, fact.formula) == (
            cell.get("unit"),
            cell.get("currency"),
            cell.get("formula"),
        ), fact_id
        if fact.amount is not None:
            assert (fact.amount, fact.period) == (Decimal(cell["amount"]), cell["period"]), fact_id
        assert fact.limitation == cell.get("reason"), fact_id
    for table_id in ("T3D.7", "T3D.8", "T3D.9"):
        rows = [[r.label, *(facts[i].text for i in r.fact_ids)] for r in tables[table_id].rows]
        assert rows == ORACLE[f"{table_id}_rows"], table_id
    assert [c.text for c in module.claims] == [c["template"] for c in ORACLE["claims"]]
    assert [tc3.resolved(c.text, facts) for c in module.claims] == [
        c["text"] for c in ORACLE["claims"]
    ]
    assert list(module.limitations)[: len(ORACLE["own_limitations"])] == ORACLE["own_limitations"]
    dumped = module.model_dump_json()
    for token in R6["forbidden_tokens"]:
        assert token not in dumped, token


def test_cp3c_r4_mismatch_is_an_entry_validator_issue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    want = a.KEY["runs"]["R4"]["modules"]["CP-3C"]["issue_contains"]
    monkeypatch.setattr(cp2d, "context_facts", lambda pack: a.CONTEXT)
    pack = tc3.make_pack()
    # CP-2D under the same EUR run refuses a USD CP-1, so CP-2D is settled under a USD run here
    # and CP-3C alone sees the EUR context.
    monkeypatch.setattr(cp2d, "context_facts", lambda pack: tpb._context("fy-2026", "USD"))
    store, pack = tc3.make_store(tmp_path, "positive", cp1=cp1_for(pack.run, "USD"))
    attempt = store.begin("CP-3C")
    upstream = tc3.upstream_of(store, attempt)
    usd = period_basis(
        tpb._context("fy-2026", "USD"),
        [
            r.model_copy(update={"text": "USD"}) if r.field == "currency" else r
            for r in tpb._oracle_facts(a.ROWS)
        ],
    )
    names = dict(cp3c.select(upstream, usd).refs)
    payload = tc3.bound_payload(tm3.SUBMISSIONS["cp3c"]["positive"], names)
    submission = cp3c.RefinancingRiskSubmission.model_validate_json(json.dumps(payload))
    monkeypatch.setattr(cp2d, "context_facts", lambda pack: a.CONTEXT)
    issues = cp3c._lines(pack, submission, upstream)
    assert any(want in i for i in issues), issues


def test_cp3c_eur_2026_view_offers_the_2026_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _store, pack, _attempt, upstream = _compose(tmp_path, monkeypatch)
    block = cp3c.context_block(pack=pack, upstream=upstream)
    text = json.dumps(block, ensure_ascii=False)
    for token in R6["forbidden_tokens"]:
        assert token not in text, token
    facts = cast("list[dict[str, Any]]", block["facts"])
    periods = {f["name"]: f.get("period") for f in facts}
    assert periods["cash_closing"] == R6["bindings"]["T4.10"]
