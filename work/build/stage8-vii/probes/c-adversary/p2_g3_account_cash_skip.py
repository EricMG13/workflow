"""P2: G3 looks only for a BS *statement line* cash_and_equivalents, but `_balance` reads
effective_accounts (explicit accounts first). With opening cash supplied as an explicit account and
the declared noncurrent row omitted at that date, G3 is silent and the computed BLOCK (53) becomes
an absent input item 82 downgrades. Exit 1 = exploit reproduced."""
import sys
from datetime import date

sys.path.insert(0, __import__("os").path.dirname(__file__))
from _common import item82
from test_cash_scope import book, cite, flow, observation
from deploy_vii.cash_bridge import cash_bridge_issues
from deploy_vii.financial_contracts import AccountObservation
from deploy_vii.financial_reconciliation import _cash_movement
from deploy_vii.financial_validation import book_issues

ca = item82()
day = date(2024, 12, 31)
acct = AccountObservation(metric_id="cash_and_equivalents", period_id="bs-2024-12-31",
                          value=observation("acct-cash-2024", 866,
                                            cite("Cash and cash equivalents | 866", "page:61")))
results = {}
for declare in (False, True):
    b = book(flows=("fy-2025",), declare=declare,
             drop={(day, "cash_and_equivalents"), (day, "restricted_cash_noncurrent")})
    b = b.model_copy(update={"accounts": (acct,)})
    b = type(b).model_validate_json(b.model_dump_json())
    chk = _cash_movement(b, flow(b, "fy-2025"))
    lim = ca.absent_input_limitation(chk, public=True,
                                     conflicting=ca.conflicting_observation_ids(b),
                                     shadowed=ca.shadowed_account_ids(b))
    results[declare] = (cash_bridge_issues(b), book_issues(b), chk.difference, lim)
    print("declared" if declare else "undeclared", "G2/G3:", cash_bridge_issues(b),
          "book_issues:", book_issues(b))
    print("  check:", chk.status, chk.calculated_value, chk.difference, "item82 ->",
          "WARN" if lim else "stays BLOCK")
ok = results[False][2] == 53 and results[False][3] is None
hit = not results[True][0] and not results[True][1] and results[True][2] is None and results[True][3]
print("EXPLOITED" if ok and hit else "not reproduced")
sys.exit(1 if ok and hit else 0)
