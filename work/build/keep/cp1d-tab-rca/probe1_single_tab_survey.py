"""Survey: every oracle block (cases/*/expected.json) with tabs, no primary, exactly one tab.
For each, report the scope that reaches it through G2 ORACLE_POINTERS (if any) and how many
shipped bindings feed the block (1 => report_view renders tab_label None, tabs ()).
Exit 1 if any G2-reached single-tab block would fail the item-28 tabs-only label compare."""
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path[:0] = [str(root / "src"), str(root)]
from deploy_vii.bindings.shipped import SHIPPED_MAPS  # noqa: E402

feeds: dict[str, list[str]] = {}
for m in SHIPPED_MAPS:
    for e in m.entries:
        feeds.setdefault(e.block_id, []).append(f"{m.module_id}:{e.fact_coord.table_id}")

hits = []
def walk(node, path):
    if isinstance(node, dict):
        tabs = node.get("tabs")
        if isinstance(tabs, list) and tabs and all(isinstance(t, dict) for t in tabs) and "primary" not in node and len(tabs) == 1:
            hits.append((path, node))
        for k, v in node.items():
            walk(v, path + [str(k)])
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, path + [str(i)])

for f in sorted((root / "cases").glob("*/expected.json")):
    walk(json.loads(f.read_text()), [f.parent.name])

import re
src = (root / "tests" / "test_owner_rendering.py").read_text()
ptrs = dict(re.findall(r'"([\w-]+)": \("([\w-]+)", "(/[^"]*)"\)', src) and
            [(a, (b, c)) for a, b, c in re.findall(r'"([\w-]+)": \("([\w-]+)", "(/[^"]*)"\)', src)])
fail = 0
for path, node in hits:
    block = path[-1]
    reached = [s for s, (d, p) in ptrs.items() if d == path[0]
               and all(part in path for part in p.replace("{c}", "").split("/") if part)]
    n = len(feeds.get(block, []))
    tab = node["tabs"][0]
    would_fail = bool(reached) and n == 1
    fail |= would_fail
    print(f"{'/'.join(path)} tab={tab.get('label')!r} table={tab.get('table_id')} feeds={feeds.get(block)} "
          f"g2_scope={reached or '-'} tab_label_None={n == 1} item28_fails={would_fail}")
print("single-tab blocks:", len(hits))
sys.exit(1 if fail else 0)
