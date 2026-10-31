"""Adversary probe (P3): `Execution.result` on the real 44 MB CP-1 blob, cold vs. warm cache.

Usage: python -I adv_p3_real_blob_cache.py <tree> <blob> <scratch-dir>
  <tree>: a `git archive 4af08ce src` extraction (the P3 commit).
Checks, in one process:
  1. a warm hit returns a Module equal to an independent fresh parse: same type, same
     model_dump_json bytes (== the blob), same fields_set;
  2. the warm hit is the *same object* as the cold result (identity change vs. before P3);
  3. the lru_cache key keeps the raw blob bytes alive (refcount rises by one);
  4. tamper after a warm hit: one changed byte, the bytes of another canonical module under
     the old name, and a deleted blob all refuse with the pre-P3 messages;
  5. timing of the cold and warm calls.
Exit 0 only when 1, 3 and 4 hold (2 is reported, not asserted either way).
"""

import hashlib
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, sys.argv[1] + "/src")
from deploy_vii import execution  # noqa: E402
from deploy_vii.contracts import Module  # noqa: E402

assert execution.__file__.startswith(sys.argv[1]), execution.__file__
blob = Path(sys.argv[2])
sha = blob.name
root = Path(sys.argv[3]) / "adv-p3-store"
shutil.rmtree(root, ignore_errors=True)
(root / "blobs").mkdir(parents=True)
shutil.copyfile(blob, root / "blobs" / sha)
store = execution.Execution(root)
execution._canonical_result.cache_clear()

t0 = time.perf_counter()
cold = store.result(sha)
t1 = time.perf_counter()
warm = store.result(sha)
t2 = time.perf_counter()
print(f"cold={t1 - t0:.2f}s warm={t2 - t1:.3f}s same_object={warm is cold}")

raw = blob.read_bytes()
fresh = Module.model_validate_json(raw)
assert type(warm) is Module
assert warm == fresh
assert warm.model_dump_json().encode() == raw == fresh.model_dump_json().encode()
assert warm.model_fields_set == fresh.model_fields_set
print("1. warm hit equals an independent parse: ok")

execution._canonical_result.cache_clear()
loaded = store._load(sha)
before = sys.getrefcount(loaded)
execution._canonical_result(sha, loaded)
after = sys.getrefcount(loaded)
print(f"3. raw bytes refcount {before} -> {after} (cache key retains {len(loaded):,} bytes)")
assert after == before + 1
del loaded

path = root / "blobs" / sha
path.chmod(0o644)
path.write_bytes(raw[:-2] + b" }" if raw.endswith(b"}") else raw + b" ")
try:
    store.result(sha)
    raise SystemExit("tampered blob was accepted")
except ValueError as error:
    assert str(error) == f"Execution blob {sha} hash mismatch", error
other = fresh.model_copy(update={"run_id": "adversary-other-run"}).model_dump_json().encode()
assert Module.model_validate_json(other).model_dump_json().encode() == other
path.write_bytes(other)
try:
    store.result(sha)
    raise SystemExit("another canonical module under the old name was accepted")
except ValueError as error:
    assert str(error) == f"Execution blob {sha} hash mismatch", error
path.unlink()
try:
    store.result(sha)
    raise SystemExit("missing blob was accepted")
except ValueError as error:
    assert str(error) == f"Execution blob {sha} is missing", error
print("4. tamper / swap / delete after a warm hit refuse with the pre-P3 messages: ok")
shutil.rmtree(root)
