"""L2 re-check on the real wiring: the term loan is a EUR facility with no FX conversion row
(probe_f_fx.py input). For every period-hop check the helper still downgrades (with the
fix-round-1 kwargs exactly as canonical_gaps passes them), print the facility terms, their
observation_ids, value_id and reason, and the fx_normalised_ids set.
Exit 1 when a downgraded period check carries a fac: term for a non-book-currency facility
(the L2 rule did not hold on the real hop), else 0."""
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from harness2 import build, hops
from deploy_vii.canonical_audit import (absent_input_limitation, conflicting_observation_ids,
                                        fx_normalised_ids, shadowed_account_ids)


def mutate(doc):
    for f in doc["books"][0]["facilities"]:
        f["currency"] = "EUR"


pack, review, definition = build("public", mutate)
_, _, _, recon = hops(pack, review, definition)
book = review.books[0]
fx = fx_normalised_ids(book)
kw = dict(public=True, conflicting=conflicting_observation_ids(book),
          shadowed=shadowed_account_ids(book), normalised=fx)
print("fx_normalised_ids:", sorted(fx))
fac_ids = {f.facility_id for f in book.facilities if f.currency != book.currency}
nodes = {n.construction_id: n for n in recon.historical.constructions}
bad = []
for c in recon.checks:
    if c.status != "BLOCK" or absent_input_limitation(c, **kw) is None:
        continue
    for t in (c.reported, *c.components):
        if t.label in fac_ids or (t.value_id or "").find("fac:") >= 0:
            n = nodes[c.construction_id]
            print(f"  downgraded {c.check_type} node={n.kind}:{n.column_key} term={t.label} amount={t.amount} "
                  f"ids={t.observation_ids} value_id={t.value_id} reason={t.reason}")
            bad.append(c.check_id)
rows = {(v.construction_id, v.series_key): v for v in recon.historical.values}
for (cid, key), v in rows.items():
    if key.startswith("fac:"):
        print("  cell", nodes[cid].column_key, key, v.value.amount, v.value.reason, v.value.observation_ids,
              v.value.normalization_ids)
        break
print("RESULT downgraded FX checks:", len(bad))
sys.exit(1 if bad else 0)
