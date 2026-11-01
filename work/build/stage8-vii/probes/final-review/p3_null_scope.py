"""A strict-mode reply carries "cash_scope": null; normalise + validate + dump must equal the undeclared form."""
import json, sys
from deploy_vii.financial_contracts import CashMovementBridge
from deploy_vii.live.schema import normalise
base = {"bridge_id": "b", "period_id": "p", "components": [], "explanation": "x",
        "citations": [{"source_id": "s", "source_sha256": "a"*64, "locator": "page:1", "quote": "q"}]}
with_null = dict(base, cash_scope=None)
out, paths = normalise(CashMovementBridge, json.dumps(with_null))
print("normalised paths:", paths)
a = CashMovementBridge.model_validate_json(out); b = CashMovementBridge.model_validate_json(json.dumps(base))
print("dump equal:", a.model_dump(mode="json") == b.model_dump(mode="json"), "cash_scope" in a.model_dump(mode="json"))
print("json:", a.model_dump_json()[:200])
rc = 0 if a.model_dump(mode="json") == b.model_dump(mode="json") and "cash_scope" not in a.model_dump(mode="json") else 1
# round trip of a declared scope through JSON
d = dict(base, cash_scope={"items": ["restricted_cash"], "citations": [{"source_id": "s", "source_sha256": "a"*64, "locator": "page:2", "quote": "cash and restricted cash"}]})
m = CashMovementBridge.model_validate_json(json.dumps(d))
rt = CashMovementBridge.model_validate_json(m.model_dump_json())
print("declared round trip:", rt == m)
rc |= 0 if rt == m else 1
sys.exit(rc)
