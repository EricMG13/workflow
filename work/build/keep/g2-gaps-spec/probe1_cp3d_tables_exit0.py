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
    n = C.assert_table_cites(payload, "CP-3D", E["cases"][case]["tables"])
    assert n >= 1
    return n


for case in ("positive", "gap_no_recovery", "gap_no_market"):
    pack = base._pack(case)
    view = C.view_with(pack.run, [base._module(case)])
    payload = C.payload_of(view)
    n = check(payload, case)
    print(case, "accepts;", n, "non-empty cites checked over all tables")
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
    def drop_entry(p, pred):
        facts = {f["fact_id"]: f for t in E["cases"][case]["tables"] for r in t["rows"] for f in r["facts"]}
        idx = p["report"]["index"]["facts"]
        hit = [e for e in idx if e["coord"]["module_id"] == "CP-3D" and pred(facts.get(e["coord"]["fact_id"]))]
        assert hit
        idx.remove(hit[0])
    p = copy.deepcopy(payload); drop_entry(p, lambda f: f is not None and not f["cites"])
    perturbs.append(("index entry of a fact whose oracle cites are [] removed (review M2)", p))
    p = copy.deepcopy(payload); drop_entry(p, lambda f: f is not None and f["status"] != "known")
    perturbs.append(("index entry of a gap fact removed", p))
    p = copy.deepcopy(payload); idx = p["report"]["index"]["facts"]
    e = next(e for e in idx if e["coord"]["module_id"] == "CP-3D"); idx.append(copy.deepcopy(e))
    perturbs.append(("index entry duplicated", p))
    for name, p in perturbs:
        try:
            check(p, case)
        except AssertionError:
            print("  fails:", name)
        else:
            print("  ACCEPTED (bad):", name); fails += 1
sys.exit(1 if fails else 0)
