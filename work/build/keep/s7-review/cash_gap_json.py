"""Print the CZR BLOCK gaps' JSON after the item 82 change (field discovery for the test 3 fix).
Usage (build worktree root): PYTHONPATH=src:tests <venv python> <this> <empty dir>"""
import sys
from pathlib import Path
import deploy_vii.narrative as narrative, deploy_vii.downstream_readiness as dr
import deploy_vii.canonical_audit as ca
import czr_runs
cap = {}
real_n, real_r = narrative.canonical_narrative, ca.reconcile_financials
def spy_n(*a, **k):
    cap["n"] = real_n(*a, **k); return cap["n"]
def spy_r(*a, **k):
    cap["r"] = real_r(*a, **k); return cap["r"]
narrative.canonical_narrative = dr.canonical_narrative = spy_n
ca.reconcile_financials = spy_r
try:
    czr_runs.czr_closed(Path(sys.argv[1]), czr_runs.SUBMISSIONS.parent / "submissions-partial.json")
except RuntimeError as e:
    print("raised:", str(e)[:120])
ids = {c.check_id: (c.check_type, c.period_id, c.metric_id) for c in cap["r"].checks}
for g in cap["n"].gaps:
    if g.severity == "BLOCK":
        j = g.model_dump_json()
        print(g.origin, "|", j[:900])
        print("   check refs:", [v for k, v in ids.items() if k in j])
