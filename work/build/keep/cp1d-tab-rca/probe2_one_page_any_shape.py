"""Wider survey: any node with a `tabs` key of length 1 (any element shape), and any node with
`primary` but no further tabs (a one-page block on the `primary` branch). Report-only, exit 0."""
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
def walk(node, path, out):
    if isinstance(node, dict):
        if "tabs" in node and isinstance(node["tabs"], list) and len(node["tabs"]) == 1:
            out.append(("tabs==1", path, type(node["tabs"][0]).__name__, "primary" in node))
        if "primary" in node and not node.get("tabs"):
            out.append(("primary-only", path, type(node["primary"]).__name__, True))
        for k, v in node.items():
            walk(v, path + [str(k)], out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, path + [str(i)], out)
out = []
for f in sorted((root / "cases").glob("*/expected.json")):
    walk(json.loads(f.read_text()), [f.parent.name], out)
for kind, path, shape, prim in out:
    print(kind, "/".join(path), shape, "primary" if prim else "")
print("total", len(out))
