"""R1: the CZR proof book (as test_czr_cash_scope._declared builds it) has no G2/G3/label issue
under the fix, the CFS cash-line citation names restricted cash, and both NCF_CASH_MOVEMENT checks
PASS. Also lists every flow period and whether the 10-Q prior YTD (h1-2025) could be declared.
Exit 1 = the fix refuses the CZR declaration."""
import copy, json, sys
from test_czr_cash_scope import _declared
from czr_runs import CASE
from deploy_vii.cash_bridge import cash_bridge_issues
from deploy_vii.financial_contracts import FinancialBook, CashMovementBridge
from deploy_vii.financial_validation import book_issues
from deploy_vii.financial_reconciliation import _cash_movement

data = _declared(copy.deepcopy(json.loads((CASE / "submissions-partial.json").read_text())))
stage = next(s for s in data["stages"] if s["step"] == "financials")
raw = stage["submission"]["financial"]["books"][0]
DIMS = {"currency": "USD", "unit": "MILLIONS", "accounting_basis": "US GAAP", "entity_perimeter": "consolidated"}
raw = {**raw, **DIMS, "periods": [{**p, **DIMS} for p in raw["periods"]]}
b = FinancialBook.model_validate_json(json.dumps(raw))
g = cash_bridge_issues(b)
allb = [i for i in book_issues(b) if "cash" in i.lower()]
print("cash_bridge_issues:", g)
print("book_issues (cash):", allb)
for br in b.cash_movement_bridges:
    print(br.bridge_id, [c.quote for c in br.cash_scope.citations])
    p = next(p for p in b.periods if p.period_id == br.period_id)
    c = _cash_movement(b, p)
    print("  ", c.status, c.calculated_value, c.difference)
for r in b.statement_lines:
    if r.statement == "BS" and r.item_id in ("restricted_cash", "restricted_cash_noncurrent"):
        print("BS", r.period_id, r.item_id, r.value.status, repr(r.label))
flows = [p.period_id for p in b.periods if p.period_type != "PERIOD_END"]
print("flow periods:", flows)
print("BS dates:", sorted({str(p.end_date) for p in b.periods if p.period_type == "PERIOD_END"}))
# Would a truthful declaration on the 10-Q prior YTD be refused?
h = next((p for p in b.periods if p.period_id == "h1-2025"), None)
if h is not None:
    line = next(r for r in b.statement_lines if r.item_id == "net_cash_change" and r.period_id == "h1-2025")
    cit = line.value.citations[0]
    print("h1-2025 CFS quote:", cit.quote)
    extra = CashMovementBridge.model_validate_json(json.dumps({"bridge_id": "bridge-h1-2025", "period_id": "h1-2025",
        "components": [], "explanation": "x", "citations": [cit.model_dump()],
        "cash_scope": {"items": ["restricted_cash", "restricted_cash_noncurrent"], "citations": [cit.model_dump()]}}, default=str))
    b2 = b.model_copy(update={"cash_movement_bridges": (*b.cash_movement_bridges, extra)})
    print("h1-2025 declared ->", cash_bridge_issues(b2))
    c = _cash_movement(b2, h)
    print("  check:", c.status, c.calculated_value, c.difference)
    b3 = b.model_copy(update={"cash_movement_bridges": (*b.cash_movement_bridges, extra.model_copy(update={"cash_scope": None}))})
    c = _cash_movement(b3, h)
    print("  undeclared h1-2025 check:", c.status, c.calculated_value, c.difference)
sys.exit(1 if g or allb else 0)
