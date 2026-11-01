"""D2 on an IFRS-style header row 'Notes  2025  2024': base reads it as a header, head as a data
line, so headers lose the years. Exit 1 if the head returns it as data."""
import importlib.util, sys
s = importlib.util.spec_from_file_location("b", "/private/tmp/claude-501/s8vii-final/base_statement_extract.py")
b = importlib.util.module_from_spec(s); s.loader.exec_module(b)
from deploy_vii.statement_extract import extract_statement_lines as head
page = "\n".join([
    "CONSOLIDATED INCOME STATEMENT",
    "                       Notes        2025        2024",
    "Revenue                    4       1,200       1,000",
    "Cost of sales                       (700)       (600)",
])
for name, f in (("base", b.extract_statement_lines), ("head", head)):
    t = f(page, "page:1")
    print(name, "headers=", [h.strip() for h in t.headers], "lines=", [(l.label, l.raw_values, l.flags) for l in t.lines])
sys.exit(1 if any(l.label == "Notes" for l in head(page, "page:1").lines) else 0)
