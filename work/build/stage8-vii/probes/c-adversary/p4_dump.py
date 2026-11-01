"""P4 helper: dump undeclared-scope outputs (single, constructed, adjusted, unadjusted, missing,
FX component) as one sha256 per scenario; run under base src and head src and compare."""
import hashlib
import sys
from datetime import date

from test_cash_scope import FLOWS, book, cite, constructed, flow, line
from deploy_vii.cash_bridge import cash_bridge_issues
from deploy_vii.financial_contracts import StatementContribution
from deploy_vii.financial_reconciliation import _cash_movement
from deploy_vii.statement_validation import statement_issues


def h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


fx = line("cfs-fx", "CFS", "fx_cash_effect", "fy-2025", 53, cite("Effect of FX | 53"), priority=500)
scen = {
    "bridged": book(flows=tuple(FLOWS), scopes={p: None for p in FLOWS}),
    "nobridge": book(flows=tuple(FLOWS), scopes={}),
    "missing": book(flows=tuple(FLOWS), scopes={p: None for p in FLOWS},
                    drop={(date(2024, 12, 31), "cash_and_equivalents")}),
    "partial": book(flows=tuple(FLOWS), scopes={"fy-2025": None, "h1-2026": None}),
    "fx": book(flows=tuple(FLOWS), scopes={p: None for p in FLOWS}, extra_lines=(fx,)),
}
b = scen["fx"]
br = b.cash_movement_bridges[0].model_copy(
    update={"components": (StatementContribution(line_id="cfs-fx", coefficient=1),)})
scen["fx"] = b.model_copy(update={"cash_movement_bridges": (br, *b.cash_movement_bridges[1:])})
for name, b in scen.items():
    out = [b.model_dump_json(), repr(cash_bridge_issues(b)), repr(statement_issues(b))]
    for pid in FLOWS:
        out.append(_cash_movement(b, flow(b, pid)).model_dump_json())
    out.append(constructed(b).model_dump_json())
    print(name, h("\n".join(out)), *(h(o) for o in out))
