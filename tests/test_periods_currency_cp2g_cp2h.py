"""Phase 8 Task 5: CP-2G and CP-2H take their period and currency strings from `PeriodBasis`.

The answer key is the frozen oracle `cases/periods-currency-owner/`, loaded at run time and never
edited: `expected.json#period_basis/<cur>`, `#module_oracles/CP-2G@EUR` and `#module_oracles/
CP-2H@EUR` (a shifted copy of the frozen gap and positive cases: calendar years +1, `US$`/`USD`
to `EUR`), `submissions.json#modules/...` and `t414.json` (the CP-1 T4.14 register of the shifted
pack). Nothing here copies a value out of those files.

The Stage 1 builders of `test_method_cp2g` and `test_method_cp2h` build the inputs; the basis is
the one `period_basis` reads from the oracle's own register and context.
"""

import dataclasses
import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import test_connect_cp2h as connect
import test_method_cp2g as g
import test_method_cp2h as h
import test_period_basis as pb

from deploy_vii.contracts import Fact, Input, ReportTable, Run, TableColumn, TableRow
from deploy_vii.execution import Execution
from deploy_vii.preparation import PreparedPack, SourceRequest, prepare_source
from deploy_workflow.owners import cp2g, cp2h
from deploy_workflow.owners.period_basis import (
    DEFAULT_BASIS,
    PeriodBasis,
    period_basis,
)

EXP: dict[str, Any] = pb._load("expected.json")
SUBS: dict[str, Any] = pb._load("submissions.json")
T414: dict[str, Any] = pb._load("t414.json")
G_EUR: dict[str, Any] = EXP["module_oracles"]["CP-2G@EUR"]["expected"]
H_EUR: dict[str, Any] = EXP["module_oracles"]["CP-2H@EUR"]["expected"]
CP2A_EUR: dict[str, Any] = EXP["module_oracles"]["CP-2A@EUR"]["expected"]
FIG = re.compile(r"\{\{FIG:([a-z_]+)\|([^}]*)\}\}")


def basis_of(run: str) -> PeriodBasis:
    """The basis the oracle's own register and context give (R1 USD fy-2026, R2 EUR q4-2026)."""
    settings = SUBS["contexts"][run]["run"]
    context = pb._context(settings["current_period"], settings["reporting_currency"])
    return period_basis(context, pb._oracle_facts(T414["contexts"][run]["rows"]))


EUR = basis_of("R2")


# --- CP-2G on the EUR 2026 basis ------------------------------------------------------------


def _cp2a_head() -> cp2g.Cp2aHead:
    """The CP-2A head from the oracle's CP-2A@EUR facts (the shape of `test_method_cp2g`)."""
    facts = {
        f["fact_id"]: g._fact(f) for f in CP2A_EUR["facts"] if f["table_id"] in ("T2B.1", "T2B.6")
    }

    def rows(table: str) -> list[str]:
        return list(dict.fromkeys(fid.split(".")[2] for fid in facts if fid.startswith(table)))

    def text(fid: str) -> str:
        value = facts[fid].text
        assert value is not None, fid
        return value

    scenarios = tuple(
        cp2g.Cp2aScenario(
            row=r,
            name=text(f"T2B.1.{r}.name"),
            decline=facts[f"T2B.1.{r}.ebitda_decline"],
            increase=facts[f"T2B.1.{r}.interest_increase"],
        )
        for r in rows("T2B.1.")
    )
    breaks = tuple(
        cp2g.Cp2aBreak(
            row=r,
            origin=text(f"T2B.6.{r}.origin"),
            test=text(f"T2B.6.{r}.test"),
            level=facts[f"T2B.6.{r}.level"],
            required_decline=facts[f"T2B.6.{r}.required_decline"],
            outcome=text(f"T2B.6.{r}.outcome"),
        )
        for r in rows("T2B.6.")
    )
    return cp2g.Cp2aHead(base_period=CP2A_EUR["base_period"], scenarios=scenarios, breaks=breaks)


