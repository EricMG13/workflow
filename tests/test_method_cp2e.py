"""CP-2E Stage 1: the pure calculation equals the frozen oracle (cases/cp2e-owner).

Inputs come from the oracle's own literals (submissions.json) and the frozen financial pages
(cases/financial/manifest.json); every expected value is read from expected.json.
"""

import copy
import dataclasses
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from deploy_vii import prose
from deploy_vii.contracts import Fact
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


_E4A_XFAIL = pytest.mark.xfail(
    strict=True,
    reason=(
        "oracle-disagreement E4a: fixture_no_rate_terms stores 'the currency of the debt is not "
        "stated'; ruling E4a gives 'the facility balance is not stated'; LEAD amendment pending"
    ),
)


def _fixture_result(name: str) -> cp2e.Sensitivity:
    raw = EXPECTED["fixtures"][name]["inputs"]
    return cp2e.derive_sensitivity(
        operands=_operands(raw),
        rate_shocks_bp=tuple(Decimal(x) for x in raw["rate_shocks"]),
        fx_shocks=tuple(Decimal(x) for x in raw["fx_shocks"]),
        hedge_ratio=None if raw["hedge"] is None else Decimal(raw["hedge"]),
    )


@pytest.mark.parametrize(
    "name",
    [
        pytest.param(name, marks=_E4A_XFAIL) if name == "fixture_no_rate_terms" else name
        for name in sorted(EXPECTED["fixtures"])
    ],
)
def test_composer_fixture(name: str) -> None:
    assert _stored_all(_fixture_result(name)) == EXPECTED["fixtures"][name]["stored"]


def test_e4a_currency_stated_without_balance_in_the_composer() -> None:
    """Ruling E4a, live: the five debt values of fixture_no_rate_terms carry the ruled reason;
    every other value equals the frozen fixture."""
    got = _stored_all(_fixture_result("fixture_no_rate_terms"))
    want = EXPECTED["fixtures"]["fixture_no_rate_terms"]["stored"]
    ruled = {"state": "missing", "reason": "the facility balance is not stated"}
    debt_keys = ("debt_change", "debt_after", "lev_after")
    assert got["foreign_debt"] == ruled
    assert got["foreign_debt_share"] == ruled
    assert [r[k] for r in got["fx"] for k in debt_keys] == [ruled] * (3 * len(got["fx"]))
    top = set(got) - {"foreign_debt", "foreign_debt_share", "fx"}
    assert {k: got[k] for k in top} == {k: want[k] for k in top}
    for g, w in zip(got["fx"], want["fx"], strict=True):
        assert {k: v for k, v in g.items() if k not in debt_keys} == {
            k: v for k, v in w.items() if k not in debt_keys
        }


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


# --- rulings round (docs/rulings/2026-10-28-stage1.md, CP-2E E1-E5) -------------------------
def _claim(result: cp2e.MacroFxResult, claim_id: str) -> cp2e.ClaimText:
    (claim,) = [c for c in result.claims if c.claim_id == claim_id]
    return claim


def _assert_prose_clean(result: cp2e.MacroFxResult) -> None:
    facts = [c.fact() for c in _cells(result)]
    bound = prose.bind(facts)
    for claim in result.claims:
        assert prose.issues(claim.text, bound) == (), (claim.claim_id, claim.text)


_SHARE = cp2e.Sourced(value=Decimal("0.2"), cite=("financial", "page:2"))
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
                for ebitda in ("30.0", "0"):
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
    """Every grid combination composes with prose-clean claims, except the one branch no ruling
    covers: coverage at base known but coverage after a shock not known (cash interest exactly
    offset by the added interest)."""
    raised = 0
    for label, inputs in _grid():
        try:
            result = cp2e.compute(inputs)
        except ValueError as error:
            assert str(error).startswith("Claim figure: T2F.3.r0"), (label, error)
            assert str(error).endswith(".cov_after is not a known number"), (label, error)
            s = cp2e.derive_sensitivity(
                operands=cp2e.operands_of(inputs),
                rate_shocks_bp=inputs.rate_shocks_bp,
                fx_shocks=inputs.fx_shocks,
                hedge_ratio=inputs.hedge_ratio,
            )
            assert s.cov_base.state == "known", label
            assert any(r.gross.state == "known" != r.cov_after.state for r in s.rate), label
            raised += 1
            continue
        _assert_prose_clean(result)
    assert raised == 24  # floating, floor 0, cash interest -0.5 (offset by the 100 bp shock)


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
