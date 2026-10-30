"""Adversary probe (P3): concurrent cold `result()` calls from 8 threads on one blob.

Usage: python -I adv_p3_threads.py <tree> <scratch-dir>
  <tree>: `git archive 4af08ce src`. A 4,000-fact module keeps one parse slow enough for the
  threads to overlap. Reports how many parses ran and how many distinct objects came back;
  exit 0 when every thread got a Module equal to the canonical one with no exception and the
  cache holds exactly one entry.
"""

import shutil
import sys
import threading
from datetime import date
from pathlib import Path

sys.path.insert(0, sys.argv[1] + "/src")
from deploy_vii import execution  # noqa: E402
from deploy_vii.contracts import Fact, Module  # noqa: E402

assert execution.__file__.startswith(sys.argv[1]), execution.__file__
root = Path(sys.argv[2]) / "adv-p3-threads"
shutil.rmtree(root, ignore_errors=True)
(root / "blobs").mkdir(parents=True)
store = execution.Execution(root)
module = Module(
    run_id="run-1",
    issuer_id="issuer-1",
    as_of=date(2026, 1, 1),
    module_id="CP-0",
    facts=tuple(Fact(fact_id=f"f{i}", label=f"f{i}", text="x" * 50) for i in range(4000)),
)
sha = store._store(module.model_dump_json())
execution._canonical_result.cache_clear()
parse = Module.model_validate_json
parses: list[int] = []


def counted(raw, *args, **kwargs):  # type: ignore[no-untyped-def]
    parses.append(1)
    return parse(raw, *args, **kwargs)


Module.model_validate_json = counted  # type: ignore[method-assign]
barrier = threading.Barrier(8)
results: list[object] = []
errors: list[BaseException] = []


def worker() -> None:
    barrier.wait()
    try:
        results.append(store.result(sha))
    except BaseException as error:  # recorded and asserted below, never swallowed
        errors.append(error)


threads = [threading.Thread(target=worker) for _ in range(8)]
for t in threads:
    t.start()
for t in threads:
    t.join()
del Module.model_validate_json
assert not errors, errors
assert len(results) == 8 and all(r == module for r in results)
assert execution._canonical_result.cache_info().currsize == 1
print(f"parses={len(parses)} distinct_objects={len({id(r) for r in results})} ok")
shutil.rmtree(root)
