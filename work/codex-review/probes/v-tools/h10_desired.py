"""H10 desired: the CP-DR bracket regression must FAIL under a display mutant. Exit 1 while it survives."""
import importlib, sys
from unittest.mock import patch
import test_connect_cpdr as dr
r = importlib.import_module("deploy_vii.render")
dr.test_a_question_with_a_bracketed_citation_renders_as_written()  # control: unmutated passes
rd, rt = r.display, r.table_display
hits = []
def display(f):
    if f.text and "[sic]?" in f.text:
        hits.append("display"); return "QUESTION DROPPED BY MUTANT"
    return rd(f)
def table(f, g):
    if f.text and "[sic]?" in f.text:
        hits.append("table"); return "QUESTION DROPPED BY MUTANT"
    return rt(f, g)
with patch.object(r, "display", display), patch.object(r, "table_display", table):
    try:
        dr.test_a_question_with_a_bracketed_citation_renders_as_written()
    except AssertionError:
        print("OK: mutant killed"); sys.exit(0)
assert hits, "mutant never applied"
print("DEFECT: display mutant survived; mutant applied", sorted(set(hits)))
sys.exit(1)
