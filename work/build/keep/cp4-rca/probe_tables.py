"""Replay test_owner_cp4.py::test_tables_claims_and_limitations_equal_the_oracle step by step on
copies of the genuine closed stores (argv[1] = stores root). Exit 1 if any step fails."""
import importlib, json, sys, traceback
from pathlib import Path
from deploy_vii.execution import Execution

t = importlib.import_module("test_owner_cp4")
stage1, EXPECTED = t.stage1, t.EXPECTED
root = Path(sys.argv[1])
bad = 0
for case in ("positive", "gap", "gap_false_same_definition"):
    module, attempt, inputs = t._cp4(Execution(root / case / "store"))
    want = EXPECTED[t.WANT_KEY[case]]["CP-4"]
    facts = {f.fact_id: f for f in module.facts}
    ctx = stage1._ctx(inputs)
    steps = []
    steps.append(("133 table_order", lambda: [x.table_id for x in module.tables] == EXPECTED["table_order"]))
    bounds = {}
    for tbl, w in zip(module.tables, want["tables"], strict=True):
        def chk(tbl=tbl, w=w):
            bounds[tbl.table_id] = stage1._check_table(tbl, w, facts, ctx)
            return True
        steps.append((f"137 _check_table {tbl.table_id}", chk))
    steps.append(("140 bound count", lambda: (sum(bounds.values()), 11 if t.WANT_KEY[case] == "positive" else 9)))
    got = [{"claim_id": c.claim_id, "text": c.text, "cites": stage1._cites(c.citations), "limitation": c.limitation} for c in module.claims]
    steps.append(("150 claims", lambda: got == want["claims"]))
    steps.append(("151 settled_limitations", lambda: (list(module.limitations), want["settled_limitations"])))
    steps.append(("152 inherited_limitations", lambda: (list(module.inherited_limitations), want["inherited_limitations"])))
    steps.append(("153 settled_module_inputs", lambda: ([i.input_id for i in module.inputs], want["settled_module_inputs"])))
    steps.append(("154 attempt_inputs", lambda: ([i.input_id for i in attempt.inputs], want["attempt_inputs_in_order"])))
    print(f"===== {case}")
    for name, fn in steps:
        try:
            r = fn()
        except AssertionError:
            bad += 1
            print(f"FAIL {name}:", traceback.format_exc().strip().splitlines()[-3:])
            continue
        if isinstance(r, tuple):
            ok = r[0] == r[1]
            if not ok:
                bad += 1
                print(f"FAIL {name}:\n  got ={json.dumps(r[0], ensure_ascii=False)}\n  want={json.dumps(r[1], ensure_ascii=False)}")
            else:
                print(f"ok   {name}")
        elif r:
            print(f"ok   {name}")
        else:
            bad += 1
            print(f"FAIL {name}")
    # G2's rule (test_owner_rendering._cp4_expected_limitations) applied to the inherited list
    cp1 = Execution(root / case / "store").head_module(t._head(Execution(root / case / "store"), "CP-1"))
    settled = want["settled_limitations"]
    rule = list(dict.fromkeys(x for x in [*want["inherited_limitations"]["literal_head_from_CP-0"], *cp1.limitations, *cp1.inherited_limitations] if x not in settled))
    print("rule-built inherited == genuine:", rule == list(module.inherited_limitations), len(rule))
    if rule != list(module.inherited_limitations):
        bad += 1
        print("  rule   =", rule); print("  genuine=", list(module.inherited_limitations))
sys.exit(1 if bad else 0)
