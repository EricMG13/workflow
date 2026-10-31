"""D1: printed rows the rules cannot parse are omitted (desired: surfaced/counted somewhere).
D3 control: flag fires on the footnote row only when no year-like row inflates the header year count.
Exits non-zero while an omitted printed row is silent."""
import sys
from deploy_vii.statement_extract import extract_statement_lines

PAGE = "\n".join([
    "CONSOLIDATED BALANCE SHEETS",
    "                         December 31, 2025    December 31, 2024",
    "Cash and equivalents  (1)          500             400",
    "Goodwill                           120",            # single value (other column blank)
    "Inventories                        n/m             300",  # non-numeric cell
    "Total assets 9,100 8,900",                           # single-space separated
    "Total liabilities                  4,000           3,900",
])
t = extract_statement_lines(PAGE, "page:1", source_id="S1")
print("headers:", t.headers)
for ln in t.lines:
    print("line", ln.line_no, repr(ln.label), ln.raw_values, ln.flags)
labels = [ln.label for ln in t.lines]
fail = []
cash = next(ln for ln in t.lines if ln.label.startswith("Cash"))
print("D3 control flags on cash row:", cash.flags)
for want in ("Goodwill", "Inventories", "Total assets"):
    if not any(l.startswith(want) for l in labels):
        fail.append(f"D1: printed row {want!r} omitted silently (ExtractedTable has no omitted-line field)")
for f in fail:
    print("FAIL", f)
sys.exit(1 if fail else 0)
