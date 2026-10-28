"""CP-4 Stage 1: the calculation (semantic gate + cp4_legal composer) against the frozen oracle.

Every expected value comes from `cases/cp4-owner/expected.json`; the inputs come from the frozen
manifests and submissions. Stage 1 builds `cp4_legal.Upstream` here from oracle values (controller
ruling 2): CP-0 authority and legal sources, `cp4_step_view.expected_values`, one CP-1 fact from
`figures.predicate_facts` plus the financial `q4_ltm_metric_oracle`, and declared stand-in head
hashes. Nothing in `src` is a stand-in; `cp4_upstream` over real CP-0/CP-1 heads is Stage 2.
"""

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from deploy_vii import cp4_legal
from deploy_vii.business_context import referencable
from deploy_vii.contracts import Citation, Fact, Input, ReportTable, Run, Source, Span
from deploy_vii.preparation import PreparedPack
from deploy_workflow.owners import cp4

ROOT = Path(__file__).parents[1]
CASE = ROOT / "cases/cp4-owner"
PINNED = {
    "manifest.json": "2c12bf6836f54b704201af217866002d279b51cd8f1ed6094154aec9198f6b23",
    "submissions.json": "f2ef2e30d3541e3a72a2337ca6cec9c9396a364f61398057cc45172a6fce9461",
    "expected.json": "a60ab627d353eeb8871024e0efe664cce38322fcfa3edaf7ccda9f257fdc1423",
}
EXPECTED = json.loads((CASE / "expected.json").read_text())
MANIFEST = json.loads((CASE / "manifest.json").read_text())
SUBMISSIONS = json.loads((CASE / "submissions.json").read_text())
FINANCIAL = json.loads((ROOT / "cases/financial/manifest.json").read_text())
LEGAL = json.loads((ROOT / "cases/legal/manifest.json").read_text())

FIG = "<<FIG:net_leverage_reported>>"
FIGURE = EXPECTED["figures"]["net_leverage_reported"]
PREDICATE = FIGURE["predicate_facts"]
VIEW = EXPECTED["cp4_step_view"]
PACK_OF = {"positive": "positive", "gap": "gap", "gap_false_same_definition": "gap"}
RUN_OF = {"positive": "slice-legal-current-positive", "gap": "slice-legal-current-definition-gap"}

# Declared stand-ins (Stage 1 only; Stage 2 binds the real heads): CP-0/CP-1 head hashes, the
# CP-1 fact id and calculation id, the CP-1 row id, one CP-1 citation and the CP-1 limitations.
CP0_HEAD = hashlib.sha256(b"stage1 stand-in CP-0 head").hexdigest()
CP1_HEAD = hashlib.sha256(b"stage1 stand-in CP-1 head").hexdigest()
CP1_FACT_ID = "stage1-standin.T4.10.net_leverage_reported.ltm_q4_25"
CP1_CALCULATION_ID = "stage1-standin.calc.net_leverage_reported"
CP1_ROW_ID = "net_leverage_reported"
CP1_QUOTE = "Reporting basis: IFRS; entity perimeter: consolidated group."


def test_oracle_files_are_the_pinned_revision() -> None:
    for name, digest in PINNED.items():
        assert hashlib.sha256((CASE / name).read_bytes()).hexdigest() == digest, name


# --- inputs from the frozen manifests -------------------------------------------------------


def _frozen_pages() -> dict[str, list[dict[str, str]]]:
    """Pages of every frozen source by its sha256, raw rule checked (U+000C joins pages)."""
    found = [*FINANCIAL["sources"], *(c["legal_source"] for c in LEGAL["cases"])]
    pages: dict[str, list[dict[str, str]]] = {}
    for source in found:
        joined = "\f".join(page["text"] for page in source["pages"])
        assert hashlib.sha256(joined.encode("utf-8")).hexdigest() == source["sha256"]
        pages[source["sha256"]] = source["pages"]
    return pages


PAGES = _frozen_pages()


