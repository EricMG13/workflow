from common import *
from deploy_vii.statement_extract import extract_statement_lines
import sys
src, page = sys.argv[1], int(sys.argv[2])
t = extract_statement_lines(PAGES[src][page-1], f"page:{page}", source_id=src)
print(t.headers)
for l in t.lines:
    print(l.line_no, repr(l.caption), repr(l.label), l.values, l.raw_values, l.flags, l.indent)
