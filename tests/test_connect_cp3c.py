"""CP-3C Stage 2: the connection of the Stage 1 core to the store, the registrations, the
bindings, the reader and the fast consumption proof (`docs/CP3C-OWNER-LEASE.md`,
`docs/G1X-OWNER-CORE-PROTOCOL.md`, `work/build/stage2/brief.md`).

Expectations come from the lease, `cases/cp3c-owner/{manifest,submissions,expected}.json` and the
pinned CP-2D oracle, never from the code under test. The stores here are real `Execution` stores
whose CP-0, CP-1, CP-1A and CP-2 heads are settled through `begin`/`finish` from records built
for the CP-2D and CP-3C bindings, and whose CP-2D head is settled by the real CP-2D core, so no
CP-1 promotion runs: the genuine runs are `tests/test_owner_cp3c.py` and `tests/cp3c_runs.py`
(deferred). The fixtures vary the CP-1 amounts and statuses, the CP-2D case (minimum cash
assessed or not, horizon), the as-of date and the case kind, so a constant equal to the oracle
cannot pass.

First section: the backlog rows (work/build/stage2-backlog.md, CP-3C Infos 1-3 as ruled in
docs/rulings/2026-10-28-stage2.md round 5 item 7, and the caller-quoting f-string sites of the
0d-c audit), each written before its code and watched red.
"""

import re
from dataclasses import replace
from decimal import Decimal
from typing import Any

import pytest
import test_method_cp3c as tm

from deploy_vii.execution import MAX_ISSUE_CHARS
from deploy_workflow.owners import cp3c

MODULE = "CP-3C"
STEP = "refinancing_risk"
UNSOURCED = (
    "CP-3C: the reporting currency is not sourced: cash_closing is not known and no known "
    "US$ m fact states a currency"
)


# --- backlog Info 1: the unsourced reporting currency is an invariant raise ----------------------


def _missing(fact: Any) -> Any:
    return replace(fact, status="missing", amount=None, text=None, reason="Not stated")


def _without_cash(inputs: cp3c.Cp3cInputs) -> cp3c.Cp3cInputs:
    return replace(inputs, cp1=replace(inputs.cp1, cash_closing=_missing(inputs.cp1.cash_closing)))


def _every_millions_fact(inputs: cp3c.Cp3cInputs, change: Any) -> cp3c.Cp3cInputs:
    """`change` applied to every US$ m fact CP-3C reads besides cash_closing."""
    cp1, cp2d = inputs.cp1, inputs.cp2d
    terms = tuple(
        replace(t, annual_amortisation=change(t.annual_amortisation)) for t in cp1.facilities
    )
    cp1 = replace(
        cp1,
        undrawn_rcf=change(cp1.undrawn_rcf),
        adjusted_ebitda=change(cp1.adjusted_ebitda),
        cash_interest=change(cp1.cash_interest),
        facilities=terms,
    )
    wall = tuple(replace(r, principal=change(r.principal)) for r in cp2d.wall)
    cp2d = replace(
        cp2d,
        run_rate=change(cp2d.run_rate),
        minimum_cash=change(cp2d.minimum_cash),
        funding_gap=change(cp2d.funding_gap),
        wall=wall,
    )
    return replace(inputs, cp1=cp1, cp2d=cp2d)


@pytest.mark.parametrize("blank", ["", " ", None])
def test_info1_cash_missing_and_every_other_currency_blank_is_unsourced(blank: str | None) -> None:
    inputs = _every_millions_fact(
        _without_cash(tm._inputs("positive")), lambda f: replace(f, currency=blank)
    )
    with pytest.raises(ValueError, match=f"^{re.escape(UNSOURCED)}$"):
        cp3c.compute(replace(inputs, currency=blank or ""))
    with pytest.raises(ValueError, match=f"^{re.escape(UNSOURCED)}$"):
        cp3c.reporting_currency(cp1=inputs.cp1, cp2d=inputs.cp2d)


def test_info1_cash_missing_and_no_other_known_millions_fact_is_unsourced() -> None:
    inputs = _every_millions_fact(_without_cash(tm._inputs("positive")), _missing)
    for currency in ("USD", "EUR"):
        with pytest.raises(ValueError, match=f"^{re.escape(UNSOURCED)}$"):
            cp3c.check_currency(cp1=inputs.cp1, cp2d=inputs.cp2d, currency=currency)
    with pytest.raises(ValueError, match=f"^{re.escape(UNSOURCED)}$"):
        cp3c.reporting_currency(cp1=inputs.cp1, cp2d=inputs.cp2d)


