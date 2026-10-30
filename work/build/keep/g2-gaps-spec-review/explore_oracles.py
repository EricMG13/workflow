import json,sys
from pathlib import Path
R=Path(sys.argv[1])/"cases"
o=lambda n: json.loads((R/n/"expected.json").read_text())
cp3d=o("cp3d-owner"); cp8=o("cp8-owner"); cp4=o("cp4-owner")
print("cp3d top", list(cp3d)); print("cp3d render keys", list(cp3d["render"]))
print("cp3d rails", json.dumps(cp3d["render"].get("rails"))[:800])
print("cp8 top", list(cp8)); print("cp8 render keys", list(cp8["render"]))
print("cp8 rails", json.dumps(cp8["render"].get("rails"))[:800])
print("cp8 lines_positive", cp8["render"]["lines_positive"])
print("cp4 render keys", list(cp4["render"]))
print("cp4 lims", json.dumps(cp4["render"]["limitations_rail_module_limitations"])[:600])
print("cp4 gap CP-4 keys", list(cp4["gap"]["CP-4"]))
print("cp4 inh", json.dumps(cp4["gap"]["CP-4"]["inherited_limitations"])[:600])
# cp4 known facts without text not covered by literals
for key in ("positive","gap"):
    lits=cp4["render"]["displayed_literals"][key]
    sectabs={t for s in cp4["render"]["sections"].values() for t in s["tables"]}
    unc=[]; f0=None
    for t in cp4[key]["CP-4"]["tables"]:
        if t["table_id"] not in sectabs: continue
        for r in t["rows"]:
            for f in r["facts"]:
                f0=f0 or list(f)
                if f["status"]=="known" and f.get("text") is None:
                    col=f["fact_id"].rsplit(".",1)[1]
                    if col not in lits.get(t["table_id"],{}): unc.append((t["table_id"],r["row_id"],col,f.get("shown")))
    print(key,"fact keys",f0); print(key,"known numeric cells w/o literal:",len(unc),unc[:12])
