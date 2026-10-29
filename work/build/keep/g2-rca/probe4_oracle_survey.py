"""Probe 4: static survey of every ORACLE_POINTERS block node the deferred complete cases reach
(tests/test_owner_rendering.py@ee95ffb :374-387, :2160-2180): per scope/case, the line keys,
synthetic_ref / ref usage in lines, cell states and whether non-known cells carry `shown`.
Usage: python -I probe4_oracle_survey.py <code-root>"""
import json, re, sys
from collections import Counter
from pathlib import Path
code = Path(sys.argv[1])
sys.path.insert(0, str(code / "src"))
P = {"s1a-credit-snapshot": ("snapshot", "/{c}/FP01"), "cp1c-fp03-peers": ("cp1c-owner", "/cases/{c}/FP03"),
     "cp1d-fp02-quality": ("cp1d-owner", "/cases/{c}/FP02"), "cp2a-fp05-downside": ("cp2a-owner", "/cases/{c}/FP05"),
     "cp2g-fp05-forward": ("cp2g-owner", "/cases/positive/FP05"), "cp2g-fp05-forward-gap": ("cp2g-owner", "/cases/gap/FP05"),
     "cp2h-fp05-ratings": ("cp2h-owner", "/cases/{c}/FP05"), "cp4c-fp05-recovery": ("cp4c-owner", "/cases/{c}/FP05"),
     "cp2d-fp04-liquidity": ("cp2d-owner", "/fp04_render"), "cp3d-fp03-market": ("cp3d-owner", "/render"),
     "cp4-fp04-covenants": ("cp4-owner", "/render"), "cp8-fp01-what-changed": ("cp8-owner", "/render")}
CASES = {"s1a-credit-snapshot": ["positive", "gap_business_without_ownership_transaction"], "cp1c-fp03-peers": ["positive", "gap", "no_peers"],
         "cp1d-fp02-quality": ["positive", "statements_only", "gap"], "cp2a-fp05-downside": ["positive", "gap"],
         "cp2g-fp05-forward": ["positive"], "cp2g-fp05-forward-gap": ["gap"], "cp2h-fp05-ratings": ["positive", "gap"],
         "cp4c-fp05-recovery": ["positive", "gap"], "cp3d-fp03-market": ["positive"], "cp4-fp04-covenants": ["positive"],
         "cp8-fp01-what-changed": ["positive"]}
import importlib; sys.path.insert(0, str(code / "tests"))
from deploy_workflow import owner_rendering as g2
def ptr(d, p):
    for part in [x for x in p.split("/") if x]:
        d = d[int(part)] if isinstance(d, list) else d[part]
    return d
def nodes(node, secs):
    cands = [node] + ([v for v in node.values() if isinstance(v, dict)] if isinstance(node, dict) else [])
    for c in cands:
        if all(s in c for s in secs): return {s: c[s] for s in secs}
    return None
def cells(rows):
    for r in rows:
        for c in r.get("cells", []): yield c

CASES.update({"cp2d-fp04-liquidity": [None], "cp3d-fp03-market": [None], "cp4-fp04-covenants": [None], "cp8-fp01-what-changed": [None]})
GAP = re.compile(r"∅ G\d+( n\.m\.)?")
for scope, cases in CASES.items():
    name, p = P[scope]
    secs = tuple(g2.DELIVERY_SCOPES[scope].sections)
    doc = json.loads((code / "cases" / name / "expected.json").read_text())
    for case in cases:
        try: ns = nodes(ptr(doc, p.format(c=case)), secs)
        except Exception as e: print(scope, case, "POINTER FAIL", repr(e)); continue
        if ns is None: print(scope, case, "SECTIONS MISSING", secs); continue
        for sid, b in ns.items():
            info = {k: type(v).__name__ for k, v in b.items()}
            prim = b.get("primary"); tabs = b.get("tabs", [])
            tabinfo = [ (sorted(t) if isinstance(t, dict) else type(t).__name__) for t in tabs][:1]
            rows = []
            if isinstance(prim, dict): rows += prim.get("rows", [])
            for t in tabs:
                if isinstance(t, dict): rows += t.get("rows", [])
            rk = sorted({k for r in rows for k in r})
            bad = Counter()
            for r in rows:
                for c in r.get("cells", []):
                    st, sh = c.get("state"), c.get("shown")
                    if not (st == "known" and sh is not None) and not (isinstance(sh, str) and GAP.fullmatch(sh)):
                        bad[(st, sh if sh is None else sh[:20])] += 1
            print(f"{scope}/{case}/{sid}: {info} tab0keys={tabinfo} rowkeys={rk} nonknown_not_gap_pattern={dict(bad.most_common(4))}")
