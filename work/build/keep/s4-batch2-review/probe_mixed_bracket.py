"""Probe: a known text fact with a valid token plus a stray bracket renders raw (fail-open).
Run from the fresh tree: PYTHONPATH=tree/src:tree/tests python probe_mixed_bracket.py. Exit 1 = fail-open present."""
import sys
sys.path[:0] = [sys.argv[1] + "/src", sys.argv[1] + "/tests"]
import deploy_vii.report_view as rv
print("module:", rv.__file__)
import test_connect_cp8 as t
bad = []
for text in (
    "No realized outcome [T7.3.window.realized_value] see [note 1].",   # valid token + label
    "Window [T7.3.window.realized_value] and a stray ] bracket.",
    "Outside [T9.9.nope.value] and [Insufficient Information].",       # unknown token + label
):
    view = t._what_changed_view("no_outcome", {"cp8.what_changed.outcome.value": text})
    try:
        lines = t._what_changed_lines(view)
    except ValueError as e:
        print("FAIL-CLOSED:", text, "->", str(e)[:80]); continue
    raw = [r for l in lines for r in l if "[T" in r[1]]
    print("RENDERED RAW:", text, "->", raw); bad.append(text)
print("carries_reference('[Insufficient Information]') =", rv._carries_reference("[Insufficient Information]"))
sys.exit(1 if bad else 0)
