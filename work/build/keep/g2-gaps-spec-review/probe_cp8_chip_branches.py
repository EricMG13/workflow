"""Which cp8 what_changed oracle facts exercise each chip branch, and what the page lines carry."""
import json, sys
E = json.load(open("cases/cp8-owner/expected.json"))
for case in ("positive", "no_outcome"):
    (t,) = [t for t in E["cases"][case]["tables"] if t["table_id"] == "cp8.what_changed"]
    for r in t["rows"]:
        f = r["facts"][0]
        print(case, f["fact_id"], f["status"], "calc=", f.get("calculation_id"), "cites=", len(f["cites"]) if isinstance(f["cites"], list) else f["cites"], f.get("value_class"))
