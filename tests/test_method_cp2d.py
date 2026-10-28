"""Stage 1: the CP-2D (Liquidity) calculation against the frozen oracle cases/cp2d-owner.

Every expected value is read from cases/cp2d-owner/expected.json; every input is built from the
oracle's own source facts, its fixtures (manifest.fixtures) and the literal submissions. The
run-time binding of ``{{FACT:name}}`` to a CP-1 fact id is stood in for by ``cp1:<name>``; the
real ids come from the promoted CP-1 head in Stage 2.
"""

import dataclasses
import json
import re
from calendar import monthrange
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from defect_classes import BLANK_CASES, EMPTY_TEXT, Adapter, BlankCase, blank_failure
from hypothesis import given, settings
from hypothesis import strategies as st

from deploy_vii import prose
from deploy_workflow.owners import cp2d

CASE = Path(__file__).resolve().parents[1] / "cases" / "cp2d-owner"
EXPECTED: dict[str, Any] = json.loads((CASE / "expected.json").read_text())
MANIFEST: dict[str, Any] = json.loads((CASE / "manifest.json").read_text())
SUBMISSIONS: dict[str, Any] = json.loads((CASE / "submissions.json").read_text())
SF: dict[str, Any] = EXPECTED["source_facts"]
CASES: dict[str, Any] = EXPECTED["cases"]
PACK_CASES = ("positive", "long_horizon", "gap_minimum_cash")
FIXTURES = {f["fixture_id"]: f for f in MANIFEST["fixtures"]}
BALANCE_DATE = date.fromisoformat(EXPECTED["method_rules"]["balance_date"])
TOKEN = re.compile(r"\{\{FACT:([^}]+)\}\}")


def _d(value: str) -> Decimal:
    return Decimal(value)


def _cp1_cell_amount(operand: str) -> Decimal:
    """A CP-1 T4.10 value the composer cross-checks, as the oracle pins it in the positive table."""
    for table in CASES["positive"]["tables"].values():
        for _, cells in table["rows"]:
            for cell in cells if isinstance(cells, list) else [cells]:
                if cell.get("cp1_operand") == operand:
                    return _d(cell["amount"])
    raise AssertionError(operand)


def _k(name: str, amount: Decimal | str) -> cp2d.Operand:
    """A known CP-1 operand carrying the period the manifest binds to `name`."""
    return cp2d.Operand("known", Decimal(amount), MANIFEST["fact_bindings"][name]["period"], None)


def _ro(operands: cp2d.Operands, **changes: Any) -> cp2d.Operands:
    """`replace` for Operands: a Decimal becomes a known operand with the bound period."""
    wrapped: dict[str, Any] = {
        k: _k(k, v) if isinstance(v, Decimal) else v for k, v in changes.items()
    }
    return replace(operands, **wrapped)


def _base_operands() -> cp2d.Operands:
    loan = SF["term_loan"]
    assert SF["net_debt_issuance_ltm"]["derivation"] == "debt issuance 5.00 less repayment 0"
    assert "explicit zeros" in SF["equity_issuance_plus_repurchases_ltm"]["source"]
    assert SF["equity_issuance_plus_repurchases_ltm"]["amount"] == "0"
    return cp2d.Operands(
        opening_cash=_k("opening_cash", SF["opening_cash_2024_12_31"]["amount"]),
        cfo=_k("cfo", _d(SF["operating_cash_flow_ltm"]["amount"])),
        investing=_k("investing", _d(SF["net_cash_used_in_investing_ltm"]["amount"])),
        net_debt_issuance=_k("net_debt_issuance", _d(SF["net_debt_issuance_ltm"]["amount"])),
        equity_issuance=_k("equity_issuance", Decimal(0)),
        equity_repurchases=_k("equity_repurchases", Decimal(0)),
        dividends_paid=_k("dividends_paid", _d(SF["dividends_paid_ltm"]["amount"])),
        other_investing_financing=_k(
            "other_investing_financing", _d(SF["other_investing_financing_ltm"]["amount"])
        ),
        financing=_k("financing", _d(SF["net_cash_used_in_financing_ltm"]["amount"])),
        fx_effect=_k("fx_effect", _d(SF["fx_effect_ltm"]["amount"])),
        closing_cash=_k("closing_cash", _d(SF["closing_cash_2025_12_31"]["amount"])),
        cash_bs=_k("cash_bs", _d(SF["closing_cash_2025_12_31"]["amount"])),
        restricted_cash=_k("restricted_cash", _d(SF["restricted_cash"]["amount"])),
        rcf_commitment=_k("rcf_commitment", _d(SF["rcf_commitment"]["amount"])),
        rcf_drawn=_k("rcf_drawn", _d(SF["rcf_drawn"]["amount"])),
        total_debt_bs=_k("total_debt_bs", _d(SF["total_debt"]["amount"])),
        cash_closing=_k("cash_closing", _d(SF["closing_cash_2025_12_31"]["amount"])),
        total_debt=_k("total_debt", _d(SF["total_debt"]["amount"])),
        undrawn_rcf=_k("undrawn_rcf", _cp1_cell_amount("undrawn_rcf")),
        liquidity=_k("liquidity", _cp1_cell_amount("liquidity")),
        liquidity_to_debt=_k("liquidity_to_debt", _cp1_cell_amount("liquidity_to_debt")),
        facilities=(
            cp2d.Facility(
                facility_id=loan["facility_id"],
                name="Northbridge Term Loan",
                currency="USD",
                principal=_d(loan["principal"]),
                maturity_date=date.fromisoformat(loan["maturity_date"]),
                commitment=_d(loan["commitment"]),
                drawn_amount=_d(loan["drawn"]),
                annual_amortisation=_d(loan["annual_amortisation"]),
                period=MANIFEST["fact_bindings"]["T4.18 principal"]["period"],
            ),
        ),
    )


def _base_loan() -> cp2d.Facility:
    facilities = _base_operands().facilities
    assert facilities is not None
    return facilities[0]


def _operands(case: str) -> cp2d.Operands:
    base = _base_operands()
    if case in ("fixture_rcf_undisclosed", "fixture_rcf_undisclosed_min_above_cash"):
        text = FIXTURES["fixture_rcf_undisclosed"]["construction"]
        for item in (
            "RCF commitment",
            "RCF drawings",
            "undrawn_rcf",
            "liquidity",
            "liquidity_to_debt",
        ):
            assert item in text
        return replace(
            base,
            rcf_commitment=None,
            rcf_drawn=None,
            undrawn_rcf=None,
            liquidity=None,
            liquidity_to_debt=None,
        )
    if case == "fixture_burn":
        assert (
            "Operating cash flow (LTM Q4 25) replaced by 13.00"
            in (FIXTURES["fixture_burn"]["construction"])
        )
        return _ro(base, cfo=Decimal("13.00"))
    return base


def _minimum_cash(case: str) -> Decimal | None:
    raw = CASES[case]["minimum_cash"]
    return None if raw is None else _d(raw)


def _bridge(case: str) -> cp2d.Bridge:
    return cp2d.compose_bridge(
        operands=_operands(case),
        horizon_months=CASES[case]["horizon_months"],
        minimum_cash=_minimum_cash(case),
        balance_date=BALANCE_DATE,
    )


def _bind(value: Any) -> Any:
    if isinstance(value, str):
        return TOKEN.sub(lambda m: "cp1:" + m.group(1).replace(" ", "_"), value)
    if isinstance(value, list):
        return [_bind(v) for v in value]
    if isinstance(value, dict):
        return {k: _bind(v) for k, v in value.items()}
    return value


OFFERED = frozenset(_bind("{{FACT:" + name + "}}") for name in MANIFEST["fact_bindings"])
MATURITY_REFS = frozenset({_bind("{{FACT:T4.18 maturity_date}}")})


def _submission(payload: dict[str, Any]) -> cp2d.LiquidityBridgeSubmission:
    return cp2d.LiquidityBridgeSubmission.model_validate_json(json.dumps(_bind(payload)))


def _inputs(case: str) -> cp2d.Cp2dInputs:
    submission = _submission(SUBMISSIONS["cp2d"][case])
    assert submission.horizon_months == CASES[case]["horizon_months"]
    amount = None if submission.minimum_cash is None else submission.minimum_cash.amount
    assert amount == _minimum_cash(case)
    return cp2d.Cp2dInputs(
        operands=_operands(case),
        balance_date=BALANCE_DATE,
        submission=submission,
        offered_refs=OFFERED,
        maturity_date_refs=MATURITY_REFS,
    )


def _plain(value: object) -> object:
    """A Gap compares as the oracle's null."""
    return None if isinstance(value, cp2d.Gap) else value


def _num_equal(got: object, want: str | None) -> bool:
    got = _plain(got)
    if want is None or got is None:
        return got is None and want is None
    return got == _d(want)


# --- derived values (Method items 1-6) ------------------------------------------------------


@pytest.mark.parametrize("case", list(CASES))
def test_derived_values_equal_oracle(case: str) -> None:
    bridge = _bridge(case)
    want = CASES[case]["derived"]
    assert len(bridge.wall) == 1
    row = bridge.wall[0]
    assert row.months_to_maturity == want["months_to_maturity"]
    assert row.inside_horizon is want["maturity_inside_horizon"]
    assert bridge.maturity_inside_horizon is want["maturity_inside_horizon"]
    assert bridge.horizon_end.isoformat() == want["horizon_end"]
    assert bridge.runway_state == want["runway_state"]
    months = bridge.months_to_minimum_cash
    assert (None if months is None else str(months)) == want["months_to_minimum_cash"]
    decimal_keys = [
        k
        for k in want
        if k
        not in (
            "months_to_maturity",
            "maturity_inside_horizon",
            "horizon_end",
            "runway_state",
            "months_to_minimum_cash",
        )
    ]
    for key in decimal_keys:
        assert _num_equal(getattr(bridge, key), want[key]), (case, key, getattr(bridge, key))
    for key in CASES[case]["missing_not_zero"]:
        assert _plain(getattr(bridge, key)) is None, (case, key)


@pytest.mark.parametrize("case", list(CASES))
def test_own_limitations_equal_oracle(case: str) -> None:
    got = cp2d.own_limitations(operands=_operands(case), bridge=_bridge(case))
    assert list(got) == CASES[case]["own_limitations"]


def test_compose_bridge_refuses_horizon_outside_bound() -> None:
    for months in (0, 61):
        with pytest.raises(ValueError, match="between 1 and 60"):
            cp2d.compose_bridge(
                operands=_base_operands(),
                horizon_months=months,
                minimum_cash=Decimal(10),
                balance_date=BALANCE_DATE,
            )


# --- tables, claims, ledgers (pack cases) -----------------------------------------------------


# --- round 13 item 1 (R1 M1): the declared delta to the frozen oracle -------------------------
#
# The frozen oracle (cases/cp2d-owner/expected.json) is NOT re-pinned until the Stage 2 release.
# Until then this test compares everything exactly as before and adds, as the two named tables
# below, the one declared delta: the `period` of each known numeric cell and the `value_class` of
# the five gap cells. Remove both tables at the Stage 2 re-pin (see
# test_frozen_oracle_still_lacks_the_round13_delta).

