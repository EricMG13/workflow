"""Attempt 4: a term whose amount is None while a sibling observation for the same metric and
period conflicts. The q2-2025 IS revenue statement line is made 'conflicting' (alternatives 30
and 31, same located citation) and an explicit 'missing' revenue account shadows it, so the
reconciliation terms carry the missing account id, not the conflicting id.
Also checks statically that every Observation-typed field of FinancialBook rows lies in a register
that canonical_audit._positions walks (so any conflict yields an independent BLOCK gap).
Exit 0 when a BLOCK gap still remains on the public case (attack fails), else 1."""
import sys, typing, types
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from harness import PREFIX, build, hops, summary
from deploy_vii.financial_contracts import FinancialBook, Observation

REGISTERS = {"accounts", "addbacks", "segments", "kpis", "facilities", "facility_fx_conversions",
             "pro_forma", "statement_lines", "balance_movements"}


def observation_fields(model, seen=None):
    seen = seen or set()
    found = set()
    for name, field in model.model_fields.items():
        stack = [field.annotation]
        while stack:
            t = stack.pop()
            if t is Observation:
                found.add(name)
            elif isinstance(t, type) and hasattr(t, "model_fields") and t not in seen:
                seen.add(t)
                if observation_fields(t, seen):
                    found.add(name)
            stack.extend(typing.get_args(t))
    return found


uncovered = observation_fields(FinancialBook) - REGISTERS
print("FinancialBook fields holding Observations outside _positions registers:", uncovered or "none")


def mutate(doc):
    book = doc["books"][0]
    line = next(l for l in book["statement_lines"]
                if l["period_id"] == "q2-2025" and l["label"] == "Revenue")
    cites = line["value"]["citations"]
    line["value"] = {"observation_id": line["value"]["observation_id"], "status": "conflicting",
                     "amount": None, "citations": cites, "reason": "Two printed revenue figures",
                     "alternatives": [
                         {"amount": "30", "citations": cites, "explanation": "statement"},
                         {"amount": "31", "citations": cites, "explanation": "release"}]}
    book["accounts"].append({"metric_id": "revenue", "period_id": "q2-2025", "value": {
        "observation_id": "revenue-shadow-q2", "status": "missing", "amount": None,
        "citations": cites, "reason": "Not printed"}})


audit, period, gate, _ = hops(*build("public", mutate))
blocks, pre = summary("public: conflicting printed revenue + shadowing missing account", audit, period, gate)
for g in pre[:4]:
    print("   WARN", g.origin, "|", g.description[len(PREFIX):][:160])
sys.exit(0 if blocks else 1)
