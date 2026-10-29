"""CP-2E Stage 1: the pure calculation equals the frozen oracle (cases/cp2e-owner).

Inputs come from the oracle's own literals (submissions.json) and the frozen financial pages
(cases/financial/manifest.json); every expected value is read from expected.json.
"""

import copy
import dataclasses
import json
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

import defect_classes as dc
import pytest

from deploy_vii import prose
from deploy_vii.contracts import Fact
from deploy_vii.quotes import normalise, reading
from deploy_workflow.owners import cp2e

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "cases" / "cp2e-owner"
EXPECTED: dict[str, Any] = json.loads((CASE / "expected.json").read_text(encoding="utf-8"))
SUBMISSIONS: dict[str, Any] = json.loads((CASE / "submissions.json").read_text(encoding="utf-8"))
_FIN: dict[str, Any] = json.loads(
    (ROOT / "cases" / "financial" / "manifest.json").read_text(encoding="utf-8")
)
_FIN_PAGES = {
    page["locator"]: page["text"]
    for source in _FIN["sources"]
    if source["source_id"] == "financial"
    for page in source["pages"]
}
CASES = ("positive", "gap_no_facility_schedule")


def _pages(case: str) -> dict[str, str]:
    """The financial pages of a case's pack, as listed by the oracle's pack_sources."""
    (financial,) = [
        s for s in EXPECTED["cases"][case]["pack_sources"] if s["source_id"] == "financial"
    ]
    return {locator: _FIN_PAGES[locator] for locator in financial["pages"]}


def _names(case: str) -> dict[str, str]:
    return {s["source_id"]: s["name"] for s in EXPECTED["cases"][case]["pack_sources"]}


def _inputs(case: str) -> cp2e.MacroFxInputs:
    return cp2e.inputs_from_submission(SUBMISSIONS[case], source_names=_names(case))


def _text(amount: Decimal | None) -> str | None:
    return None if amount is None else format(amount, "f")


def _stored(value: cp2e.Value) -> dict[str, str]:
    if value.state == "known":
        text = _text(value.amount)
        assert text is not None
        return {"state": "known", "amount": text}
    assert value.reason is not None
    return {"state": value.state, "reason": value.reason}


_TOP = ("floating", "floating_share", "cov_base", "lev_base", "hedge", "floating_after_hedge")
_RATE = (
    "shock_bp",
    "gross",
    "net",
    "interest_after",
    "cov_after",
    "cov_change",
    "fcf_after",
    "share_of_ebitda",
)
_FX = ("shock", "debt_change", "debt_after", "ebitda_change", "ebitda_after", "lev_after")


def _stored_all(s: cp2e.Sensitivity) -> dict[str, Any]:
    out: dict[str, Any] = {name: _stored(getattr(s, name)) for name in _TOP}
    out["rate"] = [{name: _stored(getattr(r, name)) for name in _RATE} for r in s.rate]
    out["foreign_debt"] = _stored(s.foreign_debt)
    out["foreign_debt_share"] = _stored(s.foreign_debt_share)
    out["fx"] = [{name: _stored(getattr(r, name)) for name in _FX} for r in s.fx]
    return out


def _cell(c: cp2e.Cell) -> dict[str, Any]:
    return {
        "fact_id": c.fact_id,
        "column": c.column,
        "period": c.period,
        "amount": _text(c.amount),
        "unit": c.unit,
        "currency": c.currency,
        "scale": format(c.scale, "f"),
        "decimals": c.decimals,
        "text": c.text,
        "shown": c.shown,
        "status": c.status,
        "cites": [list(x) for x in c.cites],
        "value_class": c.value_class,
        "calculation_id": c.calculation_id,
        "formula": c.formula,
        "limitation": c.limitation,
    }


def _head(t: cp2e.Table) -> dict[str, Any]:
    return {
        "table_id": t.table_id,
        "title": t.title,
        "row_header": t.row_header,
        "columns": [{"field": f, "label": label} for f, label in t.columns],
    }


def _table(t: cp2e.Table) -> dict[str, Any]:
    rows = [
        {"row_id": r.row_id, "label": r.label, "facts": [_cell(c) for c in r.cells]} for r in t.rows
    ]
    return {**_head(t), "rows": rows}


def _cells(result: cp2e.MacroFxResult) -> list[cp2e.Cell]:
    return [c for t in result.tables for r in t.rows for c in r.cells]


@pytest.fixture(scope="module")
def results() -> dict[str, cp2e.MacroFxResult]:
    return {case: cp2e.compute(_inputs(case)) for case in CASES}


@pytest.mark.parametrize("case", CASES)
def test_literal_is_valid_on_its_pack(case: str) -> None:
    assert cp2e.validate_macro_fx(submission=SUBMISSIONS[case], pages=_pages(case)) == ()


@pytest.mark.parametrize("case", CASES)
def test_derived_values(case: str, results: dict[str, cp2e.MacroFxResult]) -> None:
    assert _stored_all(results[case].sensitivity) == EXPECTED["cases"][case]["derived"]


@pytest.mark.parametrize("case", CASES)
def test_tables_cell_for_cell(case: str, results: dict[str, cp2e.MacroFxResult]) -> None:
    got = [_table(t) for t in results[case].tables]
    want = EXPECTED["cases"][case]["tables"]
    assert [t["table_id"] for t in got] == [t["table_id"] for t in want]
    for g, w in zip(got, want, strict=True):
        assert g == w, g["table_id"]


@pytest.mark.parametrize("case", CASES)
def test_module_tables_layout(case: str, results: dict[str, cp2e.MacroFxResult]) -> None:
    got = [
        {
            **_head(t),
            "rows": [
                {"row_id": r.row_id, "label": r.label, "fact_ids": [c.fact_id for c in r.cells]}
                for r in t.rows
            ],
        }
        for t in results[case].tables
    ]
    assert got == EXPECTED["cases"][case]["module_tables"]


@pytest.mark.parametrize("case", CASES)
def test_missing_and_not_applicable(case: str, results: dict[str, cp2e.MacroFxResult]) -> None:
    cells = _cells(results[case])
    want = EXPECTED["cases"][case]
    assert [c.fact_id for c in cells if c.status == "missing"] == want["missing_not_zero"]
    assert [c.fact_id for c in cells if c.status == "not_applicable"] == want["not_applicable"]


@pytest.mark.parametrize("case", CASES)
def test_claims(case: str, results: dict[str, cp2e.MacroFxResult]) -> None:
    got = [
        {
            "claim_id": c.claim_id,
            "text": c.text,
            "refs": list(c.refs),
            "cites": [list(x) for x in c.cites],
        }
        for c in results[case].claims
    ]
    assert got == EXPECTED["cases"][case]["claims"]


@pytest.mark.parametrize("case", CASES)
def test_claims_pass_the_product_prose_check(
    case: str, results: dict[str, cp2e.MacroFxResult]
) -> None:
    facts: list[Fact] = [c.fact() for c in _cells(results[case])]
    bound = prose.bind(facts)
    gaps = {f.fact_id for f in facts if f.status != "known"}
    literal = {
        x["claim_id"]: x["literal_text_outside_references"]
        for x in EXPECTED["cases"][case]["claim_literal_text"]
    }
    for claim in results[case].claims:
        assert prose.issues(claim.text, bound) == (), claim.claim_id
        runs = prose.tokenize(claim.text, gaps=gaps)
        assert "".join(r.text for r in runs if r.kind == "text") == literal[claim.claim_id]


@pytest.mark.parametrize("case", CASES)
def test_own_limitations(case: str, results: dict[str, cp2e.MacroFxResult]) -> None:
    assert list(results[case].limitations) == EXPECTED["cases"][case]["own_limitations"]


