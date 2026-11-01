"""M1 via the period hop: a shadowed CHILD quarter of a derived YTD period.

Input (public synthetic case + one derived period): h1-2025, a YTD with component_period_ids
[q1-2025, q2-2025], whose only printed line is IS EBIT 12.6, while q1 + q2 printed EBIT are
6.25 + 6.25 = 12.5 (a real 0.1 disagreement, tolerance 0.05). EBIT is a FLOW_METRIC that only
REPORTED_DERIVED_PERIOD (period hop) and FY_QUARTERS compare; FY_QUARTERS does not see a YTD.
'base'  : no shadow.            Expect the H1 REPORTED_DERIVED_PERIOD ebit check BLOCK (difference).
'shadow': + explicit missing ebit account for q2-2025 (printed q2 EBIT 6.25 is still in the book).
Prints BLOCK gaps, the downgraded ebit check, its terms' ids, and every check at either hop whose
terms cite the shadow id. Exit 1 when public 'base' blocks on the ebit disagreement and public
'shadow' leaves no BLOCK gap that cites or stems from it (the disagreement is fully downgraded)."""
import copy
import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from harness2 import PREFIX, build, hops, summary
from deploy_vii.canonical_audit import (absent_input_limitation, conflicting_observation_ids,
                                        fx_normalised_ids, shadowed_account_ids)

SHADOW = "shadow-ebit-q2-2025"


def add_h1(doc):
    book = doc["books"][0]
    q2 = next(p for p in book["periods"] if p["period_id"] == "q2-2025")
    h1 = copy.deepcopy(q2)
    h1.update(period_id="h1-2025", period_type="YTD", fiscal_quarter=2, start_date="2025-01-01",
              end_date="2025-06-30", day_count=181, component_period_ids=["q1-2025", "q2-2025"])
    book["periods"].insert(book["periods"].index(q2) + 1, h1)
    line = copy.deepcopy(next(l for l in book["statement_lines"]
                              if l["period_id"] == "q2-2025" and l["item_id"] == "ebit"))
    line["period_id"] = "h1-2025"
    line["value"]["observation_id"] = "IS-operating-profit-ebit-h1-2025"
    line["value"]["amount"] = "12.6"
    book["statement_lines"].append(line)


def shadow(doc):
    add_h1(doc)
    book = doc["books"][0]
    q2 = next(l for l in book["statement_lines"] if l["period_id"] == "q2-2025" and l["item_id"] == "ebit")
    book["accounts"].append({"metric_id": "ebit", "period_id": "q2-2025", "value": {
        "observation_id": SHADOW, "status": "missing", "amount": None,
        "citations": q2["value"]["citations"], "reason": "Not printed in the filing"}})


def term_ids(c):
    out = set()
    for t in (c.reported, *c.components):
        out |= set(getattr(t, "observation_ids", ()) or ())
        if getattr(t, "observation_id", None):
            out.add(t.observation_id)
    return out


res = {}
for name, m in (("base", add_h1), ("shadow", shadow)):
    try:
        pack, review, definition = build("public", m)
        audit, period, gate, recon = hops(pack, review, definition)
    except Exception as error:  # report a refusal (fail-closed) instead of hiding it
        print("==", name, "REFUSED", type(error).__name__, str(error)[:300])
        res[name] = None
        continue
    blocks, pre = summary(f"public {name}", audit, period, gate)
    res[name] = len(blocks)
    book = review.books[0]
    kw = dict(public=True, conflicting=conflicting_observation_ids(book),
              shadowed=shadowed_account_ids(book), normalised=fx_normalised_ids(book))
    print("   shadowed:", sorted(kw["shadowed"]))
    checks = list(audit.reconciliation.checks) + (list(recon.checks) if recon else [])
    for c in checks:
        if c.metric_id == "ebit" and c.status != "PASS":
            print(f"   ebit check {c.check_type} status={c.status} diff={c.difference} "
                  f"downgraded={absent_input_limitation(c, **kw) is not None}")
            for t in (c.reported, *c.components):
                print(f"      term {t.label} amount={t.amount} ids={term_ids(type('x', (), {'reported': t, 'components': ()})) } reason={t.reason}")
    citing = [(c.check_type, c.status) for c in checks if SHADOW in term_ids(c)]
    print("   checks citing the shadow id:", citing)
print("RESULT", res)
sys.exit(1 if res.get("base") and res.get("shadow") == 0 else 0)
