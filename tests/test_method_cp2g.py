"""CP-2G Stage 1: the pure forward credit model equals the frozen oracle (cases/cp2g-owner).

Inputs are built from the oracle's own literals: the CP-1 T4.10 facts of `cp1_inputs`, the
pinned CP-2A and CP-1D oracle facts named by each case's `cp2a_head` / `cp1d_head` (the D3 pins,
read from cases/cp2a-owner and cases/cp1d-owner, never from their cores), the literal analyst
submissions, and the frozen financial pack (issuer name, the cited balance-sheet lines). Every
expected value is read from expected.json.

Run-time bindings stand in for what Stage 2 binds from a real CP-1 head: each CP-1 fact gets the
id `interface-fact:<sha256 of its label>`, a calculated one a calculation id and a source one a
citation of its frozen financial page line, and `{{FIG:name|token}}` becomes `{<fact_id>|token}`
(manifest.json run_time_bindings).
"""

import copy
import dataclasses
import hashlib
import json
import re
from decimal import Decimal
from fractions import Fraction
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from deploy_vii import prose
from deploy_vii.contracts import Citation, Fact, Input, InputStatus
from deploy_vii.report_view import fact_spelling, figure_unit
from deploy_workflow.owners import cp2g

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "cp2g-owner"
EXPECTED: dict[str, Any] = json.loads((CASE / "expected.json").read_text(encoding="utf-8"))
SUBMISSIONS: dict[str, Any] = json.loads((CASE / "submissions.json").read_text(encoding="utf-8"))
PINS = {  # the builder's D3 pins (lease Prerequisites 3)
    "cases/cp2a-owner/expected.json": "457508a0643af8ca6e31bfec6103ae2a0ca9f009dfcc3bf57d29b001e88668b5",
    "cases/cp1d-owner/expected.json": "6015b443603b16f9af8c5417e6fa69f7468fa243f37b64575f745aac6549bd8c",
    "cases/financial/manifest.json": "6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432",
}


def _pinned(rel: str) -> Any:
    data = (ROOT / rel).read_bytes()
    assert hashlib.sha256(data).hexdigest() == PINS[rel], rel
    return json.loads(data)


CP2A_EXP: dict[str, Any] = _pinned("cases/cp2a-owner/expected.json")
CP1D_EXP: dict[str, Any] = _pinned("cases/cp1d-owner/expected.json")
FIN: dict[str, Any] = _pinned("cases/financial/manifest.json")
FINANCIAL = next(s for s in FIN["sources"] if s["source_id"] == "financial")
ISSUER = FIN["run"]["issuer_name"]

RUNS = ("positive", "gap", "cp1d_blocked")
FIXTURES = (
    "fixture_total_loss",
    "fixture_cash_missing",
    "fixture_debt_repaid",
    "fixture_cp2a_gap_head",
)
CASES = RUNS + FIXTURES
D = Decimal


