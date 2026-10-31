"""T4 plan probe (read-only, stdlib only): what the CZR quality_scope keeps from the kept
full QualityInputs read (`read-3-quality.txt`), without the deploy_vii import (system python3
has no pypdf). It rebuilds every scope key except `evidence[*].record` (that needs the
narrative catalogue), grouping `qa-cell:` slots by the table/status their rationale states.

Usage: python3 -I probe_scope_size.py <read-3-quality.txt>
"""

import json
import sys
from collections import Counter
from pathlib import Path

raw = Path(sys.argv[1]).read_bytes()
inputs = json.loads(raw)
print("full_bytes", len(raw))
kinds = Counter(c["field_id"].split(":", 1)[0] for c in inputs["coverage"])
print("coverage", len(inputs["coverage"]), dict(kinds))
print("references", len(inputs["references"]), "ceilings", len(inputs["ceilings"]))
ceilings = {c["evidence_id"]: c for c in inputs["ceilings"]}
slots = [c for c in inputs["coverage"] if not c["field_id"].startswith("qa-cell:")]
cells: Counter = Counter()
for c in inputs["coverage"]:
    if c["field_id"].startswith("qa-cell:"):
        table = c["rationale"].split("/", 1)[0]
        status = c["rationale"].split(": ", 1)[1].split(";", 1)[0]
        cells[(table, status, c["present"])] += 1
claim_ids = list(dict.fromkeys(e for c in inputs["claims"] for e in c["evidence_ids"]))
scope = {
    "coverage_policy": inputs["coverage_policy"],
    "source_gate": inputs["source_gate"],
    "module_status": inputs["module_status"],
    "claims": inputs["claims"],
    "evidence": [
        {k: ceilings[e][k] for k in ("evidence_id", "ceiling", "basis")} for e in claim_ids
    ],
    "coverage_slots": slots,
    "coverage_cells": [
        {"table_id": t, "status": s, "present": p, "slots": n}
        for (t, s, p), n in sorted(cells.items())
    ],
    "references_by_basis": dict(Counter(c["basis"] for c in inputs["ceilings"])),
    "inherited_findings": inputs.get("inherited_findings", []),
}
body = json.dumps(scope, sort_keys=True, separators=(",", ":"))
print("scope_without_records_bytes", len(body.encode()))
print("non_cell_slots", len(slots), "cell_groups", len(cells), "claim_evidence", len(claim_ids))
present = sum(s["present"] for s in slots) + sum(n for (_, _, p), n in cells.items() if p)
total = len(slots) + sum(cells.values())
full_present = sum(c["present"] for c in inputs["coverage"])
print("coverage_from_scope", present, total, "full", full_present, len(inputs["coverage"]))
assert (present, total) == (full_present, len(inputs["coverage"]))
