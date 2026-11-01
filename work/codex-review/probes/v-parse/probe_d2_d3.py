"""D2/D3 probe against HEAD statement_extract + financial_workflow precheck guard.
Asserts DESIRED behaviour: exits non-zero while a misparse is present."""
import sys
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from deploy_vii.statement_extract import extract_statement_lines
import deploy_workflow.financial_workflow as fw

PAGE = "\n".join([
    "CONSOLIDATED STATEMENTS OF OPERATIONS",
    "(In millions)            Years Ended December 31,",
    "                              2025        2024",
    "Net revenues                  2025        1998",   # D2: year-like amounts
    "Cost of revenues  (1)          900         800",   # D3: footnote marker 2 spaces before values
    "Operating income               1125        1198",
    "Weighted average shares        2010        1985",   # D2 again, mid-table
    "Net income                      700         650",
])

def per(pid, kind, end, fy):
    return SimpleNamespace(period_id=pid, period_type=kind, end_date=end, fiscal_year=fy,
                           fiscal_quarter=None)

t = extract_statement_lines(PAGE, "page:1", source_id="S1")
print("headers:", t.headers)
for ln in t.lines:
    print("line", ln.line_no, repr(ln.label), ln.raw_values, [str(v) for v in ln.values], ln.flags)
labels = {ln.label for ln in t.lines}
periods = (per("fy25", "FY", date(2025, 12, 31), "FY2025"), per("fy24", "FY", date(2024, 12, 31), "FY2024"))
cols = fw._column_periods(t.headers, periods)
print("columns:", cols)

fail = []
# D2: year-like data rows must be extracted, not dropped
for want in ("Net revenues", "Weighted average shares"):
    if want not in labels:
        fail.append(f"D2: printed row {want!r} omitted by extractor")
# D2b: omitted year-like row must not enter the header block
if any("Net revenues" in h or "Weighted" in h for h in t.headers):
    fail.append("D2b: year-like data row taken into headers")
# D3: footnote marker must not become a value
cost = next((ln for ln in t.lines if ln.label.startswith("Cost of revenues")), None)
if cost is None:
    fail.append("D3: cost row missing")
else:
    if Decimal("-1") in cost.values:
        fail.append(f"D3: footnote (1) parsed as value -1: values={[str(v) for v in cost.values]} flags={cost.flags}")
    # downstream: financial_workflow.py:_evidence_issues skips a book when
    # `columns is None or len(columns) != len(extracted.values)` -> line can never be covered
    if cols is not None and len(cols) != len(cost.values):
        fail.append(f"D3-downstream: len(columns)={len(cols)} != len(values)={len(cost.values)} -> precheck reports "
                    "'Uncovered extracted statement line' for any payload (fail-closed refusal)")
for f in fail:
    print("FAIL", f)
sys.exit(1 if fail else 0)
