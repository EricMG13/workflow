"""Probe: G2 test's figure comparison (tests/test_owner_rendering.py `_figure_equals`) against
rulings item 20 Q1 (S.4 title exact / regex) and Q3 (DR.6 suffix must be `(∅ G<n>, ...)` with every
G<n> a gap the page cites; dr6 oracle: positive reason carries no G#).
Run from s3-i4: PYTHONPATH=src:tests python -I-less ... (see below). Exit 0 = every forged input
was ACCEPTED (defects reproduced); prints each case."""
import sys

import test_owner_rendering as t

S4_TITLE = "Maturity wall — principal at 2025-12-31 (not a forecast)"


def fig(title=None, reason=None, fid="X"):
    return {"fig_id": fid, "placement": "above", "title": title or "",
            "chart": {"kind": "na", "unit": None, "series": [], "marks": [], "svg": "",
                      "table_twin": {"rows": []}, "reason": reason}}


def accepted(got, want):
    try:
        t._figure_equals(got, want, [])
        return True
    except AssertionError as e:
        print("   assertion:", repr(e)[:120])
        return False


base = dict(placement=None, kind=None, unit=None, series=None, marks=())
forged = {
    "S.4 title with junk suffix": (fig(title=S4_TITLE + " junk", fid="S.4"),
        t.ExpFigure("S.4", title=S4_TITLE.split(" —")[0] if False else "Maturity wall", title_prefix=True, **base)),
    "DR.6 positive reason with a G# appended (oracle: no G#)": (
        fig(fid="DR.6", reason="agency source is synthetic; a headroom chart waits for a real agency report ∅ G7"),
        t.ExpFigure("DR.6", title=None, reason="agency source is synthetic; a headroom chart waits for a real agency report", **base)),
    "DR.6 gap suffix not in the (∅ G<n>, ...) form": (
        fig(fid="DR.6", reason="a trigger threshold is not stated in the synthetic agency source; a headroom chart waits for a real agency report;;; ∅ G999 ."),
        t.ExpFigure("DR.6", title=None, reason="a trigger threshold is not stated in the synthetic agency source; a headroom chart waits for a real agency report", **base)),
}
hit = 0
for name, (got, want) in forged.items():
    ok = accepted(got, want)
    print(("ACCEPTED " if ok else "refused  ") + name)
    hit += ok
print("note: no G<n> in the suffix is checked against the page's cited gaps (no lookup in _figure_equals)")
sys.exit(0 if hit == len(forged) else 1)
