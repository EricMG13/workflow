"""Fill and print the derived facts of module_golden.json with exact Decimal.

    python3 -I derive.py          print the receipt only
    python3 -I derive.py --write  also store each derived value in module_golden.json
Ops: sum, difference (first minus the rest), negate, product, ratio. Stdlib only.
"""
import decimal, json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
PATH = HERE / "module_golden.json"
CTX = decimal.Context(prec=200, traps=[decimal.InvalidOperation, decimal.Inexact, decimal.DivisionByZero])


def compute(op, vals):
    if op == "negate":
        return CTX.minus(vals[0])
    if op == "sum":
        t = vals[0]
        for v in vals[1:]:
            t = CTX.add(t, v)
        return t
    if op == "difference":
        t = vals[1]
        for v in vals[2:]:
            t = CTX.add(t, v)
        return CTX.subtract(vals[0], t)
    if op == "product":
        t = vals[0]
        for v in vals[1:]:
            t = CTX.multiply(t, v)
        return t
    if op == "ratio":
        return decimal.Context(prec=200).divide(vals[0], vals[1])
    raise ValueError(op)


def main(write):
    data = json.loads(PATH.read_text(encoding="utf-8"))
    by_id = {f["fact_id"]: f for f in data["facts"]}
    for f in data["facts"]:
        d = f["derivation"]
        if not d:
            continue
        vals = [decimal.Decimal(by_id[o]["value"]) for o in d["operands"]]
        res = compute(d["op"], vals)
        text = format(res, "f")
        print(f"{f['fact_id']} = {d['op']}({', '.join(str(v) for v in vals)}) = {text}")
        for o, v in zip(d["operands"], vals):
            print(f"    {o} = {v}")
        if write:
            f["value"] = text
    if write:
        PATH.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main("--write" in sys.argv[1:])
