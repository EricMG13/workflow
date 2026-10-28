"""CP-2H Stage 1: the pure trigger calculation against the frozen oracle `cases/cp2h-owner`.

Every input is built from the oracle's own files: the agency source pages of `manifest.json`,
the analyst payloads of `submissions.json`, the frozen financial pack, and the settled CP-2G
facts (and CP-1 reported ratios as CP-2G recorded them) of the pinned CP-2G oracle
`cases/cp2g-owner/expected.json`. Every expectation is read from `expected.json`. Declared
stand-ins (Stage 2 binds the real ones): the CP-1 fact ids and calculation ids, and the hashes
of the attempt's bound Inputs.
"""

import copy
import hashlib
import json
import re
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from deploy_vii import prose
from deploy_vii.business_context import spelled
from deploy_vii.contracts import Fact, Input, Source, Span, validate_tables
from deploy_vii.model._cells import CONTEXT
from deploy_vii.report_view import fact_spelling, figure_unit
from deploy_workflow.owners import cp2h

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "cp2h-owner"
EXPECTED: dict[str, Any] = json.loads((CASE / "expected.json").read_text(encoding="utf-8"))
SUBMISSIONS: dict[str, Any] = json.loads((CASE / "submissions.json").read_text(encoding="utf-8"))
MANIFEST: dict[str, Any] = json.loads((CASE / "manifest.json").read_text(encoding="utf-8"))
CP2G: dict[str, Any] = json.loads(
    (ROOT / "cases" / "cp2g-owner" / "expected.json").read_text(encoding="utf-8")
)
FINANCIAL: dict[str, Any] = json.loads(
    (ROOT / "cases" / "financial" / "manifest.json").read_text(encoding="utf-8")
)
# Oracle pins: the lease header after the CP-1D 1D1 cascade (docs/CP2H-OWNER-LEASE.md:3), and the
# upstream files its builder pins.
PINS = {
    "cases/cp2h-owner/manifest.json": (
        "1c0aa69f41c19ff03cc51bc1677d0b2aff02414dd1c0a1cd7422a8d5991a0f8c"
    ),
    "cases/cp2h-owner/submissions.json": (
        "9484d2a977677244104704479114e1d986a88851c004820409ac204cff5ea647"
    ),
    "cases/cp2h-owner/expected.json": (
        "59cdb4d1c8d14b554beccc69bf7b59e94c13d5d26f51f0a05d36c7769b010ea5"
    ),
    "cases/cp2h-owner/builder/build.py": (
        "21c5ca8eb095ec2d3e34958dbd05ead13fdb1907d7662addf3f9d37d000f6e3b"
    ),
    "cases/cp2g-owner/manifest.json": (
        "1c36928c44a0a69ce9da286db4332f2d8aa8e2fca1b1d9504b9191969d105242"
    ),
    "cases/cp2g-owner/expected.json": (
        "97328745be246b3bf67fe5840f291afb3da3cbae99b51db1ba7bd24d2eef406c"
    ),
    "src/deploy_vii/methodology.json": (
        "1bb6c0bc6fa13b8e668266cb1aa76dcc8ffe6178bcf403958ce761b94dbb89a6"
    ),
}
COMPOSED = ("positive", "gap", "fixture_total_loss", "fixture_boundary")
ISSUER = FINANCIAL["run"]["issuer_name"]
FIG = re.compile(r"\{\{FIG:([a-z_]+)\|([^}]*)\}\}")
REF = re.compile(r"\{([A-Za-z0-9][A-Za-z0-9_.:-]*)\|([^}]*)\}")


@pytest.mark.parametrize("path", PINS)
def test_oracle_pins(path: str) -> None:
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == PINS[path]


# --- inputs from the oracle's own files --------------------------------------------------------


def _source(source_id: str, name: str, pages: list[dict[str, str]], sha256: str) -> Source:
    joined = "\f".join(p["text"] for p in pages)
    assert hashlib.sha256(joined.encode("utf-8")).hexdigest() == sha256, source_id
    return Source(
        source_id=source_id,
        name=name,
        status="ready",
        sha256=sha256,
        media_type="text/plain",
        spans=tuple(Span(locator=p["locator"], text=p["text"]) for p in pages),
        extraction_status="complete",
    )


def _variant(variant: str) -> dict[str, Any]:
    synthetic = MANIFEST["synthetic_source"]
    found: dict[str, Any] = (
        synthetic[variant] if variant in synthetic else synthetic["fixtures"][variant]
    )
    return found


