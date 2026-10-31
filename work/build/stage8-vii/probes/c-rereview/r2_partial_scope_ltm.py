"""R2 (remaining path, predates the fix): LTM = fy-2025 + h1-2026 - h1-2025, every source bridged.
Restricted cash does not move in H1 2025 (so h1-2025 passes cash-only). Undeclared everywhere: the
LTM check is BLOCK on a child difference (item 82 keeps it BLOCK). Declared on fy-2025 and h1-2026
only: no validation issue, the LTM check is BLOCK 'Cash scope differs' with no difference, and
item 82 downgrades it. Declared on all three: PASS. Exit 1 = the downgrade with no issue reproduces."""
import os, sys
from datetime import date
sys.path.insert(0, "/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-lead-multi-round-707c23/e6c96f51-02e9-4443-a171-c01f29919334/scratchpad/s8c")
from _common import item82
import test_cash_scope as t
from deploy_vii.cash_bridge import cash_bridge_issues
from deploy_vii.financial_validation import book_issues
from deploy_vii.period_reconciliation import _period_cash

t.BALANCES[date(2025, 6, 30)] = (982, 95, 55)  # restricted unchanged over H1 2025
t.FLOWS["h1-2025"] = t.FLOWS["h1-2025"]._replace(ncf=116)
ca = item82()
node = t.ltm_node()
out = {}
for name, scopes in (("undeclared", {p: None for p in t.FLOWS}),
                     ("partial", {"fy-2025": t.BOTH, "h1-2026": t.BOTH, "h1-2025": None}),
                     ("all", {p: t.BOTH for p in t.FLOWS})):
    b = t.book(flows=tuple(t.FLOWS), scopes=scopes)
    chk = _period_cash(b, t.historical(b, node), node, t.term("net_cash_change", -55),
                       t.term("cash_and_equivalents", 965))
    lim = ca.absent_input_limitation(chk, public=True, conflicting=frozenset(), normalised=frozenset())
    iss = (*cash_bridge_issues(b), *book_issues(b))
    out[name] = (chk.status, chk.difference, bool(lim), iss)
    print(name, chk.status, chk.calculated_value, chk.difference, "|", chk.explanation[:110])
    print("   issues:", iss, "item82:", "WARN" if lim else "stays BLOCK/as is")
hit = (out["undeclared"][0] == "BLOCK" and not out["undeclared"][2]
       and out["partial"][2] and not out["partial"][3])
print("REPRODUCED" if hit else "not reproduced")
sys.exit(1 if hit else 0)
