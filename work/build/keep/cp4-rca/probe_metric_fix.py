"""Cause 1 and 2 fix probe on the genuine stores (argv[1]): metric = the bound CP-1 fact
(s1a.figure_fact over the store's CP-1 head, as cp4_runs.metric_ref), and inherited compared by
the oracle rule (as test_owner_rendering._cp4_expected_limitations). Exit 1 if anything fails."""
import importlib, sys
from pathlib import Path
from deploy_vii.execution import Execution

t = importlib.import_module("test_owner_cp4")
runs, s1a, stage1, EXPECTED = t.runs, t.s1a, t.stage1, t.EXPECTED
bad = 0
for case in ("positive", "gap", "gap_false_same_definition"):
    store = Execution(Path(sys.argv[1]) / case / "store")
    module, attempt, inputs = t._cp4(store)
    up = inputs.upstream
    cp1 = store.head_module(t._head(store, "CP-1"))
    metric = s1a.figure_fact(cp1.facts, runs.METRIC)
    idx = [f.fact_id for f in up.facts].index(metric.fact_id)
    print(f"== {case}: upstream.facts={len(up.facts)} facts[0]={up.facts[0].fact_id} bound={metric.fact_id} at index {idx}")
    want = EXPECTED[t.WANT_KEY[case]]["CP-4"]
    facts = {f.fact_id: f for f in module.facts}
    ctx = stage1._ctx(inputs)
    ctx["metric"] = up.facts[idx]
    ctx["metric_row"] = up.rows[(metric.table_id, metric.row_id)]
    try:
        bound = sum(stage1._check_table(x, w, facts, ctx) for x, w in zip(module.tables, want["tables"], strict=True))
        print("  bound", bound, "want", 11 if t.WANT_KEY[case] == "positive" else 9)
        bad += bound != (11 if t.WANT_KEY[case] == "positive" else 9)
    except AssertionError as e:
        import traceback; traceback.print_exc(); bad += 1
    rule = want["inherited_limitations"]
    settled = want["settled_limitations"]
    exp = list(dict.fromkeys(x for x in [*rule["literal_head_from_CP-0"], *cp1.limitations, *cp1.inherited_limitations] if x not in settled))
    ok = list(module.inherited_limitations) == exp
    print("  inherited by rule:", ok); bad += not ok
sys.exit(1 if bad else 0)