_BALANCE = "2025-12-31"
_LTM = "LTM Q4 25 \u00b7 2025-01-01 to 2025-12-31"
_Q4_BALANCE = "q4-2025 \u00b7 2025-10-01 to 2025-12-31"
_T410 = "LTM Q4 25: 2025-01-01 to 2025-12-31"
# cp1_operand -> the CP-1 fact's own period, verbatim; a numeric cell with no cp1_operand takes
# the balance date.
PERIOD_DELTA: dict[str, str] = {
    **dict.fromkeys(
        (
            "opening_cash",
            "cfo",
            "investing",
            "net_debt_issuance",
            "equity_issuance+equity_repurchases",
            "dividends_paid",
            "other_investing_financing",
            "fx_effect",
            "closing_cash",
        ),
        _LTM,
    ),
    **dict.fromkeys(
        ("cash_bs", "restricted_cash", "rcf_commitment", "rcf_drawn", "total_debt_bs"), _Q4_BALANCE
    ),
    **dict.fromkeys(("undrawn_rcf", "liquidity", "liquidity_to_debt"), _T410),
    **dict.fromkeys(("T4.18 commitment - drawn_amount", "T4.18 principal"), "q4-2025"),
}
GAP_VALUE_CLASS_DELTA: dict[tuple[str, str], str] = {
    ("gap_minimum_cash", "T2E.3.r09"): "calculated",
    ("gap_minimum_cash", "T2E.5.r04"): "analyst_judgment",
    ("gap_minimum_cash", "T2E.5.r05"): "calculated",
    ("gap_minimum_cash", "T2E.5.r06"): "calculated",
    ("gap_minimum_cash", "T2E.5.r07"): "calculated",
}


def test_period_delta_names_the_manifest_periods() -> None:
    """The delta table spells each CP-1 period as the manifest binds it."""
    bindings = MANIFEST["fact_bindings"]
    for operand, period in PERIOD_DELTA.items():
        names = [n.strip() for part in operand.split("+") for n in part.split(" - ")]
        names = [n if n in bindings else f"T4.18 {n}" for n in names]
        assert {bindings[n]["period"] for n in names} == {period}, operand


def test_frozen_oracle_still_lacks_the_round13_delta() -> None:
    """Remove the delta at the Stage 2 re-pin: this fails once expected.json carries `period`
    on its known numeric cells and `value_class` on the five gap cells, at which point
    PERIOD_DELTA, GAP_VALUE_CLASS_DELTA and their use in _assert_cell are deleted."""
    gap_keys: set[tuple[str, str]] = set()
    for case in PACK_CASES:
        for table in CASES[case]["tables"].values():
            for _, cells in table["rows"]:
                for cell in cells if isinstance(cells, list) else [cells]:
                    assert "period" not in cell, (case, cell["fact_id"])
                    if cell["state"] != "known" and "value_class" not in cell:
                        gap_keys.add((case, cell["fact_id"]))
    assert gap_keys == set(GAP_VALUE_CLASS_DELTA)


def _assert_cell(got: cp2d.Cell, want: dict[str, Any], case: str) -> None:
    where = want["fact_id"]
    assert got.fact_id == want["fact_id"]
    assert got.state == want["state"], where
    want_class = want.get("value_class", GAP_VALUE_CLASS_DELTA.get((case, where)))
    assert got.value_class == want_class, where
    numeric = want["state"] == "known" and want.get("amount") is not None
    operand = want.get("cp1_operand")
    want_period = (_BALANCE if operand is None else PERIOD_DELTA[operand]) if numeric else None
    assert got.period == want_period, where
    assert got.unit == want.get("unit"), where
    assert _num_equal(got.amount, want.get("amount")), where
    assert got.cp1_operand == want.get("cp1_operand"), where
    assert got.cp1_unit == want.get("cp1_unit"), where
    assert got.reason == want.get("reason"), where
    if want["state"] == "gap":
        # The G number is assigned by the report at run time (lease Acceptance 7).
        assert got.shown is None, where
        assert want["shown_pattern"] == "∅ G<n>"
        assert got.spell(gap_id="G7") == "∅ G7", where
    else:
        assert got.shown == want["shown"], where
        assert got.spell() == want["shown"], where


@pytest.mark.parametrize("case", PACK_CASES)
def test_tables_equal_oracle(case: str) -> None:
    result = cp2d.compute(_inputs(case))
    want_tables = CASES[case]["tables"]
    assert [t.table_id for t in result.tables] == list(want_tables)
    for table in result.tables:
        want = want_tables[table.table_id]
        assert table.title == want["title"]
        assert table.row_header == want["row_header"]
        assert list(table.columns) == want["columns"]
        assert [r.label for r in table.rows] == [r[0] for r in want["rows"]]
        for row, (_, cells) in zip(table.rows, want["rows"], strict=True):
            want_cells = cells if isinstance(cells, list) else [cells]
            assert len(row.cells) == len(want_cells)
            for got_cell, want_cell in zip(row.cells, want_cells, strict=True):
                _assert_cell(got_cell, want_cell, case)


@pytest.mark.parametrize("case", PACK_CASES)
def test_ledgers_limitations_status_equal_oracle(case: str) -> None:
    result = cp2d.compute(_inputs(case))
    module = EXPECTED["cp2d_module"]
    assert result.judgments.table_id == "T2E.6"
    assert result.judgments.title == module["T2E.6"]["title"]
    assert [list(r) for r in result.judgments.rows] == CASES[case]["T2E.6_rows"]
    assert result.gaps_ledger.table_id == "T2E.7"
    assert result.gaps_ledger.title == module["T2E.7"]["title"]
    assert [list(r) for r in result.gaps_ledger.rows] == CASES[case]["T2E.7_rows"]
    assert list(result.own_limitations) == CASES[case]["own_limitations"]
    assert result.status == CASES[case]["status"]


@pytest.mark.parametrize("case", PACK_CASES)
def test_claims_equal_oracle(case: str) -> None:
    result = cp2d.compute(_inputs(case))
    want = CASES[case]["claims"]
    assert [c.claim_id for c in result.claims] == [c["claim_id"] for c in want]
    cells = {c.fact_id: c for t in result.tables for r in t.rows for c in r.cells}
    for got, exp in zip(result.claims, want, strict=True):
        assert got.template == exp["template"], got.claim_id
        assert got.text == exp["text"], got.claim_id
        assert list(got.references) == exp["references"], got.claim_id
        assert list(got.cites_from) == exp["cites_from"], got.claim_id
        for ref in got.references:  # a referenced cell is a known own amount (lease Acceptance 1)
            assert cells[ref].state == "known" and cells[ref].unit == "MILLIONS"


def _cells(result: cp2d.Cp2dResult) -> dict[str, cp2d.Cell]:
    return {c.fact_id: c for t in result.tables for r in t.rows for c in r.cells}


def _claim(result: cp2d.Cp2dResult, claim_id: str) -> cp2d.ClaimText:
    return next(c for c in result.claims if c.claim_id == claim_id)


def test_undisclosed_revolver_composes_with_chip_claims() -> None:
    """Ruling 2D2: chip-form LIQ-01 and GAP-01; the table gap reasons stay as the oracle builder
    pins them (cases/cp2d-owner/builder/build.py build_tables)."""
    inputs = replace(_inputs("positive"), operands=_operands("fixture_rcf_undisclosed"))
    result = cp2d.compute(inputs)
    assert list(result.own_limitations) == CASES["fixture_rcf_undisclosed"]["own_limitations"]
    cells = _cells(result)
    assert cells["T2E.2.r03"].reason == "Revolver commitment not disclosed in the CP-1 register"
    assert cells["T2E.2.r04"].reason == "Revolver drawings not disclosed in the CP-1 register"
    assert cells["T2E.2.r05"].reason == "Undrawn revolver not calculable: commitment undisclosed"
    assert cells["T2E.2.r07"].reason == "Available liquidity not calculable: revolver undisclosed"
    assert cells["T2E.2.r09"].reason == "Not calculable: available liquidity missing"
    assert cells["T2E.5.r03"].reason == "Not calculable: revolver undisclosed"
    assert cells["T2E.5.r07"].reason == "Not calculable: revolver undisclosed"
    assert cells["T2E.5.r05"].amount == _d(
        CASES["fixture_rcf_undisclosed"]["derived"]["cash_only_headroom"]
    )
    liq = _claim(result, "CP-2D-LIQ-01")
    assert liq.template == (
        "Available liquidity at 31 Dec 2025 is not calculated: [T2E.2.r07] needs the undrawn "
        "committed revolver, which is undisclosed; cash is {T2E.2.r01|US$ m}."
    )
    assert liq.text.endswith("; cash is 20 US$ m.")
    assert liq.chips == ("T2E.2.r07",) and liq.references == ("T2E.2.r01",)
    gap = _claim(result, "CP-2D-GAP-01")
    assert gap.text == (
        "The funding gap is not calculated because the revolver is undisclosed; cash-only "
        "headroom over the assumed minimum cash is 10 US$ m."
    )


def test_sources_and_uses_difference_composes_restricted() -> None:
    """Lease Method 6: a non-zero difference is a known value with its own limitation, never a
    refusal; the T2E.7 label is the builder's (build.py limitations())."""
    inputs = replace(_inputs("positive"), operands=_operands("fixture_burn"))
    result = cp2d.compute(inputs)
    assert result.status == "restricted"
    assert list(result.own_limitations) == CASES["fixture_burn"]["own_limitations"]
    assert ("Sources and uses difference", "Limitation") in result.gaps_ledger.rows
    assert [label for label, _ in result.gaps_ledger.rows] == [
        "Run-rate basis",
        "Minimum cash",
        "Runway basis",
        "Sources and uses difference",
    ]
    t1 = result.tables[0]
    difference = t1.rows[-1].cells[0]
    want = CASES["fixture_burn"]["derived"]["sources_and_uses_difference"]
    assert difference.state == "known" and difference.amount == _d(want)
    assert difference.shown == "(6)"


def test_unknown_basis_ref_refuses_in_compute() -> None:
    payload = SUBMISSIONS["refusal_inputs"]["unknown_basis_ref"]["payload"]
    inputs = replace(_inputs("positive"), submission=_submission(payload))
    with pytest.raises(ValueError, match=EXPECTED["refusals"]["unknown_basis_ref"]):
        cp2d.compute(inputs)


def test_liquidity_to_debt_cross_check_uses_the_cp1_division() -> None:
    """CP-1 divides with deploy_vii.model._cells.CONTEXT (38 digits, half-even); 20/30 is not
    exact, so the cross-check must divide the same way to agree exactly."""
    from deploy_vii.model._cells import CONTEXT

    inputs = _inputs("positive")
    operands = _ro(
        inputs.operands,
        total_debt_bs=Decimal(30),
        total_debt=Decimal(30),
        liquidity_to_debt=CONTEXT.divide(Decimal(20), Decimal(30)),
    )
    tampered = replace(inputs, operands=operands)
    assert cp2d.check_cp1_totals(operands=operands, bridge=cp2d.bridge_of(tampered)) == ()
    cp2d.compute(tampered)


