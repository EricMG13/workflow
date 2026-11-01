"""Adversary probe (P1): `_operands` on the real 44 MB CP-1 blob, E-QOQ-FLAT parameters.

Usage: python -I adv_p1_real_cp1_operands.py <tree> <blob> [points]
  [points]: N keeps the first N report points, A:B keeps points[A:B] (the before-P1 tree hashes the 44 MB producer
  once per reference, about 0.17 s each, so 276 references take ~50 s; 6 points keep it < 60 s).
  <tree>: a `git archive <rev> src` extraction (2ded26c = before P1, 17e07ba = after P1).
Prints the reference count, how often the producer was hashed, the elapsed seconds, and the
sha256 of the canonical JSON of the whole lineage tuple. Exit 0 only when every FactReference
carries the blob's own sha256 and the producer hash is stable across calls.
"""

import dataclasses
import hashlib
import json
import sys
import time

sys.path.insert(0, sys.argv[1] + "/src")
from deploy_vii.contracts import Module, ModuleView  # noqa: E402
from deploy_workflow import earnings_workflow as core  # noqa: E402
from deploy_workflow.earnings import build_earnings_delta  # noqa: E402

assert core.__file__.startswith(sys.argv[1]), core.__file__
raw = open(sys.argv[2], "rb").read()
sha = hashlib.sha256(raw).hexdigest()
producer = Module.model_validate_json(raw)
assert producer.content_hash() == sha == producer.content_hash(), "producer hash unstable"
view = ModuleView(
    module_id="CP-1",
    title="Financials",
    aliases=(),
    status=producer.status,
    artifact_sha256=sha,
    facts=producer.facts,
    tables=producer.tables,
    claims=producer.claims,
    limitations=(*producer.limitations, *producer.inherited_limitations),
)
report = build_earnings_delta(view, "q3-2025", "q4-2025")  # _case_parameters: slice-cp1b-flat-v1
if len(sys.argv) > 3:
    a, _, b = sys.argv[3].rpartition(":")
    report = dataclasses.replace(report, points=report.points[int(a or 0) : int(b)])

calls = 0
original = Module.content_hash


def counting(self: Module) -> str:
    global calls
    if self is producer:
        calls += 1
    return original(self)


Module.content_hash = counting  # type: ignore[method-assign]
start = time.perf_counter()
lineages = core._operands(producer, report)
elapsed = time.perf_counter() - start
del Module.content_hash

refs = [
    ref
    for lin in lineages
    for ref in (
        *(() if lin.prior is None else (lin.prior.fact,)),
        lin.current.fact,
        *lin.companions,
    )
]
assert {r.producer_sha256 for r in refs} == {sha}, "a reference carries another producer hash"
digest = hashlib.sha256(
    json.dumps([json.loads(lin.model_dump_json()) for lin in lineages], sort_keys=False).encode()
).hexdigest()
print(f"points={len(report.points)} refs={len(refs)} producer_hashes={calls} "
      f"elapsed={elapsed:.2f}s lineage_sha256={digest}")
