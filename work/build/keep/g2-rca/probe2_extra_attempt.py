"""Probe 2: on a scratch copy of the settled positive G2 inputs, (a) show the product refuses a
further begin for every planned module, (b) forge an extra pending CP-1 attempt as attacker-written
store bytes (the D1 precedent: Execution._write, tests/test_financial_render.py:285), confirm the
store still reads, and (c) show render_owner_slice refuses it with an owner_render_* ValueError.
Exit 0 iff (a),(b),(c) hold. Usage: python probe2_extra_attempt.py <code-root> <pytest-dir> <scratch>"""
import shutil, sys, time, uuid
from pathlib import Path
code, P, scratch = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(code / "src"))
from deploy_vii.execution import Attempt, Execution, current_inputs  # noqa: E402
import deploy_workflow.owner_rendering as g2  # noqa: E402
src = P / "test_genuine_cp1_model_positiv0/inputs-positive-0"
root = scratch / "probe2-run"
shutil.rmtree(root, ignore_errors=True)
shutil.copytree(src, root)
store, receipt, model = root / "store", root / "owner-run.json", root / "model"
ex = Execution(store)
snap = ex.read()
print("plan attempts:", [(a.module_id, a.number, a.status, bool(a.issues)) for a in snap.attempts])
ok = True
for m in snap.run.requested_modules + ("CP-0",):
    try:
        ex.begin(m); print("begin", m, "ACCEPTED (unexpected)"); ok = False
    except ValueError as e:
        print("begin", m, "refused:", e)
snap = ex.read()
prev = [a for a in snap.attempts if a.module_id == "CP-1"]
extra = Attempt(ticket_id=str(uuid.uuid4()), module_id="CP-1",
                inputs=current_inputs(snap, "CP-1"), number=len(prev),
                repair_of=prev[-1].ticket_id, repair_issues=prev[-1].issues)
ex._write(snap.model_copy(update={"parent": snap.content_hash(),
                                  "attempts": (*snap.attempts, extra)}))
back = Execution(store).read()
print("forged store reads; last attempt:", back.attempts[-1].module_id, back.attempts[-1].status)
ok &= back.attempts[-1].ticket_id == extra.ticket_id
dest = root / "out" / "delivery"; dest.parent.mkdir()
t = time.time()
try:
    g2.render_owner_slice(store, receipt, model, dest); print("RENDERED (defect)"); ok = False
except ValueError as e:
    print("render refused:", str(e)[:160], f"({time.time()-t:.0f}s)")
    ok &= str(e).startswith("owner_render_") and not dest.exists()
sys.exit(0 if ok else 1)