def _g_cp1_facts() -> tuple[Fact, ...]:
    out = []
    for metric, rec in G_EUR["cp1_inputs"].items():
        fact = g._cp1_fact(metric, rec)
        out.append(fact.model_copy(update={"currency": "EUR"}) if fact.currency else fact)
    return tuple(out)


def _g_figure_ids() -> dict[str, str]:
    ids = {}
    for name, fig in SUBS["modules"]["CP-2G@EUR"]["figures"].items():
        if fig["source"] == "cp1":
            ids[name] = g._cp1_id(G_EUR["cp1_inputs"][fig["metric"]]["label"])
        else:
            ids[name] = fig["fact_id"]
    return ids


def _bind(text: str, ids: dict[str, str]) -> str:
    return FIG.sub(lambda m: "{" + ids[m[1]] + "|" + m[2] + "}", text)


def _bound(obj: Any, ids: dict[str, str]) -> Any:
    if isinstance(obj, str):
        return _bind(obj, ids)
    if isinstance(obj, list):
        return [_bound(x, ids) for x in obj]
    if isinstance(obj, dict):
        return {k: _bound(v, ids) for k, v in obj.items()}
    return obj


def _g_inputs(basis: PeriodBasis = EUR) -> cp2g.ForwardInputs:
    payload = _bound(
        SUBS["modules"]["CP-2G@EUR"]["submission"]["forward_credit_model"], _g_figure_ids()
    )
    context = cp2g.ForwardContext(
        cp1_facts=_g_cp1_facts(),
        cp2a=_cp2a_head(),
        cp1d=cp2g.Cp1dHead(status=None),
        cp1_status=g._status_word("CP-1"),
        cp2a_status=g._status_word("CP-2A"),
        names=(g.ISSUER,),
        basis=basis,
    )
    submission = cp2g.ForwardSubmission.model_validate_json(json.dumps(payload))
    return cp2g.ForwardInputs(context=context, submission=submission)


G_RESULT = cp2g.compute(_g_inputs())


def test_basis_is_the_oracles() -> None:
    """The basis these tests run on is the oracle's `period_basis/EUR` (Task 1 compares every
    field); here its three load-bearing fields."""
    key = EXP["period_basis"]["EUR"]
    assert (EUR.currency, EUR.money_unit) == (key["currency"], key["money_unit"])
    assert list(EUR.years) == key["years"]
    assert EUR.ltm_period == key["ltm_period"]


def test_cp2g_eur_facts_equal_the_oracle() -> None:
    got = [g._record(c) for c in G_RESULT.cells]
    want = G_EUR["facts"]
    assert [r["fact_id"] for r in got] == [r["fact_id"] for r in want]
    for have, expected in zip(got, want, strict=True):
        assert have == expected, expected["fact_id"]


def test_cp2g_eur_tables_claims_and_limitations_equal_the_oracle() -> None:
    tables = [
        {
            "table_id": t.table_id,
            "title": t.title,
            "rows": [
                {"row_id": r.row_id, "label": r.label, "fact_ids": list(r.fact_ids)} for r in t.rows
            ],
        }
        for t in G_RESULT.tables
    ]
    assert tables == G_EUR["tables"]
    ids = _g_figure_ids()
    assert [c.claim_id for c in G_RESULT.claims] == [c["claim_id"] for c in G_EUR["claims"]]
    for claim, want in zip(G_RESULT.claims, G_EUR["claims"], strict=True):
        assert claim.text == _bind(want["text"], ids), want["claim_id"]
        assert claim.limitation == want["limitation"], want["claim_id"]
    assert list(G_RESULT.own_limitations) == G_EUR["own_limitations"]


