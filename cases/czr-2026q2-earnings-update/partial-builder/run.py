import sys, time, json, os
sys.path[:0] = [__import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), "../../..")) + "/tests", __import__("os").path.abspath(__import__("os").path.join(__import__("os").path.dirname(__file__), "../../..")) + "/src"]
from pathlib import Path
import czr_runs
from deploy_workflow.owner_workflow import OwnerWorkflow
root = Path(sys.argv[1]); sub = Path(sys.argv[2])
_real = OwnerWorkflow.read_inputs
count = [0]
def spy(self):
    r = _real(self)
    count[0] += 1
    (root / f"read-{count[0]}-{self._binding.step_id}.txt").write_text(r["body"])
    return r
OwnerWorkflow.read_inputs = spy
t = time.time()
try:
    r = czr_runs.czr_closed(root, sub)
    print("CLOSED", r)
except BaseException as e:
    import traceback; traceback.print_exc(limit=-3); print("RAISED", type(e).__name__, str(e)[:6000])
print("wall", round(time.time() - t, 1), "s")
