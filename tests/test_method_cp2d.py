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
        operands=_operands(case), balance_date=BALANCE_DATE, submission=submission
    )


def _num_equal(got: Decimal | None, want: str | None) -> bool:
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
        assert getattr(bridge, key) is None, (case, key)


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


def test_undisclosed_revolver_tables_fail_closed() -> None:
    """No claim or gap wording is pinned for an undisclosed revolver: compute refuses to compose."""
    case = "fixture_rcf_undisclosed"
    payload = json.loads(json.dumps(SUBMISSIONS["cp2d"]["positive"]))
    inputs = cp2d.Cp2dInputs(
        operands=_operands(case), balance_date=BALANCE_DATE, submission=_submission(payload)
    )
    with pytest.raises(ValueError, match="rcf_commitment"):
        cp2d.compute(inputs)


def test_compute_refuses_an_invalid_submission() -> None:
    inputs = _inputs("positive")
    payload = SUBMISSIONS["refusal_inputs"]["section_missing"]["payload"]
    with pytest.raises(ValueError, match=EXPECTED["refusals"]["section_missing"]):
        cp2d.compute(replace(inputs, submission=_submission(payload)))


def test_cp1_cross_check_mismatch_fails_closed() -> None:
    inputs = _inputs("positive")
    tampered = replace(inputs, operands=replace(inputs.operands, liquidity=Decimal(21)))
    assert cp2d.check_cp1_totals(operands=tampered.operands, bridge=cp2d.bridge_of(tampered))
    with pytest.raises(ValueError, match="liquidity"):
        cp2d.compute(tampered)
    assert cp2d.check_cp1_totals(operands=inputs.operands, bridge=cp2d.bridge_of(inputs)) == ()


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