def _operands(raw: dict[str, Any]) -> cp2e.Operands:
    def dec(key: str) -> Decimal | None:
        value = raw.get(key)
        return None if value is None else Decimal(value)

    return cp2e.Operands(
        total_debt=dec("total_debt"),
        ebitda=dec("ebitda"),
        interest=dec("interest"),
        fcf=dec("fcf"),
        facility_balance=dec("facility_balance"),
        rate_type=raw.get("rate_type"),
        floor_bp=dec("floor_bp"),
        debt_foreign=raw.get("debt_foreign"),
        foreign_ebitda_share=dec("foreign_ebitda_share"),
    )


def _fixture_result(name: str) -> cp2e.Sensitivity:
    raw = EXPECTED["fixtures"][name]["inputs"]
    return cp2e.derive_sensitivity(
        operands=_operands(raw),
        rate_shocks_bp=tuple(Decimal(x) for x in raw["rate_shocks"]),
        fx_shocks=tuple(Decimal(x) for x in raw["fx_shocks"]),
        hedge_ratio=None if raw["hedge"] is None else Decimal(raw["hedge"]),
    )


@pytest.mark.parametrize("name", sorted(EXPECTED["fixtures"]))
def test_composer_fixture(name: str) -> None:
    """All eight fixtures; fixture_no_rate_terms is the live E4a test (oracle amendment E6)."""
    assert _stored_all(_fixture_result(name)) == EXPECTED["fixtures"][name]["stored"]


def test_partial_facility_adds_its_own_limitation() -> None:
    fixture = EXPECTED["fixtures"]["fixture_partial_facility"]
    added = fixture["own_limitation_added"]
    base = _inputs("positive")
    assert base.facility is not None
    balance = copy.replace(
        base.facility.balance, value=Decimal(fixture["inputs"]["facility_balance"])
    )
    partial = copy.replace(base, facility=copy.replace(base.facility, balance=balance))
    result = cp2e.compute(partial)
    assert added in result.limitations
    assert added not in cp2e.compute(base).limitations
    assert _stored(result.sensitivity.floating) == fixture["stored"]["floating"]
    assert _stored(result.sensitivity.floating_share) == fixture["stored"]["floating_share"]


def test_cp1_cross_check(results: dict[str, cp2e.MacroFxResult]) -> None:
    check = EXPECTED["cp1_cross_check"]
    inputs = _inputs("positive")
    sourced = {
        "ebitda": inputs.ebitda,
        "cash_interest_paid": inputs.interest,
        "fcf": inputs.fcf,
        "total_debt": inputs.total_debt,
    }
    for key, entry in check["operands"].items():
        assert sourced[key].value == Decimal(entry["cp2e"]), key
    cells = {c.fact_id: c for c in _cells(results["positive"])}
    for fact_id, entry in check["ratios"].items():
        assert cells[fact_id].shown == entry["cp2e"], fact_id


def _edit(base: dict[str, Any], path: str, value: Any) -> None:
    keys: list[str | int] = [int(k) if k.isdigit() else k for k in path.split(".")]
    cur: Any = base
    for key in keys[:-1]:
        cur = cur[key]
    cur[keys[-1]] = value


def _mutated(edits: list[list[Any]]) -> dict[str, Any]:
    sub: dict[str, Any] = copy.deepcopy(SUBMISSIONS[SUBMISSIONS["refusal_mutations"]["base"]])
    for path, value in edits:
        _edit(sub, path, value)
    return sub


_REFUSALS = {r["id"]: r["issue"] for r in EXPECTED["refusals"]}


@pytest.mark.parametrize(
    "entry", SUBMISSIONS["refusal_mutations"]["entries"], ids=lambda e: str(e["id"])
)
def test_refusal(entry: dict[str, Any]) -> None:
    issues = cp2e.validate_macro_fx(submission=_mutated(entry["edits"]), pages=_pages("positive"))
    assert issues[0] == _REFUSALS[entry["id"]]
    assert list(issues) == entry["all_issues"]


def test_refusals_cover_the_oracle() -> None:
    assert len(EXPECTED["refusals"]) == 27
    assert [e["id"] for e in SUBMISSIONS["refusal_mutations"]["entries"]] == list(_REFUSALS)


@pytest.mark.parametrize("attempt", ["attempt_0", "attempt_1"])
def test_blocked_attempt_issue(attempt: str) -> None:
    issues = cp2e.validate_macro_fx(
        submission=_mutated(SUBMISSIONS["blocked"][attempt]["edits"]), pages=_pages("positive")
    )
    assert issues[0] == EXPECTED["negative_cases"]["blocked_cp2e"][f"{attempt}_issue"]


def test_blocked_result_names_the_blocked_head() -> None:
    """Stage 2 ruling 8: the store holds a blocked head with status `blocked` (as CP-1A in S1a),
    so the oracle never says the blocked module has no head."""
    result = EXPECTED["negative_cases"]["blocked_cp2e"]["result"]
    assert "no head" not in result
    assert "blocked head" in result and "status blocked" in result


# --- rulings round (docs/rulings/2026-10-28-stage1.md, CP-2E E1-E5) -------------------------
def _claim(result: cp2e.MacroFxResult, claim_id: str) -> cp2e.ClaimText:
    (claim,) = [c for c in result.claims if c.claim_id == claim_id]
    return claim


def _assert_prose_clean(result: cp2e.MacroFxResult) -> None:
    facts = [c.fact() for c in _cells(result)]
    bound = prose.bind(facts)
    for claim in result.claims:
        assert prose.issues(claim.text, bound) == (), (claim.claim_id, claim.text)


_SHARE = cp2e.Sourced(value=Decimal("0.2"), cite=cp2e.Cite("financial", "page:2"))
_NO_TERMS = cp2e.Absence(reason="Not stated", follow_up="Supply it")


def _with_share(inputs: cp2e.MacroFxInputs) -> cp2e.MacroFxInputs:
    return copy.replace(inputs, foreign_ebitda_share=_SHARE, operating_fx_absence=None)


def _floor(inputs: cp2e.MacroFxInputs, bp: str) -> cp2e.MacroFxInputs:
    assert inputs.facility is not None
    floor = copy.replace(inputs.facility.floor_bp, value=Decimal(bp))
    return copy.replace(inputs, facility=copy.replace(inputs.facility, floor_bp=floor))


def _value(inputs: cp2e.MacroFxInputs, name: str, amount: str) -> cp2e.MacroFxInputs:
    sourced: cp2e.Sourced = getattr(inputs, name)
    changed: dict[str, Any] = {name: copy.replace(sourced, value=Decimal(amount))}
    return copy.replace(inputs, **changed)


def test_e1_fx_claim_foreign_debt_known_share_known() -> None:
    result = cp2e.compute(_with_share(_inputs("positive")))
    claim = _claim(result, "CP-2E-FX-01")
    assert claim.text == (
        "The debt in a foreign currency is {T2F.2.r05.value|US$ m}, so the first currency move "
        "leaves total debt at {T2F.4.r01.debt_after|US$ m}, changes EBITDA by "
        "{T2F.4.r01.ebitda_change|US$ m} and leaves total leverage at {T2F.4.r01.lev_after|x}."
    )
    assert claim.refs == (
        "T2F.2.r05.value",
        "T2F.4.r01.debt_after",
        "T2F.4.r01.ebitda_change",
        "T2F.4.r01.lev_after",
    )
    _assert_prose_clean(result)


def test_e1_fx_claim_leverage_not_meaningful_is_a_chip() -> None:
    result = cp2e.compute(_value(_with_share(_inputs("positive")), "ebitda", "0"))
    assert result.sensitivity.fx[0].lev_after.state == "not_applicable"
    assert _claim(result, "CP-2E-FX-01").text == (
        "The debt in a foreign currency is {T2F.2.r05.value|US$ m}, so the first currency move "
        "leaves total debt at {T2F.4.r01.debt_after|US$ m}, changes EBITDA by "
        "{T2F.4.r01.ebitda_change|US$ m} and leaves total leverage at [T2F.4.r01.lev_after]."
    )
    _assert_prose_clean(result)


