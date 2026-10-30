import importlib, sys
from pathlib import Path
sys.path.insert(0, sys.argv[2])
t = importlib.import_module("test_owner_cp4")
stores = Path(sys.argv[1])
orig = t._cp4
def run(case, mutate):
    def patched(store):
        m, a, i = orig(store)
        if mutate:
            lim = list(m.inherited_limitations)
            cp1 = store.head_module(t._head(store, "CP-1"))
            drop = next(x for x in lim if x in cp1.limitations or x in cp1.inherited_limitations)
            lim.remove(drop)
            m = m.model_copy(update={"inherited_limitations": lim})
        return m, a, i
    t._cp4 = patched
    t.test_tables_claims_and_limitations_equal_the_oracle({case: (stores/case/"store", None)}, case)
bad = 0
for case in ("positive","gap","gap_false_same_definition"):
    run(case, False); print("unmutated ok", case)
    try: run(case, True); print("MUTANT SURVIVED", case); bad = 1
    except AssertionError: print("mutant killed", case)
sys.exit(bad)
