"""CP-2A Stage 1: the pure downside calculation against the frozen oracle.

Every expected value comes from `cases/cp2a-owner/expected.json` (and the literal payloads of
`submissions.json`). The CP-1 facts are built from the oracle's own `cp1_inputs` records (label,
period, status, amount, value class, limitation); only their fact ids and citations are fixture
values, standing in for the run-time binding of a promoted CP-1 head (Stage 2).
"""

import hashlib
import json
import re
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from deploy_vii import prose
from deploy_vii.business_context import spelled
from deploy_vii.contracts import Citation, Fact, validate_tables
from deploy_vii.model._cells import CONTEXT
from deploy_vii.readiness import shape_issues
from deploy_vii.report_view import fact_spelling
from deploy_workflow.owners import cp2a

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "cp2a-owner"
EXPECTED: dict[str, Any] = json.loads((CASE / "expected.json").read_text(encoding="utf-8"))
SUBMISSIONS: dict[str, Any] = json.loads((CASE / "submissions.json").read_text(encoding="utf-8"))
MANIFEST: dict[str, Any] = json.loads((CASE / "manifest.json").read_text(encoding="utf-8"))
FIGURES: dict[str, Any] = SUBMISSIONS["figures"]
FINANCIAL_SHA = next(
    s["sha256"] for s in MANIFEST["financial_baseline"]["sources"] if s["source_id"] == "financial"
)
LTM = "LTM Q4 25: 2025-01-01 to 2025-12-31"
Q3 = "Q3 25: 2025-07-01 to 2025-09-30"
ISSUER = "Northbridge Synthetic Group"
RATIO_METRICS = ("total_leverage_reported", "net_leverage_reported", "interest_coverage_reported")
COMPOSED = ("positive", "gap", "interest_undisclosed")


# --- fixtures: CP-1 facts from the oracle's own records ---------------------------------------


def _unit(metric: str) -> tuple[str, str | None, Decimal]:
    if metric in RATIO_METRICS:
        return "MULTIPLE", None, Decimal(1)
    if metric == "fcf_to_debt":
        return "PERCENT", None, Decimal(1)
    return "MILLIONS", "USD", Decimal(1000000)


def cp1_fact(metric: str, record: dict[str, Any], index: int) -> Fact:
    """One CP-1 T4.10 fact as the oracle records it; the id and the citation are fixture values
    (a promoted head binds `interface-fact:<sha256>` ids at run time)."""
    digest = hashlib.sha256(f"{record['label']}|{record['period']}".encode()).hexdigest()
    unit, currency, scale = _unit(metric)
    common: dict[str, Any] = {
        "fact_id": f"interface-fact:{digest}",
        "label": record["label"],
        "table_id": "T4.10",
        "row_id": metric,
        "field": "ltm" if record["period"] == LTM else "q3",
        "unit": unit,
        "currency": currency,
        "scale": scale,
        "period": record["period"],
        "value_class": record["value_class"],
    }
    if record["status"] != "known":
        return Fact(**common, status=record["status"], limitation=record["limitation"])
    return Fact(
        **common,
        amount=Decimal(record["amount_exact"]),
        citations=(
            Citation(
                source_id="financial",
                source_sha256=FINANCIAL_SHA,
                locator=f"page:{index}",
                quote=f"Fixture evidence of {record['label']}",
            ),
        ),
        calculation_id=f"canonical-kpi:{digest}" if record["value_class"] == "calculated" else None,
    )


def cp1_facts(case: str) -> tuple[Fact, ...]:
    """The CP-1 facts the module reads for a case: the case's own base period records plus the
    other offered base period of the same CP-1 head construction."""
    own = EXPECTED["cases"][case]["cp1_inputs"]
    other = EXPECTED["cases"]["gap" if case != "gap" else "positive"]["cp1_inputs"]
    records = [*own.items(), *other.items()]
    return tuple(cp1_fact(metric, record, n) for n, (metric, record) in enumerate(records, 1))


def by_label(facts: tuple[Fact, ...], label: str) -> Fact:
    found = [f for f in facts if f.label == label]
    assert len(found) == 1, label
    return found[0]


