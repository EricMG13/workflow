"""P5: does any serializer path drop or alter a non-None cash_scope (so a stored, rehashed artifact
would verify while meaning something else)? Exit 1 = a loss found; 0 = every round trip holds."""
import json
import sys

from test_cash_scope import FLOWS, book, constructed, flow
from deploy_vii.financial_contracts import CashMovementBridge, FinancialBook
from deploy_vii.financial_reconciliation import Reconciliation, _cash_movement
from deploy_vii.period_reconciliation import PeriodCheck

bad = []
b = book(flows=tuple(FLOWS))
br = b.cash_movement_bridges[0]
for label, dumped in (
    ("json", br.model_dump_json()),
    ("python-json", json.dumps(br.model_dump(mode="json"), separators=(",", ":"))),
    ("exclude_defaults", br.model_dump_json(exclude_defaults=True)),
    ("exclude_unset", br.model_dump_json(exclude_unset=True)),
    ("exclude_none", br.model_dump_json(exclude_none=True)),
    ("round_trip", br.model_dump_json(round_trip=True)),
):
    back = CashMovementBridge.model_validate_json(dumped)
    if back != br or back.content_hash() != br.content_hash():
        bad.append(label)
    print(label, "cash_scope" in dumped, back == br)
bb = FinancialBook.model_validate_json(b.model_dump_json())
print("book", bb == b, bb.content_hash() == b.content_hash())
bad += [] if bb == b else ["book"]
rec = _cash_movement(b, flow(b, "fy-2025"))
r2 = Reconciliation.model_validate_json(rec.model_dump_json())
print("reconciliation", r2 == rec, '"cash_scope"' in rec.model_dump_json())
bad += [] if r2 == rec else ["reconciliation"]
pc = constructed(b)
p2 = PeriodCheck.model_validate_json(pc.model_dump_json())
print("period check", p2 == pc, pc.status, '"cash_scope"' in pc.model_dump_json())
bad += [] if p2 == pc else ["period"]
# explicit null in a stored payload: parses to None and re-dumps without the key
nul = json.loads(b.cash_movement_bridges[0].model_copy(update={"cash_scope": None}).model_dump_json())
nul["cash_scope"] = None
n2 = CashMovementBridge.model_validate_json(json.dumps(nul))
print("explicit null ->", n2.cash_scope, '"cash_scope"' in n2.model_dump_json())
# model_copy(update=...) bypasses validation: an undeclared copy loses the key, as intended
print("serialization schema keeps the fields:",
      "properties" in CashMovementBridge.model_json_schema(mode="serialization"))
print("LOSS" if bad else "no loss", bad)
sys.exit(1 if bad else 0)
