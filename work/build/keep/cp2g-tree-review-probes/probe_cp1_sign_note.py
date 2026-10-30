"""Probe (genuine CP-0 + CP-1 only): for each case in argv[2:], drive cp2g_runs.promoted and
print the CP-1 T4.10 LTM cash_interest/cash_taxes status and limitation as CP-2G selects them.
argv[1] = repo copy root. Exit 0 iff every case has known + a limitation containing
'sign normalised' for both metrics."""
import sys, tempfile
from pathlib import Path
root = Path(sys.argv[1]); sys.path[:0] = [str(root / "src"), str(root / "tests")]
import os; os.chdir(root)
import cp2g_runs as runs
from deploy_workflow.owners import cp2g
from deploy_vii.execution import Execution
ok = True
for case in sys.argv[2:]:
    with tempfile.TemporaryDirectory() as d:
        wf, _ = runs.promoted(case, Path(d))
        store = Execution(Path(d) / "store")
        head = next(h for h in store.read().heads if h.module_id == "CP-1")
        base = cp2g.select_cp1(store.head_module(head).facts)
        for m in ("cash_interest", "cash_taxes"):
            f = base[m]
            print(case, m, f.status, repr(f.limitation), f.value_class)
            ok &= f.status == "known" and bool(f.limitation) and "sign normalised" in f.limitation.split("; ")
sys.exit(0 if ok else 1)