def make_pack(case: str) -> PreparedPack:
    entry = next(c for c in MANIFEST["cases"] if c["run"]["run_id"] == RUN_OF[PACK_OF[case]])
    sources = tuple(
        Source(
            source_id=item["source_id"],
            name=item["name"],
            status=item["status"],
            sha256=item["sha256"],
            spans=tuple(Span(**page) for page in PAGES[item["sha256"]]),
            extraction_status="complete",
            limitation=item["limitation"],
        )
        for item in entry["pack_sources"]
    )
    return PreparedPack(run=Run.model_validate_json(json.dumps(entry["run"])), sources=sources)


def cp1_fact() -> Fact:
    oracle = FINANCIAL["q4_ltm_metric_oracle"]["net_leverage_reported"]
    financial = next(s for s in FINANCIAL["sources"] if s["source_id"] == "financial")
    assert CP1_QUOTE in financial["pages"][0]["text"]
    return Fact(
        fact_id=CP1_FACT_ID,
        label=PREDICATE["label"],
        table_id=PREDICATE["table_id"],
        row_id=CP1_ROW_ID,
        field="ltm_q4_25",
        amount=Decimal(oracle["decimal"]),
        unit=oracle["unit"],
        period=PREDICATE["period"],
        basis=PREDICATE["basis_observed"],
        citations=(
            Citation(
                source_id="financial",
                source_sha256=financial["sha256"],
                locator="page:1",
                quote=CP1_QUOTE,
            ),
        ),
        calculation_id=CP1_CALCULATION_ID,
        value_class="calculated",
    )


def cp1_gaps(case: str) -> tuple[str, ...]:
    """Stand-in CP-1 head limitations: the CP-0 limitations CP-1 inherits (oracle values)."""
    return tuple(dict.fromkeys(EXPECTED[case]["CP-0"]["limitations"]))


def make_upstream(case: str) -> cp4_legal.Upstream:
    cp0 = EXPECTED[case]["CP-0"]
    values = VIEW["expected_values"]
    fact = cp1_fact()
    assert referencable((fact,)) == (fact,)
    return cp4_legal.Upstream(
        cp0_sha256=CP0_HEAD,
        cp1_sha256=CP1_HEAD,
        cp1_status=values["cp1_status"],
        authority=dict(cp0["T3_authority"]),
        legal_sources=tuple(cp0["legal_sources_for_cp4"]),
        facilities={f["facility_id"]: f["facility_name"] for f in values["facilities"]},
        facts=(fact,),
        rows={(fact.table_id, fact.row_id): "net_leverage_reported"},
        cp1_gaps=cp1_gaps(case),
    )


def make_inputs(case: str, pack: PreparedPack) -> tuple[Input, ...]:
    case = PACK_OF[case]
    status = {
        "prepared-pack": ("accepted", pack.content_hash()),
        "CP-0": (EXPECTED[case]["CP-0"]["status"], CP0_HEAD),
        "CP-1": (VIEW["expected_values"]["cp1_status"], CP1_HEAD),
    }
    order = EXPECTED[case]["CP-4"]["attempt_inputs_in_order"]
    return tuple(Input(input_id=i, status=status[i][0], sha256=status[i][1]) for i in order)


def select_metric(pack: PreparedPack, upstream: cp4_legal.Upstream) -> str:
    """The S1a rev 2 M2 predicate (`figures.predicate`): exactly one T4.10 fact with the frozen
    period and label, then its id offered in the context block with unit 'x', shown '1.00x'."""
    matches = [
        f
        for f in upstream.facts
        if f.table_id == PREDICATE["table_id"]
        and f.period == PREDICATE["period"]
        and f.label == PREDICATE["label"]
    ]
    if len(matches) != 1:
        raise LookupError(f"FIG predicate matched {len(matches)} CP-1 facts")
    ref = matches[0].fact_id
    offered = cp4_legal.context_block(pack, upstream)["cp1_facts"]
    assert isinstance(offered, list)
    row = next(item for item in offered if item["ref"] == ref)
    assert (row["unit"], row["shown"]) == (PREDICATE["unit_token"], PREDICATE["shown"])
    assert (row["unit"], row["shown"]) == (FIGURE["unit_token"], FIGURE["spelled"])
    return ref


def make_submission(
    case: str, pack: PreparedPack, upstream: cp4_legal.Upstream
) -> cp4_legal.CovenantInterpretationSubmission:
    raw = SUBMISSIONS[case]["legal_covenants"]
    text = json.dumps(raw).replace(FIG, select_metric(pack, upstream))
    return cp4_legal.CovenantInterpretationSubmission.model_validate_json(text)


