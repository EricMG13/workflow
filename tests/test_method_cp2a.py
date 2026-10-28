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
from defect_classes import BLANK_CASES, EMPTY_TEXT, Adapter, BlankCase, blank_failure
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
Q4 = "Q4 25: 2025-10-01 to 2025-12-31"
ISSUER = "Northbridge Synthetic Group"
RATIO_METRICS = ("total_leverage_reported", "net_leverage_reported", "interest_coverage_reported")
COMPOSED = ("positive", "gap", "interest_undisclosed", "fixture_quarter_known")
# The other base-period columns of the same CP-1 head construction, per case.
OTHER_COLUMNS = {
    "positive": ("gap",),
    "gap": ("positive",),
    "interest_undisclosed": ("gap",),
    "fixture_quarter_known": ("positive", "gap"),
}


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
        "field": {LTM: "ltm", Q3: "q3", Q4: "q4"}[record["period"]],
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
    others = [EXPECTED["cases"][c]["cp1_inputs"] for c in OTHER_COLUMNS[case]]
    records = [*own.items(), *(item for other in others for item in other.items())]
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
        submission=submission, cp1_facts=facts, offered_periods=(LTM, Q3, Q4), names=(ISSUER,)
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


def test_v02_base_ebitda_missing_on_the_composer() -> None:
    """Ruling A5: a base_period issue ends validation and is returned alone, so the literal v02
    payload gives exactly its one pinned issue."""
    assert cp2a.validate(_v02_inputs()) == tuple(REFUSAL_ISSUES["v02"])


def test_v01_base_period_issue_is_returned_alone() -> None:
    """Ruling A5: a period that is not offered ends validation; later issues are not reported."""
    facts = cp1_facts("positive")
    payload = bind_payload(REFUSALS["v01"]["payload"], fig_ids(facts))
    payload["scenarios"][0]["name"] = "Moderate downturn 2"
    payload["assessment"]["confidence"] = "High"
    assert list(cp2a.validate(inputs_for("positive", payload, facts))) == REFUSAL_ISSUES["v01"]


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


INTEREST_NOT_POSITIVE = (
    "Not calculable: base cash interest is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
)
TOTAL_DEBT_NOT_POSITIVE = "Total debt is not positive, so no EBITDA decline raises total leverage"


def test_positive_cp1_cash_interest_is_negated() -> None:
    """Ruling A7: I = -cash_interest exactly; a positive stored value gives I < 0, and the
    coverage breaks fall to the I <= 0 rule (A1)."""
    facts = cp1_facts("positive")
    label = EXPECTED["cases"]["positive"]["cp1_inputs"]["cash_interest"]["label"]
    edited = _edit(facts, label, amount=Decimal(5))
    assert cp2a.BaseOperands.from_cp1(edited, period=LTM).interest == Decimal(-5)
    payload = bind_payload(SUBMISSIONS["positive"]["downside_pathway"], fig_ids(facts))
    result = cp2a.compute(inputs_for("positive", payload, edited))
    by_id = {f.fact_id: f for f in result.facts}
    for bid in ("b02", "b05"):  # b05 is the interest coverage watch level
        point = next(p for p in result.breaks if p.break_id == bid)
        assert (point.outcome, point.reason, point.required_exact) == (
            "Not calculable",
            INTEREST_NOT_POSITIVE,
            None,
        )
        fact = by_id[f"T2B.6.{bid}.required_decline"]
        assert (fact.status, fact.limitation) == ("missing", INTEREST_NOT_POSITIVE)
    assert [p.break_id for p in result.ranking] == ["b01", "b03", "b04"]


def _base(
    *,
    interest: Decimal = Decimal(5),
    total_debt: Decimal = Decimal(50),
    cash: Decimal = Decimal(20),
) -> cp2a.BaseOperands:
    """Positive-case operands (EBITDA 30, FCF 9), with interest, debt and cash as given."""
    return cp2a.BaseOperands(
        period=LTM,
        ebitda=Decimal(30),
        interest=interest,
        fcf=Decimal(9),
        total_debt=total_debt,
        cash=cash,
        gates={},
        sources={},
    )


WATCHES = (
    cp2a.ThresholdSpec("total_leverage", Decimal("2.50"), "Total leverage watch level"),
    cp2a.ThresholdSpec("net_leverage", Decimal("2.00"), "Net leverage watch level"),
    cp2a.ThresholdSpec("interest_coverage", Decimal("2.00"), "Interest coverage watch level"),
)


