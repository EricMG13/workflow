"""Probe: origins/severities of prefixed gaps in the synthetic public case (both hops reached?)."""
import collections, tempfile
from pathlib import Path
import pytest
import test_cp1_absent_input as t

with pytest.MonkeyPatch.context() as mp:
    t._case_as(mp, "public")
    spy = t._Spy(mp)
    with tempfile.TemporaryDirectory() as d:
        out = t._promote(Path(d))
        print("status", out["status"])
        c = collections.Counter((g.origin, g.severity, g.description.startswith(t.PREFIX)) for g in spy.report.gaps)
        for k, v in sorted(c.items()):
            print(k, v)
        for g in spy.report.gaps:
            if g.description.startswith(t.PREFIX):
                print(g.origin, "|", g.description[len(t.PREFIX):][:160])
