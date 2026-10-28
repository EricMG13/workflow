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
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from defect_classes import BLANK_CASES, EMPTY_TEXT, Adapter, BlankCase, blank_failure
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
# Oracle pins: cases/PINS.json, the shared manifest LEAD regenerates (python3 -I cases/pins.py).
# The CP-2H oracle and builder, and the upstream files its builder pins.
PINS: dict[str, str] = json.loads((ROOT / "cases" / "PINS.json").read_text(encoding="utf-8"))
PINNED = (
    *(
        f"cases/cp2h-owner/{name}"
        for name in ("manifest.json", "submissions.json", "expected.json", "builder/build.py")
    ),
    "cases/cp2g-owner/manifest.json",
    "cases/cp2g-owner/expected.json",
    "src/deploy_vii/methodology.json",
)
COMPOSED = ("positive", "gap", "fixture_total_loss", "fixture_boundary")
ISSUER = FINANCIAL["run"]["issuer_name"]
FIG = re.compile(r"\{\{FIG:([a-z_]+)\|([^}]*)\}\}")
REF = re.compile(r"\{([A-Za-z0-9][A-Za-z0-9_.:-]*)\|([^}]*)\}")


@pytest.mark.parametrize("path", PINNED)
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
    return cp2h.Cp2gMetrics.select(_cp2g_fact(r) for r in head["facts"])


def _input(input_id: str, status: Any) -> Input:
    return Input(input_id=input_id, sha256=_digest(f"stage1 stand-in {input_id}"), status=status)


BOUND = (
    _input("prepared-pack", "accepted"),
    _input("CP-0", "restricted"),
    _input("CP-1", "restricted"),
    _input("CP-2G", "restricted"),
)


