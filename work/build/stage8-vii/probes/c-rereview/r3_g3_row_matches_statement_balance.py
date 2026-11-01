"""R3: G3's 'row the check reads' is exactly `_statement_balance`'s row. Every ordered list of 1-3
rows over {known, conflicting, missing, not_applicable} at 2024-12-31 for the declared noncurrent
item; each row gets its own label, and in turn each row is the only one labelled 'Restricted'.
Expect: missing issue <=> the check's term has no amount and is not a conflict; label issue <=> the
check's chosen observation is not the restricted-labelled row. Exit 1 = any mismatch."""
import itertools, sys
from datetime import date
from decimal import Decimal
from test_cash_scope import book, cite
from deploy_vii.cash_bridge import cash_bridge_issues
from deploy_vii.financial_contracts import Alternative, Observation, StatementLine
from deploy_vii.financial_reconciliation import _statement_balance

DAY = date(2024, 12, 31)
ITEM = "restricted_cash_noncurrent"
STATUSES = ("known", "conflicting", "missing", "not_applicable")


def obs(i: int, status: str) -> Observation:
    c = cite(f"Restricted and escrow cash | {50 + i}", "page:61")
    if status == "known":
        return Observation(observation_id=f"o{i}", status="known", amount=Decimal(50 + i), citations=(c,))
    alts = ()
    if status == "conflicting":
        alts = tuple(Alternative(amount=Decimal(50 + i + k), citations=(cite(f"alt {i} {k}", "page:61"),),
                                 explanation=f"alt {k}") for k in (0, 1))
    return Observation(observation_id=f"o{i}", status=status, amount=None, citations=(), reason="gap",
                       alternatives=alts)


bad = []
n = 0
for size in (1, 2, 3):
    for combo in itertools.product(STATUSES, repeat=size):
        for marked in range(size):
            rows = tuple(
                StatementLine(line_id=f"r{i}", statement="BS", item_id=ITEM,
                              label=("Restricted and escrow cash" if i == marked else f"Other long-term assets {i}"),
                              period_id="bs-2024-12-31", display_priority=500 + i, line_kind="detail",
                              value=obs(i, s))
                for i, s in enumerate(combo))
            b = book(flows=("fy-2025",), drop={(DAY, ITEM)}, extra_lines=rows)
            iss = [x for x in cash_bridge_issues(b) if "2024-12-31" in x]
            term = _statement_balance(b, DAY, ITEM)
            chosen = next((r for r in rows if r.value.observation_id == term.observation_id), None)
            settled = chosen is not None and chosen.value.status in {"known", "conflicting"}
            exp = []
            if not settled:
                exp.append("missing")
            elif chosen is not rows[marked]:
                exp.append("label")
            got = ["missing" if "missing" in x else "label" for x in iss]
            n += 1
            if got != exp:
                bad.append((combo, marked, term.observation_id, got, exp))
print("cases", n, "mismatches", len(bad))
for x in bad[:10]:
    print(x)
sys.exit(1 if bad else 0)