@pytest.mark.parametrize("debt", [Decimal(0), Decimal(-1)])
def test_total_leverage_break_without_positive_debt_is_not_reached(debt: Decimal) -> None:
    """Ruling A1: D <= 0 -> Not reached, not applicable, the ruled limitation; never ranked."""
    points = cp2a.break_points(base=_base(total_debt=debt, cash=Decimal(0)), thresholds=WATCHES)
    total = points[2]
    assert (total.outcome, total.reason, total.required_exact) == (
        "Not reached by a decline of up to 100%",
        TOTAL_DEBT_NOT_POSITIVE,
        None,
    )
    assert total not in cp2a.rank(points)


@pytest.mark.parametrize("interest", [Decimal(0), Decimal(-2)])
def test_coverage_breaks_without_positive_interest_are_not_calculable(interest: Decimal) -> None:
    """Ruling A1: I <= 0 -> Not calculable (missing) for b02 and a coverage watch level."""
    points = cp2a.break_points(base=_base(interest=interest), thresholds=WATCHES)
    for point in (points[1], points[4]):
        assert (point.outcome, point.reason, point.required_exact) == (
            "Not calculable",
            INTEREST_NOT_POSITIVE,
            None,
        )


def test_zero_debt_composes_not_applicable_total_leverage_break() -> None:
    """Ruling A1 through the composer: the T2B.6 cells are not applicable with the ruled text;
    ruling A6: on an LTM base a CP-1 ratio CP-1 reports no value for reads the FY/LTM wording."""
    facts = cp1_facts("positive")
    cells = EXPECTED["cases"]["positive"]["cp1_inputs"]
    edited = _edit(facts, cells["total_debt"]["label"], amount=Decimal(0))
    edited = _edit(edited, cells["total_leverage_reported"]["label"], amount=Decimal(0))
    no_value = "ZERO_OR_NEGATIVE_DENOMINATOR"
    edited = _edit(edited, cells["fcf_to_debt"]["label"], **MISSING, limitation=no_value)
    payload = bind_payload(SUBMISSIONS["positive"]["downside_pathway"], fig_ids(facts))
    result = cp2a.compute(inputs_for("positive", payload, edited))
    by_id = {f.fact_id: f for f in result.facts}
    for field in ("required_decline", "ebitda_at_break"):
        fact = by_id[f"T2B.6.b03.{field}"]
        assert (fact.status, fact.limitation) == ("not_applicable", TOTAL_DEBT_NOT_POSITIVE)
    assert by_id["T2B.6.b03.outcome"].text == "Not reached by a decline of up to 100%"
    assert "b03" not in [p.break_id for p in result.ranking]
    ltm_wording = (
        f"Not calculable: CP-1 reports no value for this ratio for this period ({no_value})"
    )
    assert by_id["T2B.4.s01.fcf_to_debt"].limitation == ltm_wording
    assert not any(line.startswith("Twelve-month ratios") for line in result.limitations)


def test_quarter_gate_precedes_the_net_debt_short_circuit() -> None:
    """Ruling A8: missing operands, then the CP-1 gate, then the short-circuits. On the gated
    quarter base, net debt <= 0 no longer reads Not reached; it is the gate's Not calculable."""
    facts = cp1_facts("gap")
    edited = _edit(
        facts, EXPECTED["cases"]["gap"]["cp1_inputs"]["cash_closing"]["label"], amount=Decimal(60)
    )
    payload = json.loads(json.dumps(SUBMISSIONS["gap"]["downside_pathway"]))
    payload["thresholds"] = [{
        "metric": "net_leverage", "level": "2.00", "label": "Net leverage watch level",
        "category": "Analyst Interpretation", "rationale": "An internal watch level, not a covenant.",
    }]  # fmt: skip
    result = cp2a.compute(inputs_for("gap", payload, edited))
    net = result.breaks[2]
    gate = EXPECTED["cases"]["gap"]["cp1_inputs"]["net_leverage_reported"]["limitation"]
    assert (net.outcome, net.reason) == (
        "Not calculable",
        f"Not calculable: CP-1 has no twelve-month basis for this period ({gate})",
    )