def make_inputs_object(case: str) -> cp4.Cp4Inputs:
    pack = make_pack(case)
    upstream = make_upstream(PACK_OF[case])
    return cp4.Cp4Inputs(
        pack=pack,
        submission=make_submission(case, pack, upstream),
        upstream=upstream,
        inputs=make_inputs(case, pack),
    )


@pytest.fixture(scope="module")
def results() -> dict[str, tuple[cp4.Cp4Inputs, cp4.Cp4Result]]:
    out = {}
    for case in ("positive", "gap", "gap_false_same_definition"):
        inputs = make_inputs_object(case)
        out[case] = (inputs, cp4.compute(inputs))
    return out


# --- generic and run-time-bound cell comparison --------------------------------------------


def _cites(citations: Sequence[Citation]) -> list[list[str]]:
    return [[c.source_id, c.locator] for c in citations]


def _plain(fact: Fact, column: str) -> dict[str, Any]:
    return {
        "fact_id": fact.fact_id,
        "column": column,
        "text": fact.text,
        "status": fact.status,
        "cites": _cites(fact.citations),
        "value_class": fact.value_class,
        "limitation": fact.limitation,
    }


def _check_number(actual: Fact, want: Mapping[str, Any]) -> None:
    assert actual.amount is not None and actual.text is None
    assert actual.amount == Decimal(want["amount"])
    assert (actual.unit, actual.status, actual.value_class, actual.limitation) == (
        want["unit"],
        want["status"],
        want["value_class"],
        want["limitation"],
    )


def _check_metric_copy(actual: Fact, want: Mapping[str, Any], metric: Fact) -> None:
    """T4.9 Current and T4F.2: the CP-1 fact's value, period, basis and citations."""
    _check_number(actual, want)
    assert actual.amount == metric.amount and actual.unit == metric.unit
    assert (actual.period, actual.basis) == (metric.period, metric.basis)
    assert want["period"] == f"bound from the CP-1 fact ({metric.period})"
    assert want["basis"].startswith("bound from the CP-1 fact (")
    assert actual.citations == metric.citations
    assert want["note"] == FIGURE["cp1_coordinate"]


def _check_bound(
    table: str,
    field: str,
    actual: Fact,
    want: Mapping[str, Any],
    ctx: Mapping[str, Any],
) -> None:
    """The eleven run-time-bound cells, each by the oracle's own rule."""
    metric: Fact = ctx["metric"]
    if (table, field) == ("T4.9", "current"):
        _check_metric_copy(actual, want, metric)
        assert want["carries_cp1_fact_id"] is False
        assert actual.fact_id == want["fact_id"] != metric.fact_id
        assert want["carries_cp1_fact"]["label"] == f"{metric.label} (bound from the CP-1 fact)"
        assert actual.label == metric.label
        assert actual.calculation_id == metric.calculation_id is not None
    elif (table, field) in (("T4.9", "headroom"), ("T4.9", "headroom_share")):
        _check_number(actual, want)
        assert actual.fact_id == want.get("fact_id_template", want["fact_id"])
        formula = want["formula"].replace("<metric fact_id>", metric.fact_id)
        assert actual.formula == formula
        assert want["period"] == "= the metric's period" and actual.period == metric.period
        assert want["basis"] == "= the metric's basis" and actual.basis == metric.basis
        row_cites = tuple(ctx["row_citations"])
        assert actual.citations == tuple(dict.fromkeys((*row_cites, *metric.citations)))
    elif (table, field) == ("T4C.8", "cp_1_metric") or (table, field) == (
        "T4F.3",
        "metric_operand",
    ):
        assert want["text"] == f"{FIG} (the bound CP-1 fact id)"
        assert _plain(actual, want["column"]) == {**want, "text": metric.fact_id}
    elif (table, field) == ("T4C.8", "metric_period"):
        assert want["text"] == f"{metric.period} (bound from the CP-1 fact)"
        assert _plain(actual, want["column"]) == {**want, "text": metric.period}
    elif (table, field) == ("T4F.1", "sha_256"):
        assert want["text"] == "<<bound at run time: the head's result_sha256>>"
        sha = ctx["input_sha"][actual.row_id]
        assert _plain(actual, want["column"]) == {**want, "text": sha}
    else:
        raise AssertionError(f"unhandled run-time-bound cell {table}.{field}")


