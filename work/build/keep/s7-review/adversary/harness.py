"""Shared harness for the s7 adversary probes (read-only; no repo edit).

Builds the synthetic financial case of tests/test_financial_workflow.py as a pack with
run.case_kind=<kind>, applies a mutation to the submitted financial review, and runs the real
audit hop (canonical_audit) and the real period hop (_calculation_gaps on canonical_kpis and
reconcile_periods, exactly as canonical_gaps wires it). Returns the gap lists.
Run from W with PYTHONPATH=src:tests and the lane venv python.
"""
import json
from collections import Counter
from pathlib import Path

from deploy_vii.canonical_audit import (
    ABSENT_INPUT_PREFIX,
    DefinitionReview,
    canonical_audit,
    conflicting_observation_ids,
)
from deploy_vii.canonical_gaps import _calculation_gaps
from deploy_vii.canonical_kpis import canonical_kpis
from deploy_vii.financial_adapter import kernel_registers
from deploy_vii.financial_contracts import FinancialReview, Observation
from deploy_vii.financial_validation import records
from deploy_vii.period_reconciliation import reconcile_periods
from deploy_vii.preparation import PreparedPack

PREFIX = ABSENT_INPUT_PREFIX


FIXTURE = Path(__file__).resolve().parent / "fixture"


def build(kind, mutate=None):
    """The captured composed synthetic case (capture.py) with case_kind=kind; mutate edits the
    review JSON dict in place before it is re-validated."""
    base = PreparedPack.model_validate_json((FIXTURE / "pack.json").read_text())
    pack = PreparedPack(run=base.run.model_copy(update={"case_kind": kind}), sources=base.sources)
    doc = json.loads((FIXTURE / "review.json").read_text())
    doc["pack_sha256"] = pack.content_hash()  # the review binds the pack it was written for
    if mutate is not None:
        mutate(doc)
    review = FinancialReview.model_validate_json(json.dumps(doc))
    ddoc = json.loads((FIXTURE / "definition.json").read_text())
    known = {o.observation_id for o in records(review.books[0], Observation)}
    for a in ddoc["assessments"]:  # drop ids a mutation removed from the book
        a["observation_ids"] = [i for i in a["observation_ids"] if i in known]
    definition = DefinitionReview.model_validate_json(json.dumps(ddoc))
    # the definition review binds the financial review it was written for
    definition = definition.model_copy(update={"financial_review_sha256": review.content_hash()})
    return pack, review, definition


def hops(pack, review, definition):
    audit = canonical_audit(pack, review, definition)
    book = next(b for b in review.books if b.book_id == definition.book_id)
    period = []
    gate = None
    try:
        kernel_registers(pack, review, book.book_id)
    except ValueError as error:
        gate = str(error)
    recon = None
    if gate is None:
        kpis = canonical_kpis(pack, review, book.book_id)
        recon = reconcile_periods(pack, review, book.book_id)
        period = list(
            _calculation_gaps(
                kpis,
                recon,
                public=pack.run.case_kind == "public",
                conflicting=conflicting_observation_ids(book),
            )
        )
    return audit, period, gate, recon


def summary(label, audit, period, gate):
    blocks = [g for g in audit.gaps if g.severity == "BLOCK"] + [
        g for g in period if g.severity == "BLOCK"
    ]
    pre = [g for g in audit.gaps if g.description.startswith(PREFIX)] + [
        g for g in period if g.description.startswith(PREFIX)
    ]
    print(f"== {label}")
    print("  calculation_gate:", gate)
    print("  BLOCK gaps:", len(blocks), Counter(g.origin for g in blocks))
    for g in blocks:
        print("    BLOCK", g.origin, "|", g.description[:150])
    print("  prefixed WARN gaps:", len(pre), Counter(g.origin for g in pre))
    return blocks, pre