def test_missing_operand_precedes_the_gate_and_the_short_circuit() -> None:
    """Ruling A8 on the pure function: a missing operand's reason comes first."""
    base = cp2a.BaseOperands(
        period=Q3, ebitda=Decimal(30), interest=None, fcf=Decimal(9), total_debt=None,
        cash=Decimal(20), gates={"interest_coverage": "gated", "total_leverage": "gated"},
        sources={},
    )  # fmt: skip
    points = cp2a.break_points(base=base, thresholds=WATCHES)
    assert [p.reason for p in points[1:]] == [
        "Not calculable: base cash interest is missing",
        "Not calculable: base total debt is missing",
        "Not calculable: base total debt is missing",
        "Not calculable: base cash interest is missing",
    ]


def test_fcf_reasons_come_before_interest_reasons() -> None:
    """Ruling A4: formula order puts F before I (base FCF and cash interest both missing)."""
    facts = cp1_facts("interest_undisclosed")
    fcf = EXPECTED["cases"]["interest_undisclosed"]["cp1_inputs"]["fcf"]["label"]
    edited = _edit(facts, fcf, **MISSING, limitation="Fixture: FCF withheld")
    payload = SUBMISSIONS["interest_undisclosed"]["downside_pathway"]
    result = cp2a.compute(inputs_for("interest_undisclosed", payload, edited))
    by_id = {f.fact_id: f for f in result.facts}
    # s02 carries an interest increase, so both the F and the I reason could apply
    assert by_id["T2B.3.s02.fcf"].limitation == "Not calculable: base free cash flow is missing"
    assert (
        by_id["T2B.4.s02.fcf_to_debt"].limitation
        == "Not calculable: stressed free cash flow is missing"
    )
    assert result.breaks[0].reason == "Not calculable: base free cash flow is missing"
    assert (
        "Base free cash flow is not available in CP-1 for LTM Q4 25: 2025-01-01 to 2025-12-31: "
        "every figure that needs it is Not calculable."
    ) in result.limitations


def test_limitation_figures_are_collected_after_their_rationale() -> None:
    """Ruling A3: a figure named in a limitation joins cp1_references after its row's
    rationale."""
    facts = cp1_facts("positive")
    ids = fig_ids(facts)
    payload = json.loads(json.dumps(SUBMISSIONS["positive"]["downside_pathway"]))
    payload["scenarios"][0]["rationale"] = "Earnings fall from the {{FIG:ebitda_ltm|US$ m}} level."
    payload["scenarios"][0]["limitation"] = "Free cash flow of {{FIG:fcf_ltm|US$ m}} is held."
    payload["scenarios"][1]["rationale"] = "Debt of {{FIG:total_debt_ltm|US$ m}} is held."
    payload["assessment"]["rationale"] = "The scenarios test how far earnings can fall."
    result = cp2a.compute(inputs_for("positive", bind_payload(payload, ids), facts))
    table = next(t for t in result.tables if t.table_id == "cp1_references")
    named = [ids["ebitda_ltm"], ids["fcf_ltm"], ids["total_debt_ltm"]]
    assert [r.fact_ids[0] for r in table.rows][:3] == named


def test_names_and_labels_are_guarded() -> None:
    """Ruling A3 (prohibited conclusions in names and labels) and M4 (an empty or blank name
    or label is refused with the empty-text wording)."""
    facts = cp1_facts("positive")
    payload = bind_payload(SUBMISSIONS["positive"]["downside_pathway"], fig_ids(facts))
    payload["scenarios"][0]["name"] = "Downturn versus peers"
    payload["scenarios"][1]["name"] = ""
    payload["scenarios"][2]["name"] = "   "
    payload["thresholds"][0]["label"] = "We recommend a leverage watch"
    payload["thresholds"][1]["label"] = ""
    assert list(cp2a.validate(inputs_for("positive", payload, facts))) == [
        'scenarios[0].name: prohibited conclusion (peer ranking): "versus peers"',
        "scenarios[1].name: empty text",
        "scenarios[2].name: empty text",
        'thresholds[0].label: prohibited conclusion (instrument recommendation): "we recommend"',
        "thresholds[1].label: empty text",
    ]


def _positive_payload(facts: tuple[Fact, ...]) -> Any:
    return bind_payload(SUBMISSIONS["positive"]["downside_pathway"], fig_ids(facts))


