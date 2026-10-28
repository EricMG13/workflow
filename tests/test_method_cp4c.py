"""CP-4C Stage 1: the pure restructuring waterfall equals the frozen oracle (cases/cp4c-owner).

Inputs are built from the oracle's own literals: the CP-1 T4.10 facts of `cp1_inputs` and the
T4.18 rows of `cp1_references`, the pinned CP-2G, CP-2A and CP-4 oracle facts each case's
`cp2g_head` / `cp2a_head` / `cp4_head` names (read from cases/cp2g-owner, cp2a-owner and
cp4-owner, never from their cores), the literal analyst submissions and the frozen financial and
legal packs. Every expected value is read from expected.json.

Stage 1 stand-ins for what Stage 2 binds from real heads: each CP-1 fact gets the id
`interface-fact:<sha256 of its label>`, the calculated CP-1 EBITDA a calculation id and the source
CP-1 total debt a citation of its frozen balance-sheet line; CP-4 facts carry no citations (the
oracle records only their (source, locator) pairs). `{{FIG:name|token}}` becomes
`{<fact_id>|token}` (manifest.json run_time_bindings).
"""

import copy
import hashlib
import json
import re
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from deploy_vii import prose
from deploy_vii.contracts import Citation, Fact, Input, InputStatus, Run, Source, Span
from deploy_vii.preparation import PreparedPack
from deploy_vii.report_view import fact_spelling, figure_unit
from deploy_workflow.owners import cp4c

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "cp4c-owner"
# Oracle pins: cases/PINS.json, the shared manifest LEAD regenerates (python3 -I cases/pins.py).
# The CP-4C oracle and builder and the upstream oracle files this test reads; the files it does not
# list (the financial and legal manifests) are pinned by the pinned CP-4C manifest's `pins`.
PINS: dict[str, str] = json.loads((ROOT / "cases" / "PINS.json").read_text(encoding="utf-8"))
PINNED = (
    *(
        f"cases/cp4c-owner/{name}"
        for name in ("manifest.json", "submissions.json", "expected.json", "builder/build.py")
    ),
    "cases/cp2g-owner/expected.json",
    "cases/cp2a-owner/expected.json",
    "cases/cp4-owner/expected.json",
)


def _pinned(rel: str, pins: dict[str, str] = PINS) -> Any:
    data = (ROOT / rel).read_bytes()
    assert hashlib.sha256(data).hexdigest() == pins[rel], rel
    return json.loads(data)


EXPECTED: dict[str, Any] = _pinned("cases/cp4c-owner/expected.json")
SUBMISSIONS: dict[str, Any] = _pinned("cases/cp4c-owner/submissions.json")
MANIFEST: dict[str, Any] = _pinned("cases/cp4c-owner/manifest.json")
CP2G_EXP: dict[str, Any] = _pinned("cases/cp2g-owner/expected.json")
CP2A_EXP: dict[str, Any] = _pinned("cases/cp2a-owner/expected.json")
CP4_EXP: dict[str, Any] = _pinned("cases/cp4-owner/expected.json")
FIN: dict[str, Any] = _pinned("cases/financial/manifest.json", MANIFEST["pins"])
LEGAL: dict[str, Any] = _pinned("cases/legal/manifest.json", MANIFEST["pins"])
FINANCIAL = next(s for s in FIN["sources"] if s["source_id"] == "financial")

RUNS = ("positive", "gap")
FIXTURES = ("fixture_ev_zero", "fixture_ebitda_missing", "fixture_debt_missing")
CASES = RUNS + FIXTURES
D = Decimal
UPSTREAM_PREFIXES = ("cp1:", "cp2a:", "cp2g:", "cp4:")


def test_oracle_files_are_the_pinned_revision() -> None:
    for rel in PINNED:
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == PINS[rel], rel
    for rel in ("cases/financial/manifest.json", "cases/legal/manifest.json"):
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == MANIFEST["pins"][rel], rel


