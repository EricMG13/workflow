"""P7: (a) nothing ties a declared item's BS row to restricted cash (label/quote unchecked) and no
cross-check against a printed CFS closing/opening cash total exists: an issuer whose true scope
(cash + current restricted) disagrees by 43 maps 'Other long-term assets, net' as
restricted_cash_noncurrent and the check PASSes with no issue. (b) double counting: cash already
including restricted cash plus a declared restricted_cash shows as a difference when it moves.
Exit 1 = (a) reproduced."""
import sys
from datetime import date

from test_cash_scope import book, cite, flow, line
from deploy_vii.cash_bridge import cash_bridge_issues
from deploy_vii.financial_reconciliation import _cash_movement
from deploy_vii.financial_validation import book_issues

drop = {(date(2024, 12, 31), "restricted_cash_noncurrent"),
        (date(2025, 12, 31), "restricted_cash_noncurrent")}
olta = [line(f"bs-olta-{d}", "BS", "restricted_cash_noncurrent", f"bs-{d}", v,
             cite(f"Other long-term assets, net | {v}", "page:61"), priority=900 + i)
        for i, (d, v) in enumerate((("2024-12-31", 1043), ("2025-12-31", 1000)))]
olta = [r.model_copy(update={"label": "Other long-term assets, net"}) for r in olta]
true = book(flows=("fy-2025",), scopes={"fy-2025": ("restricted_cash",)}, drop=drop)
c0 = _cash_movement(true, flow(true, "fy-2025"))
print("true scope (cash + current restricted):", c0.status, c0.calculated_value, c0.difference)
fake = book(flows=("fy-2025",), drop=drop, extra_lines=tuple(olta))
c1 = _cash_movement(fake, flow(fake, "fy-2025"))
iss = (*cash_bridge_issues(fake), *book_issues(fake))
print("mislabelled OLTA as noncurrent restricted:", c1.status, c1.calculated_value,
      c1.difference, "issues:", iss)
# (b) double count: restricted_cash also inside cash_and_equivalents, restricted moves 95 -> 85
dc = book(flows=("fy-2025",), scopes={"fy-2025": ("restricted_cash",)}, drop=drop)
c2 = _cash_movement(dc, flow(dc, "fy-2025"))
print("double count with nonzero movement shows a difference:", c2.status, c2.difference)
hit = c0.status == "BLOCK" and c0.difference == 43 and c1.status == "PASS" and not iss
sys.exit(1 if hit else 0)