def test_round5_names_line_breaks_reserved_base_label_and_duplicate_labels() -> None:
    """Round 5 Names: a line break or control character is refused; the s00 label is reserved;
    a threshold label used twice is reported once with the pinned wording."""
    facts = cp1_facts("positive")
    payload = _positive_payload(facts)
    payload["scenarios"][0]["name"] = "Deep\ndownturn"
    payload["scenarios"][1]["name"] = "Base (no stress)"
    payload["scenarios"][2]["name"] = "Severe downturn\u0007"
    payload["thresholds"][0]["label"] = "Watch level"
    payload["thresholds"][1]["label"] = "Watch level"
    payload["thresholds"][2]["label"] = "Coverage\twatch"
    assert list(cp2a.validate(inputs_for("positive", payload, facts))) == [
        "scenarios[0].name: contains a line break or control character",
        "scenarios[1].name: Base (no stress) is reserved for the unstressed row",
        "scenarios[2].name: contains a line break or control character",
        "thresholds[2].label: contains a line break or control character",
        "thresholds: Watch level appears more than once",
    ]


def test_round5_pipe_in_a_name_or_label_composes() -> None:
    facts = cp1_facts("positive")
    payload = _positive_payload(facts)
    payload["scenarios"][0]["name"] = "Downturn | volumes"
    payload["thresholds"][0]["label"] = "Leverage | watch"
    result = cp2a.compute(inputs_for("positive", payload, facts))
    assert next(r for r in result.tables if r.table_id == "T2B.1").rows[0].label == (
        "Downturn | volumes"
    )


def test_round5_limitation_references_are_stored_spelled() -> None:
    """Round 5 limitation refs: each {ref|unit} in a stored limitation is spelled as rendered
    (shown value plus unit); the fact stays in cp1_references."""
    facts = cp1_facts("positive")
    ids = fig_ids(facts)
    payload = json.loads(json.dumps(SUBMISSIONS["positive"]["downside_pathway"]))
    payload["scenarios"][2]["limitation"] = (
        "Debt of {{FIG:total_debt_ltm|US$ m}} is held at its closing balance."
    )
    payload["assessment"]["limitation"] = (
        "Total leverage of {{FIG:total_leverage_reported|x}} is CP-1's twelve-month figure."
    )
    result = cp2a.compute(inputs_for("positive", bind_payload(payload, ids), facts))
    claims = {c.claim_id: c for c in result.claims}
    assert claims["T2B.1.s03"].limitation == "Debt of 50 US$ m is held at its closing balance."
    assert claims["T2B.1.assessment"].limitation == (
        "Total leverage of 1.67x is CP-1's twelve-month figure."
    )
    assert not any("{" in (c.limitation or "") for c in result.claims)
    copied = {
        r.fact_ids[0] for t in result.tables if t.table_id == "cp1_references" for r in t.rows
    }
    assert ids["total_debt_ltm"] in copied


def test_round9_gap_texts_are_stored_spelled() -> None:
    """Round 9 choice 5: each {ref|unit} in a T2B.9 gap text, and in its `Gap (…)` own line,
    is stored spelled as rendered; the cells stay analyst judgment and the facts stay in
    cp1_references."""
    facts = cp1_facts("positive")
    ids = fig_ids(facts)
    payload = json.loads(json.dumps(SUBMISSIONS["positive"]["downside_pathway"]))
    gap = payload["gaps"][0]
    gap["gap"] = "Debt of {{FIG:total_debt_ltm|US$ m}} has no maturity schedule."
    gap["why_it_matters"] = "Leverage of {{FIG:total_leverage_reported|x}} may breach a test."
    gap["affected_analysis"] = "Break-point ranking at {{FIG:total_debt_ltm|US$ m}} of debt"
    gap["action"] = "Compare {{FIG:total_leverage_reported|x}} with the lenders' tests."
    result = cp2a.compute(inputs_for("positive", bind_payload(payload, ids), facts))
    cells = {f.fact_id: f for f in result.facts if f.table_id == "T2B.9"}
    expected = {
        "gap": "Debt of 50 US$ m has no maturity schedule.",
        "why_it_matters": "Leverage of 1.67x may breach a test.",
        "affected_analysis": "Break-point ranking at 50 US$ m of debt",
        "action": "Compare 1.67x with the lenders' tests.",
    }
    for field, text in expected.items():
        cell = cells[f"T2B.9.g01.{field}"]
        assert (cell.text, cell.value_class) == (text, "analyst_judgment")
    assert f"Gap (Material): {expected['gap']}" in result.limitations
    assert not any("{" in (f.text or "") for f in cells.values())
    assert not any("{" in line for line in result.limitations)
    copied = {
        r.fact_ids[0] for t in result.tables if t.table_id == "cp1_references" for r in t.rows
    }
    assert {ids["total_debt_ltm"], ids["total_leverage_reported"]} <= copied


