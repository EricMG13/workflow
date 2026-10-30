"""Probe: cp4c genuine case argv[1] (positive|gap) under argv[2]. Runs the failing tests' bodies
with tracebacks, then (A) the head helper with spelling compared only for known facts (unsettled
cells against the oracle cell_notation) and, for positive, (B) v17 bound with the mismatched unit
token kept. Exit 0 = every proposed-fix check passes; 1 otherwise."""
import json, sys, traceback
from pathlib import Path
import cp4c_runs as runs
import test_owner_cp4c as t
from s1a_runs import clone_workflow
from deploy_vii.execution import Execution
from deploy_vii.report_view import fact_spelling
from deploy_workflow.owners import cp4c

case, root = sys.argv[1], Path(sys.argv[2])
rc = 0

def run(name, fn, *a):
    try:
        fn(*a); print("PASS", name); return True
    except Exception:
        print("FAIL", name); traceback.print_exc(limit=-3); return False

def patched_head(store, case):
    want = t.EXPECTED["cases"][case]
    module = store.head_module(t._head(store, t.MODULE))
    own = [f for f in module.facts if f.table_id.startswith("T4E.")]
    bad = []
    if [f.fact_id for f in own] != [e["fact_id"] for e in want["facts"]]: bad.append(("ids",))
    for fact, e in zip(own, want["facts"]):
        cell = cp4c.Cell(fact, tuple(e.get("derives_from", ())), (), e["shown"])
        if t.stage1._record(cell) != {k: v for k, v in e.items() if k != "citations"}: bad.append(("record", fact.fact_id))
        _uc, _st, text = fact_spelling(fact, "G1")
        if e["shown"] is not None:
            if text.replace("G1", "G#") != e["shown"]: bad.append(("shown", fact.fact_id, text, e["shown"]))
        else:
            spelled = {"missing": "∅ G#", "not_applicable": "∅ G# n.m."}[e["status"]]
            if text.replace("G1", "G#") != spelled: bad.append(("unsettled", fact.fact_id, text))
    for table, e in zip(module.tables, want["tables"], strict=False):
        if (table.table_id, table.title) != (e["table_id"], e["title"]): bad.append(("table", table.table_id))
        if [(r.row_id, r.label, list(r.fact_ids)) for r in table.rows] != [(r["row_id"], r["label"], r["fact_ids"]) for r in e["rows"]]: bad.append(("rows", table.table_id))
    by_id = {f.fact_id: f for f in module.facts}
    for name in t.REFERENCES:
        table = next(x for x in module.tables if x.table_id == name)
        rows = want[name]["rows"]
        if [(r.row_id, r.label) for r in table.rows] != [(r["row_id"], r["label"]) for r in rows]: bad.append(("refrows", name))
        for row, e in zip(table.rows, rows, strict=True):
            fact = by_id[row.fact_ids[0]]
            if (fact.status, t.stage1._norm(fact.amount)) != (e["status"], e["amount_exact"]): bad.append(("ref", name, row.row_id))
    ids = t._fig_ids(store)
    got = [(c.claim_id, c.text, c.citations, c.limitation) for c in module.claims]
    exp = [(c["claim_id"], t._bind(c["text"], ids), (), c["limitation"]) for c in want["claims"]]
    if got != exp:
        bad.append(("claims",)); [print(" claim got", g, "\n claim want", w) for g, w in zip(got, exp) if g != w]
    if list(module.limitations) != [*want["own_limitations"], t.SYNTHETIC]:
        bad.append(("limitations",)); print(" lim got", list(module.limitations)); print(" lim want", want["own_limitations"])
    print("patched all mismatches:", bad[:20])
    assert not bad

if case == "positive":
    waiting = runs.ready("positive", root / "ready")
    wf = clone_workflow(waiting, root / "closed")
    out = runs.drive_cp4c(wf, "positive", runs.oracle()["submissions"]["cases"]["positive"][runs.STEP])
    print("positive cp4c outcome", out["status"], out.get("issues"))
    wf.write_receipt(root / "closed" / "owner-receipt.json")
    closed = (root / "closed" / "store", root / "closed" / "owner-receipt.json", None)
    run("orig a1_positive", t.test_a1_positive_heads_inputs_and_the_cp4c_head, closed)
    store = Execution(closed[0])
    if not run("patched head positive", patched_head, store, "positive"): rc = 1
    n = len([f for f in store.head_module(t._head(store, t.MODULE)).facts if "T4E." in f.table_id]); print("T4E count", n)
    if n != 256: rc = 1
    run("orig a3 v17", t.test_a3_each_refusal_is_journaled_with_the_oracle_issues, "v17", waiting, root / "v17")
    wf = clone_workflow(waiting, root / "v17b")
    body = runs.read_view(wf, "positive")
    text = json.dumps(t.REFUSALS["v17"]["payload"], ensure_ascii=False)
    figures = runs.oracle()["submissions"]["figures"]
    names = {n: figures[n] for n in dict.fromkeys(m[1] for m in runs.FIG.finditer(text)) if n in figures}
    b = runs.fig_bindings(wf, body, names)
    fixed = runs.FIG.sub(lambda m: "{" + b[m[1]][0] + "|" + m[2] + "}" if m[1] in b else m[0], text)
    o = wf.submit_review(fixed)
    exp = t._expected_issues(wf._store, "v17")
    print("v17 fixed-binding outcome", o["status"], list(o["issues"])); print("v17 expected", exp)
    if not (o["status"] == "invalid" and list(o["issues"]) == exp): rc = 1
else:
    closed = runs.cp4c_closed(case, root)
    store = Execution(closed[0])
    run("orig a2_gap", t.test_a2_gap_composes_honest_gaps_never_zero, closed)
    if not run("patched head gap", patched_head, store, "gap"): rc = 1
    facts = {f.fact_id: f for f in store.head_module(t._head(store, t.MODULE)).facts}
    unknown = [e for e in t.EXPECTED["cases"]["gap"]["facts"] if e["status"] != "known"]
    if not (unknown and all(facts[e["fact_id"]].amount is None for e in unknown)): rc = 1; print("gap amounts not None")
sys.exit(rc)
