"""Survey: which R2.5 oracle pointers carry `cites` in their cells (report only)."""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(sys.argv[1])
POINTERS = {
    "s1a-credit-snapshot": ("snapshot", ["/positive/FP01", "/gap_business_without_ownership_transaction/FP01"]),
    "cp1c-fp03-peers": ("cp1c-owner", ["/cases/{c}/FP03"]),
    "cp1d-fp02-quality": ("cp1d-owner", ["/cases/{c}/FP02"]),
    "cp2a-fp05-downside": ("cp2a-owner", ["/cases/{c}/FP05"]),
    "cp2g-fp05-forward": ("cp2g-owner", ["/cases/positive/FP05"]),
    "cp2g-fp05-forward-gap": ("cp2g-owner", ["/cases/gap/FP05"]),
    "cp2h-fp05-ratings": ("cp2h-owner", ["/cases/{c}/FP05"]),
    "cp4c-fp05-recovery": ("cp4c-owner", ["/cases/{c}/FP05"]),
    "cp2d-fp04-liquidity": ("cp2d-owner", ["/fp04_render", "/cases/{c}/tables"]),
    "cp3d-fp03-market": ("cp3d-owner", ["/render", "/cases/{c}/tables"]),
    "cp4-fp04-covenants": ("cp4-owner", ["/render", "/{c}/CP-4/tables"]),
    "cp8-fp01-what-changed": ("cp8-owner", ["/render", "/cases/{c}/tables"]),
    "cp3-fp01-relative-value": ("cp3-cp6-owner", ["/{c}/CP-3/render"]),
    "slice-cp2e-sensitivity": ("cp2e-owner", ["/render", "/cases/{c}/module_tables"]),
    "slice-cpdr-research": ("cpdr-owner", ["/evidence_rail", "/limitations_rail"]),
    "slice-cpl10-screen": ("cpl10-owner", ["/rendered/rails"]),
}


def ptr(doc, p):
    for part in [x for x in p.split("/") if x]:
        doc = doc[int(part)] if isinstance(doc, list) else doc[part]
    return doc


def walk(x, cnt):
    if isinstance(x, dict):
        if "cites" in x:
            c = x["cites"]
            ok = isinstance(c, list) and all(isinstance(i, list) and len(i) == 2 for i in c)
            cnt["list" if ok else "prose:" + str(c)[:60]] += 1
        for v in x.values():
            walk(v, cnt)
    elif isinstance(x, list):
        for v in x:
            walk(v, cnt)


for scope, (name, ptrs) in POINTERS.items():
    doc = json.loads((ROOT / "cases" / name / "expected.json").read_text())
    for p in ptrs:
        cases = ["positive"]
        if "{c}" in p:
            base = p.split("{c}")[0]
            node = ptr(doc, base)
            cases = [k for k in node if isinstance(node[k], dict)] if isinstance(node, dict) else []
        for c in cases:
            try:
                node = ptr(doc, p.format(c=c))
            except (KeyError, IndexError, TypeError) as e:
                continue
            cnt = Counter()
            walk(node, cnt)
            if cnt:
                print(f"{scope:24} {name}#{p.format(c=c)}: {dict(cnt)}")
