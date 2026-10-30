"""Probe: cp2g genuine case argv[1] under argv[2]. Runs the failing tests' bodies with tracebacks,
then the proposed fixes: (A) spelling compared only for known facts, unsettled cells against the
oracle cell_notation; (B) bound_literal keeps a mismatched unit token but binds the id (v10).
Exit 0 = every proposed-fix check passes; 1 otherwise."""
import json, re, sys, traceback
from pathlib import Path
import cp2g_runs as runs
import test_owner_cp2g as t
from s1a_runs import clone_workflow
from deploy_vii.execution import Execution
from deploy_vii.report_view import fact_spelling
from deploy_workflow.owners import cp2g

case, root = sys.argv[1], Path(sys.argv[2])
rc = 0

def run(name, fn, *a):
    global rc
    try:
        fn(*a); print("PASS", name)
    except Exception:
        print("FAIL", name); traceback.print_exc(limit=-3)
        return False
    return True

def patched_head(store, case):
    want = t.EXPECTED["cases"][case]
    module = store.head_module(t._head(store, t.MODULE))
    own = [f for f in module.facts if f.table_id.startswith("T2H.")]
    bad = []
    for fact, e in zip(own, want["facts"], strict=True):
        cell = cp2g.Cell(fact, tuple(e.get("derives_from", ())), e["shown"])
        if t.stage1._record(cell) != e: bad.append(("record", fact.fact_id))
        _uc, state, text = fact_spelling(fact, "G1")
        if e["shown"] is not None:
            if text.replace("G1", "G#") != e["shown"]: bad.append(("shown", fact.fact_id, text, e["shown"]))
        else:
            spelled = {"missing": "∅ G#", "not_applicable": "∅ G# n.m."}[e["status"]]
            if text.replace("G1", "G#") != spelled: bad.append(("unsettled", fact.fact_id, text))
    print("patched T2H record/spelling mismatches:", bad[:10])
    for table, e in zip(module.tables, want["tables"], strict=False):
        if (table.table_id, table.title) != (e["table_id"], e["title"]): bad.append(("table", table.table_id))
        if [(r.row_id, r.label, list(r.fact_ids)) for r in table.rows] != [(r["row_id"], r["label"], r["fact_ids"]) for r in e["rows"]]: bad.append(("rows", table.table_id))
    by_id = {f.fact_id: f for f in module.facts}
    for name in ("cp1_references", "cp2a_references", "cp1d_references"):
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
    out = runs.drive_cp2g(wf, runs.oracle()["submissions"]["cases"]["positive"][runs.STEP])
    print("positive cp2g outcome", out["status"], out.get("issues"))
    wf.write_receipt(root / "closed" / "owner-receipt.json")
    closed = (root / "closed" / "store", root / "closed" / "owner-receipt.json", None)
    run("orig a1_positive", t.test_a1_positive_heads_inputs_and_the_cp2g_head, closed)
    run("orig a1_one_ok_read", t.test_a1_one_ok_read_and_no_ok_pack_call_in_the_cp2g_step, closed)
    # piecewise one_ok_read
    receipt = t._receipt(closed)
    reads = [r for r in receipt.input_reads if r.binding.module_id == t.MODULE]
    calls = [c for c in receipt.calls if c.binding.module_id == t.MODULE]
    print("reads", len(reads), "calls", [(c.status, c.error_code) for c in calls])
    keys = runs.oracle()["manifest"]["tool_use"]["view_tree_draft"]["keys"]
    print("keys body", list(json.loads(reads[0].body))); print("keys want", list(keys))
    run("view_tree.check", t.view_tree.check, "cp2g", "positive", reads[0].body)
    store = Execution(closed[0])
    quotes = {c.quote for h in store.read().heads for f in store.head_module(h).facts for c in f.citations}
    leaked = [q for q in quotes if q in reads[0].body]
    print("quotes", len(quotes), "leaked", len(leaked), [q[:80] for q in leaked[:10]])
    if not run("patched head positive", patched_head, store, "positive"): rc = 1
    # v10
    ok_orig = run("orig a3 v10", t.test_a3_each_refusal_is_journaled_with_the_oracle_issues, "v10", waiting, root / "v10")
    wf = clone_workflow(waiting, root / "v10b")
    body = json.loads(wf.read_inputs()["body"])
    payload = t.REFUSALS["v10"]["payload"]
    text = json.dumps(payload, ensure_ascii=False)
    figures = runs.oracle()["submissions"]["figures"]
    names = {n: figures[n] for n in dict.fromkeys(m[1] for m in runs.FIG.finditer(text)) if n in figures}
    b = runs.fig_bindings(wf, body, names)
    fixed = runs.FIG.sub(lambda m: "{" + b[m[1]][0] + "|" + m[2] + "}" if m[1] in b else m[0], text)
    o = wf.submit_review(fixed)
    exp = t._expected_issues(wf._store, "v10")
    print("v10 fixed-binding outcome", o["status"], list(o["issues"])); print("v10 expected", exp)
    if not (o["status"] == "invalid" and list(o["issues"]) == exp): rc = 1
    wf2 = clone_workflow(waiting, root / "v10c"); body2 = json.loads(wf2.read_inputs()["body"])
    o2 = wf2.submit_review(runs.bound_literal(wf2, payload, body2)); print("v10 current-driver issues", list(o2["issues"]))
else:
    closed = runs.cp2g_closed(case, root)
    store = Execution(closed[0])
    if case == "gap":
        run("orig a2_gap", t.test_a2_gap_composes_honest_gaps_never_zero, closed)
    else:
        run("orig a2c_cp1d_blocked", t.test_a2c_cp1d_blocked_binds_the_blocked_head_under_the_restricted_edge, closed)
    if not run(f"patched head {case}", patched_head, store, case): rc = 1
    if case == "gap":
        facts = {f.fact_id: f for f in store.head_module(t._head(store, t.MODULE)).facts}
        for c in ("base", "down"):
            f = facts[f"T2H.7.m01.{c}_first"]; print(c, f.status, f.text, f.limitation)
        print("a25", facts["T2H.6.a25.liquidity_headroom"].status, "CP-1D" in {h.module_id for h in store.read().heads})
    else:
        print("CP-1D", t._head(store, "CP-1D").status)
sys.exit(rc)
