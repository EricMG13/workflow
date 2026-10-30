"""Simulate the planned audit-hop downgrade on CZR in-process (no repo edit): wrap the
reconcile_financials name canonical_audit uses so a public BLOCK check with no difference, no
conflicting observation term and no FX-normalised term reaches the audit as WARN with the
item-82 prefix. model_readiness keeps the real function. Replays the committed partial
submissions and prints the refusal plus the BLOCK gaps the narrative still carries.
Usage (repo root): PYTHONPATH=src:tests .venv/bin/python <this> <empty-dir>."""
import sys, collections
from pathlib import Path
import deploy_vii.canonical_audit as ca
import deploy_vii.narrative as nar
from deploy_vii.financial_contracts import Observation
from deploy_vii.financial_validation import records
import czr_runs

_real = ca.reconcile_financials
def patched(pack, review, book_id):
    r = _real(pack, review, book_id)
    book = next(b for b in review.books if b.book_id == book_id)
    conflicting = {o.observation_id for o in records(book, Observation) if o.status == "conflicting"}
    public = pack.run.case_kind == "public"
    out = []
    for k in r.checks:
        terms = (k.reported, *k.components)
        if (public and k.status == "BLOCK" and k.difference is None
                and not any(t.normalization is not None for t in terms)
                and not any(t.observation_id in conflicting for t in terms if t.observation_id)):
            missing = "; ".join(f"{t.label} ({t.reason})" for t in terms if t.amount is None)
            k = k.model_copy(update={"status": "WARN", "explanation":
                "Absent input, stated as a limitation on a public filed pack (rulings item 82): "
                + k.explanation + (f"; absent: {missing}" if missing else "")})
        out.append(k)
    return r.model_copy(update={"checks": tuple(out)})
ca.reconcile_financials = patched

seen = {}
_cn = nar.canonical_narrative
def spy(*a, **kw):
    rep = _cn(*a, **kw); seen["n"] = rep; return rep
nar.canonical_narrative = spy
import deploy_vii.downstream_readiness as dr
if hasattr(dr, "canonical_narrative"): dr.canonical_narrative = spy
try:
    czr_runs.czr_closed(Path(sys.argv[1]), Path("cases/czr-2026q2-earnings-update/submissions-partial.json"))
    print("CLOSED")
except BaseException as e:
    print("RAISED", type(e).__name__, str(e)[:400])
n = seen.get("n")
if n is not None:
    print("narrative status:", n.status)
    b = [g for g in n.gaps if g.severity == "BLOCK"]
    print("BLOCK gaps:", len(b), collections.Counter((g.origin, g.description[:70]) for g in b))
    w = [g for g in n.gaps if g.description.startswith("Absent input")]
    print("downgraded WARN gaps:", len(w)); print("sample:", w[0].description[:400] if w else None)