def test_compute_refuses_an_invalid_submission() -> None:
    inputs = _inputs("positive")
    payload = SUBMISSIONS["refusal_inputs"]["section_missing"]["payload"]
    with pytest.raises(ValueError, match=EXPECTED["refusals"]["section_missing"]):
        cp2d.compute(replace(inputs, submission=_submission(payload)))


def test_cp1_cross_check_mismatch_settles_with_a_limitation() -> None:
    """Ruling 2D-d: CP-2D uses its recomputed value and records the difference."""
    inputs = _inputs("positive")
    assert cp2d.check_cp1_totals(operands=inputs.operands, bridge=cp2d.bridge_of(inputs)) == ()
    tampered = replace(inputs, operands=_ro(inputs.operands, liquidity=Decimal(21)))
    result = cp2d.compute(tampered)
    want = (
        "CP-1's liquidity differs from the value recomputed from its line items; CP-2D uses the "
        "recomputed value and shows both."
    )
    assert result.own_limitations[-1] == want
    assert _cells(result)["T2E.2.r07"].amount == Decimal(20)
    absent = replace(inputs, operands=replace(inputs.operands, undrawn_rcf=None))
    result = cp2d.compute(absent)
    want = "CP-1 reports no undrawn_rcf; the value recomputed from its line items is used."
    assert result.own_limitations[-1] == want
    assert _cells(result)["T2E.2.r05"].amount == Decimal(0)


# --- calculation-level refusals ---------------------------------------------------------------


@pytest.mark.parametrize("case", list(EXPECTED["refusals"]))
def test_refusal_inputs_produce_oracle_issue(case: str) -> None:
    entry = SUBMISSIONS["refusal_inputs"][case]
    issues = cp2d.submission_issues(
        submission=_submission(entry["payload"]),
        offered_refs=OFFERED,
        maturity_date_refs=MATURITY_REFS,
    )
    assert issues == (EXPECTED["refusals"][case],)


@pytest.mark.parametrize("case", PACK_CASES)
def test_literal_submissions_are_valid(case: str) -> None:
    submission = _submission(SUBMISSIONS["cp2d"][case])
    assert (
        cp2d.submission_issues(
            submission=submission, offered_refs=OFFERED, maturity_date_refs=MATURITY_REFS
        )
        == ()
    )


@pytest.mark.parametrize("attempt", ["attempt_0", "attempt_1"])
def test_blocked_attempts_produce_oracle_issues(attempt: str) -> None:
    submission = _submission(SUBMISSIONS["cp2d_blocked"][attempt])
    want = EXPECTED["negative_cases"]["blocked_cp2d"][attempt]["issues"]
    assert (
        list(
            cp2d.submission_issues(
                submission=submission, offered_refs=OFFERED, maturity_date_refs=MATURITY_REFS
            )
        )
        == want
    )


@pytest.mark.parametrize(
    "probe",
    [
        "An LME is likely.",
        "We recommend the bonds.",
        "The recovery outcome is weak.",
        "Liability management is likely.",
    ],
)
def test_prohibited_conclusion_stems_refuse(probe: str) -> None:
    """Stems pinned by the oracle builder's FORBIDDEN list (manifest analyst_judgment_policy)."""
    payload = json.loads(json.dumps(SUBMISSIONS["cp2d"]["positive"]))
    payload["assessments"][2]["credit_implication"] += " " + probe
    issues = cp2d.submission_issues(
        submission=_submission(payload), offered_refs=OFFERED, maturity_date_refs=MATURITY_REFS
    )
    assert issues == (EXPECTED["refusals"]["figure_free_text_forbidden_word"],)


# --- missing schedule and total debt --------------------------------------------------------


def _compose(operands: cp2d.Operands, horizon: int, minimum: str | None) -> cp2d.Bridge:
    return cp2d.compose_bridge(
        operands=operands,
        horizon_months=horizon,
        minimum_cash=None if minimum is None else Decimal(minimum),
        balance_date=BALANCE_DATE,
    )


def test_empty_facility_schedule_is_missing_not_zero() -> None:
    operands = replace(_base_operands(), facilities=())
    b = _compose(operands, 24, "10")
    for key in (
        "maturity_inside_horizon",
        "maturities_in_horizon",
        "amortisation_in_horizon",
        "cash_at_horizon_end_before_refinancing",
        "resources_at_horizon_end",
        "cash_only_headroom",
        "headroom",
        "funding_gap",
        "undrawn_term_commitment",
    ):
        value = getattr(b, key)
        assert isinstance(value, cp2d.Gap), key
        assert value.reason == "Not calculable: the T4.18 facility schedule lists no facility"
    assert b.wall == ()
    result = cp2d.compute(replace(_inputs("positive"), operands=operands))
    assert _cells(result)["T2E.3.r07"].state == "gap"


@pytest.mark.parametrize("total_debt", [None, Decimal(0)])
def test_missing_total_debt_keeps_wall_terms_known(total_debt: Decimal | None) -> None:
    b = _compose(_ro(_base_operands(), total_debt_bs=total_debt), 24, "10")
    (row,) = b.wall
    assert row.months_to_maturity == CASES["positive"]["derived"]["months_to_maturity"]
    assert row.inside_horizon is False
    for value in (row.share_of_total_debt, row.cumulative_share, b.liquidity_to_total_debt):
        assert isinstance(value, cp2d.Gap)
        if total_debt is None:
            assert value.applicable and value.reason == "Not calculable: Total debt is missing"
        else:  # ruling 2D5: not meaningful
            assert not value.applicable
            assert (
                value.reason == "Not meaningful: total debt is zero (ZERO_OR_NEGATIVE_DENOMINATOR)"
            )


# --- lease-literal branch cases (controller-authorised, fix round 1) --------------------------


def test_amortisation_scaled_to_horizon() -> None:
    # lease-literal: CP2D lease Method 3 (min(annual amortisation x H / 12, principal))
    loan = _base_loan()
    operands = replace(
        _base_operands(), facilities=(replace(loan, annual_amortisation=Decimal(6)),)
    )
    b = _compose(operands, 24, "10")
    assert b.amortisation_in_horizon == Decimal(12)  # 6 x 24 / 12
    assert b.maturities_in_horizon == 0
    assert b.cash_at_horizon_end_before_refinancing == Decimal(8)  # 20 + 0 - 12 - 0


def test_amortisation_capped_at_principal() -> None:
    # lease-literal: CP2D lease Method 3 (min(30 x 24 / 12 = 60, principal 50) = 50)
    loan = _base_loan()
    operands = replace(
        _base_operands(), facilities=(replace(loan, annual_amortisation=Decimal(30)),)
    )
    b = _compose(operands, 24, "10")
    assert b.amortisation_in_horizon == Decimal(50)
    assert b.cash_at_horizon_end_before_refinancing == Decimal(-30)


def test_runway_months_round_half_up_and_count_the_revolver() -> None:
    # lease-literal: CP2D lease Method 3. F = -29 - 10 - 4 - 5 = -48; undrawn = 71 - 0 = 71;
    # start = 20 + 71 - 10 = 81; months = 81 / (48 / 12) = 20.25 -> 20.3 (1 dp half-up)
    operands = _ro(_base_operands(), cfo=Decimal(-29), rcf_commitment=Decimal(71))
    b = _compose(operands, 24, "10")
    assert b.run_rate_net_cash_flow_annual == Decimal(-48)
    assert b.undrawn_revolver == Decimal(71)
    assert b.available_liquidity == Decimal(91)
    assert b.runway_state == "months"
    assert str(b.months_to_minimum_cash) == "20.3"


def test_runway_negative_start_with_burn_is_zero_months() -> None:
    # lease-literal: CP2D lease Method 3. F = -6 < 0; start = 20 + 0 - 30 = -10;
    # max(0, start) / (6 / 12) = 0.0
    b = _compose(_ro(_base_operands(), cfo=Decimal(13)), 24, "30")
    assert b.runway_state == "months"
    assert str(b.months_to_minimum_cash) == "0.0"


def test_runway_negative_start_without_burn_is_zero_months() -> None:
    # lease-literal: CP2D lease Method 3. F = 0 >= 0 and start = 20 - 30 < 0 -> 0 months
    b = _compose(_base_operands(), 24, "30")
    assert b.runway_state == "months"
    assert str(b.months_to_minimum_cash) == "0.0"


def test_runway_revolver_missing_with_burn_is_missing() -> None:
    # lease-literal: CP2D lease Method 3. "Not reached" only when F >= 0 and cash clears the
    # minimum; F = -6 here, so missing ("Not calculable: revolver undisclosed")
    operands = _ro(_operands("fixture_rcf_undisclosed"), cfo=Decimal(13))
    b = _compose(operands, 24, "10")
    assert b.runway_state == "missing"
    assert b.runway_reason == "Not calculable: revolver undisclosed"
    assert b.months_to_minimum_cash is None


def test_fixture_runway_reason_is_the_lease_text() -> None:
    b = _bridge("fixture_rcf_undisclosed_min_above_cash")
    assert b.runway_reason == "Not calculable: revolver undisclosed"


def test_maturity_on_the_horizon_end_is_inside() -> None:
    # lease-literal: CP2D lease Method 3/4 (maturity_date <= horizon end; 2025-12-31 + 48 months
    # = 2029-12-31 = maturity)
    b = _compose(_base_operands(), 48, "10")
    assert b.horizon_end == date(2029, 12, 31)
    assert b.maturity_inside_horizon is True and b.wall[0].inside_horizon is True
    assert b.maturities_in_horizon == Decimal(50)
    assert b.cash_at_horizon_end_before_refinancing == Decimal(-30)


def test_two_facilities_cumulative_share_in_maturity_order() -> None:
    # lease-literal: CP2D lease Method 4 (share of total debt and cumulative share); ruling 2D6
    # orders by (maturity_date, facility_id): the earlier facility has the later id (N3)
    loan = _base_loan()
    early = replace(
        loan,
        facility_id="b-loan",
        principal=Decimal(20),
        commitment=Decimal(20),
        drawn_amount=Decimal(20),
        maturity_date=date(2027, 6, 30),
    )
    late = replace(
        loan,
        facility_id="a-loan",
        principal=Decimal(30),
        commitment=Decimal(30),
        drawn_amount=Decimal(30),
    )
    b = _compose(replace(_base_operands(), facilities=(late, early)), 24, "10")
    assert [r.facility.facility_id for r in b.wall] == ["b-loan", "a-loan"]
    assert [r.share_of_total_debt for r in b.wall] == [Decimal("0.4"), Decimal("0.6")]
    assert [r.cumulative_share for r in b.wall] == [Decimal("0.4"), Decimal("1.0")]
    assert b.maturities_in_horizon == Decimal(20)  # 2027-06-30 <= 2027-12-31


