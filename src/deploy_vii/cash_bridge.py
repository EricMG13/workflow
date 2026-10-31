"""Validate explicitly sourced cash movement adjustments, without inferring FX."""

from datetime import timedelta

from deploy_vii.financial_contracts import CashMovementBridge, FinancialBook, FinancialPeriod

CASH_LINE_ITEMS = {"net_cash_change", "opening_cash", "closing_cash"}


def cash_bridge_issues(book: FinancialBook) -> tuple[str, ...]:
    if not book.cash_movement_bridges:
        return ()
    periods = {p.period_id: p for p in book.periods}
    lines = {(r.period_id, r.line_id): r for r in book.statement_lines}
    targets = {(r.period_id, r.target_line_id) for r in book.statement_identities}
    ids: set[str] = set()
    assessed: set[str] = set()
    issues: list[str] = []
    for bridge in book.cash_movement_bridges:
        bridge_id, period_id = bridge.bridge_id, bridge.period_id
        if bridge_id in ids or period_id in assessed:
            issues.append(f"Duplicate cash movement bridge: {bridge_id}")
        ids.add(bridge_id)
        assessed.add(period_id)
        period = periods.get(period_id)
        if period is None or period.period_type == "PERIOD_END":
            issues.append(f"Cash movement bridge requires a flow period: {bridge_id}")
        seen: set[str] = set()
        for part in bridge.components:
            line_id = part.line_id
            if line_id in seen:
                issues.append(f"Duplicate cash adjustment line: {bridge_id} {line_id}")
            seen.add(line_id)
            key = period_id, line_id
            line = lines.get(key)
            if line is None:
                issues.append(f"Unknown cash adjustment line: {bridge_id} {line_id}")
            elif (
                line.statement != "CFS"
                or line.line_kind != "detail"
                or key in targets
                or not (line.item_id == "fx_cash_effect" or line.item_id.startswith("other:"))
            ):
                issues.append(
                    f"Cash adjustment requires a source FX/perimeter detail: {bridge_id} {line_id}"
                )
        if bridge.cash_scope is not None:
            issues.extend(_scope_issues(book, bridge, period))
    return tuple(issues)


def _scope_issues(
    book: FinancialBook, bridge: CashMovementBridge, period: FinancialPeriod | None
) -> list[str]:
    """A declared scope cites the period's CFS cash line and has its balances where checked."""
    scope = bridge.cash_scope
    assert scope is not None
    bridge_id = bridge.bridge_id
    issues: list[str] = []
    cfs_cash = {
        c
        for r in book.statement_lines
        if r.period_id == bridge.period_id and r.statement == "CFS" and r.item_id in CASH_LINE_ITEMS
        for c in r.value.citations
    }
    # One citation must both be the CFS cash line and name restricted cash.
    if not any(
        c in cfs_cash and "restricted cash" in " ".join(c.quote.split()).lower()
        for c in scope.citations
    ):
        issues.append(
            f"Cash scope citation must cite the period's CFS cash line naming restricted cash: "
            f"{bridge_id}"
        )
    if period is None or period.end_date is None:
        return issues
    days = [period.end_date]
    if period.start_date is not None and period.start_date.toordinal() > 1:
        days.append(period.start_date - timedelta(days=1))
    for day in days:
        ids = {p.period_id for p in book.periods if p.end_date == day}
        for item in scope.items:
            # The row the check reads: a conflict first, else the first stated amount.
            rows = [
                r
                for r in book.statement_lines
                if r.statement == "BS" and r.item_id == item and r.period_id in ids
            ]
            settled = [r for r in rows if r.value.status in {"known", "conflicting"}]
            used = next((r for r in settled if r.value.status == "conflicting"), None) or next(
                iter(settled), None
            )
            where = f"{bridge_id} {item} {day.isoformat()}"
            if used is None:
                issues.append(f"Declared cash scope balance missing: {where}")
            elif "restricted" not in " ".join(used.label.split()).lower():
                issues.append(f"Declared cash scope balance must be labelled restricted: {where}")
    return issues
