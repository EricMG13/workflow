"""Adversary probe (P3): resident memory held by `_canonical_result` alone and together with
host's own 4-entry `_PARSED_MODULES` cache, on four distinct canonical CP-1-size blobs.

Usage: python -I adv_p3_memory.py <tree> <blob> <scratch-dir>
  <tree>: `git archive 4af08ce src`. The four blobs are the real CP-1 module with run_id
  changed (each re-parses to identical bytes, so each is a valid canonical result blob).
Prints RSS (ps, MiB) after each stage; the deltas are the cache cost. Exit 0 when the
execution cache holds 4 entries and evicts on a 5th.
"""

import gc
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1] + "/src")
from deploy_vii import execution  # noqa: E402
from deploy_vii.contracts import Module  # noqa: E402
from deploy_workflow import host  # noqa: E402

assert execution.__file__.startswith(sys.argv[1]), execution.__file__


def rss() -> float:
    out = subprocess.run(["ps", "-o", "rss=", "-p", str(os.getpid())], capture_output=True)
    return int(out.stdout) / 1024


root = Path(sys.argv[3]) / "adv-p3-memory"
shutil.rmtree(root, ignore_errors=True)
(root / "blobs").mkdir(parents=True)
store = execution.Execution(root)
base = Module.model_validate_json(Path(sys.argv[2]).read_bytes())
shas = [
    store._store(base.model_copy(update={"run_id": f"adversary-{i}"}).model_dump_json())
    for i in range(5)
]
del base
gc.collect()
start = rss()
print(f"baseline rss={start:.0f} MiB")
for sha in shas[:4]:
    store.result(sha)
gc.collect()
one = rss()
info = execution._canonical_result.cache_info()
print(f"execution cache x4: rss={one:.0f} MiB (+{one - start:.0f}) {info}")
assert info.currsize == 4
parsed = host._ParsedExecution(root)
for sha in shas[:4]:
    assert parsed.result(sha) == store.result(sha)
    assert parsed.result(sha) is not store.result(sha)  # two separate parsed copies
gc.collect()
two = rss()
print(f"+ host cache x4: rss={two:.0f} MiB (+{two - one:.0f}; total +{two - start:.0f})")
store.result(shas[4])
assert execution._canonical_result.cache_info().currsize == 4
print("eviction at 5th entry: ok")
shutil.rmtree(root)