def test_drawn_revolver_undrawn_is_commitment_less_drawn() -> None:
    # lease-literal: CP2D lease Method 2/5. undrawn = 30 - 10 = 20; available = 20 + 20 = 40;
    # resources = 20 + 20 = 40; headroom = 40 - 10 = 30; gap = max(0, 10 - 40) = 0
    operands = _ro(_base_operands(), rcf_commitment=Decimal(30), rcf_drawn=Decimal(10))
    b = _compose(operands, 24, "10")
    assert b.undrawn_revolver == Decimal(20)
    assert b.available_liquidity == Decimal(40)
    assert b.resources_at_horizon_end == Decimal(40)
    assert b.headroom == Decimal(30)
    assert b.funding_gap == 0


def test_undrawn_term_commitment_is_commitment_less_drawn() -> None:
    # lease-literal: CP2D lease Method 2 (T4.18 commitment - drawn = 60 - 50 = 10, not counted)
    loan = _base_loan()
    operands = replace(_base_operands(), facilities=(replace(loan, commitment=Decimal(60)),))
    b = _compose(operands, 24, "10")
    assert b.undrawn_term_commitment == Decimal(10)
    assert b.available_liquidity == Decimal(20)


# --- rulings round 2 and 3 (docs/rulings/2026-10-28-stage1.md, CP-2D) -------------------------


def _analyst_issues(extra: str) -> tuple[str, ...]:
    payload = json.loads(json.dumps(SUBMISSIONS["cp2d"]["positive"]))
    payload["assessments"][0]["text"] += " " + extra
    return cp2d.submission_issues(
        submission=_submission(payload), offered_refs=OFFERED, maturity_date_refs=MATURITY_REFS
    )


@pytest.mark.parametrize(
    "extra", ["The issuer may resell the notes.", "A Helmet clause applies.", "The buyer pays."]
)
def test_forbidden_stems_match_as_substrings(extra: str) -> None:
    """Ruling 2D1: substring match, so a stem inside another word refuses (a recorded limit)."""
    assert _analyst_issues(extra) == (EXPECTED["refusals"]["covenant_compliance_wording"],)


@pytest.mark.parametrize(
    "field", ["text", "credit_implication", "limitation", "rationale", "reason", "follow_up"]
)
def test_forbidden_stems_checked_on_every_analyst_field(field: str) -> None:
    """Ruling 2D-a: every analyst text field is checked."""
    case = "gap_minimum_cash" if field in ("reason", "follow_up", "limitation") else "positive"
    payload = json.loads(json.dumps(SUBMISSIONS["cp2d"][case]))
    if field == "rationale":
        payload["minimum_cash"][field] += " Refinancing is likely."
    elif field in ("reason", "follow_up"):
        payload["minimum_cash_absence"][field] += " Refinancing is likely."
    elif field == "limitation":
        payload["assessments"][2][field] += " Refinancing is likely."
    else:
        payload["assessments"][1][field] += " Refinancing is likely."
    issues = cp2d.submission_issues(
        submission=_submission(payload), offered_refs=OFFERED, maturity_date_refs=MATURITY_REFS
    )
    assert issues == (EXPECTED["refusals"]["figure_free_text_forbidden_word"],)


def test_python_wording_is_not_checked_for_forbidden_stems() -> None:
    """Ruling 2D-a: CP-2D's own labels and claim templates carry stems and are not checked."""
    result = cp2d.compute(_inputs("positive"))
    labels = [r.label for t in result.tables for r in t.rows]
    assert "Cash at horizon end before refinancing" in labels
    assert any("refinancing" in c.template for c in result.claims)
    assert result.status == "restricted"


def test_missing_operand_settles_with_its_reason() -> None:
    """Ruling 2D-b: the cell and every dependant carry the first missing operand's reason."""
    inputs = _inputs("positive")
    result = cp2d.compute(replace(inputs, operands=replace(inputs.operands, cfo=None)))
    reason = "Not calculable: Operating cash flow is missing"
    cells = _cells(result)
    for fact_id in (
        "T2E.1.r02",
        "T2E.1.r09",
        "T2E.1.r11",
        "T2E.3.r01",
        "T2E.3.r02",
        "T2E.3.r05",
        "T2E.3.r08",
        "T2E.3.r09",
        "T2E.5.r01",
        "T2E.5.r03",
        "T2E.5.r05",
        "T2E.5.r06",
        "T2E.5.r07",
    ):
        assert cells[fact_id].state == "gap" and cells[fact_id].reason == reason, fact_id
    assert cells["T2E.2.r07"].state == "known"  # liquidity needs no cash flow
    run = _claim(result, "CP-2D-RUN-01")
    assert run.chips == ("T2E.3.r01", "T2E.3.r08") and run.references == ()
    gap = _claim(result, "CP-2D-GAP-01")
    assert gap.chips == ("T2E.5.r07",)
    assert list(result.own_limitations) == CASES["positive"]["own_limitations"]


def test_non_feeding_missing_operand_is_only_a_missing_cell() -> None:
    inputs = _inputs("positive")
    result = cp2d.compute(replace(inputs, operands=replace(inputs.operands, restricted_cash=None)))
    cell = _cells(result)["T2E.2.r02"]
    assert cell.state == "gap" and cell.reason == "Not calculable: Restricted cash is missing"
    assert list(result.own_limitations) == CASES["positive"]["own_limitations"]
    assert sum(c.state != "known" for c in _cells(result).values()) == 1


def _with_loan(loan: cp2d.Facility) -> cp2d.Cp2dInputs:
    inputs = _inputs("positive")
    return replace(inputs, operands=replace(inputs.operands, facilities=(loan,)))


LOAN = _base_loan()


def test_undated_facility_settles_with_the_date_reason() -> None:
    """Ruling 2D-c (maturity date)."""
    result = cp2d.compute(_with_loan(replace(LOAN, maturity_date=None)))
    reason = "Not calculable: facility term-loan maturity date is not stated"
    cells = _cells(result)
    for fact_id in ("T2E.4.r01.c2", "T2E.4.r01.c3", "T2E.4.r01.c4", "T2E.4.r01.c6"):
        assert cells[fact_id].state == "gap" and cells[fact_id].reason == reason, fact_id
    assert cells["T2E.4.r01.c1"].state == "known" and cells["T2E.4.r01.c5"].state == "known"
    for fact_id in ("T2E.3.r06", "T2E.3.r07", "T2E.3.r08", "T2E.5.r07"):
        assert cells[fact_id].reason == reason, fact_id
    assert result.own_limitations[-1] == (
        "Facility term-loan maturity date is not stated; maturity-wall figures that need it are "
        "not calculated."
    )
    assert _claim(result, "CP-2D-MAT-01").chips == ("T2E.3.r07",)


def test_unstated_principal_settles_with_the_principal_reason() -> None:
    """Ruling 2D-c (principal): the maturity date, months and inside-horizon stay known."""
    result = cp2d.compute(_with_loan(replace(LOAN, principal=None)))
    reason = "Not calculable: facility term-loan principal is not stated"
    cells = _cells(result)
    for fact_id in ("T2E.4.r01.c1", "T2E.4.r01.c5", "T2E.4.r01.c6"):
        assert cells[fact_id].reason == reason, fact_id
    assert cells["T2E.4.r01.c2"].shown == "2029-12-31"
    # The loan matures after the horizon: amortisation needs the principal, maturities do not.
    assert cells["T2E.3.r06"].reason == reason
    assert cells["T2E.3.r07"].amount == 0


def test_unstated_currency_takes_the_non_usd_path() -> None:
    """Ruling 2D-c (currency)."""
    result = cp2d.compute(_with_loan(replace(LOAN, currency=None)))
    reason = (
        "Not calculable: facility term-loan currency is not stated; no FX conversion is applied"
    )
    cells = _cells(result)
    for fact_id in ("T2E.4.r01.c1", "T2E.4.r01.c5", "T2E.4.r01.c6", "T2E.3.r07", "T2E.2.r06"):
        assert cells[fact_id].reason == reason, fact_id
    assert result.own_limitations[-1] == (
        "Facility term-loan currency is not stated; maturity-wall figures that need it are not "
        "calculated."
    )


def test_non_usd_facility_settles_with_the_fx_reason() -> None:
    """Ruling 2D5."""
    result = cp2d.compute(_with_loan(replace(LOAN, currency="EUR")))
    reason = "Not calculable: facility term-loan is in EUR, not USD; no FX conversion is applied"
    cells = _cells(result)
    for fact_id in (
        "T2E.4.r01.c1",
        "T2E.4.r01.c5",
        "T2E.4.r01.c6",
        "T2E.3.r06",
        "T2E.3.r07",
        "T2E.3.r08",
        "T2E.5.r01",
        "T2E.5.r03",
        "T2E.5.r05",
        "T2E.5.r06",
        "T2E.5.r07",
    ):
        assert cells[fact_id].reason == reason, fact_id
    for fact_id in ("T2E.4.r01.c2", "T2E.4.r01.c3", "T2E.4.r01.c4"):
        assert cells[fact_id].state == "known", fact_id
    assert result.own_limitations[-1] == (
        "Facility term-loan is denominated in EUR; maturity-wall totals and shares are not "
        "calculated because no FX conversion is applied."
    )
    assert _claim(result, "CP-2D-MAT-01").template == (
        "The cash outflow from debt maturing inside the horizon is not calculated: [T2E.3.r07] "
        "needs every facility in USD, and one is not; no FX conversion is applied."
    )
    assert _claim(result, "CP-2D-GAP-01").chips == ("T2E.5.r07",)


def test_fx_facility_makes_every_later_cumulative_share_missing() -> None:
    early = replace(LOAN, facility_id="eur", currency="EUR", maturity_date=date(2027, 1, 31))
    late = replace(LOAN, facility_id="usd")
    b = _compose(replace(_base_operands(), facilities=(late, early)), 24, "10")
    eur, usd = b.wall
    assert isinstance(eur.share_of_total_debt, cp2d.Gap)
    assert isinstance(usd.cumulative_share, cp2d.Gap)
    assert usd.cumulative_share.reason == eur.share_of_total_debt.reason
    assert usd.share_of_total_debt == 1


def test_undated_facility_sorts_after_dated_ones() -> None:
    """Ruling 2D-c: an undated facility follows every dated one, ordered by facility_id."""
    facilities = (
        replace(LOAN, facility_id="a-undated", maturity_date=None),
        replace(LOAN, facility_id="z-dated"),
    )
    b = _compose(replace(_base_operands(), facilities=facilities), 24, "10")
    assert [r.facility.facility_id for r in b.wall] == ["z-dated", "a-undated"]


def test_zero_total_debt_shares_are_not_meaningful() -> None:
    """Ruling 2D5 (zero total debt)."""
    inputs = _inputs("positive")
    operands = _ro(
        inputs.operands, total_debt_bs=Decimal(0), total_debt=Decimal(0), liquidity_to_debt=None
    )
    result = cp2d.compute(replace(inputs, operands=operands))
    cells = _cells(result)
    for fact_id in ("T2E.4.r01.c5", "T2E.4.r01.c6", "T2E.2.r09"):
        assert cells[fact_id].state == "not_applicable", fact_id
        assert cells[fact_id].reason == (
            "Not meaningful: total debt is zero (ZERO_OR_NEGATIVE_DENOMINATOR)"
        )
        assert cells[fact_id].spell(gap_id="G3") == "∅ G3 n.m."


