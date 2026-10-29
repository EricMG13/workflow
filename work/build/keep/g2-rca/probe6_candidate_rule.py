"""Probe 6: the CANDIDATE corrected block rule (fix plan below), run without stopping on
(a) the delivered genuine s1a positive page (pytest-2291), (b) the fast real-page fixtures for
cp1c (rv3) and cp4c (chart_dr_support), positive and gap. Exit 0 iff every check passes.
Usage: python probe6_candidate_rule.py <code-root> <s1a report.html>"""
import importlib, json, re, sys
from pathlib import Path
code, s1a_html = Path(sys.argv[1]), Path(sys.argv[2])
sys.path[:0] = [str(code / "src"), str(code / "tests")]
from deploy_workflow import owner_rendering as g2
fails = []
def check(ok, what):
    if not ok: fails.append(what); print("FAIL", what)
GAP = r"∅ G\d+( n\.m\.)?"
def text_ok(got, want):  # oracle `∅ G#` is a placeholder for the renderer's number
    return re.fullmatch(r"∅ G\d+".join(re.escape(p) for p in want.split("∅ G#")), got) is not None
def cell_ok(tag, gc, wc):
    if wc["state"] == "known" and wc.get("shown") is not None:
        check(gc["text"] == wc["shown"], f"{tag} known {gc['text']!r} != {wc['shown']!r}")
    elif wc.get("shown") is not None and "∅ G#" in wc["shown"]:
        check(text_ok(gc["text"], wc["shown"]), f"{tag} {wc['state']} {gc['text']!r} !~ {wc['shown']!r}")
    else:
        check(re.fullmatch(GAP, gc["text"]) is not None, f"{tag} {wc['state']} {gc['text']!r} !~ gap pattern")
def rows_ok(tag, got, want):
    check([r["label"] for r in got] == [r["label"] for r in want], f"{tag} row labels")
    for g, w in zip(got, want):
        if len(g["cells"]) != len(w["cells"]): check(False, f"{tag}/{w['label']} ncells"); continue
        for gc, wc in zip(g["cells"], w["cells"]): cell_ok(f"{tag}/{w['label']}", gc, wc)
def is_chip(run): return run["kind"] == "fig" and re.fullmatch(r"S\d+", run.get("ref_id") or "") and run["text"] == run["ref_id"]
def block_ok(tag, b, o):
    for k in ("title", "owner", "kind", "state", "numbered", "summary"):
        if k in o: check(b[k] == o[k], f"{tag}.{k} {b[k]!r} != {o[k]!r}")
    got_tabs = [(b["tab_label"], b["rows"])] + [(t["label"], t["rows"]) for t in b["tabs"]]
    if "primary" in o:
        want_tabs = [(o["primary"]["tab"], o["primary"]["rows"])] + [(t["tab"], t.get("rows")) for t in o.get("tabs", [])]
    else:
        want_tabs = [(t["label"], t.get("rows")) for t in o.get("tabs", [])]
    if want_tabs:
        check([l for l, _ in got_tabs] == [l for l, _ in want_tabs], f"{tag} tab labels {[l for l,_ in got_tabs]} != {[l for l,_ in want_tabs]}")
        for (gl, gr), (wl, wr) in zip(got_tabs, want_tabs):
            if wr is not None: rows_ok(f"{tag}[{wl}]", gr, wr)
    if "lines" in o:
        check(len(b["lines"]) == len(o["lines"]), f"{tag} nlines")
        for i, (ln, w) in enumerate(zip(b["lines"], o["lines"])):
            chips = [r for r in ln["runs"] if is_chip(r)]
            shown = " ".join(r["text"] for r in ln["runs"] if not is_chip(r))  # app.js:251 joins with a space
            check(text_ok(shown, w["text"]), f"{tag} line {i} {shown[-50:]!r} != {w['text'][-50:]!r}")
            check(bool(chips) == bool(w.get("synthetic_ref")), f"{tag} line {i} synthetic_ref")
def oracle(name): return json.loads((code / "cases" / name / "expected.json").read_text())
def node(name, *path, bid):
    d = oracle(name)
    for k in path: d = d[k]
    for c in [d] + [v for v in d.values() if isinstance(v, dict)]:
        if bid in c: return c[bid]
    raise KeyError(bid)
t = s1a_html.read_text(encoding="utf-8")
p = json.loads(t.split('<script id="report-data" type="application/json">', 1)[1].split("</script>", 1)[0])
blocks = {b["block_id"]: b for b in p["report"]["blocks"]}
for sid in g2.DELIVERY_SCOPES["s1a-credit-snapshot"].sections:
    block_ok(f"s1a/positive/{sid}", blocks[sid], oracle("snapshot")["positive"]["FP01"][sid])
def real(report, bid): return g2._expected_block_payload(next(b for b in report.blocks if b.block_id == bid))
rv3, dr = importlib.import_module("test_chart_render_rv3"), importlib.import_module("chart_dr_support")
for case in ("positive", "gap"):
    _, rep = rv3._report(case)
    block_ok(f"cp1c/{case}", real(rep, "peer-positioning"), node("cp1c-owner", "cases", case, "FP03", bid="peer-positioning"))
    rep = dr.report_of(dr.view_with(dr.composer_module(case), case))
    for bid in ("recovery-by-class", "value-allocation-claims"):
        block_ok(f"cp4c/{case}/{bid}", real(rep, bid), node("cp4c-owner", "cases", case, "FP05", bid=bid))
print(len(fails), "failures")
sys.exit(1 if fails else 0)
