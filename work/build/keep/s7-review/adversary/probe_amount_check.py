"""Feasibility: does validate_financial_review accept (1) a changed printed amount on a statement
line and (2) an explicit 'missing' account row shadowing a known printed statement line?
Prints the validation issues for each; exit 0 always (feasibility only)."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from harness import build
from deploy_vii.financial_validation import validate_financial_review


def bump(doc):
    book = doc["books"][0]
    line = next(l for l in book["statement_lines"]
                if l["period_id"] == "q2-2025" and l["label"] == "Reported EBITDA")
    line["value"]["amount"] = "8.5"


def shadow(doc):
    book = doc["books"][0]
    line = next(l for l in book["statement_lines"]
                if l["period_id"] == "q2-2025" and l["label"] == "Reported EBITDA")
    book["accounts"].append({"metric_id": "ebitda", "period_id": "q2-2025", "value": {
        "observation_id": "ebitda-shadow-q2", "status": "missing", "amount": None,
        "citations": line["value"]["citations"], "reason": "Not printed in the filing"}})


for name, m in (("bump", bump), ("shadow", shadow)):
    pack, review, _ = build("public", m)
    print(name, "issues:", validate_financial_review(pack, review)[:5])
