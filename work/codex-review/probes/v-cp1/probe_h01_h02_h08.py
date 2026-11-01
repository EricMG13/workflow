"""Desired-behaviour probes for H01/H02/H08 at HEAD. Exit non-zero while any defect is present."""
import json, sys
from datetime import date
from decimal import Decimal
from deploy_vii.financial_contracts import FinancialPeriod
from deploy_vii.statement_extract import extract_statement_lines
from deploy_workflow.financial_workflow import _column_periods, _statement
from test_czr_fixes import FILED_PAGES, FILED_PERIODS, _filed_table


def period(pid, kind, start, end, quarter=None):
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    return FinancialPeriod.model_validate_json(json.dumps(dict(
        period_id=pid, period_type=kind, fiscal_year=str(e.year), fiscal_quarter=quarter,
        start_date=start, end_date=end, day_count=(e-s).days+1, audit_status='unaudited',
        currency='USD', unit='MILLIONS', accounting_basis='US GAAP', entity_perimeter='consolidated',
        citations=[dict(source_id='filing', source_sha256='0'*64, locator='page:1', quote='Six Months Ended June 30,')],
    )))

fail = []
def check(name, got, want):
    ok = got == want
    print(('PASS' if ok else 'FAIL'), name, 'got=', got, 'want=', want)
    if not ok: fail.append(name)

# Controls: filed pages still map as committed.
for source, locator, statement, expected in FILED_PAGES:
    text, table = _filed_table(source, locator)
    assert _column_periods(table.headers, FILED_PERIODS) == expected
    assert {_statement(l.caption, text) for l in table.lines} == {statement}
print('filed controls PASS', len(FILED_PAGES))

# H01
six = period('six', 'YTD', '2026-01-01', '2026-06-30', 2)
nine = period('nine', 'YTD', '2025-10-01', '2026-06-30', 3)
h = ('Six Months Ended June 30,', '(In millions) | 2026')
check('H01 six-month header, correct 181-day period', _column_periods(h, (six,)), (frozenset({'six'}),))
check('H01 six-month header, 273-day period refused', _column_periods(h, (nine,)), None)
check('H01 six-month header, both -> six only', _column_periods(h, (six, nine)), (frozenset({'six'}),))

# H02
text = '''CONSOLIDATED STATEMENTS OF OPERATIONS
Years Ended December 31,
(In millions) | December 31, 2025 | December 31, 2024
Net revenues | 120 | 100'''
t = extract_statement_lines(text, 'page:1', 'filing')
print('H02 extracted headers:', t.headers, 'values:', t.lines[0].values)
fy25 = period('fy25', 'FY', '2025-01-01', '2025-12-31')
fy24 = period('fy24', 'FY', '2024-01-01', '2024-12-31')
q425 = period('q425', 'QUARTER', '2025-10-01', '2025-12-31', 4)
q424 = period('q424', 'QUARTER', '2024-10-01', '2024-12-31', 4)
check('H02 annual header, quarters refused', _column_periods(t.headers, (q425, q424)), None)
fyq = _column_periods(t.headers, (fy25, fy24, q425, q424))
check('H02 annual header, FY+Q4 -> FY only', fyq, (frozenset({'fy25'}), frozenset({'fy24'})))

# H08
cash = '''CONSOLIDATED STATEMENTS OF CASH FLOWS
Six Months Ended June 30,
(In millions) | 2026 | 2025
ADJUSTMENTS TO RECONCILE NET INCOME TO NET CASH PROVIDED BY OPERATING ACTIVITIES:
Depreciation | 35 | 30'''
ct = extract_statement_lines(cash, 'page:2', 'filing')
print('H08 caption:', repr(ct.lines[0].caption), 'label:', ct.lines[0].label)
check('H08 reconciliation caption on CFS page', _statement(ct.lines[0].caption, cash), 'CFS')

print('FAILED:', fail)
sys.exit(1 if fail else 0)
