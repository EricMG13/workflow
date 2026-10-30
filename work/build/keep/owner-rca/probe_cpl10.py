"""Probe: cpl10 genuine positive (argv[1] ignored) under argv[2]. Runs the failing test body with a
traceback, lists the citation mismatches under the test's dict.fromkeys rule and under the frozen
round 3 rule (copied cell: the CP-1 fact's own citations; derived cell and claim: one_per_page),
then reruns the whole test with `_cites` set to the round 3 rule. Exit 0 = the fixed test passes."""
import sys, traceback
from pathlib import Path
import test_owner_cpl10 as t
from deploy_workflow.owners.blank import one_per_page

root = Path(sys.argv[2]); root.mkdir(parents=True, exist_ok=True)
base = t.promoted(root / "promoted")
rc = 0
orig_cites = t._cites
for case in (t.POSITIVE, t.LIMITED):
    print("=== case", case)
    t._cites = orig_cites
    try:
        t.test_closed_run_equals_the_oracle_cell_for_cell(base, root / f"orig-{case}", case); print("PASS orig")
    except Exception:
        print("FAIL orig"); traceback.print_exc(limit=-2)
    store, receipt, _ = t._closed(base, root / f"diag-{case}", case)
    heads = {h.module_id: h for h in store.read().heads}
    module = store.head_module(heads["CP-L10"])
    cp1 = {f.label: f for f in store.head_module(heads["CP-1"]).facts if f.table_id == "T4.10"}
    got = {f.fact_id: f for f in module.facts}
    old_bad, new_bad = [], []
    for w in t.EXPECTED["cases"][case]["facts"]:
        copied = w.get("copied_from_cp1"); labels = [copied] if copied else (w.get("derives_from") or [])
        old = t._cites(cp1, labels)
        new = cp1[copied].citations if copied else one_per_page(tuple(c for l in labels for c in cp1[l].citations))
        if got[w["fact_id"]].citations != old: old_bad.append(w["fact_id"])
        if got[w["fact_id"]].citations != new: new_bad.append(w["fact_id"])
    print("facts: dict.fromkeys mismatches", len(old_bad), old_bad[:8]); print("facts: round-3 mismatches", len(new_bad), new_bad[:8])
    cl_old, cl_new = [], []
    for claim, w in zip(module.claims, t.EXPECTED["cases"][case]["claims"], strict=True):
        labels = [m.removeprefix("{{CP1_CITATIONS:").removesuffix("}}") for m in w["citations"]]
        if claim.citations != t._cites(cp1, labels): cl_old.append(claim.claim_id)
        if claim.citations != one_per_page(tuple(c for l in labels for c in cp1[l].citations)): cl_new.append(claim.claim_id)
    print("claims: dict.fromkeys mismatches", cl_old); print("claims: round-3 mismatches", cl_new)
    t._cites = lambda cp1, labels: (cp1[labels[0]].citations if len(labels) == 1 and labels[0] in cp1 and False else one_per_page(tuple(c for l in labels for c in cp1[l].citations)))
    try:
        t.test_closed_run_equals_the_oracle_cell_for_cell(base, root / f"fixed-{case}", case); print("PASS fixed (one_per_page everywhere)"); pass
    except Exception:
        print("FAIL fixed"); traceback.print_exc(limit=-2); rc = 1
    if new_bad or cl_new: rc = 1
sys.exit(rc)
