"""Task 2 review probe: old vs new Execution.result give identical results/errors, every call.

Old implementation is the verbatim 67e0c51 body. Exit 0 = all equivalent.
"""
import hashlib
import sys
import tempfile
from datetime import date
from pathlib import Path

from deploy_vii.contracts import Module
from deploy_vii.execution import Execution, _canonical_result


def old_result(self, sha256):
    module = Module.model_validate_json(self._load(sha256))
    if module.content_hash() != sha256:
        raise ValueError("Execution result blob is not the canonical module")
    return module


def outcome(fn, store, sha):
    try:
        m = fn(store, sha)
        return ("ok", m.model_dump_json())
    except Exception as e:  # probe records the outcome for comparison
        return (type(e).__name__, str(e))


fail = 0
assert _canonical_result.cache_info().maxsize == 4, "cache ceiling is not 4"
root = Path(tempfile.mkdtemp())
store = Execution(root)
(root / "blobs").mkdir()
mod = Module(run_id="run-1", issuer_id="issuer-1", as_of=date(2026, 1, 1), module_id="CP-0")
good = store._store(mod.model_dump_json())
noncanon = store._store(mod.model_dump_json() + " ")
badjson = store._store("{not json")
other = store._store('{"a": 1}')
missing = hashlib.sha256(b"nothing").hexdigest()
cases = {"good": good, "noncanon": noncanon, "badjson": badjson, "otherjson": other,
         "missing": missing, "badformat": "XYZ", "upper": good.upper()}
for name, sha in cases.items():
    olds = [outcome(old_result, store, sha) for _ in range(3)]
    news = [outcome(Execution.result, store, sha) for _ in range(3)]
    same = olds == news and len(set(news)) == 1
    print(name, "OK" if same else "DIFF", news[0][0], news[0][1][:80])
    fail |= not same
# tamper after cached hit
Execution.result(store, good)
p = root / "blobs" / good
p.chmod(0o644)
p.write_bytes(p.read_bytes() + b" ")
o, n = outcome(old_result, store, good), outcome(Execution.result, store, good)
print("tampered", "OK" if o == n else "DIFF", n)
fail |= o != n
print("cache", _canonical_result.cache_info())
sys.exit(1 if fail else 0)