@pytest.mark.parametrize(
    ("case", "needs"),
    [
        ("positive", "the facility balance"),
        ("gap_no_facility_schedule", "the currency of the debt"),
    ],
)
def test_e1_fx_claim_foreign_debt_missing_share_known(case: str, needs: str) -> None:
    inputs = _with_share(_inputs(case))
    if case == "positive":  # currency stated, no facility balance (E4a)
        inputs = copy.replace(inputs, facility=None, rate_absence=_NO_TERMS)
    result = cp2e.compute(inputs)
    claim = _claim(result, "CP-2E-FX-01")
    assert claim.text == (
        "The first currency move changes EBITDA by {T2F.4.r01.ebitda_change|US$ m}; the currency "
        f"effect on the debt is not calculated: [T2F.2.r05.value] needs {needs}, which the pack "
        "does not state."
    )
    assert claim.refs == ("T2F.4.r01.ebitda_change", "T2F.2.r05.value")
    _assert_prose_clean(result)


def test_e4a_currency_stated_without_facility_balance() -> None:
    inputs = copy.replace(_inputs("positive"), facility=None, rate_absence=_NO_TERMS)
    result = cp2e.compute(inputs)
    assert _claim(result, "CP-2E-FX-01").text == (
        "The currency effect on the debt is not calculated: [T2F.2.r05.value] needs the facility "
        "balance, which the pack does not state."
    )
    cells = {c.fact_id: c for c in _cells(result)}
    assert (
        cells["T2F.2.r05.value"].limitation == "Not calculable: the facility balance is not stated"
    )
    _assert_prose_clean(result)


def _rate_gap(nth: str, n: int, needs: str) -> str:
    return f"The effect of the {nth} rate shock is not calculated: [T2F.3.r{n:02d}.gross] {needs}."


_FLOOR_ABOVE = (
    "needs the reference rate level, which no source states, because the floor of the facility "
    "is above zero"
)


def test_e2_rate_claim_floor_above_zero() -> None:
    result = cp2e.compute(_floor(_inputs("positive"), "25"))
    assert _claim(result, "CP-2E-RATE-01").text == _rate_gap("first", 1, _FLOOR_ABOVE)
    assert _claim(result, "CP-2E-RATE-02").text == _rate_gap("second", 2, _FLOOR_ABOVE)
    _assert_prose_clean(result)


def test_e2_rate_claim_floor_not_stated_through_the_pure_composer() -> None:
    operands = cp2e.operands_of(_inputs("positive"))
    s = cp2e.derive_sensitivity(
        operands=copy.replace(operands, floor_bp=None),
        rate_shocks_bp=(Decimal(100),),
        fx_shocks=(Decimal("0.1"),),
        hedge_ratio=None,
    )
    assert cp2e.rate_gap_claim(1, s.rate[0].gross) == _rate_gap(
        "first", 1, "needs the floor of the facility, which the pack does not state"
    )


def test_e2_rate_claim_without_rate_terms_keeps_the_pinned_text() -> None:
    result = cp2e.compute(copy.replace(_inputs("positive"), facility=None, rate_absence=_NO_TERMS))
    assert _claim(result, "CP-2E-RATE-01").text == _rate_gap(
        "first", 1, "needs the facility rate terms, which the pack does not state"
    )


def _e3(nth: str, n: int, cov_after: str) -> str:
    return (
        f"For the {nth} rate shock tested, the floating-rate debt of {{T2F.2.r01.value|US$ m}} adds "
        f"{{T2F.3.r{n:02d}.gross|US$ m}} of annual cash interest before any hedge; interest "
        f"coverage after the shock is {cov_after}, and no change is stated because coverage at "
        "base is not meaningful: [T2F.2.r03.value]."
    )


def test_e3_coverage_at_base_not_meaningful() -> None:
    result = cp2e.compute(_value(_inputs("positive"), "interest", "0"))
    assert result.sensitivity.cov_base.state == "not_applicable"
    for n, nth in ((1, "first"), (2, "second")):
        claim = _claim(result, f"CP-2E-RATE-{n:02d}")
        assert claim.text == _e3(nth, n, f"{{T2F.3.r{n:02d}.cov_after|x}}")
        assert claim.refs == (
            "T2F.2.r01.value",
            f"T2F.3.r{n:02d}.gross",
            f"T2F.3.r{n:02d}.cov_after",
            "T2F.2.r03.value",
        )
    _assert_prose_clean(result)


def test_e3_coverage_after_not_known_is_a_chip() -> None:
    inputs = _value(_inputs("positive"), "interest", "0")
    assert inputs.facility is not None
    fixed = copy.replace(inputs.facility.basis, rate_type="FIXED")
    result = cp2e.compute(copy.replace(inputs, facility=copy.replace(inputs.facility, basis=fixed)))
    assert result.sensitivity.rate[0].cov_after.state == "not_applicable"
    assert _claim(result, "CP-2E-RATE-01").text == _e3("first", 1, "[T2F.3.r01.cov_after]")
    _assert_prose_clean(result)


_HEDGE_GAP = "The effect of the first rate shock after hedges is not calculated: [T2F.3.r01.net] "


def test_e4b_hedge_stated_rate_terms_missing() -> None:
    gap = _inputs("gap_no_facility_schedule")
    result = cp2e.compute(copy.replace(gap, hedge_ratio=Decimal("0.4"), hedge_absence=None))
    assert _claim(result, "CP-2E-HEDGE-01").text == (
        _HEDGE_GAP + "needs the facility rate terms, which the pack does not state."
    )
    _assert_prose_clean(result)


def test_e4b_hedge_stated_floor_above_zero() -> None:
    hedged = copy.replace(_inputs("positive"), hedge_ratio=Decimal("0.4"), hedge_absence=None)
    result = cp2e.compute(_floor(hedged, "25"))
    assert _claim(result, "CP-2E-HEDGE-01").text == _HEDGE_GAP + _FLOOR_ABOVE + "."
    _assert_prose_clean(result)


@pytest.mark.parametrize(
    "sentence",
    [
        "The facility coupon is floating against the SOFR reference rate",  # no "floating rate"
        "It has a floating rate on SOFR reference rate and no fixed rate",  # both phrases
    ],
)
def test_e5_rate_basis_needs_exactly_one_rate_phrase(sentence: str) -> None:
    pages = dict(_pages("positive"))
    pages["page:5"] += "\n" + sentence  # a variant page; the frozen sentences stay
    sub = copy.deepcopy(SUBMISSIONS["positive"])
    sub["rate_exposure"]["rate_basis"]["quote"] = sentence
    issues = cp2e.validate_macro_fx(submission=sub, pages=pages)
    assert issues == (
        "rate_exposure.rate_basis: the quote states neither a floating nor a fixed rate",
    )


def test_e5_rate_phrase_is_case_insensitive() -> None:
    sentence = "The facility has Floating Rate type with SOFR reference rate"
    pages = dict(_pages("positive"))
    pages["page:5"] += "\n" + sentence
    sub = copy.deepcopy(SUBMISSIONS["positive"])
    sub["rate_exposure"]["rate_basis"]["quote"] = sentence
    assert cp2e.validate_macro_fx(submission=sub, pages=pages) == ()


