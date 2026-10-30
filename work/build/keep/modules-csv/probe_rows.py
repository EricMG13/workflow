"""Run from the lane root: 11 columns, exactly the 16 scoped rows changed, others byte-equal."""
import csv, subprocess, sys
SCOPE = {"CP-1C","CP-1D","CP-2A","CP-2D","CP-2E","CP-2G","CP-2H","CP-3","CP-3C","CP-3D","CP-4","CP-4C","CP-8","CP-DR","CP-L10","CP-OS"}
show = lambda r: subprocess.run(["git","show",f"{r}:docs/MODULES.csv"],capture_output=True,text=True,check=True).stdout.splitlines()
o, n = show("02f7f94"), show("7c1a702")
rows = list(csv.reader(n))
bad = [r[0] for r in rows if len(r) != 11]
changed = {list(csv.reader([b]))[0][0] for a, b in zip(o, n) if a != b}
ok = len(o) == len(n) and not bad and changed == SCOPE
print(len(n), bad, sorted(changed - SCOPE), sorted(SCOPE - changed)); sys.exit(0 if ok else 1)
