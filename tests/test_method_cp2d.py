"""Stage 1: the CP-2D (Liquidity) calculation against the frozen oracle cases/cp2d-owner.

Every expected value is read from cases/cp2d-owner/expected.json; every input is built from the
oracle's own source facts, its fixtures (manifest.fixtures) and the literal submissions. The
run-time binding of ``{{FACT:name}}`` to a CP-1 fact id is stood in for by ``cp1:<name>``; the
real ids come from the promoted CP-1 head in Stage 2.
"""

import json
import re
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

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


def _base_operands() -> cp2d.Operands:
    loan = SF["term_loan"]
    assert SF["net_debt_issuance_ltm"]["derivation"] == "debt issuance 5.00 less repayment 0"
    assert "explicit zeros" in SF["equity_issuance_plus_repurchases_ltm"]["source"]
    assert SF["equity_issuance_plus_repurchases_ltm"]["amount"] == "0"
    return cp2d.Operands(
        opening_cash=_d(SF["opening_cash_2024_12_31"]["amount"]),
        cfo=_d(SF["operating_cash_flow_ltm"]["amount"]),
        investing=_d(SF["net_cash_used_in_investing_ltm"]["amount"]),
        net_debt_issuance=_d(SF["net_debt_issuance_ltm"]["amount"]),
        equity_issuance=Decimal(0),
        equity_repurchases=Decimal(0),
        dividends_paid=_d(SF["dividends_paid_ltm"]["amount"]),
        other_investing_financing=_d(SF["other_investing_financing_ltm"]["amount"]),
        financing=_d(SF["net_cash_used_in_financing_ltm"]["amount"]),
        fx_effect=_d(SF["fx_effect_ltm"]["amount"]),
        closing_cash=_d(SF["closing_cash_2025_12_31"]["amount"]),
        cash_bs=_d(SF["closing_cash_2025_12_31"]["amount"]),
        restricted_cash=_d(SF["restricted_cash"]["amount"]),
        rcf_commitment=_d(SF["rcf_commitment"]["amount"]),
        rcf_drawn=_d(SF["rcf_drawn"]["amount"]),
        total_debt_bs=_d(SF["total_debt"]["amount"]),
        cash_closing=_d(SF["closing_cash_2025_12_31"]["amount"]),
        total_debt=_d(SF["total_debt"]["amount"]),
        undrawn_rcf=_cp1_cell_amount("undrawn_rcf"),
        liquidity=_cp1_cell_amount("liquidity"),
        liquidity_to_debt=_cp1_cell_amount("liquidity_to_debt"),
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
            ),
        ),
    )


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
        return replace(base, cfo=Decimal("13.00"))
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


