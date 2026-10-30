"""Probe: only the six base.operands.{cash_interest,cash_taxes}.limitation leaves and _note differ."""
import json, sys
old = json.load(open(sys.argv[1])); new = json.load(open(sys.argv[2]))
diffs = []
def walk(a, b, p):
    if isinstance(a, dict) and isinstance(b, dict):
        if list(a) != list(b): diffs.append((p, "keys")); return
        for k in a: walk(a[k], b[k], p + [k])
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): diffs.append((p, "len")); return
        for i, (x, y) in enumerate(zip(a, b)): walk(x, y, p + [i])
    elif a != b: diffs.append((p, (a, b)))
walk(old, new, [])
for d in diffs: print(d)
expected = {(c, m) for c in ("positive", "gap", "cp1d_blocked") for m in ("cash_interest", "cash_taxes")}
got = set()
ok = True
for p, v in diffs:
    if p == ["_note"]: continue
    if p[-1] == "limitation" and v == ("NoneType", "str") and "operands" in p:
        got.add((p[0], p[-2])); continue
    ok = False
sys.exit(0 if ok and got == expected and len(diffs) == 7 else 1)
