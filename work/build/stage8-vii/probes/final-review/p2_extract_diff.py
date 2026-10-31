"""Base vs HEAD extractor over every page-like text string in cases/ and tests/ (json/txt/md).
Reports pages whose lines/headers/values change (D2/D3), and counts omitted (D1). Exit 0 always;
prints the diff list."""
import importlib.util, json, pathlib, sys
from dataclasses import asdict
root = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("base_se", "/private/tmp/claude-501/s8vii-final/base_statement_extract.py")
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
from deploy_vii import statement_extract as head
def strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values(): yield from strings(v)
    elif isinstance(o, list):
        for v in o: yield from strings(v)
seen=set(); changed=[]; npages=0; nomit=0
for p in sorted([*root.joinpath("cases").rglob("*"), *root.joinpath("tests").rglob("*")]):
    if not p.is_file() or p.suffix not in {".json", ".txt", ".jsonl"} or p.stat().st_size > 8_000_000: continue
    try: txt = p.read_text()
    except Exception: continue
    cands = []
    if p.suffix == ".json":
        try: cands = list(strings(json.loads(txt)))
        except Exception: cands = [txt]
    elif p.suffix == ".jsonl":
        for l in txt.splitlines():
            try: cands += list(strings(json.loads(l)))
            except Exception: pass
    else: cands = [txt]
    for s in cands:
        if s.count("\n") < 3 or "  " not in s or s in seen: continue
        seen.add(s)
        b = base.extract_statement_lines(s, "page:x"); h = head.extract_statement_lines(s, "page:x")
        if not b.lines and not h.lines: continue
        npages += 1; nomit += len(h.omitted)
        bl = [(l.line_no, l.label, l.raw_values) for l in b.lines]; hl = [(l.line_no, l.label, l.raw_values) for l in h.lines]
        if bl != hl or b.headers != h.headers:
            changed.append((str(p.relative_to(root)), sorted(set(hl)-set(bl))[:4], sorted(set(bl)-set(hl))[:4], b.headers != h.headers))
print("pages with lines:", npages, "omitted total:", nomit, "changed:", len(changed))
for c in changed[:40]: print(c)