def pack(variant: str) -> cp2h.PackScope:
    """identity + financial (frozen), plus the agency source variant the oracle names."""
    frozen = tuple(
        _source(s["source_id"], s["name"], s["pages"], s["sha256"]) for s in FINANCIAL["sources"]
    )
    v = _variant(variant)
    ratings = _source("ratings", MANIFEST["synthetic_source"]["name"], v["pages"], v["sha256"])
    return cp2h.PackScope(sources=(*frozen, ratings), names=(ISSUER,))


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def cp1_facts(cp2g_case: str) -> tuple[Fact, ...]:
    """The four CP-1 reported ratios as the CP-2G oracle records the CP-1 head; fact and
    calculation ids are stand-ins for the run-time binding."""
    records = CP2G["cases"][cp2g_case]["cp1_inputs"]
    out = []
    for metric in cp2h.CP1_METRICS:
        r = records[metric]
        known = r["status"] == "known"
        out.append(
            Fact(
                fact_id=f"interface-fact:{_digest(r['label'])}",
                label=r["label"],
                table_id="T4.10",
                row_id=metric,
                field="ltm",
                status=r["status"],
                amount=Decimal(r["amount_exact"]) if known else None,
                unit={"multiple": "MULTIPLE", "percent": "PERCENT"}[r["unit_class"]],
                period=r["period"],
                value_class=r["value_class"],
                calculation_id=f"canonical-kpi:{_digest(r['label'])}" if known else None,
                limitation=r["limitation"],
            )
        )
    return tuple(out)


def _cp2g_fact(r: dict[str, Any]) -> Fact:
    return Fact(
        fact_id=r["fact_id"],
        label=r["label"],
        table_id=r["table_id"],
        row_id=r["row_id"],
        field=r["field"],
        status=r["status"],
        amount=None if r.get("amount_exact") is None else Decimal(r["amount_exact"]),
        text=r.get("text"),
        unit=r.get("unit"),
        period=r.get("period"),
        decimals=r.get("decimals"),
        value_class=r.get("value_class"),
        formula=r.get("formula"),
        calculation_id=r.get("calculation_id"),
        limitation=r.get("limitation"),
    )


def cp2g_metrics(cp2g_case: str) -> cp2h.Cp2gMetrics:
    head = CP2G["cases"][cp2g_case]
    return cp2h.Cp2gMetrics.select(head["module_status"], (_cp2g_fact(r) for r in head["facts"]))


def _input(input_id: str, status: Any) -> Input:
    return Input(input_id=input_id, sha256=_digest(f"stage1 stand-in {input_id}"), status=status)


BOUND = (
    _input("prepared-pack", "accepted"),
    _input("CP-0", "restricted"),
    _input("CP-1", "restricted"),
    _input("CP-2G", "restricted"),
)
CP1_STATUS = EXPECTED["execution"]["statuses"]["CP-1"].split()[0]


def upstream(
    cp2g_case: str, current: tuple[Input, ...] | None = None, cp1: tuple[Fact, ...] | None = None
) -> cp2h.TriggerUpstream:
    return cp2h.TriggerUpstream(
        bound=BOUND,
        current=BOUND if current is None else current,
        cp1_facts=cp1_facts(cp2g_case) if cp1 is None else cp1,
        cp1_status=CP1_STATUS,
        cp2g=cp2g_metrics(cp2g_case),
    )


def fig_ids(cp1: tuple[Fact, ...]) -> dict[str, str]:
    """FIG name -> the CP-1 fact id bound by the manifest's selection rule (unique label)."""
    by_metric = cp2h.select_cp1(cp1)
    return {name: by_metric[f["metric"]].fact_id for name, f in SUBMISSIONS["figures"].items()}


@pytest.mark.parametrize("case", COMPOSED)
def test_cp1_fixture_spells_the_figures(case: str) -> None:
    by_metric = cp2h.select_cp1(cp1_facts(spec(case)[1]))
    for name, figure in EXPECTED["cases"][case]["figures"].items():
        assert spelled(by_metric[figure["cp1_metric"]]) == figure["spelled"], name


def bind(payload: Any, ids: Mapping[str, str]) -> Any:
    text = FIG.sub(lambda m: "{" + ids[m[1]] + "|" + m[2] + "}", json.dumps(payload))
    return json.loads(text)


def raw_payload(case: str) -> dict[str, Any]:
    found = SUBMISSIONS["cases"].get(case) or SUBMISSIONS["fixtures"][case]
    payload: dict[str, Any] = found["rating_triggers"]
    return payload


def spec(case: str) -> tuple[str, str]:
    """(agency source variant, CP-2G oracle case) the oracle names for a case."""
    c = EXPECTED["cases"][case]
    if case in SUBMISSIONS["fixtures"]:
        assert SUBMISSIONS["fixtures"][case]["agency_source"] == c["source_variant"]
    return c["source_variant"], c["cp2g_head"]["case"]


def inputs(case: str, payload: Any | None = None, **up: Any) -> cp2h.TriggerInputs:
    variant, cp2g_case = spec(case)
    stream = upstream(cp2g_case, **up)
    body = bind(raw_payload(case) if payload is None else payload, fig_ids(stream.cp1_facts))
    return cp2h.TriggerInputs(
        pack=pack(variant),
        upstream=stream,
        submission=cp2h.TriggerSubmission.model_validate_json(json.dumps(body)),
    )