def _grid() -> list[tuple[str, cp2e.MacroFxInputs]]:
    """Valid-input combinations the composer must settle: rate terms, rate type, floor, interest,
    EBITDA, debt currency, foreign share and hedge ratio."""
    out: list[tuple[str, cp2e.MacroFxInputs]] = []
    base = _inputs("positive")
    assert base.facility is not None
    eur = cp2e.SourcedCode(code="EUR", cite=base.facility.balance.cite)
    for terms in ("floating", "fixed", "absent"):
        for floor in ("0", "25"):
            for interest in ("5.00", "0", "-0.5"):
                for ebitda in ("30.0", "0", "-30.0"):
                    for ccy in ("USD", "EUR", "absent"):
                        for share in (False, True):
                            for hedge in (False, True):
                                i = _value(_value(base, "interest", interest), "ebitda", ebitda)
                                if terms == "absent":
                                    i = copy.replace(i, facility=None, rate_absence=_NO_TERMS)
                                else:
                                    i = _floor(i, floor)
                                    if terms == "fixed":
                                        assert i.facility is not None
                                        basis = copy.replace(i.facility.basis, rate_type="FIXED")
                                        i = copy.replace(
                                            i, facility=copy.replace(i.facility, basis=basis)
                                        )
                                if ccy == "EUR":
                                    i = copy.replace(i, debt_currency=eur)
                                elif ccy == "absent":
                                    i = copy.replace(
                                        i, debt_currency=None, debt_currency_absence=_NO_TERMS
                                    )
                                if share:
                                    i = _with_share(i)
                                if hedge:
                                    i = copy.replace(
                                        i, hedge_ratio=Decimal("0.4"), hedge_absence=None
                                    )
                                label = f"{terms}/{floor}/{interest}/{ebitda}/{ccy}/{share}/{hedge}"
                                out.append((label, i))
    return out


def test_valid_inputs_settle_with_clean_claims() -> None:
    """Every grid combination composes with prose-clean claims: A3 retired the coverage raise and
    round 6i the fixed-rate floor raise."""
    for label, inputs in _grid():
        result = cp2e.compute(inputs)
        assert result.claims, label
        _assert_prose_clean(result)


@pytest.mark.parametrize("token", ["(5", "5)"])
def test_unbalanced_parentheses_are_not_a_row_value(token: str) -> None:
    """A row whose last token has one parenthesis is an issue, never a number or a crash."""
    line = f"FX effect on cash  0  0  0  0  {token}"
    pages = dict(_pages("positive"))
    pages["page:3"] = pages["page:3"].replace("FX effect on cash  0  0  0  0  0", line)
    assert line in pages["page:3"]
    sub = copy.deepcopy(SUBMISSIONS["positive"])
    sub["fx"]["fx_cash_effect"].update(quote=line, value_text=token)
    issues = cp2e.validate_macro_fx(submission=sub, pages=pages)
    assert issues == (f"fx.fx_cash_effect: value_text {token} is not the last value of the row",)


def test_source_names_are_required() -> None:
    """No empty default: T2F.8 cannot be composed without the pack's source names."""
    (names,) = [f for f in dataclasses.fields(cp2e.MacroFxInputs) if f.name == "source_names"]
    assert names.default is dataclasses.MISSING
    assert names.default_factory is dataclasses.MISSING


# --- round 5 (E7, E8) and round 6 (A3, A4) ---------------------------------------------------
def _negative_gross_inputs(interest: str) -> cp2e.MacroFxInputs:
    """Directly built inputs (the pure composer path; a validated facility balance is never
    negative): a negative balance gives a negative added interest, so interest after the shock
    can be zero or negative while coverage at base is known."""
    base = _value(_inputs("positive"), "interest", interest)
    assert base.facility is not None
    balance = copy.replace(base.facility.balance, value=Decimal(-50))
    return copy.replace(base, facility=copy.replace(base.facility, balance=balance))


def _e7(nth: str, n: int, word: str) -> str:
    return (
        f"For the {nth} rate shock tested, the floating-rate debt of {{T2F.2.r01.value|US$ m}} adds "
        f"{{T2F.3.r{n:02d}.gross|US$ m}} of annual cash interest before any hedge; interest "
        f"coverage after the shock is not meaningful because cash interest after the shock is "
        f"{word}: [T2F.3.r{n:02d}.cov_after]."
    )


def test_e7_coverage_after_not_meaningful_with_base_known() -> None:
    result = cp2e.compute(_negative_gross_inputs("0.5"))  # 100 bp: after 0; 200 bp: after -0.5
    assert result.sensitivity.cov_base.state == "known"
    cells = {c.fact_id: c for c in _cells(result)}
    for n, nth, word in ((1, "first", "zero"), (2, "second", "negative")):
        reason = f"Not meaningful: interest after the shock is {word}"
        for field in ("cov_after", "cov_change"):
            cell = cells[f"T2F.3.r{n:02d}.{field}"]
            assert (cell.status, cell.limitation) == ("not_applicable", reason), cell.fact_id
        claim = _claim(result, f"CP-2E-RATE-{n:02d}")
        assert claim.text == _e7(nth, n, word)
        assert claim.refs == (
            "T2F.2.r01.value",
            f"T2F.3.r{n:02d}.gross",
            f"T2F.3.r{n:02d}.cov_after",
        )
    _assert_prose_clean(result)


def _derive(**changes: Any) -> cp2e.Sensitivity:
    operands = copy.replace(cp2e.operands_of(_inputs("positive")), **changes)
    return cp2e.derive_sensitivity(
        operands=operands,
        rate_shocks_bp=(Decimal(100),),
        fx_shocks=(Decimal("0.1"),),
        hedge_ratio=None,
    )


def _na(reason: str) -> dict[str, str]:
    return {"state": "not_applicable", "reason": reason}


def test_a3_negative_divisors_are_not_meaningful() -> None:
    interest = _derive(interest=Decimal(-2))
    assert _stored(interest.cov_base) == _na("cash interest is negative")
    assert _stored(interest.rate[0].cov_after) == _na("interest after the shock is negative")
    ebitda = _derive(ebitda=Decimal(-30))
    assert _stored(ebitda.lev_base) == _na("EBITDA is negative")
    assert _stored(ebitda.rate[0].share_of_ebitda) == _na("EBITDA is negative")
    assert ebitda.cov_base.state == "known"  # a negative numerator is a value
    debt = _derive(total_debt=Decimal(-50))
    assert _stored(debt.floating_share) == _na("total debt is negative")
    assert _stored(debt.foreign_debt_share) == _na("total debt is negative")
    share = copy.replace(cp2e.operands_of(_inputs("positive")), foreign_ebitda_share=Decimal(-20))
    after = cp2e.derive_sensitivity(
        operands=share,
        rate_shocks_bp=(Decimal(100),),
        fx_shocks=(Decimal("0.1"),),
        hedge_ratio=None,
    )
    assert _stored(after.fx[0].lev_after) == _na("EBITDA after the shock is negative")
    zero = _derive(interest=Decimal(0))  # the zero reasons stay byte for byte
    assert _stored(zero.cov_base) == _na("cash interest is zero")


def test_a3_negative_base_coverage_falls_under_e3() -> None:
    result = cp2e.compute(_value(_inputs("positive"), "interest", "-0.5"))
    assert result.sensitivity.cov_base.state == "not_applicable"
    assert _claim(result, "CP-2E-RATE-01").text == _e3("first", 1, "[T2F.3.r01.cov_after]")
    assert _claim(result, "CP-2E-RATE-02").text == _e3("second", 2, "{T2F.3.r02.cov_after|x}")
    _assert_prose_clean(result)


@pytest.mark.parametrize(
    ("phrase", "rate_type"),
    [("floating-rate", "FLOATING"), ("Fixed-Rate", "FIXED"), ("floating -  rate", "FLOATING")],
)
def test_e8_hyphenated_rate_phrases_count(phrase: str, rate_type: str) -> None:
    sentence = f"The facility has a {phrase} coupon on the SOFR reference rate"
    pages = dict(_pages("positive"))
    pages["page:5"] += "\n" + sentence
    sub = copy.deepcopy(SUBMISSIONS["positive"])
    sub["rate_exposure"]["rate_basis"].update(quote=sentence, rate_type=rate_type)
    assert cp2e.validate_macro_fx(submission=sub, pages=pages) == ()


def test_e8_both_stems_hyphenated_is_neither() -> None:
    sentence = (
        "The facility has a floating-rate coupon on the SOFR reference rate, not a fixed-rate"
    )
    pages = dict(_pages("positive"))
    pages["page:5"] += "\n" + sentence
    sub = copy.deepcopy(SUBMISSIONS["positive"])
    sub["rate_exposure"]["rate_basis"]["quote"] = sentence
    assert cp2e.validate_macro_fx(submission=sub, pages=pages) == (
        "rate_exposure.rate_basis: the quote states neither a floating nor a fixed rate",
    )