def _norm(x: Decimal | None) -> str | None:
    if x is None:
        return None
    text = format(x, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def _status_word(module_id: str) -> InputStatus:
    """The bound status of an upstream (expected.json execution.statuses: 'restricted (...)')."""
    word = str(EXPECTED["execution"]["statuses"][module_id]).split()[0].rstrip(":")
    statuses: tuple[InputStatus, ...] = ("accepted", "restricted", "blocked")
    return next(s for s in statuses if s == word)


def _after(pointer: str, prefix: str) -> str:
    assert pointer.startswith(prefix), pointer
    return pointer[len(prefix) :]


# --- the pack -----------------------------------------------------------------------------------
def _legal_case(case: str) -> str:
    return _after(EXPECTED["cases"][case]["legal_pack"], "cases/legal/manifest.json cases[")[:-1]


def _source(rec: dict[str, Any]) -> Source:
    joined = "\f".join(p["text"] for p in rec["pages"])
    assert hashlib.sha256(joined.encode("utf-8")).hexdigest() == rec["sha256"]
    return Source(
        source_id=rec["source_id"],
        name=rec["name"],
        status=rec["status"],
        sha256=rec["sha256"],
        spans=tuple(Span(locator=p["locator"], text=p["text"]) for p in rec["pages"]),
        extraction_status="complete",
        limitation=rec.get("limitation"),
    )


@cache
def _pack(case: str) -> PreparedPack:
    legal = next(c["legal_source"] for c in LEGAL["cases"] if c["case_id"] == _legal_case(case))
    run_case = case if case in RUNS else "positive"
    run = Run.model_validate_json(json.dumps(MANIFEST["cases"][run_case]["run"]))
    sources = tuple(_source(s) for s in (*FIN["sources"], legal))
    return PreparedPack(run=run, sources=sources)


# --- upstream facts from the oracles ------------------------------------------------------------
def _cp1_id(label: str) -> str:
    return "interface-fact:" + hashlib.sha256(label.encode()).hexdigest()


def _page_line(locator: str, prefix: str) -> str:
    page: str = next(p["text"] for p in FINANCIAL["pages"] if p["locator"] == locator)
    return next(line for line in page.split("\n") if line.startswith(prefix))


TOTAL_DEBT_CITATION = Citation(
    source_id="financial",
    source_sha256=FINANCIAL["sha256"],
    locator="page:4",
    quote=_page_line("page:4", "Total debt  "),
)


def _cp1_t410(metric: str, rec: dict[str, Any]) -> Fact:
    known = rec["status"] == "known"
    assert rec["unit_class"] == "amount"
    source = known and rec["value_class"] == "source"
    return Fact(
        fact_id=_cp1_id(rec["label"]),
        label=rec["label"],
        table_id="T4.10",
        row_id=metric,
        field="ltm",
        amount=D(rec["amount_exact"]) if known else None,
        status=rec["status"],
        unit="MILLIONS",
        currency="USD",
        scale=D(1000000),
        period=rec["period"],
        citations=(TOTAL_DEBT_CITATION,) if source else (),
        calculation_id=f"calc:cp1-{metric}"
        if known and rec["value_class"] == "calculated"
        else None,
        value_class=rec["value_class"],
        limitation=rec["limitation"],
    )


T418 = MANIFEST["fact_selection_rule"]["cp1_t418"]


def _cp1_t418(case: str, field: str) -> Fact:
    rows = EXPECTED["cases"][case]["cp1_references"]["rows"]
    facility = T418["facility_id"]
    label = f"T4.18 · {facility} · {field} · "
    row = next(r for r in rows if r["label"].startswith(label))
    assert row["status"] == "known" and row["text"] == T418["observed"][f"{facility}.{field}"]
    return Fact(
        fact_id=_cp1_id(row["label"]),
        label=f"{facility} · {field}",
        table_id="T4.18",
        row_id=facility,
        field=field,
        text=row["text"],
        period=row["period"],
        value_class=row["value_class"],
    )


def _fact(rec: dict[str, Any], **override: Any) -> Fact:
    """A settled upstream fact record (CP-2G, CP-2A oracle) as the product Fact it stands for."""
    amount = rec.get("amount_exact")
    return Fact(
        **{
            "fact_id": rec["fact_id"],
            "label": rec["label"],
            "table_id": rec["table_id"],
            "row_id": rec["row_id"],
            "field": rec["field"],
            "amount": None if amount is None else D(amount),
            "text": rec.get("text"),
            "status": rec["status"],
            "unit": rec.get("unit"),
            "currency": rec.get("currency"),
            "scale": D(rec.get("scale", "1")),
            "decimals": rec.get("decimals"),
            "period": rec.get("period"),
            "calculation_id": rec.get("calculation_id"),
            "value_class": rec.get("value_class"),
            "formula": rec.get("formula"),
            "limitation": rec.get("limitation"),
            **override,
        }
    )


CASE_ROW = {"base": "b", "down": "d"}
YEARS: tuple[cp4c.ForecastYear, ...] = ("FY2026", "FY2027", "FY2028")


def _cp2g(case: str) -> cp4c.Cp2gHead:
    exp = EXPECTED["cases"][case]
    source = _after(exp["cp2g_head"]["source"], "cases/cp2g-owner/expected.json cases.")
    recs = {f["fact_id"]: f for f in CP2G_EXP["cases"][source]["facts"]}
    # A synthetic upstream variant (fixture_ebitda_missing) is stated by the case's own
    # cp2g_references row: the copied fact there differs from the CP-2G oracle in its status.
    overrides = {
        r["fact_id"]: r
        for r in exp["cp2g_references"]["rows"]
        if r["status"] != recs[r["fact_id"]]["status"]
    }
    assert bool(overrides) == exp["cp2g_head"]["ebitda_override"]

    def fact(fid: str) -> Fact:
        row = overrides.get(fid)
        if row is None:
            return _fact(recs[fid])
        return _fact(recs[fid], status=row["status"], amount=None, limitation=row["limitation"])

    ebitda = tuple(
        cp4c.Cp2gEbitda(
            case=c,
            year=y,
            fact=fact(f"T2H.4.{CASE_ROW[c]}{26 + t}.ebitda"),
            derives_from=tuple(recs[f"T2H.4.{CASE_ROW[c]}{26 + t}.ebitda"]["derives_from"]),
        )
        for c in ("base", "down")
        for t, y in enumerate(YEARS)
    )
    return cp4c.Cp2gHead(
        status=_status_word("CP-2G"),
        ebitda=ebitda,
        base_first=fact("T2H.7.b01.base_first"),
        down_first=fact("T2H.7.b01.down_first"),
    )


def _cp2a(case: str) -> cp4c.Cp2aHead:
    source = _after(
        EXPECTED["cases"][case]["cp2a_head"]["source"], "cases/cp2a-owner/expected.json cases."
    )
    c = CP2A_EXP["cases"][source]
    return cp4c.Cp2aHead(
        status=_status_word("CP-2A"),
        base_period=c["base_period"],
        facts=tuple(_fact(f) for f in c["facts"] if f["table_id"] == "T2B.1"),
    )


def _cp4(case: str) -> cp4c.Cp4Head:
    head = EXPECTED["cases"][case]["cp4_head"]
    source = _after(head["source"], "cases/cp4-owner/expected.json ")
    assert source.endswith(".CP-4")
    cp4 = CP4_EXP[source[: -len(".CP-4")]]["CP-4"]
    assert cp4["status"] == head["status"]
    facts = []
    for table in cp4["tables"]:
        for row in table["rows"]:
            for f in row["facts"]:
                if "text" not in f:  # a run-time bound CP-4 figure: CP-4C reads none of them
                    continue
                facts.append(
                    Fact(
                        fact_id=f["fact_id"],
                        label=f["column"],
                        table_id=table["table_id"],
                        row_id=row["row_id"],
                        field=f["fact_id"].rsplit(".", 1)[1],
                        text=f["text"],
                        status=f["status"],
                        value_class=f["value_class"],
                        limitation=f["limitation"],
                    )
                )
    return cp4c.Cp4Head(status=head["status"], facts=tuple(facts))


def _cp1(case: str) -> cp4c.Cp1Head:
    t410 = tuple(_cp1_t410(m, r) for m, r in EXPECTED["cases"][case]["cp1_inputs"].items())
    return cp4c.Cp1Head(
        status=_status_word("CP-1"),
        t410=t410,
        facility_id=T418["facility_id"],
        secured_status=_cp1_t418(case, "secured_status"),
        seniority=_cp1_t418(case, "seniority"),
    )


@cache
def _context(case: str) -> cp4c.Cp4cContext:
    return cp4c.Cp4cContext(
        pack=_pack(case),
        cp1=_cp1(case),
        cp2a=_cp2a(case),
        cp2g=_cp2g(case),
        cp4=_cp4(case),
    )


def _upstream(case: str) -> dict[str, Fact]:
    """lineage id -> the upstream fact (the oracle's cp1:/cp2g:/cp2a:/cp4: lineage space)."""
    ctx = _context(case)
    out = {f"cp1:{f.row_id}": f for f in ctx.cp1.t410}
    for f in (ctx.cp1.secured_status, ctx.cp1.seniority):
        out[f"cp1:{ctx.cp1.facility_id}.{f.field}"] = f
    out.update({f"cp2g:{e.fact.fact_id}": e.fact for e in ctx.cp2g.ebitda})
    for f in (ctx.cp2g.base_first, ctx.cp2g.down_first):
        out[f"cp2g:{f.fact_id}"] = f
    out.update({f"cp2a:{f.fact_id}": f for f in ctx.cp2a.facts})
    out.update({f"cp4:{f.fact_id}": f for f in ctx.cp4.facts})
    return out


# --- submissions and FIG binding ----------------------------------------------------------------
def _fig_id(name: str, case: str = "positive") -> str:
    fig = SUBMISSIONS["figures"][name]
    if fig["source"] == "cp1":
        return _cp1_id(EXPECTED["cases"][case]["cp1_inputs"][fig["metric"]]["label"])
    return str(fig["fact_id"])


def _bind(text: str, case: str = "positive") -> str:
    return re.sub(
        r"\{\{FIG:([a-z_0-9]+)\|([^}]*)\}\}",
        lambda m: "{" + _fig_id(m[1], case) + "|" + m[2] + "}",
        text,
    )


def _bind_all(obj: Any, case: str = "positive") -> Any:
    if isinstance(obj, str):
        return _bind(obj, case)
    if isinstance(obj, list):
        return [_bind_all(x, case) for x in obj]
    if isinstance(obj, dict):
        return {k: _bind_all(v, case) for k, v in obj.items()}
    return obj


def _payload(case: str) -> dict[str, Any]:
    group = SUBMISSIONS["fixtures"] if case.startswith("fixture") else SUBMISSIONS["cases"]
    return copy.deepcopy(group[case]["restructuring_fulcrum"])


def _submission(payload: dict[str, Any]) -> cp4c.RestructuringSubmission:
    return cp4c.RestructuringSubmission.model_validate_json(json.dumps(payload))


def _inputs(case: str) -> cp4c.Cp4cInputs:
    sub = _submission(_bind_all(_payload(case), case))
    return cp4c.Cp4cInputs(context=_context(case), submission=sub)


@cache
def _result(case: str) -> cp4c.RestructuringResult:
    return cp4c.compute(_inputs(case))


# --- projections of the module output onto the oracle's record shapes ---------------------------
def _cites(citations: tuple[Citation, ...]) -> list[dict[str, str]]:
    return [{"source_id": c.source_id, "locator": c.locator, "quote": c.quote} for c in citations]


def _record(cell: cp4c.Cell) -> dict[str, Any]:
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
    else:
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
    if cell.quoted:
        rec["citations"] = _cites(cell.quoted)
    return rec


def _facts_by_id(result: cp4c.RestructuringResult) -> dict[str, Fact]:
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
    assert [t["table_id"] for t in got] == EXPECTED["d8_table_ids"]["cp4c_table_ids"]


@pytest.mark.parametrize("case", CASES)
def test_waterfall_summary(case: str) -> None:
    result = _result(case)
    got = {}
    for case_id, w in result.waterfalls.items():
        got[case_id] = {
            "ev": _norm(result.enterprise_values[case_id].amount),
            "break": None if w.value_break is None else list(w.value_break),
            "residual": _norm(w.residual.amount),
            "recovery": {k: _norm(a.recovery.amount) for k, a in w.classes.items()},
            "distribution": {k: _norm(a.distribution.amount) for k, a in w.classes.items()},
        }
    assert got == EXPECTED["cases"][case]["waterfall"]


def _named_figures(case: str) -> dict[str, str]:
    """fact id -> FIG name, for the names this case's prose uses."""
    names = re.findall(r"\{\{FIG:([a-z_0-9]+)\|", json.dumps(_payload(case)))
    return {_fig_id(n, case): n for n in names}


def _ref_rows_cp1(table: cp4c.RefTable, case: str) -> list[dict[str, Any]]:
    figs = _named_figures(case)
    rows = []
    for r in table.rows:
        f = r.fact
        rec: dict[str, Any] = {"row_id": r.row_id, "figure": figs.get(f.fact_id), "label": r.label}
        if f.table_id == "T4.10":
            cell_text = fact_spelling(f, None)[2] if f.status == "known" else None
            rec.update(
                cp1_label=f.label,
                period=f.period,
                status=f.status,
                unit="US$ m",
                shown=None if cell_text is None else f"{cell_text} {figure_unit(f)}",
                cell_text=cell_text,
            )
        else:
            rec.update(
                cp1_label=None,
                period=f.period,
                status=f.status,
                unit=None,
                shown=f.text,
                cell_text=f.text,
                text=f.text,
            )
        rec.update(value_class=f.value_class, amount_exact=_norm(f.amount), limitation=f.limitation)
        rows.append(rec)
    return rows


def _ref_rows_upstream(table: cp4c.RefTable, case: str) -> list[dict[str, Any]]:
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
            "text": r.fact.text,
            "value_class": r.fact.value_class,
            "amount_exact": _norm(r.fact.amount),
            "limitation": r.fact.limitation,
        }
        for r in table.rows
    ]