def fig_ids(facts: tuple[Fact, ...]) -> dict[str, str]:
    """FIG name -> the CP-1 fact id bound by the manifest's selection rule (unique label)."""
    out = {}
    for name, figure in FIGURES.items():
        fact = by_label(facts, figure["cp1_label"])
        if fact.status == "known":
            assert spelled(fact) == figure["spelled"], name
        out[name] = fact.fact_id
    return out


def bind(text: str, ids: dict[str, str]) -> str:
    return re.sub(r"\{\{FIG:([a-z_]+)\|([^}]*)\}\}", lambda m: f"{{{ids[m[1]]}|{m[2]}}}", text)


def bind_payload(payload: Any, ids: dict[str, str]) -> Any:
    return json.loads(bind(json.dumps(payload), ids))


def inputs_for(case: str, payload: Any, facts: tuple[Fact, ...] | None = None) -> cp2a.Inputs:
    facts = cp1_facts(case) if facts is None else facts
    submission = cp2a.DownsideSubmission.model_validate_json(json.dumps(payload))
    return cp2a.Inputs(
        submission=submission, cp1_facts=facts, offered_periods=(LTM, Q3), names=(ISSUER,)
    )


def composed(case: str) -> tuple[cp2a.Result, dict[str, str], tuple[Fact, ...]]:
    facts = cp1_facts(case)
    ids = fig_ids(facts) if case != "gap" else {}
    payload = bind_payload(SUBMISSIONS[case]["downside_pathway"], ids)
    return cp2a.compute(inputs_for(case, payload, facts)), ids, facts


def norm(value: Decimal | None) -> str | None:
    if value is None:
        return None
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


# --- the fixture itself agrees with the oracle's observed CP-1 cells ---------------------------


@pytest.mark.parametrize("case", COMPOSED)
def test_cp1_fixture_spells_the_observed_cells(case: str) -> None:
    for metric, record in EXPECTED["cases"][case]["cp1_inputs"].items():
        fact = by_label(cp1_facts(case), record["label"])
        assert fact.row_id == metric
        if record["status"] == "known":
            assert fact_spelling(fact, None)[2] == record["cell_text"]


# --- base operands -------------------------------------------------------------------------------


@pytest.mark.parametrize("case", COMPOSED)
def test_base_operands(case: str) -> None:
    expected = EXPECTED["cases"][case]
    base = cp2a.BaseOperands.from_cp1(cp1_facts(case), period=expected["base_period"])
    got = {
        "ebitda": base.ebitda,
        "interest": base.interest,
        "fcf": base.fcf,
        "total_debt": base.total_debt,
        "cash": base.cash,
        "net_debt": base.net_debt,
    }
    assert {k: norm(v) for k, v in got.items()} == expected["base_operands"]


def test_base_operands_need_exactly_one_fact_per_metric() -> None:
    facts = cp1_facts("positive")
    twice = (*facts, facts[0].model_copy(update={"fact_id": "interface-fact:duplicate"}))
    with pytest.raises(ValueError, match="exactly one"):
        cp2a.BaseOperands.from_cp1(twice, period=LTM)
    with pytest.raises(ValueError, match="exactly one"):
        cp2a.BaseOperands.from_cp1(facts, period="FY25: 2025-01-01 to 2025-12-31")


# --- the composed module ----------------------------------------------------------------------


def _fact_view(fact: Fact) -> dict[str, Any]:
    known = fact.status == "known"
    return {
        "table_id": fact.table_id,
        "row_id": fact.row_id,
        "field": fact.field,
        "label": fact.label,
        "status": fact.status,
        "text": fact.text,
        "unit": fact.unit,
        "period": fact.period,
        "amount_exact": norm(fact.amount),
        "shown": fact_spelling(fact, None)[2] if known else None,
        "decimals": fact.decimals,
        "value_class": fact.value_class,
        "formula": fact.formula,
        "calculation_id": fact.calculation_id,
        "limitation": fact.limitation,
        "currency": fact.currency,
        "scale": str(fact.scale) if fact.currency else None,
    }