def test_ledger_headers() -> None:
    """Ruling 2D8."""
    result = cp2d.compute(_inputs("positive"))
    assert result.judgments.row_header == "Judgment"
    assert result.judgments.column == ("value", "Value")
    assert result.gaps_ledger.row_header == "Item"
    assert result.gaps_ledger.column == ("kind", "Kind")


def test_sources_and_uses_use_the_financing_total() -> None:
    """Ruling 2D9: the financing lines are display rows; a difference is a limitation."""
    inputs = _inputs("positive")
    operands = _ro(inputs.operands, dividends_paid=Decimal(-8))  # lines sum to (3), total (4)
    result = cp2d.compute(replace(inputs, operands=operands))
    b = result.bridge
    assert b.sources_and_uses_closing_cash_calculated == Decimal(20)  # 15 + 19 - 10 - 4 + 0
    assert b.sources_and_uses_difference == 0
    assert b.financing_lines_difference == Decimal(1)
    assert ("Financing lines difference", "Limitation") in result.gaps_ledger.rows
    assert (
        "Financing lines differ from CP-1's net cash used in financing by 1 US$ m; sources and "
        "uses use the financing total."
    ) in result.own_limitations


def test_negative_zero_minimum_cash_is_stored_unsigned() -> None:
    """N2: "-0" passes validation and is stored as an unsigned zero."""
    payload = json.loads(json.dumps(SUBMISSIONS["cp2d"]["positive"]))
    payload["minimum_cash"]["amount"] = "-0"
    result = cp2d.compute(replace(_inputs("positive"), submission=_submission(payload)))
    assert result.bridge.minimum_cash is not None and not result.bridge.minimum_cash.is_signed()
    amount = _cells(result)["T2E.5.r04"].amount
    assert amount is not None and not amount.is_signed()


def _no_raise_cases() -> list[tuple[str, cp2d.Cp2dInputs]]:
    """The reviewer's raise list (probe3 section 5): valid submissions that used to raise."""
    inputs = _inputs("positive")
    o = inputs.operands
    cases: list[tuple[str, cp2d.Cp2dInputs]] = []
    for amount in ("1E+30", "123456789012345678901234567890"):
        payload = json.loads(json.dumps(SUBMISSIONS["cp2d"]["positive"]))
        payload["minimum_cash"]["amount"] = amount
        cases.append((f"minimum cash {amount}", replace(inputs, submission=_submission(payload))))
    missing: dict[str, Any] = dict.fromkeys(cp2d.OPERAND_LABELS)
    all_missing = replace(o, **missing)
    variants: tuple[tuple[str, cp2d.Operands], ...] = (
        ("restricted_cash None", replace(o, restricted_cash=None)),
        ("undrawn_rcf None", replace(o, undrawn_rcf=None)),
        ("liquidity_to_debt None", replace(o, liquidity_to_debt=None)),
        ("cash_closing differs", _ro(o, cash_closing=Decimal(21))),
        ("facility commitment None", replace(o, facilities=(replace(LOAN, commitment=None),))),
        ("total debt zero", _ro(o, total_debt_bs=Decimal(0), total_debt=Decimal(0))),
        ("EUR facility", replace(o, facilities=(replace(LOAN, currency="EUR"),))),
        (
            "negative total debt",
            _ro(o, total_debt_bs=Decimal(-50), total_debt=Decimal(-50), liquidity_to_debt=None),
        ),
        ("tiny burn", _ro(o, cfo=Decimal(19) - Decimal("1E-60"))),
        ("every operand missing", all_missing),
        ("no facilities", replace(o, facilities=())),
        ("revolver drawn missing only", replace(o, rcf_drawn=None)),
    )
    for label, operands in variants:
        cases.append((label, replace(inputs, operands=operands)))
    return cases


NO_RAISE = _no_raise_cases()


@pytest.mark.parametrize("index", range(len(NO_RAISE)), ids=[label for label, _ in NO_RAISE])
def test_valid_submissions_never_raise(index: int) -> None:
    label, inputs = NO_RAISE[index]
    result = cp2d.compute(inputs)
    assert result.status == "restricted", label
    for cell in _cells(result).values():
        assert cell.state == "known" or cell.reason, (label, cell.fact_id)


# --- Stage 1 layer review: ledger Low L4 (first-missing precedence) ----------------------------


def test_first_missing_operand_in_formula_order_wins() -> None:
    """Ruling 2D-b: a dependant carries the reason of the first missing operand in formula
    order. Cash at horizon end = cash_bs + F over horizon - amortisation - maturities, so with
    cash_bs and cfo both missing every dependant names cash; F's own cell, which does not read
    cash, names operating cash flow. With cfo and investing both missing, F = cfo + investing +
    financing - net debt issuance names operating cash flow."""
    inputs = _inputs("positive")
    o = inputs.operands
    cash = "Not calculable: Cash and cash equivalents is missing"
    cfo = "Not calculable: Operating cash flow is missing"
    cells = _cells(cp2d.compute(replace(inputs, operands=replace(o, cash_bs=None, cfo=None))))
    for fact_id in ("T2E.3.r08", "T2E.3.r09", "T2E.5.r01", "T2E.5.r03", "T2E.5.r07", "T2E.2.r07"):
        assert cells[fact_id].reason == cash, fact_id
    assert cells["T2E.3.r01"].reason == cfo
    cells = _cells(cp2d.compute(replace(inputs, operands=replace(o, cfo=None, investing=None))))
    for fact_id in ("T2E.1.r09", "T2E.3.r01", "T2E.3.r08", "T2E.3.r09", "T2E.5.r07"):
        assert cells[fact_id].reason == cfo, fact_id


# --- rulings round 5 (docs/rulings/2026-10-28-stage1.md "# Round 5", CP-2D) --------------------

GAP_FX = (
    "The funding gap is not calculated: [T2E.5.r07] needs every facility in USD, and one is not."
)


def _gap_text(result: cp2d.Cp2dResult) -> str:
    return _claim(result, "CP-2D-GAP-01").template


def test_d1_facility_term_rows_are_gaps() -> None:
    result = cp2d.compute(_with_loan(replace(LOAN, maturity_date=None)))
    assert ("Facility maturity date (term-loan)", "Gap") in result.gaps_ledger.rows


def test_d1_d3_empty_schedule_row_and_reason() -> None:
    inputs = _inputs("positive")
    result = cp2d.compute(replace(inputs, operands=replace(inputs.operands, facilities=())))
    assert ("Facility schedule", "Gap") in result.gaps_ledger.rows
    assert (
        "The T4.18 facility schedule lists no facility; maturity-wall figures are not calculated."
    ) in result.own_limitations
    reason = "Not calculable: the T4.18 facility schedule lists no facility"
    assert _cells(result)["T2E.3.r07"].reason == reason


def test_d3_empty_schedule_with_zero_total_debt_is_known_zero() -> None:
    operands = _ro(_base_operands(), facilities=(), total_debt_bs=Decimal(0), total_debt=Decimal(0))
    b = _compose(operands, 24, "10")
    assert b.maturities_in_horizon == 0 and b.amortisation_in_horizon == 0
    assert b.cash_at_horizon_end_before_refinancing == Decimal(20)
    assert b.maturity_inside_horizon is False
    inputs = _inputs("positive")
    result = cp2d.compute(replace(inputs, operands=operands))
    assert not any(label == "Facility schedule" for label, _ in result.gaps_ledger.rows)
    assert _cells(result)["T2E.2.r09"].reason == cp2d.ZERO_DEBT


def test_d3_absent_schedule_keeps_schedule_missing() -> None:
    b = _compose(replace(_base_operands(), facilities=None), 24, "10")
    assert isinstance(b.maturities_in_horizon, cp2d.Gap)
    assert b.maturities_in_horizon.reason == "Not calculable: T4.18 facility schedule is missing"


@pytest.mark.parametrize(
    "term,field,fact_id",
    [
        ("commitment", "commitment", "T2E.2.r06"),
        ("drawn amount", "drawn_amount", "T2E.2.r06"),
        ("annual amortisation", "annual_amortisation", "T2E.3.r06"),
    ],
)
def test_d3_term_reasons_use_the_not_stated_frame(term: str, field: str, fact_id: str) -> None:
    cleared: dict[str, Any] = {field: None}
    result = cp2d.compute(_with_loan(replace(LOAN, **cleared)))
    want = f"Not calculable: facility term-loan {term} is not stated"
    assert _cells(result)[fact_id].reason == want


def test_d4_negative_total_debt_reason() -> None:
    b = _compose(_ro(_base_operands(), total_debt_bs=Decimal(-50)), 24, "10")
    share = b.wall[0].share_of_total_debt
    assert isinstance(share, cp2d.Gap) and not share.applicable
    assert share.reason == "Not meaningful: total debt is negative (ZERO_OR_NEGATIVE_DENOMINATOR)"


def test_d5_wall_assessment_must_cite_the_maturity_date() -> None:
    payload = json.loads(json.dumps(SUBMISSIONS["cp2d"]["positive"]))
    wall = next(a for a in payload["assessments"] if a["section"] == "maturity_wall")
    wall["basis_refs"] = [r for r in wall["basis_refs"] if "maturity_date" not in r]
    issues = cp2d.submission_issues(
        submission=_submission(payload), offered_refs=OFFERED, maturity_date_refs=MATURITY_REFS
    )
    assert issues == ("the maturity_wall assessment must cite T4.18 maturity_date",)


@pytest.mark.parametrize(
    "loan,want",
    [
        (replace(LOAN, currency="EUR"), GAP_FX),
        (
            replace(LOAN, currency=None),
            (
                "The funding gap is not calculated: [T2E.5.r07] needs every facility with "
                "its currency stated, and one is not."
            ),
        ),
        (
            replace(LOAN, maturity_date=None),
            (
                "The funding gap is not calculated: [T2E.5.r07] needs every facility with "
                "its maturity date stated, and one is not."
            ),
        ),
        (
            replace(LOAN, principal=None),
            (
                "The funding gap is not calculated: [T2E.5.r07] needs every facility with "
                "its principal stated, and one is not."
            ),
        ),
    ],
)
def test_d2_l5_gap01_facility_forms(loan: cp2d.Facility, want: str) -> None:
    assert _gap_text(cp2d.compute(_with_loan(loan))) == want


@pytest.mark.parametrize(
    "loan,term",
    [
        (replace(LOAN, currency=None, maturity_date=None, principal=None), "currency"),
        (replace(LOAN, maturity_date=None, principal=None), "maturity date"),
    ],
)
def test_d2_facility_causes_in_the_ruled_order(loan: cp2d.Facility, term: str) -> None:
    assert _gap_text(cp2d.compute(_with_loan(loan))) == (
        f"The funding gap is not calculated: [T2E.5.r07] needs every facility with its {term} "
        "stated, and one is not."
    )


def test_d2_facility_cause_beats_a_missing_operand() -> None:
    inputs = _with_loan(replace(LOAN, currency="EUR"))
    inputs = replace(inputs, operands=replace(inputs.operands, cash_bs=None))
    assert _gap_text(cp2d.compute(inputs)) == GAP_FX