@pytest.mark.parametrize("case", CASES)
def test_references(case: str) -> None:
    exp = EXPECTED["cases"][case]
    cp1_refs, cp2g_refs, cp2a_refs, cp4_refs = _result(case).references
    for table, key in (
        (cp1_refs, "cp1_references"),
        (cp2g_refs, "cp2g_references"),
        (cp2a_refs, "cp2a_references"),
        (cp4_refs, "cp4_references"),
    ):
        want = exp[key]
        assert (table.table_id, table.title, table.row_header) == (
            want["table_id"],
            want["title"],
            want["row_header"],
        )
    want_cp1 = [
        {k: v for k, v in r.items() if k != "fact_id"} for r in exp["cp1_references"]["rows"]
    ]
    assert _ref_rows_cp1(cp1_refs, case) == want_cp1
    assert _ref_rows_upstream(cp2g_refs, case) == exp["cp2g_references"]["rows"]
    assert _ref_rows_upstream(cp2a_refs, case) == exp["cp2a_references"]["rows"]
    assert _ref_rows_upstream(cp4_refs, case) == exp["cp4_references"]["rows"]
    # carried verbatim: the bound upstream fact itself, never a rebuilt copy
    upstream = set(_upstream(case).values())
    for table in (cp1_refs, cp2g_refs, cp2a_refs, cp4_refs):
        for r in table.rows:
            assert r.fact in upstream, r.fact.fact_id


@pytest.mark.parametrize("case", CASES)
def test_claims(case: str) -> None:
    exp = EXPECTED["cases"][case]["claims"]
    result = _result(case)
    facts = _facts_by_id(result)
    assert [c.claim_id for c in result.claims] == [c["claim_id"] for c in exp]
    for got, want in zip(result.claims, exp, strict=True):
        assert got.text == _bind(want["text"], case), want["claim_id"]
        assert got.limitation == want["limitation"], want["claim_id"]
        assert want["citations"] == []
        assert list(got.references) == [_fig_id(n, case) for n in want["cp1_references"]]
        assert _render(got.text, facts) == want["text_rendered"], want["claim_id"]


@pytest.mark.parametrize("case", CASES)
def test_own_limitations(case: str) -> None:
    assert list(_result(case).own_limitations) == EXPECTED["cases"][case]["own_limitations"]


@pytest.mark.parametrize("case", CASES)
def test_cell_spelling_matches_fp05(case: str) -> None:
    """Every rendered T4E cell spelled by report_view.fact_spelling (G# bound at render time)."""
    blocks = EXPECTED["cases"][case]["FP05"]["blocks"]
    result = _result(case)
    by_id = {c.fact.fact_id: c.fact for c in result.cells}
    tables = {t.table_id: t for t in result.tables}
    for block in blocks.values():
        for tab in block["tabs"]:
            table = tables[tab["table_id"]]
            assert [r["row_id"] for r in tab["rows"]] == [r.row_id for r in table.rows]
            for row, trow in zip(tab["rows"], table.rows, strict=True):
                assert row["label"] == trow.label
                assert [c["fact_id"] for c in row["cells"]] == list(trow.fact_ids)
                for cell in row["cells"]:
                    fact = by_id[cell["fact_id"]]
                    _uc, state, text = fact_spelling(fact, "G1")
                    assert (state, text.replace("G1", "G#")) == (cell["state"], cell["shown"])
                    assert fact.field == cell["field"]


def _oracle_citations(case: str) -> dict[str, list[dict[str, str]]]:
    """The lineage rule applied to the oracle's own records: a quoted cell keeps its quote, a
    calculated cell takes the ordered, de-duplicated citations of what it derives from."""
    recs = {f["fact_id"]: f for f in EXPECTED["cases"][case]["facts"]}
    upstream = _upstream(case)
    memo: dict[str, list[dict[str, str]]] = {}

    def of(fid: str) -> list[dict[str, str]]:
        if fid in memo:
            return memo[fid]
        rec = recs[fid]
        out: list[dict[str, str]] = []
        if "citations" in rec:
            out = list(rec["citations"])
        elif rec.get("value_class") == "calculated":
            for dep in rec.get("derives_from", []):
                more = (
                    _cites(upstream[dep].citations)
                    if dep.startswith(UPSTREAM_PREFIXES)
                    else of(dep)
                )
                out += [c for c in more if c not in out]
        memo[fid] = out
        return out

    return {fid: of(fid) for fid in recs}


@pytest.mark.parametrize("case", CASES)
def test_lineage_citations(case: str) -> None:
    want = _oracle_citations(case)
    for cell in _result(case).cells:
        assert _cites(cell.fact.citations) == want[cell.fact.fact_id], cell.fact.fact_id
    # the stand-in CP-1 total debt citation reaches the secured claim's figures
    if case != "fixture_debt_missing":
        assert TOTAL_DEBT_CITATION in {c for x in _result(case).cells for c in x.fact.citations}


@pytest.mark.parametrize("case", CASES)
def test_known_fact_never_derives_from_unknown(case: str) -> None:
    cells = {c.fact.fact_id: c for c in _result(case).cells}
    upstream = _upstream(case)
    for cell in cells.values():
        if cell.fact.status != "known":
            continue
        for dep in cell.derives_from:
            fact = upstream[dep] if dep.startswith(UPSTREAM_PREFIXES) else cells[dep].fact
            assert fact.status == "known", (cell.fact.fact_id, dep)


@pytest.mark.parametrize("case", CASES)
def test_cells_are_valid_product_facts(case: str) -> None:
    result = _result(case)
    assert len({c.fact.fact_id for c in result.cells}) == len(result.cells)
    bound = prose.bind(_facts_by_id(result).values())
    names = (_pack(case).run.issuer_name,)
    for claim in result.claims:  # every claim resolves against the module's facts and references
        assert prose.issues(claim.text, bound, names=names) == (), claim.claim_id


def test_headline_values() -> None:
    """The lease's headline figures (positive case)."""
    cells = {c.fact.fact_id: c for c in _result("positive").cells}

    def shown(fid: str) -> str | None:
        return cells[fid].shown

    assert [shown(f"T4E.3.v0{n}.ev") for n in (1, 2, 3)] == ["123.60", "55.62", "37.08"]
    assert shown("T4E.5.v02c02.recovery") == "18.7%"
    assert cells["T4E.5.v02c02.recovery"].fact.amount == D(
        "0.18733333333333333333333333333333333333"
    )
    assert shown("T4E.5.v03c01.recovery") == "74.2%"
    assert [shown(f"T4E.7.v0{n}.value_break") for n in (1, 2, 3)] == [
        "Equity (every creditor class is paid in full)",
        "Trade payables and Other current liabilities",
        "Senior secured term loan",
    ]
    assert [shown(f"T4E.7.v0{n}.break_multiple") for n in (2, 3)] == ["4.31x", "2.70x"]
    for n in (1, 2, 3):
        assert cells[f"T4E.9.v0{n}.balance"].fact.amount == 0


def test_fixture_ev_zero_gives_known_zero_recoveries() -> None:
    """A known enterprise value of 0 gives known 0 recoveries (never missing, never invented)."""
    cells = {c.fact.fact_id: c.fact for c in _result("fixture_ev_zero").cells}
    for v in ("v02", "v03"):
        assert cells[f"T4E.3.{v}.ev"].amount == 0
        for k in ("c01", "c02", "c03"):
            recovery = cells[f"T4E.5.{v}{k}.recovery"]
            assert recovery.status == "known" and recovery.amount == 0


def test_missing_is_never_zero() -> None:
    """A missing input never becomes a known 0 anywhere downstream."""
    for case in ("gap", "fixture_ebitda_missing", "fixture_debt_missing"):
        exp = {f["fact_id"]: f for f in EXPECTED["cases"][case]["facts"]}
        for cell in _result(case).cells:
            if exp[cell.fact.fact_id]["status"] != "known":
                assert cell.fact.amount is None and cell.fact.text is None


# --- refusals (calculation level): shape alone, then content in the pinned order ----------------
REFUSALS = {r["id"]: r for r in SUBMISSIONS["refusals"]}
EXPECTED_REFUSALS = {r["id"]: r for r in EXPECTED["refusals"]}
STALE = {"v24": "CP-2A", "v25": "CP-2G", "v26": "CP-4", "v27": "CP-1"}
SHAPE_AND_CONTENT = [rid for rid in REFUSALS if rid not in STALE]


def _refusal_text(rid: str) -> str:
    r = REFUSALS[rid]
    if r.get("payload_text") is not None:
        return str(r["payload_text"])
    payload = r["payload"] if r.get("bind_placeholders") is False else _bind_all(r["payload"])
    return json.dumps(payload)


def _expected_issues(rid: str) -> list[str]:
    return [
        re.sub(r"\{\{FACT_ID:([a-z_0-9]+)\}\}", lambda m: _fig_id(m[1]), issue)
        for issue in EXPECTED_REFUSALS[rid]["expected_issues"]
    ]