AT_BASE_LINE = (
    "Free cash flow at or below zero is already reached at the base period, before any EBITDA "
    "decline."
)


def test_round6_a2_already_reached_at_base_with_a_later_break() -> None:
    """Round 6 A2: the at-base break keeps a true (negative) s*, ranks first, and the claim
    names it without a figure, then the first break reached by a decline."""
    facts = cp1_facts("positive")
    fcf = EXPECTED["cases"]["positive"]["cp1_inputs"]["fcf"]["label"]
    edited = _edit(facts, fcf, amount=Decimal(-3))
    result = cp2a.compute(inputs_for("positive", _positive_payload(facts), edited))
    by_id = {f.fact_id: f for f in result.facts}
    b01 = result.breaks[0]
    assert (b01.outcome, b01.required_decline, b01.ebitda_at_break) == (
        "Already reached at base",
        Decimal("-0.1"),
        Decimal(33),
    )
    decline = by_id["T2B.6.b01.required_decline"]
    assert (decline.status, decline.value_class, _percent(decline.amount)) == (
        "known",
        "calculated",
        "(10.0)%",
    )
    assert [p.break_id for p in result.ranking] == ["b01", "b03", "b04", "b05", "b02"]
    first = next(c for c in result.claims if c.claim_id == "T2B.7.first")
    assert first.text == (
        "The first test reached is Free cash flow at or below zero, already reached at base "
        "before any EBITDA decline. The first test reached by a decline is Total leverage watch "
        "level at an EBITDA decline of {T2B.7.r02.required_decline|%}."
    )
    assert prose.issues(first.text, prose.bind(result.facts), names=(ISSUER,)) == ()
    assert result.limitations.count(AT_BASE_LINE) == 1


def test_round6_a2_already_reached_at_base_alone() -> None:
    """No break is reached by a decline: the claim has the first sentence only."""
    facts = cp1_facts("interest_undisclosed")
    fcf = EXPECTED["cases"]["interest_undisclosed"]["cp1_inputs"]["fcf"]["label"]
    edited = _edit(facts, fcf, amount=Decimal(-3))
    payload = SUBMISSIONS["interest_undisclosed"]["downside_pathway"]
    result = cp2a.compute(inputs_for("interest_undisclosed", payload, edited))
    first = next(c for c in result.claims if c.claim_id == "T2B.7.first")
    assert first.text == (
        "The first test reached is Free cash flow at or below zero, already reached at base "
        "before any EBITDA decline."
    )
    assert AT_BASE_LINE in result.limitations


P1W = "Not meaningful: the base period is a single quarter, and ratios need a twelve-month base"
P1W_LINE = (
    "Ratios are not calculated on a single-quarter base: CP-1 reads each ratio from the twelve "
    "months ending that quarter, while CP-2A's base operands are one quarter's flows."
)


def test_p1w_mixed_quarter_base() -> None:
    """P1-W on a mixed quarter base: a CP-1 ratio that is not known keeps A6's missing text
    byte for byte; a known one is not meaningful; both own lines are present."""
    facts = cp1_facts("fixture_quarter_known")
    cells = EXPECTED["cases"]["fixture_quarter_known"]["cp1_inputs"]
    gap_text = EXPECTED["cases"]["gap"]["cp1_inputs"]["total_leverage_reported"]["limitation"]
    edited = _edit(facts, cells["total_leverage_reported"]["label"], **MISSING, limitation=gap_text)
    payload = SUBMISSIONS["fixture_quarter_known"]["downside_pathway"]
    result = cp2a.compute(inputs_for("fixture_quarter_known", payload, edited))
    by_id = {f.fact_id: f for f in result.facts}
    a6 = f"Not calculable: CP-1 has no twelve-month basis for this period ({gap_text})"
    total, net = by_id["T2B.4.s01.total_leverage"], by_id["T2B.4.s01.net_leverage"]
    assert (total.status, total.limitation) == ("missing", a6)
    assert (net.status, net.limitation) == ("not_applicable", P1W)
    assert [(p.break_id, p.outcome, p.reason) for p in result.breaks[1:]] == [
        ("b02", "Not meaningful on a single-quarter base", P1W),
        ("b03", "Not calculable", a6),
    ]
    assert by_id["T2B.8.s01-b03.result"].text == "Not calculable"
    assert by_id["T2B.8.s01-b02.result"].text == "Not meaningful on a single-quarter base"
    twelve = f"Twelve-month ratios are not calculable on the base period {Q4}: {a6[16:]}"
    assert result.limitations[-3:-1] == (twelve, P1W_LINE)