_A4_ABOVE = (
    "The reference rate level is not in any source and the facility floor is above zero, so the "
    "rate shocks are not calculated and downward shocks are not tested"
)


def test_a4_floor_above_zero_limitation() -> None:
    result = cp2e.compute(_floor(_inputs("positive"), "25"))
    assert _A4_ABOVE in result.limitations
    assert not any(
        t.startswith("The reference rate level is not in any source, so")
        for t in result.limitations
    )
    assert result.limitations == tuple(r.cells[0].text for r in result.tables[8].rows)


def _fixed(inputs: cp2e.MacroFxInputs) -> cp2e.MacroFxInputs:
    assert inputs.facility is not None
    basis = copy.replace(inputs.facility.basis, rate_type="FIXED")
    return copy.replace(inputs, facility=copy.replace(inputs.facility, basis=basis))


@pytest.mark.parametrize("floor", ["0", "25"])
def test_round6i_no_floor_limitation_on_fixed_rate_debt(floor: str) -> None:
    """Round 6i: a floor does not bind a fixed coupon, so neither floor line is emitted; every
    other limitation stays as built (the positive case's own limitations without its floor line)."""
    result = cp2e.compute(_fixed(_floor(_inputs("positive"), floor)))
    positive = EXPECTED["cases"]["positive"]["own_limitations"]
    floor_line = positive[2]
    assert floor_line.startswith("The reference rate level is not in any source, so a floor")
    assert _A4_ABOVE not in result.limitations
    assert list(result.limitations) == [t for t in positive if t != floor_line]
    _assert_prose_clean(result)


@pytest.mark.parametrize("phrase", ["fixed rates", "prefixed rate"])
def test_e8_word_boundaries_are_pinned(phrase: str) -> None:
    """The ruled \\b anchors: "fixed rates" and "prefixed rate" carry no rate phrase."""
    sentence = f"The facility has a {phrase} coupon on the SOFR reference rate"
    pages = dict(_pages("positive"))
    pages["page:5"] += "\n" + sentence
    sub = copy.deepcopy(SUBMISSIONS["positive"])
    sub["rate_exposure"]["rate_basis"].update(quote=sentence, rate_type="FIXED")
    assert cp2e.validate_macro_fx(submission=sub, pages=pages) == (
        "rate_exposure.rate_basis: the quote states neither a floating nor a fixed rate",
    )


# --- round 10: figure signs in quote readers, the product quote match, the riding Low --------
def _share_submission(sentence: str, percent_text: str) -> tuple[dict[str, Any], dict[str, str]]:
    """The positive literal with a stated foreign EBITDA share quoted from a variant page:2."""
    pages = dict(_pages("positive"))
    pages["page:2"] += "\n" + sentence
    sub = copy.deepcopy(SUBMISSIONS["positive"])
    sub["fx"]["operating_fx_absence"] = None
    sub["fx"]["foreign_ebitda_share"] = {
        "source_id": "financial",
        "locator": "page:2",
        "quote": sentence,
        "percent_text": percent_text,
    }
    return sub, pages


@pytest.mark.parametrize(
    "printed",
    ["\u221225", "-25", "\u201325", "(25)"],
    ids=["minus_sign", "ascii_hyphen", "en_dash", "parentheses"],
)
def test_round10_signed_share_does_not_occur(printed: str) -> None:
    sub, pages = _share_submission(f"Earnings abroad were {printed} percent of EBITDA.", "25")
    assert cp2e.validate_macro_fx(submission=sub, pages=pages) == (
        "fx.foreign_ebitda_share: percent_text 25 does not occur in the quote",
    )


@pytest.mark.parametrize(
    ("sentence", "percent_text"),
    [
        ("Earnings abroad were 25 percent of EBITDA from 1-December.", "1"),
        ("Earnings abroad were 95-96 percent of EBITDA.", "96"),
        ("Earnings abroad of S-25 were reported.", "25"),
        ("Earnings abroad of mid-25 were reported.", "25"),
        ("Earnings abroad were 20 percent over 2024-2025.", "20"),
        ("Earnings abroad were +25 percent of EBITDA.", "25"),
        ("Earnings abroad were (25 percent) of EBITDA.", "25"),
    ],
    ids=[
        "1-December",
        "95-96",
        "S-25",
        "mid-25",
        "2024-2025",
        "plus_ignored",
        "parenthesised_words",
    ],
)
def test_round10_non_sign_forms_still_validate(sentence: str, percent_text: str) -> None:
    sub, pages = _share_submission(sentence, percent_text)
    assert cp2e.validate_macro_fx(submission=sub, pages=pages) == ()


def test_round10_signed_labelled_operand_does_not_occur() -> None:
    """A labelled operand printed with a minus gets the "does not occur" issue (one check before
    the label adjacency)."""
    sentence = "The margin is spread \u22125 basis points over the reference rate."
    pages = dict(_pages("positive"))
    pages["page:5"] += "\n" + sentence
    sub = copy.deepcopy(SUBMISSIONS["positive"])
    sub["rate_exposure"]["spread"] = {
        "source_id": "financial",
        "locator": "page:5",
        "quote": sentence,
        "bps_text": "5",
    }
    assert cp2e.validate_macro_fx(submission=sub, pages=pages) == (
        "rate_exposure.spread: bps_text 5 does not occur in the quote",
    )


@pytest.mark.parametrize(
    ("sentence", "accepted"),
    [
        ("The margin is spread - 25 basis points over the reference rate.", False),
        ("The margin is spread -\n25 basis points over the reference rate.", False),
        ("The margin is spread 25 basis points over the reference rate.", True),
        ("The margin is spread\n25 basis points over the reference rate.", True),
    ],
    ids=["minus-space", "minus-wrap", "minus-space-twin", "minus-wrap-twin"],
)
def test_round12_w_labelled_operand(sentence: str, accepted: bool) -> None:
    """Rule W in the labelled reader: a minus one space (or a line break) before the operand
    signs it, so it does not occur; its twin without the minus is a labelled operand."""
    pages = dict(_pages("positive"))
    pages["page:5"] += "\n" + sentence
    sub = copy.deepcopy(SUBMISSIONS["positive"])
    sub["rate_exposure"]["spread"] = {
        "source_id": "financial",
        "locator": "page:5",
        "quote": sentence,
        "bps_text": "25",
    }
    expected = (
        () if accepted else ("rate_exposure.spread: bps_text 25 does not occur in the quote",)
    )
    assert cp2e.validate_macro_fx(submission=sub, pages=pages) == expected


@pytest.mark.parametrize(
    "printed",
    ["( 25)", "(25 )", "( 25 )", "(\n25\n)", "(25\n)"],
    ids=["open-space", "close-space", "both-spaces", "both-breaks", "close-break"],
)
def test_round12_w_spaced_parentheses(printed: str) -> None:
    """Rule W: an accounting negative may hold one space inside each parenthesis; the twin is
    round 10's `parenthesised_words`, `(25 percent)`, which validates."""
    sub, pages = _share_submission(f"Earnings abroad were {printed} percent of EBITDA.", "25")
    assert cp2e.validate_macro_fx(submission=sub, pages=pages) == (
        "fx.foreign_ebitda_share: percent_text 25 does not occur in the quote",
    )


def test_round10_on_page_uses_the_product_quote_match() -> None:
    """An en dash in a quote of a page that prints a hyphen matches, as citation_issues does."""
    sub = copy.deepcopy(SUBMISSIONS["positive"])
    basis = {
        "source_id": "financial",
        "locator": "page:1",
        "quote": "January 1\u2013December 31, 2025",
    }
    sub["assessments"][0]["basis"].append(basis)
    assert cp2e.validate_macro_fx(submission=sub, pages=_pages("positive")) == ()