@pytest.mark.parametrize("rid", SHAPE_AND_CONTENT)
def test_refusal(rid: str) -> None:
    against = REFUSALS[rid].get("against", "positive")
    assert against == EXPECTED_REFUSALS[rid].get("against", "positive")
    got = cp4c.payload_issues(_refusal_text(rid), _context(against))
    assert list(got) == _expected_issues(rid)
    assert EXPECTED_REFUSALS[rid]["issue_kind"] == ("shape" if rid.startswith("r") else "content")


@pytest.mark.parametrize("case", CASES)
def test_oracle_submissions_have_no_issue(case: str) -> None:
    assert cp4c.payload_issues(json.dumps(_bind_all(_payload(case), case)), _context(case)) == ()


def test_blocked_case_attempts() -> None:
    """The blocked case's two attempts give the pinned limitations (r01 rejected, v13 blocked)."""
    blocked = EXPECTED["cases"]["blocked"]
    for key in ("attempt_0", "attempt_1"):
        attempt = blocked[key]
        got = cp4c.payload_issues(_refusal_text(attempt["payload"]), _context("positive"))
        assert list(got) == attempt["limitations"]
    assert blocked["attempt_1"]["repair_issues"] == blocked["attempt_0"]["limitations"]


def test_invalid_submission_is_not_composed() -> None:
    sub = _submission(_bind_all(REFUSALS["v13"]["payload"]))
    with pytest.raises(ValueError, match="High is not allowed"):
        cp4c.compute(cp4c.Cp4cInputs(context=_context("positive"), submission=sub))


def _input(input_id: str, status: InputStatus = "restricted") -> Input:
    digest = hashlib.sha256(input_id.encode()).hexdigest()
    return Input(input_id=input_id, sha256=digest, status=status)


@pytest.mark.parametrize("rid", sorted(STALE))
def test_stale_input(rid: str) -> None:
    """Validator-only (v24-v27): the attempt's bound tuple against a current tuple in which only
    one upstream Input differs; the payload itself is the positive one and has no issue."""
    upstream_id = STALE[rid]
    bound = tuple(
        _input(i, "accepted" if i == "prepared-pack" else "restricted")
        for i in EXPECTED["execution"]["inputs"]
    )
    lit = REFUSALS[rid]["upstream_literal"]["current"][0]
    assert lit["input_id"] == upstream_id
    replaced = Input(input_id=lit["input_id"], sha256=lit["sha256"], status=lit["status"])
    current = tuple(replaced if i.input_id == upstream_id else i for i in bound)
    (issue,) = _expected_issues(rid)
    want = re.sub(
        r"<12 hex of [^>]*>", next(i.sha256[:12] for i in bound if i.input_id == upstream_id), issue
    )
    assert want.startswith(EXPECTED_REFUSALS[rid]["issue_prefix"])
    assert cp4c.stale_issues(bound=bound, current=current) == (want,)
    assert cp4c.stale_issues(bound=bound, current=bound) == ()
    assert cp4c.payload_issues(_refusal_text(rid), _context("positive")) == ()


@pytest.mark.parametrize("probe", EXPECTED["guard"]["probe"], ids=lambda p: p["sentence"][:30])
def test_guard_probe(probe: dict[str, Any]) -> None:
    assert list(cp4c.guard_issues("p", probe["sentence"])) == probe["issues"]


def test_guard_kinds_are_the_pinned_ones() -> None:
    guard = EXPECTED["guard"]
    assert list(cp4c.PRODUCT_GUARD_KINDS) == guard["product_kinds_checked"]
    assert {k: list(v) for k, v in cp4c.CORE_GUARD_PHRASES.items()} == guard["core_local_kinds"]
    # CP-4C owns recovery conclusions: the product's recovery-conclusion phrases pass
    assert cp4c.guard_issues("p", "The expected recovery is full; the notes would recover.") == ()
    # word-bounded, not substring (lease "Phrase guard")
    assert cp4c.guard_issues("p", "The recommendations of nobody.") == ()


# --- helpers for the round 8 states ---------------------------------------------------------------
def _ctx_with(case: str, **changes: Any) -> cp4c.Cp4cContext:
    return replace(_context(case), **changes)


def _compute_with(ctx: cp4c.Cp4cContext, payload: dict[str, Any]) -> cp4c.RestructuringResult:
    return cp4c.compute(cp4c.Cp4cInputs(context=ctx, submission=_submission(payload)))


def _payload_issues(
    payload: dict[str, Any], ctx: cp4c.Cp4cContext | None = None
) -> tuple[str, ...]:
    return cp4c.payload_issues(json.dumps(payload), ctx or _context("positive"))


def _records(result: cp4c.RestructuringResult) -> dict[str, dict[str, Any]]:
    return {c.fact.fact_id: _record(c) for c in result.cells}


def _oracle_records(case: str) -> dict[str, dict[str, Any]]:
    return {r["fact_id"]: r for r in EXPECTED["cases"][case]["facts"]}


def _refact(f: Fact, **changes: Any) -> Fact:
    return Fact.model_validate({**f.model_dump(), **changes})


def _with_cp1(ctx: cp4c.Cp4cContext, metric: str, **changes: Any) -> cp4c.Cp4cContext:
    t410 = tuple(_refact(f, **changes) if f.row_id == metric else f for f in ctx.cp1.t410)
    return replace(ctx, cp1=replace(ctx.cp1, t410=t410))


def _with_cp2g(ctx: cp4c.Cp4cContext, fact: Fact) -> cp4c.Cp4cContext:
    ebitda = tuple(
        replace(e, fact=fact) if e.fact.fact_id == fact.fact_id else e for e in ctx.cp2g.ebitda
    )
    return replace(ctx, cp2g=replace(ctx.cp2g, ebitda=ebitda))


def _zero_rank_payload() -> dict[str, Any]:
    """The positive payload plus a rank-3 class reading the statement's Unsecured debt row (0)."""
    payload: dict[str, Any] = _bind_all(_payload("positive"))
    zero = copy.deepcopy(payload["claims"][2])
    zero.update(class_id="c04", rank="3", name="Unsecured debt")
    zero["amount_quote"]["quote"] = _page_line("page:4", "Unsecured debt  ")
    payload["claims"].append(zero)
    for plan in payload["plan"]:
        plan["treatments"].insert(3, {"class_id": "c04", "treatment": "No recovery"})
    return payload


LTM = "LTM Q4 25: 2025-01-01 to 2025-12-31"
FACILITY = str(T418["facility_id"])


# --- round 8 A-2: the 13 states no frozen case pins (docs/rulings/2026-10-28-stage1.md) ----------
def test_a2_1_bound_cp3c_shows_its_input_status() -> None:
    ctx = _ctx_with("positive", cp3c_status="restricted")
    result = cp4c.compute(cp4c.Cp4cInputs(context=ctx, submission=_inputs("positive").submission))
    got, want = _records(result), _oracle_records("positive")
    assert want["T4E.1.u_cp3c.status"]["text"] == "not part of this run"
    assert got["T4E.1.u_cp3c.status"]["text"] == "restricted"
    assert {k for k in want if got[k] != want[k]} == {"T4E.1.u_cp3c.status"}
    assert list(result.own_limitations) == EXPECTED["cases"]["positive"]["own_limitations"]


def test_a2_2_term_loan_not_secured_senior_is_a_validator_issue() -> None:
    ctx = _context("positive")
    issue = (
        f"claims[0].kind: CP-1 T4.18 does not show {FACILITY} SECURED and SENIOR, so no class can "
        "be secured_debt"
    )
    variants = (
        replace(ctx.cp1, secured_status=_refact(ctx.cp1.secured_status, text="UNSECURED")),
        replace(ctx.cp1, seniority=_refact(ctx.cp1.seniority, text="SUBORDINATED")),
        replace(
            ctx.cp1,
            secured_status=_refact(
                ctx.cp1.secured_status, status="missing", text=None, limitation="Not stated"
            ),
        ),
    )
    payload = _bind_all(_payload("positive"))
    for cp1 in variants:
        assert _payload_issues(payload, replace(ctx, cp1=cp1)) == (issue,)
    # after the v02 kind/source check of the same class
    payload["claims"][0]["amount_source"] = "not_stated"
    v02 = next(r for r in EXPECTED["refusals"] if r["id"] == "v02")["expected_issues"][0]
    assert _payload_issues(payload, replace(ctx, cp1=variants[0])) == (v02, issue)


def test_a2_3_other_period_column_is_a_validator_issue() -> None:
    payload = _bind_all(_payload("positive"))
    payload["claims"][1]["period_column"] = "Q3 2025-09-30"
    assert _payload_issues(payload) == (
        "claims[1].period_column: claims are the 31 December 2025 balances; use Q4 2025-12-31",
    )
    payload["claims"][1]["period_column"] = "Q5 2026-03-31"  # the v05 check comes first
    assert _payload_issues(payload) == (
        "claims[1].period_column: not a column of the quoted statement: Q5 2026-03-31",
    )


