"""End-to-end version of probe_h_shadow.py: the synthetic financial case run through the real CP-1
workflow (tests/test_financial_workflow.quality_ready_case) as case_kind=<kind>.
Variant 'disagree': the q2-2025 segment revenue observation is 31 while revenue is 30 (a real
1.0 SEGMENT_REVENUE disagreement; printed statement lines are untouched, so the extraction
coverage check still passes). Variant 'shadow': the same, plus an explicit 'missing' revenue
account for q2-2025 that shadows the known printed IS revenue line.
(A first attempt that edited the printed EBITDA line was refused by the workflow's extraction
coverage check, 'Uncovered extracted statement line', so the disagreement is put in the segment.)
Usage from W: PYTHONPATH=src:tests <lane>/.venv/bin/python probe_h_e2e.py <empty-dir> <kind> <disagree|shadow>
Prints the promotion outcome, the QA status and the BLOCK gaps of the narrative. Exit 1 when a
public 'shadow' run promotes (attack succeeds), else 0."""
import json, sys
from collections import Counter
from pathlib import Path
import test_financial_workflow as tfw
import deploy_vii.narrative as nar
import deploy_vii.downstream_readiness as dr
from deploy_vii.contracts import Run
from deploy_vii.execution import Execution
from deploy_vii.preparation import PreparedPack
from deploy_vii.cp1_workflow import CP1Handoff

root, kind, variant = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
real_pack, real_fin = tfw.make_pack, tfw.financials


def make_pack(gap=False):
    p = real_pack(gap)
    return PreparedPack(run=p.run.model_copy(update={"case_kind": kind}), sources=p.sources)


def financials(pack):
    doc = real_fin(pack)
    book = doc["financial"]["books"][0]
    seg = next(s for s in book["segments"] if s["period_id"] == "q2-2025")
    seg["revenue"]["amount"] = "31"
    if variant == "shadow":
        line = next(l for l in book["statement_lines"]
                    if l["period_id"] == "q2-2025" and l["label"] == "Revenue")
        book["accounts"].append({"metric_id": "revenue", "period_id": "q2-2025", "value": {
            "observation_id": "revenue-shadow-q2", "status": "missing", "amount": None,
            "citations": line["value"]["citations"], "reason": "Not printed in the filing"}})
    return doc


tfw.make_pack, tfw.financials = make_pack, financials
seen = {}
real_n = nar.canonical_narrative
def spy(*a, **k):
    seen["n"] = real_n(*a, **k)
    return seen["n"]
nar.canonical_narrative = spy
dr.canonical_narrative = spy
workflow, raw_qa, _ = tfw.quality_ready_case(root)
out = workflow.submit_review(json.dumps(raw_qa))
print("promotion:", out.get("status"), str(out.get("issues") or "")[:300])
n = seen.get("n")
if n is not None:
    print("narrative:", n.status, "BLOCK:", Counter(g.origin for g in n.gaps if g.severity == "BLOCK"))
store = Execution(root / "store")
heads = [h for h in store.read().heads if h.module_id == "CP-1"]
if heads:
    module = store.head_module(heads[0])
    print("CP-1 head limitation[0]:", module.limitations[0][:160])
    att = next(a for a in store.read().attempts if a.module_id == "CP-1")
    h = CP1Handoff.model_validate_json(store.step_output(att.steps[-1].output_sha256))
    print("QA:", h.quality.confidence.qa_status, h.quality.confidence.confidence_score)
sys.exit(1 if (kind == "public" and variant == "shadow" and out.get("status") == "valid") else 0)