@pytest.mark.parametrize("case", COMPOSED)
def test_facts_equal_the_oracle(case: str) -> None:
    result, _, facts = composed(case)
    expected = EXPECTED["cases"][case]["facts"]
    mine = [f for f in result.facts if f.table_id != "cp1_references"]
    assert [f.fact_id for f in mine] == [e["fact_id"] for e in expected]
    period = EXPECTED["cases"][case]["base_period"]
    cp1_by_metric = {f.row_id: f for f in facts if f.period == period}
    for fact, exp in zip(mine, expected, strict=True):
        view = _fact_view(fact)
        want = {key: exp.get(key) for key in view}
        assert view == want, fact.fact_id
        # lineage (M2): citations are the derives_from CP-1 facts' citations, ordered, de-duplicated
        lineage = tuple(
            dict.fromkeys(
                c for m in exp.get("derives_from") or () for c in cp1_by_metric[m].citations
            )
        )
        assert fact.citations == lineage, fact.fact_id


@pytest.mark.parametrize("case", COMPOSED)
def test_tables_equal_the_oracle(case: str) -> None:
    result, _, _ = composed(case)
    tables = {t.table_id: t for t in result.tables}
    for exp in EXPECTED["cases"][case]["tables"]:
        table = tables[exp["table_id"]]
        assert table.title == exp["title"]
        rows = [
            {"row_id": r.row_id, "label": r.label, "fact_ids": list(r.fact_ids)} for r in table.rows
        ]
        assert rows == exp["rows"], exp["table_id"]
    assert [t.table_id for t in result.tables] == [
        *(t["table_id"] for t in EXPECTED["cases"][case]["tables"]),
        "cp1_references",
    ]
    validate_tables(result.tables, result.facts)


@pytest.mark.parametrize("case", COMPOSED)
def test_cp1_references_equal_the_oracle(case: str) -> None:
    result, _, facts = composed(case)
    exp = EXPECTED["cases"][case]["cp1_references"]
    table = next(t for t in result.tables if t.table_id == "cp1_references")
    assert (table.title, table.row_header) == (exp["title"], exp["row_header"])
    by_id = {f.fact_id: f for f in result.facts}
    assert len(table.rows) == len(exp["rows"])
    for row, want in zip(table.rows, exp["rows"], strict=True):
        source = by_label(facts, want["cp1_label"])
        fact = by_id[row.fact_ids[0]]
        assert (row.row_id, row.label) == (want["row_id"], want["label"])
        assert fact == source.model_copy(
            update={"table_id": "cp1_references", "row_id": want["row_id"], "field": "value"}
        )
        assert (fact.status, fact.value_class, fact.limitation, fact.period) == (
            want["status"],
            want["value_class"],
            want["limitation"],
            want["period"],
        )
        assert norm(fact.amount) == want["amount_exact"]
        if want["status"] == "known":
            assert spelled(fact) == want["shown"]
            assert fact_spelling(fact, None)[2] == want["cell_text"]


@pytest.mark.parametrize("case", COMPOSED)
def test_claims_equal_the_oracle(case: str) -> None:
    result, ids, _ = composed(case)
    expected = EXPECTED["cases"][case]["claims"]
    assert [c.claim_id for c in result.claims] == [e["claim_id"] for e in expected]
    for claim, exp in zip(result.claims, expected, strict=True):
        assert claim.text == bind(exp["text"], ids), claim.claim_id
        assert claim.limitation == exp["limitation"]
        assert claim.citations == ()
    bound = prose.bind(result.facts)
    for claim in result.claims:
        assert prose.issues(claim.text, bound, names=(ISSUER,)) == (), claim.claim_id


@pytest.mark.parametrize("case", COMPOSED)
def test_own_limitations_equal_the_oracle(case: str) -> None:
    result, _, _ = composed(case)
    assert list(result.limitations) == EXPECTED["cases"][case]["own_limitations"]


@pytest.mark.parametrize("case", COMPOSED)
def test_stress_rows_equal_the_oracle(case: str) -> None:
    result, _, _ = composed(case)
    expected = EXPECTED["cases"][case]["stress"]
    assert list(result.stressed) == list(expected)
    for row_id, row in result.stressed.items():
        got = {name: norm(getattr(row, name)) for name in cp2a.STRESSED_FIELDS}
        want = {k: v for k, v in expected[row_id].items() if k != "not_calculable"}
        assert got == want, row_id
        # the oracle records the reasons of the ratios and of a missing stressed FCF
        reasons = {k: v for k, v in row.why.items() if k in (*cp2a.RATIOS, "fcf")}
        assert reasons == expected[row_id]["not_calculable"], row_id


