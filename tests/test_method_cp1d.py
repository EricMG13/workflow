"""CP-1D Stage 1: the pure calculation against the frozen oracle `cases/cp1d-owner`.

Every input is built from the oracle's own files (manifest pages and figures, submissions,
the financial pack); every expectation is read from `expected.json`. Nothing here derives an
expected value.
"""

import copy
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from deploy_vii.contracts import Source, Span
from deploy_workflow.owners import cp1d

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "cp1d-owner"
EXPECTED: dict[str, Any] = json.loads((CASE / "expected.json").read_text())
MANIFEST: dict[str, Any] = json.loads((CASE / "manifest.json").read_text())
SUBMISSIONS: dict[str, Any] = json.loads((CASE / "submissions.json").read_text())
FINANCIAL: dict[str, Any] = json.loads((ROOT / "cases" / "financial" / "manifest.json").read_text())
CASES = ("positive", "statements_only", "gap")


def _source(source_id: str, name: str, pages: list[dict[str, str]], sha256: str) -> Source:
    return Source(
        source_id=source_id,
        name=name,
        status="ready",
        sha256=sha256,
        media_type="text/plain",
        spans=tuple(Span(locator=p["locator"], text=p["text"]) for p in pages),
        extraction_status="complete",
    )


def _pack_sources(pack: str) -> tuple[Source, ...]:
    """identity + financial (frozen), plus the bridge variant the oracle names."""
    frozen = tuple(
        _source(s["source_id"], s["name"], s["pages"], s["sha256"]) for s in FINANCIAL["sources"]
    )
    if pack == "statements_only":
        return frozen
    synthetic = MANIFEST["synthetic_source"]
    variant = (
        synthetic["fixtures"]["bridge_table_not_found"]
        if pack == "unparseable"
        else synthetic[pack]
    )
    bridge = _source("bridge", synthetic["name"], variant["pages"], variant["sha256"])
    return (*frozen, bridge)


def _cp1() -> cp1d.Cp1Operands:
    """CP-1 figures from manifest `figures`; the amount currency is the pack's dimension."""
    currency = FINANCIAL["source_dimensions"]["currency"]
    figures = {
        name: cp1d.Cp1Figure(
            figure=name,
            label=f["label"],
            unit=f["unit"],
            period=f["period"],
            amount=Decimal(f["amount_exact"]),
            value_class=f["value_class"],
            currency=currency if f["unit"] == "MILLIONS" else None,
        )
        for name, f in MANIFEST["figures"].items()
    }
    return cp1d.Cp1Operands(
        adjusted_ebitda=figures["adjusted_ebitda_ltm"],
        ebitda=figures["ebitda_ltm"],
        cfo=figures["cfo_ltm"],
        total_debt=figures["total_debt_ltm"],
        net_debt=figures["net_debt_ltm"],
        total_leverage=figures["total_leverage_adjusted"],
        net_leverage=figures["net_leverage_adjusted"],
    )


def _inputs(
    pack: str, payload: dict[str, Any], cp1b: cp1d.Cp1bState = "unbound"
) -> cp1d.EarningsQualityInputs:
    return cp1d.EarningsQualityInputs(
        sources=_pack_sources(pack),
        cp1=_cp1(),
        submission=cp1d.EarningsQualitySubmission.model_validate_json(json.dumps(payload)),
        cp1b=cp1b,
    )


def _case_inputs(case: str) -> cp1d.EarningsQualityInputs:
    return _inputs(case, SUBMISSIONS[case]["earnings_quality"])


def _citation(c: Any) -> dict[str, str]:
    return {"source_id": c.source_id, "locator": c.locator, "quote": c.quote}


def _assert_fact(mine: cp1d.CellFact, want: dict[str, Any]) -> None:
    record = mine.record()
    for key, value in want.items():
        got = record[key]
        if key == "citations":
            got = [_citation(c) for c in got]
        if key == "derives_from":
            got = list(got)
        assert got == value, (want["fact_id"], key, got, value)
    for key, value in record.items():
        if key not in want:
            assert value in (None, ()), (want["fact_id"], key, value)


def _assert_facts(result: cp1d.EarningsQualityResult, want: list[dict[str, Any]]) -> None:
    assert [f.fact_id for f in result.facts] == [f["fact_id"] for f in want]
    for mine, expected in zip(result.facts, want, strict=True):
        _assert_fact(mine, expected)


def _tables(result: cp1d.EarningsQualityResult) -> list[dict[str, Any]]:
    return [
        {
            "table_id": t.table_id,
            "title": t.title,
            "rows": [
                {"row_id": r.row_id, "label": r.label, "fact_ids": list(r.fact_ids)} for r in t.rows
            ],
        }
        for t in result.tables
    ]


