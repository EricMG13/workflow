"""Probe: the smaller rule `prose._TOKEN.search(text) is not None` keeps CP-3's literal label and
fails closed on the mixed cases. argv[1] = fresh tree. Exit 0 = rule holds (CP-3/CP-8 pass, mixed fail closed)."""
import sys
tree = sys.argv[1]
sys.path[:0] = [tree + "/src", tree + "/tests"]
import pytest
from deploy_vii import prose
import deploy_vii.report_view as rv
rv._carries_reference = lambda text: prose._TOKEN.search(text) is not None
import test_connect_cp8 as t
open_ = 0
for text in ("No realized outcome [T7.3.window.realized_value] see [note 1].",
             "Outside [T9.9.nope.value] and [Insufficient Information]."):
    try:
        t._what_changed_lines(t._what_changed_view("no_outcome", {"cp8.what_changed.outcome.value": text}))
        print("STILL OPEN:", text); open_ += 1
    except ValueError as e:
        print("fail-closed:", text, "->", str(e)[:70])
rc = pytest.main(["-q", "-x", "-p", "no:cacheprovider", "--rootdir", tree,
                  tree + "/tests/test_connect_cp3.py", tree + "/tests/test_connect_cp8.py"])
print("pytest rc", rc)
sys.exit(1 if open_ or rc else 0)
