"""Adversary probe (P3): `head_module` on a stale head never alters the shared cached Module.

Usage: python -I adv_p3_stale_head.py <tree> <scratch-dir>
  <tree>: `git archive 4af08ce src`. Reads the settled head (cache miss), then the same blob
through a stale head (model_copy with status/limitations), then the settled head again.
Exit 0 when the stale variant is a new object and later readers still get the blob's own
status, limitations and canonical hash.
"""

import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, sys.argv[1] + "/src")
from deploy_vii import execution  # noqa: E402
from deploy_vii.contracts import Fact, Module  # noqa: E402

assert execution.__file__.startswith(sys.argv[1]), execution.__file__
root = Path(sys.argv[2]) / "adv-p3-stale"
shutil.rmtree(root, ignore_errors=True)
(root / "blobs").mkdir(parents=True)
store = execution.Execution(root)
module = Module(
    run_id="run-1",
    issuer_id="issuer-1",
    as_of=date(2026, 1, 1),
    module_id="CP-0",
    status="accepted",
    facts=(Fact(fact_id="f1", label="f1", text="x"),),
)
sha = store._store(module.model_dump_json())
settled = execution.head_of(module)
assert settled.result_sha256 == sha
stale = settled.model_copy(update={"status": "stale", "notes": ("Upstream changed",)})
execution._canonical_result.cache_clear()

first = store.head_module(settled)
variant = store.head_module(stale)
again = store.head_module(settled)
assert variant is not first and variant.status == "stale"
assert variant.limitations == ("Upstream changed",)
assert again is first and again.status == "accepted" and again.limitations == ()
assert again.content_hash() == sha and store.result(sha).model_fields_set == first.model_fields_set
print("stale head is a copy; shared cached module unchanged: ok")
shutil.rmtree(root)