def test_d2_missing_operand_form() -> None:
    inputs = _inputs("positive")
    result = cp2d.compute(replace(inputs, operands=replace(inputs.operands, cfo=None)))
    assert _gap_text(result) == (
        "The funding gap is not calculated: [T2E.5.r07] needs Operating cash flow, which is "
        "missing."
    )


@pytest.mark.parametrize(
    "facilities,label",
    [(None, "the facility schedule"), ((), "a facility in the facility schedule")],
)
def test_d2_schedule_form_carries_no_bare_figure(
    facilities: tuple[cp2d.Facility, ...] | None, label: str
) -> None:
    inputs = _inputs("positive")
    result = cp2d.compute(replace(inputs, operands=replace(inputs.operands, facilities=facilities)))
    text = _gap_text(result)
    assert (
        text == f"The funding gap is not calculated: [T2E.5.r07] needs {label}, which is missing."
    )
    assert prose.check(text, refs=(), gaps={"T2E.5.r07"}) == ()


def test_d2_missing_operand_beats_the_revolver_form() -> None:
    operands = replace(_operands("fixture_rcf_undisclosed"), cfo=None)
    result = cp2d.compute(replace(_inputs("positive"), operands=operands))
    assert _gap_text(result) == (
        "The funding gap is not calculated: [T2E.5.r07] needs Operating cash flow, which is "
        "missing."
    )


def test_l1_commitment_known_drawings_missing() -> None:
    inputs = _inputs("positive")
    result = cp2d.compute(replace(inputs, operands=replace(inputs.operands, rcf_drawn=None)))
    cells = _cells(result)
    assert cells["T2E.2.r05"].reason == "Undrawn revolver not calculable: drawings undisclosed"
    assert cells["T2E.2.r07"].reason == (
        "Available liquidity not calculable: revolver drawings undisclosed"
    )
    assert result.bridge.runway_reason is None  # F = 0 and cash clears the minimum: not reached
    burn = _ro(inputs.operands, rcf_drawn=None, cfo=Decimal(13))
    b = cp2d.compose_bridge(
        operands=burn, horizon_months=24, minimum_cash=Decimal(10), balance_date=BALANCE_DATE
    )
    assert b.runway_reason == "Not calculable: revolver drawings undisclosed"
    assert _claim(result, "CP-2D-LIQ-01").template == (
        "Available liquidity at 31 Dec 2025 is not calculated: [T2E.2.r07] needs the revolver "
        "drawings, which are undisclosed; cash is {T2E.2.r01|US$ m}."
    )
    assert _gap_text(result) == (
        "The funding gap is not calculated because the revolver drawings are undisclosed; "
        "cash-only headroom over the assumed minimum cash is {T2E.5.r05|US$ m}."
    )
    assert result.own_limitations[-1] == (
        "The funding gap is not calculated because the revolver drawings are undisclosed; the "
        "cash-only headroom over minimum cash is shown as a lower bound."
    )


def test_l3_differences_are_spelled_exactly() -> None:
    inputs = _inputs("positive")
    operands = _ro(inputs.operands, closing_cash=Decimal("20.4"), dividends_paid=Decimal("-8.75"))
    result = cp2d.compute(replace(inputs, operands=operands))
    assert "Sources and uses differ from reported closing cash by (0.4) US$ m." in (
        result.own_limitations
    )
    assert (
        "Financing lines differ from CP-1's net cash used in financing by 0.25 US$ m; sources "
        "and uses use the financing total."
    ) in result.own_limitations


def test_l3_difference_is_not_rounded_to_the_default_context() -> None:
    inputs = _inputs("positive")
    closing = Decimal("20.123456789012345678901234567890123")  # 33 significant digits differ
    result = cp2d.compute(replace(inputs, operands=_ro(inputs.operands, closing_cash=closing)))
    assert (
        "Sources and uses differ from reported closing cash by "
        "(0.123456789012345678901234567890123) US$ m."
    ) in result.own_limitations


# --- round 6 (A1) and round 6f -----------------------------------------------------------------


@pytest.mark.parametrize(
    "maturity,months",
    [
        ("2027-06-30", 18),  # Dec 31 to a 30-day month end: add_months(D0, 18) = 2027-06-30
        ("2028-06-30", 30),  # the ruling's example
        ("2027-06-29", 17),
        ("2027-12-31", 24),  # the frozen maturities keep their values
        ("2028-07-31", 31),
        ("2029-12-31", 48),
        ("2030-12-31", 60),
    ],
)
def test_a1_months_is_the_largest_n_on_or_before_maturity(maturity: str, months: int) -> None:
    loan = replace(LOAN, maturity_date=date.fromisoformat(maturity))
    b = _compose(replace(_base_operands(), facilities=(loan,)), 24, "10")
    assert b.wall[0].months_to_maturity == months


def test_a1_months_and_inside_horizon_agree_at_a_month_end() -> None:
    loan = replace(LOAN, maturity_date=date(2027, 6, 30))
    for horizon, inside in ((17, False), (18, True)):
        b = _compose(replace(_base_operands(), facilities=(loan,)), horizon, "10")
        assert (b.wall[0].months_to_maturity, b.wall[0].inside_horizon) == (18, inside)


def _clamped(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, monthrange(year, month)[1]))


# Month ends (28 to 31) are where calendar months and day counts disagree, so most draws land there.
_DATES = st.builds(
    _clamped, st.integers(2000, 2040), st.integers(1, 12), st.sampled_from([1, 15, 28, 29, 30, 31])
)


@settings(max_examples=500, deadline=None)
@given(d0=_DATES, maturity=_DATES, horizon=st.integers(1, 60))
def test_a1_property_months_bound_the_horizon_test(d0: date, maturity: date, horizon: int) -> None:
    months = cp2d.months_between(d0, maturity)
    assert cp2d.add_months(d0, months) <= maturity < cp2d.add_months(d0, months + 1)
    inside = maturity <= cp2d.add_months(d0, horizon)
    if months < horizon:
        assert inside
    if months > horizon:
        assert not inside


def test_6f_d_unstated_currency_takes_the_currency_frame_on_mat01() -> None:
    result = cp2d.compute(_with_loan(replace(LOAN, currency=None)))
    assert _claim(result, "CP-2D-MAT-01").template == (
        "The cash outflow from debt maturing inside the horizon is not calculated: [T2E.3.r07] "
        "needs every facility with its currency stated, and one is not; no FX conversion is "
        "applied."
    )


def test_6f_d_stated_foreign_currency_keeps_mat_fx() -> None:
    result = cp2d.compute(_with_loan(replace(LOAN, currency="EUR")))
    assert _claim(result, "CP-2D-MAT-01").template == (
        "The cash outflow from debt maturing inside the horizon is not calculated: [T2E.3.r07] "
        "needs every facility in USD, and one is not; no FX conversion is applied."
    )


def test_6f_e_drawings_case_carries_only_the_l1_strings() -> None:
    inputs = _inputs("positive")
    result = cp2d.compute(replace(inputs, operands=replace(inputs.operands, rcf_drawn=None)))
    cells = _cells(result)
    # Round 9 item 1 corrects 6f (e): the ratio names its operand, available liquidity.
    assert cells["T2E.2.r09"].reason == (
        "Available liquidity not calculable: revolver drawings undisclosed"
    )
    assert cells["T2E.5.r03"].reason == "Not calculable: revolver drawings undisclosed"


# --- round 9 (item 1, D-1) and the riding Lows L1-L6 of round5-6-review.md ----------------------

CASH_MISSING = "Not calculable: Cash and cash equivalents is missing"


def test_r9_d1_currency_rows_by_kind() -> None:
    unstated = cp2d.compute(_with_loan(replace(LOAN, currency=None)))
    assert [r for r in unstated.gaps_ledger.rows if r[0].startswith("Facility currency")] == [
        ("Facility currency (term-loan)", "Gap")
    ]
    assert (
        "Facility term-loan currency is not stated; maturity-wall figures that need it are not "
        "calculated."
    ) in unstated.own_limitations
    foreign = cp2d.compute(_with_loan(replace(LOAN, currency="EUR")))
    assert [r for r in foreign.gaps_ledger.rows if r[0].startswith("Facility currency")] == [
        ("Facility currency (term-loan)", "Limitation")
    ]


def _two_loans(first: str | None, second: str | None) -> cp2d.Cp2dInputs:
    inputs = _inputs("positive")
    a = replace(LOAN, facility_id="a-loan", currency=first, maturity_date=date(2028, 12, 31))
    b = replace(LOAN, facility_id="b-loan", currency=second, maturity_date=date(2029, 12, 31))
    return replace(inputs, operands=replace(inputs.operands, facilities=(a, b)))


@pytest.mark.parametrize(
    "first,second,need",
    [(None, "EUR", "with its currency stated"), ("EUR", None, "in USD")],
)
def test_r9_l1_first_facility_in_wall_order_picks_the_mat01_form(
    first: str | None, second: str | None, need: str
) -> None:
    result = cp2d.compute(_two_loans(first, second))
    assert _claim(result, "CP-2D-MAT-01").template == (
        "The cash outflow from debt maturing inside the horizon is not calculated: [T2E.3.r07] "
        f"needs every facility {need}, and one is not; no FX conversion is applied."
    )


def test_r9_l2_amortisation_cause_only_after_the_horizon() -> None:
    inside = replace(LOAN, maturity_date=date(2026, 6, 30), annual_amortisation=None)
    operands = replace(_operands("fixture_rcf_undisclosed"), facilities=(inside,))
    result = cp2d.compute(replace(_inputs("positive"), operands=operands))
    assert _gap_text(result) == (
        "The funding gap is not calculated because the revolver is undisclosed; cash-only "
        "headroom over the assumed minimum cash is {T2E.5.r05|US$ m}."
    )


def test_r9_l3_cash_reason_wins_over_the_drawings_strings() -> None:
    inputs = _inputs("positive")
    operands = replace(inputs.operands, cash_bs=None, rcf_drawn=None)
    cells = _cells(cp2d.compute(replace(inputs, operands=operands)))
    for fact_id in ("T2E.2.r07", "T2E.5.r03", "T2E.2.r09"):
        assert cells[fact_id].reason == CASH_MISSING, fact_id


@pytest.mark.parametrize(
    "missing,label",
    [
        ({"cash_bs": None}, "Cash and cash equivalents"),
        ({"cfo": None, "net_debt_issuance": None}, "Operating cash flow"),
        ({"cfo": None, "facilities": None}, "Operating cash flow"),
    ],
)
def test_r9_l4_form4_names_the_first_operand_in_formula_order(
    missing: dict[str, Any], label: str
) -> None:
    inputs = _inputs("positive")
    result = cp2d.compute(replace(inputs, operands=replace(inputs.operands, **missing)))
    assert _gap_text(result) == (
        f"The funding gap is not calculated: [T2E.5.r07] needs {label}, which is missing."
    )


def test_r9_l5_only_a_known_zero_debt_makes_an_empty_schedule_known() -> None:
    b = _compose(_ro(_base_operands(), facilities=(), total_debt_bs=Decimal(-50)), 24, "10")
    assert isinstance(b.maturities_in_horizon, cp2d.Gap)
    assert b.maturities_in_horizon.reason == (
        "Not calculable: the T4.18 facility schedule lists no facility"
    )


