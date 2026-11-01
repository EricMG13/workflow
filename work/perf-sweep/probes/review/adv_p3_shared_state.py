"""Adversary probe (P3): is state written through one `result()` object visible to later reads?

Usage: python -I adv_p3_shared_state.py <tree> <scratch-dir>
  <tree>: `git archive <rev> src` (67e0c51 = before P3, 4af08ce = after P3).
Each later `result()` is fresh before P3 and the shared cached object after it. Two writes
that bypass `frozen=True` are tried: the public `model_fields_set` set (pydantic returns the
live set) and `object.__setattr__`. Prints what a second, independent reader then sees.
"""

import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, sys.argv[1] + "/src")
from deploy_vii import execution  # noqa: E402
from deploy_vii.contracts import Fact, Module  # noqa: E402

assert execution.__file__.startswith(sys.argv[1]), execution.__file__
root = Path(sys.argv[2]) / "adv-p3-shared"
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

first = store.result(sha)
print("model_fields_set is live:", first.model_fields_set is first.__pydantic_fields_set__)
first.model_fields_set.discard("status")
second = store.result(sha)
print("A. second reader exclude_unset keys:", sorted(second.model_dump(exclude_unset=True)))

object.__setattr__(first, "status", "blocked")
third = store.result(sha)
print("B. third reader status:", third.status, "| canonical:", third.content_hash() == sha)
shutil.rmtree(root)
