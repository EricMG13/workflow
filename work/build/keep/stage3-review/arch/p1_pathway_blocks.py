"""Probe 1: pathway x block cross-table.

For every pathway: preset blocks, _Spec producers/kind, registered figure producer (and its
pathway filter), DELIVERY_SCOPES rows that assign the block, and which frozen chart oracle names
a figure for (pathway, block). Prints gaps: figure producer with no scope row; scope section
not in the pathway preset; oracle figure with no producer; duplicate scope triples.
Run from the s3-i4 worktree: PYTHONPATH=src:tests <python> -I p1_pathway_blocks.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from deploy_vii import report_view as rv
from deploy_workflow.owner_rendering import DELIVERY_SCOPES

root = Path.cwd()
oracles = {p.stem.replace("-expected", ""): json.loads(p.read_text()) for p in (root / "cases/charts").glob("*-expected.json")}

# which (pathway, block) each oracle claims to draw on
oracle_claims: dict[tuple[str, str], list[str]] = defaultdict(list)


def walk(name: str, node, path: str = "") -> None:
    if isinstance(node, dict):
        if "pathway" in node and "block" in node and isinstance(node.get("pathway"), str):
            oracle_claims[(node["pathway"], node["block"])].append(f"{name}:{path}")
        for k, v in node.items():
            walk(name, v, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(name, v, f"{path}/{i}")


for name, doc in oracles.items():
    walk(name, doc.get("render", doc))
    # some oracles key render by pathway name
    r = doc.get("render", {})
    if isinstance(r, dict):
        for k, v in r.items():
            if isinstance(v, dict) and "block" in v and k in {"credit_snapshot", "earnings_update", "relative_value", "covenant_refinancing", "distressed_restructuring", "portfolio_decision"}:
                oracle_claims[(k, v["block"])].append(f"{name}:/render/{k}")

presets: dict[str, list[str]] = defaultdict(list)
for pathway, _title, _question, _blocks in rv._PRESETS:
  for block in _blocks:
    presets[pathway].append(block)

scope_rows: dict[tuple[str, str], list[str]] = defaultdict(list)
triples = defaultdict(list)
for sid, s in DELIVERY_SCOPES.items():
    triples[(s.pathway, s.requested_modules, s.case_kind)].append(sid)
    for b in s.sections:
        scope_rows[(s.pathway, b)].append(sid)
        if b not in presets[s.pathway]:
            print(f"GAP scope section not in preset: {sid} {s.pathway}/{b}")
for t, ids in triples.items():
    if len(ids) > 1:
        print(f"GAP duplicate triple {t}: {ids}")

print("\nscope ids:", sorted(DELIVERY_SCOPES))
print()
for pathway, blocks in presets.items():
    print(f"== {pathway}")
    for b in blocks:
        try:
            spec = rv._spec_of(b)
            prod, kind = spec.producers, spec.kind
        except Exception as e:  # noqa: BLE001 - probe only
            prod, kind = ("<no _Spec: %s>" % type(e).__name__,), "?"
        fp = rv._FIGURE_PRODUCERS.get(b)
        fp_desc = "-"
        if fp:
            fn, paths = fp
            fp_desc = f"{getattr(fn, '__name__', fn)}[{','.join(sorted(paths)) if paths else '*'}]"
        rows = scope_rows.get((pathway, b), [])
        claims = oracle_claims.get((pathway, b), [])
        flags = []
        if fp and (fp[1] is None or pathway in fp[1]) and not rows and kind != "?":
            flags.append("FIGURE-NO-SCOPE")
        if claims and not fp:
            flags.append("ORACLE-NO-PRODUCER")
        if kind == "?":
            flags.append("NO-SPEC")
        print(f"  {b:28} kind={kind:6} prod={prod} fig={fp_desc} scopes={rows} oracle={[c.split(':')[0] for c in claims]} {' '.join(flags)}")
sys.exit(0)
