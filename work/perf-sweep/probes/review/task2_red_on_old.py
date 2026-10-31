"""Task 2 review probe: the parse-count check fails with the 67e0c51 `result` body.

Exit 0 = old body parses twice (test would fail on old code) and new body parses once.
"""
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


def count(fn):
    _canonical_result.cache_clear()
    root = Path(tempfile.mkdtemp())
    (root / "blobs").mkdir()
    store = Execution(root)
    sha = store._store(Module(run_id="r", issuer_id="i", as_of=date(2026, 1, 1),
                              module_id="CP-0").model_dump_json())
    parse = Module.model_validate_json
    calls = []

    def counted(raw, *a, **k):
        calls.append(raw)
        return parse(raw, *a, **k)

    Module.model_validate_json = counted
    try:
        fn(store, sha); fn(store, sha)
    finally:
        del Module.model_validate_json
    return len(calls)


old, new = count(old_result), count(Execution.result)
print("old", old, "new", new)
sys.exit(0 if (old, new) == (2, 1) else 1)
