"""Probe: the period hop cannot see FX normalisation (PeriodTerm has no normalization field).

An FX-normalised facility cell whose amount is None (missing/unsourced rate, not a conflict)
reaches the period DEBT_TOTAL_EX_LEASES check as a plain PeriodTerm; the helper downgrades it,
while the same term at the audit hop (ReconciliationTerm.normalization set) stays BLOCK.
Exit 1 if the asymmetry exists.
"""
import sys
from decimal import Decimal
from deploy_vii.canonical_audit import absent_input_limitation
from deploy_vii.period_reconciliation import PeriodCheck, PeriodTerm
from deploy_vii.financial_reconciliation import Reconciliation, ReconciliationTerm

print("PeriodTerm fields:", sorted(PeriodTerm.model_fields))
pt = lambda label, amt, oids, reason=None: PeriodTerm.model_construct(
    label=label, value_id=None, amount=amt, coefficient=1, observation_ids=oids, citations=(), reason=reason)
pc = PeriodCheck.model_construct(
    check_id="pc", construction_id="c", check_type="DEBT_TOTAL_EX_LEASES", metric_id="total_debt",
    reported=pt("total_debt", Decimal("100"), ("obs-td",)),
    components=(pt("fac:eur-loan", None, ("obs-eur-carrying",), "FX rate not sourced"),),
    difference=None, status="BLOCK", explanation="Reported value or independent components are unavailable")
rt = lambda label, amt, oid, norm=None, reason=None: ReconciliationTerm.model_construct(
    label=label, observation_id=oid, original_amount=amt, amount=amt, coefficient=1, reason=reason,
    citations=(), normalization=norm)
rc = Reconciliation.model_construct(
    check_id="rc", period_id="p", reported=rt("total_debt", Decimal("100"), "obs-td"),
    components=(rt("eur-loan", None, "obs-eur-carrying", norm="fx-normalisation", reason="FX rate not sourced"),),
    difference=None, status="BLOCK", explanation="Missing reported value or complete independent components")
p = absent_input_limitation(pc, public=True, conflicting=frozenset(), normalised=frozenset({"obs-eur-carrying"}))
a = absent_input_limitation(rc, public=True, conflicting=frozenset(), normalised=frozenset({"obs-eur-carrying"}))
print("period hop:", p)
print("audit hop:", a)
sys.exit(1 if (p is not None and a is None) else 0)