def test_info1_cash_missing_takes_the_currency_the_known_facts_state() -> None:
    inputs = _without_cash(tm._inputs("positive"))
    assert cp3c.reporting_currency(cp1=inputs.cp1, cp2d=inputs.cp2d) == "USD"
    euro = _every_millions_fact(inputs, lambda f: replace(f, currency="EUR"))
    assert cp3c.reporting_currency(cp1=euro.cp1, cp2d=euro.cp2d) == "EUR"
    cp3c.check_currency(cp1=euro.cp1, cp2d=euro.cp2d, currency="EUR")  # sourced: no raise
    # One known US$ m fact is enough to source it; the rest may be gaps.
    one = _every_millions_fact(inputs, _missing)
    one = replace(one, cp2d=replace(one.cp2d, run_rate=inputs.cp2d.run_rate))
    assert cp3c.reporting_currency(cp1=one.cp1, cp2d=one.cp2d) == "USD"


def test_info1_the_reporting_currency_is_cash_closings_when_it_is_known() -> None:
    inputs = tm._inputs("positive")
    cash = replace(inputs.cp1.cash_closing, currency="GBP")
    cp1 = replace(inputs.cp1, cash_closing=cash)
    assert cp3c.reporting_currency(cp1=cp1, cp2d=inputs.cp2d) == "GBP"
    for unset in (None, "", " "):
        cp1 = replace(inputs.cp1, cash_closing=replace(cash, currency=unset))
        with pytest.raises(ValueError, match=r"^CP-3C cash_closing: currency is not set$"):
            cp3c.reporting_currency(cp1=cp1, cp2d=inputs.cp2d)


# --- backlog Info 2: a conflicting status takes the conflicting frame ---------------------------

_UNSETTLED = ("conflicting", "not_applicable")
_WORD = {"conflicting": "conflicting", "not_applicable": "not applicable"}


def _unsettled(fact: Any, status: str) -> Any:
    return replace(fact, status=status, amount=None, text=None, reason="CP-1 says so")


def _cells(result: cp3c.Cp3cResult) -> dict[str, cp3c.Cell]:
    return {c.fact_id: c for t in result.tables for r in t.rows for c in r.cells}


@pytest.mark.parametrize("status", _UNSETTLED)
def test_info2_minimum_cash_dependants_name_its_status(status: str) -> None:
    inputs = tm._inputs("positive")
    cp2d = replace(inputs.cp2d, minimum_cash=_unsettled(inputs.cp2d.minimum_cash, status))
    result = cp3c.compute(replace(inputs, cp2d=cp2d))
    reason = f"Not calculable: minimum cash is {_WORD[status]}"
    cells = _cells(result)
    for fact_id in ("T3D.1.r01.c7", "T3D.1.r01.c9", "T3D.2.r02", "T3D.2.r03", "T3D.2.r09"):
        assert (cells[fact_id].status, cells[fact_id].reason) == ("missing", reason), fact_id
    (need,) = (c for c in result.claims if c.claim_id == "CP-3C-NEED-01")
    assert f"because minimum cash is {_WORD[status]}." in need.template


def test_info2_a_missing_minimum_cash_keeps_the_oracle_reason() -> None:
    result = cp3c.compute(tm._inputs("gap_minimum_cash"))
    assert _cells(result)["T3D.2.r03"].reason == "Not calculable: minimum cash not assessed"


_TERMS = [
    ("cp1", "seniority", "seniority", "T3D.4.r01.c5"),
    ("cp1", "secured_status", "secured status", "T3D.4.r01.c5"),
    ("cp1", "annual_amortisation", "annual amortisation", "T3D.1.r01.c6"),
    ("cp2d", "principal", "principal", "T3D.1.r01.c6"),
    ("cp2d", "maturity_date", "maturity date", "T3D.2.r05"),
]


def _with_term(inputs: cp3c.Cp3cInputs, side: str, name: str, status: str) -> cp3c.Cp3cInputs:
    if side == "cp1":
        (terms,) = inputs.cp1.facilities
        terms = replace(terms, **{name: _unsettled(getattr(terms, name), status)})
        return replace(inputs, cp1=replace(inputs.cp1, facilities=(terms,)))
    (row,) = inputs.cp2d.wall
    fact = replace(_unsettled(getattr(row, name), status), period=None)
    return replace(inputs, cp2d=replace(inputs.cp2d, wall=(replace(row, **{name: fact}),)))


