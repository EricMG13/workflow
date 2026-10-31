"""P3: G1 (a quote naming restricted cash) and G2 (a citation equal to the period's CFS cash line)
may be satisfied by *different* citations, so a scope is accepted for a CFS whose cash line is cash
and equivalents only (no restricted cash), using a BS 'Restricted cash' quote for G1.
Exit 1 = accepted with no issue (guard gap reproduced)."""
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from test_cash_scope import BOTH, book, bridge, cite, flow
from deploy_vii.cash_bridge import cash_bridge_issues
from deploy_vii.financial_reconciliation import _cash_movement
from deploy_vii.financial_validation import book_issues

ncf_only = cite("Net decrease in cash and cash equivalents | (32) | (127)")
bs_rc = cite("Restricted cash | 85 | 95", "page:61")
b = book(flows=("fy-2025",), declare=False, ncf_citations={"fy-2025": ncf_only})
b = b.model_copy(update={"cash_movement_bridges": (
    bridge("fy-2025", BOTH, (ncf_only, bs_rc)).model_copy(update={"citations": (ncf_only,)}),)})
b = type(b).model_validate_json(b.model_dump_json())
assert "restricted cash" not in ncf_only.quote.lower()
g = cash_bridge_issues(b)
print("CFS cash line quote:", ncf_only.quote)
print("cash_bridge_issues:", g, "book_issues:", book_issues(b))
chk = _cash_movement(b, flow(b, "fy-2025"))
print("check:", chk.status, chk.calculated_value, chk.difference, chk.formula)
sys.exit(1 if not g and not book_issues(b) else 0)
