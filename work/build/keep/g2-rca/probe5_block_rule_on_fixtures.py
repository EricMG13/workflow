"""Probe 5: exec the ee95ffb block-comparison functions (_cell_ok .. assert_block_equals_oracle,
tests/test_owner_rendering.py@ee95ffb :1978-2015) verbatim and apply them to (a) each ORACLE_POINTERS
oracle node with a minimal block, to expose oracle-shape crashes, and (b) the fast real-page fixtures
(rv3/cr1/chart_dr_support) for cp1c, cp4, cp4c. Prints one verdict per (scope, case, block).
Usage: python probe5_block_rule_on_fixtures.py <code-root> <ee95ffb-test-text>"""
import importlib, json, re, sys, traceback
from pathlib import Path
from typing import Any
code, ttext = Path(sys.argv[1]), Path(sys.argv[2]).read_text(encoding="utf-8")
sys.path[:0] = [str(code / "src"), str(code / "tests")]
start, end = ttext.index("def _cell_ok("), ttext.index("def _s1a(")
ns: dict[str, Any] = {"re": re, "Any": Any}
exec(compile(ttext[start:end], "ee95ffb:block-rule", "exec"), ns)
rule = ns["assert_block_equals_oracle"]
from deploy_workflow import owner_rendering as g2
def oracle(name): return json.loads((code / "cases" / name / "expected.json").read_text())
def ptr(d, p):
    for part in [x for x in p.split("/") if x]: d = d[int(part)] if isinstance(d, list) else d[part]
    return d
def nodes(node, secs):
    for c in [node] + [v for v in node.values() if isinstance(v, dict)]:
        if all(s in c for s in secs): return {s: c[s] for s in secs}
def verdict(tag, block, want):
    try: rule(block, want); print("PASS", tag)
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)[-1]
        print("FAIL", tag, type(e).__name__, str(e)[:160].replace("\n", " "), f"@{tb.name}:{tb.line}")
# (a) oracle-shape: a block carrying the oracle's own scalar keys, so only structure can fail
for scope, (name, p) in {"cp3d-fp03-market": ("cp3d-owner", "/render"), "cp4-fp04-covenants": ("cp4-owner", "/render"),
                         "cp8-fp01-what-changed": ("cp8-owner", "/render")}.items():
    for sid, want in nodes(ptr(oracle(name), p), tuple(g2.DELIVERY_SCOPES[scope].sections)).items():
        block = {k: want.get(k) for k in ("title", "owner", "kind", "state", "numbered", "summary")}
        block.update(tab_label="x", rows=[], tabs=[{"label": "x", "rows": []}] * 9, lines=[])
        verdict(f"shape {scope}/{sid}", block, want)
# (b) real fixture pages
def real(report, bid): return g2._expected_block_payload(next(b for b in report.blocks if b.block_id == bid))
rv3, cr1 = importlib.import_module("test_chart_render_rv3"), importlib.import_module("test_chart_render_cr1")
dr = importlib.import_module("chart_dr_support")
for case in ("positive", "gap"):
    _, rep = rv3._report(case)
    verdict(f"real cp1c/{case}/peer-positioning", real(rep, "peer-positioning"), ptr(oracle("cp1c-owner"), f"/cases/{case}/FP03")["peer-positioning"] if "peer-positioning" in ptr(oracle("cp1c-owner"), f"/cases/{case}/FP03") else nodes(ptr(oracle("cp1c-owner"), f"/cases/{case}/FP03"), ("peer-positioning",))["peer-positioning"])
    _, rep = cr1._report(case)
    verdict(f"real cp4/{case}/covenant-tests-headroom", real(rep, "covenant-tests-headroom"), nodes(ptr(oracle("cp4-owner"), "/render"), ("covenant-tests-headroom",))["covenant-tests-headroom"])
    view = dr.view_with(dr.composer_module(case), case); rep = dr.report_of(view)
    for bid in ("recovery-by-class", "value-allocation-claims"):
        b = real(rep, bid); w = nodes(ptr(oracle("cp4c-owner"), f"/cases/{case}/FP05"), (bid,))[bid]
        print("   ", bid, "payload tabs", [b["tab_label"]] + [t["label"] for t in b["tabs"]], "oracle tabs", [t.get("label") for t in w.get("tabs", [])])
        verdict(f"real cp4c/{case}/{bid}", b, w)
