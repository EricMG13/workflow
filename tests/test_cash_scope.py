"""A declared cash scope: NCF_CASH_MOVEMENT sums the change in each declared scope balance.

The books carry the CZR filing numbers (10-K FY2025, 10-Q Q2 2026). A missing scope balance is an
absent input, never zero; a book without a declaration is byte-identical to the old contract.
"""

import hashlib
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from deploy_vii.cash_bridge import cash_bridge_issues
from deploy_vii.contracts import Citation
from deploy_vii.financial_contracts import (
    CashMovementBridge,
    Disclosure,
    FinancialBook,
    FinancialPeriod,
    Observation,
    StatementLine,
)
from deploy_vii.financial_periods import HistoricalReport, PeriodConstruction, PeriodReference
from deploy_vii.financial_reconciliation import _cash_movement
from deploy_vii.period_reconciliation import PeriodTerm, _period_cash

SHA = "a" * 64
BOTH = ("restricted_cash", "restricted_cash_noncurrent")
D = Decimal
# date -> (cash and equivalents, restricted cash, restricted and escrow cash in other LT assets)
BALANCES = {
    date(2024, 12, 31): (866, 95, 55),
    date(2025, 6, 30): (982, 85, 19),
    date(2025, 12, 31): (887, 85, 12),
    date(2026, 6, 30): (965, 96, 16),
}
BS_QUOTES = {
    "cash_and_equivalents": "Cash and cash equivalents",
    "restricted_cash": "Restricted cash",
    "restricted_cash_noncurrent": "Restricted and escrow cash included in other long-term assets",
}
FLOWS = {  # period -> (type, quarter, fiscal year, start, end, reported NCF)
    "fy-2025": ("FY", None, "FY2025", date(2025, 1, 1), date(2025, 12, 31), -32),
    "h1-2026": ("YTD", 2, "FY2026", date(2026, 1, 1), date(2026, 6, 30), 93),
    "h1-2025": ("YTD", 2, "FY2025", date(2025, 1, 1), date(2025, 6, 30), 70),
}
NCF_QUOTE = {
    "fy-2025": "Decrease in cash, cash equivalents and restricted cash | (32) | (127) | (160)",
    "h1-2026": "Increase in cash, cash equivalents and restricted cash | 93 | 70",
    "h1-2025": "Increase in cash, cash equivalents and restricted cash | 70 | 12",
}
SCOPE_FORMULA = (
    "closing cash scope - opening cash scope "
    "(cash_and_equivalents + restricted_cash + restricted_cash_noncurrent) "
    "- signed source adjustments"
)


def cite(quote: str, locator: str = "page:60") -> Citation:
    return Citation(source_id="k", source_sha256=SHA, locator=locator, quote=quote)


def observation(name: str, amount: int, citation: Citation) -> Observation:
    return Observation(
        observation_id=name, status="known", amount=D(amount), citations=(citation,)
    )


def period(pid: str, kind: str, quarter, year: str, start, end) -> FinancialPeriod:
    return FinancialPeriod(
        period_id=pid,
        fiscal_year=year,
        fiscal_quarter=quarter,
        period_type=kind,
        start_date=start,
        end_date=end,
        day_count=None,
        audit_status="unaudited",
        currency="USD",
        unit="MILLIONS",
        accounting_basis="US GAAP",
        entity_perimeter="Consolidated",
        citations=(cite("period", "page:1"),),
    )


def line(lid, statement, item, pid, amount, citation, *, kind="detail", priority=1):
    return StatementLine(
        line_id=lid,
        statement=statement,
        item_id=item,
        label=item,
        period_id=pid,
        display_priority=priority,
        line_kind=kind,
        value=observation(f"obs-{lid}", amount, citation),
    )


def scope_of(items=BOTH, citations=None):
    from deploy_vii.financial_contracts import CashScope

    return CashScope(items=items, citations=citations or ())