def upstream(
    cp2g_case: str,
    current: tuple[Input, ...] | str | None = None,
    cp1: tuple[Fact, ...] | None = None,
    bound: tuple[Input, ...] = BOUND,
) -> cp2h.TriggerUpstream:
    return cp2h.TriggerUpstream(
        bound=bound,
        current=BOUND if current is None else current,
        cp1_facts=cp1_facts(cp2g_case) if cp1 is None else cp1,
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


def _with_cp2g(case: str, changes: Mapping[str, str]) -> cp2h.TriggerInputs:
    """The case's inputs with the named CP-2G facts unsettled: fact id -> status (the reason is
    a stand-in per fact)."""
    variant, cp2g_case = spec(case)
    metrics = cp2g_metrics(cp2g_case)
    facts = tuple(
        f.model_copy(
            update={"status": changes[f.fact_id], "amount": None, "limitation": _why(f.fact_id)}
        )
        if f.fact_id in changes
        else f
        for f in metrics.facts
    )
    stream = cp2h.TriggerUpstream(
        bound=BOUND,
        current=BOUND,
        cp1_facts=cp1_facts(cp2g_case),
        cp2g=cp2h.Cp2gMetrics(facts=facts),
    )
    body = bind(raw_payload(case), fig_ids(stream.cp1_facts))
    submission = cp2h.TriggerSubmission.model_validate_json(json.dumps(body))
    return cp2h.TriggerInputs(pack(variant), stream, submission)


def _why(fact_id: str) -> str:
    return f"Not meaningful: a stand-in reason for {fact_id}"


def test_unsettled_cp2g_actual_keeps_its_status() -> None:
    """A CP-2G a25 ratio that is not applicable: the copy keeps CP-2G's status, limitation and
    the metric's unit (G-decisions); round 7 (f): the T2R.4 headroom and status take
    not_applicable too, with its limitation."""
    a25 = "T2H.6.a25.interest_coverage"
    got = cp2h.compute(_with_cp2g("positive", {a25: "not_applicable"}))
    cells = {c.fact.fact_id: c.fact for c in got.cells}
    actual, head = cells["T2R.4.t02.actual"], cells["T2R.4.t02.headroom"]
    status = cells["T2R.4.t02.status"]
    assert (actual.status, actual.unit, actual.limitation) == (
        "not_applicable",
        "MULTIPLE",
        _why(a25),
    )
    assert (head.status, head.unit, head.limitation) == ("not_applicable", "MULTIPLE", _why(a25))
    assert (status.status, status.text, status.limitation) == ("not_applicable", None, _why(a25))
    assert cells["T2R.4.t02.check"].text == "Not compared"


def test_unsettled_cp2g_missing_actual_stays_missing() -> None:
    a25 = "T2H.6.a25.interest_coverage"
    got = cp2h.compute(_with_cp2g("positive", {a25: "missing"}))
    cells = {c.fact.fact_id: c.fact for c in got.cells}
    for field in ("actual", "headroom", "status"):
        fact = cells[f"T2R.4.t02.{field}"]
        assert (fact.status, fact.limitation) == ("missing", _why(a25)), field


def test_not_applicable_forecast_year() -> None:
    """Round 7 (f): a not_applicable CP-2G forecast ratio makes its T2R.5 year and the case's
    tightest not_applicable with its limitation; T2R.6 stays missing (Not calculable) and T2R.9
    counts it as not calculable."""
    b27 = "T2H.6.b27.fcf_to_debt"
    got = cp2h.compute(_with_cp2g("positive", {b27: "not_applicable"}))
    cells = {c.fact.fact_id: c.fact for c in got.cells}
    for field, unit in (("y2", "pp"), ("tightest", "pp"), ("tightest_year", None)):
        fact = cells[f"T2R.5.t03_base.{field}"]
        assert (fact.status, fact.unit, fact.limitation) == ("not_applicable", unit, _why(b27))
    assert [cells[f"T2R.5.t03_base.{y}"].status for y in ("y1", "y3")] == ["known", "known"]
    first = cells["T2R.6.t03.base_first"]
    assert (first.status, first.limitation) == ("missing", _why(b27))
    assert got.totals["not_calculable_base"] == ("t03",)
    assert cells["T2R.9.total.not_calculable_base"].amount == 1
    assert cp2h.NOT_CALCULABLE_LINE in got.own_limitations


# --- round 7 rulings: the states no frozen case reaches ---------------------------------------------


def _pages(variant: str) -> list[str]:
    return [p["text"] for p in _variant(variant)["pages"]]


def _ratings(pages: Sequence[str]) -> Source:
    return Source(
        source_id="ratings",
        name="Fixture",
        status="ready",
        sha256=_digest("\f".join(pages)),
        media_type="text/plain",
        spans=tuple(Span(locator=f"page:{n}", text=t) for n, t in enumerate(pages, 1)),
        extraction_status="complete",
    )


def _sources(case_inputs: cp2h.TriggerInputs, *ratings: Source) -> cp2h.TriggerInputs:
    """The inputs with the pack's agency source replaced (or left out)."""
    frozen = tuple(s for s in case_inputs.pack.sources if s.source_id != "ratings")
    the_pack = cp2h.PackScope(sources=(*frozen, *ratings), names=case_inputs.pack.names)
    return cp2h.TriggerInputs(the_pack, case_inputs.upstream, case_inputs.submission)


def _over(case_inputs: cp2h.TriggerInputs, pages: Sequence[str]) -> cp2h.TriggerInputs:
    """The inputs over a changed agency source; the analyst's citations follow its new hash."""
    old, new = cp2h.ratings_source(case_inputs.pack), _ratings(pages)
    assert old.sha256 is not None and new.sha256 is not None
    text = case_inputs.submission.model_dump_json().replace(old.sha256, new.sha256)
    moved = _sources(case_inputs, new)
    return cp2h.TriggerInputs(
        moved.pack, moved.upstream, cp2h.TriggerSubmission.model_validate_json(text)
    )


def _edited(variant: str, edits: Sequence[tuple[int, str, str]]) -> list[str]:
    pages = _pages(variant)
    for page, old, new in edits:
        assert pages[page].count(old) == 1, (page, old)
        pages[page] = pages[page].replace(old, new)
    return pages


CP1D_BOUND = (
    "CP-1D (earnings quality) is bound but not read in this version, so no earnings-quality "
    "adjustment is applied to the reported ratios."
)


@pytest.mark.parametrize("status", ["accepted", "restricted", "blocked"])
def test_bound_cp1d_settles(status: str) -> None:
    """Round 7 item 1: T2R.1 u_cp1d shows the bound Input's status, its other cells stay as
    pinned, and the CP-1D own line takes the bound frame in the same position."""
    bound = (*BOUND, _input("CP-1D", status))
    got = cp2h.compute(inputs("positive", bound=bound, current=bound))
    base = report("positive")
    changed = [
        a.fact.fact_id
        for a, b in zip(got.cells, base.cells, strict=True)
        if a.record() != b.record()
    ]
    assert changed == ["T2R.1.u_cp1d.status"]
    assert next(c for c in got.cells if c.fact.fact_id == changed[0]).fact.text == status
    want = list(EXPECTED["cases"]["positive"]["own_limitations"])
    assert want[7] == (
        "CP-1D (earnings quality) is not part of this run, so no earnings-quality adjustment is "
        "applied to the reported ratios."
    )
    want[7] = CP1D_BOUND
    assert list(got.own_limitations) == want
    assert (got.tables, got.claims) == (base.tables, base.claims)


def _not_ready(state: str, real: Source) -> tuple[Source, ...]:
    if state == "absent":
        return ()
    if state == "missing":
        return (Source(source_id="ratings", name=real.name, status="missing", limitation="Absent"),)
    unreadable = Source(
        source_id="ratings",
        name=real.name,
        status="unreadable",
        sha256=real.sha256,
        spans=real.spans,
        limitation="The agency source could not be read",
    )
    return (unreadable,)


@pytest.mark.parametrize("state", ["absent", "missing", "unreadable"])
def test_no_ready_ratings_source(state: str) -> None:
    """Round 7 item 2: an absent, missing or unreadable agency source gives `Rating register not
    found` alone, after the stale issues and before any parse."""
    case_inputs = inputs("positive")
    without = _sources(case_inputs, *_not_ready(state, cp2h.ratings_source(case_inputs.pack)))
    assert cp2h.validate(without) == ("Rating register not found",)
    with pytest.raises(ValueError, match="^Rating register not found$"):
        cp2h.compute(without)
    stale = (*BOUND[:3], _input("CP-2G", "blocked"))
    late = cp2h.TriggerInputs(without.pack, upstream("gap", current=stale), without.submission)
    sha = BOUND[3].sha256[:12]
    assert cp2h.validate(late) == (
        f"Stale input CP-2G: bound restricted {sha}, current blocked {sha}",
    )
    shape = cp2h.payload_issues(
        SUBMITTED["r06"]["payload_text"], pack=without.pack, upstream=without.upstream
    )
    assert shape == ("(root): Invalid JSON: key must be a string at line 1 column 2",)


def test_ratings_source_invariants() -> None:
    """Round 7 item 2: two agency sources, or a ready one without a hash, cannot happen
    (preparation, contracts); they stay invariant raises of plain ValueError."""
    case_inputs = inputs("positive")
    real = cp2h.ratings_source(case_inputs.pack)
    with pytest.raises(ValueError, match="more than one ratings source") as twice:
        cp2h.ratings_source(_sources(case_inputs, real, real).pack)
    unhashed = real.model_copy(update={"sha256": None})
    with pytest.raises(ValueError, match="ready ratings source has no sha256") as no_hash:
        cp2h.ratings_source(_sources(case_inputs, unhashed).pack)
    assert type(twice.value) is ValueError and type(no_hash.value) is ValueError


TERMS = "Agency  Direction  Metric  Comparison  Threshold"
ALDER_ROW = "Alder Ratings  Issuer rating  BB  Negative  2025-11-14"
BROOK_ROW = "Brook Credit  Issuer rating  Ba3  Stable  2025-10-02"
SOURCE_BREACHES: dict[str, tuple[list[tuple[int, str, str]], str]] = {
    # item 3: a terms header with no trigger row
    "terms_header_only": (
        [(2, TERMS + "\n", TERMS + "\nNo terms are published.\n")],
        "Trigger terms not found",
    ),
    # item 6: a withdrawn agency with trigger terms
    "unrated_agency_terms": ([(0, "Ba3  Stable", "Withdrawn  Stable")], "Trigger terms not found"),
    # (h): a term for an agency not in the register
    "unregistered_agency_terms": (
        [(2, "Brook Credit  Upgrade", "Zeta Ratings  Upgrade")],
        "Trigger terms not found",
    ),
    # item 8: the table rules
    "scale_position_not_whole": ([(1, "11  BB  Ba2", "11.5  BB  Ba2")], "Rating scale not found"),
    "scale_symbol_twice": ([(1, "13  B+  B1", "13  BB  B1")], "Rating scale not found"),
    "scale_position_twice": ([(1, "13  B+  B1", "11  B+  B1")], "Rating scale not found"),
    "register_date_not_iso": (
        [(0, "Negative  2025-11-14", "Negative  2025/11/14")],
        "Rating register not found",
    ),
    "register_date_not_on_calendar": (
        [(0, "Negative  2025-11-14", "Negative  2025-13-45")],
        "Rating register not found",
    ),
    "register_agency_twice": (
        [(0, BROOK_ROW, "Alder Ratings  Issuer rating  BB  Stable  2025-10-02")],
        "Rating register not found",
    ),
    "terms_direction_unknown": (
        [(2, "Brook Credit  Upgrade", "Brook Credit  Watch")],
        "Trigger terms not found",
    ),
    "terms_comparison_unknown": (
        [(2, "Total debt to EBITDA  Above", "Total debt to EBITDA  Over")],
        "Trigger terms not found",
    ),
    "threshold_form": ([(2, "Above  2.75x", "Above  2.75 times")], "Trigger terms not found"),
    # grammar-valid (`N.NNx`) with the wrong unit for a percent metric: the unit check refuses it
    "threshold_unit": ([(2, "Below  10.0%", "Below  10.00x")], "Trigger terms not found"),
    "term_twice": (
        [
            (
                2,
                "Upgrade  Net debt to EBITDA  Below  0.50x",
                "Downgrade  Net debt to EBITDA  Above  1.50x",
            )
        ],
        "Trigger terms not found",
    ),
    # item 8 order: headers, then scale rows, register rows, terms rows, then the agency rules
    "headers_before_rows": (
        [(1, "11  BB  Ba2", "11.5  BB  Ba2"), (2, TERMS, "Agency  Direction  Metric")],
        "Trigger terms not found",
    ),
    "scale_before_register": (
        [(1, "11  BB  Ba2", "11.5  BB  Ba2"), (0, "Negative  2025-11-14", "Negative  2025-13-45")],
        "Rating scale not found",
    ),
    "register_before_terms": (
        [
            (0, "Negative  2025-11-14", "Negative  2025-13-45"),
            (2, "Brook Credit  Upgrade", "Brook Credit  Watch"),
        ],
        "Rating register not found",
    ),
    "off_scale_before_terms": (
        [(0, "BB  Negative", "CCC  Negative"), (2, "Brook Credit  Upgrade", "Brook Credit  Watch")],
        "Rating not on the scale: Alder Ratings CCC",
    ),
    "terms_rows_before_agency_rules": (
        [
            (2, "Alder Ratings  Downgrade  Total debt", "Zeta Ratings  Downgrade  Total debt"),
            (2, "Upgrade  Net debt to EBITDA", "Upgrade  Funds from operations to debt"),
        ],
        "Unrecognised trigger metric: Funds from operations to debt",
    ),
}


@pytest.mark.parametrize("breach", SOURCE_BREACHES)
def test_source_breaches_refuse_alone(breach: str) -> None:
    """Round 7 items 3, 6, 8 and (h): each breach gives its table's pinned text alone, at parse,
    the first failure in the ruled order; the attempt gets that one issue."""
    edits, issue = SOURCE_BREACHES[breach]
    pages = _edited("positive", edits)
    with pytest.raises(cp2h.SourceIssue, match=f"^{re.escape(issue)}$"):
        cp2h.parse_ratings(pages)
    assert cp2h.validate(_over(inputs("positive"), pages)) == (issue,)


def test_term_block_ends_at_the_first_short_line() -> None:
    """The pinned parse rule: a block ends at the first line of zero or one field; later lines of
    zero or one field are notes, not rows (gap page:1 relies on it). A later row-shaped line
    breaches the block (round 12 B8, `B8_BREACHES`)."""
    pages = _edited(
        "positive", [(2, "Below  0.50x", "Below  0.50x\nEnd of terms.\n  \nSee page:1.")]
    )
    assert len(cp2h.parse_ratings(pages).triggers) == 5


T2R8_COLUMNS = [
    ("first_agency", "First agency"),
    ("second_agency", "Second agency"),
    ("notches", "Notches apart"),
    ("lower_rated", "Lower rated"),
    ("outlook_match", "Outlooks"),
]
T2R10_COLUMNS = [
    ("id", "Gap id"),
    ("gap", "Gap"),
    ("why_it_matters", "Why it matters"),
    ("affected_analysis", "Affected analysis"),
    ("severity", "Severity"),
    ("action", "Action"),
]


def _columns(got: cp2h.TriggerReport, table: str) -> list[tuple[str, str]]:
    found = next(t for t in got.tables if t.table_id == table)
    return [(c.field, c.label) for c in found.columns]


def test_fixed_columns_match_the_facts() -> None:
    """The fixed T2R.8 and T2R.10 columns are the columns of their facts when rows exist."""
    got = report("positive")
    facts = {c.fact.fact_id: c.fact for c in got.cells}
    for table, want in (("T2R.8", T2R8_COLUMNS), ("T2R.10", T2R10_COLUMNS)):
        rows = next(t for t in got.tables if t.table_id == table).rows
        assert [(facts[f].field, facts[f].label) for f in rows[0].fact_ids] == want
        assert _columns(got, table) == want


def test_one_agency_register_settles() -> None:
    """Round 7 item 4: T2R.8 has zero rows and its fixed columns, no pair claim, and the own line
    `Only <agency> ...` sits after the withdrawn-agency lines, before NOT_CALCULABLE_LINE."""
    pages = _edited(
        "gap", [(0, "Brook Credit  Issuer rating  Withdrawn  Not applicable  2025-12-05\n", "")]
    )
    payload = copy.deepcopy(raw_payload("gap"))
    payload["views"] = [v for v in payload["views"] if v["agency"] == "Alder Ratings"]
    got = cp2h.compute(_over(inputs("gap", payload), pages))
    assert next(t for t in got.tables if t.table_id == "T2R.8").rows == ()
    assert _columns(got, "T2R.8") == T2R8_COLUMNS
    assert not [c for c in got.cells if c.fact.table_id == "T2R.8"]
    assert not [c for c in got.claims if c.claim_id.startswith("T2R.8")]
    validate_tables(got.tables, got.facts)
    want = list(EXPECTED["cases"]["gap"]["own_limitations"])
    withdrawn = (
        "Brook Credit's rating is withdrawn: no notch comparison is made and no trigger terms "
        "are published."
    )
    assert want.index(withdrawn) == want.index(cp2h.NOT_CALCULABLE_LINE) - 1
    want[want.index(withdrawn)] = (
        "Only Alder Ratings is in the rating register, so no notch comparison is made."
    )
    assert list(got.own_limitations) == want


def test_no_gap_settles() -> None:
    """Round 7 item 5: T2R.10 has zero rows and its fixed columns; nothing else changes and no
    own line is added."""
    payload = copy.deepcopy(raw_payload("positive"))
    payload["gaps"] = []
    got = cp2h.compute(inputs("positive", payload))
    base = report("positive")
    assert next(t for t in got.tables if t.table_id == "T2R.10").rows == ()
    assert _columns(got, "T2R.10") == T2R10_COLUMNS
    assert [c.record() for c in got.cells] == [
        c.record() for c in base.cells if c.fact.table_id != "T2R.10"
    ]
    assert list(got.own_limitations) == [
        x for x in base.own_limitations if not x.startswith("Gap (")
    ]
    assert got.claims == base.claims
    validate_tables(got.tables, got.facts)


PUBLISHED = "Published January 10, 2026.\n"
TERMS_PERIOD = "Terms publication date {}, tested at each fiscal year end"
REGISTER_PERIOD = "As of the rating register, publication date {}"
PERIOD_STATES = {
    "terms_not_stated": (2, "", "T2R.3", TERMS_PERIOD.format("not stated")),
    "terms_twice": (2, PUBLISHED * 2, "T2R.3", TERMS_PERIOD.format("unclear")),
    "terms_not_on_calendar": (
        2,
        "Published February 30, 2026.\n",
        "T2R.3",
        TERMS_PERIOD.format("unclear"),
    ),
    "register_not_stated": (0, "", "T2R.8", REGISTER_PERIOD.format("not stated")),
    "register_twice": (0, PUBLISHED * 2, "T2R.8", REGISTER_PERIOD.format("unclear")),
    "register_not_on_calendar": (
        0,
        "Published February 30, 2026.\n",
        "T2R.8",
        REGISTER_PERIOD.format("unclear"),
    ),
}


@pytest.mark.parametrize("state", PERIOD_STATES)
def test_publication_date_states(state: str) -> None:
    """Round 7 item 7: an absent Published line gives the `not stated` period frame, two lines
    or a date not on the calendar the `unclear` frame; no own line is added."""
    page, line, table, period = PERIOD_STATES[state]
    got = cp2h.compute(_over(inputs("positive"), _edited("positive", [(page, PUBLISHED, line)])))
    base = report("positive")
    field = "threshold" if table == "T2R.3" else "notches"
    dated = [c.fact for c in got.cells if c.fact.table_id == table and c.fact.field == field]
    assert dated and all(f.period == period for f in dated)
    others = [
        (a.fact.fact_id, a.fact.period)
        for a, b in zip(got.cells, base.cells, strict=True)
        if a.fact.period != b.fact.period
    ]
    assert sorted(fid for fid, _ in others) == sorted(f.fact_id for f in dated)
    assert got.own_limitations == base.own_limitations


def test_limitations_get_the_prose_check() -> None:
    """Round 7 (d): a view or overall limitation gets `prose.check` with no resolvable reference
    and the pack's names, prefixed with its path, then the phrase guard."""
    payload = copy.deepcopy(raw_payload("positive"))
    payload["views"][0]["limitation"] = "Headroom of 2.75x is thin."
    payload["views"][1]["limitation"] = "See {T2R.4.t01.headroom|x}; it will be downgraded."
    payload["overall"]["limitation"] = "Unbalanced {T2R.4.t01.headroom|x and more."
    assert cp2h.validate(inputs("positive", payload)) == (
        "views[0].limitation: Bare figure: 2.75x",
        "views[1].limitation: Unresolved reference: T2R.4.t01.headroom",
        'views[1].limitation: prohibited conclusion (rating call): "will be downgraded"',
        "overall.limitation: Malformed run text: unbalanced or empty reference",
    )


def test_limitation_check_reads_the_pack_names() -> None:
    payload = copy.deepcopy(raw_payload("positive"))
    payload["overall"]["limitation"] = "Agency 7 Holdings is not covered."
    case_inputs = inputs("positive", payload)
    named = cp2h.PackScope(case_inputs.pack.sources, (*case_inputs.pack.names, "Agency 7 Holdings"))
    assert (
        cp2h.validate(cp2h.TriggerInputs(named, case_inputs.upstream, case_inputs.submission)) == ()
    )
    assert cp2h.validate(case_inputs) == ("overall.limitation: Bare figure: 7",)


def test_empty_rationale_is_refused_when_blank() -> None:
    """`empty text` covers a whitespace-only rationale as well as an empty one (v10)."""
    payload = copy.deepcopy(raw_payload("positive"))
    payload["views"][1]["rationale"] = "  \n "
    assert cp2h.validate(inputs("positive", payload)) == ("views[1].rationale: empty text",)


def test_input_selection_fails_closed() -> None:
    facts = cp1_facts("gap")
    with pytest.raises(ValueError, match="exactly one"):
        cp2h.select_cp1(
            (*facts, facts[0].model_copy(update={"fact_id": "interface-fact:duplicate"}))
        )
    metrics = cp2g_metrics("gap")
    with pytest.raises(ValueError, match="exactly one"):
        cp2h.Cp2gMetrics.select(metrics.facts[1:])
    with pytest.raises(ValueError, match="28 T2H.6 facts"):
        cp2h.Cp2gMetrics(facts=tuple(reversed(metrics.facts)))


# --- fix round 1 (review-adversary F1-F4) -----------------------------------------------------------

TL_TERM, FCF_TERM = "Above  2.75x", "Below  10.0%"
THRESHOLD_FORMS = {
    "multiple_no_point": (TL_TERM, "Above  4x"),
    "multiple_one_place": (TL_TERM, "Above  2.7x"),
    "multiple_three_places": (TL_TERM, "Above  2.755x"),
    "percent_no_point": (FCF_TERM, "Below  10%"),
    "percent_two_places": (FCF_TERM, "Below  10.05%"),
    "percent_many_places": (FCF_TERM, "Below  1.23456789012345678901234567891%"),
    "multiple_no_integer": (TL_TERM, "Above  .75x"),
    "percent_no_integer": (FCF_TERM, "Below  .5%"),
    "minus": (TL_TERM, "Above  -2.75x"),
    "percent_minus": (FCF_TERM, "Below  -10.0%"),
    "plus": (TL_TERM, "Above  +2.75x"),
    "comma": (TL_TERM, "Above  2,75x"),
    "fullwidth": (TL_TERM, "Above  ２.７５x"),
}


@pytest.mark.parametrize("form", THRESHOLD_FORMS)
def test_threshold_grammar(form: str) -> None:
    """F1 (questions.md Q1): the manifest parse rule's `N.NNx` and `N.N%` only; any other form,
    a sign included, is `Trigger terms not found`."""
    old, new = THRESHOLD_FORMS[form]
    with pytest.raises(cp2h.SourceIssue, match="^Trigger terms not found$"):
        cp2h.parse_ratings(_edited("positive", [(2, old, new)]))


def test_percent_threshold_is_an_exact_shift() -> None:
    """F3 (Q2): a percent threshold becomes a fraction by an exact exponent shift; a value longer
    than the default 28-digit context is not rounded."""
    pages = _edited("positive", [(2, FCF_TERM, "Below  1234567890123456789012345678.9%")])
    term = next(t for t in cp2h.parse_ratings(pages).triggers if t.metric.startswith("Free"))
    assert term.threshold == Decimal("12345678901234567890123456.789")
    assert cp2h.exact_text(term.threshold) == "12345678901234567890123456.789"


def test_scale_position_sign_is_refused() -> None:
    """F4 C46: a signed scale position is not a whole number."""
    with pytest.raises(cp2h.SourceIssue, match="^Rating scale not found$"):
        cp2h.parse_ratings(_edited("positive", [(1, "11  BB  Ba2", "-11  BB  Ba2")]))


def test_issue_order_on_one_payload() -> None:
    """F2: round 7 (a) on one payload with several issues per view: views in register order,
    unknown agencies last by submission index; within a view agency, confidence, rationale,
    evidence, limitation; then the missing views; overall rationale, High, limitation; gaps."""
    payload = copy.deepcopy(raw_payload("positive"))
    alder = payload["views"][0]
    zeta, yota = copy.deepcopy(alder), copy.deepcopy(alder)
    zeta["agency"], yota["agency"] = "Zeta Ratings", "Yota Ratings"
    for v in (alder, zeta, yota):
        v["confidence"] = "High"
        v["rationale"] = "Headroom is 2.75x today."
        v["evidence"] = [dict(v["evidence"][0], quote="not on the page")]
        v["limitation"] = "Limit 9 applies."
    payload["views"] = [zeta, alder, yota]  # Brook Credit has no view
    payload["overall"].update(
        confidence="High", rationale="Overall 3.1x.", limitation="Overall limit 4."
    )
    payload["gaps"][0]["gap"] = "Gap 5x."
    issues = cp2h.validate(inputs("positive", payload))
    view = ("confidence", "rationale", "evidence[0]", "limitation")
    assert [i.split(":", 1)[0] for i in issues] == [
        *(f"views[1].{f}" for f in view),
        "views[0].agency",
        *(f"views[0].{f}" for f in view),
        "views[2].agency",
        *(f"views[2].{f}" for f in view),
        "views",
        "overall.rationale",
        "overall.confidence",
        "overall.limitation",
        "gaps[0].gap",
    ]
    assert issues[4] == "views[0].agency: not an agency in the rating register: Zeta Ratings"
    assert issues[14] == "views: no view for agency Brook Credit"


def test_unsettled_reasons_take_the_first_year() -> None:
    """F4 C25, C26: the tightest headroom and year take the first unsettled year's reason and
    status (lease T2R.5, round 7 (f)); T2R.6 the first unknown year's reason, status missing."""
    b26, b28 = "T2H.6.b26.fcf_to_debt", "T2H.6.b28.fcf_to_debt"
    for first, last in (("missing", "not_applicable"), ("not_applicable", "missing")):
        got = cp2h.compute(_with_cp2g("positive", {b26: first, b28: last}))
        cells = {c.fact.fact_id: c.fact for c in got.cells}
        for field in ("tightest", "tightest_year"):
            fact = cells[f"T2R.5.t03_base.{field}"]
            assert (fact.status, fact.limitation) == (first, _why(b26)), (first, field)
        fact = cells["T2R.6.t03.base_first"]
        assert (fact.status, fact.limitation) == ("missing", _why(b26)), first


def test_root_reason_puts_the_threshold_first() -> None:
    """F4 C27: an unstated threshold is the root reason even when the CP-2G ratio is unsettled;
    the T2R.4 copy keeps CP-2G's own reason."""
    a25, d27 = "T2H.6.a25.fcf_to_debt", "T2H.6.d27.fcf_to_debt"
    got = cp2h.compute(_with_cp2g("gap", {a25: "missing", d27: "not_applicable"}))
    cells = {c.fact.fact_id: c.fact for c in got.cells}
    assert cells["T2R.4.t03.actual"].limitation == _why(a25)
    for fact_id in ("T2R.4.t03.headroom", "T2R.5.t03_down.y2", "T2R.6.t03.down_first"):
        assert (cells[fact_id].status, cells[fact_id].limitation) == (
            "missing",
            cp2h.THRESHOLD_NS,
        ), fact_id


def test_publication_dates_are_read_from_the_lines() -> None:
    """F4 G1, round 7 (g): another valid date reaches the T2R.3 and T2R.8 periods."""
    pages = _edited(
        "positive",
        [
            (2, PUBLISHED, "Published March 3, 2026.\n"),
            (0, PUBLISHED, "Published February 29, 2024.\n"),
        ],
    )
    got = cp2h.compute(_over(inputs("positive"), pages))
    periods = {
        (c.fact.table_id, c.fact.period)
        for c in got.cells
        if (c.fact.table_id, c.fact.field) in (("T2R.3", "threshold"), ("T2R.8", "notches"))
    }
    assert periods == {
        ("T2R.3", "Terms published 2026-03-03, tested at each fiscal year end"),
        ("T2R.8", "As of 2024-02-29"),
    }


def test_input_invariants() -> None:
    """C47: a CP-2G fact with another unit fails; C48: the CP-1 selection reads table T4.10 only."""
    metrics = cp2g_metrics("gap")
    wrong = tuple(
        f.model_copy(update={"unit": "PERCENT"}) if f.fact_id == "T2H.6.a25.total_leverage" else f
        for f in metrics.facts
    )
    with pytest.raises(ValueError, match="unexpected unit or period"):
        cp2h.Cp2gMetrics(facts=wrong)
    facts = cp1_facts("gap")
    other = facts[0].model_copy(update={"fact_id": "interface-fact:other", "table_id": "T4.9"})
    assert cp2h.select_cp1((*facts, other))[facts[0].row_id] == facts[0]


# --- fix round 1 part b (LEAD round 11 B2, B3; controller B5, B6) -------------------------------

FCF_ROW = "Alder Ratings  Downgrade  Free cash flow to total debt  Below  10.0%"
BLOCK_BREACHES: dict[str, tuple[list[tuple[int, str, str]], str]] = {
    "terms_four_fields": (
        [(2, FCF_ROW, "Alder Ratings  Downgrade  Free cash flow to total debt  Below")],
        "Trigger terms not found",
    ),
    "terms_six_fields": ([(2, FCF_ROW, FCF_ROW + "  sustained")], "Trigger terms not found"),
    "terms_split_metric": (
        [(2, FCF_ROW, "Alder Ratings  Downgrade  Free cash flow  to total debt  Below  10.0%")],
        "Trigger terms not found",
    ),
    "terms_first_line": (
        [(2, TERMS + "\n", TERMS + "\nNo terms  this year\n")],
        "Trigger terms not found",
    ),
    "register_four_fields": (
        [(0, ALDER_ROW, "Alder Ratings  Issuer rating  BB  Negative")],
        "Rating register not found",
    ),
    "scale_two_fields": ([(1, "11  BB  Ba2", "11  BB")], "Rating scale not found"),
    # item 8 order: the scale rows step before the register rows, the register before the terms
    "scale_breach_before_register_breach": (
        [
            (1, "11  BB  Ba2", "11  BB"),
            (0, ALDER_ROW, "Alder Ratings  Issuer rating  BB  Negative"),
        ],
        "Rating scale not found",
    ),
    "register_breach_before_terms_breach": (
        [
            (0, ALDER_ROW, "Alder Ratings  Issuer rating  BB  Negative"),
            (2, FCF_ROW, FCF_ROW + "  x"),
        ],
        "Rating register not found",
    ),
    "off_scale_before_terms_breach": (
        [(0, "BB  Negative", "CCC  Negative"), (2, FCF_ROW, FCF_ROW + "  x")],
        "Rating not on the scale: Alder Ratings CCC",
    ),
}


@pytest.mark.parametrize("breach", BLOCK_BREACHES)
def test_block_row_breach_refuses(breach: str) -> None:
    """Round 11 B2: after a header, a line of two or more fields that is not the block's width
    makes the source invalid with that block's text alone, at the block's rows step; a later
    published term is never dropped silently."""
    edits, issue = BLOCK_BREACHES[breach]
    pages = _edited("positive", edits)
    with pytest.raises(cp2h.SourceIssue, match=f"^{re.escape(issue)}$"):
        cp2h.parse_ratings(pages)
    assert cp2h.validate(_over(inputs("positive"), pages)) == (issue,)


def test_one_field_line_ends_a_block() -> None:
    """Round 11 B2: a line of zero or one field ends the block (gap page:1's withdrawal note).
    A row after that line breaches the block (round 12 B8, `scale_blank_line`)."""
    assert len(cp2h.parse_ratings(_pages("gap")).register) == 2


# --- round 12 B8: nothing row-shaped after a block end -------------------------------------------

REGISTER = cp2h.REGISTER_HEADER
SCALE = cp2h.SCALE_HEADER
LAST_TERM = "Brook Credit  Upgrade  Net debt to EBITDA  Below  0.50x"
B8_BREACHES: dict[str, tuple[list[tuple[int, str, str]], str]] = {
    # "The lane today": each composed with fewer triggers before B8
    "terms_blank_line": ([(2, FCF_ROW, "\n" + FCF_ROW)], "Trigger terms not found"),
    "terms_whitespace_line": ([(2, FCF_ROW, "  \n" + FCF_ROW)], "Trigger terms not found"),
    "terms_single_tab_row": (
        [(2, FCF_ROW, "\t".join(FCF_ROW.split("  ")))],
        "Trigger terms not found",
    ),
    "terms_single_space_row": (
        [(2, FCF_ROW, " ".join(FCF_ROW.split("  ")))],
        "Trigger terms not found",
    ),
    "terms_second_header": (
        [
            (
                2,
                LAST_TERM,
                f"{LAST_TERM}\n\n{TERMS}\nBrook Credit  Downgrade  Total debt to EBITDA  Above  3.00x",
            )
        ],
        "Trigger terms not found",
    ),
    "terms_note_then_row": (
        [(2, LAST_TERM, f"{LAST_TERM}\nEnd of terms.\nZeta  Watch  X  Over  1x")],
        "Trigger terms not found",
    ),
    # any later line on the page, not only the next; two fields are already row-shaped
    "terms_row_lines_after_the_end": (
        [(2, LAST_TERM, f"{LAST_TERM}\n\nEnd of terms.\n\nZeta  Watch  X  Over  1x")],
        "Trigger terms not found",
    ),
    "terms_two_fields_after_the_end": (
        [(2, LAST_TERM, f"{LAST_TERM}\nEnd of terms.\nSee  page:1")],
        "Trigger terms not found",
    ),
    # each block's own text
    "scale_blank_line": ([(1, "\n12  BB-  Ba3", "\n\n12  BB-  Ba3")], "Rating scale not found"),
    "register_blank_line": (
        [(0, "\n" + BROOK_ROW, "\n\n" + BROOK_ROW)],
        "Rating register not found",
    ),
    # a header followed at once by an end line, then rows: breached at the rows step, not empty
    # at the header step (an empty terms block would give its text before the scale rows)
    "terms_header_then_end_line": (
        [(2, TERMS + "\n", TERMS + "\n\n"), (1, "11  BB  Ba2", "11  BB")],
        "Rating scale not found",
    ),
    "register_header_then_end_line": (
        [(0, REGISTER + "\n", REGISTER + "\n\n"), (1, "11  BB  Ba2", "11  BB")],
        "Rating scale not found",
    ),
    "scale_header_then_end_line": (
        [(1, SCALE + "\n", SCALE + "\n\n"), (2, TERMS + "\n", "Terms follow.\n")],
        "Trigger terms not found",
    ),
    # item 8 order: scale rows, register rows, terms rows
    "scale_b8_before_register_b8": (
        [(1, "\n12  BB-  Ba3", "\n\n12  BB-  Ba3"), (0, "\n" + BROOK_ROW, "\n\n" + BROOK_ROW)],
        "Rating scale not found",
    ),
    "register_b8_before_terms_b8": (
        [(0, "\n" + BROOK_ROW, "\n\n" + BROOK_ROW), (2, FCF_ROW, "\n" + FCF_ROW)],
        "Rating register not found",
    ),
}


@pytest.mark.parametrize("breach", B8_BREACHES)
def test_row_after_a_block_end_breaches(breach: str) -> None:
    """Round 12 B8: after a block ends at a line of zero or one field, a later line of two or
    more fields on that page breaches the block: its pinned text alone, at its rows step, in
    item 8's order. No published term is dropped silently."""
    edits, issue = B8_BREACHES[breach]
    pages = _edited("positive", edits)
    with pytest.raises(cp2h.SourceIssue, match=f"^{re.escape(issue)}$"):
        cp2h.parse_ratings(pages)
    assert cp2h.validate(_over(inputs("positive"), pages)) == (issue,)


def test_header_then_end_line_alone_reads_as_no_header() -> None:
    """Round 12 B8: a header followed by an end line and nothing row-shaped stays `empty`, so it
    gives the block's text at the header step, as round 7 item 3 (before the scale rows)."""
    pages = _edited("positive", [(1, "11  BB  Ba2", "11  BB")])
    pages[2] = pages[2].split(TERMS)[0] + TERMS + "\n\nNone are published."
    with pytest.raises(cp2h.SourceIssue, match="^Trigger terms not found$"):
        cp2h.parse_ratings(pages)


def test_malformed_last_row_is_the_known_limit() -> None:
    """Accepted known limit (round 12 B8, "Known limit"): a malformed LAST row (single tabs or
    single spaces) cannot be told from a one-field note under the pinned `\\s{2,}` grammar, so it
    still ends the block and is dropped (4 of 5 terms). Closing it would move `parse_rule`; the
    limit is recorded in `methods/cp2h.md` (Stage 2 note)."""
    for sep in ("\t", " "):
        pages = _edited("positive", [(2, LAST_TERM, sep.join(LAST_TERM.split("  ")))])
        assert len(cp2h.parse_ratings(pages).triggers) == 4, repr(sep)


def test_blank_limitation_is_refused() -> None:
    """Round 11 B3: a non-null blank limitation gets the v10 frame; null is no limitation."""
    payload = copy.deepcopy(raw_payload("positive"))
    payload["views"][0]["limitation"] = "  \n"
    payload["views"][1]["limitation"] = None
    payload["overall"]["limitation"] = ""
    assert cp2h.validate(inputs("positive", payload)) == (
        "views[0].limitation: empty text",
        "overall.limitation: empty text",
    )


# --- round 12 B10: the shared blank-text class over every analyst text field -------------------

# (issue path, payload keys): every analyst text field of the submission. `agency` is a register
# key, not text: any value off the register is refused as `not an agency in the rating register`.
BLANK_FIELDS: tuple[tuple[str, tuple[str | int, ...]], ...] = (
    *(
        (f"views[{i}].{name}", ("views", i, name))
        for i in (0, 1)
        for name in ("rationale", "limitation")
    ),
    ("overall.rationale", ("overall", "rationale")),
    ("overall.limitation", ("overall", "limitation")),
    *(
        (f"gaps[0].{name}", ("gaps", 0, name))
        for name in ("gap", "why_it_matters", "affected_analysis", "action")
    ),
)


def _blank_adapter(keys: tuple[str | int, ...]) -> Adapter:
    """(page, quote, value) -> the positive case's issues with `value` in the field at `keys`
    (the fields sit beside no quote, so page and quote are unused)."""

    def adapter(page: str, quote: str, value: str) -> Sequence[str]:
        payload = copy.deepcopy(raw_payload("positive"))
        node: Any = payload
        for key in keys[:-1]:
            node = node[key]
        node[keys[-1]] = value
        return cp2h.validate(inputs("positive", payload))

    return adapter


def test_blank_fields_cover_every_analyst_text_field() -> None:
    models = (("views", cp2h.AgencyView), ("overall", cp2h.Overall), ("gaps", cp2h.SynthesisGap))
    text = {
        (where, name)
        for where, model in models
        for name, info in model.model_fields.items()
        if info.annotation in (str, str | None) and name != "agency"
    }
    assert {(keys[0], keys[-1]) for _, keys in BLANK_FIELDS} == text


@pytest.mark.parametrize("field", BLANK_FIELDS, ids=lambda f: f[0])
@pytest.mark.parametrize("blank", BLANK_CASES, ids=lambda c: c.case_id)
def test_blank_text_is_refused(blank: BlankCase, field: tuple[str, tuple[str | int, ...]]) -> None:
    """Round 11 blank class and round 12 B10: whitespace and Unicode `Cf` text alike get CP-2H's
    pinned frame `<path>: empty text` at the field's existing blank check."""
    path, keys = field
    failure = blank_failure(blank, _blank_adapter(keys), EMPTY_TEXT.format(path=path))
    assert failure is None, failure


@pytest.mark.parametrize("field", BLANK_FIELDS, ids=lambda f: f[0])
def test_blank_text_twin_is_accepted(field: tuple[str, tuple[str | int, ...]]) -> None:
    """The twin: a field holding a word next to a format character is not blank (`a\\u200b`)."""
    path, keys = field
    issues = _blank_adapter(keys)("", "", "Read from the agency source.\u200b")
    assert EMPTY_TEXT.format(path=path) not in issues, issues


def test_upstream_statuses_are_the_bound_inputs() -> None:
    """B5 (lease :123, round 7 item 1): every T2R.1 status is its bound Input's status."""
    bound = (*BOUND[:2], _input("CP-1", "accepted"), _input("CP-2G", "blocked"))
    got = cp2h.compute(inputs("positive", bound=bound, current=bound))
    cells = {c.fact.fact_id: c.fact for c in got.cells}
    assert [cells[f"T2R.1.{r}.status"].text for r in ("u_cp1", "u_cp2g", "u_cp1d")] == [
        "accepted",
        "blocked",
        "not part of this run",
    ]


def test_frozen_composer_only_cp2g_status() -> None:
    """B7 (round 12): `cases.fixture_total_loss` pins `T2R.1.u_cp2g.status` as the bound CP-2G
    Input's status, `restricted`, no longer CP-2G's head status `composer_only`."""
    want = next(
        f
        for f in EXPECTED["cases"]["fixture_total_loss"]["facts"]
        if f["fact_id"] == "T2R.1.u_cp2g.status"
    )
    assert want["text"] == want["shown"] == "restricted"
    got = next(c for c in report("fixture_total_loss").cells if c.fact.fact_id == want["fact_id"])
    _assert_cell(got, want)


def test_upstream_status_needs_a_bound_input() -> None:
    with pytest.raises(ValueError, match="CP-2G is not bound"):
        cp2h.compute(inputs("positive", bound=BOUND[:3], current=BOUND[:3]))


def test_stale_issue_order_and_wording() -> None:
    """B6 (lease :107): every changed input in bound order, then those only current; an unbound
    or vanished input reads `absent`; a refused current binding is its text."""
    changed_cp0, changed_cp1 = (
        _input("CP-0", "blocked"),
        Input(input_id="CP-1", sha256=_digest("new CP-1"), status="restricted"),
    )
    cp1d = _input("CP-1D", "accepted")
    current = (cp1d, changed_cp1, BOUND[0], changed_cp0)  # CP-2G vanished; CP-1D appeared
    sha = {i.input_id: i.sha256[:12] for i in (*BOUND, cp1d)}
    sha["new"] = changed_cp1.sha256[:12]
    assert cp2h.stale_issues(bound=BOUND, current=current) == (
        f"Stale input CP-0: bound restricted {sha['CP-0']}, current blocked {sha['CP-0']}",
        f"Stale input CP-1: bound restricted {sha['CP-1']}, current restricted {sha['new']}",
        f"Stale input CP-2G: bound restricted {sha['CP-2G']}, current absent",
        f"Stale input CP-1D: bound absent, current accepted {sha['CP-1D']}",
    )
    refused = "the CP-2G head is not settled"
    assert cp2h.stale_issues(bound=BOUND, current=refused) == (f"Stale inputs: {refused}",)
    stream = upstream("gap", current=refused)
    case_inputs = inputs("positive")
    late = cp2h.TriggerInputs(case_inputs.pack, stream, case_inputs.submission)
    assert cp2h.validate(late) == (f"Stale inputs: {refused}",)


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
