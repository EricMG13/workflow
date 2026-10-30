import sys
from pathlib import Path as _P
sys.path[:0] = [str(_P.cwd() / "src"), str(_P.cwd() / "tests")]
"""Plan, create, per-step inputs, and the unsettled-head error text (CZR driver review)."""
import tempfile
from pathlib import Path

import czr_runs
from deploy_vii.registry import plan
from deploy_workflow.owner_workflow import OWNER_SPECS, OwnerWorkflow

pack = czr_runs.make_pack()
planned = plan(pack.run.requested_modules)
print("plan", planned)
assert planned == ("CP-0", "CP-1", "CP-1A", "CP-2", "CP-5"), planned
with tempfile.TemporaryDirectory() as d:
    wf = OwnerWorkflow.create(Path(d) / "store", pack, publication_directory=Path(d) / "model")
    print("create ok; plan", wf._plan, "first step", wf._binding.step_id)
    steps = {(m, s.step_id): s.inputs for m in planned if m in OWNER_SPECS for s in OWNER_SPECS[m].steps}
    for k, v in steps.items():
        print(k, v)
    assert steps[("CP-1", "financials")] == "none", "financials declares inputs"
    try:
        czr_runs._settled_facts(wf)("CP-1")
    except RuntimeError as e:
        print("unsettled head error:", e, "| names a figure:", "FIG" in str(e))