def test_cp2g_eur_forecast_and_breaks_equal_the_oracle() -> None:
    for name in ("base", "down"):
        got = [
            {
                "year": fy,
                **{k: g._norm(getattr(y, attr).amount) for k, attr in g._YEAR_KEYS.items()},
            }
            for fy, y in zip(EUR.year_labels, G_RESULT.forecast[name].years, strict=True)
        ]
        assert got == G_EUR["forecast"][name], name
    firsts = [
        {"row": b.row, "base_first": b.base.first, "down_first": b.down.first}
        for b in G_RESULT.break_tests
    ]
    assert firsts == [
        {"row": b["row"], "base_first": b["base_first"], "down_first": b["down_first"]}
        for b in G_EUR["break_tests"]
    ]


def test_b_driver_columns_are_the_three_years_after_the_base() -> None:
    """RED (b): the T2H.3 driver columns follow the basis; `years` is (2027, 2028, 2029)."""
    key = EXP["period_basis"]["EUR"]
    assert list(EUR.years) == key["years"]
    drivers = [
        c.fact
        for c in G_RESULT.cells
        if c.fact.table_id == "T2H.3" and c.fact.field in ("fy1", "fy2", "fy3")
    ]
    assert drivers
    for fact in drivers:
        year = int(fact.field[2:]) - 1
        assert fact.label == EUR.year_labels[year]
        assert fact.period == cp2g.fy_periods(EUR)[year]
    assert {f.label for f in drivers} == set(key["year_labels"])


def test_c_not_reached_names_the_last_forecast_year() -> None:
    """RED (c): a break not reached in the base case reads `Not reached by FY2029`."""
    reached = [b for b in G_RESULT.break_tests if b.base.first == EUR.not_reached_text]
    assert reached
    key = EXP["period_basis"]["EUR"]
    assert EUR.not_reached_text == key["not_reached_text"]
    assert cp2g.first_result([False, False, False], EUR) == key["not_reached_text"]
    assert cp2g.first_result([False, True, None], EUR) == key["year_labels"][1]


def test_default_composer_is_the_2025_default() -> None:
    """RED (a): with no basis given the module reads the default (`DEFAULT_BASIS`), spelled as
    before; the unchanged owner tests compare that with the frozen cp2g and cp2h oracles."""
    assert cp2g.LTM_PERIOD == DEFAULT_BASIS.ltm_period
    assert cp2g.FY == DEFAULT_BASIS.year_labels == ("FY2026", "FY2027", "FY2028")
    assert cp2g.YEARS == (2026, 2027, 2028)
    assert cp2h.NOT_REACHED == "Not reached by FY2028"


def _money_cells(result: cp2g.ForwardResult) -> list[Fact]:
    return [c.fact for c in result.cells if c.fact.unit == "MILLIONS" and c.fact.status == "known"]


def test_f_eur_run_has_no_us_dollar_token_in_cp2g() -> None:
    """RED (f), CP-2G: no `US$` and no `USD` in any cell, label, claim or limitation; every
    money cell states EUR."""
    money = _money_cells(G_RESULT)
    assert money
    assert {f.currency for f in money} == {"EUR"}
    texts = [
        *(json.dumps(c.fact.model_dump(mode="json")) for c in G_RESULT.cells),
        *(c.text for c in G_RESULT.claims),
        *G_RESULT.own_limitations,
    ]
    for text in texts:
        assert "US$" not in text and "USD" not in text, text
    assert any("|EUR m}" in c.text for c in G_RESULT.claims)


def test_cp2g_refuses_a_book_in_another_currency() -> None:
    """The USD-only check (`_usd_millions`) now reads the run's currency: a USD operand under a
    EUR basis fails closed."""
    facts = tuple(
        f.model_copy(update={"currency": "USD"}) if f.currency else f for f in _g_cp1_facts()
    )
    with pytest.raises(ValueError, match="must be EUR MILLIONS at scale 1000000, not USD"):
        cp2g.Operands.from_cp1(facts, EUR)
    default = tuple(
        f.model_copy(update={"currency": "EUR"}) if f.currency else f for f in g._cp1_facts("gap")
    )
    with pytest.raises(ValueError, match="must be USD MILLIONS at scale 1000000, not EUR"):
        cp2g.Operands.from_cp1(default, DEFAULT_BASIS)