def test_a2_4_other_cp4_rating_or_conditions_stays_fail_closed() -> None:
    ctx = _context("positive")
    for fid, text in (
        ("T4.13.rating.rating", "Moderate"),
        ("T4.10.r02.conditions", "Consent of the majority lenders"),
    ):
        facts = tuple(_refact(f, text=text) if f.fact_id == fid else f for f in ctx.cp4.facts)
        bad = replace(ctx, cp4=replace(ctx.cp4, facts=facts))
        with pytest.raises(ValueError, match=r"round 8 A-2 #4") as raised:
            cp4c.compute(cp4c.Cp4cInputs(context=bad, submission=_inputs("positive").submission))
        assert "LEAD to" not in str(raised.value)


CP1_EBITDA_MISSING = f"Not calculable: EBITDA is missing in CP-1 for {LTM}"
CP1_EBITDA_NOT_POSITIVE = (
    f"Not calculable: EBITDA is zero or negative in CP-1 for {LTM} (ZERO_OR_NEGATIVE_DENOMINATOR)"
)


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        (
            {"status": "missing", "amount": None, "calculation_id": None, "limitation": "Gone"},
            CP1_EBITDA_MISSING,
        ),
        (  # round 11 B6: an unknown CP-1 EBITDA names its state
            {"status": "conflicting", "amount": None, "calculation_id": None, "limitation": "Two"},
            f"Not calculable: EBITDA is conflicting in CP-1 for {LTM}",
        ),
        (
            {
                "status": "not_applicable",
                "amount": None,
                "calculation_id": None,
                "limitation": "NA",
            },
            f"Not calculable: EBITDA is not applicable in CP-1 for {LTM}",
        ),
        ({"amount": D(0)}, CP1_EBITDA_NOT_POSITIVE),
        ({"amount": D(-3)}, CP1_EBITDA_NOT_POSITIVE),
    ],
    ids=["missing", "conflicting", "not_applicable", "zero", "negative"],
)
def test_a2_5_cp1_ebitda_not_a_known_positive(changes: dict[str, Any], reason: str) -> None:
    ctx = _with_cp1(_context("positive"), "ebitda", **changes)
    result = cp4c.compute(cp4c.Cp4cInputs(context=ctx, submission=_inputs("positive").submission))
    got, want = _records(result), _oracle_records("positive")
    implied = {f"T4E.3.v0{n}.implied_ltm_multiple" for n in (1, 2, 3)}
    for fid in implied:
        assert (got[fid]["status"], got[fid]["limitation"]) == ("missing", reason)
        assert got[fid]["period"] == want[fid]["period"] == LTM
    assert {k for k in want if got[k] != want[k]} == implied
    assert list(result.own_limitations) == EXPECTED["cases"]["positive"]["own_limitations"]


def test_a2_6_conflicting_total_debt_is_a_missing_claim() -> None:
    case = "fixture_debt_missing"
    base = _context(case)
    debt = next(f for f in base.cp1.t410 if f.row_id == "total_debt")
    assert debt.status == "missing"
    ctx = _with_cp1(base, "total_debt", status="conflicting")
    result = cp4c.compute(cp4c.Cp4cInputs(context=ctx, submission=_inputs(case).submission))
    old = f"total debt is missing in CP-1 for {LTM}"
    new = f"total debt is conflicting in CP-1 for {LTM}"
    exp = EXPECTED["cases"][case]
    assert any(old in line for line in exp["own_limitations"])
    want_facts = json.loads(json.dumps(exp["facts"]).replace(old, new))
    assert [_record(c) for c in result.cells] == want_facts
    assert list(result.own_limitations) == json.loads(
        json.dumps(exp["own_limitations"]).replace(old, new)
    )
    ref = result.references[0].rows[0].fact  # the copy keeps CP-1's state verbatim (6g)
    assert (ref.status, ref.limitation) == ("conflicting", debt.limitation)


def test_a2_6_total_debt_of_another_period_stays_an_invariant() -> None:
    ctx = _context("positive")
    with pytest.raises(ValueError, match="not for LTM"):
        cp4c.select_cp1(_with_cp1(ctx, "total_debt", period="FY 2025").cp1.t410)


def test_a2_7_negative_cp2g_ebitda_makes_the_enterprise_value_missing() -> None:
    case = "fixture_ebitda_missing"
    base = _context(case)
    gone = next(e.fact for e in base.cp2g.ebitda if e.fact.status == "missing")
    recs = {f["fact_id"]: f for f in CP2G_EXP["cases"]["gap"]["facts"]}
    ctx = _with_cp2g(base, _fact(recs[gone.fact_id], amount=D(-5)))
    result = cp4c.compute(cp4c.Cp4cInputs(context=ctx, submission=_inputs(case).submission))
    got = _records(result)
    reason = "Not calculable: downside FY2026 EBITDA is negative in CP-2G"
    for v in ("v02", "v03"):
        assert got[f"T4E.3.{v}.ebitda"]["amount_exact"] == "-5"
        assert (got[f"T4E.3.{v}.ev"]["status"], got[f"T4E.3.{v}.ev"]["limitation"]) == (
            "missing",
            reason,
        )
        for c in ("c01", "c02", "c03"):
            assert got[f"T4E.5.{v}{c}.recovery"]["limitation"] == reason
    old = str(gone.limitation).removeprefix("Not calculable: ")
    assert old.startswith("downside FY2026 EBITDA is missing in CP-2G")
    exp = EXPECTED["cases"][case]["own_limitations"]
    assert list(result.own_limitations) == [
        line.replace(old, "downside FY2026 EBITDA is negative in CP-2G") for line in exp
    ]


def test_a2_7_claim_not_above_zero_is_a_validator_issue() -> None:
    assert _payload_issues(_zero_rank_payload()) == (
        "claims[3]: a claim class needs a claim above zero; Unsecured debt reads 0",
    )
    payload = _bind_all(_payload("positive"))
    ctx = _with_cp1(_context("positive"), "total_debt", amount=D(0))
    name = payload["claims"][0]["name"]
    assert _payload_issues(payload, ctx) == (
        f"claims[0]: a claim class needs a claim above zero; {name} reads 0",
    )


def test_a2_9_blank_or_multiline_names_are_text_issues() -> None:
    payload = _bind_all(_payload("positive"))
    payload["claims"][1]["name"] = "  "
    payload["valuation"][0]["label"] = "Base\ncase"
    payload["assessment"]["confidence"] = "High"
    high = next(r for r in EXPECTED["refusals"] if r["id"] == "v13")["expected_issues"][0]
    assert _payload_issues(payload) == (
        high,
        "claims[1].name: empty text",
        "valuation[0].label: one line only",
    )


def test_a2_11_quoted_row_without_a_number_is_a_validator_issue() -> None:
    payload = _bind_all(_payload("positive"))
    payload["claims"][1]["amount_quote"]["quote"] = "Period end  Opening 2024-12-31"
    assert _payload_issues(payload) == (
        "claims[1].amount_quote: the quoted row has no number under Q4 2025-12-31",
    )


def test_a2_13_more_than_38_digits_is_a_value_error_naming_the_operation() -> None:
    for claims, ev, operation in (
        (((1, "1E+37"), (1, "0.1")), "1", "the claims of rank 1"),
        (((1, "1E+37"), (2, "0.1")), "1", "the claims through rank 2"),
        (((1, "0.1"),), "1E+38", "the value left after rank 1"),
    ):
        with pytest.raises(ValueError, match=f"{operation}: the exact value needs more than 38"):
            _w(*claims, ev=ev)
    ctx = _context("positive")
    b26 = next(e.fact for e in ctx.cp2g.ebitda if e.fact.fact_id == "T2H.4.b26.ebitda")
    wide = _with_cp2g(ctx, _refact(b26, amount=D("3." + "3" * 37)))
    with pytest.raises(
        ValueError, match="the enterprise value of v01: the exact value needs more than 38"
    ):
        _payload_issues(_bind_all(_payload("positive")), wide)


def test_lender_protection_other_than_insufficient_fails_closed() -> None:
    ctx = _context("positive")
    facts = tuple(
        f.model_copy(update={"text": "Moderate"}) if f.fact_id == "T4.13.rating.rating" else f
        for f in ctx.cp4.facts
    )
    bad = _ctx_with("positive", cp4=replace(ctx.cp4, facts=facts))
    with pytest.raises(ValueError, match="Insufficient Information"):
        cp4c.compute(cp4c.Cp4cInputs(context=bad, submission=_inputs("positive").submission))


def test_cp1_selection_needs_exactly_one_fact() -> None:
    ctx = _context("positive")
    with pytest.raises(ValueError, match="exactly one"):
        cp4c.select_cp1(ctx.cp1.t410[1:])
    dup = ctx.cp1.t410[0].model_copy(update={"fact_id": "interface-fact:dup"})
    with pytest.raises(ValueError, match="exactly one"):
        cp4c.select_cp1((*ctx.cp1.t410, dup))


