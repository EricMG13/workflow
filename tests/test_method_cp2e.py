"""CP-2E Stage 1: the pure calculation equals the frozen oracle (cases/cp2e-owner).

Inputs come from the oracle's own literals (submissions.json) and the frozen financial pages
(cases/financial/manifest.json); every expected value is read from expected.json.
"""

import copy
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


@pytest.mark.parametrize("name", sorted(EXPECTED["fixtures"]))
def test_composer_fixture(name: str) -> None:
    fixture = EXPECTED["fixtures"][name]
    raw = fixture["inputs"]
    got = cp2e.derive_sensitivity(
        operands=_operands(raw),
        rate_shocks_bp=tuple(Decimal(x) for x in raw["rate_shocks"]),
        fx_shocks=tuple(Decimal(x) for x in raw["fx_shocks"]),
        hedge_ratio=None if raw["hedge"] is None else Decimal(raw["hedge"]),
    )
    assert _stored_all(got) == fixture["stored"]


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
    sub = copy.deepcopy(SUBMISSIONS[SUBMISSIONS["refusal_mutations"]["base"]])
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


def test_fx_claim_with_a_stated_share_is_refused() -> None:
    """The lease fixes no FX claim wording when the foreign EBITDA share is stated: fail closed."""
    inputs = _inputs("positive")
    share = cp2e.Sourced(value=Decimal("0.2"), cite=("financial", "page:2"))
    stated = copy.replace(inputs, foreign_ebitda_share=share, operating_fx_absence=None)
    with pytest.raises(ValueError, match="FX claim"):
        cp2e.compute(stated)


def test_rate_claim_without_fixed_wording_is_refused() -> None:
    """Branches the lease gives no claim wording for fail closed instead of misstating."""
    inputs = _inputs("positive")
    assert inputs.facility is not None
    floor = copy.replace(inputs.facility.floor_bp, value=Decimal(25))
    floor_binds = copy.replace(inputs, facility=copy.replace(inputs.facility, floor_bp=floor))
    with pytest.raises(ValueError, match="Rate claim"):
        cp2e.compute(floor_binds)
    no_interest = copy.replace(inputs, interest=copy.replace(inputs.interest, value=Decimal(0)))
    with pytest.raises(ValueError, match="Rate claim"):
        cp2e.compute(no_interest)
