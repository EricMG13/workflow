"""T5 root-cause probe 3: owner path (serve_json_lines frames, then the real
owner_workflow._verify_calls_reads replay, as review p5/p7). Names {offered, "", unknown,
extract_statements, unencodable} x refusals {depth, surrogate value, non-dict}; argv[1]
"current" or "proposed". Needs the review dir on PYTHONPATH for common_run.
Exit 1 if a frame desyncs or a retained call fails replay."""
import json, sys
from types import SimpleNamespace
from common_run import run, GOOD
import deploy_workflow.owner_workflow as ow
from deploy_workflow import host
from deploy_workflow.workflow import WorkflowError
from rc_fix import proposed_invoke

if sys.argv[1:] == ["proposed"]:
    host.SourceSession.invoke = proposed_invoke
deep = "[" * 105 + "]" * 105
NAMES = {"offered": '"search_pack"', "empty": '""', "unknown": '"foo"',
         "extract": '"extract_statements"', "unencodable": '"foo\\ud800"', "int": "5"}
ARGS = {"depth": '{"query":"x","e":' + deep + '}', "surrogate_val": '{"query":"\\ud800"}',
        "non_dict": "[1]"}
bad = 0
for nk, n in NAMES.items():
    for ak, a in ARGS.items():
        frame = '{"operation":"invoke","tool":' + n + ',"arguments":' + a + '}'
        states, replies, w = run("owner", [frame, GOOD])
        try:
            ow._verify_calls_reads(w._store, SimpleNamespace(calls=tuple(w._calls), input_reads=()), ow.OWNER_SPECS)
            res = "REPLAYS"
        except WorkflowError as e:  # reported, not hidden
            res = "MISMATCH " + e.code
        ok = states[-1] == ("ok", None) and res == "REPLAYS"
        bad |= not ok
        print(f"{nk:12} {ak:14} {states} {(replies[0].get('tool'), replies[0].get('arguments'))} {res}{'' if ok else '  <-- FAIL'}")
sys.exit(bad)
