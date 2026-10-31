"""Item 82 fix 2 probe: the cash-scope blocker (alone, joined with an absent-input blocker,
or quoted by a parent) stays BLOCK at HEAD of claude/s7-absent-input-3; a plain absent input
still downgrades. Run with W/src on sys.path. Exit 0 = all hold."""
import sys
from decimal import Decimal
from deploy_vii.canonical_audit import absent_input_limitation
from deploy_vii.period_reconciliation import PeriodCheck, PeriodTerm

def term(label, amount, ids):
    return PeriodTerm.model_construct(label=label, amount=None if amount is None else Decimal(amount),
                                      coefficient=1, observation_ids=ids, citations=(), reason=None)

def check(expl):
    return PeriodCheck.model_construct(check_id="pc", construction_id="c",
        reported=term("Reported", "10", ("r",)),
        components=(term("Unassessed cash bridge: q1", None, ()), term("B", "4", ("b",))),
        difference=None, status="BLOCK", explanation=expl)

none = frozenset()
def run(expl):
    return absent_input_limitation(check(expl), public=True, conflicting=none, shadowed=none, normalised=none)

cases = {
    "alone": ("Cash scope differs across source periods: fy-2025", None),
    "joined": ("Unassessed cash bridge: q1; Cash scope differs across source periods: h1-2025", None),
    "quoted": ("ltm-2025: Cash scope differs across source periods: h1-2025", None),
}
ok = True
for name, (expl, want) in cases.items():
    got = run(expl)
    print(name, "->", got)
    ok &= got is want
plain = run("Unassessed cash bridge: q1")
print("plain absent ->", plain)
ok &= plain is not None
sys.exit(0 if ok else 1)
