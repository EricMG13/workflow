"""At base: module path, CashScope absent, undeclared fy-2025/h1-2026 give 21/53 and 78/-15 BLOCK."""
import sys
sys.path.insert(0, sys.argv[1])
import deploy_vii.financial_contracts as fc, test_cash_scope as t
from deploy_vii.financial_reconciliation import _cash_movement
print(fc.__file__, hasattr(fc, "CashScope"))
b = t.book(declare=False)
for pid in ("fy-2025", "h1-2026"):
    c = _cash_movement(b, t.flow(b, pid))
    print(pid, c.calculated_value, c.difference, c.status, c.formula)