def _norm(x: Decimal | None) -> str | None:
    if x is None:
        return None
    text = format(x, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def _status_word(module_id: str) -> InputStatus:
    """The bound status of an upstream (expected.json execution.statuses: 'restricted (...)')."""
    word = str(EXPECTED["execution"]["statuses"][module_id]).split()[0]
    statuses: tuple[InputStatus, ...] = ("accepted", "restricted", "blocked")
    return next(s for s in statuses if s == word)


# --- inputs from the oracle's own literals ------------------------------------------------------
_UNIT = {"amount": "MILLIONS", "percent": "PERCENT", "multiple": "MULTIPLE"}
_PAGE_LINE = {"total_debt": ("page:4", "Total debt  "), "cash_closing": ("page:4", "Cash and cash")}


def _cp1_id(label: str) -> str:
    return "interface-fact:" + hashlib.sha256(label.encode()).hexdigest()


def _page_line(locator: str, prefix: str) -> str:
    page: str = next(p["text"] for p in FINANCIAL["pages"] if p["locator"] == locator)
    return next(line for line in page.split("\n") if line.startswith(prefix))


def _cp1_fact(metric: str, rec: dict[str, Any]) -> Fact:
    known = rec["status"] == "known"
    amount_unit = rec["unit_class"] == "amount"
    cites: tuple[Citation, ...] = ()
    if known and rec["value_class"] == "source":
        locator, prefix = _PAGE_LINE[metric]
        cites = (
            Citation(
                source_id="financial",
                source_sha256=FINANCIAL["sha256"],
                locator=locator,
                quote=_page_line(locator, prefix),
            ),
        )
    return Fact(
        fact_id=_cp1_id(rec["label"]),
        label=rec["label"],
        table_id="T4.10",
        row_id=metric,
        field="ltm",
        amount=D(rec["amount_exact"]) if known else None,
        status=rec["status"],
        unit=_UNIT[rec["unit_class"]],
        currency="USD" if amount_unit else None,
        scale=D(1000000) if amount_unit else D(1),
        period=rec["period"],
        citations=cites,
        calculation_id=f"calc:cp1-{metric}"
        if known and rec["value_class"] == "calculated"
        else None,
        value_class=rec["value_class"],
        limitation=rec["limitation"],
    )


def _fact(rec: dict[str, Any]) -> Fact:
    """A settled upstream fact record (CP-2A, CP-1D oracle) as the product Fact it stands for."""
    amount = rec.get("amount_exact")
    return Fact(
        fact_id=rec["fact_id"],
        label=rec["label"],
        table_id=rec["table_id"],
        row_id=rec["row_id"],
        field=rec["field"],
        amount=None if amount is None else D(amount),
        text=rec.get("text"),
        status=rec["status"],
        unit=rec.get("unit"),
        currency=rec.get("currency"),
        scale=D(rec.get("scale", "1")),
        decimals=rec.get("decimals"),
        period=rec.get("period"),
        calculation_id=rec.get("calculation_id"),
        value_class=rec.get("value_class"),
        formula=rec.get("formula"),
        limitation=rec.get("limitation"),
    )


def _source_case(pointer: str, prefix: str) -> str:
    assert pointer.startswith(prefix), pointer
    return pointer[len(prefix) :]


@cache
def _cp2a_head(source_case: str) -> cp2g.Cp2aHead:
    c = CP2A_EXP["cases"][source_case]
    facts = {f["fact_id"]: _fact(f) for f in c["facts"] if f["table_id"] in ("T2B.1", "T2B.6")}

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
    return cp2g.Cp2aHead(base_period=c["base_period"], scenarios=scenarios, breaks=breaks)


CP1D_IDS = (
    "T1D.3.supported.value",
    "T1D.6.supported.total_leverage",
    "T1D.6.supported.net_leverage",
)


def _cp1d_head(case: str) -> cp2g.Cp1dHead:
    head = EXPECTED["cases"][case]["cp1d_head"]
    if head["state"] == "unbound":
        return cp2g.Cp1dHead(status=None)
    if head["state"] == "blocked":
        return cp2g.Cp1dHead(status="blocked")
    source = _source_case(head["source"], "cases/cp1d-owner/expected.json cases.")
    facts = {f["fact_id"]: _fact(f) for f in CP1D_EXP["cases"][source]["facts"]}
    assert head["facts"] == list(CP1D_IDS)
    return cp2g.Cp1dHead(
        status=_status_word("CP-1D"),
        supported=facts[CP1D_IDS[0]],
        total_leverage=facts[CP1D_IDS[1]],
        net_leverage=facts[CP1D_IDS[2]],
    )


def _cp1_facts(case: str) -> tuple[Fact, ...]:
    return tuple(_cp1_fact(m, rec) for m, rec in EXPECTED["cases"][case]["cp1_inputs"].items())


def _context(case: str) -> cp2g.ForwardContext:
    pointer = EXPECTED["cases"][case]["cp2a_head"]["source"]
    return cp2g.ForwardContext(
        cp1_facts=_cp1_facts(case),
        cp2a=_cp2a_head(_source_case(pointer, "cases/cp2a-owner/expected.json cases.")),
        cp1d=_cp1d_head(case),
        cp1_status=_status_word("CP-1"),
        cp2a_status=_status_word("CP-2A"),
        names=(ISSUER,),
    )


def _fig_id(name: str) -> str:
    fig = SUBMISSIONS["figures"][name]
    if fig["source"] == "cp1":
        label = EXPECTED["cases"]["positive"]["cp1_inputs"][fig["metric"]]["label"]
        return _cp1_id(label)
    return str(fig["fact_id"])


def _bind(text: str) -> str:
    return re.sub(
        r"\{\{FIG:([a-z_]+)\|([^}]*)\}\}", lambda m: "{" + _fig_id(m[1]) + "|" + m[2] + "}", text
    )


def _bind_all(obj: Any) -> Any:
    if isinstance(obj, str):
        return _bind(obj)
    if isinstance(obj, list):
        return [_bind_all(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _bind_all(v) for k, v in obj.items()}
    return obj


def _payload(case: str) -> dict[str, Any]:
    group = SUBMISSIONS["fixtures"] if case.startswith("fixture") else SUBMISSIONS["cases"]
    return copy.deepcopy(group[case]["forward_credit_model"])


def _inputs(case: str) -> cp2g.ForwardInputs:
    sub = cp2g.ForwardSubmission.model_validate_json(json.dumps(_bind_all(_payload(case))))
    return cp2g.ForwardInputs(context=_context(case), submission=sub)


@cache
def _result(case: str) -> cp2g.ForwardResult:
    return cp2g.compute(_inputs(case))


# --- projections of the module output onto the oracle's record shapes ----------------------------
def _record(cell: cp2g.Cell) -> dict[str, Any]:
    f = cell.fact
    rec: dict[str, Any] = {
        "fact_id": f.fact_id,
        "table_id": f.table_id,
        "row_id": f.row_id,
        "field": f.field,
        "label": f.label,
        "status": f.status,
    }
    if f.unit is None:
        rec.update(text=f.text, shown=cell.shown)
        if f.status == "known":
            rec["value_class"] = f.value_class
            if cell.derives_from:
                rec["derives_from"] = list(cell.derives_from)
        else:
            rec["limitation"] = f.limitation
        return rec
    rec.update(unit=f.unit, period=f.period, amount_exact=_norm(f.amount), shown=cell.shown)
    if f.status != "known":
        rec["limitation"] = f.limitation
        return rec
    if f.unit == "MILLIONS":
        rec.update(currency=f.currency, scale=_norm(f.scale))
    rec.update(
        decimals=f.decimals,
        value_class=f.value_class,
        formula=f.formula,
        calculation_id=f.calculation_id,
        derives_from=list(cell.derives_from),
    )
    return rec


def _facts_by_id(result: cp2g.ForwardResult) -> dict[str, Fact]:
    out = {c.fact.fact_id: c.fact for c in result.cells}
    for table in result.references:
        out.update({r.fact.fact_id: r.fact for r in table.rows})
    return out


def _render(text: str, facts: dict[str, Fact]) -> str:
    """A claim as the reader sees it: each figure spelled by the product, chips left as chips."""
    gaps = {fid for fid, f in facts.items() if f.status != "known"}
    out: list[str] = []
    for run in prose.tokenize(text, gaps=gaps):
        if run.kind == "text":
            out.append(run.text)
        elif not run.figure:
            out.append(f"[{run.text}]")
        else:
            fact = facts[run.text]
            unit_class, _state, shown = fact_spelling(fact, None)
            unit = figure_unit(fact) if unit_class == "amount" else None
            out.append(f"{shown} {unit}" if unit else shown)
    return "".join(out)


# --- oracle cases: cell for cell ----------------------------------------------------------------
@pytest.mark.parametrize("case", CASES)
def test_case_frame(case: str) -> None:
    exp, ctx = EXPECTED["cases"][case], _context(case)
    assert exp["base_period"] == cp2g.LTM_PERIOD
    assert exp["forecast_years"] == list(cp2g.FY)
    assert exp["cp2a_head"]["base_period"] == ctx.cp2a.base_period
    assert exp["cp2a_head"]["break_rows"] == [b.row for b in ctx.cp2a.breaks]
    scenario = next(s for s in ctx.cp2a.scenarios if s.row == exp["cp2a_head"]["downside_scenario"])
    assert scenario.name == exp["cp2a_head"]["downside_name"]
    assert _inputs(case).submission.downside.scenario == scenario.row
    assert ctx.cp1d.state == exp["cp1d_head"]["state"]


@pytest.mark.parametrize("case", CASES)
def test_base_operands(case: str) -> None:
    exp = EXPECTED["cases"][case]
    ops = cp2g.Operands.from_cp1(_context(case).cp1_facts)
    assert {k: _norm(v.amount) for k, v in ops.items()} == exp["base_operands"]
    assert {k: v.reason for k, v in ops.items() if v.reason} == exp["base_missing"]
    assert _result(case).operands == ops


_YEAR_KEYS = {
    "R": "revenue",
    "E": "ebitda",
    "I": "interest",
    "X": "tax_wc",
    "K": "capex",
    "CFO": "cfo",
    "FCF": "fcf",
    "Dopen": "opening_debt",
    "Dclose": "closing_debt",
    "Copen": "opening_cash",
    "Cclose": "closing_cash",
    "Liq": "liquidity",
    "TL": "total_leverage",
    "NL": "net_leverage",
    "IC": "coverage",
    "FD": "fcf_to_debt",
}


@pytest.mark.parametrize("case", CASES)
def test_forecast_path(case: str) -> None:
    exp, result = EXPECTED["cases"][case]["forecast"], _result(case)
    for name in ("base", "down"):
        got = [
            {"year": fy, **{k: _norm(getattr(y, attr).amount) for k, attr in _YEAR_KEYS.items()}}
            for fy, y in zip(cp2g.FY, result.forecast[name].years, strict=True)
        ]
        assert got == exp[name], name


@pytest.mark.parametrize("case", CASES)
def test_facts(case: str) -> None:
    exp = EXPECTED["cases"][case]["facts"]
    got = [_record(c) for c in _result(case).cells]
    assert [r["fact_id"] for r in got] == [r["fact_id"] for r in exp]
    for g, e in zip(got, exp, strict=True):
        assert g == e, e["fact_id"]


@pytest.mark.parametrize("case", CASES)
def test_tables(case: str) -> None:
    got = [
        {
            "table_id": t.table_id,
            "title": t.title,
            "rows": [
                {"row_id": r.row_id, "label": r.label, "fact_ids": list(r.fact_ids)} for r in t.rows
            ],
        }
        for t in _result(case).tables
    ]
    assert got == EXPECTED["cases"][case]["tables"]
    assert [t["table_id"] for t in got] == EXPECTED["d8_table_ids"]["cp2g_table_ids"]


def _named_figures(case: str) -> dict[str, str]:
    """fact id -> FIG name, for the names this case's prose uses."""
    names = re.findall(r"\{\{FIG:([a-z_]+)\|", json.dumps(_payload(case)))
    return {_fig_id(n): n for n in names}


def _ref_rows_cp1(table: cp2g.RefTable, case: str) -> list[dict[str, Any]]:
    figs = _named_figures(case)
    rows = []
    for r in table.rows:
        f = r.fact
        uc, _state, cell_text = (
            fact_spelling(f, None) if f.status == "known" else (None, None, None)
        )
        unit = figure_unit(f) if f.status == "known" else None
        shown = (
            None if cell_text is None else (f"{cell_text} {unit}" if uc == "amount" else cell_text)
        )
        display_unit = {"MILLIONS": "US$ m", "PERCENT": "%", "MULTIPLE": "x"}[str(f.unit)]
        rows.append(
            {
                "row_id": r.row_id,
                "figure": figs.get(f.fact_id),
                "label": r.label,
                "cp1_label": f.label,
                "period": f.period,
                "status": f.status,
                "unit": display_unit,
                "shown": shown,
                "cell_text": cell_text,
                "value_class": f.value_class,
                "amount_exact": _norm(f.amount),
                "limitation": f.limitation,
            }
        )
    return rows


def _ref_rows_upstream(table: cp2g.RefTable, case: str) -> list[dict[str, Any]]:
    figs = _named_figures(case)
    return [
        {
            "row_id": r.row_id,
            "figure": figs.get(r.fact.fact_id),
            "fact_id": r.fact.fact_id,
            "label": r.label,
            "period": r.fact.period,
            "status": r.fact.status,
            "unit": r.fact.unit,
            "shown": fact_spelling(r.fact, None)[2] if r.fact.status == "known" else None,
            "value_class": r.fact.value_class,
            "amount_exact": _norm(r.fact.amount),
            "limitation": r.fact.limitation,
        }
        for r in table.rows
    ]


@pytest.mark.parametrize("case", CASES)
def test_references(case: str) -> None:
    exp = EXPECTED["cases"][case]
    cp1_refs, cp2a_refs, cp1d_refs = _result(case).references
    for table, key in (
        (cp1_refs, "cp1_references"),
        (cp2a_refs, "cp2a_references"),
        (cp1d_refs, "cp1d_references"),
    ):
        want = exp[key]
        assert (table.table_id, table.title, table.row_header) == (
            want["table_id"],
            want["title"],
            want["row_header"],
        )
        assert table.note == want.get("note"), key
    want_cp1 = [
        {k: v for k, v in r.items() if k != "fact_id"} for r in exp["cp1_references"]["rows"]
    ]
    assert _ref_rows_cp1(cp1_refs, case) == want_cp1
    for r in cp1_refs.rows:  # carried verbatim: the bound CP-1 fact itself
        assert r.fact in _context(case).cp1_facts
    assert _ref_rows_upstream(cp2a_refs, case) == exp["cp2a_references"]["rows"]
    assert _ref_rows_upstream(cp1d_refs, case) == exp["cp1d_references"]["rows"]


@pytest.mark.parametrize("case", CASES)
def test_claims(case: str) -> None:
    exp = EXPECTED["cases"][case]["claims"]
    result = _result(case)
    facts = _facts_by_id(result)
    assert [c.claim_id for c in result.claims] == [c["claim_id"] for c in exp]
    for got, want in zip(result.claims, exp, strict=True):
        assert got.text == _bind(want["text"]), want["claim_id"]
        assert got.limitation == want["limitation"], want["claim_id"]
        assert want["citations"] == []
        assert list(got.references) == [_fig_id(n) for n in want["cp1_references"]], want[
            "claim_id"
        ]
        assert _render(got.text, facts) == want["text_rendered"], want["claim_id"]


@pytest.mark.parametrize("case", CASES)
def test_own_limitations(case: str) -> None:
    assert list(_result(case).own_limitations) == EXPECTED["cases"][case]["own_limitations"]


@pytest.mark.parametrize("case", CASES)
def test_break_tests(case: str) -> None:
    got = [
        {
            "row": b.row,
            "kind": b.kind,
            "test": b.test,
            "base_first": b.base.first,
            "down_first": b.down.first,
            "base_values": [_norm(v) for v in b.base.values],
            "down_values": [_norm(v) for v in b.down.values],
            "base_hits": list(b.base.hits),
            "down_hits": list(b.down.hits),
        }
        for b in _result(case).break_tests
    ]
    assert got == EXPECTED["cases"][case]["break_tests"]


@pytest.mark.parametrize("case", CASES)
def test_trajectory(case: str) -> None:
    got = {
        name: {"change": _norm(t.change), "peak": _norm(t.peak), "peak_year": t.peak_year}
        for name, t in _result(case).trajectory.items()
    }
    assert got == EXPECTED["cases"][case]["trajectory"]


@pytest.mark.parametrize("case", CASES)
def test_cell_spelling_matches_fp05(case: str) -> None:
    """Every T2H.4-T2H.8 cell spelled by report_view.fact_spelling (G# bound at render time)."""
    blocks = EXPECTED["cases"][case]["FP05"]["blocks"]
    result = _result(case)
    by_id = {c.fact.fact_id: c.fact for c in result.cells}
    tables = {t.table_id: t for t in result.tables}
    states = {"known": "known", "gap": "gap", "not_meaningful": "not_meaningful"}
    for block in blocks.values():
        for tab in block["tabs"]:
            table = tables[tab["table_id"]]
            assert [r["row_id"] for r in tab["rows"]] == [r.row_id for r in table.rows]
            for row, trow in zip(tab["rows"], table.rows, strict=True):
                assert [c["fact_id"] for c in row["cells"]] == list(trow.fact_ids)
                for cell in row["cells"]:
                    fact = by_id[cell["fact_id"]]
                    _uc, state, text = fact_spelling(fact, "G1")
                    assert (states[state], text.replace("G1", "G#")) == (
                        cell["state"],
                        cell["shown"],
                    )
                    assert fact.field == cell["field"]


@pytest.mark.parametrize("case", CASES)
def test_known_fact_never_derives_from_unknown(case: str) -> None:
    cells = {c.fact.fact_id: c for c in _result(case).cells}
    for cell in cells.values():
        if cell.fact.status != "known":
            continue
        for dep in cell.derives_from:
            if not dep.startswith(("cp1:", "cp2a:", "cp1d:")):
                assert cells[dep].fact.status == "known", (cell.fact.fact_id, dep)


@pytest.mark.parametrize("case", CASES)
def test_cells_are_valid_product_facts(case: str) -> None:
    result = _result(case)
    assert len({c.fact.fact_id for c in result.cells}) == len(result.cells)
    bound = prose.bind(_facts_by_id(result).values())
    for claim in result.claims:  # every claim resolves against the module's facts and references
        assert prose.issues(claim.text, bound, names=(ISSUER,)) == (), claim.claim_id


def test_headline_values() -> None:
    """A1's headline figures, as the lease states them."""
    cells = {c.fact.fact_id: c for c in _result("positive").cells}

    def shown(fid: str) -> str | None:
        return cells[fid].shown

    assert [shown(f"T2H.4.b2{t}.ebitda") for t in (6, 7, 8)] == ["30.90", "33.10", "35.40"]
    assert [shown(f"T2H.5.d2{t}.closing_cash") for t in (6, 7, 8)] == ["11.47", "(1.22)", "(17.42)"]
    assert [shown(f"T2H.6.d2{t}.total_leverage") for t in (6, 7, 8)] == ["2.70x", "2.27x", "1.65x"]
    assert shown("T2H.2.fcf.check") == "Reconciled to CP-1"
    assert cells["T2H.6.a25.liquidity_headroom"].fact.status == "not_applicable"


def test_break_boundaries() -> None:
    """Lease: crossing is at or beyond the level (<= for FCF and coverage, >= for leverage);
    the minimum-liquidity test is strictly below. No oracle case sits on a level."""
    year = _result("positive").forecast["base"].years[0]
    at = cp2g.Val(D("2"))
    on_level = dataclasses.replace(
        year, fcf=at, coverage=at, total_leverage=at, net_leverage=at, liquidity=at
    )
    path = cp2g.CaseForecast(years=(on_level, on_level, on_level))
    kinds: tuple[cp2g.BreakKind, ...] = (
        "fcf",
        "coverage",
        "total_leverage",
        "net_leverage",
        "liquidity",
    )
    tests = [cp2g.BreakTest(k, k, k, D("2"), None) for k in kinds]
    got = {r.row: r.first for r in cp2g.test_breaks(tests=tests, forecast=path)}
    assert got == {
        "fcf": "FY2026",
        "coverage": "FY2026",
        "total_leverage": "FY2026",
        "net_leverage": "FY2026",
        "liquidity": "Not reached by FY2028",
    }


# --- refusals (calculation level): shape alone, then content in the pinned order -----------------
REFUSALS = {r["id"]: r for r in SUBMISSIONS["refusals"]}
EXPECTED_REFUSALS = {r["id"]: r for r in EXPECTED["refusals"]}
SHAPE_AND_CONTENT = [rid for rid in REFUSALS if rid not in ("v18", "v19", "v20")]


def _refusal_text(rid: str) -> str:
    r = REFUSALS[rid]
    if r.get("payload_text") is not None:
        return str(r["payload_text"])
    payload = r["payload"] if r.get("bind_placeholders") is False else _bind_all(r["payload"])
    return json.dumps(payload)


def _expected_issues(rid: str) -> list[str]:
    return [
        re.sub(r"\{\{FACT_ID:([a-z_]+)\}\}", lambda m: _fig_id(m[1]), issue)
        for issue in EXPECTED_REFUSALS[rid]["expected_issues"]
    ]


@pytest.mark.parametrize("rid", SHAPE_AND_CONTENT)
def test_refusal(rid: str) -> None:
    got = cp2g.payload_issues(_refusal_text(rid), _context("positive"))
    assert list(got) == _expected_issues(rid)
    assert EXPECTED_REFUSALS[rid]["issue_kind"] == ("shape" if rid.startswith("r") else "content")


@pytest.mark.parametrize("case", RUNS + FIXTURES)
def test_oracle_submissions_have_no_issue(case: str) -> None:
    assert cp2g.payload_issues(json.dumps(_bind_all(_payload(case))), _context(case)) == ()


def test_invalid_submission_is_not_composed() -> None:
    payload = _bind_all(REFUSALS["v13"]["payload"])
    sub = cp2g.ForwardSubmission.model_validate_json(json.dumps(payload))
    with pytest.raises(ValueError, match="High is not allowed"):
        cp2g.compute(cp2g.ForwardInputs(context=_context("positive"), submission=sub))


def _input(input_id: str, status: InputStatus = "restricted") -> Input:
    digest = hashlib.sha256(input_id.encode()).hexdigest()
    return Input(input_id=input_id, sha256=digest, status=status)


@pytest.mark.parametrize("rid,upstream_id", [("v18", "CP-2A"), ("v19", "CP-1D"), ("v20", "CP-1")])
def test_stale_input(rid: str, upstream_id: str) -> None:
    """Validator-only (v18-v20): the attempt's bound tuple against a current tuple in which only
    one upstream Input differs; the payload itself is the positive one and has no issue."""
    bound = tuple(
        _input(i, "accepted" if i == "prepared-pack" else "restricted")
        for i in ("prepared-pack", "CP-0", "CP-1", "CP-1D", "CP-2A")
    )
    lit = REFUSALS[rid]["upstream_literal"]["current"][0]
    replaced = Input(input_id=lit["input_id"], sha256=lit["sha256"], status=lit["status"])
    current = tuple(replaced if i.input_id == upstream_id else i for i in bound)
    (issue,) = _expected_issues(rid)
    want = re.sub(
        r"<12 hex of [^>]*>", next(i.sha256[:12] for i in bound if i.input_id == upstream_id), issue
    )
    assert cp2g.stale_issues(bound=bound, current=current) == (want,)
    assert cp2g.stale_issues(bound=bound, current=bound) == ()
    assert (
        cp2g.payload_issues(json.dumps(_bind_all(REFUSALS[rid]["payload"])), _context("positive"))
        == ()
    )


# --- LEAD rulings round 5 (docs/rulings/2026-10-28-stage1.md "# Round 5", CP-2G) ------------------
LTM = "LTM Q4 25: 2025-01-01 to 2025-12-31"
OPERAND_WORDS = {  # G-1
    "revenue": "revenue",
    "ebitda": "EBITDA",
    "interest": "cash interest",
    "taxes": "cash taxes",
    "wc": "working capital change",
    "capex": "capital expenditure",
    "fcf": "free cash flow",
    "debt": "total debt",
    "undrawn": "undrawn revolver",
    "cash": "cash and cash equivalents",
}


def _with_cp1(case: str, metric: str, status: str) -> cp2g.ForwardContext:
    ctx = _context(case)
    unknown = {
        "status": status,
        "amount": None,
        "citations": (),
        "calculation_id": None,
        "limitation": "not disclosed",
    }
    facts = tuple(f.model_copy(update=unknown) if f.row_id == metric else f for f in ctx.cp1_facts)
    return dataclasses.replace(ctx, cp1_facts=facts)


def _plain(payload: dict[str, Any]) -> dict[str, Any]:
    """The payload with every figure reference written out, for inputs that unsettle a fact the
    oracle prose references (a constructed submission, not an oracle payload)."""
    text = re.sub(r"\{\{FIG:[a-z_]+\|[^}]*\}\}", "the stated figure", json.dumps(payload))
    out: dict[str, Any] = json.loads(text)
    return out


def _compose(ctx: cp2g.ForwardContext, payload: dict[str, Any]) -> cp2g.ForwardResult:
    sub = cp2g.ForwardSubmission.model_validate_json(json.dumps(payload))
    return cp2g.compute(cp2g.ForwardInputs(context=ctx, submission=sub))


def _cells(result: cp2g.ForwardResult) -> dict[str, Fact]:
    return {c.fact.fact_id: c.fact for c in result.cells}


def _claim_texts(result: cp2g.ForwardResult) -> dict[str, str]:
    return {c.claim_id: c.text for c in result.claims}


def _gap_of(f: Fact) -> tuple[str, str | None]:
    return f.status, f.limitation


@pytest.mark.parametrize("key", OPERAND_WORDS)
def test_g1_missing_operand_words(key: str) -> None:
    word = OPERAND_WORDS[key]
    ctx = _with_cp1("gap", cp2g.OPERAND_METRIC[key], "missing")
    ops = cp2g.Operands.from_cp1(ctx.cp1_facts)
    assert getattr(ops, key) == cp2g.Val(
        None, f"Not calculable: base {word} is missing in CP-1 ({LTM})"
    )
    line = (
        f"Base {word} is not available in CP-1 for {LTM}: every figure that needs it is "
        "Not calculable."
    )
    assert line in _compose(ctx, _plain(_payload("gap"))).own_limitations


@pytest.mark.parametrize("key,row", [("ebitda", "b03"), ("debt", "b03"), ("interest", "b05")])
def test_g1_unverified_cause_words(key: str, row: str) -> None:
    ctx = _with_cp1("positive", cp2g.OPERAND_METRIC[key], "missing")
    payload = _plain(_payload("positive"))
    assert cp2g.payload_issues(json.dumps(payload), ctx) == ()
    cause = f"base {OPERAND_WORDS[key]} is missing in CP-1 for {LTM}"
    assert _unverified(row, cause) in _compose(ctx, payload).own_limitations


def test_g2_single_first_test_claim() -> None:
    payload = _bind_all(_payload("positive"))
    payload["minimum_liquidity"]["amount"] = "25"  # base liquidity 24.83 in FY2026: one test first
    claims = _claim_texts(_compose(_context("positive"), payload))
    assert claims["T2H.7.base"] == (
        "The first test reached in the base case is Accessible liquidity below the minimum "
        "liquidity in FY2026."
    )


def test_g3_fy28_known_peak_not_calculated() -> None:
    payload = _bind_all(_payload("positive"))
    payload["base_drivers"]["ebitda_margin"]["values"] = ["0", "0.26", "0.27"]
    claims = _claim_texts(_compose(_context("positive"), payload))
    for case, lab in (("base", "base"), ("down", "downside")):
        assert claims[f"T2H.8.{case}"] == (
            f"In the {lab} case, total leverage ends FY2028 at "
            f"{{T2H.8.{case}.total_leverage_fy28|x}}; the peak is not calculated: "
            f"[T2H.8.{case}.peak_total_leverage]."
        )


def test_g3_peak_known_fy28_not_calculated() -> None:
    """A known peak needs every forecast year, so compute never reaches this pair; the wording
    is checked on the template alone."""
    got = cp2g._leverage_claim("base", "{P|x}", "[F]", (True, False), "FY2027")
    assert got == (
        "In the base case, total leverage peaks at {P|x} in FY2027; FY2028 leverage is not "
        "calculated: [F]."
    )


def test_g4_margin_on_non_positive_revenue() -> None:
    payload = _bind_all(_payload("positive"))
    payload["base_drivers"]["revenue_growth"]["values"] = ["-1", "0.03", "0.03"]
    cells = _cells(_compose(_context("positive"), payload))
    reason = "Not calculable: revenue is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
    for row in ("b26", "b27", "b28", "d26", "d27", "d28"):
        assert _gap_of(cells[f"T2H.4.{row}.margin"]) == ("missing", reason)


def _unknown_shock(field: str) -> cp2g.ForwardContext:
    ctx = _context("positive")
    unknown = {
        "status": "missing",
        "amount": None,
        "calculation_id": None,
        "value_class": None,
        "formula": None,
        "limitation": "Not stated by CP-2A",
    }
    scenarios = tuple(
        dataclasses.replace(s, **{field: getattr(s, field).model_copy(update=unknown)})
        if s.row == "s03"
        else s
        for s in ctx.cp2a.scenarios
    )
    return dataclasses.replace(ctx, cp2a=dataclasses.replace(ctx.cp2a, scenarios=scenarios))


_DOWN = re.compile(r"T2H\.[4-6]\.d2[678]\.|T2H\.7\.[a-z0-9]+\.down_first$|T2H\.8\.down\.")
_BASE = re.compile(r"T2H\.[4-6]\.(a25|b2[678])\.|T2H\.7\.[a-z0-9]+\.base_first$|T2H\.8\.base\.")


@pytest.mark.parametrize(
    "field,row,words",
    [("decline", "d01", "EBITDA decline"), ("increase", "d02", "interest increase")],
)
def test_g5_unknown_cp2a_shock(field: str, row: str, words: str) -> None:
    result = _compose(_unknown_shock(field), _bind_all(_payload("positive")))
    cells, was = _cells(result), _cells(_result("positive"))
    reason = f"Not calculable: CP-2A scenario s03 states no known {words}"
    down = {fid: f for fid, f in cells.items() if _DOWN.match(fid)}
    assert set(down) == {fid for fid in was if _DOWN.match(fid)}
    label = "T2H.8.down.downstream"  # the downstream-module label is not a downside value
    assert {fid: _gap_of(f) for fid, f in down.items() if fid != label} == {
        fid: ("missing", reason) for fid in down if fid != label
    }
    assert down[label] == was[label]
    assert {fid: f for fid, f in cells.items() if _BASE.match(fid)} == {
        fid: f for fid, f in was.items() if _BASE.match(fid)
    }
    for t in (1, 2, 3):  # the T2H.3 copy keeps CP-2A's status and limitation
        assert _gap_of(cells[f"T2H.3.{row}.fy{t}"]) == ("missing", "Not stated by CP-2A")
    assert (
        "CP-2A scenario s03 has no known shock, so the downside case is not calculated."
        in result.own_limitations
    )
    claims = _claim_texts(result)
    assert "[T2H.6.d26.total_leverage]" in claims["T2H.6.down"]
    assert claims["T2H.8.down"] == (
        "In the downside case, the leverage path is not fully calculable: peak "
        "[T2H.8.down.peak_total_leverage], FY2028 [T2H.8.down.total_leverage_fy28]."
    )


CP2D_LINE = (
    "CP-2D (liquidity cash flow bridge) is bound but its liquidity bridge is not read in this "
    "version."
)


def test_g6_bound_cp2d() -> None:
    ctx = dataclasses.replace(_context("gap"), cp2d_status="restricted")
    result = _compose(ctx, _bind_all(_payload("gap")))
    assert CP2D_LINE in result.own_limitations
    assert [x for x in result.own_limitations if x != CP2D_LINE] == list(
        _result("gap").own_limitations
    )
    assert _cells(result)["T2H.1.u_cp2d.status"].text == "restricted"


def _other_definition(test: str) -> cp2g.ForwardContext:
    ctx = _context("positive")
    breaks = tuple(
        dataclasses.replace(b, test=test) if b.row == "b01" else b for b in ctx.cp2a.breaks
    )
    return dataclasses.replace(ctx, cp2a=dataclasses.replace(ctx.cp2a, breaks=breaks))


def test_g7_other_definition_wording_settles() -> None:
    other = "Free cash flow below zero"
    ctx = _other_definition(other)
    payload = _bind_all(_payload("positive"))
    assert cp2g.payload_issues(json.dumps(payload), ctx) == ()
    result = _compose(ctx, payload)
    cells, was = _cells(result), _cells(_result("positive"))
    reason = f"Not calculable: CP-2A definition break b01 has a test CP-2G does not map ({other})"
    for field in ("metric", "base_first", "down_first"):
        assert _gap_of(cells[f"T2H.7.b01.{field}"]) == ("missing", reason)
    for field in ("level", "static_decline"):
        assert cells[f"T2H.7.b01.{field}"] == was[f"T2H.7.b01.{field}"]
    assert cells["T2H.7.b01.test"].text == other
    assert (
        f"CP-2A definition break b01 has the test {other}, which CP-2G does not map; its first "
        "years are not calculated." in result.own_limitations
    )
    payload["break_metrics"].append({"break_id": "b01", "metric": "total_leverage"})
    assert cp2g.payload_issues(json.dumps(payload), ctx) == (
        "break_metrics[3].break_id: b01 is a definition break with a fixed metric",
    )


def _unverified(row: str, cause: str) -> str:
    return (
        f"The metric named for CP-2A break {row} could not be checked against its CP-2A required "
        f"decline: {cause}."
    )


@pytest.mark.parametrize("amount", ["0", "-5"])
def test_g8_non_positive_base_ebitda(amount: str) -> None:
    ctx = _context("positive")
    facts = tuple(
        f.model_copy(update={"amount": D(amount)}) if f.row_id == "ebitda" else f
        for f in ctx.cp1_facts
    )
    ctx = dataclasses.replace(ctx, cp1_facts=facts)
    payload = _bind_all(_payload("positive"))
    assert cp2g.payload_issues(json.dumps(payload), ctx) == ()
    cause = f"base EBITDA is zero or negative in CP-1 for {LTM} (ZERO_OR_NEGATIVE_DENOMINATOR)"
    lines = _compose(ctx, payload).own_limitations
    for row in ("b03", "b04", "b05"):
        assert _unverified(row, cause) in lines


@pytest.mark.parametrize("amount", ["0", "-1"])
def test_g8_non_positive_cp2a_level(amount: str) -> None:
    ctx = _context("positive")
    breaks = tuple(
        dataclasses.replace(b, level=b.level.model_copy(update={"amount": D(amount)}))
        if b.row == "b03"
        else b
        for b in ctx.cp2a.breaks
    )
    ctx = dataclasses.replace(ctx, cp2a=dataclasses.replace(ctx.cp2a, breaks=breaks))
    payload = _bind_all(_payload("positive"))
    assert cp2g.payload_issues(json.dumps(payload), ctx) == ()
    cause = "the CP-2A level of b03 is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
    assert _unverified("b03", cause) in _compose(ctx, payload).own_limitations


def _cp1d_with(field: str, **update: Any) -> cp2g.ForwardContext:
    ctx = _context("positive")
    fact = getattr(ctx.cp1d, field).model_copy(update=update)
    return dataclasses.replace(ctx, cp1d=dataclasses.replace(ctx.cp1d, **{field: fact}))


def _cp1d_line(label: str) -> str:
    return (
        f"CP-1D is bound but its supported {label} is not a known {LTM} figure, so starting "
        "leverage is not restated on it."
    )


_CP1D_DEPENDENT = (
    "T2H.2.ebitda_adjustment.value",
    "T2H.8.base.ebitda_fy26_vs_supported",
    "T2H.8.down.ebitda_fy26_vs_supported",
)


@pytest.mark.parametrize("status", ["missing", "not_applicable"])
def test_g9_cp1d_supported_not_known(status: str) -> None:
    ctx = _cp1d_with(
        "supported", status=status, amount=None, calculation_id=None, limitation="Not in CP-1D"
    )
    result = _compose(ctx, _bind_all(_payload("positive")))
    cells = _cells(result)
    assert _gap_of(cells["T2H.2.ebitda_supported.value"]) == (status, "Not in CP-1D")
    reason = "Not calculable: CP-1D supported Supported adjusted EBITDA is not available"
    for fid in _CP1D_DEPENDENT:
        assert _gap_of(cells[fid]) == ("missing", reason)
    assert _cp1d_line("Supported adjusted EBITDA") in result.own_limitations


def test_g9_cp1d_supported_other_period() -> None:
    period = "FY2025: 2025-01-01 to 2025-12-31"
    result = _compose(_cp1d_with("supported", period=period), _bind_all(_payload("positive")))
    cells = _cells(result)
    copied = cells["T2H.2.ebitda_supported.value"]
    assert (copied.status, copied.amount, copied.period) == ("known", D("31.8"), period)
    reason = f"Not compared: CP-1D supported earnings are for {period}, not {LTM}"
    for fid in _CP1D_DEPENDENT:
        assert _gap_of(cells[fid]) == ("missing", reason)
    assert _cp1d_line("Supported adjusted EBITDA") in result.own_limitations


def test_g9_cp1d_leverage_not_known_uses_chip() -> None:
    ctx = _cp1d_with(
        "total_leverage",
        status="not_applicable",
        amount=None,
        calculation_id=None,
        limitation="Not in CP-1D",
    )
    result = _compose(ctx, _plain(_payload("positive")))
    cells = _cells(result)
    assert _gap_of(cells["T2H.2.total_leverage_supported.value"]) == (
        "not_applicable",
        "Not in CP-1D",
    )
    assert _claim_texts(result)["T2H.2.cp1d"] == (
        "On the earnings CP-1D supports, opening total leverage is "
        "[T2H.2.total_leverage_supported.value] against {T2H.2.total_leverage.value|x} on "
        "reported earnings."
    )
    assert _cp1d_line("Total leverage") in result.own_limitations
    assert cells["T2H.2.ebitda_adjustment.value"].status == "known"


def test_g_decisions_unknown_cp2a_copy_keeps_status() -> None:
    """G-decisions: a copy of an unknown CP-2A cell keeps CP-2A's status (here not_applicable)."""
    ctx = _context("positive")
    na = {"status": "not_applicable", "amount": None, "calculation_id": None, "limitation": "n/a"}
    breaks = tuple(
        dataclasses.replace(b, required_decline=b.required_decline.model_copy(update=na))
        if b.row == "b03"
        else b
        for b in ctx.cp2a.breaks
    )
    ctx = dataclasses.replace(ctx, cp2a=dataclasses.replace(ctx.cp2a, breaks=breaks))
    cells = _cells(_compose(ctx, _bind_all(_payload("positive"))))
    assert _gap_of(cells["T2H.7.b03.static_decline"]) == ("not_applicable", "n/a")


def test_selection_rule_needs_exactly_one_fact() -> None:
    facts = _context("gap").cp1_facts
    with pytest.raises(ValueError, match="exactly one"):
        cp2g.select_cp1(facts[1:])
    with pytest.raises(ValueError, match="exactly one"):
        cp2g.select_cp1((*facts, facts[0].model_copy(update={"fact_id": "interface-fact:dup"})))


# --- property tests (lease A-section; expected.json property_tests) ------------------------------
def _dec(lo: int, hi: int, places: int = 4) -> st.SearchStrategy[Decimal]:
    return st.integers(lo, hi).map(lambda n: Decimal(n).scaleb(-places))


def _known_ops(
    r: Decimal, e: Decimal, i: Decimal, d: Decimal, c: Decimal, u: Decimal
) -> cp2g.Operands:
    v = cp2g.Val
    return cp2g.Operands(
        revenue=v(r),
        ebitda=v(e),
        interest=v(i),
        taxes=v(D(0)),
        wc=v(D(0)),
        capex=v(D(0)),
        fcf=v(e - i),
        debt=v(d),
        cash=v(c),
        undrawn=v(u),
    )


_drivers = st.builds(
    lambda g, m, c, w, r, div, rep: cp2g.Drivers(
        revenue_growth=g,
        ebitda_margin=m,
        capex_pct_revenue=c,
        tax_wc_pct_revenue=w,
        interest_rate=r,
        dividends=div,
        debt_repayment=rep,
    ),
    st.tuples(_dec(-5000, 5000), _dec(-5000, 5000), _dec(-5000, 5000)),
    st.tuples(_dec(1, 10000), _dec(1, 10000), _dec(1, 10000)),
    st.tuples(_dec(0, 3000), _dec(0, 3000), _dec(0, 3000)),
    st.tuples(_dec(0, 3000), _dec(0, 3000), _dec(0, 3000)),
    st.tuples(_dec(0, 2000), _dec(0, 2000), _dec(0, 2000)),
    st.tuples(_dec(0, 500, 1), _dec(0, 500, 1), _dec(0, 500, 1)),
    st.tuples(_dec(0, 100, 1), _dec(0, 100, 1), _dec(0, 100, 1)),
)
_ops = st.builds(
    _known_ops,
    _dec(1000, 100000, 1),
    _dec(10, 50000, 1),
    _dec(0, 5000, 1),
    _dec(400, 20000, 1),
    _dec(-1000, 5000, 1),
    _dec(0, 1000, 1),
)
_shock = st.tuples(_dec(0, 10000), _dec(0, 10000))


def _f(v: cp2g.Val) -> Fraction:
    assert v.amount is not None
    return Fraction(v.amount)


@settings(max_examples=150, deadline=None)
@given(ops=_ops, drivers=_drivers, shock=st.none() | _shock)
def test_property_roll_forward(
    ops: cp2g.Operands, drivers: cp2g.Drivers, shock: tuple[Decimal, Decimal] | None
) -> None:
    path = cp2g.forecast(operands=ops, drivers=drivers, shock=shock)
    debt, cash = _f(ops.debt), _f(ops.cash)
    for t, y in enumerate(path.years):
        rep, div = Fraction(drivers.debt_repayment[t]), Fraction(drivers.dividends[t])
        assert (_f(y.opening_debt), _f(y.opening_cash)) == (debt, cash)
        assert _f(y.closing_debt) == _f(y.opening_debt) - rep
        assert _f(y.closing_cash) == _f(y.opening_cash) + _f(y.fcf) - div - rep
        assert _f(y.fcf) == _f(y.ebitda) - _f(y.interest) - _f(y.tax_wc) - _f(y.capex)
        debt, cash = _f(y.closing_debt), _f(y.closing_cash)


@settings(max_examples=150, deadline=None)
@given(ops=_ops, drivers=_drivers, shock=_shock)
def test_property_downside_dominance(
    ops: cp2g.Operands, drivers: cp2g.Drivers, shock: tuple[Decimal, Decimal]
) -> None:
    base = cp2g.forecast(operands=ops, drivers=drivers, shock=None)
    down = cp2g.forecast(operands=ops, drivers=drivers, shock=shock)
    for b, d in zip(base.years, down.years, strict=True):
        assert _f(d.ebitda) <= _f(b.ebitda)
        assert _f(d.interest) >= _f(b.interest)
        assert _f(d.fcf) <= _f(b.fcf)


@settings(max_examples=150, deadline=None)
@given(ops=_ops, drivers=_drivers, s1=_dec(0, 10000), s2=_dec(0, 10000), k=_dec(0, 10000))
def test_property_monotonic(
    ops: cp2g.Operands, drivers: cp2g.Drivers, s1: Decimal, s2: Decimal, k: Decimal
) -> None:
    lo, hi = sorted((s1, s2))
    a = cp2g.forecast(operands=ops, drivers=drivers, shock=(lo, k))
    b = cp2g.forecast(operands=ops, drivers=drivers, shock=(hi, k))
    for ya, yb in zip(a.years, b.years, strict=True):
        assert _f(yb.ebitda) <= _f(ya.ebitda)
        if ya.total_leverage.amount is not None and yb.total_leverage.amount is not None:
            assert yb.total_leverage.amount >= ya.total_leverage.amount


@settings(max_examples=150, deadline=None)
@given(r=_dec(1000, 100000, 1), m=_dec(1, 10000), rate=_dec(1, 3000), d=_dec(400, 20000, 1))
def test_property_base_control(r: Decimal, m: Decimal, rate: Decimal, d: Decimal) -> None:
    """FY2025-equivalent drivers (no growth, the base margin and rate, no repayment) reproduce
    the base EBITDA, interest, leverage and coverage in the first forecast year."""
    e, i = r * m, d * rate
    ops = _known_ops(r, e, i, d, D(0), D(0))
    zero = (D(0), D(0), D(0))
    drivers = cp2g.Drivers(
        revenue_growth=zero,
        ebitda_margin=(m, m, m),
        capex_pct_revenue=zero,
        tax_wc_pct_revenue=zero,
        interest_rate=(rate, rate, rate),
        dividends=zero,
        debt_repayment=zero,
    )
    y = cp2g.forecast(operands=ops, drivers=drivers, shock=None).years[0]
    assert (_f(y.ebitda), _f(y.interest)) == (Fraction(e), Fraction(i))
    assert _f(y.total_leverage) == round_38(Fraction(d) / Fraction(e))
    assert _f(y.coverage) == round_38(Fraction(e) / Fraction(i))


def round_38(x: Fraction) -> Fraction:
    """The correctly rounded 38-significant-digit half-even value of an exact rational."""
    from decimal import ROUND_HALF_EVEN, Context

    return Fraction(
        Context(prec=38, rounding=ROUND_HALF_EVEN).divide(
            Decimal(x.numerator), Decimal(x.denominator)
        )
    )


_hits = st.lists(st.sampled_from([True, False, None]), min_size=3, max_size=3)


@settings(max_examples=200, deadline=None)
@given(hits=_hits)
def test_property_first_result(hits: list[bool | None]) -> None:
    got = cp2g.first_result(tuple(hits))
    met = [t for t, h in enumerate(hits) if h]
    if met and None not in hits[: met[0]]:
        assert got == cp2g.FY[met[0]]
    elif not met and None not in hits:
        assert got == "Not reached by FY2028"
    else:
        assert got == "Not calculable"


_RECIPE_KINDS: list[cp2g.BreakKind] = ["total_leverage", "net_leverage", "coverage"]


@settings(max_examples=200, deadline=None)
@given(
    e=_dec(10, 50000, 1),
    d=_dec(400, 20000, 1),
    c=_dec(0, 300, 1),
    i=_dec(1, 5000, 1),
    level=_dec(1, 90, 1),
    kind=st.sampled_from(_RECIPE_KINDS),
)
def test_property_break_decline_round_trip(
    e: Decimal, d: Decimal, c: Decimal, i: Decimal, level: Decimal, kind: cp2g.BreakKind
) -> None:
    ops = _known_ops(D(100000), e, i, d, c, D(0))
    s = cp2g.break_decline(kind=kind, level=level, operands=ops)
    assert s is not None
    stressed = Fraction(e) * (1 - s)
    if kind == "coverage":
        assert stressed / Fraction(i) == Fraction(level)
    else:
        num = Fraction(d) if kind == "total_leverage" else Fraction(d) - Fraction(c)
        assert num / stressed == Fraction(level)