def report(case: str) -> cp2h.TriggerReport:
    return cp2h.compute(inputs(case))


def names_of(stream: cp2h.TriggerUpstream) -> dict[str, str]:
    """CP-1 fact id -> FIG name (the inverse of the run-time binding)."""
    return {fid: name for name, fid in fig_ids(stream.cp1_facts).items()}


# --- the composed module -------------------------------------------------------------------------


@pytest.mark.parametrize("case", COMPOSED)
def test_cp2g_and_cp1_inputs_are_the_oracles(case: str) -> None:
    """The oracle's CP-1 inputs and cp2g_head are the pinned CP-2G oracle's own."""
    want = EXPECTED["cases"][case]
    _, cp2g_case = spec(case)
    assert want["cp2g_head"]["module_status"] == CP2G["cases"][cp2g_case]["module_status"]
    for metric, record in want["cp1_inputs"].items():
        assert record == CP2G["cases"][cp2g_case]["cp1_inputs"][metric]


@pytest.mark.parametrize("case", COMPOSED)
def test_parsed_source(case: str) -> None:
    variant, _ = spec(case)
    ratings = cp2h.ratings_source(pack(variant))
    parsed = cp2h.parse_ratings(cp2h.source_pages(ratings))
    register = [
        {
            "agency": r.agency,
            "instrument": r.instrument,
            "rating": r.rating,
            "outlook": r.outlook,
            "date": r.date,
            "position": r.position,
        }
        for r in parsed.register
    ]
    triggers = [
        {
            "agency": t.agency,
            "direction": t.direction,
            "metric": t.metric,
            "comparison": t.comparison,
            "threshold_text": t.threshold_text,
            "threshold": None if t.threshold is None else cp2h.exact_text(t.threshold),
        }
        for t in parsed.triggers
    ]
    assert {"register": register, "triggers": triggers} == EXPECTED["cases"][case]["parsed_source"]
    assert EXPECTED["cases"][case]["source_sha256"] == ratings.sha256


def _assert_cell(cell: cp2h.Cell, want: dict[str, Any]) -> None:
    record = cell.record()
    for key, value in want.items():
        assert record[key] == value, (want["fact_id"], key, record[key], value)
    for key, value in record.items():
        if key not in want:
            assert value in (None, []), (want["fact_id"], key, value)


@pytest.mark.parametrize("case", COMPOSED)
def test_facts(case: str) -> None:
    want = EXPECTED["cases"][case]["facts"]
    got = report(case)
    assert [c.fact.fact_id for c in got.cells] == [f["fact_id"] for f in want]
    for cell, expected in zip(got.cells, want, strict=True):
        _assert_cell(cell, expected)


@pytest.mark.parametrize("case", COMPOSED)
def test_tables(case: str) -> None:
    got = report(case)
    tables = [
        {
            "table_id": t.table_id,
            "title": t.title,
            "columns": [c.field for c in t.columns],
            "rows": [
                {"row_id": r.row_id, "label": r.label, "fact_ids": list(r.fact_ids)} for r in t.rows
            ],
        }
        for t in got.tables
    ]
    assert tables == EXPECTED["cases"][case]["tables"]
    assert [t.table_id for t in got.tables] == EXPECTED["d8_table_ids"]["cp2h_table_ids"]
    validate_tables(got.tables, got.facts)  # one fact per column in every row
    placed = [fid for t in got.tables for r in t.rows for fid in r.fact_ids]
    assert sorted(placed) == sorted(f.fact_id for f in got.facts)  # every fact in one row


def _rendered(text: str, got: cp2h.TriggerReport, cp1: Mapping[str, Fact]) -> str:
    cells = {c.fact.fact_id: c for c in got.cells}

    def spell(m: re.Match[str]) -> str:
        fid = m[1]
        if fid in cp1:
            return spelled(cp1[fid])
        shown = cells[fid].shown
        assert shown is not None, fid
        return shown

    return REF.sub(spell, text)


@pytest.mark.parametrize("case", COMPOSED)
def test_claims(case: str) -> None:
    case_inputs = inputs(case)
    got = cp2h.compute(case_inputs)
    names = names_of(case_inputs.upstream)
    cp1 = {f.fact_id: f for f in case_inputs.upstream.cp1_facts}

    def unbind(text: str) -> str:
        return REF.sub(
            lambda m: "{{FIG:" + names[m[1]] + "|" + m[2] + "}}" if m[1] in names else m[0], text
        )

    claims = [
        {
            "claim_id": c.claim_id,
            "text": unbind(c.text),
            "limitation": c.limitation,
            "citations": [x.model_dump() for x in c.citations],
            "cp1_references": [names[f] for f in c.cp1_references],
            "text_rendered": _rendered(c.text, got, cp1),
        }
        for c in got.claims
    ]
    want = [
        {
            k: c[k]
            for k in (
                "claim_id",
                "text",
                "limitation",
                "citations",
                "cp1_references",
                "text_rendered",
            )
        }
        for c in EXPECTED["cases"][case]["claims"]
    ]
    assert claims == want


