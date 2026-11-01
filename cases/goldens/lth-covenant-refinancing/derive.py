"""Recompute every derived fact in module_golden.json with exact Decimal and print the receipt.

Run: python3 -I derive.py   (from this directory). Exit 1 if any stored value differs.
"""
import json
import pathlib
import sys
from decimal import Decimal

here = pathlib.Path(__file__).resolve().parent
facts = {f["fact_id"]: f for f in json.loads((here / "module_golden.json").read_text())["facts"]}
bad = 0
for f in facts.values():
    d = f["derivation"]
    if not d:
        continue
    v = [Decimal(facts[o]["value"]) for o in d["operands"]]
    if d["op"] == "sum":
        r = sum(v[1:], v[0])
    elif d["op"] == "difference":
        r = v[0] - sum(v[1:], Decimal(0))
    else:
        raise SystemExit(f"unsupported op {d['op']}")
    ok = r == Decimal(f["value"])
    bad += not ok
    sym = " + " if d["op"] == "sum" else " - "
    print(f"{'OK ' if ok else 'BAD'} {f['fact_id']}: {sym.join(str(x) for x in v)} = {r} (stored {f['value']})")
sys.exit(1 if bad else 0)