def test_negative_floor_fails_closed() -> None:
    """The riding Low: a negative floor (direct construction only) has no floor limitation."""
    with pytest.raises(ValueError, match="Floor limitation"):
        cp2e.compute(_floor(_inputs("positive"), "-25"))


# --- fix round 1 (round 10 review M1): reads after the normalised quote match ----------------
_SH = "\u00ad"  # soft hyphen: quotes.normalise deletes it, so quotes.quoted accepts the quote


def _validate_with_page5(sub: dict[str, Any], sentence: str) -> tuple[str, ...]:
    pages = dict(_pages("positive"))
    pages["page:5"] += "\n" + sentence
    return cp2e.validate_macro_fx(submission=sub, pages=pages)


def test_m1_code_is_read_on_the_normalised_quote() -> None:
    """A: the page prints only EURIBOR; a hidden break must not yield the code EUR."""
    sub = copy.deepcopy(SUBMISSIONS["positive"])
    quote = f"priced off EUR{_SH}IBOR"
    sub["fx"]["debt_currency"] = {
        "source_id": "financial",
        "locator": "page:5",
        "quote": quote,
        "code_text": "EUR",
    }
    assert _validate_with_page5(sub, "Debt is priced off EURIBOR.") == (
        "fx.debt_currency: code_text EUR does not occur in the quote",
    )


def test_m1_rate_phrase_is_read_on_the_normalised_quote() -> None:
    """B: the page states both phrases; a hidden break in one stem must not hide it."""
    sub = copy.deepcopy(SUBMISSIONS["positive"])
    page = "It has a floating rate on SOFR reference rate and no fixed rate"
    sub["rate_exposure"]["rate_basis"]["quote"] = page.replace("fixed", f"fi{_SH}xed")
    assert _validate_with_page5(sub, page) == (
        "rate_exposure.rate_basis: the quote states neither a floating nor a fixed rate",
    )


def test_m1_label_adjacency_is_read_on_the_normalised_quote() -> None:
    """C: the page's spread is 250; 25 is another figure on the page."""
    sub = copy.deepcopy(SUBMISSIONS["positive"])
    page = "The spread 250 basis points applies and 25 basis points is the fee"
    sub["rate_exposure"]["spread"] = {
        "source_id": "financial",
        "locator": "page:5",
        "quote": page.replace("250", f"25{_SH}0"),
        "bps_text": "25",
    }
    assert _validate_with_page5(sub, page) == (
        "rate_exposure.spread: bps_text 25 is not labelled spread in the quote",
    )


def test_m1_reference_rate_is_read_on_the_normalised_quote() -> None:
    """D: the page names SOFR; a hidden break in the quote must not refuse it."""
    sub = copy.deepcopy(SUBMISSIONS["positive"])
    page = "The loan has a floating rate type with SOFR reference rate"
    sub["rate_exposure"]["rate_basis"]["quote"] = page.replace("SOFR", f"SO{_SH}FR")
    assert _validate_with_page5(sub, page) == ()


# --- round 11: the shared defect classes (tests/defect_classes.py) through the validator -------
# Each case places (page, quote, value) in one analyst field of the positive literal; the case
# page is a fresh locator of the financial source (the validator needs only that it exists).
_LOC = "page:9"
_FLOATING = " The loan carries a floating rate."


def _issues_with(raw: dict[str, Any], page: str | None = None) -> tuple[str, ...]:
    pages = _pages("positive") if page is None else {**_pages("positive"), _LOC: page}
    return cp2e.validate_macro_fx(submission=raw, pages=pages)


def _cited(quote: str) -> dict[str, str]:
    return {"source_id": "financial", "locator": _LOC, "quote": quote}


def _share_adapter(page: str, quote: str, value: str) -> tuple[str, ...]:
    raw = copy.deepcopy(SUBMISSIONS["positive"])
    raw["fx"]["operating_fx_absence"] = None
    raw["fx"]["foreign_ebitda_share"] = {**_cited(quote), "percent_text": value}
    return _issues_with(raw, page)


def _spread_adapter(page: str, quote: str, value: str) -> tuple[str, ...]:
    raw = copy.deepcopy(SUBMISSIONS["positive"])
    raw["rate_exposure"]["spread"] = {**_cited(quote), "bps_text": value}
    return _issues_with(raw, page)


def _reference_rate_adapter(page: str, quote: str, value: str) -> tuple[str, ...]:
    """The reader needs one stated rate phrase: it follows the quote, in the quote and on the page
    (inserted right after where the page prints the quote, so the quote stays contiguous)."""
    raw = copy.deepcopy(SUBMISSIONS["positive"])
    raw["rate_exposure"]["rate_basis"] = {
        **_cited(quote + _FLOATING),
        "rate_type": "FLOATING",
        "reference_rate": value,
    }
    return _issues_with(raw, _after_quote(page, quote, _FLOATING))


def _after_quote(page: str, quote: str, text: str) -> str:
    """``page`` with ``text`` inserted right after the raw span the quote matches."""
    needles = (normalise(quote), reading(quote, join_wraps=True).text)
    for join_wraps in (False, True):
        span = reading(page, join_wraps=join_wraps)
        for needle in needles:
            at = span.text.find(needle)
            if at >= 0:
                end = span.origin[at + len(needle) - 1] + 1
                return page[:end] + text + page[end:]
    raise AssertionError(f"the case quote is not on its page: {quote!r}")


def _share_holds(value: str) -> bool:
    """The share's bound (at most 999.9999 and at most 100) folds into the same refusal, so a case
    whose value is outside it cannot be judged on its quote."""
    return bool(cp2e._SENTENCE_NUM.fullmatch(value)) and Decimal(value) <= 100


_SHARE_CASES = [c for c in dc.FIGURE_CASES if _share_holds(c.value)]
_SPREAD_FIGURE_CASES = [c for c in dc.FIGURE_CASES if cp2e._SENTENCE_NUM.fullmatch(c.value)]
_SPREAD_LABEL_CASES = [c for f in dc.FIGURES for c in dc.label_cases("spread", f)]


def _ids(c: dc.QuoteCase) -> str:
    return c.case_id


def _does_not_occur(path: str, key: str, value: str) -> str:
    return f"{path}: {key} {value} does not occur in the quote"


def test_class_cases_cover_the_bounds() -> None:
    """Only the three figures above the share's bound and the two off the operand shape (each
    2025, four digits) are left out, so every edge, sign, dash, NBSP and soft-hyphen family is
    judged."""
    left = {c.case_id for c in dc.FIGURE_CASES} - {c.case_id for c in _SHARE_CASES}
    assert left == {"sign-2024-2025", "sign-s-350", "w-2024-2025-wrap"}
    left = {c.case_id for c in dc.FIGURE_CASES} - {c.case_id for c in _SPREAD_FIGURE_CASES}
    assert left == {"sign-2024-2025", "w-2024-2025-wrap"}


@pytest.mark.parametrize("c", _SHARE_CASES, ids=_ids)
def test_class_foreign_share_figure(c: dc.QuoteCase) -> None:
    refusal = _does_not_occur("fx.foreign_ebitda_share", "percent_text", c.value)
    assert dc.quote_failure(c, _share_adapter, refusal) is None
    # Not vacuous: an accepted case is a valid submission, a refused one has only the refusal.
    assert _share_adapter(c.page, c.quote, c.value) == (() if c.accepted else (refusal,))


@pytest.mark.parametrize("c", _SPREAD_FIGURE_CASES, ids=_ids)
def test_class_labelled_operand_figure(c: dc.QuoteCase) -> None:
    """A labelled operand reads its figure with the same rule (round 11 B1 in every reader)."""
    refusal = _does_not_occur("rate_exposure.spread", "bps_text", c.value)
    assert dc.quote_failure(c, _spread_adapter, refusal) is None
    issues = _spread_adapter(c.page, c.quote, c.value)
    labelled = f"rate_exposure.spread: bps_text {c.value} is not labelled spread in the quote"
    # These pages carry no `spread` label: an accepted figure reaches the label check.
    assert issues == ((labelled,) if c.accepted else (refusal,))


