"""Probe 2: is a CP-3C FP-04 run (lease rev 2 row `cp3c-fp04-refinancing`) matched by any
DELIVERY_SCOPES row? Rulings item 4 Q-S2 says the row ships in Stage 3 with the Q-C2 wiring.
Run from the s3-i4 worktree: PYTHONPATH=src:tests <python> p2_cp3c_scope_refused.py
Exit 0 = refused (gap confirmed), 1 = matched."""
import sys
from deploy_workflow import owner_rendering as g2
from test_owner_rendering import _cp1_model_run

run = _cp1_model_run().model_copy(update={
    "pathway": "covenant_refinancing",
    "requested_modules": ("CP-1", "CP-1A", "CP-2", "CP-2D", "CP-3C"),
})
print("run triple:", run.pathway, tuple(run.requested_modules), run.case_kind)
try:
    scope = g2._scope_of(run)
except ValueError as e:
    print("REFUSED:", e)
    print("cp3c-fp04-refinancing in DELIVERY_SCOPES:", "cp3c-fp04-refinancing" in g2.DELIVERY_SCOPES)
    sys.exit(0)
print("matched", scope.scope_id)
sys.exit(1)
