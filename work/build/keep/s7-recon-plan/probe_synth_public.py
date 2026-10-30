"""RED-test feasibility probe for the planned change (no repo edit). Runs the synthetic
financial case of tests/test_financial_workflow.py with run.case_kind=<kind> and
segment_disclosure 'partial' (an absent-component structural blocker) to CP-1 promotion.
mode 'today' uses the product as is; mode 'planned' simulates the audit-hop and the
period-reconciliation-hop downgrade (wrapping only the names canonical_audit and canonical_gaps
use). Prints the promotion outcome, narrative status and the BLOCK/downgraded gap counts.
Usage (repo root): PYTHONPATH=src:tests .venv/bin/python <this> <empty-dir> <today|planned> <public|synthetic>"""
import sys, json, collections
from pathlib import Path
import test_financial_workflow as tfw
from deploy_vii.contracts import Run
from deploy_vii.preparation import PreparedPack
from deploy_vii.execution import Execution
root, mode, kind = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
PREFIX = "Absent input, stated as a limitation on a public filed pack (rulings item 82): "
_mp = tfw.make_pack
def make_pack(gap=False):
    p = _mp(gap)
    return PreparedPack(run=p.run.model_copy(update={"case_kind": kind}), sources=p.sources)
tfw.make_pack = make_pack
_fin = tfw.financials
def financials(pack):
    d = _fin(pack)
    d["financial"]["books"][0]["segment_disclosure"]["status"] = "partial"
    return d
tfw.financials = financials
if mode == "planned":
    import deploy_vii.canonical_audit as ca, deploy_vii.canonical_gaps as cg
    from deploy_vii.financial_contracts import Observation
    from deploy_vii.financial_validation import records
    _rf = ca.reconcile_financials
    def rf(pack, review, book_id):
        r = _rf(pack, review, book_id)
        book = next(b for b in review.books if b.book_id == book_id)
        conf = {o.observation_id for o in records(book, Observation) if o.status == "conflicting"}
        out = []
        for k in r.checks:
            t = (k.reported, *k.components)
            if (pack.run.case_kind == "public" and k.status == "BLOCK" and k.difference is None
                    and not any(x.normalization is not None for x in t)
                    and not any(x.observation_id in conf for x in t if x.observation_id)):
                k = k.model_copy(update={"status": "WARN", "explanation": PREFIX + k.explanation})
            out.append(k)
        return r.model_copy(update={"checks": tuple(out)})
    ca.reconcile_financials = rf
    _rp = cg.reconcile_periods
    def rp(pack, review, book_id):
        r = _rp(pack, review, book_id)
        book = next(b for b in review.books if b.book_id == book_id)
        conf = {o.observation_id for o in records(book, Observation) if o.status == "conflicting"}
        out = []
        for k in r.checks:
            t = (k.reported, *k.components)
            if (pack.run.case_kind == "public" and k.status == "BLOCK" and k.difference is None
                    and not any(set(x.observation_ids) & conf for x in t)):
                k = k.model_copy(update={"status": "WARN", "explanation": PREFIX + k.explanation})
            out.append(k)
        return r.model_copy(update={"checks": tuple(out)})
    cg.reconcile_periods = rp
import deploy_vii.narrative as nar
seen = {}
_cn = nar.canonical_narrative
def spy(*a, **kw):
    rep = _cn(*a, **kw); seen["n"] = rep; return rep
nar.canonical_narrative = spy
workflow, raw_qa, score = tfw.quality_ready_case(root)
out = workflow.submit_review(json.dumps(raw_qa))
print("promotion:", out.get("status"), str(out.get("issues") or out.get("error") or "")[:300])
n = seen.get("n")
if n:
    print("narrative status:", n.status)
    print("BLOCK gaps:", collections.Counter((g.origin, g.description[:60]) for g in n.gaps if g.severity == "BLOCK"))
    print("downgraded:", collections.Counter(g.origin for g in n.gaps if g.description.startswith("Absent input")))
store = Execution(root / "store")
a = next(x for x in store.read().attempts if x.module_id == "CP-1")
if a.steps and a.steps[-1].output_sha256 and a.steps[-1].step_id == "quality":
    from deploy_vii.cp1_workflow import CP1Handoff
    h = CP1Handoff.model_validate_json(store.step_output(a.steps[-1].output_sha256))
    print("QA:", h.quality.confidence.qa_status, h.quality.confidence.confidence_score)
heads = {x.module_id: x for x in store.read().heads}
print("CP-1 head:", heads.get("CP-1") and heads["CP-1"].status)