@pytest.mark.parametrize("case", COMPOSED)
def test_claims_pass_prose_checks(case: str) -> None:
    """Every claim resolves against the module's facts and the CP-1 facts, no bare figure."""
    case_inputs = inputs(case)
    got = cp2h.compute(case_inputs)
    bound = prose.bind((*got.facts, *case_inputs.upstream.cp1_facts))
    for claim in got.claims:
        assert prose.issues(claim.text, bound, names=(ISSUER,)) == (), claim.claim_id


@pytest.mark.parametrize("case", COMPOSED)
def test_own_limitations(case: str) -> None:
    assert list(report(case).own_limitations) == EXPECTED["cases"][case]["own_limitations"]


@pytest.mark.parametrize("case", COMPOSED)
def test_cp1_references(case: str) -> None:
    case_inputs = inputs(case)
    got = cp2h.compute(case_inputs)
    want = EXPECTED["cases"][case]["cp1_references"]
    assert (want["table_id"], want["title"], want["row_header"]) == cp2h.CP1_REFERENCES
    rows = [
        {
            "row_id": r.row_id,
            "figure": r.figure,
            "label": r.label,
            "cp1_label": r.fact.label,
            "period": r.fact.period,
            "status": r.fact.status,
            "unit": figure_unit(r.fact),
            "shown": fact_spelling(r.fact, None)[2],
            "cell_text": fact_spelling(r.fact, None)[2],
            "value_class": r.fact.value_class,
            "amount_exact": None if r.fact.amount is None else cp2h.exact_text(r.fact.amount),
            "limitation": r.fact.limitation,
        }
        for r in got.cp1_references
    ]
    assert rows == [{k: v for k, v in r.items() if k != "fact_id"} for r in want["rows"]]
    by_metric = cp2h.select_cp1(case_inputs.upstream.cp1_facts)
    for r in got.cp1_references:  # carried verbatim
        assert r.fact == by_metric[r.fact.row_id]


@pytest.mark.parametrize("case", COMPOSED)
def test_cp2g_references(case: str) -> None:
    got = report(case)
    want = EXPECTED["cases"][case]["cp2g_references"]
    assert (want["table_id"], want["title"], want["row_header"]) == cp2h.CP2G_REFERENCES
    rows = [
        {
            "row_id": r.row_id,
            "fact_id": r.fact.fact_id,
            "label": r.fact.label,
            "period": r.fact.period,
            "status": r.fact.status,
            "unit": r.fact.unit,
            "shown": fact_spelling(r.fact, None)[2] if r.fact.status == "known" else None,
            "value_class": r.fact.value_class,
            "amount_exact": None if r.fact.amount is None else cp2h.exact_text(r.fact.amount),
            "limitation": r.fact.limitation,
        }
        for r in got.cp2g_references
    ]
    assert rows == want["rows"]
    assert (
        sorted(r.fact.fact_id for r in got.cp2g_references)
        == EXPECTED["cases"][case]["cp2g_head"]["facts_read"]
    )


def _exact(value: Decimal | None) -> str | None:
    return None if value is None else cp2h.exact_text(value)


@pytest.mark.parametrize("case", COMPOSED)
def test_results_totals_and_divergence(case: str) -> None:
    got = report(case)
    want = EXPECTED["cases"][case]
    results = {
        o.row: {
            "fy25_headroom": _exact(o.fy25_headroom),
            "fy25_reached": o.fy25_reached,
            **{
                name: {
                    "headroom": [_exact(h) for h in c.headroom],
                    "hits": list(c.hits),
                    "first": c.first,
                }
                for name, c in (("base", o.base), ("down", o.down))
            },
        }
        for o in got.outcomes
    }
    assert results == want["results"]
    assert {k: list(v) for k, v in got.totals.items()} == want["totals"]
    facts = {c.fact.fact_id: c.fact for c in got.cells}
    for d in want["divergence"]:
        notches = facts[f"T2R.8.{d['row']}.notches"]
        lower = facts[f"T2R.8.{d['row']}.lower_rated"]
        outlooks = facts[f"T2R.8.{d['row']}.outlook_match"]
        assert (
            None if notches.amount is None else int(notches.amount),
            lower.text,
            outlooks.text,
        ) == (
            d["notches"],
            d["lower"],
            d["outlooks"],
        )


