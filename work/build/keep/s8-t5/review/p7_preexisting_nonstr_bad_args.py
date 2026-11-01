"""T5 fix-2 review probe 7 (pre-existing check, not this round): a NON-str tool with bad
arguments is refused ("", {}, bad_arguments) before 7961c63c too; does it replay on receipt
verification? Exit 1 on mismatch."""
import sys
from types import SimpleNamespace
from common_run import run, GOOD
import deploy_workflow.owner_workflow as ow
from deploy_workflow.workflow import WorkflowError

frame = '{"operation":"invoke","tool":5,"arguments":[1]}'
bad = 0
for kind in ("owner",):
    states, _, w = run(kind, [frame, GOOD])
    try:
        ow._verify_calls_reads(w._store, SimpleNamespace(calls=tuple(w._calls), input_reads=()), ow.OWNER_SPECS)
        print(kind, states, "REPLAYS")
    except WorkflowError as e:
        bad = 1
        print(kind, states, "MISMATCH", e.code)
sys.exit(bad)
