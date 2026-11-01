"""T1 review probes. Usage: python probe_t1.py [base]; exit 1 if any tip defect shows."""
import importlib.util, sys
from datetime import date
from types import SimpleNamespace
from pathlib import Path

if len(sys.argv) > 1 and sys.argv[1] == "base":
    spec = importlib.util.spec_from_file_location("fw_base", Path(__file__).with_name("fw_base.py"))
    fw = importlib.util.module_from_spec(spec); spec.loader.exec_module(fw)
else:
    import deploy_workflow.financial_workflow as fw

def P(pid, kind, start, end, q=None):
    return SimpleNamespace(period_id=pid, period_type=kind, fiscal_year=str(end.year),
                           fiscal_quarter=q, start_date=start, end_date=end)

bad = 0
def check(name, fn, want):
    global bad
    try:
        got = fn()
    except Exception as e:
        got = f"RAISE {type(e).__name__}: {e}"
    ok = got == want
    bad += not ok
    print(("ok  " if ok else "FAIL"), name, "->", got)

# 1. start_date None (allowed by FinancialPeriod with a limitation)
nodate = P("q", "QUARTER", None, date(2026, 6, 30), 2)
check("start_date None does not crash (refuses)",
      lambda: fw._column_periods(("Three Months Ended June 30,", "2026"), (nodate,)), None)

# 2. 52/53-week filer (13-week quarter ending Dec 28; 52-week FY)
q = P("q1", "QUARTER", date(2024, 9, 29), date(2024, 12, 28), 1)
check("13-week quarter maps",
      lambda: fw._column_periods(("Three Months Ended December 28,", "2024"), (q,)), (frozenset({"q1"}),))
fy = P("fy", "FY", date(2023, 10, 1), date(2024, 9, 28))
check("52-week FY maps",
      lambda: fw._column_periods(("Years Ended September 28,", "2024"), (fy,)), (frozenset({"fy"}),))

# 3. caption on a multi-heading page
both = "CONSOLIDATED BALANCE SHEETS\nCONSOLIDATED STATEMENTS OF OPERATIONS"
for cap, want in [("CONSOLIDATED STATEMENTS OF COMPREHENSIVE INCOME", "IS"),
                  ("CONSOLIDATED STATEMENTS OF EARNINGS", "IS"),
                  ("STATEMENTS OF FINANCIAL POSITION", "BS")]:
    check(f"caption {cap!r}", lambda cap=cap: fw._statement(cap, both), want)

# 4. period length on its own row (pre-existing H02 variant)
ytd = P("ytd", "YTD", date(2026, 1, 1), date(2026, 6, 30))
q2 = P("q2", "QUARTER", date(2026, 4, 1), date(2026, 6, 30), 2)
check("'Three Months Ended' own row does not accept YTD",
      lambda: fw._column_periods(("Three Months Ended", "June 30,", "2026"), (ytd, q2)), (frozenset({"q2"}),))
sys.exit(1 if bad else 0)
