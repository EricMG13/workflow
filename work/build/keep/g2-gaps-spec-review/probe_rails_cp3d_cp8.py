"""Ruling 6 feasibility: cp3d/cp8 rails from the oracle on fast pages; and the oracle limitation split."""
import importlib, json, sys
sys.path.insert(0, sys.argv[1])
import common as C
E3 = C.oracle("cp3d-owner"); E8 = C.oracle("cp8-owner")
base = importlib.import_module("test_connect_cp3d")
bad = 0
for case in ("positive", "gap_no_recovery", "gap_no_market"):
    pack = base._pack(case); mod = base._module(case)
    p = C.payload_of(C.view_with(pack.run, [mod]))
    m = C.module_payload(p, "CP-3D"); tids = {t["table_id"] for t in m["tables"]}
    rails = set(E3["render"]["blocks"]["evidence rail"]) | set(E3["render"]["blocks"]["limitations rail"])
    oc = E3["cases"][case]
    want = list(dict.fromkeys([*oc["own_limitations"], *oc["inherited_limitations"]]))
    print(case, "rails<=tables", rails <= tids, "limits==own+inh", m["limitations"] == want, len(m["limitations"]), len(want))
    if not rails <= tids: bad += 1
print("cp8 case keys", [k for k in E8["cases"]["positive"] if "limit" in k])
for k in E8["cases"]["positive"]:
    if "limit" in k: print(k, json.dumps(E8["cases"]["positive"][k])[:300])
sys.exit(bad)
