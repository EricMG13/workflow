"""E2: known facts in cases/*-owner oracles whose text or shown holds 'G#'. argv[1]=tree. Exit 1 if any outside CP-8 outcome."""
import json, sys, glob
hits = []
def walk(o, path, case):
    if isinstance(o, dict):
        if "fact_id" in o and o.get("status") == "known":
            for k in ("text", "shown"):
                if "G#" in (o.get(k) or ""):
                    hits.append((path, o["fact_id"], k))
        for k, v in o.items(): walk(v, path, case)
    elif isinstance(o, list):
        for v in o: walk(v, path, case)
for p in sorted(glob.glob(sys.argv[1] + "/cases/*-owner/expected.json")):
    walk(json.load(open(p)), p.split("/cases/")[1], None)
for h in hits: print(h)
sys.exit(1 if any(h[1] != "cp8.what_changed.outcome.value" for h in hits) else 0)
