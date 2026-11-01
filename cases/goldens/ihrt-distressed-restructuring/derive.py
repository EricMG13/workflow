"""Recompute every derived fact in module_golden.json with exact Decimal and print the receipt.

Usage: python3 -I derive.py [module_golden.json]   (exit 0 = every stored value matches)
Scale rule: operands are converted exactly to units (the same rule as cases/goldens/check.py), the
operation runs at 200 digits, and a money result is converted back to the derived fact's scale.
Ratios are unitless; a percent ratio is multiplied by 100. The result is rounded half-up to the
stored value's decimal places (only ratios can need it).
"""
import decimal
import json
import pathlib
import sys
from decimal import Decimal, ROUND_HALF_UP

CTX = decimal.Context(prec=200)
SCALE_EXP = {None: 0, "units": 0, "thousands": 3, "millions": 6, "billions": 9}


def compute(op, operands):
    """operands: Decimals in units."""
    if op == "sum":
        return sum(operands, Decimal(0))
    if op == "difference":
        return operands[0] - sum(operands[1:], Decimal(0))
    if op == "negate":
        return -operands[0]
    if op == "product":
        out = Decimal(1)
        for x in operands:
            out = CTX.multiply(out, x)
        return out
    if op == "ratio":
        return CTX.divide(operands[0], operands[1])
    raise ValueError("unknown op " + op)


def evaluate(fact, by_id):
    """Return (Decimal result in the fact's own scale and unit, receipt lines)."""
    d = fact["derivation"]
    vals, lines = [], []
    for oid in d["operands"]:
        o = by_id[oid]
        raw = Decimal(o["value"])
        units = raw.scaleb(SCALE_EXP[o["scale"]], CTX)
        vals.append(units)
        note = "" if o["scale"] is None else f"  [{o['scale']}]"
        lines.append(f"    {oid} = {raw}{note} -> {units} units")
    res = compute(d["op"], vals)
    if d["op"] == "ratio":
        if fact["value_type"] == "percent":
            res = res.scaleb(2, CTX)
    else:
        res = res.scaleb(-SCALE_EXP[fact["scale"]], CTX)
    places = max(0, -Decimal(fact["value"]).as_tuple().exponent)
    res = res.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP, context=CTX)
    return res, lines


def main(path):
    g = json.load(open(path))
    by_id = {f["fact_id"]: f for f in g["facts"]}
    bad = 0
    for f in g["facts"]:
        if not f.get("derivation"):
            continue
        res, lines = evaluate(f, by_id)
        ok = Decimal(f["value"]) == res
        bad += not ok
        print(f"{f['fact_id']} = {f['derivation']['op']}(...) = {res} {f['scale']} {'OK' if ok else 'MISMATCH stored ' + f['value']}")
        print("\n".join(lines))
    print("derived facts mismatching:", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else str(pathlib.Path(__file__).with_name("module_golden.json"))))
