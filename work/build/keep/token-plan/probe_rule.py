"""The recommended rule on the CP-8 connect view. Exit 0 only if:
(1) a verbatim CP-8 thesis quote holding "[Reserved]" renders as written in block and payload;
(2) a malformed or unbalanced reference in CP-8's composed outcome line fails closed;
(3) the outcome line still spells the page's gap (∅ G<n>) in the payload."""
import sys
import pytest
import test_connect_cp8 as tc
from deploy_vii.report_view import build_index, gap_refs

ok = True
view = tc._what_changed_view("positive")
thesis = next(f for f in view.modules[0].facts if f.table_id == "T7.2" and f.status == "known" and f.text)
text = "Section 7.11 [Reserved]; see [sic] and [1]."
v = tc._what_changed_view("positive", {thesis.fact_id: text})
fact = tc._payload_facts(v)[thesis.fact_id]
print("verbatim", thesis.fact_id, "->", fact["display"], "|", fact["table_display"])
ok &= fact["display"] == text
for bad in ("No realized outcome is recorded [T7.3.window.realized_valu].",
            "No realized outcome is recorded [T7.3.window.realized_value"):
    v = tc._what_changed_view("no_outcome", {"cp8.what_changed.outcome.value": bad})
    for step in (tc._what_changed_lines, tc._payload_facts):
        try:
            step(v)
            print("SILENT:", step.__name__, bad); ok = False
        except ValueError as e:
            print("fails closed:", step.__name__, str(e)[:80])
v = tc._what_changed_view("no_outcome")
gap = gap_refs(build_index(v)[1])[("CP-8", "T7.3.window.realized_value")]
shown = tc._payload_facts(v)["cp8.what_changed.outcome.value"]["display"]
print("outcome display:", shown); ok &= f"∅ {gap}" in shown
sys.exit(0 if ok else 1)
