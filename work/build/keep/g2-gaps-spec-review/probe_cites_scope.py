"""Non-empty list cites inside the block-rendered tables vs all oracle tables (cp3d, cp8, cp4)."""
import json
def ne(t): return sum(1 for r in t["rows"] for f in r["facts"] if isinstance(f.get("cites"), list) and f["cites"])
d = json.load(open("cases/cp3d-owner/expected.json")); shown = {tid for tid, _ in d["render"]["blocks"]["market-against-fundamentals"]["tabs"]}
for c, v in d["cases"].items():
    if isinstance(v, dict) and "tables" in v:
        print("cp3d", c, "in block:", sum(ne(t) for t in v["tables"] if t["table_id"] in shown), "all:", sum(ne(t) for t in v["tables"]))
d = json.load(open("cases/cp8-owner/expected.json"))
for c in ("positive", "no_outcome"):
    v = d["cases"][c]; print("cp8", c, "in block:", sum(ne(t) for t in v["tables"] if t["table_id"] == "cp8.what_changed"), "all:", sum(ne(t) for t in v["tables"]))
d = json.load(open("cases/cp4-owner/expected.json")); shown = {t for s in d["render"]["sections"].values() for t in s["tables"]}
for k in ("positive", "gap"):
    v = d[k]["CP-4"]; print("cp4", k, "in sections:", sum(ne(t) for t in v["tables"] if t["table_id"] in shown), "all:", sum(ne(t) for t in v["tables"]))