@pytest.mark.parametrize("case", COMPOSED)
def test_break_points_equal_the_oracle(case: str) -> None:
    result, _, _ = composed(case)
    expected = EXPECTED["cases"][case]["break_points"]
    assert len(result.breaks) == len(expected)
    for point, exp in zip(result.breaks, expected, strict=True):
        assert (point.break_id, point.origin, point.test, point.outcome) == (
            exp["break_id"],
            exp["origin"],
            exp["test"],
            exp["outcome"],
        )
        assert norm(point.required_decline) == exp["required_decline"]
        assert norm(point.ebitda_at_break) == exp["ebitda_at_break"]
        exact = point.required_exact
        got_fraction = None if exact is None else f"{exact.numerator}/{exact.denominator}"
        assert got_fraction == exp["required_decline_fraction"]
        if exp["required_decline_shown"] is not None:
            assert _percent(point.required_decline) == exp["required_decline_shown"]
        assert result.crossings[point.break_id] == exp["crossings"]
        if exp["round_trip_exact_in_fraction"]:
            assert exact is not None
            assert _level_at(result.base, point, exact) == Fraction(point.level)


@pytest.mark.parametrize("case", COMPOSED)
def test_ranking_and_first_break(case: str) -> None:
    result, _, _ = composed(case)
    exp = EXPECTED["cases"][case]
    got = [(n, p.break_id, p.test) for n, p in enumerate(result.ranking, 1)]
    assert got == [(r["rank"], r["break_id"], r["test"]) for r in exp["ranking"]]
    shown = [_percent(p.required_decline) for p in result.ranking]
    assert shown == [r["required_decline_shown"] for r in exp["ranking"]]
    first = exp["first_break"]
    assert (result.ranking[0].break_id, result.ranking[0].test) == (
        first["break_id"],
        first["test"],
    )


def _percent(value: Decimal | None) -> str:
    fact = Fact(fact_id="probe", label="probe", amount=value, unit="PERCENT", period=LTM)
    return fact_spelling(fact, None)[2]


@pytest.mark.parametrize("case", COMPOSED)
def test_fp05_block_cells(case: str) -> None:
    result, _, _ = composed(case)
    by_id = {f.fact_id: f for f in result.facts}
    tables = {t.table_id: t for t in result.tables}
    fp05 = EXPECTED["cases"][case]["FP05"]
    for block in fp05["blocks"].values():
        for tab in block["tabs"]:
            table = tables[tab["table_id"]]
            for row, want in zip(table.rows, tab["rows"], strict=True):
                assert (row.row_id, row.label) == (want["row_id"], want["label"])
                for fact_id, cell in zip(row.fact_ids, want["cells"], strict=True):
                    _, state, text = fact_spelling(by_id[fact_id], "G1")
                    assert fact_id == cell["fact_id"]
                    assert (state, text.replace("G1", "G#")) == (cell["state"], cell["shown"])
    assert set(fp05["evidence_rail_tables"]) | set(fp05["limitations_rail_tables"]) <= set(tables)


def test_positive_scenario_results_named_by_the_lease() -> None:
    """A1's spelled results: s00 reconciles, s04 coverage 0.00x, s04 leverage Not calculable."""
    result, _, _ = composed("positive")
    by_id = {f.fact_id: f for f in result.facts}

    def shown(fact_id: str) -> str:
        return fact_spelling(by_id[fact_id], "G1")[2]

    assert [shown(f"T2B.5.{r}.result") for r in cp2a.RATIOS] == ["Reconciled"] * 4
    assert shown("T2B.4.s04.interest_coverage") == "0.00x"
    assert by_id["T2B.4.s04.total_leverage"].status == "missing"


# --- refusals -----------------------------------------------------------------------------------

REFUSALS = {r["id"]: r for r in SUBMISSIONS["refusals"]}
REFUSAL_ISSUES = {r["id"]: r["expected_issues"] for r in EXPECTED["refusals"]}
SHAPE = [r["id"] for r in EXPECTED["refusals"] if r["issue_kind"] == "shape"]
CONTENT = [
    r["id"]
    for r in EXPECTED["refusals"]
    if r["issue_kind"] == "content" and not REFUSALS[r["id"]].get("composer_only")
]