def bridge(pid: str, items=BOTH, citations=None) -> CashMovementBridge:
    quote = cite(NCF_QUOTE[pid])
    extra = {"cash_scope": scope_of(items, citations or (quote,))} if items else {}
    return CashMovementBridge(
        bridge_id=f"b-{pid}",
        period_id=pid,
        components=(),
        explanation="no FX or perimeter adjustment is printed",
        citations=(quote,),
        **extra,
    )


def book(
    flows=("fy-2025", "h1-2026"),
    scopes=None,
    *,
    drop=(),
    extra_lines=(),
    declare=True,
    ncf_citations=None,
) -> FinancialBook:
    """`scopes` maps a bridged period to its declared items (None: bridge without scope)."""
    scopes = scopes if scopes is not None else {pid: BOTH if declare else None for pid in flows}
    periods, lines, order = [], [], 1
    for day, values in BALANCES.items():
        pid = f"bs-{day.isoformat()}"
        periods.append(period(pid, "PERIOD_END", None, f"FY{day.year}", None, day))
        for item, amount in zip(BS_QUOTES, values, strict=True):
            if (day, item) in drop:
                continue
            quote = f"{BS_QUOTES[item]} | {amount}"
            lines.append(line(f"{pid}-{item}", "BS", item, pid, amount, cite(quote, "page:61"),
                              priority=order))
            order += 1
    for pid in flows:
        kind, quarter, year, start, end, ncf = FLOWS[pid]
        periods.append(period(pid, kind, quarter, year, start, end))
        citation = (ncf_citations or {}).get(pid) or cite(NCF_QUOTE[pid])
        lines.append(line(f"cfs-ncf-{pid}", "CFS", "net_cash_change", pid, ncf, citation,
                          kind="total", priority=order))
        order += 1
    disclosure = Disclosure(
        status="not_applicable", explanation="none", citations=(cite("none", "page:1"),)
    )
    return FinancialBook(
        book_id="czr",
        entity_perimeter="Consolidated",
        accounting_basis="US GAAP",
        currency="USD",
        unit="MILLIONS",
        periods=tuple(periods),
        accounts=(),
        addbacks=(),
        segments=(),
        kpis=(),
        facilities=(),
        pro_forma=(),
        statement_lines=(*lines, *extra_lines),
        cash_movement_bridges=tuple(bridge(pid, items) for pid, items in scopes.items()),
        segment_allocation=(),
        addback_disclosure=disclosure,
        segment_disclosure=disclosure,
    )


def signed(check) -> list[Decimal]:
    return [t.amount * t.coefficient for t in check.components]


def flow(b: FinancialBook, pid: str) -> FinancialPeriod:
    return next(p for p in b.periods if p.period_id == pid)


def test_declared_fy_2025_sums_the_change_in_each_scope_balance():
    b = book()
    check = _cash_movement(b, flow(b, "fy-2025"))
    assert signed(check) == [887, -866, 85, -95, 12, -55]
    assert check.calculated_value == D(-32)
    assert check.difference == D(0)
    assert check.status == "PASS"
    assert check.formula == SCOPE_FORMULA
    assert check.cash_movement_bridges == (b.cash_movement_bridges[0],)


def test_declared_h1_2026_sums_the_change_in_each_scope_balance():
    b = book()
    check = _cash_movement(b, flow(b, "h1-2026"))
    assert signed(check) == [965, -887, 96, -85, 16, -12]
    assert check.calculated_value == D(93)
    assert check.difference == D(0)
    assert check.status == "PASS"
    assert check.formula == SCOPE_FORMULA


def test_restricted_cash_only_scope_passes_without_a_noncurrent_balance():
    b = book(flows=("fy-2025",), scopes={"fy-2025": ("restricted_cash",)})
    check = _cash_movement(b, flow(b, "fy-2025"))
    assert signed(check) == [887, -866, 85, -95]
    assert check.calculated_value == D(11)
    assert check.formula == (
        "closing cash scope - opening cash scope (cash_and_equivalents + restricted_cash) "
        "- signed source adjustments"
    )


