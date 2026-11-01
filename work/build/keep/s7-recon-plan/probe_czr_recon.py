"""Run the committed CZR partial submissions to the QA refusal, capturing the source
reconciliation report and the financial review the canonical audit consumed; classify every
BLOCK check under the proposed absent-input predicate (difference is None, no conflicting
observation term, no FX-normalised term, explanation in the absent-input allow-list).
Usage (repo root): PYTHONPATH=src:tests .venv/bin/python <this> <empty-dir>. Exit 0 always
after printing; it asserts nothing about the product."""
import sys, json, collections
from pathlib import Path
import deploy_vii.canonical_audit as ca
from deploy_vii.financial_contracts import Observation
from deploy_vii.financial_validation import records
import czr_runs

cap = {}
_real = ca.reconcile_financials
def spy(pack, review, book_id):
    r = _real(pack, review, book_id)
    cap["report"], cap["review"], cap["book_id"] = r, review, book_id
    return r
ca.reconcile_financials = spy
try:
    czr_runs.czr_closed(Path(sys.argv[1]), Path("cases/czr-2026q2-earnings-update/submissions-partial.json"))
    print("CLOSED (unexpected)")
except BaseException as e:
    print("RAISED", type(e).__name__, str(e)[:300])
rep, review = cap["report"], cap["review"]
book = next(b for b in review.books if b.book_id == cap["book_id"])
conflicting = {o.observation_id for o in records(book, Observation) if o.status == "conflicting"}
print("conflicting observations in book:", len(conflicting))
print("addback_disclosure:", book.addback_disclosure.status, "segment_disclosure:", book.segment_disclosure.status)
c = collections.Counter(); ncf = set()
for k in rep.checks:
    if k.status != "BLOCK": continue
    terms = (k.reported, *k.components)
    conf = any(t.observation_id in conflicting for t in terms if t.observation_id)
    fx = any(t.normalization is not None for t in terms)
    c[(k.check_type, k.difference is not None, conf, fx)] += 1
    if k.check_type == "NCF_IDENTITY": ncf.add(k.explanation)
print("BLOCK checks by (type, has_difference, conflicting_term, fx_term):")
for key, v in sorted(c.items()): print("  ", v, key)
print("NCF_IDENTITY explanations:")
for e in sorted(ncf): print("   ", e)
print("all statuses:", collections.Counter(k.status for k in rep.checks))