def _assert_cell(got: cp2d.Cell, want: dict[str, Any]) -> None:
    where = want["fact_id"]
    assert got.fact_id == want["fact_id"]
    assert got.state == want["state"], where
    assert got.value_class == want.get("value_class"), where
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
                _assert_cell(got_cell, want_cell)


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
    operands = replace(
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
    tampered = replace(inputs, operands=replace(inputs.operands, liquidity=Decimal(21)))
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
    issues = cp2d.submission_issues(submission=_submission(entry["payload"]), offered_refs=OFFERED)
    assert issues == (EXPECTED["refusals"][case],)


@pytest.mark.parametrize("case", PACK_CASES)
def test_literal_submissions_are_valid(case: str) -> None:
    submission = _submission(SUBMISSIONS["cp2d"][case])
    assert cp2d.submission_issues(submission=submission, offered_refs=OFFERED) == ()


@pytest.mark.parametrize("attempt", ["attempt_0", "attempt_1"])
def test_blocked_attempts_produce_oracle_issues(attempt: str) -> None:
    submission = _submission(SUBMISSIONS["cp2d_blocked"][attempt])
    want = EXPECTED["negative_cases"]["blocked_cp2d"][attempt]["issues"]
    assert list(cp2d.submission_issues(submission=submission, offered_refs=OFFERED)) == want


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
    issues = cp2d.submission_issues(submission=_submission(payload), offered_refs=OFFERED)
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
        assert value.reason == "Not calculable: T4.18 facility schedule is missing", key
    assert b.wall == ()
    result = cp2d.compute(replace(_inputs("positive"), operands=operands))
    assert _cells(result)["T2E.3.r07"].state == "gap"


@pytest.mark.parametrize("total_debt", [None, Decimal(0)])
def test_missing_total_debt_keeps_wall_terms_known(total_debt: Decimal | None) -> None:
    b = _compose(replace(_base_operands(), total_debt_bs=total_debt), 24, "10")
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
    loan = _base_operands().facilities[0]
    operands = replace(
        _base_operands(), facilities=(replace(loan, annual_amortisation=Decimal(6)),)
    )
    b = _compose(operands, 24, "10")
    assert b.amortisation_in_horizon == Decimal(12)  # 6 x 24 / 12
    assert b.maturities_in_horizon == 0
    assert b.cash_at_horizon_end_before_refinancing == Decimal(8)  # 20 + 0 - 12 - 0


def test_amortisation_capped_at_principal() -> None:
    # lease-literal: CP2D lease Method 3 (min(30 x 24 / 12 = 60, principal 50) = 50)
    loan = _base_operands().facilities[0]
    operands = replace(
        _base_operands(), facilities=(replace(loan, annual_amortisation=Decimal(30)),)
    )
    b = _compose(operands, 24, "10")
    assert b.amortisation_in_horizon == Decimal(50)
    assert b.cash_at_horizon_end_before_refinancing == Decimal(-30)


def test_runway_months_round_half_up_and_count_the_revolver() -> None:
    # lease-literal: CP2D lease Method 3. F = -29 - 10 - 4 - 5 = -48; undrawn = 71 - 0 = 71;
    # start = 20 + 71 - 10 = 81; months = 81 / (48 / 12) = 20.25 -> 20.3 (1 dp half-up)
    operands = replace(_base_operands(), cfo=Decimal(-29), rcf_commitment=Decimal(71))
    b = _compose(operands, 24, "10")
    assert b.run_rate_net_cash_flow_annual == Decimal(-48)
    assert b.undrawn_revolver == Decimal(71)
    assert b.available_liquidity == Decimal(91)
    assert b.runway_state == "months"
    assert str(b.months_to_minimum_cash) == "20.3"


def test_runway_negative_start_with_burn_is_zero_months() -> None:
    # lease-literal: CP2D lease Method 3. F = -6 < 0; start = 20 + 0 - 30 = -10;
    # max(0, start) / (6 / 12) = 0.0
    b = _compose(replace(_base_operands(), cfo=Decimal(13)), 24, "30")
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
    operands = replace(_operands("fixture_rcf_undisclosed"), cfo=Decimal(13))
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
    loan = _base_operands().facilities[0]
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
    operands = replace(_base_operands(), rcf_commitment=Decimal(30), rcf_drawn=Decimal(10))
    b = _compose(operands, 24, "10")
    assert b.undrawn_revolver == Decimal(20)
    assert b.available_liquidity == Decimal(40)
    assert b.resources_at_horizon_end == Decimal(40)
    assert b.headroom == Decimal(30)
    assert b.funding_gap == 0


def test_undrawn_term_commitment_is_commitment_less_drawn() -> None:
    # lease-literal: CP2D lease Method 2 (T4.18 commitment - drawn = 60 - 50 = 10, not counted)
    loan = _base_operands().facilities[0]
    operands = replace(_base_operands(), facilities=(replace(loan, commitment=Decimal(60)),))
    b = _compose(operands, 24, "10")
    assert b.undrawn_term_commitment == Decimal(10)
    assert b.available_liquidity == Decimal(20)


# --- rulings round 2 and 3 (docs/rulings/2026-10-28-stage1.md, CP-2D) -------------------------


def _analyst_issues(extra: str) -> tuple[str, ...]:
    payload = json.loads(json.dumps(SUBMISSIONS["cp2d"]["positive"]))
    payload["assessments"][0]["text"] += " " + extra
    return cp2d.submission_issues(submission=_submission(payload), offered_refs=OFFERED)


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
    issues = cp2d.submission_issues(submission=_submission(payload), offered_refs=OFFERED)
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


LOAN = _base_operands().facilities[0]


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
        "needs facility term-loan in USD; no FX conversion is applied."
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
    operands = replace(
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
    operands = replace(inputs.operands, dividends_paid=Decimal(-8))  # lines sum to (3), total (4)
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
        ("cash_closing differs", replace(o, cash_closing=Decimal(21))),
        ("facility commitment None", replace(o, facilities=(replace(LOAN, commitment=None),))),
        ("total debt zero", replace(o, total_debt_bs=Decimal(0), total_debt=Decimal(0))),
        ("EUR facility", replace(o, facilities=(replace(LOAN, currency="EUR"),))),
        (
            "negative total debt",
            replace(o, total_debt_bs=Decimal(-50), total_debt=Decimal(-50), liquidity_to_debt=None),
        ),
        ("tiny burn", replace(o, cfo=Decimal(19) - Decimal("1E-60"))),
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