@pytest.mark.parametrize("case", COMPOSED)
def test_fp05_cells(case: str) -> None:
    """Every FP05 tab cell: fact, field, display (`fact_spelling`) and state; tab rows follow the
    table rows. The block itself is a Stage 3 rendering concern."""
    got = report(case)
    cells = {c.fact.fact_id: c for c in got.cells}
    tables = {t.table_id: t for t in got.tables}
    fp05 = EXPECTED["cases"][case]["FP05"]
    assert fp05["evidence_rail_tables"] == [
        *list(cp2h.TABLES)[:3],
        cp2h.CP1_REFERENCES[0],
        cp2h.CP2G_REFERENCES[0],
    ]
    for block in fp05["blocks"].values():
        for tab in block["tabs"]:
            rows = tables[tab["table_id"]].rows
            assert [(r["row_id"], r["label"]) for r in tab["rows"]] == [
                (r.row_id, r.label) for r in rows
            ]
            for row, mine in zip(tab["rows"], rows, strict=True):
                assert [c["fact_id"] for c in row["cells"]] == list(mine.fact_ids)
                for want in row["cells"]:
                    cell = cells[want["fact_id"]]
                    _, state, text = fact_spelling(
                        cell.fact, None if cell.fact.status == "known" else "G1"
                    )
                    shown = text.replace("G1", "G#") if state != "known" else cell.shown
                    assert (cell.fact.field, shown, state) == (
                        want["field"],
                        want["shown"],
                        want["state"],
                    )


@pytest.mark.parametrize("case", COMPOSED)
def test_known_facts_never_derive_from_unsettled(case: str) -> None:
    got = report(case)
    status = {c.fact.fact_id: c.fact.status for c in got.cells}
    for cell in got.cells:
        if cell.fact.status == "known":
            for ref in cell.derives_from:
                if not ref.startswith(("cp1:", "cp2g:")):
                    assert status[ref] == "known", (cell.fact.fact_id, ref)


def test_consumption_lineage() -> None:
    """D3 (c): T2R.4 actuals list the CP-2G a25 facts (5), the yearly headrooms their row's
    facts (30) and the first-year texts the facts of their three rows (10)."""
    got = report("positive")
    lineage = {c.fact.fact_id: c.derives_from for c in got.cells}
    actual = [
        k
        for k, d in lineage.items()
        if k.endswith(".actual") and any(x.startswith("cp2g:T2H.6.a25.") for x in d)
    ]
    yearly = [
        k
        for k, d in lineage.items()
        if re.fullmatch(r"T2R\.5\..*\.y[123]", k) and d[0].startswith("cp2g:")
    ]
    first = [
        k
        for k, d in lineage.items()
        if k.endswith("_first") and sum(x.startswith("cp2g:") for x in d) == 3
    ]
    assert (len(actual), len(yearly), len(first)) == (5, 30, 10)
    cp2g = {f.fact_id: f for f in cp2g_metrics("gap").facts}
    for cell in got.cells:  # (d) every copied value equals the CP-2G head's own fact
        if cell.fact.field == "actual":
            source = cp2g[cell.derives_from[0].removeprefix("cp2g:")]
            assert cell.fact.amount == source.amount


# --- refusals (calculation level) ----------------------------------------------------------------

SUBMITTED = {r["id"]: r for r in SUBMISSIONS["refusals"]}


def _matches(issue: str, expected: str, prefix: str | None) -> bool:
    return issue.startswith(prefix) if prefix else issue == expected


def _refusal_issues(refusal: dict[str, Any]) -> tuple[tuple[str, ...], cp2h.TriggerInputs | None]:
    submitted = SUBMITTED[refusal["id"]]
    variant = submitted.get("source_fixture", "positive")
    current = None
    if "upstream_literal" in submitted:
        changed = {c["input_id"]: c for c in submitted["upstream_literal"]["current"]}
        current = tuple(
            Input(
                input_id=i.input_id,
                sha256=changed[i.input_id]["sha256"],
                status=changed[i.input_id]["status"],
            )
            if i.input_id in changed
            else i
            for i in BOUND
        )
    stream = upstream("gap", current=current)
    the_pack = pack(variant)
    if submitted.get("payload_text") is not None:
        text = submitted["payload_text"]
    elif submitted.get("bind_placeholders") is False:
        text = json.dumps(submitted["payload"])
    else:
        text = json.dumps(bind(submitted["payload"], fig_ids(stream.cp1_facts)))
    issues = cp2h.payload_issues(text, pack=the_pack, upstream=stream)
    try:
        parsed = cp2h.TriggerSubmission.model_validate_json(text)
    except ValueError:
        return issues, None
    return issues, cp2h.TriggerInputs(pack=the_pack, upstream=stream, submission=parsed)


def _expected(refusal: dict[str, Any]) -> list[str]:
    if refusal["id"] not in ("v17", "v18"):
        return list(refusal["expected_issues"])
    upstream_id = "CP-2G" if refusal["id"] == "v17" else "CP-1"
    bound = next(i for i in BOUND if i.input_id == upstream_id)
    tail = refusal["expected_issues"][0].split(">", 1)[1]
    return [f"{refusal['issue_prefix']}{bound.sha256[:12]}{tail}"]


