"""Edge cases for 3d93a4c _column_periods/_statement; prints each result, exit 1 if an expectation fails."""
import sys, types
from datetime import date
from pathlib import Path
WT = Path("/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a3822801a9a54e78a")
sys.path[:0] = [str(WT / "src"), str(WT / "tests")]
from deploy_workflow import financial_workflow as fw
assert Path(fw.__file__).resolve().is_relative_to(WT)
def P(i, t, e, q=None): return types.SimpleNamespace(period_id=i, period_type=t, fiscal_year=str(e.year), fiscal_quarter=q, end_date=e)
q26=P("q26","QUARTER",date(2026,6,30),2); q25=P("q25","QUARTER",date(2025,6,30),2)
y26=P("y26","YTD",date(2026,6,30)); y25=P("y25","YTD",date(2025,6,30))
fy25=P("fy25","FY",date(2025,12,31)); pe25=P("pe25","PERIOD_END",date(2025,12,31)); ltm=P("ltm","LTM",date(2026,6,30))
fy26=P("fy26","FY",date(2026,6,30))
ALL=(q26,q25,y26,y25,fy25,pe25,ltm)
S=lambda *g: tuple(frozenset(x.split()) for x in g)
fails=0
def chk(name, got, exp):
    global fails
    ok = got == exp; fails += not ok
    print(("ok  " if ok else "FAIL"), name, "->", got, "" if ok else f"(expected {exp})")
cp=fw._column_periods
chk("month abbrev", cp(("(In millions) | Jun 30, 2026",), ALL), None)
chk("missing comma", cp(("(In millions) | June 30 2026",), ALL), None)
chk("footnote (1)", cp(("(In millions) | June 30, 2026 (1)",), ALL), None)
chk("span+single dated: span first", cp(("Three Months Ended June 30,", "(In millions) | 2026 | 2025", "x | June 30, 2026 | June 30, 2025"), ALL), S("q26","q25"))
chk("single dated then span", cp(("x | June 30, 2026 | December 31, 2025", "Three Months Ended June 30,", "(In millions) | 2026 | 2025"), ALL), S("q26 y26","fy25 pe25"))
chk("k=2 n=3", cp(("Three Months Ended June 30, | Six Months Ended June 30,", "x | 2026 | 2025 | 2026"), ALL), None)
chk("k=2 n=4 pairing", cp(("Three Months Ended June 30, | Six Months Ended June 30,", "x | 2026 | 2025 | 2026 | 2025"), ALL), S("q26","q25","y26","y25"))
chk("k=1 n=2 nine months", cp(("Nine Months Ended June 30,", "x | 2026 | 2025"), ALL), S("y26","y25"))
chk("k=2 n=2", cp(("Three Months Ended June 30, | Six Months Ended June 30,", "x | 2026 | 2026"), ALL), S("q26","y26"))
chk("Feb 30 span", cp(("Three Months Ended February 30,", "x | 2026"), ALL), None)
chk("Feb 30 date cell", cp(("x | February 30, 2026",), ALL), None)
chk("Feb 29 non-leap", cp(("Years Ended February 29,", "x | 2025"), ALL), None)
chk("Year Ended singular", cp(("Year Ended December 31,", "x | 2025"), ALL), S("fy25"))
chk("bare balance span", cp(("December 31,", "x | 2025"), ALL), S("fy25 pe25"))
chk("balance 2026-06-30 excludes LTM", cp(("x | June 30, 2026",), ALL), S("q26 y26"))
chk("balance includes FY ending then", cp(("x | June 30, 2026",), (q26,y26,fy26,ltm)), S("q26 y26 fy26"))
chk("overlap balance+flow -> None", cp(("x | June 30, 2026 | June 30, 2026",), ALL), None)
chk("years without span", cp(("x | 2026 | 2025",), ALL), None)
chk("span not followed by years", cp(("Three Months Ended June 30,", "x | foo"), ALL), None)
chk("span last header", cp(("Three Months Ended June 30,",), ALL), None)
chk("mixed span + non-span row", cp(("Three Months Ended June 30, | Total", "x | 2026"), ALL), None)
chk("YTD needs exactly one", cp(("Six Months Ended June 30,", "x | 2026"), (y26, P("y26b","YTD",date(2026,6,30)))), None)
chk("FY needs exactly one", cp(("Years Ended December 31,", "x | 2025"), (fy25, P("fy25b","FY",date(2025,12,31)))), None)
chk("year 1899 rejected", cp(("Years Ended December 31,", "x | 1899"), ALL), None)
chk("pipe synthetic form", cp(("Period | Q4 2025 | FY 2025",), (P("q4","QUARTER",date(2025,12,31),4), fy25)), S("q4","fy25"))
chk("first cell is column (kept)", cp(("Q4 2025  FY 2025",), (P("q4","QUARTER",date(2025,12,31),4), fy25)), S("q4","fy25"))
chk("first cell is span (kept)", cp(("June 30, | December 31,", "x | 2026 | 2025"), ALL), S("q26 y26","fy25 pe25"))
# _statement
st=fw._statement
chk("stmt caption IS", st("CONSOLIDATED STATEMENTS OF OPERATIONS", "BALANCE SHEET"), "IS")
chk("stmt page BS", st("ASSETS", "  CONSOLIDATED CONDENSED BALANCE SHEETS  \n"), "BS")
chk("stmt page CFS", st("OPERATING", "CONSOLIDATED STATEMENTS OF CASH FLOWS"), "CFS")
chk("stmt page two kinds", st("X", "INCOME STATEMENT\nBALANCE SHEET"), None)
chk("stmt same kind twice", st("X", "INCOME STATEMENT\nCONSOLIDATED STATEMENTS OF OPERATIONS"), "IS")
chk("stmt heading not on own line", st("X", "see the BALANCE SHEET above"), None)
sys.exit(1 if fails else 0)