@pytest.mark.parametrize(
    ("pid", "calculated", "difference"), [("fy-2025", 21, 53), ("h1-2026", 78, -15)]
)
def test_undeclared_scope_keeps_the_cash_only_check(pid, calculated, difference):
    b = book(declare=False)
    bridge_ = b.cash_movement_bridges[0 if pid == "fy-2025" else 1]
    assert bridge_.cash_scope is None
    assert "cash_scope" not in bridge_.model_dump_json()
    check = _cash_movement(b, flow(b, pid))
    assert [t.label for t in check.components] == ["cash_and_equivalents"] * 2
    assert check.calculated_value == D(calculated)
    assert check.difference == D(difference)
    assert check.status == "BLOCK"
    assert check.formula == "closing cash - opening cash - signed source adjustments"


def test_undeclared_scope_without_a_bridge_keeps_the_old_formula():
    b = book(scopes={})
    check = _cash_movement(b, flow(b, "fy-2025"))
    assert check.formula == "closing cash - opening cash; no inferred FX or other cash adjustment"
    assert [t.label for t in check.components] == ["cash_and_equivalents"] * 2


def test_a_missing_scope_balance_is_an_absent_input_never_zero():
    b = book(drop={(date(2024, 12, 31), "restricted_cash_noncurrent")})
    check = _cash_movement(b, flow(b, "fy-2025"))
    missing = check.components[5]
    assert (missing.label, missing.amount, missing.reason) == (
        "restricted_cash_noncurrent",
        None,
        "Not supplied",
    )
    assert check.calculated_value is None
    assert check.difference is None
    assert check.status == "BLOCK"
    assert check.explanation == "Missing reported value or complete independent components"


def test_a_not_applicable_scope_balance_carries_its_reason():
    day = date(2024, 12, 31)
    absent = Observation(
        observation_id="obs-na",
        status="not_applicable",
        amount=None,
        citations=(),
        reason="No such balance at that date",
    )
    na = StatementLine(
        line_id="bs-na",
        statement="BS",
        item_id="restricted_cash_noncurrent",
        label="restricted_cash_noncurrent",
        period_id="bs-2024-12-31",
        display_priority=99,
        line_kind="detail",
        value=absent,
    )
    b = book(drop={(day, "restricted_cash_noncurrent")}, extra_lines=(na,))
    check = _cash_movement(b, flow(b, "fy-2025"))
    assert check.components[5].amount is None
    assert check.components[5].reason == "No such balance at that date"
    assert check.calculated_value is None
    assert check.status == "BLOCK"


def test_cash_scope_contract_refuses_a_quote_that_does_not_name_restricted_cash():
    with pytest.raises(ValidationError, match="names restricted cash"):
        scope_of(BOTH, (cite("Total cash and cash equivalents | 887"),))


def test_cash_scope_contract_accepts_the_quote_across_whitespace_and_case():
    scope = scope_of(("restricted_cash",), (cite("Increase in cash and Restricted\n  CASH | 93"),))
    assert scope.items == ("restricted_cash",)


def test_cash_scope_contract_refuses_duplicate_items():
    with pytest.raises(ValidationError, match="distinct"):
        scope_of(("restricted_cash", "restricted_cash"), (cite(NCF_QUOTE["fy-2025"]),))


def test_scope_citation_must_cite_the_period_cfs_cash_line():
    other = cite("Net cash used in operating activities, excluding restricted cash | 1")
    b = book(
        flows=("fy-2025",),
        extra_lines=(line("cfs-cfo", "CFS", "cfo_ncfo", "fy-2025", 1, other, kind="total"),),
    )
    assert cash_bridge_issues(b) == ()
    off = b.model_copy(
        update={"cash_movement_bridges": (bridge("fy-2025", BOTH, (other,)),)}
    )
    assert cash_bridge_issues(off) == (
        "Cash scope citation must cite the period's CFS cash line: b-fy-2025",
    )


def test_declared_item_without_a_balance_where_cash_is_stated_is_refused():
    b = book(flows=("fy-2025",), drop={(date(2024, 12, 31), "restricted_cash_noncurrent")})
    assert cash_bridge_issues(b) == (
        "Declared cash scope balance missing: b-fy-2025 restricted_cash_noncurrent 2024-12-31",
    )


