"""Recompute every derived fact in module_golden.json with exact Decimal and print the receipt.

Usage: python3 -I derive.py [module_golden.json]   (exit 0 = every stored value matches)
Scale rule: every derived fact uses operands printed at the same scale as its own value, so no
rescaling happens (to_scale only guards that and would convert exactly if ever needed).
Ratio results are rounded to 6 decimal places, ROUND_HALF_UP. Other ops are exact.
"""
import json
import sys
from decimal import Decimal, ROUND_HALF_UP

PER_MILLION = {"millions": Decimal(1), "thousands": Decimal("0.001"), "units": Decimal("0.000001")}


def to_scale(value, from_scale, to_scale):
    """Convert a decimal amount between money scales, exactly."""
    if from_scale is None or to_scale is None:
        if from_scale != to_scale:
            raise ValueError("cannot convert between scaled and unscaled values")
        return value
    return value * PER_MILLION[from_scale] / PER_MILLION[to_scale]


def compute(op, operands):
    """operands: list of Decimal already in the target scale."""
    if op == "sum":
        return sum(operands, Decimal(0))
    if op == "difference":
        return operands[0] - operands[1]
    if op == "negate":
        return -operands[0]
    if op == "product":
        out = Decimal(1)
        for x in operands:
            out *= x
        return out
    if op == "ratio":
        return (operands[0] / operands[1]).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    raise ValueError("unknown op " + op)


def evaluate(fact, by_id):
    """Return (Decimal result, receipt lines) for one derived fact."""
    d = fact["derivation"]
    target = fact["scale"]
    vals, lines = [], []
    for oid in d["operands"]:
        o = by_id[oid]
        raw = Decimal(o["value"])
        # ratio operands are compared at one common scale (the first operand's), result unscaled
        tgt = target if d["op"] != "ratio" else by_id[d["operands"][0]]["scale"]
        conv = to_scale(raw, o["scale"], tgt)
        vals.append(conv)
        note = "" if o["scale"] == tgt else f"  [{o['scale']} -> {tgt}]"
        lines.append(f"    {oid} = {raw}{note} -> {conv}")
    return compute(d["op"], vals), lines


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
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "module_golden.json"))