@pytest.mark.parametrize("c", _SPREAD_LABEL_CASES, ids=lambda c: f"{c.case_id}-{c.value}")
def test_class_labelled_operand_label(c: dc.QuoteCase) -> None:
    """Round 10: a signed labelled figure with an unsigned repeat is refused at the label check;
    an accepted case gets neither refusal."""
    not_labelled = f"rate_exposure.spread: bps_text {c.value} is not labelled spread in the quote"
    occurs = _does_not_occur("rate_exposure.spread", "bps_text", c.value)
    if c.accepted:
        for refusal in (not_labelled, occurs):
            assert dc.quote_failure(c, _spread_adapter, refusal) is None
    else:
        assert dc.quote_failure(c, _spread_adapter, not_labelled) is None
    issues = _spread_adapter(c.page, c.quote, c.value)
    assert issues == (() if c.accepted else (not_labelled,))


@pytest.mark.parametrize("c", dc.TEXT_CASES, ids=_ids)
def test_class_reference_rate_text(c: dc.QuoteCase) -> None:
    refusal = "rate_exposure.rate_basis: reference_rate does not occur in the quote"
    assert dc.quote_failure(c, _reference_rate_adapter, refusal) is None
    assert _reference_rate_adapter(c.page, c.quote, c.value) == (() if c.accepted else (refusal,))


def _set_text(
    keys: tuple[str | int, ...], prep: Callable[[dict[str, Any]], None] | None = None
) -> dc.Adapter:
    def adapter(page: str, quote: str, value: str) -> tuple[str, ...]:
        raw = copy.deepcopy(SUBMISSIONS["positive"])
        if prep is not None:
            prep(raw)
        cur: Any = raw
        for key in keys[:-1]:
            cur = cur[key]
        cur[keys[-1]] = value
        return _issues_with(raw, _FIXED_PAGE)

    return adapter


_ABSENT = {"reason": "Not stated in the pack", "follow_up": "Supply the disclosure"}


def _rate_absent(raw: dict[str, Any]) -> None:
    raw["rate_exposure"] = None
    raw["rate_absence"] = dict(_ABSENT)


def _debt_currency_absent(raw: dict[str, Any]) -> None:
    raw["fx"]["debt_currency"] = None
    raw["fx"]["debt_currency_absence"] = dict(_ABSENT)


def _hedge_stated(raw: dict[str, Any]) -> None:
    raw["hedge_absence"] = None
    raw["hedge_ratio"] = {"percent_text": "40", "rationale": "The policy hedges part of the debt"}


_FIXED_PAGE = "The loan carries a fixed rate."


def _fixed_rate(raw: dict[str, Any]) -> None:
    """A fixed-rate basis: its reference rate is not read from the quote, but it is still text."""
    raw["rate_exposure"]["rate_basis"] = {
        **_cited(_FIXED_PAGE),
        "rate_type": "FIXED",
        "reference_rate": "SOFR",
    }


# Every analyst text field (path, where it sits, the state change that makes it present). Not
# here: quotes, source ids and locators (citations); value_text, bps_text, percent_text and
# code_text (figures and codes, read from quotes); rate_type, section and category (closed sets).
_TEXT_FIELDS: tuple[tuple[str, tuple[str | int, ...], Callable[[dict[str, Any]], None] | None], ...]
_TEXT_FIELDS = (
    ("shock_rationale", ("shock_rationale",), None),
    *(
        (f"assessments[{i}].text", ("assessments", i, "text"), None)
        for i in range(len(SUBMISSIONS["positive"]["assessments"]))
    ),
    ("assessments[2].limitation", ("assessments", 2, "limitation"), None),
    ("summary.text", ("summary", "text"), None),
    ("hedge_ratio.rationale", ("hedge_ratio", "rationale"), _hedge_stated),
    ("hedge_absence.reason", ("hedge_absence", "reason"), None),
    ("hedge_absence.follow_up", ("hedge_absence", "follow_up"), None),
    ("fx.operating_fx_absence.reason", ("fx", "operating_fx_absence", "reason"), None),
    ("fx.operating_fx_absence.follow_up", ("fx", "operating_fx_absence", "follow_up"), None),
    ("rate_absence.reason", ("rate_absence", "reason"), _rate_absent),
    ("rate_absence.follow_up", ("rate_absence", "follow_up"), _rate_absent),
    (
        "fx.debt_currency_absence.reason",
        ("fx", "debt_currency_absence", "reason"),
        _debt_currency_absent,
    ),
    (
        "fx.debt_currency_absence.follow_up",
        ("fx", "debt_currency_absence", "follow_up"),
        _debt_currency_absent,
    ),
    (
        "rate_exposure.rate_basis.reference_rate",
        ("rate_exposure", "rate_basis", "reference_rate"),
        None,
    ),
    (
        "rate_exposure.rate_basis.reference_rate",
        ("rate_exposure", "rate_basis", "reference_rate"),
        _fixed_rate,
    ),
)


@pytest.mark.parametrize(("path", "keys", "prep"), _TEXT_FIELDS, ids=[f[0] for f in _TEXT_FIELDS])
def test_class_text_field_set_up_is_valid(
    path: str, keys: tuple[str | int, ...], prep: Callable[[dict[str, Any]], None] | None
) -> None:
    """Each field's set-up, with its own literal text, is a valid submission."""
    raw = copy.deepcopy(SUBMISSIONS["positive"])
    if prep is not None:
        prep(raw)
    assert _issues_with(raw, _FIXED_PAGE) == ()


@pytest.mark.parametrize("c", dc.BLANK_CASES, ids=lambda c: c.case_id)
@pytest.mark.parametrize(("path", "keys", "prep"), _TEXT_FIELDS, ids=[f[0] for f in _TEXT_FIELDS])
def test_class_blank_text(
    path: str,
    keys: tuple[str | int, ...],
    prep: Callable[[dict[str, Any]], None] | None,
    c: dc.BlankCase,
) -> None:
    expected = dc.EMPTY_TEXT.format(path=path)
    assert dc.blank_failure(c, _set_text(keys, prep), expected) is None


_ONLY_II = "limitation is required for Insufficient Information and only for it"


@pytest.mark.parametrize("value", dc.BLANK_VALUES, ids=lambda v: repr(v))
def test_class_blank_limitation_off_insufficient_information(value: str) -> None:
    """Round 12 Info (the `bool()` asymmetry): a blank limitation is no limitation, so on an
    Analyst Interpretation assessment every blank value, `""` and whitespace alike, gets only the
    empty-text frame, not the "only for Insufficient Information" issue."""
    raw = copy.deepcopy(SUBMISSIONS["positive"])
    assert raw["assessments"][0]["category"] != "Insufficient Information"
    raw["assessments"][0]["limitation"] = value
    assert _issues_with(raw) == ("assessments[0].limitation: empty text",)


@pytest.mark.parametrize("value", dc.BLANK_VALUES, ids=lambda v: repr(v))
def test_class_blank_limitation_on_insufficient_information(value: str) -> None:
    """Round 12 Info (confirmed): a blank limitation on an Insufficient Information assessment
    gets the empty-text frame and then the "required" issue, for `""` and whitespace alike."""
    raw = copy.deepcopy(SUBMISSIONS["positive"])
    assert raw["assessments"][2]["category"] == "Insufficient Information"
    raw["assessments"][2]["limitation"] = value
    assert _issues_with(raw) == (
        "assessments[2].limitation: empty text",
        f"assessments[2]: {_ONLY_II}",
    )