# Release batch item 1 (fb371d5; round 6 batch review L1): the break-at-base own line.
BREAK_AT_BASE = (
    "Break points hold cash interest at the base period level (no interest increase). The break "
    "at which EBITDA no longer covers cash interest compares same-period flows but is gated like "
    "a ratio: it is Not calculable wherever CP-1 has no twelve-month basis for the base period."
)
BREAK_AT_BASE_NA = BREAK_AT_BASE[:-1] + ", and it is not calculated on a single-quarter base."


@pytest.mark.parametrize("case", COMPOSED)
def test_break_at_base_line_names_the_single_quarter_gate(case: str) -> None:
    """L1: the single-quarter clause is added exactly where the ratio gate holds (a quarter base
    whose CP-1 ratios are known, the builder's gate_na); a quarter base without a twelve-month
    basis (gap) and the FY/LTM bases keep the old line byte for byte."""
    want, other = (
        (BREAK_AT_BASE_NA, BREAK_AT_BASE)
        if case == "fixture_quarter_known"
        else (BREAK_AT_BASE, BREAK_AT_BASE_NA)
    )
    assert want in EXPECTED["cases"][case]["own_limitations"]
    result, _, _ = composed(case)
    assert want in result.limitations
    assert other not in result.limitations


@pytest.mark.parametrize(
    ("metric", "line"),
    [
        ("total_leverage_reported", BREAK_AT_BASE_NA),
        ("interest_coverage_reported", BREAK_AT_BASE),
    ],
    ids=["coverage-not-meaningful", "coverage-no-twelve-month-basis"],
)
def test_break_at_base_line_follows_the_coverage_break_gate(metric: str, line: str) -> None:
    """On a mixed quarter base the clause follows the gate of the break it describes, the one
    at which EBITDA no longer covers cash interest (gated by interest coverage): not meaningful
    there adds it, no twelve-month basis there keeps the old line."""
    facts = cp1_facts("fixture_quarter_known")
    cells = EXPECTED["cases"]["fixture_quarter_known"]["cp1_inputs"]
    gap_text = EXPECTED["cases"]["gap"]["cp1_inputs"][metric]["limitation"]
    edited = _edit(facts, cells[metric]["label"], **MISSING, limitation=gap_text)
    payload = SUBMISSIONS["fixture_quarter_known"]["downside_pathway"]
    result = cp2a.compute(inputs_for("fixture_quarter_known", payload, edited))
    assert line in result.limitations
    other = BREAK_AT_BASE if line == BREAK_AT_BASE_NA else BREAK_AT_BASE_NA
    assert other not in result.limitations


def _quarter_base(
    *, interest: Decimal = Decimal("1.25"), total_debt: Decimal = Decimal(50)
) -> cp2a.BaseOperands:
    """A quarter base whose four CP-1 ratios are known (P1-W gates every ratio)."""
    return cp2a.BaseOperands(
        period=Q4,
        ebitda=Decimal("7.5"),
        interest=interest,
        fcf=Decimal("2.25"),
        total_debt=total_debt,
        cash=Decimal(20),
        gates={},
        sources={},
        not_meaningful=frozenset(cp2a.REPORTED),
    )


def test_p1w_gate_precedes_the_short_circuits_and_the_zero_check() -> None:
    """P1-W item 2 (A8 order): missing operands, then A6, then P1-W, then the short-circuits
    (breaks) or the zero-denominator check (stressed ratios)."""
    # breaks: interest <= 0 and debt / net debt <= 0 would short-circuit; P1-W comes first
    for base in (_quarter_base(interest=Decimal(-1)), _quarter_base(total_debt=Decimal(0))):
        points = cp2a.break_points(base=base, thresholds=WATCHES)
        assert [(p.outcome, p.reason) for p in points[1:]] == [
            ("Not meaningful on a single-quarter base", P1W)
        ] * 4
    # stressed ratios: a 100% decline gives E' = 0, a negative interest I' < 0 and zero debt
    # D = 0; each zero check comes after P1-W
    zero_ebitda = cp2a.stress(base=_quarter_base(), decline=Decimal(1), increase=Decimal(0))
    negative = cp2a.stress(
        base=_quarter_base(interest=Decimal(-1), total_debt=Decimal(0)),
        decline=Decimal(0),
        increase=Decimal(0),
    )
    for row in (zero_ebitda, negative):
        assert row.not_applicable == frozenset(cp2a.RATIOS)
        assert {name: row.why[name] for name in cp2a.RATIOS} == dict.fromkeys(cp2a.RATIOS, P1W)