@pytest.mark.parametrize("rid", SHAPE)
def test_shape_refusals(rid: str) -> None:
    refusal = REFUSALS[rid]
    text = refusal.get("payload_text") or json.dumps(refusal["payload"])
    with pytest.raises(ValidationError) as error:
        cp2a.DownsideSubmission.model_validate_json(text)
    assert list(shape_issues(error.value)) == REFUSAL_ISSUES[rid]


def _expected_issues(rid: str, ids: dict[str, str]) -> list[str]:
    return [
        re.sub(r"\{\{FACT_ID:([a-z_]+)\}\}", lambda m: ids[m[1]], issue)
        for issue in REFUSAL_ISSUES[rid]
    ]


@pytest.mark.parametrize("rid", CONTENT)
def test_content_refusals(rid: str) -> None:
    refusal = REFUSALS[rid]
    facts = cp1_facts("positive")
    ids = fig_ids(facts)
    payload = refusal["payload"]
    if refusal.get("bind_placeholders", True):
        payload = bind_payload(payload, ids)
    inputs = inputs_for("positive", payload, facts)
    assert list(cp2a.validate(inputs)) == _expected_issues(rid, ids)
    with pytest.raises(ValueError):
        cp2a.compute(inputs)


def _edit(facts: tuple[Fact, ...], label: str, **update: Any) -> tuple[Fact, ...]:
    """The facts with the one fact labelled `label` updated (a composer-only fixture edit)."""
    assert sum(f.label == label for f in facts) == 1, label
    return tuple(f.model_copy(update=update) if f.label == label else f for f in facts)


MISSING = {"status": "missing", "amount": None, "citations": (), "calculation_id": None}


def _v02_inputs() -> cp2a.Inputs:
    """Composer only: the positive CP-1 facts with the base EBITDA fact set to missing, and the
    literal v02 payload, unrewritten (its prose still names the now unsettled EBITDA fact)."""
    facts = cp1_facts("positive")
    ids = fig_ids(facts)
    label = FIGURES["ebitda_ltm"]["cp1_label"]
    edited = _edit(facts, label, **MISSING, limitation="Fixture: EBITDA withheld")
    return inputs_for("positive", bind_payload(REFUSALS["v02"]["payload"], ids), edited)


@pytest.mark.xfail(
    strict=True,
    reason="oracle-disagreement v02: frozen oracle expects 1 issue, validator returns 3; "
    "pending LEAD amendment",
)
def test_v02_base_ebitda_missing_on_the_composer() -> None:
    assert cp2a.validate(_v02_inputs()) == tuple(REFUSAL_ISSUES["v02"])


def test_v02_is_refused_by_the_composer() -> None:
    with pytest.raises(ValueError):
        cp2a.compute(_v02_inputs())


def _t2b7_columns() -> list[tuple[str, str]]:
    """The oracle's populated T2B.7 columns: field and label of the first row's facts."""
    exp = EXPECTED["cases"]["positive"]
    table = next(t for t in exp["tables"] if t["table_id"] == "T2B.7")
    labels = {f["fact_id"]: (f["field"], f["label"]) for f in exp["facts"]}
    return [labels[fid] for fid in table["rows"][0]["fact_ids"]]


def _assert_no_ranked_break(result: cp2a.Result) -> None:
    assert result.ranking == ()
    t2b7 = next(t for t in result.tables if t.table_id == "T2B.7")
    assert t2b7.rows == ()
    assert [(c.field, c.label) for c in t2b7.columns] == _t2b7_columns()
    assert "T2B.7.first" not in {c.claim_id for c in result.claims}
    assert result.limitations[-1] == "No break point is calculable, so no first break is ranked."
    validate_tables(result.tables, result.facts)


def test_no_ranked_break_gap_case_without_base_fcf() -> None:
    """The quarter base (ratios gated) with base free cash flow missing: no break ranks."""
    facts = cp1_facts("gap")
    q3_fcf = EXPECTED["cases"]["gap"]["cp1_inputs"]["fcf"]["label"]
    edited = _edit(facts, q3_fcf, **MISSING, limitation="Fixture: FCF withheld")
    inputs = inputs_for("gap", SUBMISSIONS["gap"]["downside_pathway"], edited)
    assert cp2a.validate(inputs) == ()
    result = cp2a.compute(inputs)
    _assert_no_ranked_break(result)
    assert [p.outcome for p in result.breaks] == ["Not calculable"] * 3