BOUND_CELLS = frozenset(
    {
        ("T4.9", "current"),
        ("T4.9", "headroom"),
        ("T4.9", "headroom_share"),
        ("T4C.8", "cp_1_metric"),
        ("T4C.8", "metric_period"),
        ("T4F.1", "sha_256"),
        ("T4F.3", "metric_operand"),
    }
)
_DECIMAL_NOTE = re.compile(r"^(\S+) \(Decimal equal to (\S+); exponent follows the CP-1 amount\)$")


def _is_bound(want: Mapping[str, Any]) -> bool:
    text = json.dumps(want, ensure_ascii=False)
    return "amount" in want or "<<" in text or "bound" in text


def _check_table(
    actual: ReportTable, want: Mapping[str, Any], facts: Mapping[str, Fact], ctx: Mapping[str, Any]
) -> int:
    """Compare one table; returns how many run-time-bound cells it checked."""
    assert actual.table_id == want["table_id"]
    assert actual.title == want["title"]
    assert actual.row_header == want["row_header"]
    assert [(c.field, c.label) for c in actual.columns] == [
        (c["field"], c["label"]) for c in want["columns"]
    ]
    labels = {c.field: c.label for c in actual.columns}
    metric: Fact = ctx["metric"]
    bound = 0
    if actual.table_id == "T4F.2":
        (row,) = want["rows"]
        (got,) = actual.rows
        assert row["label"].endswith(" (row label, then the CP-1 period)")
        assert got.row_id == row["row_id"]
        assert got.label == f"{ctx['metric_row']} · {metric.period}"
        assert row["label"] == f"{got.label} (row label, then the CP-1 period)"
        (cell,) = row["facts"]
        assert cell["copy_of_cp1_fact"] == FIG and cell["column"] == "Value"
        assert cell["fact_id"] == "the CP-1 fact's own fact_id (preserved)"
        (fact_id,) = got.fact_ids
        assert fact_id == metric.fact_id
        _check_metric_copy(facts[fact_id], cell, metric)
        return 1
    if actual.table_id == "T4F.5":
        (row,) = want["rows"]
        assert (row["row_id"], row["label"]) == ("r01..rN", "CP-1-GAP-001..NNN")
        assert row["facts"][0]["text"].startswith("<<CP-1 head: its limitations then")
        gaps = ctx["cp1_gaps"]
        assert [(r.row_id, r.label) for r in actual.rows] == [
            (f"r{i:02d}", f"CP-1-GAP-{i:03d}") for i in range(1, len(gaps) + 1)
        ]
        template = {k: v for k, v in row["facts"][0].items() if k not in ("fact_id", "text")}
        for got, gap in zip(actual.rows, gaps, strict=True):
            (fact_id,) = got.fact_ids
            assert _plain(facts[fact_id], "Gap") == {
                **template,
                "fact_id": f"T4F.5.{got.row_id}.gap",
                "text": gap,
            }
        return 1
    assert [(r.row_id, r.label) for r in actual.rows] == [
        (r["row_id"], r["label"]) for r in want["rows"]
    ]
    for got, row in zip(actual.rows, want["rows"], strict=True):
        assert len(got.fact_ids) == len(row["facts"])
        for field, fact_id, cell in zip(
            (c.field for c in actual.columns), got.fact_ids, row["facts"], strict=True
        ):
            fact = facts[fact_id]
            ctx_row = {**ctx, "row_citations": ctx["row_citations"].get(got.row_id, ())}
            # A bound coordinate may be a plain unsettled cell (gap headroom); the per-case
            # count in test_tables_equal_oracle pins how many are bound.
            if (actual.table_id, field) in BOUND_CELLS and _is_bound(cell):
                _check_bound(actual.table_id, field, fact, cell, ctx_row)
                bound += 1
                continue
            assert not _is_bound(cell), f"unhandled run-time-bound cell {fact_id}"
            note = _DECIMAL_NOTE.match(cell["text"] or "")
            if note:
                shown, equal = note.groups()
                assert fact.text == shown and Decimal(fact.text) == Decimal(equal)
                assert _plain(fact, labels[field]) == {**cell, "text": shown}
                continue
            assert _plain(fact, labels[field]) == cell
    return bound


