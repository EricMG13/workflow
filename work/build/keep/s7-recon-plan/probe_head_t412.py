"""Read the CP-1 head of a store; print its limitations and the T4.12 facts carrying the
item-82 prefix. Usage: PYTHONPATH=src .venv/bin/python <this> <store-dir>"""
import sys
from pathlib import Path
from deploy_vii.execution import Execution
from deploy_vii.contracts import Module
s = Execution(Path(sys.argv[1]))
h = next(x for x in s.read().heads if x.module_id == "CP-1")
blob = s.blob(h.result_sha256) if hasattr(s, "blob") else (Path(sys.argv[1]) / "blobs" / h.result_sha256).read_text()
m = Module.model_validate_json(blob)
print("head:", h.status); print("limitations:", [l[:90] for l in m.limitations])
rows = [f for f in m.facts if f.table_id == "T4.12" and "Absent input" in (f.text or "")]
print("T4.12 facts with prefix:", len(rows)); print(rows[0].text[:300] if rows else None)
sev = [f for f in m.facts if f.table_id == "T4.12" and f.text in ("WARN", "BLOCK")]
import collections; print("T4.12 severity cells:", collections.Counter(f.text for f in sev))
