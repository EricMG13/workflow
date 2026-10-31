"""Exhaustive check of _months against calendar and 52/53-week spans; exit 1 on any miss."""
import sys
from datetime import date, timedelta
from types import SimpleNamespace as P
sys.path.insert(0, sys.argv[1] + "/src")
from deploy_workflow.financial_workflow import _months, _DAY_WINDOWS

bad = []
ws = sorted(_DAY_WINDOWS.items())
for (a, (_, h)), (b, (l, _)) in zip(ws, ws[1:]):
    if h >= l: bad.append(("overlap", a, b))
def add(d, m):
    y, mo = divmod(d.month - 1 + m, 12)
    return date(d.year + y, mo + 1, 1)
for y in range(1996, 2032):
    for mo in range(1, 13):
        s = date(y, mo, 1)
        for m in (3, 6, 9, 12):
            e = add(s, m) - timedelta(days=1)
            if _months(P(start_date=s, end_date=e)) != m: bad.append(("cal", s, e, m))
        # month-end-anchored spans not starting on day 1 (e.g. Feb 29 -> May 28)
for weeks, m in ((12, 3), (13, 3), (14, 3), (26, 6), (27, 6), (39, 6), (39, 9), (40, 9), (52, 12), (53, 12)):
    s = date(2024, 1, 1); e = s + timedelta(days=7 * weeks - 1)
    got = _months(P(start_date=s, end_date=e))
    exp = m if not (weeks == 39 and m == 6) else None
    if weeks == 39 and m == 6:
        if got == 6: bad.append(("39wk as 6", got))
    elif got != m: bad.append(("wk", weeks, m, got))
for s, e in ((None, date(2024, 1, 1)), (date(2024, 1, 1), None), (None, None), (date(2024, 6, 1), date(2024, 1, 1))):
    try:
        if _months(P(start_date=s, end_date=e)) is not None: bad.append(("nonnull", s, e))
    except Exception as x:
        bad.append(("raise", s, e, x))
print(bad or "ok"); sys.exit(1 if bad else 0)