@pytest.mark.parametrize("refusal", EXPECTED["refusals"], ids=lambda r: str(r["id"]))
def test_refusal_issues(refusal: dict[str, Any]) -> None:
    issues, parsed = _refusal_issues(refusal)
    expected = _expected(refusal)
    prefix = refusal.get("issue_prefix") if refusal["id"] == "v16" else None
    assert len(issues) == len(expected), issues
    assert all(_matches(i, e, prefix) for i, e in zip(issues, expected, strict=True)), issues
    if parsed is not None:
        with pytest.raises(ValueError):
            cp2h.compute(parsed)


def test_blocked_attempts_issue_text() -> None:
    """The blocked case's two invalid attempts (r01, then v08) give the head's limitations."""
    blocked = EXPECTED["cases"]["blocked"]
    by_id = {r["id"]: r for r in EXPECTED["refusals"]}
    for key in ("attempt_0", "attempt_1"):
        issues, _ = _refusal_issues(by_id[blocked[key]["payload"]])
        assert list(issues) == blocked[key]["limitations"]


@pytest.mark.parametrize("case", COMPOSED)
def test_valid_cases_have_no_issues(case: str) -> None:
    assert cp2h.validate(inputs(case)) == ()


@pytest.mark.parametrize(
    ("fixture", "issue"),
    [
        ("register_not_found", "Rating register not found"),
        ("terms_not_found", "Trigger terms not found"),
    ],
)
def test_parse_rule_refusals(fixture: str, issue: str) -> None:
    pages = [p["text"] for p in _variant(fixture)["pages"]]
    with pytest.raises(cp2h.SourceIssue, match=f"^{issue}$"):
        cp2h.parse_ratings(pages)


def test_parse_rule_scale_and_metric() -> None:
    pages = [p["text"] for p in _variant("positive")["pages"]]
    with pytest.raises(cp2h.SourceIssue, match="^Rating scale not found$"):
        cp2h.parse_ratings([pages[0], pages[1].replace(cp2h.SCALE_HEADER, "Position"), pages[2]])
    off = pages[0].replace("Issuer rating  BB  Negative", "Issuer rating  CCC  Negative")
    with pytest.raises(cp2h.SourceIssue, match="^Rating not on the scale: Alder Ratings CCC$"):
        cp2h.parse_ratings([off, pages[1], pages[2]])
    odd = pages[2].replace("Free cash flow to total debt", "Funds from operations to debt")
    with pytest.raises(
        cp2h.SourceIssue, match="^Unrecognised trigger metric: Funds from operations to debt$"
    ):
        cp2h.parse_ratings([pages[0], pages[1], odd])


def test_phrase_guard() -> None:
    """Every core-local phrase trips the guard, case-insensitively, quoted as listed; 'probability
    of' is deliberately not listed (expected.json phrase_guard)."""
    guard = EXPECTED["phrase_guard"]["core_local"]
    for kind, phrases in guard.items():
        for phrase in phrases:
            assert cp2h.phrase_issues("p", f"Text {phrase.upper()} here.") == (
                f'p: prohibited conclusion ({kind}): "{phrase}"',
            )
    assert {k: list(v) for k, v in cp2h.CORE_PHRASES.items()} == guard
    assert cp2h.phrase_issues("p", "The probability of a review is not computed.") == ()


def test_phrase_guard_covers_limitations() -> None:
    payload = copy.deepcopy(raw_payload("positive"))
    payload["views"][1]["limitation"] = "The issuer will be downgraded."
    payload["overall"]["limitation"] = "Results are probability weighted."
    assert cp2h.validate(inputs("positive", payload)) == (
        'views[1].limitation: prohibited conclusion (rating call): "will be downgraded"',
        'overall.limitation: prohibited conclusion (probability weighting): "probability weighted"',
    )


def test_views_compose_in_register_order() -> None:
    """id_rules: T2R.7 rows are the views in register order, whatever the submission order."""
    payload = copy.deepcopy(raw_payload("positive"))
    payload["views"].reverse()
    got = cp2h.compute(inputs("positive", payload))
    base = report("positive")
    assert [c.record() for c in got.cells] == [c.record() for c in base.cells]
    assert got.claims == base.claims


def test_prose_reference_rules() -> None:
    """Analyst cells are not bound (ruling P2), a figure naming a gap is refused, and a CP-2G
    fact is not referencable (lease: module facts and CP-1 figures only)."""
    payload = copy.deepcopy(raw_payload("gap"))
    payload["views"][0]["rationale"] = "The view is [T2R.7.a01.view]."
    payload["views"][1]["rationale"] = "They are {T2R.8.p01.notches|notches} apart."
    payload["overall"]["rationale"] = "Leverage is {T2H.6.b26.total_leverage|x}."
    assert cp2h.validate(inputs("gap", payload)) == (
        "views[0].rationale: Unresolved reference: T2R.7.a01.view",
        "views[1].rationale: Figure reference names a gap: T2R.8.p01.notches",
        "overall.rationale: Unresolved reference: T2H.6.b26.total_leverage",
    )


# --- branches no frozen case reaches -----------------------------------------------------------------