def test_p1w_own_line_from_rows_alone() -> None:
    """The P1-W own line is emitted when only T2B.4 rows show the reason: cash interest
    missing (b02 is the operand's Not calculable) and no leverage watch level."""
    facts = cp1_facts("fixture_quarter_known")
    cells = EXPECTED["cases"]["fixture_quarter_known"]["cp1_inputs"]
    edited = _edit(
        facts, cells["cash_interest"]["label"], **MISSING, limitation="Fixture: withheld"
    )
    payload = json.loads(json.dumps(SUBMISSIONS["fixture_quarter_known"]["downside_pathway"]))
    payload["thresholds"] = []
    result = cp2a.compute(inputs_for("fixture_quarter_known", payload, edited))
    assert [(p.break_id, p.outcome) for p in result.breaks] == [
        ("b01", "Reached at the stated decline"),
        ("b02", "Not calculable"),
    ]
    assert result.stressed["s00"].not_applicable == frozenset(
        ("total_leverage", "net_leverage", "fcf_to_debt")
    )
    assert result.limitations.count(P1W_LINE) == 1


def test_round5_names_line_separators_and_padded_reserved_label() -> None:
    """Round 5 Names, confirmed choices: U+2028 (Zl) and U+2029 (Zp) are line breaks; the
    reserved base label is matched after stripping."""
    facts = cp1_facts("positive")
    payload = _positive_payload(facts)
    payload["scenarios"][0]["name"] = "Deep\u2028downturn"
    payload["scenarios"][1]["name"] = " Base (no stress) "
    payload["scenarios"][2]["name"] = "Severe\u2029downturn"
    assert list(cp2a.validate(inputs_for("positive", payload, facts))) == [
        "scenarios[0].name: contains a line break or control character",
        "scenarios[1].name: Base (no stress) is reserved for the unstressed row",
        "scenarios[2].name: contains a line break or control character",
    ]


def test_blank_threshold_labels_are_not_reported_as_duplicates() -> None:
    """Two blank labels give their two empty-text issues only, as the scenario-name duplicate
    check skips a blank name."""
    facts = cp1_facts("positive")
    payload = _positive_payload(facts)
    payload["thresholds"][0]["label"] = " "
    payload["thresholds"][1]["label"] = " "
    assert list(cp2a.validate(inputs_for("positive", payload, facts))) == [
        "thresholds[0].label: empty text",
        "thresholds[1].label: empty text",
    ]


def test_new_strings_pass_the_prose_rules() -> None:
    """Round 5/6 process: every new stored string passes prose.issues and bare_figures."""
    for text in (P1W, P1W_LINE, AT_BASE_LINE, cp2a.QUARTER_OUTCOME, cp2a.QUARTER_NOT_COMPARED):
        assert prose.issues(text, {}) == (), text
        assert prose.bare_figures(text) == (), text


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
@given(e=positive, i=amounts, f=amounts, d=amounts, c=nonneg, ts=thresholds)
def test_property_round_trip(
    e: Decimal,
    i: Decimal,
    f: Decimal,
    d: Decimal,
    c: Decimal,
    ts: list[tuple[cp2a.Metric, Decimal]],
) -> None:
    # any sign of debt and interest: ruling A1 short-circuits D <= 0 (Not reached) and I <= 0
    # (Not calculable), which carry no s* and are not round-tripped
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
        assert not (point.kind == "total_leverage" and d <= 0)
        assert not (point.kind == "coverage" and i <= 0)


