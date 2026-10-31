"""Capture the composed pack, FinancialReview and DefinitionReview that canonical_audit consumes
when the synthetic financial case (tests/test_financial_workflow.py) runs to CP-1 QA.
Usage from W: PYTHONPATH=src:tests <lane>/.venv/bin/python capture.py <empty-dir> <out-dir>
Writes pack.json, review.json, definition.json into <out-dir>. Exit 0 when captured."""
import json, sys
from pathlib import Path
import test_financial_workflow as tfw
import deploy_vii.canonical_audit as ca

root, out = Path(sys.argv[1]), Path(sys.argv[2])
cap = {}
real = ca.canonical_audit
def spy(pack, review, definition):
    cap.update(pack=pack, review=review, definition=definition)
    return real(pack, review, definition)
ca.canonical_audit = spy
import deploy_vii.canonical_gaps as cg
cg.canonical_audit = spy
workflow, raw_qa, score = tfw.quality_ready_case(root)
assert cap, "canonical_audit not reached"
out.mkdir(parents=True, exist_ok=True)
for name in ("pack", "review", "definition"):
    (out / f"{name}.json").write_text(cap[name].model_dump_json())
print("captured", cap["pack"].run.case_kind, len(cap["review"].books[0].statement_lines))
