"""Exact-Decimal derivations for tdg-credit-snapshot. Run: python3 -I derive.py
Recomputes every derivation in module_golden.json, prints a receipt, and runs tie-outs.
Exit 1 on any mismatch."""
import json
import pathlib
import sys
from decimal import Decimal

HERE = pathlib.Path(__file__).resolve().parent


def compute(op, values):
    """sum: a+b+...; difference: first minus the rest; negate; product; ratio: first / second."""
    v = [Decimal(x) for x in values]
    if op == "sum":
        return sum(v, Decimal(0))
    if op == "difference":
        return v[0] - sum(v[1:], Decimal(0))
    if op == "negate":
        return -v[0]
    if op == "product":
        out = Decimal(1)
        for x in v:
            out *= x
        return out
    if op == "ratio":
        return v[0] / v[1]
    raise ValueError(op)


def val_of(facts, fid):
    for f in facts:
        if f["fact_id"] == fid:
            return f["value"]
    raise KeyError(fid)


def find(facts, topic, subject, field, pe):
    hits = [f for f in facts if f["topic"] == topic and f["subject"] == subject and f["field"] == field and f["period_end"] == pe]
    assert len(hits) == 1, (topic, subject, field, pe, len(hits))
    return Decimal(hits[0]["value"])


def main():
    facts = json.loads((HERE / "module_golden.json").read_text(encoding="utf-8"))["facts"]
    bad = 0
    for f in facts:
        d = f["derivation"]
        if not d:
            continue
        got = compute(d["op"], [val_of(facts, o) for o in d["operands"]])
        ok = got == Decimal(f["value"])
        bad += not ok
        print(("OK " if ok else "BAD"), f["fact_id"], d["op"], "=", got, "stored", f["value"])
    pe = "2024-12-28"
    ties = []
    tr = [find(facts, "debt_stack", f"Term loan Tranche {x}", "principal_outstanding", pe) for x in "IJKL"]
    ties.append(("term loan tranches sum to Term loans", sum(tr), find(facts, "debt_stack", "Term loans", "principal_outstanding", pe)))
    names = ["Term loans", "5.50% 2027 Notes", "2028 Secured Notes", "4.625% 2029 Notes", "2029 Secured Notes", "4.875% 2029 Notes", "2030 Secured Notes", "2031 Secured Notes", "2032 Secured Notes", "2033 Secured Notes", "Government refundable advances", "Finance lease obligations"]
    ties.append(("components excl securitization sum to printed total", sum(find(facts, "debt_stack", n, "principal_outstanding", pe) for n in names), find(facts, "debt_totals", "Debt excluding securitization facility", "principal_outstanding", pe)))
    ms = [f for f in facts if f["topic"] == "maturity_schedule" and f["field"] == "scheduled_maturity"]
    total = [Decimal(f["value"]) for f in ms if f["subject"] == "Total"][0]
    ties.append(("maturity years sum to printed total", sum(Decimal(f["value"]) for f in ms if f["subject"] != "Total"), total))
    ties.append(("cash plus availability equals printed cash liquidity", find(facts, "liquidity", "Cash and cash equivalents", "balance", pe) + find(facts, "revolver", "Revolving credit facility", "availability", pe), find(facts, "liquidity", "Cash liquidity (cash plus revolver availability)", "amount", pe)))
    ties.append(("reconciled 2024-09-30 gross less leases equals schedule total", find(facts, "maturity_schedule", "Reconciliation: gross debt excl. securitization less finance leases", "amount", "2024-09-30"), total))
    ties.append(("total gross incl securitization equals printed total plus securitization principal", find(facts, "debt_totals", "Total gross principal including securitization facility", "principal_outstanding", pe), find(facts, "debt_totals", "Debt excluding securitization facility", "principal_outstanding", pe) + find(facts, "debt_stack", "Trade receivable securitization facility", "principal_outstanding", pe)))
    for name, a, b in ties:
        ok = a == b
        bad += not ok
        print(("OK " if ok else "BAD"), name, a, b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
