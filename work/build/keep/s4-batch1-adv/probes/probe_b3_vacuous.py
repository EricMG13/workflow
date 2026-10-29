"""Count the B3 conformance rows that reach no conditional assertion (only `kind == analytical`)."""
import sys

import test_owner_stage4 as s

vacuous = []
for oracle, module, text in s.SECTIONS:
    hits = []
    if any(p in text for p in s.SUBMIT_ONLY):
        hits.append("submit-only")
    if "ok read_pages" in text and not any(p in text for p in s.SUBMIT_ONLY):
        hits.append("read_pages")
    if "zero read_inputs" in text:
        hits.append("zero-read_inputs")
    elif "read_inputs" in text and s.READS_INPUTS.search(text):
        hits.append("read_inputs")
    if not hits:
        vacuous.append((oracle, module, text[:160]))
    print(oracle, module, hits)
print("rows", len(s.SECTIONS), "vacuous", len(vacuous))
for v in vacuous:
    print("VACUOUS", v)
sys.exit(0)