def _replaced(facts: tuple[Fact, ...], metric: str, **update: Any) -> tuple[Fact, ...]:
    return tuple(f.model_copy(update=update) if f.row_id == metric else f for f in facts)


def test_check_differs_from_cp1() -> None:
    """Lease T2R.4: 'Differs from CP-1' when the copy and CP-1's ratio differ exactly."""
    cp1 = _replaced(cp1_facts("gap"), "net_leverage_reported", amount=Decimal("1.01"))
    got = cp2h.compute(inputs("positive", cp1=cp1))
    facts = {c.fact.fact_id: c.fact for c in got.cells}
    assert facts["T2R.4.t04.check"].text == "Differs from CP-1"
    assert facts["T2R.4.t05.check"].text == "Differs from CP-1"
    assert facts["T2R.4.t01.check"].text == "Reconciled to CP-1"


def test_check_not_compared_when_cp1_missing() -> None:
    cp1 = _replaced(
        cp1_facts("gap"),
        "fcf_to_debt",
        status="missing",
        amount=None,
        calculation_id=None,
        limitation="Not stated",
    )
    got = cp2h.compute(inputs("positive", cp1=cp1))
    check = next(c for c in got.cells if c.fact.fact_id == "T2R.4.t03.check")
    assert (check.fact.text, check.derives_from) == ("Not compared", ())


def test_unsettled_cp2g_actual_keeps_its_status() -> None:
    """A CP-2G a25 ratio that is not applicable: the copy keeps CP-2G's status and limitation
    (rulings G-decisions, the L10-c copy rule); the headroom is missing with that reason."""
    variant, cp2g_case = spec("positive")
    metrics = cp2g_metrics(cp2g_case)
    reason = "Not meaningful: a stand-in reason"
    facts = tuple(
        f.model_copy(update={"status": "not_applicable", "amount": None, "limitation": reason})
        if f.fact_id == "T2H.6.a25.interest_coverage"
        else f
        for f in metrics.facts
    )
    stream = cp2h.TriggerUpstream(
        bound=BOUND,
        current=BOUND,
        cp1_facts=cp1_facts(cp2g_case),
        cp1_status=CP1_STATUS,
        cp2g=cp2h.Cp2gMetrics(status=metrics.status, facts=facts),
    )
    body = bind(raw_payload("positive"), fig_ids(stream.cp1_facts))
    got = cp2h.compute(
        cp2h.TriggerInputs(
            pack(variant), stream, cp2h.TriggerSubmission.model_validate_json(json.dumps(body))
        )
    )
    cells = {c.fact.fact_id: c.fact for c in got.cells}
    actual, head = cells["T2R.4.t02.actual"], cells["T2R.4.t02.headroom"]
    assert (actual.status, actual.unit, actual.limitation) == ("not_applicable", "MULTIPLE", reason)
    assert (head.status, head.limitation) == ("missing", reason)
    assert cells["T2R.4.t02.check"].text == "Not compared"


UNPINNED = {
    "cp1d_bound": "CP-1D is bound",
    "no_gaps": "no gap",
    "no_triggers": "no trigger term",
    "one_agency": "one agency",
    "unrated_with_terms": "unrated agency Brook Credit has a trigger term",
    "no_published": "page:3 states no single publication date",
    "no_ratings": "no single ready ratings source",
}


@pytest.mark.parametrize("mutate", UNPINNED)
def test_unpinned_states_fail_closed(mutate: str) -> None:
    payload = copy.deepcopy(raw_payload("positive"))
    case_inputs = inputs("positive", payload)
    the_pack, stream = case_inputs.pack, case_inputs.upstream
    pages = [p["text"] for p in _variant("positive")["pages"]]
    if mutate == "cp1d_bound":
        stream = cp2h.TriggerUpstream(
            bound=stream.bound,
            current=stream.current,
            cp1_facts=stream.cp1_facts,
            cp1_status=stream.cp1_status,
            cp2g=stream.cp2g,
            cp1d_status="restricted",
        )
    elif mutate == "no_gaps":
        payload["gaps"] = []
    elif mutate == "no_ratings":
        the_pack = cp2h.PackScope(sources=the_pack.sources[:2], names=the_pack.names)
    else:
        if mutate == "no_triggers":
            pages[2] = pages[2].split(cp2h.TERMS_HEADER)[0] + cp2h.TERMS_HEADER
        elif mutate == "one_agency":
            pages[0] = "\n".join(
                ln for ln in pages[0].split("\n") if not ln.startswith("Brook Credit  ")
            )
            payload["views"].pop()
        elif mutate == "unrated_with_terms":
            pages[0] = pages[0].replace(
                "Issuer rating  Ba3  Stable", "Issuer rating  Withdrawn  Stable"
            )
        elif mutate == "no_published":
            pages[2] = pages[2].replace("Published January 10, 2026.\n", "")
        joined = "\f".join(pages)
        ratings = Source(
            source_id="ratings",
            name="Fixture",
            status="ready",
            sha256=_digest(joined),
            media_type="text/plain",
            spans=tuple(Span(locator=f"page:{n}", text=t) for n, t in enumerate(pages, 1)),
            extraction_status="complete",
        )
        the_pack = cp2h.PackScope(sources=(*the_pack.sources[:2], ratings), names=the_pack.names)
    body = bind(payload, fig_ids(stream.cp1_facts))
    sub = cp2h.TriggerSubmission.model_validate_json(json.dumps(body))
    with pytest.raises(cp2h.UnpinnedCase, match=UNPINNED[mutate]):
        cp2h.validate(cp2h.TriggerInputs(the_pack, stream, sub))


