"""Item 82 before/after: replay CZR's committed partial submissions, capture the CP-1 narrative
gap ledger, and print the refusal plus gap counts by (severity, origin, item-82 prefix).
Usage (repo root of the code under test): PYTHONPATH=src:tests <venv python> <this> <empty dir>"""
import collections, sys
from pathlib import Path
import deploy_vii.narrative as narrative, deploy_vii.downstream_readiness as dr
import czr_runs
PREFIX = "Absent input, stated as a limitation on a public filed pack (rulings item 82): "
cap = {}
real = narrative.canonical_narrative
def spy(*a, **k):
    cap["n"] = real(*a, **k)
    return cap["n"]
narrative.canonical_narrative = dr.canonical_narrative = spy
try:
    czr_runs.czr_closed(Path(sys.argv[1]), czr_runs.CASE / "submissions-partial.json")
    print("refusal: none (CP-1 closed)")
except RuntimeError as e:
    print("refusal:", str(e)[:140])
gaps = cap["n"].gaps
print("narrative status:", cap["n"].status, "| gaps:", len(gaps))
for k, v in sorted(collections.Counter((g.severity, g.origin, g.description.startswith(PREFIX)) for g in gaps).items()):
    print(f"  {k[0]:5} {k[1]:22} prefixed={k[2]!s:5} {v}")
