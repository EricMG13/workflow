"""Probe (no genuine run): diff the CP-2G read body of the saved genuine positive receipt
(argv[1] = owner-receipt.json) against cases/cp2g-owner/cp2g-view-tree.json positive, path by path.
Exit 0 = equal; 1 = differences printed."""
import json, sys
sys.path[:0] = ["src", "tests"]
import view_tree
from deploy_workflow.owner_workflow import OwnerRunReceipt
r = OwnerRunReceipt.model_validate_json(open(sys.argv[1], "rb").read())
body = next(x.body for x in r.input_reads if x.binding.module_id == "CP-2G")
got, want = view_tree.entry(body), view_tree.load("cp2g")["positive"]
diffs = []
def walk(g, w, p):
    if type(g) != type(w): diffs.append((p, g, w)); return
    if isinstance(g, dict):
        if list(g) != list(w): diffs.append((p + " keys", list(g), list(w)))
        for k in g:
            if k in w: walk(g[k], w[k], f"{p}.{k}")
    elif isinstance(g, list):
        if len(g) != len(w): diffs.append((p + " shapes", json.dumps(g)[:400], json.dumps(w)[:400]))
        for i, (a, b) in enumerate(zip(g, w)): walk(a, b, f"{p}[{i}]")
    elif g != w: diffs.append((p, g, w))
walk(got, want, "")
for d in diffs: print(d)
parsed = json.loads(body)
for k in ("cp1_facts", "cp1d_facts", "upstream"):
    print(k, json.dumps([e for e in parsed[k] if any(v is None for v in e.values())][:3], ensure_ascii=False)[:600] if isinstance(parsed[k], list) else "")
sys.exit(1 if diffs else 0)
