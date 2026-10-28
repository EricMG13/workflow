"""CP-1D Stage 1: the pure calculation against the frozen oracle `cases/cp1d-owner`.

Every input is built from the oracle's own files (manifest pages and figures, submissions,
the financial pack); every expectation is read from `expected.json`. Nothing here derives an
expected value.
"""

import copy
import dataclasses
import hashlib
import json
import re
from collections.abc import Sequence
from decimal import ROUND_HALF_EVEN, Context, Decimal
from pathlib import Path
from typing import Any

import pytest
from defect_classes import (
    BLANK_CASES,
    EMPTY_TEXT,
    FIGURE_CASES,
    BlankCase,
    QuoteCase,
    blank_failure,
    quote_failure,
)
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from deploy_vii import quotes
from deploy_vii.contracts import Citation, Source, Span
from deploy_vii.readiness import citation_issues
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
            # manifest `figures.<name>.fact_id` is bound at run time (Stage 2); Stage 1 names the
            # fact by the module's own reference to it, `cp1:<figure>` (`cell_notation`).
            fact_id=f"cp1:{name}",
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
    pack: str,
    payload: dict[str, Any],
    cp1b: cp1d.Cp1bState = "unbound",
    cp1: cp1d.Cp1Operands | None = None,
) -> cp1d.EarningsQualityInputs:
    return cp1d.EarningsQualityInputs(
        sources=_pack_sources(pack),
        cp1=_cp1() if cp1 is None else cp1,
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
        got: Any = record[key]
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


A03_BASIS = "They were 0.20 in each of the four quarters"
SOFT_HYPHEN = "­"
A03_QUOTES = {
    "basis": A03_BASIS,
    # CP-8 adversary M1 class: the quote matches with U+00AD deleted, and the kept amount is
    # read from that same text (0.20, the amount the page states).
    "basis, U+00AD in the figure": A03_BASIS.replace("0.20", f"0.{SOFT_HYPHEN}20"),
}


@pytest.mark.parametrize("given", ["fraction", *A03_QUOTES])
def test_partly_supported_recurring_composes_as_zero(given: str) -> None:
    """Lease recipe: Recurring forces f = 0, and accepted is a known 0 from applied_fraction.

    In the positive case a03 (Supported, Recurring) already has f = 0, so every fact, table,
    claim and limitation equals the oracle except a03's achievability text."""
    payload = copy.deepcopy(SUBMISSIONS["positive"]["earnings_quality"])
    a03 = payload["assessments"][2]
    a03["achievability"] = "Partly supported"
    if given == "fraction":
        a03["accepted_fraction"] = "0.50"
    else:
        a03["accepted_basis"] = {**a03["evidence"][0], "quote": A03_QUOTES[given]}
    inputs = _inputs("positive", payload)
    assert cp1d.validation_issues(inputs) == ()
    result = cp1d.compute(inputs)
    base = EXPECTED["cases"]["positive"]
    achievability = {"text": "Partly supported", "shown": "Partly supported"}
    want = [
        {**f, **achievability} if f["fact_id"] == "T1D.2.a03.achievability" else f
        for f in base["facts"]
    ]
    limitations = list(base["own_limitations"])
    if given != "fraction":
        # Rulings 1D2 + round 2: the cited amount stays a known source fact, with one own line.
        quote = {"source_id": "bridge", "locator": "page:2", "quote": A03_QUOTES[given]}
        basis = {
            "fact_id": "T1D.2.a03.basis",
            "table_id": "T1D.2",
            "row_id": "a03",
            "field": "basis",
            "label": "Source-supported amount",
            "status": "known",
            "unit": "MILLIONS",
            "period": base["cp1_references"][0]["period"],
            "amount_exact": "0.2",
            "shown": "0.20",
            "currency": "USD",
            "scale": "1000000",
            "decimals": 2,
            "value_class": "source",
            "formula": "Amount in the cited quote",
            "calculation_id": None,
            "derives_from": [],
            "citations": [quote],
            "limitation": None,
        }
        want = [basis if f["fact_id"] == "T1D.2.a03.basis" else f for f in want]
        limitations.insert(
            1,
            "Recurring add-back excluded although a source amount is cited: "
            "Legal and advisory fees.",
        )
    _assert_facts(result, want)
    assert _tables(result) == base["tables"]
    assert _claims(result) == base["claims"]
    assert list(result.limitations) == limitations
    assert _operands(result) == base["operands"]


def _with_adjusted_ebitda(amount: Decimal) -> cp1d.Cp1Operands:
    cp1 = _cp1()
    return dataclasses.replace(
        cp1, adjusted_ebitda=dataclasses.replace(cp1.adjusted_ebitda, amount=amount)
    )


def _not_meaningful(label: str) -> str:
    return f"Not meaningful: {label} is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"


@pytest.mark.parametrize("amount", ["-5", "0", "-10"])
@pytest.mark.parametrize("case", CASES)
def test_nonpositive_ebitda_settles(case: str, amount: str) -> None:
    """Ruling 1D3: ratios and shares on a basis whose EBITDA is <= 0 are not meaningful; the
    CP-1 controls compare nothing; validation and compute never raise for it."""
    inputs = _inputs(
        case, SUBMISSIONS[case]["earnings_quality"], cp1=_with_adjusted_ebitda(Decimal(amount))
    )
    assert cp1d.validation_issues(inputs) == ()
    facts = {f.fact_id: f for f in cp1d.compute(inputs).facts}
    statements = _not_meaningful("Adjusted EBITDA, statements (CP-1)")
    for name in ("cfo_to_ebitda", "total_leverage", "net_leverage"):
        fact = facts[f"T1D.6.statements.{name}"]
        assert (fact.status, fact.limitation, fact.cell_state) == (
            "not_applicable",
            statements,
            "not_meaningful",
        )
    for row, figure in (
        ("cp1_total_leverage", "total_leverage_adjusted"),
        ("cp1_net_leverage", "net_leverage_adjusted"),
    ):
        reported = facts[f"T1D.4.{row}.reported"]
        assert (reported.status, reported.amount_exact) == (
            "known",
            MANIFEST["figures"][figure]["amount_exact"],
        )
        recomputed = facts[f"T1D.4.{row}.recomputed"]
        assert (recomputed.status, recomputed.limitation) == ("not_applicable", statements)
        difference = facts[f"T1D.4.{row}.difference"]
        assert (difference.status, difference.limitation) == (
            "missing",
            "Not compared: one side is not available",
        )
        assert facts[f"T1D.4.{row}.result"].text == "Not compared"
    management = facts["T1D.3.mgmt.value"]
    if management.amount is not None and management.amount <= 0:
        # Round 4 (i): a T1D.5 share uses its own denominator's label.
        want = _not_meaningful("Management financing-case EBITDA")
        share = facts["T1D.5.management.value"]
        assert (share.status, share.limitation) == ("not_applicable", want)
        assert facts["T1D.6.management.net_leverage"].limitation == want
    supported = facts["T1D.3.supported.value"]
    assert supported.amount is not None
    if supported.amount <= 0:
        share = facts["T1D.5.supported.value"]
        want = _not_meaningful("Supported adjusted EBITDA")
        assert (share.status, share.limitation) == ("not_applicable", want)
        assert facts["T1D.6.supported.total_leverage"].limitation == want


def test_cp1_reported_leverage_keeps_cp1_status() -> None:
    """Ruling 1D3: the reported side of a CP-1 control keeps CP-1's own status."""
    cp1 = _cp1()
    limitation = "Not meaningful: EBITDA is zero or negative (ZERO_OR_NEGATIVE_DENOMINATOR)"
    unsettled = dataclasses.replace(
        cp1.total_leverage, amount=None, status="not_applicable", limitation=limitation
    )
    inputs = _inputs(
        "positive",
        SUBMISSIONS["positive"]["earnings_quality"],
        cp1=dataclasses.replace(cp1, total_leverage=unsettled),
    )
    result = cp1d.compute(inputs)
    facts = {f.fact_id: f for f in result.facts}
    reported = facts["T1D.4.cp1_total_leverage.reported"]
    assert (reported.status, reported.amount, reported.limitation) == (
        "not_applicable",
        None,
        limitation,
    )
    assert facts["T1D.4.cp1_total_leverage.recomputed"].status == "known"
    assert facts["T1D.4.cp1_total_leverage.result"].text == "Not compared"
    ref = next(r for r in result.cp1_references if r.figure == "total_leverage_adjusted")
    assert (ref.status, ref.amount_exact, ref.shown) == ("not_applicable", None, None)


@pytest.mark.parametrize(
    ("where", "value"),
    [
        ("confidence", "high"),
        ("confidence", "HIGH"),
        ("confidence", "Very high"),
        ("category", "Whatever"),
        ("severity", "Whatever"),
    ],
)
def test_judgment_enums_are_the_product_literals(where: str, value: str) -> None:
    payload = copy.deepcopy(SUBMISSIONS["positive"]["earnings_quality"])
    if where == "severity":
        payload["gaps"][0]["severity"] = value
    elif where == "category":
        payload["assessments"][0]["category"] = value
    else:
        payload["overall"]["confidence"] = value
    with pytest.raises(ValidationError):
        cp1d.EarningsQualitySubmission.model_validate_json(json.dumps(payload))


def test_partial_composition_resolves_module_totals_only() -> None:
    """r03 fails a01's shape; a02 naming a module total is not an issue, an unknown id is."""
    refusal = _submitted_refusal("r03")
    payload = copy.deepcopy(refusal["payload"])
    payload["assessments"][1]["rationale"] += " Supported EBITDA is {T1D.3.supported.value|US$ m}."
    issues = cp1d.validation_issues(_inputs("positive", payload))
    assert list(issues) == refusal["expected_issues"]
    payload["assessments"][1]["rationale"] += " Nothing is {T1D.9.none.value|US$ m}."
    issues = cp1d.validation_issues(_inputs("positive", payload))
    assert list(issues) == [*refusal["expected_issues"], "Unresolved reference: T1D.9.none.value"]


@pytest.mark.parametrize("case", CASES)
def test_module_ids_equal_a_full_composition(case: str) -> None:
    inputs = _case_inputs(case)
    result = cp1d.compute(inputs)
    source = next((s for s in inputs.sources if s.source_id == "bridge"), None)
    bridge = None if source is None else cp1d.parse_bridge([p.text for p in source.spans])
    ids = cp1d.module_fact_ids(bridge, len(inputs.submission.gaps))
    assert ids == frozenset(f.fact_id for f in result.facts)


def _bridge_inputs(page1: str, payload: dict[str, Any]) -> cp1d.EarningsQualityInputs:
    """The positive pack with page:1 of the bridge replaced; citations re-pinned to its hash."""
    page2 = MANIFEST["synthetic_source"]["positive"]["pages"][1]
    pages = [{"locator": "page:1", "text": page1}, page2]
    sha = hashlib.sha256("\f".join(p["text"] for p in pages).encode()).hexdigest()
    payload = copy.deepcopy(payload)
    for assessment in payload["assessments"]:
        for citation in [*assessment["evidence"], assessment["accepted_basis"]]:
            if citation is not None:
                citation["source_sha256"] = sha
    inputs = _inputs("positive", payload)
    bridge = _source("bridge", MANIFEST["synthetic_source"]["name"], pages, sha)
    frozen = tuple(s for s in inputs.sources if s.source_id != "bridge")
    return dataclasses.replace(inputs, sources=(*frozen, bridge))


POSITIVE_PAGE1 = MANIFEST["synthetic_source"]["positive"]["pages"][0]["text"]
HEADER = "Item  Type  Status  Amount"


UNUSABLE_PAGES = {
    "1D4 type": POSITIVE_PAGE1.replace("fees  Cost  Incurred", "fees  Expense  Incurred"),
    "1D5 blank line": POSITIVE_PAGE1 + "\n",
    "1D5 stray row": POSITIVE_PAGE1 + "\nRounding  0.01",
    "1D5 duplicate total": POSITIVE_PAGE1 + "\nTotal proposed adjustments  6.00",
    "1D5 non-decimal": POSITIVE_PAGE1.replace("Unrealised  1.00", "Unrealised  1,00"),
    "1D9 no rows": POSITIVE_PAGE1.split(HEADER)[0] + HEADER,
    "digits": POSITIVE_PAGE1.replace("Unrealised  1.00", "Unrealised  1." + "0" * 250 + "1"),
    # Round 4 (k): the product `financial_contracts.Number` bound.
    "(k) 11 places": POSITIVE_PAGE1.replace("Unrealised  1.00", "Unrealised  1.00000000001"),
    "(k) 1e18": POSITIVE_PAGE1.replace("Unrealised  1.00", "Unrealised  1" + "0" * 18 + ".00"),
    "(k) 30 digits": POSITIVE_PAGE1.replace(
        "Unrealised  1.00", "Unrealised  " + "9" * 17 + ".1234567890123"
    ),
    # Round 10: `_bridge_amount` keeps its unsigned full match.
    "round 10 minus": POSITIVE_PAGE1.replace("Unrealised  1.00", "Unrealised  -1.00"),
    "round 10 parentheses": POSITIVE_PAGE1.replace("Unrealised  1.00", "Unrealised  (1.00)"),
}


@pytest.mark.parametrize("ruling", UNUSABLE_PAGES)
def test_unusable_bridge_table_is_not_found(ruling: str) -> None:
    page1 = UNUSABLE_PAGES[ruling]
    assert cp1d.parse_bridge([page1]) is None
    inputs = _bridge_inputs(page1, SUBMISSIONS["positive"]["earnings_quality"])
    assert cp1d.validation_issues(inputs) == ("Bridge table not found",)
    with pytest.raises(ValueError):
        cp1d.compute(inputs)


def test_amount_inside_the_product_bound_composes() -> None:
    """Round 4 (k): 18 whole digits and 10 places is still a bridge amount."""
    page1 = POSITIVE_PAGE1.replace("Unrealised  1.00", "Unrealised  " + "9" * 17 + ".0123456789")
    inputs = _bridge_inputs(page1, SUBMISSIONS["positive"]["earnings_quality"])
    assert cp1d.validation_issues(inputs) == ()
    claimed = {f.fact_id: f for f in cp1d.compute(inputs).facts}["T1D.1.a04.claimed"]
    assert claimed.amount_exact == "9" * 17 + ".0123456789"


LONG_DECIMAL = "0." + "0" * 250 + "1"


EXACTNESS = "Accepted basis amount cannot be held exactly as a product amount: "
BOUNDS = "Accepted basis must be above 0 and below the proposed amount: "
EXACTLY_ONE = "Accepted basis quote must contain exactly one amount: "


@pytest.mark.parametrize(
    ("case", "row", "amount", "issue"),
    [
        # Round 5b Y4: precision beyond ten places is not a bounds failure.
        ("positive", 0, LONG_DECIMAL, EXACTNESS),
        ("positive", 2, LONG_DECIMAL, EXACTNESS),  # Partly supported + Recurring keeps the basis
        ("positive", 0, "1.12345678901", EXACTNESS),  # between 0 and the proposed 3.00
        ("positive", 0, "20.12345678901", EXACTNESS),  # checked before the bounds comparison
        # Y4: at or above 1e18 against a stated proposed amount, the bounds text is true.
        ("positive", 0, "1" + "0" * 18, BOUNDS),
        # Y4: the Recurring path on an unstated proposed amount has no bound to compare with.
        ("gap", 3, "1" + "0" * 18, EXACTNESS),
    ],
)
def test_basis_amount_outside_the_product_bound_is_an_issue(
    case: str, row: int, amount: str, issue: str
) -> None:
    """Fix round 2 N1 and round 5b Y4: a quoted basis amount outside `financial_contracts.Number`
    is a step-6 shape failure, returned alone, that never reaches composition."""
    assert _basis_issues(case, row, amount) == (f"{issue}{_label(case, row)}",)


@pytest.mark.parametrize(
    ("case", "row", "amount"),
    [
        # Round 10: a signed amount against a stated proposed amount, before the exactness test.
        ("positive", 0, "-1.80"),
        ("positive", 0, "(1.80)"),
        ("positive", 0, "-0.00000000001"),
        ("positive", 0, "-1" + "0" * 18),
        ("positive", 2, "-0.50"),  # Partly supported + Recurring, below the proposed 0.80
        # LEAD round 10: "above 0" applies on its own on an unstated proposed amount (the
        # Recurring path), also before the exactness test.
        ("gap", 3, "0"),
        ("gap", 3, "-1.80"),
        ("gap", 3, "(1.80)"),
        ("gap", 3, "-" + LONG_DECIMAL),
    ],
)
def test_basis_amount_at_or_below_zero_is_the_bounds_issue(
    case: str, row: int, amount: str
) -> None:
    """Round 10: the quote's sign is read, and a basis of 0 or less gets step 6's bounds text."""
    assert _basis_issues(case, row, amount) == (f"{BOUNDS}{_label(case, row)}",)


def _label(case: str, row: int) -> str:
    return str(SUBMISSIONS[case]["earnings_quality"]["assessments"][row]["addback"])


def _basis_issues(case: str, row: int, amount: str) -> tuple[str, ...]:
    """Row `row` made Partly supported (Recurring in the gap pack, whose amount is unstated)
    with a basis quote `a saving of <amount>`."""
    payload = copy.deepcopy(SUBMISSIONS[case]["earnings_quality"])
    assessment = payload["assessments"][row]
    assessment["achievability"] = "Partly supported"
    if case == "gap":
        assessment["recurrence"] = "Recurring"
    assessment["accepted_basis"] = {
        **(
            assessment["evidence"]
            or SUBMISSIONS["positive"]["earnings_quality"]["assessments"][0]["evidence"]
        )[0],
        "quote": f"a saving of {amount}",
    }
    return cp1d.validation_issues(_inputs(case, payload))


# CP-8 adversary M1 class: `citation_issues` matches a quote through `quotes.normalise` (U+00AD
# deleted, each `quotes._DASHES` character as "-"), so the basis amount is read from that text.
A01_BASIS = "Signed supplier contracts cover an annualised saving of 1.80."
A01_LABEL = "Procurement programme savings"


def _replaced(text: str, old: str, new: str) -> str:
    changed = text.replace(old, new)
    assert changed != text, (text, old)
    return changed


@pytest.mark.parametrize(
    "figure", [f"1{SOFT_HYPHEN}.80", f"1.{SOFT_HYPHEN}80", f"1.8{SOFT_HYPHEN}0"]
)
def test_soft_hyphen_in_the_basis_figure_composes_the_page_amount(figure: str) -> None:
    """The source path (`_outcome`): the page states one amount, 1.80, so a01 composes exactly
    the oracle's facts; the basis fact keeps the citation as given."""
    payload = copy.deepcopy(SUBMISSIONS["positive"]["earnings_quality"])
    basis = payload["assessments"][0]["accepted_basis"]
    assert basis["quote"] == A01_BASIS
    basis["quote"] = _replaced(A01_BASIS, "1.80", figure)
    inputs = _inputs("positive", payload)
    assert cp1d.validation_issues(inputs) == ()
    want = [
        {**f, "citations": [{**f["citations"][0], "quote": basis["quote"]}]}
        if f["fact_id"] == "T1D.2.a01.basis"
        else f
        for f in EXPECTED["cases"]["positive"]["facts"]
    ]
    _assert_facts(cp1d.compute(inputs), want)


R17_QUOTE = _submitted_refusal("r17")["payload"]["assessments"][0]["accepted_basis"]["quote"]
YEAR_QUOTE = "One-time costs to achieve the saving are expected in 2026."


@pytest.mark.parametrize(
    "quote",
    [
        _replaced(R17_QUOTE, "3.00", f"3{SOFT_HYPHEN}.00"),
        _replaced(R17_QUOTE, "3.00", f"3.0{SOFT_HYPHEN}0"),
        # Read as written, the first run (2) lies below the proposed 3.00 and would compose.
        _replaced(YEAR_QUOTE, "2026", f"2{SOFT_HYPHEN}026"),
    ],
)
def test_soft_hyphen_in_the_basis_figure_meets_the_bounds_rule(quote: str) -> None:
    """The bounds step (`_shape_issue`): a page:2 quote with U+00AD inside its figure still
    holds one amount, not below the proposed 3.00, so the issue is r17's own bounds text."""
    refusal = _submitted_refusal("r17")
    payload = copy.deepcopy(refusal["payload"])
    payload["assessments"][0]["accepted_basis"]["quote"] = quote
    inputs = _inputs(refusal["pack"], payload)
    accepted = inputs.submission.assessments[0].accepted_basis
    assert accepted is not None
    assert citation_issues((accepted,), inputs.sources) == ()
    assert list(cp1d.validation_issues(inputs)) == refusal["expected_issues"]


@pytest.mark.parametrize("dash", [chr(c) for c in quotes._DASHES], ids=lambda c: f"U+{ord(c):04X}")
def test_dash_in_the_basis_figure_reads_like_the_match(dash: str) -> None:
    """Not reproduced (guard): the amount pattern reads ASCII digits and '.', and a mapped dash
    or minus becomes '-', so both readings hold the same two amounts and r18's rule refuses."""
    line = "Signed contracts cover 1.20-1.80 of the saving."
    page1 = _replaced(POSITIVE_PAGE1, HEADER, f"{line}\n{HEADER}")
    payload = copy.deepcopy(SUBMISSIONS["positive"]["earnings_quality"])
    payload["assessments"][0]["accepted_basis"].update(
        locator="page:1", quote=_replaced(line, "-", dash)
    )
    inputs = _bridge_inputs(page1, payload)
    accepted = inputs.submission.assessments[0].accepted_basis
    assert accepted is not None
    assert citation_issues((accepted,), inputs.sources) == ()
    assert cp1d.validation_issues(inputs) == (
        f"Accepted basis quote must contain exactly one amount: {A01_LABEL}",
    )


# Round 10 (LEAD, figure signs in quote readers): the basis amount is the signed numeral the
# normalised quote prints. A "-" before the first digit is a minus when it starts the quote or
# follows a character that is neither a letter nor a digit; "+" is ignored; a numeral in
# accounting parentheses reads as negative.
A01_LINE = "Signed contracts cover an annualised saving of {}."
SIGNED_FIGURES = {
    "U+2212": "\u22121.80",
    "ASCII": "-1.80",
    "U+2013": "\u20131.80",
    "parentheses": "(1.80)",
}


def _a01_on_page1(line: str) -> cp1d.EarningsQualityInputs:
    """The positive pack with `line` printed on page:1 and quoted as a01's accepted basis."""
    page1 = _replaced(POSITIVE_PAGE1, HEADER, f"{line}\n{HEADER}")
    payload = copy.deepcopy(SUBMISSIONS["positive"]["earnings_quality"])
    payload["assessments"][0]["accepted_basis"].update(locator="page:1", quote=line)
    inputs = _bridge_inputs(page1, payload)
    accepted = inputs.submission.assessments[0].accepted_basis
    assert accepted is not None
    assert citation_issues((accepted,), inputs.sources) == ()
    return inputs


@pytest.mark.parametrize("figure", SIGNED_FIGURES.values(), ids=SIGNED_FIGURES.keys())
def test_signed_basis_figure_meets_the_bounds_rule(figure: str) -> None:
    """A page printing a minus (or parentheses) before 1.80 states -1.80, below 0, so a01 gets
    step 6's pinned bounds text instead of composing an unsigned 1.80."""
    inputs = _a01_on_page1(A01_LINE.format(figure))
    assert cp1d.validation_issues(inputs) == (f"{BOUNDS}{A01_LABEL}",)


@pytest.mark.parametrize(
    ("line", "issues"),
    [
        ("From 1-December, signed contracts cover the saving.", ()),
        ("Supplier contract S-1.80 covers the annualised saving.", ()),
        (A01_LINE.format("+1.80"), ()),
        (A01_LINE.format("(1.80 million)"), ()),
        ("Savings were signed over 2024-2025.", (f"{EXACTLY_ONE}{A01_LABEL}",)),
        ("Savings were 95-96 percent signed.", (f"{EXACTLY_ONE}{A01_LABEL}",)),
    ],
)
def test_hyphen_after_a_letter_or_digit_is_not_a_sign(line: str, issues: tuple[str, ...]) -> None:
    """Non-sign forms read unsigned: a single amount below the proposed 3.00 composes, and a
    range still holds two amounts (step 5)."""
    assert cp1d.validation_issues(_a01_on_page1(line)) == issues


@pytest.mark.parametrize(
    ("quote", "amounts"),
    [
        ("from 1-December", ["1"]),
        ("over 2024-2025", ["2024", "2025"]),
        ("the 95-96 range", ["95", "96"]),
        ("contract S-350", ["350"]),
        ("a saving of +1.80", ["1.80"]),
        ("(4.30 percent)", ["4.30"]),
        ("-1.80 saved", ["-1.80"]),
        ("a saving of (1.80)", ["-1.80"]),
        ("a saving of \u22121.80", ["-1.80"]),
        ("a saving of \u20141.80", ["-1.80"]),
        ("a saving of 1.80 and 2.40", ["1.80", "2.40"]),
        # Round 10 review Low: the "(" side is required; ")" alone after the digits is unsigned.
        ("saving 1.80)", ["1.80"]),
    ],
)
def test_basis_amounts_read_the_printed_sign(quote: str, amounts: list[str]) -> None:
    """Step 5 counts signed tokens; counts on unsigned text do not change. These quotes are not
    on the cited page, so no occurrence can show an edge cut (round 11 B1): the citation check
    refuses them instead."""
    citation = Citation.model_validate(
        {
            **SUBMISSIONS["positive"]["earnings_quality"]["assessments"][0]["accepted_basis"],
            "quote": quote,
        }
    )
    assert cp1d._basis_amounts(citation, _pack_sources("positive")) == amounts


@pytest.mark.parametrize("amount", ["-1.80", "(1.80)", "0"])
def test_unstated_amount_rule_precedes_the_bounds_text(amount: str) -> None:
    """Round 10 review Low (ruling 1D7 ahead of round 10's "above 0"): an accepting row that is
    not Recurring, on an unstated proposed amount, gets `Cannot accept an unstated amount` and no
    bounds text, whatever the sign of its basis."""
    payload = copy.deepcopy(SUBMISSIONS["gap"]["earnings_quality"])
    a04 = payload["assessments"][3]
    assert a04["recurrence"] == "Not applicable"
    a04["achievability"] = "Partly supported"
    a04["accepted_basis"] = {
        **SUBMISSIONS["positive"]["earnings_quality"]["assessments"][0]["evidence"][0],
        "quote": f"a saving of {amount}",
    }
    issues = cp1d.validation_issues(_inputs("gap", payload))
    label = _label("gap", 3)
    assert issues[:2] == (
        f"Evidence required for an accepted add-back: {label}",
        f"Cannot accept an unstated amount: {label}",
    )
    assert not [issue for issue in issues if issue.startswith(BOUNDS)]


@pytest.mark.parametrize(("numerator", "denominator"), [("2.5", "30"), ("1", "30"), ("-1", "30")])
def test_cp1_ratio_at_cp1_precision_binds(numerator: str, denominator: str) -> None:
    """Fix round 2 N2: CP-1's own 38-digit quotients below 0.1x are CP-1 facts and bind."""
    value = Context(prec=38, rounding=ROUND_HALF_EVEN).divide(
        Decimal(numerator), Decimal(denominator)
    )
    cp1 = _cp1()
    cp1 = dataclasses.replace(cp1, net_leverage=dataclasses.replace(cp1.net_leverage, amount=value))
    payload = SUBMISSIONS["positive"]["earnings_quality"]
    facts = {f.fact_id: f for f in cp1d.compute(_inputs("positive", payload, cp1=cp1)).facts}
    assert facts["T1D.4.cp1_net_leverage.reported"].amount == value
    assert facts["T1D.4.cp1_net_leverage.result"].text == "Differs"


@pytest.mark.parametrize("amount", ["1E-38", "1" + "0" * 18])
@pytest.mark.parametrize("figure", ["total_debt", "adjusted_ebitda"])
def test_cp1_amount_outside_the_product_bound_is_an_invariant_raise(
    figure: str, amount: str
) -> None:
    """Round 5b Y1 (1D-y): an invariant raise naming the CP-1 fact, not a refusal."""
    cp1 = _cp1()
    operand = getattr(cp1, figure)
    want = (
        f"CP-1 fact {operand.fact_id} ({operand.figure}) is outside financial_contracts.Number; "
        "CP-1D cannot hold it exactly"
    )
    with pytest.raises(ValueError) as raised:
        dataclasses.replace(operand, amount=Decimal(amount))
    assert str(raised.value) == want


ORACLE_PINS = {
    # docs/CP1D-OWNER-LEASE.md header, oracle amendment 1D1 (LEAD 2026-10-28).
    "expected.json": "6015b443603b16f9af8c5417e6fa69f7468fa243f37b64575f745aac6549bd8c",
    "manifest.json": "7e1766071125b41fb459428f37e90166f9f35f2a806310a2f74baf81e926f585",
    "submissions.json": "e19bc64bf6b9d388ca355fcb5de5160be1c4c0e7e27d3b348f1996a17fbd93d7",
}


@pytest.mark.parametrize("name", ORACLE_PINS)
def test_oracle_is_the_pinned_revision(name: str) -> None:
    assert hashlib.sha256((CASE / name).read_bytes()).hexdigest() == ORACLE_PINS[name]


def test_reported_bridge_totals_cite_their_line() -> None:
    """Ruling 1D1 / oracle amendment: the two stated totals cite their bridge total line."""
    facts = {f.fact_id: f for f in cp1d.compute(_case_inputs("positive")).facts}
    sha = MANIFEST["synthetic_source"]["positive"]["sha256"]
    for fact_id, line in (
        ("T1D.4.proposed_total.reported", "Total proposed adjustments  6.00"),
        ("T1D.4.mgmt_ebitda.reported", "Management financing-case EBITDA  36.00"),
    ):
        assert [c.model_dump() for c in facts[fact_id].citations] == [
            {"source_id": "bridge", "source_sha256": sha, "locator": "page:1", "quote": line}
        ]


def test_missing_bridge_source_is_not_found() -> None:
    """Round 5b Y2: 1D-x covers a bridge source CP-0 marks `missing`."""
    missing = Source(
        source_id="bridge",
        name=MANIFEST["synthetic_source"]["name"],
        status="missing",
        limitation="Not supplied",
    )
    inputs = _case_inputs("positive")
    frozen = tuple(s for s in inputs.sources if s.source_id != "bridge")
    inputs = dataclasses.replace(inputs, sources=(*frozen, missing))
    assert cp1d.validation_issues(inputs) == ("Bridge table not found",)


FULL_ONLY = sorted(
    cp1d.module_fact_ids(
        cp1d.parse_bridge([p["text"] for p in MANIFEST["synthetic_source"]["positive"]["pages"]]),
        1,
    )
    - {f"T1D.1.a{n:02d}.{name}" for n in range(1, 5) for name in ("type", "status", "claimed")}
    - {"T1D.1.stmt.type", "T1D.1.stmt.status", "T1D.1.stmt.claimed"}
    - {f"T1D.2.a{n:02d}.{name}" for n in range(2, 5) for name in cp1d._ASSESSMENT_FIELDS}
)


@settings(max_examples=150, deadline=None)
@given(
    ref=st.sampled_from(FULL_ONLY),
    form=st.sampled_from(["{%s}", "{%s|US$ m}", "{%s|%%}", "{%s|x}", "[%s]", "{calc:%s|US$ m}"]),
)
def test_partial_checks_never_exceed_the_full_check(ref: str, form: str) -> None:
    """Round 5b Y3 (c): under r03 (a01 fails its shape) a02's references to facts only a full
    composition carries report no issue the full module does not also report."""
    refusal = _submitted_refusal("r03")
    text = " See " + form % ref + "."
    partial = copy.deepcopy(refusal["payload"])
    partial["assessments"][1]["rationale"] += text
    full = copy.deepcopy(SUBMISSIONS["positive"]["earnings_quality"])
    full["assessments"][1]["rationale"] += text
    full_issues = set(cp1d.validation_issues(_inputs("positive", full)))
    partial_issues = set(cp1d.validation_issues(_inputs("positive", partial)))
    assert partial_issues - set(refusal["expected_issues"]) <= full_issues


@pytest.mark.parametrize("sha256", [None, MANIFEST["synthetic_source"]["positive"]["sha256"]])
def test_unreadable_bridge_is_not_found_before_parse(sha256: str | None) -> None:
    """Ruling 1D-x: CP-0's `unreadable` status governs; hash and spans are not read."""
    synthetic = MANIFEST["synthetic_source"]
    unreadable = Source(
        source_id="bridge",
        name=synthetic["name"],
        status="unreadable",
        sha256=sha256,
        spans=tuple(
            Span(locator=p["locator"], text=p["text"]) for p in synthetic["positive"]["pages"]
        ),
        limitation="Unreadable",
    )
    inputs = _case_inputs("positive")
    frozen = tuple(s for s in inputs.sources if s.source_id != "bridge")
    inputs = dataclasses.replace(inputs, sources=(*frozen, unreadable))
    assert cp1d.validation_issues(inputs) == ("Bridge table not found",)


def test_issue_order_follows_ruling_1d10() -> None:
    """Assessment set first, then per assessment in submission order: evidence, recurrence,
    unstated amount, citations, prose; then overall."""
    payload = copy.deepcopy(SUBMISSIONS["gap"]["earnings_quality"])
    a04 = payload["assessments"][3]
    a04.update(achievability="Partly supported", accepted_fraction="0.50")
    a04["recurrence"] = "Non-recurring"
    a03 = payload["assessments"][2]
    a03["rationale"] += " It was 0.2."
    payload["assessments"] = [a04, a03, *payload["assessments"][:2]]
    payload["overall"]["confidence"] = "High"
    issues = cp1d.validation_issues(_inputs("gap", payload))
    label = "Insurance and facilities savings"
    assert list(issues) == [
        f"Evidence required for an accepted add-back: {label}",
        f"Recurrence does not fit the add-back type: {label}",
        f"Cannot accept an unstated amount: {label}",
        "Bare figure: 0.2",
        "Confidence cannot be High: the add-back evidence is management-supplied",
    ]


@pytest.mark.parametrize(
    "ref",
    [
        "{calc:T1D.3.supported.value|US$ m}",
        "{T1D.3.supported.value|%}",
        "{T1D.4.cp1_total_leverage.result|x}",
        "{T1D.6.supported.total_leverage|US$ m}",
    ],
)
def test_partial_composition_checks_like_the_full_module(ref: str) -> None:
    """Reviewer L-a/L-b: under r03 (a01 shape failure) a02's references to facts only a full
    composition carries give exactly the issues the full module gives them."""
    refusal = _submitted_refusal("r03")
    partial = copy.deepcopy(refusal["payload"])
    partial["assessments"][1]["rationale"] += f" See {ref}."
    full = copy.deepcopy(SUBMISSIONS["positive"]["earnings_quality"])
    full["assessments"][1]["rationale"] += f" See {ref}."
    full_issues = list(cp1d.validation_issues(_inputs("positive", full)))
    partial_issues = list(cp1d.validation_issues(_inputs("positive", partial)))
    assert partial_issues == [*refusal["expected_issues"], *full_issues]


# --- shared defect classes (AGENTS.md rules 3 and 4; LEAD round 11) -------------------------
# Quote cases: CP-1D reads one figure, the accepted basis amount, from the basis quote. It has no
# analyst figure, so a case's value is the amount its page states. The cases run on the gap
# pack's a04 made Partly supported + Recurring: its proposed amount is unstated, so only "above
# 0" bounds the basis (LEAD round 10) and any positive amount is accepted. Accepted cases there
# also get `Recurrence does not fit the add-back type`, which is outside the classes.

DEFECT_ROW = 3
DEFECT_LABEL = _label("gap", DEFECT_ROW)
DEFECT_BOUNDS = f"{BOUNDS}{DEFECT_LABEL}"
DEFECT_EXACTLY_ONE = f"{EXACTLY_ONE}{DEFECT_LABEL}"


def _defect_inputs(page: str, quote: str) -> cp1d.EarningsQualityInputs:
    """a04's basis cites `quote` on page:1 of a one-span source `defect` printing `page`."""
    sha = hashlib.sha256(page.encode()).hexdigest()
    payload = copy.deepcopy(SUBMISSIONS["gap"]["earnings_quality"])
    payload["assessments"][DEFECT_ROW].update(
        achievability="Partly supported",
        recurrence="Recurring",
        accepted_basis={
            "source_id": "defect",
            "source_sha256": sha,
            "locator": "page:1",
            "quote": quote,
        },
    )
    inputs = _inputs("gap", payload)
    page_source = _source("defect", "Defect-class page", [{"locator": "page:1", "text": page}], sha)
    return dataclasses.replace(inputs, sources=(*inputs.sources, page_source))


def _basis_adapter(page: str, quote: str, value: str) -> Sequence[str]:
    """The library `Adapter`; `value` is not placed anywhere (CP-1D has no analyst figure)."""
    return cp1d.validation_issues(_defect_inputs(page, quote))


_FIGURE = re.compile(r"[0-9]+(?:\.[0-9]+)?")


def _not_applicable(c: QuoteCase) -> str:
    """Why a figure case cannot be expressed in CP-1D ("" when it can)."""
    if c.accepted and Decimal(c.value) <= 0:
        return "an amount of 0 is the bounds refusal by design"
    if not c.accepted and c.defect == "soft_hyphen":
        return "no analyst figure to contradict: CP-1D composes the page's figure itself"
    if c.accepted and len(_FIGURE.findall(quotes.normalise(c.quote))) != 1:
        return "the quote prints two figures: the pinned exactly-one rule refuses it by design"
    return ""


QUOTE_CASES = [c for c in FIGURE_CASES if not _not_applicable(c)]


def test_defect_class_cases_not_applicable() -> None:
    """The cases CP-1D cannot express are exactly these (so a library change is seen here)."""
    assert {c.case_id for c in FIGURE_CASES if _not_applicable(c)} == {
        "genuine-0",
        "edge-start-0",
        *(
            f"{kind}-{f}"
            for kind in ("shy-prefix", "en-inside", "em-inside")
            for f in ("25", "1.25")
        ),
        "minus-inside-25",
        "minus-inside-1.25",
        "sign-2024-2025",
        "sign-95-96",
    }


@pytest.mark.parametrize("c", QUOTE_CASES, ids=lambda c: c.case_id)
def test_defect_class_basis_quote(c: QuoteCase) -> None:
    """Round 10 signs and parentheses, round 9 M1 normalisation, round 11 B1 edge cut. An edge
    cut is not counted, so the pinned exactly-one text fires (B1); a sign or accounting
    parentheses read as negative, so the pinned bounds text fires (round 10). An accepted case
    reads exactly the page's figure and gets neither."""
    refusal = DEFECT_EXACTLY_ONE if c.defect == "edge_cut" else DEFECT_BOUNDS
    assert quote_failure(c, _basis_adapter, refusal) is None
    inputs = _defect_inputs(c.page, c.quote)
    if c.accepted:
        issues = cp1d.validation_issues(inputs)
        assert DEFECT_BOUNDS not in issues
        assert DEFECT_EXACTLY_ONE not in issues
    basis = inputs.submission.assessments[DEFECT_ROW].accepted_basis
    assert basis is not None
    read = [c.value] if c.accepted else [] if c.defect == "edge_cut" else [f"-{c.value}"]
    assert cp1d._basis_amounts(basis, inputs.sources) == read


@pytest.mark.parametrize(
    ("page", "quote"),
    [
        # A page minus at a line end: the plain page reading holds "- 25", the joined one "-25".
        ("The level is -\n25 percent over the reference rate.", "25 percent over the reference"),
        # A wrapped quote found only with its wrap joined, cut at its end edge (250 on the page).
        ("The first-priority level is 250 percent.", "The first-\npriority level is 25"),
        # The same at its start edge (425 on the page): the joined quote keeps the offsets
        # from its start.
        ("The level is 425 first-priority points.", "25 first-\npriority points."),
    ],
)
def test_edge_cut_is_read_in_every_reading(page: str, quote: str) -> None:
    """Round 11 B1: every occurrence of the quote (as written and with its wraps joined) in every
    reading of the page (normalised, and with its wraps joined)."""
    inputs = _defect_inputs(page, quote)
    basis = inputs.submission.assessments[DEFECT_ROW].accepted_basis
    assert basis is not None
    assert citation_issues((basis,), inputs.sources) == ()
    assert DEFECT_EXACTLY_ONE in cp1d.validation_issues(inputs)
    assert cp1d._basis_amounts(basis, inputs.sources) == []


@pytest.mark.parametrize(
    ("page", "quote"),
    [
        ("The first-priority level is 25 percent.", "The first-\npriority level is 25"),
        ("The level is - 25 percent; it was 425 before.", "25 percent;"),
        ("The level is 25 first-priority points.", "25 first-\npriority points."),
        # Accounting parentheses need both sides: "(" before a start-edge figure whose ")" is
        # not right after it, or ")" after an end-edge figure with no "(" right before it.
        ("The level (25 percent over) holds.", "25 percent over) holds."),
        ("The level is 25) percent.", "The level is 25"),
    ],
)
def test_edge_figure_whole_on_the_page_is_counted(page: str, quote: str) -> None:
    """The twins: the same unsigned whole figure at every occurrence composes as the amount."""
    inputs = _defect_inputs(page, quote)
    basis = inputs.submission.assessments[DEFECT_ROW].accepted_basis
    assert basis is not None
    assert cp1d._basis_amounts(basis, inputs.sources) == ["25"]
    assert DEFECT_EXACTLY_ONE not in cp1d.validation_issues(inputs)


@pytest.mark.parametrize(
    ("page", "quote", "read", "refusal"),
    [
        # Start edge after a page ".": 25 is cut from 0.25.
        ("The level is 0.25 percent.", "25 percent.", [], DEFECT_EXACTLY_ONE),
        # End edge with only "." after the digits: 25.5 on the page is cut to "25.".
        ("The level is 25.5 percent.", "The level is 25.", [], DEFECT_EXACTLY_ONE),
        ("The level is 25. It holds.", "The level is 25.", ["25"], None),
        # Start edge with only a sign before the digits: the page character before them is the
        # quote's "-". A minus there (round 10) is not the unsigned whole figure, so it is not
        # counted; after a digit it is not a sign, and the quote's own -25 is read.
        ("The level is -25 percent over the rate.", "-25 percent over the", [], DEFECT_EXACTLY_ONE),
        (
            "The level is 4-25 percent over the rate.",
            "-25 percent over the",
            ["-25"],
            DEFECT_BOUNDS,
        ),
    ],
)
def test_edge_with_a_stop_or_a_sign(
    page: str, quote: str, read: list[str], refusal: str | None
) -> None:
    inputs = _defect_inputs(page, quote)
    basis = inputs.submission.assessments[DEFECT_ROW].accepted_basis
    assert basis is not None
    assert citation_issues((basis,), inputs.sources) == ()
    assert cp1d._basis_amounts(basis, inputs.sources) == read
    issues = cp1d.validation_issues(inputs)
    refusals = [issue for issue in issues if issue in (DEFECT_BOUNDS, DEFECT_EXACTLY_ONE)]
    assert refusals == ([] if refusal is None else [refusal])


def test_edge_cut_at_any_occurrence_is_not_counted() -> None:
    """Every occurrence is checked: one whole and one cut (from 425) is not counted."""
    page = "The level is 25 percent; it was 425 percent."
    inputs = _defect_inputs(page, "25 percent")
    basis = inputs.submission.assessments[DEFECT_ROW].accepted_basis
    assert basis is not None
    assert cp1d._basis_amounts(basis, inputs.sources) == []


# Blank text (round 11): every analyst text field. No CP-1D empty-text frame is pinned, so the
# fallback `<path>: empty text` applies. A `Text` field's "" is the schema's `min_length`
# refusal (controller decision, library fix 1); a `limitation` of "" gets the frame.
TEXT_FIELDS: dict[str, tuple[str, tuple[str | int, ...]]] = {
    "assessments[0].rationale": ("positive", ("assessments", 0, "rationale")),
    "assessments[0].limitation": ("positive", ("assessments", 0, "limitation")),
    "assessments[3].rationale": ("positive", ("assessments", 3, "rationale")),
    "assessments[2].limitation": ("positive", ("assessments", 2, "limitation")),
    "overall.rationale": ("positive", ("overall", "rationale")),
    "overall.limitation": ("positive", ("overall", "limitation")),
    "gaps[0].gap": ("gap", ("gaps", 0, "gap")),
    "gaps[0].why_it_matters": ("gap", ("gaps", 0, "why_it_matters")),
    "gaps[0].affected_analysis": ("gap", ("gaps", 0, "affected_analysis")),
    "gaps[0].action": ("gap", ("gaps", 0, "action")),
    "gaps[1].gap": ("gap", ("gaps", 1, "gap")),
    "gaps[1].action": ("gap", ("gaps", 1, "action")),
    "assessments[1].rationale": ("positive", ("assessments", 1, "rationale")),
    "assessments[1].limitation": ("gap", ("assessments", 1, "limitation")),
    "statements_only overall.rationale": ("statements_only", ("overall", "rationale")),
}


def _text_inputs(path: str, text: str) -> cp1d.EarningsQualityInputs:
    case, keys = TEXT_FIELDS[path]
    payload = copy.deepcopy(SUBMISSIONS[case]["earnings_quality"])
    if keys[:2] == ("gaps", 1):  # the fixtures hold one gap; a second copy of it
        payload["gaps"].append(copy.deepcopy(payload["gaps"][0]))
    target: Any = payload
    for key in keys[:-1]:
        target = target[key]
    target[keys[-1]] = text
    return _inputs(case, payload)


def _frame(path: str) -> str:
    return EMPTY_TEXT.format(path=path.split(" ")[-1])


@pytest.mark.parametrize("c", BLANK_CASES, ids=lambda c: c.case_id)
@pytest.mark.parametrize("path", TEXT_FIELDS)
def test_defect_class_blank_text(path: str, c: BlankCase) -> None:
    """Whitespace-only text gets `<path>: empty text` and nothing else on a valid case."""

    def adapter(page: str, quote: str, value: str) -> Sequence[str]:
        return cp1d.validation_issues(_text_inputs(path, value))

    assert blank_failure(c, adapter, _frame(path)) is None
    if c.whitespace_only:
        assert adapter(c.page, c.quote, c.value) == (_frame(path),)


def test_blank_text_is_refused_by_compute() -> None:
    with pytest.raises(ValueError, match=re.escape(_frame("gaps[0].action"))):
        cp1d.compute(_text_inputs("gaps[0].action", " \n"))


@pytest.mark.skip(reason="Stage 2/4: needs a store, a CP-1 promotion and G1 execution")
def test_stage2_execution_sections() -> None:
    """cases.refused, tool_refusals, the blocked head, cp1_readiness, module_status,
    settled_limitations, execution, consumption and the CP-1B inherited lines."""
