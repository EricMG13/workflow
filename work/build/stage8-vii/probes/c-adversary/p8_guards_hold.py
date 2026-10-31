"""P8 (negative): guards that should refuse do refuse. (1) restricted_cash on CFS/IS is an unknown
item; (2) the noncurrent row at another date (2024-12-30) leaves G3 reporting 2024-12-31 and the
term absent; (3) a scope citing another period's CFS cash line fails G2; (4) a conflicting scope
row stays BLOCK under item 82; (5) mixed constructed scope blocks. Exit 0 = all hold."""
import sys
from datetime import date

sys.path.insert(0, __import__("os").path.dirname(__file__))
from _common import item82
from test_cash_scope import BOTH, FLOWS, NCF_QUOTE, book, bridge, cite, constructed, flow, line, period
from deploy_vii.cash_bridge import cash_bridge_issues
from deploy_vii.financial_contracts import Alternative, Observation, StatementLine
from deploy_vii.financial_reconciliation import _cash_movement
from deploy_vii.financial_validation import book_issues
from deploy_vii.statement_validation import statement_issues

ca = item82()
fails = []
for st in ("CFS", "IS"):
    b = book(flows=("fy-2025",), extra_lines=(line("x", st, "restricted_cash", "fy-2025", 1,
                                                   cite("Restricted cash | 1"), priority=777),))
    ok = any("Unknown statement item" in i for i in statement_issues(b))
    print("1", st, ok); fails += [] if ok else [f"1{st}"]
d = date(2024, 12, 30)
b = book(flows=("fy-2025",), drop={(date(2024, 12, 31), "restricted_cash_noncurrent")})
p = period("bs-2024-12-30", "PERIOD_END", None, "FY2024", None, d)
b = b.model_copy(update={"periods": (*b.periods, p), "statement_lines": (*b.statement_lines,
    line("nc30", "BS", "restricted_cash_noncurrent", "bs-2024-12-30", 55,
         cite("Restricted and escrow cash | 55", "page:61"), priority=778))})
g = cash_bridge_issues(b); c = _cash_movement(b, flow(b, "fy-2025"))
ok = any("2024-12-31" in i for i in g) and c.difference is None
print("2", g, c.difference); fails += [] if ok else ["2"]
b = book(flows=("fy-2025", "h1-2026"))
b = b.model_copy(update={"cash_movement_bridges": (
    bridge("fy-2025", BOTH, (cite(NCF_QUOTE["h1-2026"]),)), b.cash_movement_bridges[1])})
ok = any("must cite the period's CFS cash line: b-fy-2025" in i for i in cash_bridge_issues(b))
print("3", cash_bridge_issues(b)); fails += [] if ok else ["3"]
alts = tuple(Alternative(amount=__import__("decimal").Decimal(v), citations=(cite(f"Restricted and escrow cash | {v}", "page:61"),),
                         explanation="two columns") for v in (55, 56))
cf = StatementLine(line_id="nc-c", statement="BS", item_id="restricted_cash_noncurrent", label="x",
                   period_id="bs-2024-12-31", display_priority=779, line_kind="detail",
                   value=Observation(observation_id="obs-c", status="conflicting", amount=None,
                                     citations=(), reason="two values", alternatives=alts))
b = book(flows=("fy-2025",), drop={(date(2024, 12, 31), "restricted_cash_noncurrent")}, extra_lines=(cf,))
c = _cash_movement(b, flow(b, "fy-2025"))
lim = ca.absent_input_limitation(c, public=True, conflicting=ca.conflicting_observation_ids(b))
print("4", c.status, c.difference, "stays BLOCK" if lim is None else "WARN"); fails += [] if lim is None else ["4"]
pc = constructed(book(flows=tuple(FLOWS), scopes={"fy-2025": BOTH, "h1-2026": BOTH, "h1-2025": ("restricted_cash",)}))
ok = pc.status == "BLOCK" and "Cash scope differs across source periods: h1-2025" in pc.explanation
print("5", pc.status, pc.explanation[:120]); fails += [] if ok else ["5"]
print("FAIL" if fails else "all hold", fails)
sys.exit(1 if fails else 0)
