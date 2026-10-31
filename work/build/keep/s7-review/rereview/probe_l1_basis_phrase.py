"""L1 second phrase (CHILD_BASIS_DIFFERENCE_BLOCKER): can it ever sit in a BLOCK explanation?
Static: every source site that builds the phrase sets "status": "WARN" in the same update dict.
Dynamic: across the public synthetic variants used in this re-review, no BLOCK check at either hop
has the phrase in its explanation. Exit 1 if either fails (phrase could keep a BLOCK), else 0."""
import re
import sys
from pathlib import Path
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from deploy_vii.canonical_audit import CHILD_BASIS_DIFFERENCE_BLOCKER as P
from harness2 import build, hops

bad = []
for f in Path("src/deploy_vii").rglob("*.py"):
    text = f.read_text()
    for m in re.finditer(re.escape(P.strip()), text):
        if f.name == "canonical_audit.py":
            continue
        window = text[max(0, m.start() - 200):m.start()]
        ok = '"status": "WARN"' in window
        print(f"{f}:{text[:m.start()].count(chr(10)) + 1} status WARN in same update: {ok}")
        if not ok:
            bad.append(str(f))


def seg_fy(doc):
    next(s for s in doc["books"][0]["segments"] if s["period_id"] == "fy-2025")["revenue"]["amount"] = "121"


for name, m in (("baseline", None), ("fy segment 121", seg_fy)):
    audit, period, gate, recon = hops(*build("public", m))
    checks = list(audit.reconciliation.checks) + list(recon.checks if recon else ())
    hit = [c.check_type for c in checks if c.status == "BLOCK" and P in c.explanation]
    print(name, "BLOCK checks carrying the phrase:", hit)
    bad += hit
print("RESULT", bad or "phrase never in a BLOCK explanation")
sys.exit(1 if bad else 0)
