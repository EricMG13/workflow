"""P4: run p4_dump.py under base (5a1d2e2f, extracted to ./base/src) and head src; every field must
match except field 3 (statement_issues: base refuses the new optional BS item that the fixture
book carries). Exit 0 = undeclared output byte-identical to base."""
import os
import pathlib
import subprocess
import sys

here = pathlib.Path(__file__).parent
wt = pathlib.Path.cwd()
out = {}
for side, src in (("base", here / "base" / "src"), ("head", wt / "src")):
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": f"{src}:{wt / 'tests'}"}
    r = subprocess.run([sys.executable, str(here / "p4_dump.py")], env=env, capture_output=True,
                       text=True, check=True)
    out[side] = [line.split() for line in r.stdout.splitlines()]
bad = []
for b, h in zip(out["base"], out["head"], strict=True):
    for i, (x, y) in enumerate(zip(b, h, strict=True)):
        if x != y and i not in (1, 4):  # 1 = combined hash, 4 = statement_issues (fields shift by name+combined)
            bad.append((b[0], i))
    print(b[0], "differs only in statement_issues" if not [k for k in bad if k[0] == b[0]] else "DIFFERS")
sys.exit(1 if bad else 0)
