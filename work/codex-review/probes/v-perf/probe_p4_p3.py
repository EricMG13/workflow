"""P3(upstream)/P4 probe on the real CZR CP-1 register module (37k facts, 38 MB).

Measures per-tool-call costs at HEAD:
- P4a: CP-5 _integrity_lookup's full sort (upstream.py:1731) per request
- P4b: CP-1B _projection_page's full scan with _coordinate per fact (upstream.py:562)
- P3u: per-_context producer re-authentication: Execution.result re-hash + decode + content_hash
Exits 1 if the per-call producer re-authentication exceeds 100 ms (desired: memoised by digest).
"""
import sys, time, hashlib
from pathlib import Path
from deploy_vii.contracts import Module
from deploy_workflow.tools.upstream import _coordinate

raw = Path(sys.argv[1]).read_bytes()
m = Module.model_validate_json(raw)
def t(f, k=3):
    best = 1e9
    for _ in range(k):
        s = time.perf_counter(); f(); best = min(best, time.perf_counter() - s)
    return best * 1000
sort_ms = t(lambda: [f for f in sorted(m.facts, key=lambda f: (f.table_id, f.row_id, f.field, f.fact_id)) if f.table_id == "T4.1"])
scan_ms = t(lambda: {_coordinate(f): f for f in m.facts})
def reauth():
    assert hashlib.sha256(raw).hexdigest()
    mod = Module.model_validate_json(raw)
    mod.content_hash()
reauth_ms = t(reauth, 2)
print(f"P4a sort per lookup: {sort_ms:.0f} ms")
print(f"P4b scan per page (coordinate only, no admits): {scan_ms:.0f} ms")
print(f"P3u producer re-auth per _context: {reauth_ms:.0f} ms (x2-3 per invoke)")
sys.exit(1 if reauth_ms > 100 else 0)
