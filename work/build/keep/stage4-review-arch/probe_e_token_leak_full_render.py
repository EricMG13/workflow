"""Class E probe: the CP-8 no_outcome module rendered through every shipped path. The full page
(`render.render(view)`) and every pathway's `build()` must not show the literal token
`[T7.3.window.realized_value]` or `G#` outside the machine `report-data` JSON, and the what-changed
outcome line must carry the same G<n> the index assigns to T7.3.window.realized_value.
Run from the extracted tree with PYTHONPATH=src:tests. Exit 1 on any leak or mismatch."""

import re
import sys

import test_connect_cp8 as tc
from deploy_vii import render as core_render
from deploy_vii.report_view import build, build_index, gap_refs, pathways

failures: list[str] = []
view = tc._what_changed_view("no_outcome")
_, index = build_index(view)
gap = gap_refs(index)[("CP-8", "T7.3.window.realized_value")]
print("page gap ref for T7.3.window.realized_value:", gap)

maps = getattr(tc, "SHIPPED_MAPS", None)
if maps is None:
    from deploy_workflow.owner_rendering import SHIPPED_MAPS as maps  # type: ignore[no-redef]

for pathway in pathways():
    try:
        report = build(view, pathway, maps)
    except ValueError as error:
        print(f"pathway {pathway.id}: build refused: {error}")
        continue
    for block in report.blocks:
        for line in getattr(block, "lines", ()):
            runs = [(r.kind, r.text, r.ref_id) for r in line.runs]
            joined = "".join(r[1] for r in runs)
            if "[T7.3" in joined or "G#" in joined:
                failures.append(f"{pathway.id}/{block.block_id}: literal in {runs}")
            if joined.startswith("No realized outcome is recorded"):
                gaps = [r for r in runs if r[0] == "gap"]
                if gaps != [("gap", f"∅ {gap}", gap)]:
                    failures.append(f"{pathway.id}/{block.block_id}: gap runs {gaps} != {gap}")
                else:
                    print(f"pathway {pathway.id}/{block.block_id}: outcome line bound to {gap}")

page = core_render.render(view)
visible = re.sub(r"<script[^>]*>.*?</script>", "", page, flags=re.S)
for needle in ("[T7.3.window.realized_value]", "G#", "T7.3.window.realized_value]"):
    count = visible.count(needle)
    print(f"visible page: {needle!r} x{count}")
    if count:
        failures.append(f"full page shows {needle!r} {count} times")
print("full page carries the bound chip:", f"∅ {gap}" in visible)
if f"∅ {gap}" not in visible:
    failures.append("full page does not show the bound chip")

for line in failures:
    print("FAIL", line)
sys.exit(1 if failures else 0)