def test_negative_enterprise_value_stays_an_invariant() -> None:
    with pytest.raises(ValueError, match="negative"):
        cp4c.waterfall(
            classes=(cp4c.ClassClaim("c01", "Loan", 1, cp4c.Val(D(10))),),
            enterprise_value=cp4c.Val(D(-1)),
        )


# --- round 8 A-4: unknown upstream copies keep their status, conflicting included ----------------
def test_a4_conflicting_copies_keep_their_status() -> None:
    case = "fixture_ebitda_missing"
    base = _context(case)
    gone = next(e.fact for e in base.cp2g.ebitda if e.fact.status == "missing")
    ctx = _with_cp2g(base, _refact(gone, status="conflicting"))
    result = cp4c.compute(cp4c.Cp4cInputs(context=ctx, submission=_inputs(case).submission))
    got, want = _records(result), _oracle_records(case)
    copies = {f"T4E.3.{v}.ebitda" for v in ("v02", "v03")}  # the downside FY2026 copies
    for fid in copies:
        assert want[fid]["status"] == "missing"
        assert got[fid] == dict(want[fid], status="conflicting")
    assert {k for k in want if got[k] != want[k]} == copies
    assert list(result.own_limitations) == EXPECTED["cases"][case]["own_limitations"]


# --- round 8 A-1: exact largest-remainder allocation ----------------------------------------------
def _w(*claims: tuple[int, str], ev: str) -> cp4c.Waterfall:
    classes = tuple(
        cp4c.ClassClaim(f"c{i:02d}", f"Class {i}", rank, cp4c.Val(D(amount)))
        for i, (rank, amount) in enumerate(claims, 1)
    )
    return cp4c.waterfall(classes=classes, enterprise_value=cp4c.Val(D(ev)))


def _shares(w: cp4c.Waterfall, *ids: str) -> list[str]:
    return [str(w.classes[i].distribution.amount) for i in ids]


BIG = "9999999999999999999999999999999999999.9"
SMALL = "5000000000000000000000000000000000000.1"


def test_a1_worked_example_three_equal_classes_share_100() -> None:
    w = _w((1, "50"), (2, "50"), (2, "50"), (2, "50"), ev="150")
    floor = "33." + "3" * 35
    assert _shares(w, "c02", "c03", "c04") == [floor, floor, "33." + "3" * 34 + "4"]
    assert sum(Fraction(s) for s in _shares(w, "c01", "c02", "c03", "c04")) == 150
    assert w.residual.amount == 0


def test_a1_leftover_unit_goes_to_the_largest_remainder() -> None:
    w = _w((1, "10"), (1, "20"), ev="10")
    assert _shares(w, "c01", "c02") == ["3." + "3" * 36, "6." + "6" * 35 + "7"]


def test_a1_fully_paid_rank_pays_each_claim_exactly() -> None:
    w = _w((1, BIG), (1, SMALL), ev="2E+37")
    assert _shares(w, "c01", "c02") == [BIG, SMALL]
    assert w.classes["c01"].recovery.amount == 1


def test_a1_unpaid_rank_pays_zero() -> None:
    w = _w((1, "1E-40"), ev="0")  # a claim finer than any 38-digit quantum of a payment
    a = w.classes["c01"]
    assert a.distribution.amount == 0 and a.recovery.amount == 0


def test_a1_state_14_claim_not_a_multiple_of_the_rank_quantum() -> None:
    with pytest.raises(ValueError, match="state 14"):
        _w((1, "1"), (2, BIG), (2, SMALL), ev="12000000000000000000000000000000000001")


def test_a1_exact_sum_is_never_rounded() -> None:
    thirds = "0." + "3" * 37
    assert cp4c._exact_sum([D("1E+10"), D(thirds)]) == D("10000000000." + "3" * 37)
    wide = cp4c._exact_sum([D("9E+50"), D("1E+50"), D("1E-40")])  # 92 digits, past the floor
    assert Fraction(wide) == 10**51 + Fraction(1, 10**40)


def test_a1_t4e9_balances_exactly_with_three_equal_classes() -> None:
    """Three equal classes share 5.62 in v02: two floors and the tie unit to the last class; the
    distributions plus the residual are the enterprise value exactly (T4E.9 balance 0)."""
    payload = _bind_all(_payload("positive"))
    other = payload["claims"][2]  # other current liabilities, 10 at rank 2
    payload["claims"][1:] = [dict(copy.deepcopy(other), class_id=c) for c in ("c02", "c03", "c04")]
    for plan in payload["plan"]:
        treatment = plan["treatments"][2]["treatment"]
        plan["treatments"].insert(3, {"class_id": "c04", "treatment": treatment})
    payload["fulcrum"][1]["class_ids"] = ["c02", "c03", "c04"]
    assert _payload_issues(payload) == ()
    cells = {c.fact.fact_id: c.fact for c in _compute_with(_context("positive"), payload).cells}

    def x(fid: str) -> Fraction:
        amount = cells[fid].amount
        assert amount is not None, fid
        return Fraction(amount)

    shares = [x(f"T4E.4.v02{c}.distribution") for c in ("c02", "c03", "c04")]
    assert x("T4E.4.v02c02.value_available") == Fraction("5.62") == sum(shares)
    assert shares[0] == shares[1] == shares[2] - Fraction(1, 10**37)
    assert cells["T4E.9.v02.balance"].status == "known" and x("T4E.9.v02.balance") == 0
    for v in ("v01", "v02", "v03"):
        paid, residual = x(f"T4E.9.{v}.creditor_distributions"), x(f"T4E.9.{v}.equity_residual")
        assert paid + residual == x(f"T4E.9.{v}.ev")


# --- property tests (expected.json property_tests; round 8 A-1) -----------------------------------
_amount = st.integers(1, 10**6).map(lambda n: D(n).scaleb(-2))
_classes = st.lists(st.tuples(st.integers(1, 4), _amount), min_size=1, max_size=6).map(
    lambda xs: tuple(
        cp4c.ClassClaim(f"c{i + 1:02d}", f"Class {i + 1}", r, cp4c.Val(a))
        for i, (r, a) in enumerate(xs)
    )
)
_ev = st.integers(0, 10**7).map(lambda n: D(n).scaleb(-2))


def _f(v: cp4c.Val) -> Fraction:
    assert v.amount is not None
    return Fraction(v.amount)


def _round38(x: Fraction) -> Decimal:
    from decimal import ROUND_HALF_EVEN, Context

    return Context(prec=38, rounding=ROUND_HALF_EVEN).divide(D(x.numerator), D(x.denominator))


_fine = st.one_of(
    _amount,
    st.integers(1, 10**12).map(lambda n: D(n).scaleb(-7)),
    st.sampled_from([D(10), D(50), D("33.3")]),  # ties
)
_mixed = st.lists(st.tuples(st.integers(1, 3), _fine), min_size=1, max_size=6).map(
    lambda xs: tuple(
        cp4c.ClassClaim(f"c{i + 1:02d}", f"Class {i + 1}", r, cp4c.Val(a))
        for i, (r, a) in enumerate(xs)
    )
)
_mixed_ev = st.one_of(_ev, st.integers(0, 10**13).map(lambda n: D(n).scaleb(-7)))