def _ctx(inputs: cp4.Cp4Inputs) -> dict[str, Any]:
    metric = inputs.upstream.facts[0]
    return {
        "metric": metric,
        "metric_row": inputs.upstream.rows[(metric.table_id, metric.row_id)],
        "cp1_gaps": inputs.upstream.cp1_gaps,
        "input_sha": {item.input_id.lower(): item.sha256 for item in inputs.inputs},
        "row_citations": {
            f"r{i:02d}": tuple(
                Citation(
                    source_id=q.source_id,
                    source_sha256=next(
                        s.sha256 for s in inputs.pack.sources if s.source_id == q.source_id
                    ),
                    locator=q.locator,
                    quote=q.quote,
                )
                for q in c.citations
            )
            for i, c in enumerate(inputs.submission.covenants, 1)
        },
    }


# --- A1/A2: positive and gap packs ----------------------------------------------------------


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_tables_equal_oracle(
    case: str, results: dict[str, tuple[cp4.Cp4Inputs, cp4.Cp4Result]]
) -> None:
    inputs, result = results[case]
    assert result.issues == ()
    report = result.report
    assert report is not None
    want = EXPECTED[case]["CP-4"]
    assert [t.table_id for t in report.tables] == EXPECTED["table_order"]
    assert [t["table_id"] for t in want["tables"]] == EXPECTED["table_order"]
    facts = {f.fact_id: f for f in report.facts}
    assert len(facts) == len(report.facts)
    ctx = _ctx(inputs)
    bound = sum(
        _check_table(t, w, facts, ctx) for t, w in zip(report.tables, want["tables"], strict=True)
    )
    # Positive: T4.9 current/headroom/share, T4C.8 x2, T4F.1 x3, T4F.2, T4F.3, T4F.5 = 11.
    # Gap: headroom and share are plain missing cells, so 9.
    assert bound == (11 if case == "positive" else 9)


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_claims_and_limitations_equal_oracle(
    case: str, results: dict[str, tuple[cp4.Cp4Inputs, cp4.Cp4Result]]
) -> None:
    inputs, result = results[case]
    report = result.report
    assert report is not None
    want = EXPECTED[case]["CP-4"]
    got = [
        {
            "claim_id": c.claim_id,
            "text": c.text,
            "cites": _cites(c.citations),
            "limitation": c.limitation,
        }
        for c in report.claims
    ]
    assert got == want["claims"]
    assert list(report.limitations) == want["own_limitations"]
    module = cp4_legal.cp4_module(report, inputs.inputs, 0)
    assert [i.input_id for i in module.inputs] == want["settled_module_inputs"]
    assert [i.input_id for i in inputs.inputs] == want["attempt_inputs_in_order"]
    assert report.pack_sha256 == inputs.pack.content_hash()


def _fact(report: cp4_legal.CovenantInterpretationReport, fact_id: str) -> Fact:
    return next(f for f in report.facts if f.fact_id == fact_id)


def test_python_values_positive(
    results: dict[str, tuple[cp4.Cp4Inputs, cp4.Cp4Result]],
) -> None:
    inputs, result = results["positive"]
    report = result.report
    assert report is not None
    values = EXPECTED["positive"]["CP-4"]["python_values"]
    metric = values["metric_net_leverage_reported"]
    assert inputs.upstream.facts[0].amount == Decimal(metric["value"])
    parsed, _ = cp4_legal.parse_threshold("4.00x", values["threshold"]["unit"])
    assert parsed == Decimal(values["threshold"]["value"])
    assert _fact(report, "T4C.7.r01.parsed_value").text == values["threshold"]["value"]
    room = _fact(report, "T4.9.r01.headroom")
    share = _fact(report, "T4.9.r01.headroom_share")
    assert (room.amount, room.unit) == (Decimal(values["headroom"]["value"]), "MULTIPLE")
    assert (share.amount, share.unit) == (Decimal(values["headroom_share"]["value"]), "PERCENT")
    assert values["within"]["value"] is True
    assert _fact(report, "T4.9.r01.test_on_cp_1_metric").text == values["within"]["verdict"]
    assert _fact(report, "T4C.9.r01.calculable").text == values["T4C.9_calculable"]