def test_r9_l6_wall_date_issue_follows_basis_issue() -> None:
    payload = json.loads(json.dumps(SUBMISSIONS["cp2d"]["positive"]))
    payload["horizon_months"] = 0
    wall = next(a for a in payload["assessments"] if a["section"] == "maturity_wall")
    wall["basis_refs"] = [r for r in wall["basis_refs"] if "maturity_date" not in r]
    wall["basis_refs"].append("cp1:not-offered")
    issues = cp2d.submission_issues(
        submission=_submission(payload), offered_refs=OFFERED, maturity_date_refs=MATURITY_REFS
    )
    assert issues == (
        "horizon_months must be between 1 and 60",
        "basis_refs names a fact the view does not offer",
        "the maturity_wall assessment must cite T4.18 maturity_date",
    )


# --- round 11 class round: blank text (docs/rulings/2026-10-28-stage1.md "# Round 11", LEAD
# rulings "Blank text is one defect class"; tests/defect_classes.py). CP-2D reads no figure, name
# or label from an analyst quote, so only the blank cases apply. No CP-2D frame is pinned, so the
# fallback `<path>: empty text` is used.


def _blank_adapter(case: str, path: tuple[str | int, ...]) -> Adapter:
    """Places the value at `path` in a frozen literal submission; the page and quote are unused
    (CP-2D cites no quote)."""

    def adapter(page: str, quote: str, value: str) -> tuple[str, ...]:
        payload = json.loads(json.dumps(SUBMISSIONS["cp2d"][case]))
        cur: Any = payload
        for key in path[:-1]:
            cur = cur[key]
        cur[path[-1]] = value
        return cp2d.submission_issues(
            submission=_submission(payload),
            offered_refs=OFFERED,
            maturity_date_refs=MATURITY_REFS,
        )

    return adapter


def _blank_field(case: str, *path: str | int) -> tuple[str, Adapter]:
    """(the issue path, e.g. `assessments[0].text`, and its adapter)."""
    named = "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in path).lstrip(".")
    return named, _blank_adapter(case, path)


BLANK_FIELDS: tuple[tuple[str, Adapter], ...] = (
    *(
        _blank_field("positive", "assessments", i, field)
        for i in range(3)
        for field in ("text", "credit_implication")
    ),
    # A limitation on a non-Insufficient assessment also gets LIMITATION_ISSUE; on the
    # Insufficient Information assessment it also gets INSUFFICIENT_ISSUE (both unchanged).
    _blank_field("positive", "assessments", 0, "limitation"),
    _blank_field("gap_minimum_cash", "assessments", 2, "limitation"),
    _blank_field("positive", "minimum_cash", "rationale"),
    _blank_field("gap_minimum_cash", "minimum_cash_absence", "reason"),
    _blank_field("gap_minimum_cash", "minimum_cash_absence", "follow_up"),
)


@pytest.mark.parametrize("blank", BLANK_CASES, ids=[c.case_id for c in BLANK_CASES])
@pytest.mark.parametrize("path,adapter", BLANK_FIELDS, ids=[path for path, _ in BLANK_FIELDS])
def test_r11_blank_text_is_refused(blank: BlankCase, path: str, adapter: Adapter) -> None:
    assert blank_failure(blank, adapter, EMPTY_TEXT.format(path=path)) is None


@pytest.mark.parametrize("path,adapter", BLANK_FIELDS, ids=[path for path, _ in BLANK_FIELDS])
def test_r11_blank_text_twin_is_not_refused_as_empty(path: str, adapter: Adapter) -> None:
    """Real text in the same field is not refused as empty."""
    issues = adapter("", "", "Cash is held as an analyst assumption.")
    assert EMPTY_TEXT.format(path=path) not in issues


@pytest.mark.parametrize(
    "blank",
    [c for c in BLANK_CASES if c.whitespace_only],
    ids=[c.case_id for c in BLANK_CASES if c.whitespace_only],
)
def test_r12_b10_blank_limitation_is_not_stated(blank: BlankCase) -> None:
    """Round 12 B10: a blank limitation (whitespace or `Cf` only) on the Insufficient Information
    assessment is not stated, so it gets the empty-text issue and then the insufficient one."""
    adapter = _blank_adapter("gap_minimum_cash", ("assessments", 2, "limitation"))
    assert adapter(blank.page, blank.quote, blank.value) == (
        "assessments[2].limitation: empty text",
        EXPECTED["refusals"]["insufficient_without_limitation"],
    )


def test_r11_blank_fields_cover_every_analyst_text_field() -> None:
    """Every path CP-2D reads as analyst text (2D-a's list) is in BLANK_FIELDS, by field name."""
    positive = json.loads(json.dumps(SUBMISSIONS["cp2d"]["positive"]))
    for a in positive["assessments"]:
        a["limitation"] = "A stated limitation."
    read = [
        path
        for case in (positive, SUBMISSIONS["cp2d"]["gap_minimum_cash"])
        for path, _ in cp2d.analyst_text_fields(_submission(case))
    ]

    def name(path: str) -> str:
        return re.sub(r"\[\d+\]", "[i]", path)

    assert {name(p) for p in read} == {name(p) for p, _ in BLANK_FIELDS}
    assert set(read) >= {p for p, _ in BLANK_FIELDS}


def test_r11_blank_issue_sits_with_the_text_checks_in_field_order() -> None:
    """The empty-text issues follow SECTION_ISSUE and precede DIGIT_ISSUE, one per path."""
    payload = json.loads(json.dumps(SUBMISSIONS["cp2d"]["positive"]))
    payload["assessments"] = payload["assessments"][:2]
    payload["assessments"][1]["credit_implication"] = " "
    payload["assessments"][0]["text"] = "\t"
    payload["minimum_cash"]["rationale"] += " Seven of them."
    payload["minimum_cash"]["rationale"] = payload["minimum_cash"]["rationale"].replace(
        "Seven", "7"
    )
    issues = cp2d.submission_issues(
        submission=_submission(payload), offered_refs=OFFERED, maturity_date_refs=MATURITY_REFS
    )
    assert issues == (
        "assessments must hold exactly one row per section",
        "assessments[0].text: empty text",
        "assessments[1].credit_implication: empty text",
        "text must not contain a figure",
    )


# --- round 11 riding item: a maturity before D0 takes the CP-3C B1 rule (LEAD rulings "CP-2D, a
# maturity before D0") ---------------------------------------------------------------------------

PRE_D0 = "Not calculable: facility term-loan maturity date is before the balance date"
PRE_D0_LINE = (
    "Facility term-loan maturity date is before the balance date; maturity-wall figures that "
    "need it are not calculated."
)
PRE_D0_GAP = (
    "The funding gap is not calculated: [T2E.5.r07] needs every facility to mature on or after "
    "the balance date, and one does not."
)
# Months from D0 and inside-horizon, then every dependant: amortisation and maturities inside the
# horizon, cash at horizon end and the funding-gap rows built on it.
PRE_D0_CELLS = (
    "T2E.4.r01.c3",
    "T2E.4.r01.c4",
    "T2E.3.r06",
    "T2E.3.r07",
    "T2E.3.r08",
    "T2E.5.r01",
    "T2E.5.r03",
    "T2E.5.r05",
    "T2E.5.r06",
    "T2E.5.r07",
)


@pytest.mark.parametrize("maturity", [date(2025, 6, 30), BALANCE_DATE - timedelta(days=1)])
def test_r11_a_maturity_before_d0_is_a_gap(maturity: date) -> None:
    """D0 - 1 day included. The date, principal, shares and cumulative share stay known."""
    assert BALANCE_DATE == date(2025, 12, 31)
    result = cp2d.compute(_with_loan(replace(LOAN, maturity_date=maturity)))
    cells = _cells(result)
    for fact_id in PRE_D0_CELLS:
        assert (cells[fact_id].state, cells[fact_id].reason) == ("gap", PRE_D0), fact_id
    assert cells["T2E.4.r01.c2"].shown == maturity.isoformat()
    for fact_id in ("T2E.4.r01.c1", "T2E.4.r01.c5", "T2E.4.r01.c6", "T2E.3.r09", "T2E.2.r06"):
        assert cells[fact_id].state == "known", fact_id
    b = result.bridge
    assert b.maturity_inside_horizon == cp2d.Gap(PRE_D0)
    assert result.own_limitations[-1] == PRE_D0_LINE
    assert result.gaps_ledger.rows[-1] == ("Facility maturity date (term-loan)", "Limitation")
    assert "Interest after maturity" not in [label for label, _ in result.gaps_ledger.rows]
    assert _gap_text(result) == PRE_D0_GAP
    assert prose.check(PRE_D0_GAP, refs=(), gaps={"T2E.5.r07"}) == ()
    assert prose.bare_figures("needs every facility to mature on or after the balance date") == ()
    # MAT-01 keeps the chip form, as an unstated maturity date does.
    assert _claim(result, "CP-2D-MAT-01").chips == ("T2E.3.r07",)


def test_r11_a_maturity_on_d0_is_zero_months_and_inside() -> None:
    """D0 itself is not before D0: no reason, no own line, and the principal falls due."""
    result = cp2d.compute(_with_loan(replace(LOAN, maturity_date=BALANCE_DATE)))
    cells = _cells(result)
    assert (cells["T2E.4.r01.c3"].amount, cells["T2E.4.r01.c4"].shown) == (Decimal(0), "Yes")
    assert LOAN.principal is not None
    assert cells["T2E.3.r07"].amount == -LOAN.principal
    assert result.bridge.maturity_inside_horizon is True
    assert PRE_D0 not in {c.reason for c in cells.values()}
    assert not [x for x in result.own_limitations if "before the balance date" in x]
    assert ("Interest after maturity", "Limitation") in result.gaps_ledger.rows
    assert "before the balance date" not in _gap_text(result)
    # With the gap missing for another cause, form 3 finds nothing on D0 and form 4 speaks.
    on_d0 = _with_loan(replace(LOAN, maturity_date=BALANCE_DATE))
    on_d0 = replace(on_d0, operands=replace(on_d0.operands, cfo=None))
    assert _gap_text(cp2d.compute(on_d0)) == (
        "The funding gap is not calculated: [T2E.5.r07] needs Operating cash flow, which is "
        "missing."
    )


def test_r11_pre_d0_takes_the_maturity_date_slot_in_d2_order() -> None:
    """Currency comes first; the pre-D0 cause comes before an unstated principal."""
    past = replace(LOAN, maturity_date=date(2025, 6, 30))
    assert _gap_text(cp2d.compute(_with_loan(replace(past, principal=None)))) == PRE_D0_GAP
    assert _gap_text(cp2d.compute(_with_loan(replace(past, currency=None)))) == (
        "The funding gap is not calculated: [T2E.5.r07] needs every facility with its currency "
        "stated, and one is not."
    )


