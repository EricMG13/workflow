"""P6: constructed LTM (fy-2025 + h1-2026 - h1-2025), every source declares BOTH, the 2025-06-30
noncurrent row (the LTM opening boundary and h1-2025's closing) is `not_applicable`. G3 passes;
the constructed check and h1-2025's source check have no difference, so item 82 downgrades the
constructed check too. Exit 1 = downgraded with no validation issue."""
import sys
from datetime import date

sys.path.insert(0, __import__("os").path.dirname(__file__))
from _common import item82
from test_cash_scope import FLOWS, book, constructed, flow
from deploy_vii.cash_bridge import cash_bridge_issues
from deploy_vii.financial_contracts import Observation, StatementLine
from deploy_vii.financial_reconciliation import _cash_movement
from deploy_vii.financial_validation import book_issues

ca = item82()
na = StatementLine(line_id="bs-rc-nc", statement="BS", item_id="restricted_cash_noncurrent",
                   label="Restricted and escrow cash", period_id="bs-2025-06-30",
                   display_priority=999, line_kind="detail",
                   value=Observation(observation_id="obs-na", status="not_applicable",
                                     amount=None, citations=(), reason="Not presented"))
b = book(flows=tuple(FLOWS), scopes={p: ("restricted_cash", "restricted_cash_noncurrent")
                                     for p in FLOWS},
         drop={(date(2025, 6, 30), "restricted_cash_noncurrent")}, extra_lines=(na,))
print("G2/G3:", cash_bridge_issues(b), "book_issues:", book_issues(b))
src = _cash_movement(b, flow(b, "h1-2025"))
print("h1-2025 source:", src.status, src.difference, src.explanation)
pc = constructed(b)
lim = ca.absent_input_limitation(pc, public=True, conflicting=frozenset(),
                                 normalised=frozenset())
print("constructed:", pc.status, pc.calculated_value, pc.difference, "|", pc.explanation)
print("item82 ->", "WARN" if lim else "stays BLOCK")
sys.exit(1 if lim and not cash_bridge_issues(b) and not book_issues(b) else 0)
