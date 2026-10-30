"""Class E probe 3: the page's machine payload (`report-data`, what app.js draws). The
what-changed block's outcome line must resolve to the index's G<n>; every place the literal token
`[T7.3.window.realized_value]` survives in the payload is listed with its JSON path. Exit 1 if the
block line is wrong or the token appears anywhere outside `modules[].facts[].text` (the stored
fact itself)."""

import json
import re
import sys

import test_connect_cp8 as tc
from deploy_vii import render as core_render
from deploy_vii.report_view import build_index, gap_refs

view = tc._what_changed_view("no_outcome")
_, index = build_index(view)
gap = gap_refs(index)[("CP-8", "T7.3.window.realized_value")]
page = core_render.render(view)
m = re.search(r'<script[^>]*id="report-data"[^>]*>(.*?)</script>', page, flags=re.S)
if not m:
    print("no report-data script found; script tags:", re.findall(r"<script[^>]*>", page)[:5])
    sys.exit(1)
payload = json.loads(m.group(1))

paths: list[str] = []
def walk(node, path):
    if isinstance(node, dict):
        for k, v in node.items():
            walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, f"{path}[{i}]")
    elif isinstance(node, str) and ("[T7.3.window.realized_value]" in node or "G#" in node):
        paths.append(path)
walk(payload, "$")
print("token/G# survivals in the payload:")
for p in paths:
    print("  ", p)
bad = [p for p in paths if not re.fullmatch(r"\$\.modules\[\d+\]\.facts\[\d+\]\.text", p)]

blocks = {b["block_id"]: b for b in payload["report"]["blocks"]}
wc = blocks.get("what-changed")
if wc is None:
    print("no what-changed block in payload; blocks:", list(blocks))
    sys.exit(1)
line = next((l for l in wc["lines"] if l["runs"] and l["runs"][0]["text"].startswith("No realized outcome")), None)
print("what-changed outcome line runs:", None if line is None else [(r["kind"], r["text"], r.get("ref_id")) for r in line["runs"]])
ok_line = line is not None and [(r["kind"], r["text"], r.get("ref_id")) for r in line["runs"]][1] == ("gap", f"∅ {gap}", gap)
print("outcome line bound to", gap, ":", ok_line)
print("payload paths outside the stored fact text:", bad)
sys.exit(0 if ok_line and not bad else 1)