def test_a_book_without_any_declaration_serializes_as_before():
    expected = (
        '{"bridge_id":"b-fy-2025","period_id":"fy-2025","components":[],'
        '"explanation":"no FX or perimeter adjustment is printed","citations":[{"source_id":"k",'
        f'"source_sha256":"{SHA}","locator":"page:60","quote":"{NCF_QUOTE["fy-2025"]}"}}]}}'
    )
    b = book(declare=False)
    assert b.cash_movement_bridges[0].model_dump_json() == expected
    assert b.cash_movement_bridges[0].content_hash() == hashlib.sha256(expected.encode()).hexdigest()
    rec = _cash_movement(b, flow(b, "fy-2025"))
    assert f'"cash_movement_bridges":[{expected}]' in rec.model_dump_json()


def historical(b: FinancialBook, node: PeriodConstruction) -> HistoricalReport:
    return HistoricalReport(
        run_id="r",
        issuer_id="czr",
        as_of=date(2026, 6, 30),
        pack_sha256=SHA,
        review_sha256=SHA,
        book_id=b.book_id,
        entity_perimeter=b.entity_perimeter,
        accounting_basis=b.accounting_basis,
        currency=b.currency,
        scale="MILLIONS",
        periods=b.periods,
        observations=(),
        facility_normalizations=(),
        input_rows=(),
        columns=(),
        constructions=(node,),
        values=(),
        limitations=(),
    )


def ltm_node() -> PeriodConstruction:
    terms = (("fy-2025", 1), ("h1-2026", 1), ("h1-2025", -1))
    return PeriodConstruction(
        construction_id="ltm-2026-06-30",
        column_key="ltm",
        label="LTM",
        kind="LTM",
        fiscal_year="FY2026",
        fiscal_quarter=2,
        start_date=date(2025, 7, 1),
        end_date=date(2026, 6, 30),
        days=365,
        own_period_id=None,
        stated_period_id=None,
        terms=tuple(PeriodReference(kind="period", reference=r, coefficient=c) for r, c in terms),
        formula="fy-2025 + h1-2026 - h1-2025",
        limitation=None,
    )


def term(label: str, amount: int) -> PeriodTerm:
    return PeriodTerm(
        label=label,
        value_id=None,
        amount=D(amount),
        observation_ids=(),
        citations=(),
        reason=None,
    )


def constructed(b: FinancialBook):
    node = ltm_node()
    return _period_cash(
        b, historical(b, node), node, term("net_cash_change", -9), term("cash_and_equivalents", 965)
    )


def test_constructed_period_sums_scope_balances_at_the_construction_boundaries():
    b = book(flows=tuple(FLOWS), scopes={pid: BOTH for pid in FLOWS})
    check = constructed(b)
    assert [t.amount * t.coefficient for t in check.components] == [965, -982, 96, -85, 16, -19]
    assert check.calculated_value == D(-9)
    assert check.difference == D(0)
    assert check.status == "PASS"
    assert check.formula == (
        "closing cash scope - opening cash scope "
        "(cash_and_equivalents + restricted_cash + restricted_cash_noncurrent) "
        "- signed period combination of source adjustments"
    )
    assert [br.bridge_id for br in check.cash_movement_bridges] == [
        "b-fy-2025",
        "b-h1-2026",
        "b-h1-2025",
    ]


def test_constructed_period_refuses_sources_with_different_scopes():
    scopes = {"fy-2025": BOTH, "h1-2026": BOTH, "h1-2025": None}
    check = constructed(book(flows=tuple(FLOWS), scopes=scopes))
    assert check.status == "BLOCK"
    assert check.calculated_value is None
    assert "Cash scope differs across source periods: h1-2025" in check.explanation


def test_constructed_period_without_any_scope_keeps_the_adjusted_formula_and_bytes():
    b = book(flows=tuple(FLOWS), scopes={pid: None for pid in FLOWS})
    check = constructed(b)
    assert [t.label for t in check.components[:2]] == ["cash_and_equivalents"] * 2
    assert check.formula == (
        "closing cash - opening cash - signed period combination of source adjustments"
    )
    assert '"cash_scope"' not in check.model_dump_json()
