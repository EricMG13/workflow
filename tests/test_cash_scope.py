"""A declared cash scope: NCF_CASH_MOVEMENT sums the change in each declared scope balance.

The books carry the CZR filing numbers (10-K FY2025, 10-Q Q2 2026). A missing scope balance is an
absent input, never zero; a book without a declaration is byte-identical to the old contract.
"""

import hashlib
from collections.abc import Collection, Mapping
from datetime import date
from decimal import Decimal
from typing import Literal, NamedTuple

import pytest
from pydantic import ValidationError

from deploy_vii.cash_bridge import cash_bridge_issues
from deploy_vii.contracts import Citation
from deploy_vii.financial_contracts import (
    AccountObservation,
    CashMovementBridge,
    CashScope,
    Disclosure,
    FinancialBook,
    FinancialPeriod,
    Observation,
    StatementLine,
)
from deploy_vii.financial_periods import HistoricalReport, PeriodConstruction, PeriodReference
from deploy_vii.financial_reconciliation import Reconciliation, _cash_movement
from deploy_vii.period_reconciliation import PeriodCheck, PeriodTerm, _period_cash

SHA = "a" * 64
Item = Literal["restricted_cash", "restricted_cash_noncurrent"]
PeriodKind = Literal["QUARTER", "YTD", "FY", "LTM", "PERIOD_END"]
Statement = Literal["IS", "CFS", "BS"]
BOTH: tuple[Item, ...] = ("restricted_cash", "restricted_cash_noncurrent")
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


class Flow(NamedTuple):
    kind: PeriodKind
    quarter: int | None
    year: str
    start: date
    end: date
    ncf: int


FLOWS = {
    "fy-2025": Flow("FY", None, "FY2025", date(2025, 1, 1), date(2025, 12, 31), -32),
    "h1-2026": Flow("YTD", 2, "FY2026", date(2026, 1, 1), date(2026, 6, 30), 93),
    "h1-2025": Flow("YTD", 2, "FY2025", date(2025, 1, 1), date(2025, 6, 30), 70),
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
FY_CASH_LINE = "Cash scope citation must cite the period's CFS cash line naming restricted cash: "
NONCURRENT_2024 = (date(2024, 12, 31), "restricted_cash_noncurrent")
MISSING_2024 = (
    "Declared cash scope balance missing: b-fy-2025 restricted_cash_noncurrent 2024-12-31"
)


def cite(quote: str, locator: str = "page:60") -> Citation:
    return Citation(source_id="k", source_sha256=SHA, locator=locator, quote=quote)


def observation(name: str, amount: int, citation: Citation) -> Observation:
    return Observation(observation_id=name, status="known", amount=D(amount), citations=(citation,))


def period(
    pid: str,
    kind: PeriodKind,
    quarter: int | None,
    year: str,
    start: date | None,
    end: date,
) -> FinancialPeriod:
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
        limitation="Point-in-time balance sheet date, not a duration" if start is None else None,
    )


def line(
    lid: str,
    statement: Statement,
    item: str,
    pid: str,
    amount: int,
    citation: Citation,
    *,
    kind: Literal["detail", "subtotal", "total"] = "detail",
    priority: int = 1,
    label: str | None = None,
) -> StatementLine:
    return StatementLine(
        line_id=lid,
        statement=statement,
        item_id=item,
        label=label or item,
        period_id=pid,
        display_priority=priority,
        line_kind=kind,
        value=observation(f"obs-{lid}", amount, citation),
    )


def unsettled(status: Literal["missing", "not_applicable"], pid: str) -> StatementLine:
    """A declared noncurrent row that carries no amount, only its reason."""
    return StatementLine(
        line_id=f"bs-{status}",
        statement="BS",
        item_id="restricted_cash_noncurrent",
        label="restricted_cash_noncurrent",
        period_id=pid,
        display_priority=99,
        line_kind="detail",
        value=Observation(
            observation_id=f"obs-{status}",
            status=status,
            amount=None,
            citations=(),
            reason="No such balance at that date",
        ),
    )


def scope_of(items: tuple[Item, ...] = BOTH, citations: tuple[Citation, ...] = ()) -> CashScope:
    return CashScope(items=items, citations=citations)


def bridge(
    pid: str,
    items: tuple[Item, ...] | None = BOTH,
    citations: tuple[Citation, ...] | None = None,
) -> CashMovementBridge:
    quote = cite(NCF_QUOTE[pid])
    return CashMovementBridge(
        bridge_id=f"b-{pid}",
        period_id=pid,
        components=(),
        explanation="no FX or perimeter adjustment is printed",
        citations=(quote,),
        cash_scope=scope_of(items, citations or (quote,)) if items else None,
    )


