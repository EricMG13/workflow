"""V3 detail: fy-2025 revenue shadowed by an explicit missing account (+ fy segment 121).
Lists every period-hop check that is BLOCK with no difference, whether the helper downgrades it,
and its terms' observation ids, so a downgrade caused by the shadow but not citing it shows.
Exit 1 when a downgraded period check exists in 'shadow' that is PASS/computed in 'base'."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from harness2 import build, hops
from deploy_vii.canonical_audit import (absent_input_limitation, conflicting_observation_ids,
                                        fx_normalised_ids, shadowed_account_ids)


def seg(doc):
    s = next(s for s in doc["books"][0]["segments"] if s["period_id"] == "fy-2025")
    s["revenue"]["amount"] = "121"


def shadow(doc):
    seg(doc)
    book = doc["books"][0]
    l = next(l for l in book["statement_lines"] if l["period_id"] == "fy-2025" and l["item_id"] == "revenue")
    book["accounts"].append({"metric_id": "revenue", "period_id": "fy-2025", "value": {
        "observation_id": "shadow-revenue-fy", "status": "missing", "amount": None,
        "citations": l["value"]["citations"], "reason": "Not printed"}})


state = {}
for name, m in (("base", seg), ("shadow", shadow)):
    pack, review, definition = build("public", m)
    audit, period, gate, recon = hops(pack, review, definition)
    book = review.books[0]
    kw = dict(public=True, conflicting=conflicting_observation_ids(book),
              shadowed=shadowed_account_ids(book), normalised=fx_normalised_ids(book))
    state[name] = {c.check_id: c for c in recon.checks}
    print("==", name, "shadowed:", sorted(kw["shadowed"]))
    for c in recon.checks:
        if c.status == "BLOCK":
            lim = absent_input_limitation(c, **kw)
            print(f"  {c.check_type:26} {c.metric_id:18} {c.construction_id[:28]:28} diff={c.difference} "
                  f"downgraded={lim is not None} expl={c.explanation[:70]!r}")
            if lim is not None:
                for t in (c.reported, *c.components):
                    print(f"      term {t.label[:30]:30} amount={t.amount} ids={t.observation_ids} reason={t.reason}")
bad = [cid for cid, c in state["shadow"].items()
       if c.status == "BLOCK" and c.difference is None and cid in state["base"]
       and state["base"][cid].status != "BLOCK"
       and absent_input_limitation(c, public=True, conflicting=frozenset(), shadowed=frozenset({"shadow-revenue-fy"})) is not None]
print("downgraded only because of the shadow:", [(state['shadow'][b].check_type, state['shadow'][b].metric_id, state['base'][b].status) for b in bad])
sys.exit(1 if bad else 0)
