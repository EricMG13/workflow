"""Cash scope vs the schema the model is shown and prefill's marked-field walk."""
import json, sys
from deploy_vii.financial_contracts import CashMovementBridge
from deploy_vii.live import schema as S
from deploy_vii.live.schema import marked_fields, strict_copy
rc = 0
sc = CashMovementBridge.model_json_schema()
prop = sc["properties"].get("cash_scope")
print("validation-mode cash_scope:", json.dumps(prop))
st = strict_copy(CashMovementBridge)
print("strict required has cash_scope:", "cash_scope" in st.get("required", []))
print("strict cash_scope:", json.dumps(st["properties"]["cash_scope"]))
cs = st["$defs"].get("CashScope")
print("strict CashScope:", json.dumps(cs)[:600])
doc = {"bridge_id": "b", "period_id": "p", "components": [], "explanation": "x",
       "citations": [{"source_id": "s", "locator": "page:1", "quote": "q"}],
       "cash_scope": {"items": ["restricted_cash"],
                      "citations": [{"source_id": "s", "locator": "page:61", "quote": "restricted cash"}]}}
found = [m.path for m in marked_fields(CashMovementBridge, doc)]
print("marked:", found)
if not any(p.startswith("cash_scope.") for p in found):
    print("FAIL: prefill walk misses cash_scope citations"); rc = 1
sent = getattr(S, "strict_schema", None)
if sent:
    try:
        out = sent(CashMovementBridge)
        print("strict_schema ok; cash_scope sent:", json.dumps(out["properties"]["cash_scope"] if "properties" in out else "?")[:300])
    except Exception as e:
        print("strict_schema raised", type(e).__name__, e); rc = 1
sys.exit(rc)
