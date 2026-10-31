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
EXPECTED_REFUSAL = (
    "submission not valid: invalid ['CP-1 QA Blocked: confidence 39 (Insufficient Information); "
    "a Blocked handoff is not promoted']"
)
t = time.time()
try:
    r = czr_runs.czr_closed(root, sub)
    print("CLOSED", r)
except BaseException as e:
    # Only the recorded CP-1 QA refusal is the expected partial outcome; anything else fails.
    if not (type(e) is RuntimeError and str(e) == EXPECTED_REFUSAL):
        raise
    import traceback; traceback.print_exc(limit=-3); print("RAISED", type(e).__name__, str(e)[:6000])
finally:
    print("wall", round(time.time() - t, 1), "s")