def book(
    flows: tuple[str, ...] = ("fy-2025", "h1-2026"),
    scopes: Mapping[str, tuple[Item, ...] | None] | None = None,
    *,
    drop: Collection[tuple[date, str]] = (),
    extra_lines: tuple[StatementLine, ...] = (),
    declare: bool = True,
    ncf_citations: Mapping[str, Citation] | None = None,
    labels: Mapping[tuple[date, str], str] | None = None,
) -> FinancialBook:
    """`scopes` maps a bridged period to its declared items (None: bridge without scope)."""
    if scopes is None:
        scopes = {pid: BOTH if declare else None for pid in flows}
    periods: list[FinancialPeriod] = []
    lines: list[StatementLine] = []
    order = 1
    for day, values in BALANCES.items():
        pid = f"bs-{day.isoformat()}"
        periods.append(period(pid, "PERIOD_END", None, f"FY{day.year}", None, day))
        for item, amount in zip(BS_QUOTES, values, strict=True):
            if (day, item) in drop:
                continue
            quote = cite(f"{BS_QUOTES[item]} | {amount}", "page:61")
            label = (labels or {}).get((day, item))
            lines.append(
                line(f"{pid}-{item}", "BS", item, pid, amount, quote, priority=order, label=label)
            )
            order += 1
    for pid in flows:
        flow_ = FLOWS[pid]
        periods.append(period(pid, flow_.kind, flow_.quarter, flow_.year, flow_.start, flow_.end))
        citation = (ncf_citations or {}).get(pid) or cite(NCF_QUOTE[pid])
        lines.append(
            line(
                f"cfs-ncf-{pid}",
                "CFS",
                "net_cash_change",
                pid,
                flow_.ncf,
                citation,
                kind="total",
                priority=order,
            )
        )
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


def signed(check: Reconciliation | PeriodCheck) -> list[Decimal]:
    return [t.amount * t.coefficient for t in check.components if t.amount is not None]


def flow(b: FinancialBook, pid: str) -> FinancialPeriod:
    return next(p for p in b.periods if p.period_id == pid)


def test_declared_fy_2025_sums_the_change_in_each_scope_balance() -> None:
    b = book()
    check = _cash_movement(b, flow(b, "fy-2025"))
    assert signed(check) == [887, -866, 85, -95, 12, -55]
    assert check.calculated_value == D(-32)
    assert check.difference == D(0)
    assert check.status == "PASS"
    assert check.formula == SCOPE_FORMULA
    assert check.cash_movement_bridges == (b.cash_movement_bridges[0],)


def test_declared_h1_2026_sums_the_change_in_each_scope_balance() -> None:
    b = book()
    check = _cash_movement(b, flow(b, "h1-2026"))
    assert signed(check) == [965, -887, 96, -85, 16, -12]
    assert check.calculated_value == D(93)
    assert check.difference == D(0)
    assert check.status == "PASS"
    assert check.formula == SCOPE_FORMULA


def test_restricted_cash_only_scope_passes_without_a_noncurrent_balance() -> None:
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
def test_undeclared_scope_keeps_the_cash_only_check(
    pid: str, calculated: int, difference: int
) -> None:
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


def test_undeclared_scope_without_a_bridge_keeps_the_old_formula() -> None:
    b = book(scopes={})
    check = _cash_movement(b, flow(b, "fy-2025"))
    assert check.formula == "closing cash - opening cash; no inferred FX or other cash adjustment"
    assert [t.label for t in check.components] == ["cash_and_equivalents"] * 2


def test_a_missing_scope_balance_is_an_absent_input_never_zero() -> None:
    b = book(drop={NONCURRENT_2024})
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


def test_a_not_applicable_scope_balance_carries_its_reason() -> None:
    na = unsettled("not_applicable", "bs-2024-12-31")
    b = book(drop={NONCURRENT_2024}, extra_lines=(na,))
    check = _cash_movement(b, flow(b, "fy-2025"))
    assert check.components[5].amount is None
    assert check.components[5].reason == "No such balance at that date"
    assert check.calculated_value is None
    assert check.status == "BLOCK"


def test_cash_scope_contract_refuses_a_quote_that_does_not_name_restricted_cash() -> None:
    with pytest.raises(ValidationError, match="names restricted cash"):
        scope_of(BOTH, (cite("Total cash and cash equivalents | 887"),))


def test_cash_scope_contract_accepts_the_quote_across_whitespace_and_case() -> None:
    scope = scope_of(("restricted_cash",), (cite("Increase in cash and Restricted\n  CASH | 93"),))
    assert scope.items == ("restricted_cash",)


def test_cash_scope_contract_refuses_duplicate_items() -> None:
    with pytest.raises(ValidationError, match="distinct"):
        scope_of(("restricted_cash", "restricted_cash"), (cite(NCF_QUOTE["fy-2025"]),))


def test_a_complete_declared_book_has_no_cash_scope_issue() -> None:
    assert cash_bridge_issues(book(flows=("fy-2025",))) == ()


def test_scope_citation_must_cite_the_period_cfs_cash_line() -> None:
    other = cite("Net cash used in operating activities, excluding restricted cash | 1")
    cfo = line("cfs-cfo", "CFS", "cfo_ncfo", "fy-2025", 1, other, kind="total")
    b = book(flows=("fy-2025",), extra_lines=(cfo,))
    off = b.model_copy(update={"cash_movement_bridges": (bridge("fy-2025", BOTH, (other,)),)})
    assert cash_bridge_issues(off) == (FY_CASH_LINE + "b-fy-2025",)