def test_cp2g_selects_the_ltm_column_of_its_basis() -> None:
    assert set(cp2g.select_cp1(_g_cp1_facts(), EUR)) == set(G_EUR["cp1_inputs"])
    with pytest.raises(ValueError, match="LTM Q4 25 .* found 0"):
        cp2g.select_cp1(_g_cp1_facts())


def test_cp2g_base_period_other_than_the_basis_is_not_comparable() -> None:
    """The base-period equality now reads `basis.ltm_period` (cp2g :798): a CP-2A head stressed
    on the 2025 base under a 2026 basis is not reproducible."""
    context = dataclasses.replace(
        _g_inputs().context, cp2a=dataclasses.replace(_cp2a_head(), base_period=cp2g.LTM_PERIOD)
    )
    result = cp2g.compute(dataclasses.replace(_g_inputs(), context=context))
    stale = f"CP-2A stressed the base period {cp2g.LTM_PERIOD}"
    assert any(line.startswith(stale) for line in result.own_limitations)
    assert not any(
        line.startswith("CP-2A stressed the base period") for line in G_RESULT.own_limitations
    )


# --- CP-2H on the EUR 2026 basis -------------------------------------------------------------


def _h_cp1_facts() -> tuple[Fact, ...]:
    out = []
    for metric in cp2h.CP1_METRICS:
        r = H_EUR["cp1_inputs"][metric]
        known = r["status"] == "known"
        out.append(
            Fact(
                fact_id=f"interface-fact:{h._digest(r['label'])}",
                label=r["label"],
                table_id="T4.10",
                row_id=metric,
                field="ltm",
                status=r["status"],
                amount=Decimal(r["amount_exact"]) if known else None,
                unit={"multiple": "MULTIPLE", "percent": "PERCENT"}[r["unit_class"]],
                period=r["period"],
                value_class=r["value_class"],
                calculation_id=f"canonical-kpi:{h._digest(r['label'])}" if known else None,
                limitation=r["limitation"],
            )
        )
    return tuple(out)


def _h_cp2g_facts() -> tuple[Fact, ...]:
    """The CP-2G@EUR oracle's facts as the CP-2H head reads them."""
    return tuple(h._cp2g_fact(r) for r in G_EUR["facts"])


def _h_pack() -> cp2h.PackScope:
    agency = SUBS["modules"]["CP-2H@EUR"]["agency_source"]
    pages = [{"locator": f"page:{n}", "text": t} for n, t in enumerate(agency["pages"], 1)]
    ratings = h._source("ratings", "Credit rating summary", pages, agency["sha256"])
    return cp2h.PackScope(sources=(ratings,), names=(h.ISSUER,))


def _h_ids(cp1: tuple[Fact, ...]) -> dict[str, str]:
    by_metric = cp2h.select_cp1(cp1, EUR)
    figures = SUBS["modules"]["CP-2H@EUR"]["figures"]
    return {name: by_metric[f["metric"]].fact_id for name, f in figures.items()}


def _h_upstream(cp2g_facts: tuple[Fact, ...], basis: PeriodBasis) -> cp2h.TriggerUpstream:
    return cp2h.TriggerUpstream(
        bound=h.BOUND,
        current=h.BOUND,
        cp1_facts=_h_cp1_facts(),
        cp2g=cp2h.Cp2gMetrics.select(cp2g_facts, basis),
        basis=basis,
    )


def _h_inputs() -> cp2h.TriggerInputs:
    stream = _h_upstream(_h_cp2g_facts(), EUR)
    payload = _bound(
        SUBS["modules"]["CP-2H@EUR"]["submission"]["rating_triggers"], _h_ids(stream.cp1_facts)
    )
    return cp2h.TriggerInputs(
        pack=_h_pack(),
        upstream=stream,
        submission=cp2h.TriggerSubmission.model_validate_json(json.dumps(payload)),
    )