def test_input_selection_fails_closed() -> None:
    facts = cp1_facts("gap")
    with pytest.raises(ValueError, match="exactly one"):
        cp2h.select_cp1(
            (*facts, facts[0].model_copy(update={"fact_id": "interface-fact:duplicate"}))
        )
    metrics = cp2g_metrics("gap")
    with pytest.raises(ValueError, match="exactly one"):
        cp2h.Cp2gMetrics.select("restricted", metrics.facts[1:])
    with pytest.raises(ValueError, match="28 T2H.6 facts"):
        cp2h.Cp2gMetrics(status="restricted", facts=tuple(reversed(metrics.facts)))


# --- property tests (expected.json property_tests) -------------------------------------------------

DECIMALS = st.decimals(min_value=Decimal(-1000), max_value=Decimal(1000), places=6, allow_nan=False)
COMPARISONS = st.sampled_from(("Above", "Below"))
UNITS = st.sampled_from(("multiple", "percent"))


@given(metric=DECIMALS, threshold=DECIMALS, comparison=COMPARISONS, unit=UNITS)
def test_headroom_sign_matches_reached(
    metric: Decimal, threshold: Decimal, comparison: Any, unit: Any
) -> None:
    h = cp2h.headroom(comparison=comparison, metric=metric, threshold=threshold, unit_class=unit)
    reached = cp2h.is_reached(comparison=comparison, metric=metric, threshold=threshold)
    assert (h < 0) == reached
    assert (h == 0) == (metric == threshold)


@given(a=DECIMALS, b=DECIMALS, threshold=DECIMALS, comparison=COMPARISONS, unit=UNITS)
def test_headroom_monotone(
    a: Decimal, b: Decimal, threshold: Decimal, comparison: Any, unit: Any
) -> None:
    """'Above': the headroom does not fall as the metric falls; 'Below': as the metric rises."""
    low, high = sorted((a, b))
    h_low = cp2h.headroom(comparison=comparison, metric=low, threshold=threshold, unit_class=unit)
    h_high = cp2h.headroom(comparison=comparison, metric=high, threshold=threshold, unit_class=unit)
    assert (h_low >= h_high) if comparison == "Above" else (h_high >= h_low)


@given(metric=DECIMALS, threshold=DECIMALS, comparison=COMPARISONS)
def test_pp_scale_is_scaleb(metric: Decimal, threshold: Decimal, comparison: Any) -> None:
    pp = cp2h.headroom(
        comparison=comparison, metric=metric, threshold=threshold, unit_class="percent"
    )
    raw = cp2h.headroom(
        comparison=comparison, metric=metric, threshold=threshold, unit_class="multiple"
    )
    assert pp == raw.scaleb(2, CONTEXT)
    assert pp.as_tuple().digits == raw.as_tuple().digits  # an exponent shift, no rounding


@given(hits=st.lists(st.sampled_from((True, False, None)), min_size=3, max_size=3))
def test_first_year_is_the_earliest_reached(hits: list[bool | None]) -> None:
    result = cp2h.first_year(hits=hits)
    first_hit = next((k for k, h in enumerate(hits) if h), None)
    first_unknown = next((k for k, h in enumerate(hits) if h is None), None)
    if first_hit is not None and (first_unknown is None or first_hit < first_unknown):
        assert result == cp2h.FY[first_hit]
    elif first_unknown is not None:
        assert result == cp2h.NOT_CALCULABLE
    else:
        assert result == cp2h.NOT_REACHED


@pytest.mark.parametrize("case", COMPOSED)
def test_reconciliation_property(case: str) -> None:
    """T2R.4 actual equals CP-2G T2H.6.a25 and CP-1's reported ratio exactly."""
    case_inputs = inputs(case)
    got = cp2h.compute(case_inputs)
    cp1 = cp2h.select_cp1(case_inputs.upstream.cp1_facts)
    for o in got.outcomes:
        cell = next(c for c in got.cells if c.fact.fact_id == f"T2R.4.{o.row}.actual")
        a25 = case_inputs.upstream.cp2g.fact("a25", cell.derives_from[0].rsplit(".", 1)[1])
        metric = next(m for m in cp2h.METRICS.values() if m.field == a25.field)
        assert cell.fact.amount == a25.amount == cp1[metric.cp1_metric].amount