def test_no_ranked_break_fcf_above_ebitda_interest_missing_no_thresholds() -> None:
    """FCF above EBITDA (s* > 1, not reached), cash interest missing, no watch level."""
    facts = cp1_facts("interest_undisclosed")
    fcf = EXPECTED["cases"]["interest_undisclosed"]["cp1_inputs"]["fcf"]["label"]
    edited = _edit(facts, fcf, amount=Decimal(40))
    payload = SUBMISSIONS["interest_undisclosed"]["downside_pathway"]
    assert payload["thresholds"] == []
    inputs = inputs_for("interest_undisclosed", payload, edited)
    assert cp2a.validate(inputs) == ()
    result = cp2a.compute(inputs)
    _assert_no_ranked_break(result)
    assert [p.outcome for p in result.breaks] == [
        "Not reached by a decline of up to 100%",
        "Not calculable",
    ]


def test_limitation_fields_are_prose_checked() -> None:
    """Every prose field, the scenario and assessment limitations included, carries no bare
    figure and no prohibited conclusion (as cp2_synthesis checks every text field)."""
    facts = cp1_facts("positive")
    ids = fig_ids(facts)
    payload = bind_payload(SUBMISSIONS["positive"]["downside_pathway"], ids)
    payload["scenarios"][2]["limitation"] = "No disclosure supports a 20 percent increase."
    payload["assessment"]["limitation"] = "Earnings look weak versus peers."
    payload["scenarios"][0]["limitation"] = " "
    assert list(cp2a.validate(inputs_for("positive", payload, facts))) == [
        "scenarios[0].limitation: empty text",
        "scenarios[2].limitation: Bare figure: 20",
        'assessment.limitation: prohibited conclusion (peer ranking): "versus peers"',
    ]


def test_positive_cp1_cash_interest_fails_closed() -> None:
    """CP-1 stores cash interest as a negative outflow; a positive amount is refused until LEAD
    rules between the lease (I = -cash_interest) and the manifest (magnitude)."""
    facts = cp1_facts("positive")
    label = EXPECTED["cases"]["positive"]["cp1_inputs"]["cash_interest"]["label"]
    edited = _edit(facts, label, amount=Decimal(5))
    with pytest.raises(ValueError, match="cash interest"):
        cp2a.BaseOperands.from_cp1(edited, period=LTM)


def test_v17_stale_input_is_stage_2() -> None:
    pytest.skip("v17 needs the attempt's bound Input records (Upstream): Stage 2")


def test_valid_payloads_have_no_issue() -> None:
    for case in COMPOSED:
        facts = cp1_facts(case)
        ids = fig_ids(facts) if case != "gap" else {}
        payload = bind_payload(SUBMISSIONS[case]["downside_pathway"], ids)
        assert cp2a.validate(inputs_for(case, payload, facts)) == ()


def test_lineage_never_reads_an_unsettled_cp1_fact() -> None:
    """A known CP-2A fact never derives from a CP-1 fact that is not known (fail closed)."""
    facts = cp1_facts("interest_undisclosed")
    base = cp2a.BaseOperands.from_cp1(facts, period=LTM)
    with pytest.raises(ValueError, match="not known"):
        cp2a.lineage(base, ("ebitda", "cash_interest"))


# --- property tests (expected.json property_tests) ------------------------------------------

amounts = st.decimals(min_value=-1000, max_value=1000, places=2, allow_nan=False)
positive = st.decimals(min_value="0.01", max_value=1000, places=2, allow_nan=False)
nonneg = st.decimals(min_value=0, max_value=1000, places=2, allow_nan=False)
fractions_ = st.decimals(min_value=0, max_value=1, places=4, allow_nan=False)
levels = st.decimals(min_value="0.0001", max_value=50, places=4, allow_nan=False)


