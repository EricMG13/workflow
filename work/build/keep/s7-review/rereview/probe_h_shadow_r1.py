"""Attempt: a present, printed value that disagrees is turned into an 'absent input' WARN by an
explicit 'missing' account row that shadows the known printed statement line (effective_accounts
gives explicit accounts precedence, statement_validation.py:329-341).
Hop-level twin of probe_h_e2e.py (which proves the CP-1 promotion end to end).

Input: the synthetic case, q2-2025 segment revenue 31 against revenue 30 (a real 1.0
SEGMENT_REVENUE disagreement). 'disagree' keeps only that; 'shadow' adds an explicit revenue
account for q2-2025 with status missing, while the book still holds the known printed IS revenue
line. Also shows that a guard set (explicit accounts with no amount whose (period, metric) has a
known printed statement account) names the shadow id that every downgraded audit-hop check cites.
Exit 1 when public 'shadow' leaves no BLOCK gap while public 'disagree' blocks (attack succeeds)."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from harness2 import PREFIX, build, hops, summary
from deploy_vii.statement_validation import statement_accounts


def disagree(doc):
    seg = next(s for s in doc["books"][0]["segments"] if s["period_id"] == "q2-2025")
    seg["revenue"]["amount"] = "31"


def shadow(doc):
    disagree(doc)
    book = doc["books"][0]
    line = next(l for l in book["statement_lines"]
                if l["period_id"] == "q2-2025" and l["label"] == "Revenue")
    book["accounts"].append({"metric_id": "revenue", "period_id": "q2-2025", "value": {
        "observation_id": "revenue-shadow-q2", "status": "missing", "amount": None,
        "citations": line["value"]["citations"], "reason": "Not printed in the filing"}})


results = {}
for kind in ("public", "synthetic"):
    for name, m in (("disagree", disagree), ("shadow", shadow)):
        pack, review, definition = build(kind, m)
        audit, period, gate, _ = hops(pack, review, definition)
        blocks, pre = summary(f"{kind} {name}", audit, period, gate)
        results[kind, name] = len(blocks)
        if kind == "public" and name == "shadow":
            book = review.books[0]
            printed = {(r.period_id, r.metric_id): r.value.amount for r in statement_accounts(book)
                       if r.value.amount is not None}
            print("   printed q2 revenue still in the book:", printed.get(("q2-2025", "revenue")))
            guard = {a.value.observation_id for a in book.accounts
                     if a.value.amount is None and (a.period_id, a.metric_id) in printed}
            print("   guard set:", guard)
            for c in audit.reconciliation.checks:
                if c.status == "BLOCK" and c.period_id == "q2-2025":
                    ids = {t.observation_id for t in (c.reported, *c.components)}
                    print("   downgraded audit check", c.check_type, c.metric_id,
                          "cites guard id:", bool(ids & guard))
            for g in pre[:3]:
                print("   WARN", g.origin, "|", g.description[len(PREFIX):][:160])
print("RESULT", results)
sys.exit(1 if results["public", "disagree"] > 0 and results["public", "shadow"] == 0 else 0)
