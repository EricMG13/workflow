"""P1: G3 accepts a declared item row of any status, so a `not_applicable`/`missing` row with no
citation turns CZR fy-2025's computed BLOCK (difference 53) into difference None, which item 82
downgrades to WARN on a public case. Exit 1 = exploit reproduced."""
import sys
from datetime import date

sys.path.insert(0, __import__("os").path.dirname(__file__))
from _common import item82
from test_cash_scope import book, flow
from deploy_vii.cash_bridge import cash_bridge_issues
from deploy_vii.financial_contracts import Observation, StatementLine
from deploy_vii.financial_reconciliation import _cash_movement
from deploy_vii.financial_validation import book_issues

ca = item82()
day = date(2024, 12, 31)
exploited = []
for status in ("not_applicable", "missing"):
    absent = Observation(observation_id=f"obs-{status}", status=status, amount=None,
                         citations=(), reason="Not separately presented at this date")
    row = StatementLine(line_id="bs-rc-nc", statement="BS", item_id="restricted_cash_noncurrent",
                        label="Restricted and escrow cash in other long-term assets",
                        period_id="bs-2024-12-31", display_priority=999, line_kind="detail",
                        value=absent)
    b = book(flows=("fy-2025",), drop={(day, "restricted_cash_noncurrent")}, extra_lines=(row,))
    g = cash_bridge_issues(b)
    allb = book_issues(b)
    chk = _cash_movement(b, flow(b, "fy-2025"))
    lim = ca.absent_input_limitation(chk, public=True,
                                     conflicting=ca.conflicting_observation_ids(b),
                                     shadowed=ca.shadowed_account_ids(b))
    print(status, "cash_bridge_issues=", g, "book_issues=", allb)
    print("  check:", chk.status, chk.calculated_value, chk.difference)
    print("  item82 ->", "WARN: " + lim if lim else "stays BLOCK")
    if not g and not allb and lim:
        exploited.append(status)

base = book(flows=("fy-2025",), declare=False)
c0 = _cash_movement(base, flow(base, "fy-2025"))
l0 = ca.absent_input_limitation(c0, public=True, conflicting=frozenset())
print("undeclared:", c0.status, c0.calculated_value, c0.difference, "item82 ->", l0 or "stays BLOCK")
print("EXPLOITED" if exploited else "not reproduced", exploited)
sys.exit(1 if exploited and l0 is None else 0)