@settings(max_examples=300, deadline=None)
@given(
    e=positive, i=amounts, f=amounts, d=amounts, c=nonneg, k=fractions_, s=fractions_,
    t=fractions_,
)  # fmt: skip
def test_property_monotonic(
    e: Decimal,
    i: Decimal,
    f: Decimal,
    d: Decimal,
    c: Decimal,
    k: Decimal,
    s: Decimal,
    t: Decimal,
) -> None:
    """Ruling A2 scopes, as the decline rises at fixed k (where calculable): EBITDA and FCF do
    not rise; coverage does not rise; total leverage does not fall when D >= 0; net leverage
    does not fall when ND >= 0 and does not rise when ND < 0; FCF/debt does not rise when D > 0."""
    base = operands(e, i, f, d, c)
    low, high = sorted((s, t))
    a = cp2a.stress(base=base, decline=low, increase=k)
    b = cp2a.stress(base=base, decline=high, increase=k)

    def pair(name: str) -> tuple[Decimal, Decimal] | None:
        before, after = getattr(a, name), getattr(b, name)
        return None if before is None or after is None else (before, after)

    assert b.ebitda <= a.ebitda
    assert a.fcf is not None and b.fcf is not None and b.fcf <= a.fcf
    if (cover := pair("interest_coverage")) is not None:
        assert cover[1] <= cover[0]
    if d >= 0 and (total := pair("total_leverage")) is not None:
        assert total[1] >= total[0]
    if (net := pair("net_leverage")) is not None:
        assert net[1] >= net[0] if d - c >= 0 else net[1] <= net[0]
    if d > 0 and (to_debt := pair("fcf_to_debt")) is not None:
        assert to_debt[1] <= to_debt[0]


# --- round 11 blank text, round 12 B10 (Unicode Cf characters count as blank) -----------------

# Every analyst text field `validate` reads, with the keys that reach it in the payload.
BLANK_FIELDS: tuple[tuple[str, tuple[str | int, ...]], ...] = (
    ("scenarios[0].name", ("scenarios", 0, "name")),
    ("scenarios[0].rationale", ("scenarios", 0, "rationale")),
    ("scenarios[0].limitation", ("scenarios", 0, "limitation")),
    ("thresholds[0].label", ("thresholds", 0, "label")),
    ("thresholds[0].rationale", ("thresholds", 0, "rationale")),
    ("assessment.rationale", ("assessment", "rationale")),
    ("assessment.limitation", ("assessment", "limitation")),
    ("gaps[0].gap", ("gaps", 0, "gap")),
    ("gaps[0].why_it_matters", ("gaps", 0, "why_it_matters")),
    ("gaps[0].affected_analysis", ("gaps", 0, "affected_analysis")),
    ("gaps[0].action", ("gaps", 0, "action")),
)


def _blank_adapter(keys: tuple[str | int, ...]) -> Adapter:
    """Places the value in one analyst text field of the frozen positive payload. Page and quote
    are unused: CP-2A reads no value from an analyst quote."""

    def adapter(page: str, quote: str, value: str) -> tuple[str, ...]:
        facts = cp1_facts("positive")
        payload = _positive_payload(facts)
        cur: Any = payload
        for key in keys[:-1]:
            cur = cur[key]
        cur[keys[-1]] = value
        return cp2a.validate(inputs_for("positive", payload, facts))

    return adapter


@pytest.mark.parametrize("field", BLANK_FIELDS, ids=lambda f: f[0])
@pytest.mark.parametrize("blank", BLANK_CASES, ids=lambda c: c.case_id)
def test_blank_text_is_refused(blank: BlankCase, field: tuple[str, tuple[str | int, ...]]) -> None:
    path, keys = field
    failure = blank_failure(blank, _blank_adapter(keys), EMPTY_TEXT.format(path=path))
    assert failure is None, failure


@pytest.mark.parametrize("field", BLANK_FIELDS, ids=lambda f: f[0])
def test_blank_text_twin_is_accepted(field: tuple[str, tuple[str | int, ...]]) -> None:
    """The twin: the same field holding text is not refused as empty."""
    path, keys = field
    issues = _blank_adapter(keys)("", "", "Downside drivers are desk judgments")
    assert EMPTY_TEXT.format(path=path) not in issues, issues


def test_format_character_labels_are_not_reported_as_duplicates() -> None:
    """B10: two labels of a format character alone are blank, so they give their two empty-text
    issues only, as two whitespace labels do."""
    facts = cp1_facts("positive")
    payload = _positive_payload(facts)
    payload["thresholds"][0]["label"] = "\u200b"
    payload["thresholds"][1]["label"] = "\u200b"
    assert list(cp2a.validate(inputs_for("positive", payload, facts))) == [
        "thresholds[0].label: empty text",
        "thresholds[1].label: empty text",
    ]
