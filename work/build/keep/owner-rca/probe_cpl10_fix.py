"""Probe: the proposed test fix for test_owner_cpl10.py, applied to an in-memory copy of the test
module (the checkout is not touched): a copied cell expects its CP-1 fact's own citations, a derived
cell and a claim `one_per_page` of the cited CP-1 facts' citations. Runs the whole cell-for-cell
test for positive and limited on one genuine promotion (argv[2] = work dir). Exit 0 = both pass."""
import sys, traceback, types
from pathlib import Path
src = open("tests/test_owner_cpl10.py").read()
old_fact = 'citations = _cites(cp1, [copied] if copied else w.get("derives_from") or [])'
new_fact = 'citations = cp1[copied].citations if copied else _cites(cp1, w.get("derives_from") or [])'
old_cites = "    return tuple(dict.fromkeys(c for label in labels for c in cp1[label].citations))"
new_cites = "    from deploy_workflow.owners.blank import one_per_page\n    return one_per_page(tuple(c for label in labels for c in cp1[label].citations))"
assert src.count(old_fact) == 1 and src.count(old_cites) == 1
mod = types.ModuleType("test_owner_cpl10_fixed"); mod.__file__ = str(Path("tests/test_owner_cpl10.py").resolve())
exec(compile(src.replace(old_fact, new_fact).replace(old_cites, new_cites), mod.__file__, "exec"), mod.__dict__)
root = Path(sys.argv[2]); root.mkdir(parents=True, exist_ok=True)
base = mod.promoted(root / "promoted")
rc = 0
for case in (mod.POSITIVE, mod.LIMITED):
    try:
        mod.test_closed_run_equals_the_oracle_cell_for_cell(base, root / f"fixed-{case}", case); print("PASS fixed", case)
    except Exception:
        rc = 1; print("FAIL fixed", case); traceback.print_exc(limit=-2)
sys.exit(rc)
