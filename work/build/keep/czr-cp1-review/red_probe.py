"""Run the RED tests (aa6ab1d = cf4c0ec src + new tests) from a scratch archive; print failure causes.
Exit 0 when every new test fails and no pre-existing test in the file fails."""
import sys, io, contextlib
from pathlib import Path
R = Path(__file__).resolve().parent / "scratch" / "red"
sys.path[:0] = [str(R / "src"), str(R / "tests")]
import pytest
from deploy_workflow import financial_workflow as fw
assert Path(fw.__file__).resolve().is_relative_to(R), fw.__file__
class Rec:
    def __init__(s): s.res = {}
    def pytest_runtest_logreport(s, report):
        if report.when == "call" or report.failed:
            s.res[report.nodeid.split("::")[-1]] = (report.outcome, str(report.longrepr).strip().splitlines()[-1] if report.failed else "")
rec = Rec()
pytest.main(["-q", "-p", "no:cacheprovider", "--rootdir", str(R), str(R / "tests/test_czr_fixes.py")], plugins=[rec])
new = ("filed_page", "statement_caption", "balance_date", "year_count", "years_without", "ltm_period")
bad = 0
for n, (o, why) in rec.res.items():
    is_new = any(k in n for k in new)
    print(("NEW " if is_new else "OLD "), o, n, "|", why[:160])
    bad += (is_new and o != "failed") or (not is_new and o != "passed")
sys.exit(1 if bad else 0)
