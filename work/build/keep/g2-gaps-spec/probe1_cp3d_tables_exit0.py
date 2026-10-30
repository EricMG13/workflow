"""cp3d: `#/cases/<c>/tables` against the block's registers on real fast pages; perturbations fail."""
import copy
import importlib
import sys

sys.path.insert(0, sys.argv[1])
import common as C  # noqa: E402

base = importlib.import_module("test_connect_cp3d")
E = C.oracle("cp3d-owner")
node = E["render"]["blocks"]["market-against-fundamentals"]
fails = 0


def check(payload, case):
    (block,) = [b for b in payload["report"]["blocks"] if b["block_id"] == "market-against-fundamentals"]
    regs = C.registers(block)
    tables = {t["table_id"]: t for t in E["cases"][case]["tables"]}
    assert len(regs) == len(node["tabs"])
    for reg, (tid, label) in zip(regs, node["tabs"], strict=True):
        C.assert_register_equals_table(reg, label, tables[tid], "CP-3D", payload)


for case in ("positive", "gap_no_recovery", "gap_no_market"):
    pack = base._pack(case)
    view = C.view_with(pack.run, [base._module(case)])
    payload = C.payload_of(view)
    check(payload, case)
    print(case, "accepts")
    # perturbations: one field each
    perturbs = []
    p = copy.deepcopy(payload); b = [x for x in p["report"]["blocks"] if x["block_id"] == "market-against-fundamentals"][0]
    known = next(c for r in [*b["rows"], *[r for t in b["tabs"] for r in t["rows"]]] for c in r["cells"] if c["state"] == "known"); known["text"] += "0"; perturbs.append(("known cell text", p))
    p = copy.deepcopy(payload); b = [x for x in p["report"]["blocks"] if x["block_id"] == "market-against-fundamentals"][0]
    b["tabs"][2]["rows"][0]["label"] = "X"; perturbs.append(("tab row label", p))
    p = copy.deepcopy(payload); b = [x for x in p["report"]["blocks"] if x["block_id"] == "market-against-fundamentals"][0]
    b["tabs"][0]["columns"][0] += " x"; perturbs.append(("tab column label", p))
    p = copy.deepcopy(payload)
    pp = p["report"]["passports"]; s = next(x for x in pp if x["kind"] == "synthetic")
    for f in s["fields"]:
        if f["name"] == "Locator": f["value"] = "page:99"
    perturbs.append(("passport locator", p))
    p = copy.deepcopy(payload); b = [x for x in p["report"]["blocks"] if x["block_id"] == "market-against-fundamentals"][0]
    gapcell = next((c for r in [*b["rows"], *[r for t in b["tabs"] for r in t["rows"]]] for c in r["cells"] if c["state"] != "known"), None)
    if gapcell is not None:
        gapcell["text"] = "0"; perturbs.append(("gap cell -> 0", p))
    for name, p in perturbs:
        try:
            check(p, case)
        except AssertionError:
            print("  fails:", name)
        else:
            print("  ACCEPTED (bad):", name); fails += 1
sys.exit(1 if fails else 0)
