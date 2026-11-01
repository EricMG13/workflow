"""Re-review harness (read-only). Same as keep/s7-review/adversary/harness.py but wires the
fix-round-1 signature: _calculation_gaps(..., shadowed=, normalised=) exactly as canonical_gaps
does. Run from W with PYTHONPATH=src:tests and the lane venv python."""
import json
from collections import Counter
from pathlib import Path

from deploy_vii.canonical_audit import (
    ABSENT_INPUT_PREFIX,
    DefinitionReview,
    canonical_audit,
    conflicting_observation_ids,
    fx_normalised_ids,
    shadowed_account_ids,
)
from deploy_vii.canonical_gaps import _calculation_gaps
from deploy_vii.canonical_kpis import canonical_kpis
from deploy_vii.financial_adapter import kernel_registers
from deploy_vii.financial_contracts import FinancialReview, Observation
from deploy_vii.financial_validation import records
from deploy_vii.period_reconciliation import reconcile_periods
from deploy_vii.preparation import PreparedPack

PREFIX = ABSENT_INPUT_PREFIX
FIXTURE = Path("/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/work/build/keep/s7-review/adversary/fixture")


def build(kind, mutate=None):
    base = PreparedPack.model_validate_json((FIXTURE / "pack.json").read_text())
    pack = PreparedPack(run=base.run.model_copy(update={"case_kind": kind}), sources=base.sources)
    doc = json.loads((FIXTURE / "review.json").read_text())
    doc["pack_sha256"] = pack.content_hash()
    if mutate is not None:
        mutate(doc)
    review = FinancialReview.model_validate_json(json.dumps(doc))
    ddoc = json.loads((FIXTURE / "definition.json").read_text())
    known = {o.observation_id for o in records(review.books[0], Observation)}
    for a in ddoc["assessments"]:
        a["observation_ids"] = [i for i in a["observation_ids"] if i in known]
    definition = DefinitionReview.model_validate_json(json.dumps(ddoc))
    definition = definition.model_copy(update={"financial_review_sha256": review.content_hash()})
    return pack, review, definition


def hops(pack, review, definition):
    audit = canonical_audit(pack, review, definition)
    book = next(b for b in review.books if b.book_id == definition.book_id)
    period, gate, recon = [], None, None
    try:
        kernel_registers(pack, review, book.book_id)
    except ValueError as error:
        gate = str(error)
    if gate is None:
        kpis = canonical_kpis(pack, review, book.book_id)
        recon = reconcile_periods(pack, review, book.book_id)
        period = list(_calculation_gaps(
            kpis, recon, public=pack.run.case_kind == "public",
            conflicting=conflicting_observation_ids(book),
            shadowed=shadowed_account_ids(book),
            normalised=fx_normalised_ids(book),
        ))
    return audit, period, gate, recon


def summary(label, audit, period, gate):
    blocks = [g for g in audit.gaps if g.severity == "BLOCK"] + [g for g in period if g.severity == "BLOCK"]
    pre = [g for g in audit.gaps if g.description.startswith(PREFIX)] + [g for g in period if g.description.startswith(PREFIX)]
    print(f"== {label}")
    print("  calculation_gate:", gate)
    print("  BLOCK gaps:", len(blocks), Counter(g.origin for g in blocks))
    for g in blocks:
        print("    BLOCK", g.origin, "|", g.description[:150])
    print("  prefixed WARN gaps:", len(pre), Counter(g.origin for g in pre))
    return blocks, pre