def _claims(result: cp1d.EarningsQualityResult) -> list[dict[str, Any]]:
    out = []
    for c in result.claims:
        row: dict[str, Any] = {"claim_id": c.claim_id, "text": c.text, "limitation": c.limitation}
        if c.evidence is not None:
            row["evidence"] = [
                {**_citation(e), "source_sha256": e.source_sha256} for e in c.evidence
            ]
        out.append(row)
    return out


def _cp1_refs(result: cp1d.EarningsQualityResult) -> list[dict[str, Any]]:
    return [
        {
            "row_id": r.row_id,
            "figure": r.figure,
            "label": r.label,
            "unit": r.unit,
            "period": r.period,
            "amount_exact": r.amount_exact,
            "shown": r.shown,
            "value_class": r.value_class,
            "status": r.status,
        }
        for r in result.cp1_references
    ]


def _operands(result: cp1d.EarningsQualityResult) -> dict[str, str]:
    return {name: cp1d.exact_text(value) for name, value in result.operands}


@pytest.mark.parametrize("case", CASES)
def test_case_facts_tables_claims_limitations(case: str) -> None:
    want = EXPECTED["cases"][case]
    result = cp1d.compute(_case_inputs(case))
    _assert_facts(result, want["facts"])
    assert _tables(result) == want["tables"]
    assert _cp1_refs(result) == want["cp1_references"]
    assert _claims(result) == want["claims"]
    assert list(result.limitations) == want["own_limitations"]
    assert _operands(result) == want["operands"]
    assert list(result.operands_unavailable) == want["operands_unavailable"]
    bridge = want["bridge_source"]
    if bridge is None:
        assert result.bridge_source is None
    else:
        assert result.bridge_source == cp1d.BridgeSourceRef(**bridge)


@pytest.mark.parametrize("case", CASES)
def test_fp02_cell_state_and_spelling(case: str) -> None:
    """Every FP02 cell's fact, its known/gap/not_meaningful state and `shown`; tab rows follow
    the table rows (the blocks themselves are a Stage 3 rendering concern)."""
    result = cp1d.compute(_case_inputs(case))
    facts = {f.fact_id: f for f in result.facts}
    tables = {t.table_id: t for t in result.tables}
    for block in EXPECTED["cases"][case]["FP02"]["blocks"].values():
        for tab in block["tabs"]:
            rows = tables[tab["table_id"]].rows
            assert [r["row_id"] for r in tab["rows"]] == [r.row_id for r in rows]
            for row, mine in zip(tab["rows"], rows, strict=True):
                assert [c["fact_id"] for c in row["cells"]] == list(mine.fact_ids)
                for cell in row["cells"]:
                    fact = facts[cell["fact_id"]]
                    got = (fact.field, fact.shown, fact.cell_state)
                    assert got == (cell["field"], cell["shown"], cell["state"]), cell


@pytest.mark.parametrize("case", CASES)
def test_known_facts_never_derive_from_unsettled(case: str) -> None:
    """expected.json lineage_rule: a known fact never derives from a fact that is not known."""
    result = cp1d.compute(_case_inputs(case))
    status = {f.fact_id: f.status for f in result.facts}
    for fact in result.facts:
        if fact.status != "known":
            continue
        for ref in fact.derives_from:
            if ref.startswith("cp1:") or "<each>" in ref:
                continue
            assert status[ref] == "known", (fact.fact_id, ref)


def test_analyst_fraction_composer_fixture() -> None:
    fixture = EXPECTED["composer_fixtures"]["analyst_fraction"]
    payload = copy.deepcopy(SUBMISSIONS["positive"]["earnings_quality"])
    payload["assessments"][0]["accepted_basis"] = None
    payload["assessments"][0]["accepted_fraction"] = "0.60"
    payload["assessments"][0]["rationale"] = fixture["rationale"]
    inputs = _inputs("positive", payload)
    assert cp1d.validation_issues(inputs) == ()
    alt = cp1d.compute(inputs)
    base = EXPECTED["cases"]["positive"]
    deltas = fixture["fact_deltas"]
    _assert_facts(alt, [deltas.get(f["fact_id"], f) for f in base["facts"]])
    assert _tables(alt) == base["tables"]
    assert _cp1_refs(alt) == base["cp1_references"]
    assert _operands(alt) == base["operands"]
    assert list(alt.limitations) == fixture["expected_own_limitations"]
    added = fixture["added_limitation"]
    assert alt.limitations[added["index"]] == added["text"]
    changed = [
        mine["claim_id"]
        for mine, old in zip(_claims(alt), base["claims"], strict=True)
        if mine != old
    ]
    assert changed == fixture["changed_claims"]
    assert {f.fact_id: f for f in alt.facts}["T1D.2.a01.basis"].cell_state == "not_meaningful"


