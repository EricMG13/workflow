import sys, time, json
from pathlib import Path
from deploy_vii.execution import Execution
from deploy_vii.cp1_workflow import cp1_registers
store = Execution(Path(sys.argv[1]))
snap = store.read()
cp1 = [a for a in snap.attempts if a.module_id == "CP-1" and len(a.steps) >= 4][0]
t = time.perf_counter(); regs = cp1_registers(store, cp1.ticket_id); dt = time.perf_counter() - t
m = regs.module
raw = m.model_dump_json()
print("cp1_registers s", round(dt, 2))
print("module facts", len(m.facts), "claims", len(m.claims), "tables", len(m.tables), "bytes", len(raw))
t = time.perf_counter(); [m.content_hash() for _ in range(5)]; h = (time.perf_counter() - t) / 5
print("module content_hash ms", round(h * 1000, 2))
Path(sys.argv[2]).write_text(raw)
t = time.perf_counter(); p = store.pack(snap); print("Execution.pack ms", round((time.perf_counter()-t)*1000,1))