def operands(
    e: Decimal, i: Decimal | None, f: Decimal, d: Decimal, c: Decimal
) -> cp2a.BaseOperands:
    return cp2a.BaseOperands(
        period=LTM, ebitda=e, interest=i, fcf=f, total_debt=d, cash=c, gates={}, sources={}
    )


def _level_at(base: cp2a.BaseOperands, point: cp2a.BreakPoint, s: Fraction) -> Fraction:
    """The stress recipe in exact fractions over the Decimal inputs at decline s (k = 0)."""

    def fr(x: Decimal | None) -> Fraction:
        assert x is not None
        return Fraction(x)

    e2 = fr(base.ebitda) * (1 - s)
    if point.kind == "fcf":
        return fr(base.fcf) - fr(base.ebitda) * s
    if point.kind == "coverage":
        return e2 / fr(base.interest)
    if point.kind == "total_leverage":
        return fr(base.total_debt) / e2
    return (fr(base.total_debt) - fr(base.cash)) / e2


@settings(max_examples=300, deadline=None)
@given(e=positive, i=nonneg, f=amounts, d=nonneg, c=nonneg)
def test_property_base_control(e: Decimal, i: Decimal, f: Decimal, d: Decimal, c: Decimal) -> None:
    base = operands(e, i, f, d, c)
    row = cp2a.stress(base=base, decline=Decimal(0), increase=Decimal(0))
    assert (row.ebitda, row.interest, row.fcf) == (e, i, f)
    assert row.total_leverage == CONTEXT.divide(d, e)
    assert row.net_leverage == CONTEXT.divide(d - c, e)
    assert row.interest_coverage == (CONTEXT.divide(e, i) if i > 0 else None)
    assert row.fcf_to_debt == (CONTEXT.divide(f, d) if d > 0 else None)


WATCH_METRICS: tuple[cp2a.Metric, ...] = ("total_leverage", "net_leverage", "interest_coverage")
thresholds = st.lists(
    st.tuples(st.sampled_from(WATCH_METRICS), levels),
    max_size=3,
    unique_by=lambda t: t[0],
)


@settings(max_examples=300, deadline=None)
@given(e=positive, i=positive, f=amounts, d=positive, c=nonneg, ts=thresholds)
def test_property_round_trip(
    e: Decimal,
    i: Decimal,
    f: Decimal,
    d: Decimal,
    c: Decimal,
    ts: list[tuple[cp2a.Metric, Decimal]],
) -> None:
    # debt and cash interest kept positive: at zero debt (or zero interest) the lease recipe gives
    # s* = 1 where the stressed ratio is undefined (reported to LEAD, not exercised by the oracle)
    base = operands(e, i, f, d, c)
    spec = tuple(cp2a.ThresholdSpec(metric=m, level=lvl, label=f"{m} watch") for m, lvl in ts)
    for point in cp2a.break_points(base=base, thresholds=spec):
        exact = point.required_exact
        if exact is None:
            continue
        assert point.required_decline == CONTEXT.divide(
            Decimal(exact.numerator), Decimal(exact.denominator)
        )
        assert _level_at(base, point, exact) == Fraction(point.level), point.break_id


@settings(max_examples=300, deadline=None)
@given(
    e=positive, i=positive, f=amounts, d=nonneg, extra=nonneg, k=fractions_, s=fractions_,
    t=fractions_,
)  # fmt: skip
def test_property_monotonic(
    e: Decimal,
    i: Decimal,
    f: Decimal,
    d: Decimal,
    extra: Decimal,
    k: Decimal,
    s: Decimal,
    t: Decimal,
) -> None:
    # net debt kept non-negative: with negative net debt a falling EBITDA lowers net leverage
    base = operands(e, i, f, d + extra, d)
    low, high = sorted((s, t))
    a = cp2a.stress(base=base, decline=low, increase=k)
    b = cp2a.stress(base=base, decline=high, increase=k)
    assert a.ebitda is not None and b.ebitda is not None and b.ebitda <= a.ebitda
    assert a.fcf is not None and b.fcf is not None and b.fcf <= a.fcf
    assert a.interest_coverage is not None and b.interest_coverage is not None
    assert b.interest_coverage <= a.interest_coverage
    for name in ("total_leverage", "net_leverage"):
        before, after = getattr(a, name), getattr(b, name)
        if before is not None and after is not None:
            assert after >= before, name
