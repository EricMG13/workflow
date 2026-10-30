"""Info: the fact path and the block path resolve CP-8 run text without names=(issuer_name,).
Exit 1 if an outcome line naming an issuer with digits ("3M Company") raises Bare figure."""
import sys
import test_connect_cp8 as tc
text = "No realized outcome is recorded for 3M Company, so the window [T7.3.window.realized_value] is missing."
v = tc._what_changed_view("no_outcome", {"cp8.what_changed.outcome.value": text})
v = v.model_copy(update={"run": v.run.model_copy(update={"issuer_name": "3M Company"})})
bad = 0
for step in (tc._what_changed_lines, tc._payload_facts):
    try:
        step(v); print("renders:", step.__name__)
    except ValueError as e:
        bad += 1; print("RAISES:", step.__name__, str(e)[:90])
sys.exit(1 if bad else 0)