def test_r11_pre_d0_own_line_takes_the_maturity_date_slot() -> None:
    """The line sits where an unstated maturity date's line would, after the FX line and before
    the principal line."""
    past = replace(LOAN, maturity_date=date(2025, 6, 30), currency="EUR", principal=None)
    labels = [label for label, _ in cp2d.compute(_with_loan(past)).gaps_ledger.rows]
    start = labels.index("Facility currency (term-loan)")
    assert labels[start : start + 3] == [
        "Facility currency (term-loan)",
        "Facility maturity date (term-loan)",
        "Facility principal (term-loan)",
    ]


def test_r11_a_foreign_facility_before_d0_takes_the_fx_reason_in_the_schedule() -> None:
    """The currency precedence holds: a EUR facility that matures before D0 gives the schedule
    cells the FX reason, not the pre-D0 one."""
    past = replace(LOAN, maturity_date=date(2025, 6, 30), currency="EUR")
    cells = _cells(cp2d.compute(_with_loan(past)))
    fx = "Not calculable: facility term-loan is in EUR, not USD; no FX conversion is applied"
    for fact_id in ("T2E.3.r06", "T2E.3.r07", "T2E.3.r08"):
        assert (cells[fact_id].state, cells[fact_id].reason) == ("gap", fx), fact_id


def test_r11_a_known_inside_facility_keeps_the_flag_known() -> None:
    """With another facility known inside the horizon, some maturity falls inside it."""
    inputs = _inputs("positive")
    past = replace(LOAN, facility_id="old-loan", maturity_date=date(2025, 6, 30))
    inside = replace(LOAN, maturity_date=date(2026, 6, 30))
    result = cp2d.compute(
        replace(inputs, operands=replace(inputs.operands, facilities=(past, inside)))
    )
    assert result.bridge.maturity_inside_horizon is True
    reason = "Not calculable: facility old-loan maturity date is before the balance date"
    assert result.bridge.maturities_in_horizon == cp2d.Gap(reason)
    assert [w.facility.facility_id for w in result.bridge.wall] == ["old-loan", "term-loan"]
    assert not isinstance(result.bridge.wall[1].cumulative_share, cp2d.Gap)


# --- round 13 (docs/rulings/2026-10-28-stage1.md "# Round 13", R1 M1 and R1 M3) ----------------


def _op_inputs(**changes: Any) -> cp2d.Cp2dInputs:
    inputs = _inputs("positive")
    return replace(inputs, operands=_ro(inputs.operands, **changes))


def _opd(status: cp2d.OperandStatus, limitation: str | None = None) -> cp2d.Operand:
    """A non-known CP-1 operand: no amount, no period, the CP-1 limitation."""
    return cp2d.Operand(status, None, None, limitation or f"CP-1 limitation: {status}")


def test_r13_m1_a_copy_keeps_the_cp1_period_verbatim() -> None:
    """R1 M1: a known numeric copy carries its CP-1 fact's own period, whatever the string."""
    odd = cp2d.Operand("known", Decimal(19), "an odd CP-1 period string", None)
    cells = _cells(cp2d.compute(_op_inputs(cfo=odd)))
    assert cells["T2E.1.r02"].period == "an odd CP-1 period string"
    assert cells["T2E.1.r03"].period == PERIOD_DELTA["investing"]  # the others keep their own
    assert cells["T2E.1.r09"].period == _BALANCE  # a computed cell takes the balance date


def test_r13_m1_a_sum_takes_the_one_period_its_operands_share() -> None:
    shared = "LTM shared"
    inputs = _op_inputs(
        equity_issuance=cp2d.Operand("known", Decimal(0), shared, None),
        equity_repurchases=cp2d.Operand("known", Decimal(0), shared, None),
    )
    assert _cells(cp2d.compute(inputs))["T2E.1.r05"].period == shared


def test_r13_m1_a_sum_of_differing_periods_raises_the_invariant() -> None:
    inputs = _op_inputs(
        equity_issuance=cp2d.Operand("known", Decimal(0), "period a", None),
        equity_repurchases=cp2d.Operand("known", Decimal(0), "period b", None),
    )
    with pytest.raises(ValueError, match=r"^CP-2D: operands of T2E\.1\.r05 differ in period$"):
        cp2d.compute(inputs)


def test_r13_m1_a_difference_of_differing_facility_periods_raises_the_invariant() -> None:
    """T2E.2.r06 is the sum over facilities of commitment less drawn amount."""
    other = replace(LOAN, facility_id="other-loan", period="a different period")
    inputs = _with_loan(LOAN)
    inputs = replace(inputs, operands=replace(inputs.operands, facilities=(LOAN, other)))
    with pytest.raises(ValueError, match=r"^CP-2D: operands of T2E\.2\.r06 differ in period$"):
        cp2d.compute(inputs)


def test_r13_m1_a_facility_principal_keeps_the_facility_period() -> None:
    odd = replace(LOAN, period="a facility period")
    cells = _cells(cp2d.compute(_with_loan(odd)))
    assert cells["T2E.4.r01.c1"].period == "a facility period"
    assert cells["T2E.2.r06"].period == "a facility period"


def test_r13_m1_gap_not_applicable_and_text_cells_carry_no_period() -> None:
    missing = _cells(cp2d.compute(_op_inputs(cfo=None)))
    assert missing["T2E.1.r02"].state == "gap" and missing["T2E.1.r02"].period is None
    zero_debt = _cells(cp2d.compute(_op_inputs(total_debt_bs=Decimal(0))))
    assert zero_debt["T2E.2.r09"].state == "not_applicable"
    assert zero_debt["T2E.2.r09"].period is None
    positive = _cells(cp2d.compute(_inputs("positive")))
    assert positive["T2E.3.r04"].period is None  # horizon end date (text)
    assert positive["T2E.4.r01.c2"].period is None  # maturity date (text)
    inputs = _inputs("positive")
    assert all(c.period is None for c in _cells(cp2d.compute(inputs)).values() if c.amount is None)


def test_r13_m1_every_cell_carries_a_value_class_and_a_gap_takes_its_twins() -> None:
    twin = {fid: c.value_class for fid, c in _cells(cp2d.compute(_inputs("positive"))).items()}
    variants = (
        _inputs("gap_minimum_cash"),
        _op_inputs(cfo=None),
        _op_inputs(total_debt_bs=Decimal(0)),
        _op_inputs(cash_bs=_opd("conflicting")),
        replace(_inputs("positive"), operands=_operands("fixture_rcf_undisclosed")),
    )
    for inputs in variants:
        for fid, cell in _cells(cp2d.compute(inputs)).items():
            assert cell.value_class is not None, fid
            assert cell.value_class == twin[fid], fid


def test_r13_m1_a_copied_gap_keeps_cp1_operand_and_cp1_unit() -> None:
    cells = _cells(cp2d.compute(_op_inputs(cfo=None, rcf_commitment=None)))
    cfo = cells["T2E.1.r02"]
    assert (cfo.state, cfo.cp1_operand, cfo.cp1_unit) == ("gap", "cfo", "currency")
    commitment = cells["T2E.2.r03"]
    assert (commitment.value_class, commitment.cp1_operand) == ("source", "rcf_commitment")
    assert commitment.cp1_unit == "currency"
    undrawn = cells["T2E.2.r05"]
    assert (undrawn.value_class, undrawn.cp1_operand) == ("calculated", "undrawn_rcf")


def test_r13_m3_operand_shape_is_status_amount_period_limitation() -> None:
    assert [f.name for f in dataclasses.fields(cp2d.Operand)] == [
        "status",
        "amount",
        "period",
        "limitation",
    ]
    with pytest.raises(ValueError, match=r"^CP-2D: a known operand needs an amount and a period$"):
        cp2d.Operand("known", Decimal(1), None, None)
    with pytest.raises(ValueError, match=r"^CP-2D: a missing operand needs a limitation and no "):
        cp2d.Operand("missing", None, None, None)
    with pytest.raises(ValueError, match=r"^CP-2D: a conflicting operand needs a limitation"):
        cp2d.Operand("conflicting", Decimal(1), None, "x")


@pytest.mark.parametrize(
    "status,state,spelled",
    [
        ("missing", "gap", "∅ G7"),
        ("conflicting", "conflicting", "∅ G7"),
        ("not_applicable", "not_applicable", "∅ G7 n.m."),
    ],
)
def test_r13_m3_a_copy_keeps_the_cp1_status_with_its_limitation(
    status: cp2d.OperandStatus, state: str, spelled: str
) -> None:
    limitation = "CP-1 says: the line items disagree"
    cells = _cells(cp2d.compute(_op_inputs(cfo=_opd(status, limitation))))
    copy = cells["T2E.1.r02"]
    assert (copy.state, copy.reason, copy.amount, copy.period) == (state, limitation, None, None)
    assert copy.spell(gap_id="G7") == spelled
    assert (copy.value_class, copy.cp1_operand, copy.cp1_unit) == ("calculated", "cfo", "currency")


@pytest.mark.parametrize(
    "status,word",
    [
        ("missing", "missing"),
        ("conflicting", "conflicting"),
        ("not_applicable", "not applicable"),
    ],
)
def test_r13_m3_dependants_stay_gaps_with_the_state_word(
    status: cp2d.OperandStatus, word: str
) -> None:
    cells = _cells(cp2d.compute(_op_inputs(cfo=_opd(status))))
    reason = f"Not calculable: Operating cash flow is {word}"
    for fact_id in ("T2E.1.r09", "T2E.1.r11", "T2E.3.r01", "T2E.3.r08", "T2E.5.r07"):
        assert (cells[fact_id].state, cells[fact_id].reason) == ("gap", reason), fact_id


@pytest.mark.parametrize(
    "status,word",
    [
        ("missing", "missing"),
        ("conflicting", "conflicting"),
        ("not_applicable", "not applicable"),
    ],
)
def test_r13_m3_gap_operand_claim_names_the_status(status: cp2d.OperandStatus, word: str) -> None:
    result = cp2d.compute(_op_inputs(cfo=_opd(status)))
    text = _gap_text(result)
    assert text == (
        f"The funding gap is not calculated: [T2E.5.r07] needs Operating cash flow, which is "
        f"{word}."
    )
    assert prose.check(text, refs=(), gaps={"T2E.5.r07"}) == ()


def test_r13_m3_the_first_gap_in_formula_order_names_the_claim() -> None:
    both = cp2d.compute(_op_inputs(cash_bs=_opd("not_applicable"), cfo=_opd("conflicting")))
    assert _gap_text(both).endswith("needs Cash and cash equivalents, which is not applicable.")
    later = cp2d.compute(_op_inputs(investing=_opd("conflicting"), financing=_opd("missing")))
    assert _gap_text(later).endswith("needs Net cash used in investing, which is conflicting.")


@pytest.mark.parametrize("status", ["missing", "conflicting", "not_applicable"])
def test_r13_m3_a_non_known_operand_is_never_read_as_zero(status: cp2d.OperandStatus) -> None:
    inputs = _op_inputs(dividends_paid=_opd(status), rcf_drawn=_opd(status))
    result = cp2d.compute(inputs)
    for cell in _cells(result).values():
        assert cell.state == "known" or cell.reason
    assert _cells(result)["T2E.1.r06"].amount is None