def test_python_values_gap(results: dict[str, tuple[cp4.Cp4Inputs, cp4.Cp4Result]]) -> None:
    _, result = results["gap"]
    report = result.report
    assert report is not None
    values = EXPECTED["gap"]["CP-4"]["python_values"]
    assert values["headroom"] is None and values["headroom_share"] is None
    reason = f"{cp4_legal.NOT_CALCULABLE}: {values['reason']}"
    for field in ("headroom", "headroom_share"):
        fact = _fact(report, f"T4.9.r01.{field}")
        assert (fact.status, fact.amount, fact.text, fact.limitation) == (
            "missing",
            None,
            None,
            reason,
        )
    assert _fact(report, "T4.9.r01.test_on_cp_1_metric").text == values["verdict"]
    assert _fact(report, "T4C.9.r01.calculable").text == values["T4C.9_calculable"]
    assert _fact(report, "T4C.9.r01.reason").text == values["reason"]
    assert _fact(report, "T4.9.r01.threshold").text == values["threshold"]["display"]
    for fact in report.facts:
        for phrase in ("within threshold", "outside threshold", "zero headroom"):
            assert phrase not in (fact.text or "").casefold()


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_source_context_never_a_cell(
    case: str, results: dict[str, tuple[cp4.Cp4Inputs, cp4.Cp4Result]]
) -> None:
    _, result = results[case]
    report = result.report
    assert report is not None
    rule = EXPECTED[case]["CP-4"]["source_context_only"]
    forbidden = rule["must_not_appear_as_cell_values"]["values"]
    for fact in report.facts:
        if fact.amount is not None:
            assert all(fact.amount != Decimal(v) for v in forbidden), fact.fact_id
        if fact.text is not None:
            assert fact.text.strip() not in forbidden, fact.fact_id
    for row in ("r01", "r02", "r03"):
        cell = _fact(report, f"T4.10.{row}.capacity_amount")
        assert rule["capacity_amount"] is None
        assert (cell.status, cell.amount, cell.text, cell.limitation) == (
            "missing",
            None,
            None,
            rule["capacity_reason"],
        )


# --- A3/A3b: the semantic gate --------------------------------------------------------------


@pytest.mark.parametrize("case", ["positive", "gap", "gap_false_same_definition"])
def test_semantic_gate_per_case(case: str) -> None:
    gate = EXPECTED["semantic_gate"]
    want = gate["per_case"][case]
    inputs = make_inputs_object(case)
    (covenant,) = inputs.submission.covenants
    assert covenant.metric_basis == want["metric_basis"]
    assert list(cp4.markers_in_scope(inputs.pack, covenant)) == want["markers_matched_in_scope"]
    assert (
        list(cp4.semantic_issues(pack=inputs.pack, submission=inputs.submission))
        == (want["issues"])
    )
    assert list(cp4.MARKERS) == gate["markers"]
    assert not set(cp4.MARKERS) & set(gate["never_markers"])


def test_semantic_gate_scope_includes_cited_page_text() -> None:
    """Lease scope rule: the full text of every cited pack page is scanned, not only the quotes.
    The oracle cases cite the marker sentence itself, so drop that quote: page:2 is still cited
    and still carries both markers, so the frozen refusal string is unchanged."""
    inputs = make_inputs_object("gap_false_same_definition")
    (covenant,) = inputs.submission.covenants
    kept = tuple(
        q
        for q in covenant.citations
        if not any(m in q.quote for m in EXPECTED["semantic_gate"]["markers"])
    )
    assert 0 < len(kept) < len(covenant.citations)
    assert {(q.source_id, q.locator) for q in kept} == {("legal-covenants", "page:2")}
    variant = inputs.submission.model_copy(
        update={"covenants": (covenant.model_copy(update={"citations": kept}),)}
    )
    refusal = EXPECTED["gap_false_same_definition"]["CP-4"]["refusal"]
    assert list(cp4.semantic_issues(pack=inputs.pack, submission=variant)) == refusal["issues"]