@pytest.mark.parametrize("status", _UNSETTLED)
@pytest.mark.parametrize(("side", "name", "term", "fact_id"), _TERMS)
def test_info2_facility_term_dependants_name_its_status(
    side: str, name: str, term: str, fact_id: str, status: str
) -> None:
    result = cp3c.compute(_with_term(tm._inputs("positive"), side, name, status))
    cell = _cells(result)[fact_id]
    assert cell.reason == f"Not calculable: facility term-loan {term} is {_WORD[status]}"


@pytest.mark.parametrize(("side", "name", "term", "fact_id"), _TERMS)
def test_info2_a_missing_facility_term_stays_not_stated(
    side: str, name: str, term: str, fact_id: str
) -> None:
    result = cp3c.compute(_with_term(tm._inputs("positive"), side, name, "missing"))
    assert (
        _cells(result)[fact_id].reason == f"Not calculable: facility term-loan {term} is not stated"
    )


def test_info2_a_not_stated_flag_stays_not_stated() -> None:
    inputs = tm._inputs("positive")
    (terms,) = inputs.cp1.facilities
    terms = replace(terms, seniority=replace(terms.seniority, text="NOT_STATED"))
    result = cp3c.compute(replace(inputs, cp1=replace(inputs.cp1, facilities=(terms,))))
    reason = "Not calculable: facility term-loan seniority is not stated"
    assert _cells(result)["T3D.4.r01.c5"].reason == reason


# --- backlog Info 3: the `_check_value` frame is CP-3C's ----------------------------------------


def test_info3_check_value_messages_are_in_the_cp3c_frame() -> None:
    with pytest.raises(ValueError, match=r"^CP-3C T4\.10: a known fact carries exactly one "):
        cp3c.Cp1Fact(table_id="T4.10", period="p", status="known")
    with pytest.raises(ValueError, match=r"^CP-3C T2E\.3\.r01: a missing fact carries a reason "):
        cp3c.Cp2dFact(fact_id="T2E.3.r01", status="missing", amount=Decimal(1), reason="r")
    with pytest.raises(ValueError, match=r"^CP-3C T4\.18: a known fact carries no reason$"):
        cp3c.Cp1Fact(table_id="T4.18", period="p", status="known", text="x", reason="r")


# --- backlog: caller-quoting lines are clipped (protocol section 6; 0d-c audit cp3c sites) ------

LONG = "X" * 5000


def test_an_unknown_ranking_flag_is_clipped() -> None:
    inputs = tm._inputs("positive")
    (terms,) = inputs.cp1.facilities
    terms = replace(terms, seniority=replace(terms.seniority, text=LONG))
    with pytest.raises(ValueError) as raised:
        cp3c.compute(replace(inputs, cp1=replace(inputs.cp1, facilities=(terms,))))
    message = str(raised.value)
    assert message.startswith("CP-3C term-loan: unknown ranking flag 'XXX")
    assert len(message) <= MAX_ISSUE_CHARS


def test_an_inside_horizon_flag_is_clipped() -> None:
    (row,) = tm._inputs("positive").cp2d.wall
    flag = replace(row.inside_horizon, text=LONG)
    with pytest.raises(ValueError) as raised:
        cp3c._flag(flag)
    message = str(raised.value)
    assert message.startswith("CP-3C T2E.4.r01.c4: inside-horizon flag 'XXX")
    assert len(message) <= MAX_ISSUE_CHARS


def test_claim_figure_and_chip_refusals_are_clipped() -> None:
    cells = tm._cells_of(cp3c.compute(tm._inputs("positive")))
    known, gap = cells["T3D.2.r01"], cells["T3D.5.r01.c2"]
    long_id = "T3D.2." + "r" * 3000
    claims = cp3c._Claims({long_id: known, "gap" + long_id: gap})
    with pytest.raises(ValueError) as chip:
        claims.chip(long_id)
    with pytest.raises(ValueError) as fig:
        claims.fig("gap" + long_id)
    for raised in (chip, fig):
        assert str(raised.value).startswith("CP-3C claim")
        assert len(str(raised.value)) <= MAX_ISSUE_CHARS


def test_an_invalid_submission_raise_is_bounded() -> None:
    payload = tm._bind(tm.SUBMISSIONS["cp3c"]["positive"])
    payload["paths"] = [
        {**path, "text": path["text"] + " 1"} for path in payload["paths"] * 30
    ]  # 150 rows, each with a figure: many issues
    inputs = replace(tm._inputs("positive"), submission=tm._submission(payload))
    with pytest.raises(ValueError) as raised:
        cp3c.compute(inputs)
    assert str(raised.value).count("; ") <= 21 and "further issues not listed" in str(raised.value)
