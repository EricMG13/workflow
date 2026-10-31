"""P2 probe: _IntegrityCatalog.ref() cost with the real CZR CP-1 register module (37k facts).

Desired behaviour: ref() cost independent of producer size (hash once per catalog).
Exits 1 while 100 ref() calls on the real-size producer take > 0.5 s.
"""
import sys, time
from pathlib import Path
from deploy_vii.contracts import Module
from deploy_workflow.tools.upstream import _IntegrityCatalog

raw = Path(sys.argv[1]).read_text()
t = time.perf_counter(); real = Module.model_validate_json(raw); decode = time.perf_counter() - t
real = real.model_copy(update={"status": "accepted"}) if real.status != "accepted" else real
print(f"real CP-1: facts={len(real.facts)} bytes={len(raw)} decode_ms={decode*1000:.0f}")

def catalog(head):
    c = object.__new__(_IntegrityCatalog)  # real method, attributes as __init__ sets them
    c.heads = {head.module_id: head}
    c.facts = {(head.module_id, f.fact_id): f for f in head.facts}
    c.claims = {}
    return c

def time_refs(head, n):
    c = catalog(head)
    ids = [f.fact_id for f in head.facts][:n]
    t = time.perf_counter()
    out = [c.ref(head.module_id, "fact", i) for i in ids]
    assert all(o["producer_sha256"] == out[0]["producer_sha256"] for o in out)
    return time.perf_counter() - t

for n in (100, 400, 800):  # Codex's sizes: producer with n facts, n refs
    small = real.model_copy(update={"facts": real.facts[:n], "tables": ()})
    print(f"synthetic n={n}: {n} refs {time_refs(small, n)*1000:.0f} ms")
real_100 = time_refs(real, 100)
print(f"real 37k-fact producer: 100 refs {real_100*1000:.0f} ms ({real_100*10:.1f} ms/ref)")
sys.exit(1 if real_100 > 0.5 else 0)
