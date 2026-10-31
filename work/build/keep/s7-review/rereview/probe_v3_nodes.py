"""Which period-hop constructions does the fy-2025 revenue shadow reach, and with which cell ids.
Prints each construction's kind/column/own/stated/terms and its acct:revenue cell (amount, reason,
observation_ids) for the 'shadow' variant of probe_v3_detail.py. Exit 0 always (inventory)."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from harness2 import build, hops


def shadow(doc):
    s = next(s for s in doc["books"][0]["segments"] if s["period_id"] == "fy-2025")
    s["revenue"]["amount"] = "121"
    book = doc["books"][0]
    l = next(l for l in book["statement_lines"] if l["period_id"] == "fy-2025" and l["item_id"] == "revenue")
    book["accounts"].append({"metric_id": "revenue", "period_id": "fy-2025", "value": {
        "observation_id": "shadow-revenue-fy", "status": "missing", "amount": None,
        "citations": l["value"]["citations"], "reason": "Not printed"}})


pack, review, definition = build("public", shadow)
_, _, _, recon = hops(pack, review, definition)
h = recon.historical
rows = {(v.construction_id, v.series_key): v for v in h.values}
for n in h.constructions:
    cell = rows.get((n.construction_id, "acct:revenue"))
    print(n.construction_id[:28], n.kind, n.column_key, "own", n.own_period_id, "stated", n.stated_period_id,
          "terms", [(t.kind, (t.reference or "")[:20], t.coefficient) for t in n.terms],
          "column", n.construction_id in h.columns,
          "| revenue", None if cell is None else (cell.value.amount, cell.value.reason, cell.value.observation_ids))
