"""Attempt 5: can model-written input reach run.case_kind?
(1) The review contracts the model writes refuse an extra 'case_kind' / 'run' key (extra=forbid).
(2) A review written for the synthetic pack cannot be consumed with a public pack: canonical_audit
    refuses it because the review binds the pack sha (and the definition binds the review).
(3) Only Run carries case_kind; Run is fixed in the PreparedPack at Execution.create.
Exit 0 when all three hold (attack fails), else 1."""
import json, sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pathlib import Path
from pydantic import ValidationError
from harness2 import FIXTURE
from deploy_vii.canonical_audit import DefinitionReview, canonical_audit
from deploy_vii.financial_contracts import FinancialReview
from deploy_vii.preparation import PreparedPack

ok = True
doc = json.loads((FIXTURE / "review.json").read_text())
for key, value in (("case_kind", "public"), ("run", {"case_kind": "public"})):
    try:
        FinancialReview.model_validate_json(json.dumps({**doc, key: value}))
        print("(1) FinancialReview accepted extra", key); ok = False
    except ValidationError:
        print("(1) FinancialReview refuses extra", key)
d = json.loads((FIXTURE / "definition.json").read_text())
try:
    DefinitionReview.model_validate_json(json.dumps({**d, "case_kind": "public"}))
    print("(1) DefinitionReview accepted case_kind"); ok = False
except ValidationError:
    print("(1) DefinitionReview refuses case_kind")
base = PreparedPack.model_validate_json((FIXTURE / "pack.json").read_text())
public = PreparedPack(run=base.run.model_copy(update={"case_kind": "public"}), sources=base.sources)
review = FinancialReview.model_validate_json(json.dumps(doc))
definition = DefinitionReview.model_validate_json((FIXTURE / "definition.json").read_text())
try:
    canonical_audit(public, review, definition)
    print("(2) synthetic-bound review consumed with a public pack"); ok = False
except ValueError as error:
    print("(2) refused:", str(error)[:120])
src = Path("src/deploy_vii")
hits = [f"{p}:{i}" for p in src.rglob("*.py") for i, l in enumerate(p.read_text().splitlines(), 1)
        if "case_kind" in l and ("=" in l.split("case_kind", 1)[1][:3] or "case_kind:" in l)]
print("(3) case_kind assignments/declarations in src:", hits)
sys.exit(0 if ok else 1)