H_INPUTS = _h_inputs()
H_REPORT = cp2h.compute(H_INPUTS)


def test_cp2h_eur_facts_tables_claims_and_limitations_equal_the_oracle() -> None:
    assert cp2h.validate(H_INPUTS) == ()
    assert [c.fact.fact_id for c in H_REPORT.cells] == [f["fact_id"] for f in H_EUR["facts"]]
    for cell, want in zip(H_REPORT.cells, H_EUR["facts"], strict=True):
        h._assert_cell(cell, want)
    tables = [
        {
            "table_id": t.table_id,
            "title": t.title,
            "columns": [c.field for c in t.columns],
            "rows": [
                {"row_id": r.row_id, "label": r.label, "fact_ids": list(r.fact_ids)} for r in t.rows
            ],
        }
        for t in H_REPORT.tables
    ]
    assert tables == H_EUR["tables"]
    ids = _h_ids(H_INPUTS.upstream.cp1_facts)
    assert [c.claim_id for c in H_REPORT.claims] == [c["claim_id"] for c in H_EUR["claims"]]
    for claim, want in zip(H_REPORT.claims, H_EUR["claims"], strict=True):
        assert claim.text == _bind(want["text"], ids), want["claim_id"]
    assert list(H_REPORT.own_limitations) == H_EUR["own_limitations"]


def test_cp2h_eur_first_reached_text_follows_the_basis() -> None:
    """RED (c), CP-2H: `Not reached by FY2029` is the oracle's own text for run R2."""
    want = next(m for m in [EXP["runs"]["R2"]["modules"]["CP-2H"]])["first_reached_text"]
    assert want == EUR.not_reached_text
    firsts = [
        c.fact.text
        for c in H_REPORT.cells
        if c.fact.field in ("base_first", "down_first") and c.fact.status == "known"
    ]
    assert want in firsts
    assert cp2h.first_year(hits=[False, False, False], basis=EUR) == want
    assert (
        cp2h.first_year(hits=[False, True, False], basis=EUR)
        == (EXP["period_basis"]["EUR"]["year_labels"][1])
    )


def test_cp2h_forecast_columns_are_fy2027_to_fy2029() -> None:
    labels = {
        c.fact.label
        for c in H_REPORT.cells
        if c.fact.table_id == "T2R.5" and c.fact.field in ("y1", "y2", "y3")
    }
    assert labels == set(EXP["period_basis"]["EUR"]["year_labels"])
    periods = {
        c.fact.period
        for c in H_REPORT.cells
        if c.fact.table_id == "T2R.5" and c.fact.field in ("y1", "y2", "y3")
    }
    assert periods == set(cp2g.fy_periods(EUR))


def test_f_eur_run_has_no_us_dollar_token_in_cp2h() -> None:
    """RED (f), CP-2H: no `US$` and no `USD` in any cell or claim."""
    texts = [
        *(json.dumps(c.fact.model_dump(mode="json")) for c in H_REPORT.cells),
        *(c.text for c in H_REPORT.claims),
        *H_REPORT.own_limitations,
    ]
    for text in texts:
        assert "US$" not in text and "USD" not in text, text


def test_d_a_cp2g_head_on_the_2025_basis_is_stale_under_a_2026_context() -> None:
    """RED (d): the existing period equality (CP-2G metrics must state the periods of the basis
    they are read under) refuses a 2025-basis head under the 2026 basis, and the converse."""
    stale = tuple(h._cp2g_fact(r) for r in h.CP2G["cases"]["gap"]["facts"])
    with pytest.raises(ValueError, match="unexpected unit or period"):
        cp2h.Cp2gMetrics.select(stale, EUR)
    with pytest.raises(ValueError, match="unexpected unit or period"):
        cp2h.Cp2gMetrics.select(_h_cp2g_facts(), DEFAULT_BASIS)
    assert cp2h.Cp2gMetrics.select(stale, DEFAULT_BASIS).basis is DEFAULT_BASIS
    assert cp2h.Cp2gMetrics.select(_h_cp2g_facts(), EUR).basis is EUR