def test_false_same_definition_refused_before_composition(
    results: dict[str, tuple[cp4.Cp4Inputs, cp4.Cp4Result]],
) -> None:
    _, result = results["gap_false_same_definition"]
    refusal = EXPECTED["gap_false_same_definition"]["CP-4"]["refusal"]
    assert list(result.issues) == refusal["issues"]
    assert result.report is None


def test_false_same_values_would_compose_without_the_gate(
    results: dict[str, tuple[cp4.Cp4Inputs, cp4.Cp4Result]],
) -> None:
    """The engine alone composes the values `semantic_acceptance` says must never settle; the
    gate is what refuses them (`engine_note`)."""
    inputs, _ = results["gap_false_same_definition"]
    must_not = EXPECTED["gap_false_same_definition"]["CP-4"]["semantic_acceptance"][
        "values_the_documented_rules_would_compose_from_these_inputs_and_that_must_not_qualify"
    ]
    report = cp4_legal.covenant_interpretation(
        inputs.pack, inputs.submission, inputs.upstream, inputs.inputs
    )
    room = _fact(report, "T4.9.r01.headroom")
    share = _fact(report, "T4.9.r01.headroom_share")
    assert f"{room.amount.normalize()} {room.unit}" == must_not["headroom"]
    assert f"{share.amount} {share.unit}" == must_not["headroom_share"]
    assert _fact(report, "T4.9.r01.test_on_cp_1_metric").text == must_not["verdict"]
    assert _fact(report, "T4C.9.r01.calculable").text == must_not["T4C.9_calculable"]


def test_corrected_resubmission_equals_gap(
    results: dict[str, tuple[cp4.Cp4Inputs, cp4.Cp4Result]],
) -> None:
    refused, _ = results["gap_false_same_definition"]
    corrected = cp4.Cp4Inputs(
        pack=refused.pack,
        submission=make_submission("gap", refused.pack, refused.upstream),
        upstream=refused.upstream,
        inputs=refused.inputs,
    )
    result = cp4.compute(corrected)
    assert result.issues == ()
    assert result.report == results["gap"][1].report


# --- calculation-level refusals and the context view ----------------------------------------


def test_unresolved_figure_placeholder_is_invalid() -> None:
    inputs = make_inputs_object("positive")
    raw = cp4_legal.CovenantInterpretationSubmission.model_validate_json(
        json.dumps(SUBMISSIONS["positive"]["legal_covenants"])
    )
    result = cp4.compute(
        cp4.Cp4Inputs(
            pack=inputs.pack, submission=raw, upstream=inputs.upstream, inputs=inputs.inputs
        )
    )
    assert result.report is None
    assert any(f"metric_ref {FIG} is not a CP-1 figure offered" in i for i in result.issues)


def test_figure_predicate_refuses_zero_or_several_candidates() -> None:
    pack = make_pack("positive")
    upstream = make_upstream("positive")
    alias = cp1_fact().model_copy(update={"fact_id": "stage1-standin.alias", "field": "alias"})
    several = cp4_legal.Upstream(**{**upstream.__dict__, "facts": (*upstream.facts, alias)})
    none = cp4_legal.Upstream(**{**upstream.__dict__, "facts": ()})
    for bad in (several, none):
        with pytest.raises(LookupError):
            select_metric(pack, bad)


def _shape(value: object) -> object:
    if isinstance(value, dict):
        return {k: _shape(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_shape(v) for v in value[:1]]
    return type(value).__name__


@pytest.mark.parametrize("case", ["positive", "gap"])
def test_context_block_matches_step_view(case: str) -> None:
    pack = make_pack(case)
    upstream = make_upstream(case)
    block = cp4_legal.context_block(pack, upstream)
    assert _shape(block) == VIEW["key_tree"]
    values = VIEW["expected_values"]
    legal = block["legal_sources"]
    other = block["other_sources"]
    assert isinstance(legal, list) and isinstance(other, list)
    assert [s["source_id"] for s in legal] == values["legal_sources"]
    assert legal[0]["authority"] == values["legal_sources[0].authority"]
    assert [f"{s['source_id']} ({s['authority']})" for s in other] == values["other_sources"]
    assert block["facilities"] == values["facilities"]
    assert block["cp1_status"] == values["cp1_status"]
    body = json.dumps(block, ensure_ascii=False)
    for key in ('"quote"', '"citations"', '"record_json"'):
        assert key not in body