def test_scope_citation_met_by_two_different_citations_is_refused() -> None:
    # One citation is the CFS cash line (no restricted cash named); another names restricted cash.
    ncf_only = cite("Net decrease in cash and cash equivalents | (32) | (127)")
    bs_restricted = cite("Restricted cash | 85 | 95", "page:61")
    b = book(flows=("fy-2025",), declare=False, ncf_citations={"fy-2025": ncf_only})
    split = b.model_copy(
        update={"cash_movement_bridges": (bridge("fy-2025", BOTH, (ncf_only, bs_restricted)),)}
    )
    assert cash_bridge_issues(split) == (FY_CASH_LINE + "b-fy-2025",)


def test_declared_item_without_a_balance_is_refused() -> None:
    b = book(flows=("fy-2025",), drop={NONCURRENT_2024})
    assert cash_bridge_issues(b) == (MISSING_2024,)


@pytest.mark.parametrize("status", ["not_applicable", "missing"])
def test_declared_item_with_an_unsettled_row_is_refused(
    status: Literal["missing", "not_applicable"],
) -> None:
    row = unsettled(status, "bs-2024-12-31")
    b = book(flows=("fy-2025",), drop={NONCURRENT_2024}, extra_lines=(row,))
    assert cash_bridge_issues(b) == (MISSING_2024,)


def test_declared_item_is_required_where_cash_is_only_an_explicit_account() -> None:
    day = date(2024, 12, 31)
    cash_cite = cite("Cash and cash equivalents | 866", "page:61")
    account = AccountObservation(
        metric_id="cash_and_equivalents",
        period_id="bs-2024-12-31",
        value=observation("acct-cash-2024", 866, cash_cite),
    )
    b = book(flows=("fy-2025",), drop={(day, "cash_and_equivalents"), NONCURRENT_2024})
    b = b.model_copy(update={"accounts": (account,)})
    assert cash_bridge_issues(b) == (MISSING_2024,)


def test_declared_item_row_must_be_labelled_restricted() -> None:
    b = book(flows=("fy-2025",), labels={NONCURRENT_2024: "Other long-term assets, net"})
    assert cash_bridge_issues(b) == (
        "Declared cash scope balance must be labelled restricted: "
        "b-fy-2025 restricted_cash_noncurrent 2024-12-31",
    )


def test_a_book_without_any_declaration_serializes_as_before() -> None:
    expected = (
        '{"bridge_id":"b-fy-2025","period_id":"fy-2025","components":[],'
        '"explanation":"no FX or perimeter adjustment is printed","citations":[{"source_id":"k",'
        f'"source_sha256":"{SHA}","locator":"page:60","quote":"{NCF_QUOTE["fy-2025"]}"}}]}}'
    )
    b = book(declare=False)
    first = b.cash_movement_bridges[0]
    assert first.model_dump_json() == expected
    assert first.content_hash() == hashlib.sha256(expected.encode()).hexdigest()
    rec = _cash_movement(b, flow(b, "fy-2025"))
    assert f'"cash_movement_bridges":[{expected}]' in rec.model_dump_json()
    assert "cash_scope" not in rec.model_dump_json()
    assert rec.content_hash() == hashlib.sha256(rec.model_dump_json().encode()).hexdigest()
    pc = constructed(book(flows=tuple(FLOWS), scopes={pid: None for pid in FLOWS}))
    assert "cash_scope" not in pc.model_dump_json()
    assert pc.content_hash() == hashlib.sha256(pc.model_dump_json().encode()).hexdigest()


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
    terms: tuple[tuple[str, Literal[-1, 1]], ...] = (
        ("fy-2025", 1),
        ("h1-2026", 1),
        ("h1-2025", -1),
    )
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


def constructed(b: FinancialBook) -> PeriodCheck:
    node = ltm_node()
    return _period_cash(
        b, historical(b, node), node, term("net_cash_change", -9), term("cash_and_equivalents", 965)
    )


def test_constructed_period_sums_scope_balances_at_the_construction_boundaries() -> None:
    b = book(flows=tuple(FLOWS), scopes={pid: BOTH for pid in FLOWS})
    check = constructed(b)
    assert signed(check) == [965, -982, 96, -85, 16, -19]
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


def test_constructed_period_refuses_sources_with_different_scopes() -> None:
    scopes: dict[str, tuple[Item, ...] | None] = {
        "fy-2025": BOTH,
        "h1-2026": BOTH,
        "h1-2025": None,
    }
    check = constructed(book(flows=tuple(FLOWS), scopes=scopes))
    assert check.status == "BLOCK"
    assert check.calculated_value is None
    assert "Cash scope differs across source periods: h1-2025" in check.explanation


def test_constructed_period_without_any_scope_keeps_the_adjusted_formula_and_bytes() -> None:
    b = book(flows=tuple(FLOWS), scopes={pid: None for pid in FLOWS})
    check = constructed(b)
    assert [t.label for t in check.components[:2]] == ["cash_and_equivalents"] * 2
    assert check.formula == (
        "closing cash - opening cash - signed period combination of source adjustments"
    )
    assert '"cash_scope"' not in check.model_dump_json()
