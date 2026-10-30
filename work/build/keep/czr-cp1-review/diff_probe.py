"""Differential probe: cf4c0ec vs 3d93a4c _column_periods and statement over every synthetic page.

Pages: every string in cases/**/*.json (recursing into JSON-in-strings) that contains a
STATEMENT_HEADING line, plus every page of every tests/*_runs.py make_pack and
test_financial_workflow.make_pack. Period sets: every list of period dicts (period_id,
period_type, end_date) in cases/**/*.json. Exit 1 on any difference outside "old None -> new
mapping on a page/period set the submissions do not reach" (reported separately).
"""
import importlib, importlib.util, inspect, json, subprocess, sys, types
from datetime import date
from pathlib import Path
WT = Path("/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a3822801a9a54e78a")
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(WT / "src"), str(WT / "tests")]
old_src = subprocess.run(["git", "show", "cf4c0ec:src/deploy_workflow/financial_workflow.py"],
                         cwd=WT, capture_output=True, text=True, check=True).stdout
(HERE / "scratch").mkdir(exist_ok=True)
old_path = HERE / "scratch" / "fw_old.py"
old_path.write_text(old_src)
from deploy_workflow import financial_workflow as new
assert Path(new.__file__).resolve().is_relative_to(WT), new.__file__
spec = importlib.util.spec_from_file_location("deploy_workflow.fw_old", old_path)
old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
from deploy_vii.statement_extract import extract_statement_lines

def old_statement(caption):
    c = (caption or "").upper()
    return ("IS" if "INCOME" in c or "OPERATIONS" in c else "CFS" if "CASH FLOW" in c
            else "BS" if "BALANCE SHEET" in c else None)

pages, period_sets = {}, {}
def walk(node, where):
    if isinstance(node, dict):
        for k, v in node.items(): walk(v, where)
    elif isinstance(node, list):
        if node and all(isinstance(x, dict) and {"period_id", "period_type", "end_date"} <= x.keys() for x in node):
            key = json.dumps(node, sort_keys=True)
            period_sets.setdefault(key, (where, node))
        for v in node: walk(v, where)
    elif isinstance(node, str):
        s = node.strip()
        if s[:1] in "{[" and len(s) > 2:
            try: walk(json.loads(s), where); return
            except ValueError: pass
        if new.STATEMENT_HEADING.search(node):
            pages.setdefault(node, where)
for f in sorted((WT / "cases").rglob("*.json")):
    walk(json.loads(f.read_text()), str(f.relative_to(WT)))
# make_pack builders
built = 0
def add_pack(pack, where):
    global built
    for s in pack.sources:
        for sp in s.spans:
            if new.STATEMENT_HEADING.search(sp.text):
                pages.setdefault(sp.text, where); built += 1
for f in sorted((WT / "tests").glob("*_runs.py")):
    mod = importlib.import_module(f.stem)
    mp = getattr(mod, "make_pack", None)
    if mp is None: continue
    if inspect.signature(mp).parameters:
        cases = getattr(mod, "CASES", ())
        for c in (list(cases) if not isinstance(cases, dict) else list(cases)):
            add_pack(mp(c), f"{f.stem}.make_pack({c})")
    else:
        add_pack(mp(), f"{f.stem}.make_pack()")
tfw = importlib.import_module("test_financial_workflow")
add_pack(tfw.make_pack(), "tfw.make_pack()"); add_pack(tfw.make_pack(gap=True), "tfw.make_pack(gap)")

def ns(d):
    e = d["end_date"]; e = date.fromisoformat(e) if isinstance(e, str) else e
    return types.SimpleNamespace(period_id=d["period_id"], period_type=d["period_type"],
        fiscal_year=str(d.get("fiscal_year", "")), fiscal_quarter=d.get("fiscal_quarter"), end_date=e)
psets = [(w, tuple(ns(d) for d in node)) for w, node in period_sets.values()]
# reached = (page, period set) where old mapping is non-None (what synthetic submissions can match)
n_lines = 0; hard = []; soft = []; stmt_diff = []; zip_mismatch = []
for text, where in pages.items():
    is_czr = "czr" in where
    table = extract_statement_lines(text, "p", None)
    n_lines += len(table.lines)
    for line in table.lines:
        o, nw = old_statement(line.caption), new._statement(line.caption, text)
        if o != nw:
            (soft if o is None else hard).append(("STATEMENT", where, line.caption, line.label, o, nw)) if is_czr else stmt_diff.append((where, line.caption, line.label, o, nw))
    for pw, ps in psets:
        o = old._column_periods(table.headers, ps)
        n = new._column_periods(table.headers, ps)
        exp = None if o is None else tuple(frozenset({x}) for x in o)
        if exp != n:
            rec = (where, pw, table.headers[:4], o, n)
            if o is None and not is_czr: soft.append(rec)
            elif not is_czr: hard.append(rec)
        if n is not None and not is_czr:
            for line in table.lines:
                if len(line.values) != len(n): zip_mismatch.append((where, line.label, len(line.values), len(n)))
syn = {t: w for t, w in pages.items() if "czr" not in w}
print(f"pages total={len(pages)} synthetic={len(syn)} czr={len(pages)-len(syn)} built-page-hits={built}")
print(f"extracted lines={n_lines} period sets={len(psets)} comparisons={len(pages)*len(psets)}")
print(f"synthetic statement diffs={len(stmt_diff)}"); [print("  ", r) for r in stmt_diff[:20]]
print(f"synthetic column hard diffs={len(hard)}"); [print("  ", r) for r in hard[:20]]
print(f"synthetic column old-None->mapping={len(soft)}"); [print("  ", r) for r in soft[:20]]
print(f"zip length mismatches under new mapping={len(zip_mismatch)}"); [print("  ", r) for r in zip_mismatch[:10]]
for text, where in syn.items():
    t = extract_statement_lines(text, "p", None)
    print("PAGE", where, "lines", len(t.lines), "headers", [h[:70] for h in t.headers][:3])
    for pw, ps in psets:
        print("   old", old._column_periods(t.headers, ps), "new", new._column_periods(t.headers, ps))
sys.exit(1 if (hard or stmt_diff or zip_mismatch) else 0)