@pytest.mark.parametrize("value", ["a limit", "a\u200b"], ids=["plain", "cf-bearing"])
def test_class_non_blank_limitation_off_insufficient_information(value: str) -> None:
    """Round 12 M1: the "only for it" half. A non-blank, digit-free limitation on an assessment
    that is not Insufficient Information gets exactly that issue. The Cf-bearing twin (a zero
    width space after a letter) is non-blank, so it pins `not is_blank`."""
    raw = copy.deepcopy(SUBMISSIONS["positive"])
    assert raw["assessments"][0]["category"] != "Insufficient Information"
    raw["assessments"][0]["limitation"] = value
    assert _issues_with(raw) == (f"assessments[0]: {_ONLY_II}",)


# --- round 11 B1 and B3 beyond the shared cases: every quote occurrence in every reading --------
@pytest.mark.parametrize(
    ("page", "quote", "accepted"),
    [
        # The joined page reading prints a minus before the figure (the plain one a spaced dash).
        ("Earnings abroad were -\n25 percent of EBITDA.", "25 percent of EBITDA.", False),
        # Only the wrapped quote's joined spelling is on the page, and there it is cut from 255.
        (
            "Earnings abroad of the first-priority unit were 255 percent.",
            "Earnings abroad of the first-\npriority unit were 25",
            False,
        ),
        ("Earnings abroad of the first-priority unit were 25 percent.", None, True),
        # Only the wrapped page's joined reading holds the joined quote, and there it is whole.
        (
            "Earnings abroad of the first-\npriority unit were 25 percent.",
            "Earnings abroad of the first-priority unit were 25",
            True,
        ),
        # The quote occurs twice; the second occurrence is cut from 255.
        ("Share 25 percent. Share 255 percent.", "Share 25", False),
        ("Share 25 percent. Share 25 percent.", "Share 25", True),
        # The second occurrence overlaps the first (it starts on the first's last digit).
        ("Units 5 of 25 of 255 percent.", "5 of 25", False),
        ("Units 5 of 25 of 25 percent.", "5 of 25", True),
    ],
    ids=[
        "joined-page-minus",
        "wrapped-quote-cut",
        "wrapped-quote-twin",
        "wrapped-page-joined-twin",
        "second-occurrence-cut",
        "second-occurrence-twin",
        "overlapping-occurrence-cut",
        "overlapping-occurrence-twin",
    ],
)
def test_b1_every_occurrence_in_every_reading(page: str, quote: str | None, accepted: bool) -> None:
    quote = "Earnings abroad of the first-\npriority unit were 25" if quote is None else quote
    refusal = _does_not_occur("fx.foreign_ebitda_share", "percent_text", "25")
    assert _share_adapter(page, quote, "25") == (() if accepted else (refusal,))


def test_b1_reads_the_labelled_operand_on_the_page() -> None:
    """A floor quoted as `floor 2` from a page that prints `floor 25` is refused."""
    sub = copy.deepcopy(SUBMISSIONS["positive"])
    sub["rate_exposure"]["floor"] = {**_cited("floor 2"), "bps_text": "2"}
    assert _issues_with(sub, "The loan has a floor 25 basis points.") == (
        "rate_exposure.floor: bps_text 2 does not occur in the quote",
    )


def test_b3_applies_only_to_a_wrapped_quote() -> None:
    """An unwrapped quote that prints `first- priority` itself holds the value: it occurs."""
    page = "The SOFR first- priority loan has terms."
    assert _reference_rate_adapter(page, "SOFR first- priority loan", "first- priority") == ()


def test_b3_refuses_only_the_wrap_spelling() -> None:
    """A wrapped quote still holds a hyphenated name that is not spelled with the wrap's `- `."""
    page = "The Term-SOFR loan is first-\npriority debt."
    assert _reference_rate_adapter(page, page, "Term-SOFR") == ()


# --- round 13: item 8 (a comma joins the digit run) and the B3 exemption for rule W's minus ----
_ITEM8_JOINS = ["1,25", "1, 25", "1,\n25"]


@pytest.mark.parametrize("join", _ITEM8_JOINS, ids=["comma", "comma-space", "comma-break"])
def test_round13_comma_join_before_the_figure_in_the_quote(join: str) -> None:
    """Item 8 (R3 M4): `<digit>,` and `<digit>, ` before the figure make it part of a longer
    number, in the quote, through the share and the labelled readers."""
    sentence = f"Earnings abroad were {join} percent of EBITDA."
    assert _share_adapter(sentence, sentence, "25") == (
        _does_not_occur("fx.foreign_ebitda_share", "percent_text", "25"),
    )
    spread = f"The margin is spread {join} basis points over the reference rate."
    assert _spread_adapter(spread, spread, "25") == (
        _does_not_occur("rate_exposure.spread", "bps_text", "25"),
    )


@pytest.mark.parametrize("join", _ITEM8_JOINS, ids=["comma", "comma-space", "comma-break"])
def test_round13_comma_join_before_the_figure_at_the_page_edge(join: str) -> None:
    """Item 8, B1: the quote starts at the figure and the page continues it from the left."""
    page = f"Earnings abroad were {join} percent of EBITDA."
    quote = "25 percent of EBITDA."
    assert _share_adapter(page, quote, "25") == (
        _does_not_occur("fx.foreign_ebitda_share", "percent_text", "25"),
    )
    page = f"The margin is spread {join} basis points over the reference rate."
    quote = "25 basis points over the reference rate."
    assert _spread_adapter(page, quote, "25") == (
        _does_not_occur("rate_exposure.spread", "bps_text", "25"),
    )


@pytest.mark.parametrize("join", ["25,1", "25, 1", "25,\n1"], ids=["comma", "comma-space", "break"])
def test_round13_comma_join_after_the_figure(join: str) -> None:
    """Item 8: the trailing guard also refuses `<figure>,<digit>` and `<figure>, <digit>`, in the
    quote and when the page continues a quote that ends at the figure."""
    sentence = f"Earnings abroad were {join} percent of EBITDA."
    assert _share_adapter(sentence, sentence, "25") == (
        _does_not_occur("fx.foreign_ebitda_share", "percent_text", "25"),
    )
    page = f"Earnings abroad were {join} percent of EBITDA."
    assert _share_adapter(page, "Earnings abroad were 25", "25") == (
        _does_not_occur("fx.foreign_ebitda_share", "percent_text", "25"),
    )


@pytest.mark.parametrize(
    "sentence",
    ["Earnings abroad were 25, a share of EBITDA.", "Earnings abroad, up, 25 percent of EBITDA."],
    ids=["25-comma-letter", "letter-comma-25"],
)
def test_round13_comma_twins_with_a_letter_stay_figures(sentence: str) -> None:
    assert _share_adapter(sentence, sentence, "25") == ()


@pytest.mark.parametrize(
    ("page", "quote", "value", "accepted"),
    [
        ("The level is -\n1.25 percent here.", "The level is -\n1.25 percent", "is - 1.25", True),
        ("Term Loan A-\n1.25 notes.", "Term Loan A-\n1.25 notes", "- 1.25 notes", False),
        ("In 2024-\n2025 notes.", "In 2024-\n2025 notes", "- 2025 notes", False),
        ("Term Loan A-\n1.25 notes.", "Term Loan A-\n1.25 notes", "A- 1.25", False),
        ("The rate a -\nb applies.", "The rate a -\nb applies", "a - b", False),
        ("The level is -\n1.25 percent here.", "The level is -\n1.25 percent", "- 1.25", False),
    ],
    ids=["w-minus", "index-0-letter", "index-0-digit", "after-letter", "no-digit", "index-0-minus"],
)
def test_round13_b3_exempts_only_rule_w_minus_inside_the_value(
    page: str, quote: str, value: str, accepted: bool
) -> None:
    """Addenda 1 and 3: a `- ` that W reads as a minus, with a character before it in the value
    itself, is no wrap split; index 0, after a letter or digit, or before a non-digit still is."""
    refusal = "rate_exposure.rate_basis: reference_rate does not occur in the quote"
    assert _reference_rate_adapter(page, quote, value) == (() if accepted else (refusal,))
