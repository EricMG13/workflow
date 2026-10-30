"""Probe 3 (rulings item 20 Q3): in the DR.6 `gap` case, the n/a frame reason's suffix has the
form `(∅ G<n>, ...)` and every G<n> resolves to a gap the page's report index cites.
Run from the s3-i4 worktree: PYTHONPATH=src:tests <python> p3_dr6_gap_refs_resolve.py
Exit 0 = every ref resolves, 1 = a ref does not resolve or the suffix form is wrong."""
import re, sys, tempfile
from pathlib import Path
import test_chart_render_dr6 as t

ok = True
with tempfile.TemporaryDirectory() as d:
    for case in ("positive", "gap"):
        report, _mod = t._settled(case, Path(d) / case)
        block = t._block(report)
        reason = block.figures[0].chart.reason or ""
        base = t.FRAMES[case]["reason"]
        suffix = reason[len(base):]
        cited = {r for e in report.index.facts for r in e.ref_ids if r.startswith("G")}
        refs = re.findall(r"∅ (G\d+)", suffix)
        form_ok = suffix == "" or re.fullmatch(r" \((∅ G\d+)(, ∅ G\d+)*\)", suffix) is not None
        unresolved = [g for g in refs if g not in cited]
        print(f"{case}: suffix={suffix!r} form_ok={form_ok} refs={refs} unresolved={unresolved} cited={sorted(cited)}")
        ok = ok and form_ok and not unresolved and reason.startswith(base)
sys.exit(0 if ok else 1)
