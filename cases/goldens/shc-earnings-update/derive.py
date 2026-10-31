"""Receipt for every derived value in module_golden.json (exact Decimal, stdlib only).

Run: python3 -I derive.py   (exit 0 only when every derivation and every check agrees)
Stored values are USD millions (printed thousands / 1000, exact); evidence.printed stays in thousands as printed.
"""
import json
import sys
from decimal import Decimal
from pathlib import Path


def apply_op(op, vals):
    if op == "sum":
        return sum(vals, Decimal(0))
    if op == "difference":  # operands[0] - operands[1] - ...
        r = vals[0]
        for v in vals[1:]:
            r -= v
        return r
    if op == "negate":
        return -vals[0]
    if op == "product":
        r = Decimal(1)
        for v in vals:
            r *= v
        return r
    if op == "ratio":
        return vals[0] / vals[1]
    raise ValueError("unknown op " + op)


def parse_printed(s):
    s = s.strip().replace("$", "").replace(",", "").replace(" ", "")
    if s in ("—", "-"):
        return Decimal(0)
    neg = s.startswith("(") and s.endswith(")")
    d = Decimal(s.strip("()"))
    return -d if neg else d


def main():
    here = Path(__file__).resolve().parent
    data = json.loads((here / "module_golden.json").read_text())
    facts = {f["fact_id"]: f for f in data["facts"]}
    bad = 0
    print("== derivations ==")
    for f in data["facts"]:
        d = f.get("derivation")
        if not d:
            continue
        vals = [Decimal(facts[o]["value"]) for o in d["operands"]]
        got = apply_op(d["op"], vals)
        ok = got == Decimal(f["value"])
        # cross-check against the printed change, where the filing prints one
        for e in f.get("evidence", []):
            if parse_printed(e["printed"]) != got * 1000:
                ok = False
        bad += not ok
        print(f"{'OK ' if ok else 'BAD'} {f['fact_id']} = {d['op']}({', '.join(o.split('.', 3)[-1] for o in d['operands'])}) = {got}")

    def v(fid):
        return Decimal(facts[fid]["value"])

    print("== consistency checks (printed subtotals vs printed lines) ==")
    for pe in ("2025-06-30", "2024-06-30"):
        base = "CP-1D.ebitda_reconciliation.%s.amount." + pe
        ni_lines = ["Net income (loss)", "Amortization of intangible assets", "Share-based compensation",
                    "Loss on refinancing of debt", "(Gain) loss on FX and derivatives not designated as hedges, net",
                    "Business optimization expenses", "Professional services relating to EO sterilization facilities",
                    "Illinois EO litigation settlements", "Accretion of asset retirement obligations",
                    "Income tax benefit associated with pre-tax adjustments"]
        s1 = sum((v(base % x) for x in ni_lines), Decimal(0))
        ani = v(base % "Adjusted Net Income")
        s2 = ani + v(base % "Interest expense, net") + v(base % "Depreciation") + v(base % "Income tax provision applicable to Adjusted Net Income")
        ebitda = v(base % "Adjusted EBITDA")
        for name, a, b in ((f"{pe} lines -> Adjusted Net Income", s1, ani), (f"{pe} Adjusted Net Income + 3 lines -> Adjusted EBITDA", s2, ebitda)):
            ok = a == b
            bad += not ok
            print(f"{'OK ' if ok else 'BAD'} {name}: {a} vs printed {b}")
        for what, key in (("segment revenue", "net_revenues"), ("segment income", "segment_income")):
            segs = sum((v(f"CP-1B.period_comparison.{s}.{key}.{pe}") for s in ("Sterigenics", "Nordion", "Nelson Labs")), Decimal(0))
            tot = v(f"CP-1B.period_comparison.Consolidated.{'net_revenues' if key == 'net_revenues' else 'adjusted_ebitda'}.{pe}")
            ok = segs == tot
            bad += not ok
            print(f"{'OK ' if ok else 'BAD'} {pe} sum of {what} vs consolidated {'revenue' if key == 'net_revenues' else 'adjusted EBITDA'}: {segs} vs {tot}")
    rv = v("CP-1B.debt_context.Revolving Credit Facility.total_commitments.2025-06-30")
    lc = v("CP-1B.debt_context.Revolving Credit Facility.letters_of_credit_issued.2025-06-30")
    av = v("CP-1B.debt_context.Revolving Credit Facility.availability.2025-06-30")
    ok = rv - lc == av
    bad += not ok
    print(f"{'OK ' if ok else 'BAD'} revolver commitments {rv} - LCs {lc} = {rv - lc} vs printed availability {av} (USD millions)")
    print("RESULT", "FAIL" if bad else "PASS", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
