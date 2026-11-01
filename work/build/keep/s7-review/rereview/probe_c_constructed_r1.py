"""Attempt 2: a period check built from constructed periods.
Lists the constructions of the public synthetic case (kind, own/stated period, terms, limitation)
and the period-check blockers that are built from other checks or from node.limitation.
Then variant: the q2-2025 segment revenue is 31 (revenue 30) with the q2-2025 revenue account
shadowed as missing - see probe_h - but here the question is only whether any period-hop
downgrade lacks a twin BLOCK at the audit hop: for each prefixed period gap, report whether the
source periods it names carry a BLOCK reconciliation check at the audit hop.
Exit 0 always (inventory)."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from harness2 import PREFIX, build, hops

pack, review, definition = build("public")
audit, period, gate, recon = hops(pack, review, definition)
for n in recon.historical.constructions:
    print(n.kind, n.column_key, "own", n.own_period_id, "stated", n.stated_period_id,
          "terms", [(t.kind, t.reference and t.reference[:24], t.coefficient) for t in n.terms],
          "limitation", n.limitation)
print("period checks:", len(recon.checks), "non-PASS:",
      sorted({(c.check_type, c.status) for c in recon.checks if c.status != "PASS"}))


def drop_q4(doc):
    """Remove every q4-2025 row so the kernel must construct Q4 from FY and three quarters."""
    book = doc["books"][0]
    for key, rows in list(book.items()):
        if isinstance(rows, list) and rows and isinstance(rows[0], dict) and "period_id" in rows[0]:
            book[key] = [r for r in rows if r.get("period_id") != "q4-2025"]


def drop_q4_fy_seg(doc):
    drop_q4(doc)
    seg = next(s for s in doc["books"][0]["segments"] if s["period_id"] == "fy-2025")
    seg["revenue"]["amount"] = "121"


for name, m in (("Q4 constructed", drop_q4), ("Q4 constructed + FY segment 121", drop_q4_fy_seg)):
    try:
        pack, review, definition = build("public", m)
        audit, period, gate, recon = hops(pack, review, definition)
    except Exception as error:  # feasibility probe: report the refusal and continue
        print("==", name, "refused:", type(error).__name__, str(error)[:200])
        continue
    print("==", name, "gate:", gate)
    if recon is not None:
        for n in recon.historical.constructions:
            if n.terms or n.limitation:
                print("  node", n.kind, n.column_key, "terms", len(n.terms), "limitation", n.limitation)
    ab = [g for g in audit.gaps if g.severity == "BLOCK"]
    pb = [g for g in period if g.severity == "BLOCK"]
    print("  audit BLOCK:", [(g.origin, g.description[:70]) for g in ab])
    print("  period BLOCK:", [(g.origin, g.description[:70]) for g in pb])
    print("  period prefixed:", [g.description[len(PREFIX):][:90] for g in period if g.description.startswith(PREFIX)])