# --- (e) a base that is not fy or q4 is refused in both entry validators ---------------------


def _h2_pack(sources: tuple[Any, ...] = ()) -> PreparedPack:
    """A pack whose context (the oracle's R5) has the h2 base."""
    context = SUBS["contexts"]["R5"]
    raw = json.dumps(context).encode()
    source = prepare_source(
        SourceRequest(source_id="context", path="context.json", media_type="text/plain"), raw
    )
    return PreparedPack(run=_run_of(context, ("CP-2H",)), sources=(*sources, source))


def _run_of(context: dict[str, Any], modules: tuple[str, ...]) -> Run:
    """The pack's run, agreeing with the oracle context (`context_facts` compares them)."""
    return Run(
        run_id="p8-t5",
        issuer_id=context["identity"]["issuer_id"],
        issuer_name=context["identity"]["issuer_name"],
        as_of=date.fromisoformat(context["run"]["as_of"]),
        case_kind=context["run"]["case_kind"],
        pathway=context["run"]["pathway"],
        requested_modules=modules,
    )


def _refusal_text() -> str:
    """The R5 refusal message, from the key (`expected.json#runs/R5/refusal/message`)."""
    message = EXP["runs"]["R5"]["refusal"]["message"]
    assert isinstance(message, str)
    return message


def _register() -> tuple[Fact, ...]:
    """The CP-1 T4.14 register of the R2 pack (2026 columns), as CP-1 states it."""
    return tuple(pb._oracle_facts(T414["contexts"]["R2"]["rows"]))


def test_e_h2_base_is_refused_in_the_cp2g_entry_validator() -> None:
    refusal = _refusal_text()
    inputs = _g_inputs()
    bound = (
        Input(input_id="CP-1", sha256="1" * 64, status="accepted"),
        Input(input_id="CP-2A", sha256="2" * 64, status="accepted"),
    )
    upstream = cp2g.Upstream(
        bound=bound,
        current=bound,
        cp1=(*inputs.context.cp1_facts, *_register()),
        cp2a=inputs.context.cp2a,
        cp1d=inputs.context.cp1d,
    )
    issues = cp2g.validate_forward(pack=_h2_pack(), submission=inputs.submission, upstream=upstream)
    assert issues == (refusal,)
    view = cp2g.context_block(pack=_h2_pack(), upstream=upstream)
    assert view["context_issue"] == refusal


def test_e_h2_base_is_refused_in_the_cp2h_entry_validator(tmp_path: Path) -> None:
    refusal = _refusal_text()
    store, pack, attempt = _seed_cp2h(
        tmp_path, _h2_pack(), (*_h_cp1_facts(), *_register()), _h_cp2g_facts()
    )
    upstream = cp2h.cp2h_upstream(store=store, attempt=attempt)
    assert upstream.basis_refusal == refusal
    assert upstream.basis is DEFAULT_BASIS
    head = store.head_module(connect._head(store, "CP-1"))
    payload = _bound(
        SUBS["modules"]["CP-2H@EUR"]["submission"]["rating_triggers"], _h_ids(head.facts)
    )
    submission = cp2h.TriggerSubmission.model_validate_json(json.dumps(payload))
    assert cp2h.validate_triggers(pack=pack, submission=submission, upstream=upstream) == (refusal,)
    view = cp2h.context_block(pack=pack, upstream=upstream)
    assert view["context_issue"] == refusal


