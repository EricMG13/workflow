"""Merge survey_*.json: print every (builder, table, field) whose known text equals a text that
prose.issues validated (outside report_view), or that holds a reserved character."""
import glob, json, sys
rows = {}
for p in sorted(glob.glob(sys.argv[1] + "/survey_*.json")):
    for k, v in json.load(open(p)).items():
        r = rows.setdefault(k, {"validated_by": set(), "eq": 0, "reserved": set()})
        r["validated_by"] |= set(v["validated_by"]); r["eq"] += v["equals_runtext"]
        r["reserved"] |= set(v["reserved"])
for k, r in sorted(rows.items()):
    vb = sorted(x for x in r["validated_by"] if x not in ("deploy_vii.report_view", "deploy_vii.execution", "deploy_vii.envelope", "deploy_vii.narrative_projection", "deploy_vii.cp5_integrity"))
    if vb or r["reserved"]:
        print(k, "| validated_by:", vb, "| eq_runtext:", r["eq"], "| reserved:", [t[:60] for t in sorted(r["reserved"])][:2])
