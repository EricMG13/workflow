"""D3 false positive: a 2-year table with a printed change column; a genuine small negative in the
first year column is dropped as a 'footnote marker', shifting the row's values. Exit 1 if dropped."""
import sys
from decimal import Decimal
from deploy_vii.statement_extract import extract_statement_lines
page = "\n".join([
    "                                    Year ended December 31,",
    "                                    2025        2024      Change",
    "Revenues                            1,200       1,000       200",
    "Other income (expense), net           (12)         (8)        (4)",
    "Income tax benefit (provision)        (5)         10        (15)",
])
t = extract_statement_lines(page, "page:1")
rc = 0
for line in t.lines:
    print(line.label, line.raw_values, line.flags)
    if "footnote_marker" in line.flags:
        rc = 1
print("headers:", t.headers)
sys.exit(rc)