@settings(max_examples=400, deadline=None)
@given(classes=_mixed, ev=_mixed_ev)
def test_property_conservation(classes: tuple[cp4c.ClassClaim, ...], ev: Decimal) -> None:
    """Round 8 A-1: each rank's shares sum to `paid` exactly; a partly paid rank floors each exact
    share to its quantum q = 10^(paid.adjusted() - 37) and hands the leftover units to the
    largest remainders (ties to the later class), so each share is within q of its exact value,
    never negative and never above its claim; a fully or un-paid rank pays the exact share. The
    distributions plus the residual are the enterprise value exactly."""
    w = cp4c.waterfall(classes=classes, enterprise_value=cp4c.Val(ev))
    total = Fraction(0)
    for rank in sorted({c.rank for c in classes}):
        members = [c for c in classes if c.rank == rank]
        first = w.classes[members[0].class_id]
        assert first.available.amount is not None and first.group.amount is not None
        paid_d = min(first.available.amount, first.group.amount)
        group, paid = _f(first.group), Fraction(paid_d)
        shares = [_f(w.classes[c.class_id].distribution) for c in members]
        exact = [_f(c.claim) * paid / group for c in members]
        assert sum(shares) == paid
        for c, share in zip(members, shares, strict=True):
            a = w.classes[c.class_id]
            assert 0 <= share <= _f(c.claim)
            assert _f(a.recovery) == Fraction(_round38(paid / group))
            assert a.shortfall.amount == _round38(_f(c.claim) - share)
        if 0 < paid < group:
            q = Fraction(10) ** (paid_d.adjusted() - 37)
            floors = [(e // q) * q for e in exact]
            assert all(s in (f, f + q) for s, f in zip(shares, floors, strict=True))
            assert all(abs(s - e) < q for s, e in zip(shares, exact, strict=True))
            ups = [i for i, (s, f) in enumerate(zip(shares, floors, strict=True)) if s != f]
            assert len(ups) == (paid - sum(floors)) / q
            order = sorted(
                range(len(members)), key=lambda i: (exact[i] - floors[i], i), reverse=True
            )
            assert sorted(ups) == sorted(order[: len(ups)])
        else:
            assert shares == exact
        total += paid
    assert total + _f(w.residual) == Fraction(ev)


@settings(max_examples=200, deadline=None)
@given(classes=_classes, ev=_ev, more=_ev)
def test_property_priority(
    classes: tuple[cp4c.ClassClaim, ...], ev: Decimal, more: Decimal
) -> None:
    w = cp4c.waterfall(classes=classes, enterprise_value=cp4c.Val(ev))
    w2 = cp4c.waterfall(classes=classes, enterprise_value=cp4c.Val(ev + more))
    for c in classes:
        a = w.classes[c.class_id]
        if _f(a.distribution) > 0:
            for b in classes:
                if b.rank < c.rank:
                    assert _f(w.classes[b.class_id].shortfall) == 0, (b, c)
        assert _f(w2.classes[c.class_id].recovery) >= _f(a.recovery)


@settings(max_examples=200, deadline=None)
@given(classes=_classes, ev=_ev)
def test_property_pari_passu(classes: tuple[cp4c.ClassClaim, ...], ev: Decimal) -> None:
    w = cp4c.waterfall(classes=classes, enterprise_value=cp4c.Val(ev))
    for c in classes:
        for b in classes:
            if b.rank == c.rank:
                assert w.classes[b.class_id].recovery == w.classes[c.class_id].recovery


def _break_rank(w: cp4c.Waterfall, classes: tuple[cp4c.ClassClaim, ...]) -> int:
    assert w.value_break is not None
    if w.value_break == ("equity",):
        return 10
    ranks = {c.class_id: c.rank for c in classes}
    (rank,) = {ranks[i] for i in w.value_break}
    return rank


@settings(max_examples=200, deadline=None)
@given(classes=_classes, ebitda=_amount, m1=st.integers(0, 2000), m2=st.integers(0, 2000))
def test_property_break_monotone(
    classes: tuple[cp4c.ClassClaim, ...], ebitda: Decimal, m1: int, m2: int
) -> None:
    lo, hi = sorted((D(m1).scaleb(-2), D(m2).scaleb(-2)))
    a = cp4c.waterfall(classes=classes, enterprise_value=cp4c.Val(ebitda * lo))
    b = cp4c.waterfall(classes=classes, enterprise_value=cp4c.Val(ebitda * hi))
    assert _break_rank(b, classes) >= _break_rank(a, classes)


@settings(max_examples=200, deadline=None)
@given(classes=_classes, ev=_ev, drop=st.integers(0, 5), ev_missing=st.booleans())
def test_property_missing_never_zero(
    classes: tuple[cp4c.ClassClaim, ...], ev: Decimal, drop: int, ev_missing: bool
) -> None:
    gone = classes[drop % len(classes)]
    cut = tuple(
        replace(c, claim=cp4c.Val(None, "Not calculable: claim removed")) if c is gone else c
        for c in classes
    )
    value = cp4c.Val(None, "Not calculable: multiple removed") if ev_missing else cp4c.Val(ev)
    w = cp4c.waterfall(classes=cut, enterprise_value=value)
    if ev_missing:
        assert w.value_break is None and w.break_reason
    for c in cut:
        a = w.classes[c.class_id]
        if ev_missing or c.rank >= gone.rank:
            for v in (a.distribution, a.recovery, a.shortfall):
                assert v.amount is None and v.reason
    assert w.residual.amount is None


# --- fix round 1 (review-adversary.md; questions.md Q1-Q4) ----------------------------------------
NO_NUMBER = "claims[2].amount_quote: the quoted row has no number under Q4 2025-12-31"


def _with_page4(ctx: cp4c.Cp4cContext, extra: str) -> cp4c.Cp4cContext:
    """The context with lines appended to the financial page:4 statement."""
    fin = next(s for s in ctx.pack.sources if s.source_id == "financial")
    spans = tuple(
        sp.model_copy(update={"text": sp.text + "\n" + extra}) if sp.locator == "page:4" else sp
        for sp in fin.spans
    )
    sources = tuple(
        fin.model_copy(update={"spans": spans}) if s.source_id == "financial" else s
        for s in ctx.pack.sources
    )
    return replace(ctx, pack=ctx.pack.model_copy(update={"sources": sources}))


def _quoting(quote: str) -> dict[str, Any]:
    payload: dict[str, Any] = _bind_all(_payload("positive"))
    payload["claims"][2]["amount_quote"]["quote"] = quote
    return payload


def test_m1_source_row_reads_the_cited_line_not_the_first_label_match() -> None:
    ctx = _with_page4(_context("positive"), "Other  1  1  1  1  5  5\nOther  9  9  9  9  9  9")
    payload = _quoting("Other  9  9  9  9  9  9")
    assert _payload_issues(payload, ctx) == ()
    cells = {c.fact.fact_id: c.fact for c in _compute_with(ctx, payload).cells}
    claim = cells["T4E.2.c03.claim"]
    assert claim.amount == 9 and claim.citations[0].quote == "Other  9  9  9  9  9  9"


def test_m1_a_quote_no_line_starts_with_is_refused() -> None:
    ctx = _with_page4(
        _context("positive"), "Provisions  1  2  3  4  5  6\nOther Provisions  7  8  9  10  11  12"
    )
    assert _payload_issues(_quoting("Provisions  7  8  9  10  11  12"), ctx) == (NO_NUMBER,)


def test_m1_a_line_holding_the_quote_mid_line_is_not_a_cited_row() -> None:
    row = "Deferred items  1  1  1  1  5.00  1"
    ctx = _with_page4(_context("positive"), row + "\nOther " + row)
    payload = _quoting(row)
    assert _payload_issues(payload, ctx) == ()
    cells = {c.fact.fact_id: c.fact for c in _compute_with(ctx, payload).cells}
    assert cells["T4E.2.c03.claim"].amount == 5


def test_m1_a_quote_starting_two_different_lines_is_refused() -> None:
    ctx = _with_page4(_context("positive"), "Other  9  1  1  1  1  1\nOther  9  2  2  2  2  2")
    assert _payload_issues(_quoting("Other  9"), ctx) == (NO_NUMBER,)


def test_l1_a_row_whose_cells_do_not_match_the_header_has_no_number() -> None:
    row = "Deferred items  1  1    1  5.00  7.00"
    assert _payload_issues(_quoting(row), _with_page4(_context("positive"), row)) == (NO_NUMBER,)


@pytest.mark.parametrize(
    "cell", ["(5.00)", "−5.00", "1,234.00", "1E+1", "1_000", "٥", "Infinity", "NaN", "5."]
)
def test_q4_a_cell_outside_the_ascii_grammar_has_no_number(cell: str) -> None:
    row = f"Deferred items  1  1  1  1  {cell}  1"
    assert _payload_issues(_quoting(row), _with_page4(_context("positive"), row)) == (NO_NUMBER,)


def test_q4_a_signed_ascii_cell_is_read() -> None:
    row = "Deferred items  1  1  1  1  -5.00  1"
    assert _payload_issues(_quoting(row), _with_page4(_context("positive"), row)) == (
        "claims[2]: a claim class needs a claim above zero; Other current liabilities reads -5",
    )


def test_l2_known_cp1_ebitda_without_an_amount_is_an_invariant() -> None:
    ctx = _with_cp1(
        _context("positive"), "ebitda", amount=None, text="see note 7", calculation_id=None
    )
    with pytest.raises(ValueError, match="invariant"):
        _compute_with(ctx, _bind_all(_payload("positive")))


def test_l3_state_14_on_a_payment_over_38_digits() -> None:
    with pytest.raises(ValueError, match="state 14"):
        _w((1, "10"), (1, "20"), ev="1.0000000000000000000000000000000000000001")


def test_l4_claims_through_carry_the_first_missing_rank() -> None:
    v = cp4c.Val
    classes = (
        cp4c.ClassClaim("c01", "a", 1, v(D(10))),
        cp4c.ClassClaim("c02", "b", 2, v(None, "Not calculable: r2")),
        cp4c.ClassClaim("c03", "c", 3, v(None, "Not calculable: r3")),
    )
    w = cp4c.waterfall(classes=classes, enterprise_value=v(D(5)))
    assert w.classes["c03"].through.reason == "Not calculable: r2"


def test_l4_a_rank_carries_its_first_missing_claim() -> None:
    v = cp4c.Val
    classes = (
        cp4c.ClassClaim("c01", "a", 1, v(D(10))),
        cp4c.ClassClaim("c02", "b", 2, v(None, "Not calculable: a")),
        cp4c.ClassClaim("c03", "c", 2, v(None, "Not calculable: b")),
    )
    w = cp4c.waterfall(classes=classes, enterprise_value=v(D(50)))
    assert w.classes["c03"].distribution.reason == "Not calculable: a"


def test_l4_a_zero_rank_total_or_negative_claim_is_an_invariant() -> None:
    with pytest.raises(ValueError, match="invariant broken"):
        _w((1, "0"), ev="5")
    with pytest.raises(ValueError, match="negative; invariant broken"):
        _w((1, "10"), (1, "-3"), ev="5")


def test_l4_partial_equity_for_a_zero_recovery_does_not_fit() -> None:
    payload = _bind_all(_payload("positive"))
    payload["plan"][2]["treatments"][1]["treatment"] = "Receives reorganised equity"
    assert _payload_issues(payload) == (
        (
            "plan[2].treatments[1]: Receives reorganised equity does not fit the waterfall result of "
            "c02 in v03"
        ),
    )


def test_l4_cp2g_ebitda_of_another_period_is_an_invariant() -> None:
    ctx = _context("positive")
    b26 = next(e.fact for e in ctx.cp2g.ebitda if e.fact.fact_id == "T2H.4.b26.ebitda")
    bad = _with_cp2g(ctx, _refact(b26, period="FY2027: 2027-01-01 to 2027-12-31"))
    with pytest.raises(ValueError, match="is not T2H.4.b26.ebitda of FY2026"):
        _compute_with(bad, _bind_all(_payload("positive")))


def test_l4_a_downside_year_on_another_cp2a_scenario_is_an_invariant() -> None:
    ctx = _context("positive")
    payload = _bind_all(_payload("positive"))
    payload["valuation"][2]["ebitda_year"] = "FY2027"
    d27 = next(e for e in ctx.cp2g.ebitda if e.fact.fact_id == "T2H.4.d27.ebitda")
    other = replace(
        d27,
        derives_from=tuple(
            x.replace("T2B.1.", "T2B.1.zz", 1) if x.startswith("cp2a:T2B.1.") else x
            for x in d27.derives_from
        ),
    )
    ebitda = tuple(other if e is d27 else e for e in ctx.cp2g.ebitda)
    bad = replace(ctx, cp2g=replace(ctx.cp2g, ebitda=ebitda))
    with pytest.raises(ValueError, match="applies another CP-2A scenario"):
        if not _payload_issues(payload, bad):
            _compute_with(bad, payload)


# --- round 11 (docs/rulings/2026-10-28-stage1.md B2, B3, B6; questions.md Q5-Q7) -------------------
def test_b2_not_applicable_total_debt_is_a_missing_claim() -> None:
    case = "fixture_debt_missing"
    base = _context(case)
    debt = next(f for f in base.cp1.t410 if f.row_id == "total_debt")
    ctx = _with_cp1(base, "total_debt", status="not_applicable")
    result = cp4c.compute(cp4c.Cp4cInputs(context=ctx, submission=_inputs(case).submission))
    old = f"total debt is missing in CP-1 for {LTM}"
    new = f"total debt is not applicable in CP-1 for {LTM}"
    exp = EXPECTED["cases"][case]
    want_facts = json.loads(json.dumps(exp["facts"]).replace(old, new))
    assert [_record(c) for c in result.cells] == want_facts
    assert list(result.own_limitations) == json.loads(
        json.dumps(exp["own_limitations"]).replace(old, new)
    )
    ref = result.references[0].rows[0].fact  # the copy keeps CP-1's state verbatim
    assert (ref.status, ref.limitation) == ("not_applicable", debt.limitation)


def test_b3_a_name_or_label_with_a_figure_is_a_bare_figure_issue() -> None:
    payload = _bind_all(_payload("positive"))
    payload["claims"][1]["name"] = "Class 2"
    payload["valuation"][0]["label"] = "Base FY2026"  # the claims spell it lower-case
    assert _payload_issues(payload) == (
        "claims[1].name: Bare figure: 2",
        "valuation[0].label: Bare figure: fy2026",
    )


def test_b3_a_name_the_validator_accepts_composes() -> None:
    payload = _bind_all(_payload("positive"))
    payload["claims"][1]["name"] = "Tranche B 2027"
    assert _payload_issues(payload) == ()
    claims = _compute_with(_context("positive"), payload).claims
    assert any("Tranche B 2027" in c.text for c in claims)


def test_b3_the_issuer_name_is_spared_in_a_class_name() -> None:
    """B3 reads names with the same `names` compute uses: the issuer's own digit is no bare
    figure, and the class name composes."""
    base = _context("positive")
    run = base.pack.run.model_copy(update={"issuer_name": "Northbridge 2 Holdings"})
    ctx = replace(base, pack=base.pack.model_copy(update={"run": run}))
    payload = _bind_all(_payload("positive"))
    payload["claims"][1]["name"] = "Northbridge 2 Holdings Notes"
    assert _payload_issues(payload, ctx) == ()
    assert _payload_issues(payload) == ("claims[1].name: Bare figure: 2",)  # another issuer
    claims = _compute_with(ctx, payload).claims
    assert any("Northbridge 2 Holdings Notes" in c.text for c in claims)


@pytest.mark.parametrize("name", ["Term Loan B-2", "Q1 Notes"])
def test_b3_a_class_name_is_read_as_spelt(name: str) -> None:
    """Class names keep their case in the claims, so B3 reads them as typed (only a valuation
    label is lower-cased): these pass, and compose."""
    payload = _bind_all(_payload("positive"))
    payload["claims"][1]["name"] = name
    assert _payload_issues(payload) == ()
    claims = _compute_with(_context("positive"), payload).claims
    assert any(name in c.text for c in claims)


def test_b2_a_known_total_debt_without_an_amount_still_raises() -> None:
    ctx = _with_cp1(
        _context("positive"), "total_debt", status="known", amount=None, text="n/a", unit=None
    )
    with pytest.raises(ValueError, match="CP-1 total debt .* is known without an amount"):
        _compute_with(ctx, _bind_all(_payload("positive")))


def test_b6_ev_reason_comes_first_when_both_operands_are_unknown() -> None:
    """Gap v03 has no EV; with CP-1 EBITDA missing too, the implied multiple takes EV's reason."""
    changes = {"status": "missing", "amount": None, "calculation_id": None, "limitation": "Gone"}
    ctx = _with_cp1(_context("gap"), "ebitda", **changes)
    got = _records(cp4c.compute(cp4c.Cp4cInputs(context=ctx, submission=_inputs("gap").submission)))
    ev_reason = "Not calculable: the EV multiple was not assessed"
    assert (got["T4E.3.v03.ev"]["status"], got["T4E.3.v03.ev"]["limitation"]) == (
        "missing",
        ev_reason,
    )
    implied = got["T4E.3.v03.implied_ltm_multiple"]
    assert (implied["status"], implied["limitation"]) == ("missing", ev_reason)
    assert got["T4E.3.v01.implied_ltm_multiple"]["limitation"] == CP1_EBITDA_MISSING


def test_q6_a_quote_must_cover_whole_cells() -> None:
    assert _payload_issues(_quoting("Pr")) == (NO_NUMBER,)
    cut = "Other current liabilities  10  10  10  10  1"  # cuts the last figure
    assert _payload_issues(_quoting(cut)) == (NO_NUMBER,)
    assert _payload_issues(_quoting("Other current liabilities  10  10")) == ()


@pytest.mark.parametrize("tail", ["\r", " "], ids=["bare CR", "U+2028"])
def test_q7_the_cited_line_is_one_physical_line(tail: str) -> None:
    row = "Deferred items  1  1  1  1  5.00  1"
    ctx = _with_page4(_context("positive"), row + tail + "x")
    assert _payload_issues(_quoting(row), ctx) == (NO_NUMBER,)
    # the break past the quoted cells: whole cells hold (Q6), the line is still not one line
    assert _payload_issues(_quoting("Deferred items  1  1  1  1  5.00"), ctx) == (NO_NUMBER,)


def test_q7_a_trailing_cr_is_stripped() -> None:
    row = "Deferred items  1  1  1  1  5.00  1"
    assert _payload_issues(_quoting(row), _with_page4(_context("positive"), row + "\r")) == ()


def test_n1_a_row_longer_than_the_header_has_no_number() -> None:
    row = "Deferred  items  1  2  3  4  5.00  6"
    assert _payload_issues(_quoting(row), _with_page4(_context("positive"), row)) == (NO_NUMBER,)


def test_n2_identical_duplicate_lines_are_one_cited_row() -> None:
    row = "Other  9  9  9  9  9  9"
    ctx = _with_page4(_context("positive"), row + "\n" + row)
    payload = _quoting(row)
    assert _payload_issues(payload, ctx) == ()
    cells = {c.fact.fact_id: c.fact for c in _compute_with(ctx, payload).cells}
    assert cells["T4E.2.c03.claim"].amount == 9


@pytest.mark.parametrize("cell", ["+5.00", ".5"])
def test_n2_a_signed_plus_or_bare_fraction_cell_has_no_number(cell: str) -> None:
    row = f"Deferred items  1  1  1  1  {cell}  1"
    assert _payload_issues(_quoting(row), _with_page4(_context("positive"), row)) == (NO_NUMBER,)