def _submitted_refusal(refusal_id: str) -> dict[str, Any]:
    """The literal invalid payload (`submissions.json refusals`)."""
    found: dict[str, Any] = next(r for r in SUBMISSIONS["refusals"] if r["id"] == refusal_id)
    return found


def _matches(issue: str, expected: str) -> bool:
    return issue.startswith(expected) if expected.endswith("(") else issue == expected


@pytest.mark.parametrize("refusal", EXPECTED["refusals"], ids=lambda r: str(r["id"]))
def test_refusal_issues(refusal: dict[str, Any]) -> None:
    submitted = _submitted_refusal(refusal["id"])
    assert (submitted["pack"], submitted["expected_issues"]) == (
        refusal["pack"],
        refusal["expected_issues"],
    )
    inputs = _inputs(refusal["pack"], submitted["payload"])
    issues = cp1d.validation_issues(inputs)
    expected = refusal["expected_issues"]
    assert all(any(_matches(i, e) for i in issues) for e in expected), issues
    assert all(any(_matches(i, e) for e in expected) for i in issues), issues
    with pytest.raises(ValueError):
        cp1d.compute(inputs)


@pytest.mark.parametrize("case", CASES)
def test_valid_cases_have_no_issues(case: str) -> None:
    assert cp1d.validation_issues(_case_inputs(case)) == ()


def test_blocked_attempts_issue_text() -> None:
    """Both blocked attempts (r06) give the issue the blocked head's limitations carry."""
    blocked = EXPECTED["blocked"]
    for key in ("attempt_0", "attempt_1"):
        refusal = _submitted_refusal(blocked[key])
        issues = cp1d.validation_issues(_inputs(refusal["pack"], refusal["payload"]))
        assert blocked["limitations_contain"] in issues


@pytest.mark.parametrize(
    ("state", "wording"),
    [("unbound", "unbound"), ("settled", "bound_settled"), ("blocked", "bound_blocked")],
)
def test_cp1b_own_limitation_line(state: cp1d.Cp1bState, wording: str) -> None:
    wordings = EXPECTED["cp1b"]["limitation_wordings"]
    if state == "blocked":
        fixture = EXPECTED["cp1b"]["blocked"]["fixture"]
        assert wordings[wording] == fixture["expected_own_cp1b_line"]
    payload = SUBMISSIONS["positive"]["earnings_quality"]
    result = cp1d.compute(_inputs("positive", payload, state))
    base = EXPECTED["cases"]["positive"]["own_limitations"]
    position = base.index(wordings["unbound"])
    assert list(result.limitations) == [*base[:position], wordings[wording], *base[position + 1 :]]


def test_rationale_may_reference_module_totals() -> None:
    """Run text may name any module fact (lease: refs name module facts), not only T1D.1/T1D.2."""
    payload = copy.deepcopy(SUBMISSIONS["positive"]["earnings_quality"])
    payload["assessments"][1]["rationale"] += (
        " Supported adjusted EBITDA stays {T1D.3.supported.value|US$ m}."
    )
    assert cp1d.validation_issues(_inputs("positive", payload)) == ()


def test_basis_fact_cites_the_analyst_citation() -> None:
    """The source-supported amount cites the accepted basis as given (source, locator, quote)."""
    payload = SUBMISSIONS["positive"]["earnings_quality"]
    result = cp1d.compute(_inputs("positive", payload))
    basis = {f.fact_id: f for f in result.facts}["T1D.2.a01.basis"]
    given = payload["assessments"][0]["accepted_basis"]
    assert [c.model_dump() for c in basis.citations] == [given]


def test_bridge_table_rule() -> None:
    synthetic = MANIFEST["synthetic_source"]
    fixture = synthetic["fixtures"]["bridge_table_not_found"]["pages"]
    assert cp1d.parse_bridge([p["text"] for p in fixture]) is None
    gap = cp1d.parse_bridge([p["text"] for p in synthetic["gap"]["pages"]])
    assert gap is not None
    assert gap.items[-1].amount is None
    assert gap.proposed_total is None and gap.management_ebitda is None


@pytest.mark.skip(reason="Stage 2/4: needs a store, a CP-1 promotion and G1 execution")
def test_stage2_execution_sections() -> None:
    """cases.refused, tool_refusals, the blocked head, cp1_readiness, module_status,
    settled_limitations, execution, consumption and the CP-1B inherited lines."""
