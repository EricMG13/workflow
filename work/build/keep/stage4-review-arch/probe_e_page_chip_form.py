"""Class E follow-up: how the full page spells the outcome line's gap chip (HTML form), so the
first probe's "bound chip" check is read against the real markup. Exit 1 if the outcome sentence
is absent from the visible page, or if G<n> on it differs from the index's reference."""

import re
import sys

import test_connect_cp8 as tc
from deploy_vii import render as core_render
from deploy_vii.report_view import build_index, gap_refs

view = tc._what_changed_view("no_outcome")
_, index = build_index(view)
gap = gap_refs(index)[("CP-8", "T7.3.window.realized_value")]
page = core_render.render(view)
visible = re.sub(r"<script[^>]*>.*?</script>", "", page, flags=re.S)
hits = [m.start() for m in re.finditer(r"No realized outcome is recorded", visible)]
print("occurrences of the outcome sentence on the visible page:", len(hits))
for pos in hits:
    print("...", visible[pos : pos + 420].replace("\n", " "), "...")
print("count of '∅' on visible page:", visible.count("∅"), "| '&#8709;':", visible.count("&#8709;"))
print("count of the gap id", gap, "on the visible page:", visible.count(gap))
if not hits:
    sys.exit(1)
window = visible[hits[0] : hits[0] + 420]
ok = (gap in window) and ("[T7.3" not in window) and ("G#" not in window)
print("outcome sentence carries", gap, "and no literal token:", ok)
sys.exit(0 if ok else 1)