def _seed_cp2h(
    root: Path,
    pack: PreparedPack,
    cp1: tuple[Fact, ...],
    cp2g_facts: tuple[Fact, ...] | None = None,
) -> tuple[Execution, PreparedPack, Any]:
    """A real store over `pack` with CP-0, CP-1, CP-2A and CP-2G settled and CP-2H begun: CP-1
    carries the given facts, CP-2G the given facts (default: the 2025 gap head)."""
    store = Execution.create(root / "store", pack)
    commands = tuple(connect._command(m) for m in ("CP-1", "CP-2A", "CP-2G", "CP-2H"))
    connect._finish(store, "CP-0", commands, None)
    connect._finish(store, "CP-1", cp1, None)
    connect._finish(store, "CP-2A", (), None)
    if cp2g_facts is None:
        connect._finish(
            store, "CP-2G", connect._cp2g_facts("gap"), None, (connect._cp2g_t2h7("gap"),)
        )
    else:
        connect._finish(store, "CP-2G", cp2g_facts, None, (_t2h7_of(G_EUR),))
    return store, store.pack(), store.begin("CP-2H")


def _t2h7_of(expected: dict[str, Any]) -> Any:
    """The oracle's T2H.7 layout, as `connect._cp2g_t2h7` reads it from the 2025 oracle."""
    t = next(t for t in expected["tables"] if t["table_id"] == "T2H.7")
    fields = [fid.rsplit(".", 1)[1] for fid in t["rows"][0]["fact_ids"]]
    return ReportTable(
        table_id="T2H.7",
        title=t["title"],
        columns=tuple(TableColumn(field=f, label=f) for f in fields),
        rows=tuple(
            TableRow(row_id=r["row_id"], label=r["label"], fact_ids=tuple(r["fact_ids"]))
            for r in t["rows"]
        ),
    )


def _eur_pack() -> PreparedPack:
    """The R2 run: its context (EUR, q4-2026) and the shifted agency source, in a prepared pack."""
    context = SUBS["contexts"]["R2"]
    source = prepare_source(
        SourceRequest(source_id="context", path="context.json", media_type="text/plain"),
        json.dumps(context).encode(),
    )
    ratings = _h_pack().sources[0]
    run = _run_of(context, ("CP-2H",))
    return PreparedPack(run=run, sources=(ratings, source))


def test_g_store_reads_the_basis_from_the_context_and_the_register(tmp_path: Path) -> None:
    """`cp2h_upstream` over a real store: the context (EUR, q4-2026) and the CP-1 T4.14 register
    give the oracle's basis, the CP-2G head states its periods, and the oracle's submission
    validates and composes the oracle's facts."""
    cp1 = (*_h_cp1_facts(), *_register())
    store, pack, attempt = _seed_cp2h(tmp_path, _eur_pack(), cp1, _h_cp2g_facts())
    upstream = cp2h.cp2h_upstream(store=store, attempt=attempt)
    assert upstream.basis_refusal is None
    assert upstream.basis == EUR
    head = store.head_module(connect._head(store, "CP-1"))
    ids = _h_ids(head.facts)
    payload = _bound(SUBS["modules"]["CP-2H@EUR"]["submission"]["rating_triggers"], ids)
    submission = cp2h.TriggerSubmission.model_validate_json(json.dumps(payload))
    assert cp2h.validate_triggers(pack=pack, submission=submission, upstream=upstream) == ()
    report = cp2h.rating_triggers(pack=pack, submission=submission, upstream=upstream)
    own = [f.fact_id for f in report.facts if f.table_id.startswith("T2R.")]
    assert own == [f["fact_id"] for f in H_EUR["facts"]]
    block = cp2h.context_block(pack=pack, upstream=upstream)
    assert '"row": "a25"' in json.dumps(block["cp2g"])


def test_g_store_refuses_a_2025_cp2g_head_under_the_2026_context(tmp_path: Path) -> None:
    """RED (d) through the store: the 2025 gap head under the 2026 context raises the period
    equality of `Cp2gMetrics`."""
    cp1 = (*_h_cp1_facts(), *_register())
    store, _pack, attempt = _seed_cp2h(tmp_path, _eur_pack(), cp1)
    with pytest.raises(ValueError, match="unexpected unit or period"):
        cp2h.cp2h_upstream(store=store, attempt=attempt)
