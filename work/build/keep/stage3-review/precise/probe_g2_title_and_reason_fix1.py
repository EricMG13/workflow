"""probe_g2_title_and_reason.py adapted to the fix-1 API (title_prefix -> title_pattern; the three
forged inputs and the exact figure comparator are unchanged). Exit 0 = every forged input is
REFUSED; exit 1 = at least one forged input was accepted."""

import sys

import test_owner_rendering as t

S4_TITLE = "Maturity wall — principal at 2025-12-31 (not a forecast)"


def fig(title=None, reason=None, fid="X"):
    return {
        "fig_id": fid,
        "placement": "above",
        "title": title or "",
        "chart": {
            "kind": "na",
            "unit": None,
            "series": [],
            "marks": [],
            "svg": "",
            "table_twin": {"rows": []},
            "reason": reason,
        },
    }


def accepted(got, want):
    try:
        t._figure_equals(got, want, [])
        return True
    except AssertionError as e:
        print("   assertion:", repr(e)[:120])
        return False


base = dict(placement=None, kind=None, unit=None, series=None, marks=())
gap_reason = (
    "a trigger threshold is not stated in the synthetic agency source; "
    "a headroom chart waits for a real agency report"
)
forged = {
    "S.4 title with junk suffix": (
        fig(title=S4_TITLE + " junk", fid="S.4"),
        t.ExpFigure("S.4", title=None, title_pattern=t._S4_TITLE_PATTERN, **base),
    ),
    "DR.6 positive reason with a G# appended (oracle: no G#)": (
        fig(
            fid="DR.6",
            reason="agency source is synthetic; a headroom chart waits for a real agency report "
            "∅ G7",
        ),
        t.ExpFigure(
            "DR.6",
            title=None,
            reason="agency source is synthetic; a headroom chart waits for a real agency report",
            **base,
        ),
    ),
    "DR.6 gap suffix not in the (∅ G<n>, ...) form": (
        fig(fid="DR.6", reason=gap_reason + ";;; ∅ G999 ."),
        t.ExpFigure("DR.6", title=None, reason=gap_reason, reason_gap_suffix=True, **base),
    ),
}
hit = 0
for name, (got, want) in forged.items():
    ok = accepted(got, want)
    print(("ACCEPTED " if ok else "refused  ") + name)
    hit += ok
sys.exit(0 if hit == 0 else 1)
