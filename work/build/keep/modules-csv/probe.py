import csv
import io
import subprocess
import sys

BASE = "02f7f94"
SCOPE = {"CP-1C", "CP-1D", "CP-2A", "CP-2D", "CP-2E", "CP-2G", "CP-2H", "CP-3", "CP-3C",
         "CP-3D", "CP-4", "CP-4C", "CP-8", "CP-DR", "CP-L10", "CP-OS"}
new_raw = open("docs/MODULES.csv", newline="").read()
old_raw = subprocess.run(["git", "show", f"{BASE}:docs/MODULES.csv"], capture_output=True,
                         text=True, check=True).stdout
new = list(csv.reader(io.StringIO(new_raw)))
old = list(csv.reader(io.StringIO(old_raw)))
bad = [r[0] for r in new if len(r) != 11]
print("rows", len(new), "bad column counts:", bad)
assert not bad and len(new) == len(old) and new[0] == old[0]
changed = []
for o, n in zip(old, new):
    assert o[0] == n[0]
    for col, (a, b) in enumerate(zip(o, n)):
        if a != b:
            changed.append((n[0], old[0][col]))
for m, c in changed:
    print("changed", m, c)
outside = {m for m, _ in changed} - SCOPE
print("modules changed:", len({m for m, _ in changed}), "outside scope:", sorted(outside))
untouched_cols = {c for _, c in changed} & {"module", "responsibility", "lane", "assigned_sections"}
print("identity columns changed:", sorted(untouched_cols))
sys.exit(1 if outside or untouched_cols else 0)
