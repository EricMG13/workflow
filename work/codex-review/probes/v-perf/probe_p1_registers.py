"""P1 probe: one _stage_registers call on the real CZR CP-1 store.

Desired: shared narrative inputs computed once per call. Exits 1 while narrative_inputs runs > 1x.
Counting wrapper calls the real function; results are unchanged.
"""
import sys, time
from pathlib import Path
import deploy_vii.narrative as narrative
import deploy_vii.cp1_workflow as cp1
from deploy_vii.execution import Execution

real = narrative.narrative_inputs
calls = [0]
def counted(*a, **k):
    calls[0] += 1
    return real(*a, **k)
narrative.narrative_inputs = counted
cp1.narrative_inputs = counted
store = Execution(Path(sys.argv[1]))
snap = store.read()
attempt = [a for a in snap.attempts if a.module_id == "CP-1" and len(a.steps) >= 4][0]
pack = store.pack(snap)
t = time.perf_counter()
cp1._stage_registers(store, pack, attempt)
print(f"_stage_registers {time.perf_counter()-t:.2f} s; narrative_inputs calls={calls[0]}")
sys.exit(1 if calls[0] > 1 else 0)
