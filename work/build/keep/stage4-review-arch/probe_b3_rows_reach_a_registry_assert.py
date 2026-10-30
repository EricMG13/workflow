"""Class B probe: every parametrised row of test_tool_use_sections_match_registrations reaches at
least one registry assertion beyond `spec.kind == "analytical"`. Run from the extracted tree with
PYTHONPATH=src:tests. Exit 1 if any row is vacuous or SECTIONS is empty."""

import sys

import test_owner_stage4 as t

rows = t.SECTIONS
if not rows:
    print("SECTIONS is empty")
    sys.exit(1)
vacuous = []
for oracle, module, text in rows:
    hits = []
    if module in t.PACK_TOOL_MODULES:
        hits.append("pack-tool scope")
    if any(p in text for p in t.SUBMIT_ONLY):
        hits.append("submit-only")
    if "ok read_pages" in text and not any(p in text for p in t.SUBMIT_ONLY):
        hits.append("host scope")
    if "zero read_inputs" in text:
        hits.append("no inputs")
    elif "read_inputs" in text and t.READS_INPUTS.search(text):
        hits.append("views row")
    print(f"{oracle}:{module}: {hits}")
    if not hits:
        vacuous.append((oracle, module))
print(f"rows={len(rows)} vacuous={vacuous}")
sys.exit(1 if vacuous else 0)
