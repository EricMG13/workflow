"""T5 fix-2 review probe 5: does a host refusal receipt REPLAY? Receipt verification
(owner `_verify_calls_reads`, financial `_verify`) re-invokes each retained call as
`fresh_session.invoke(call.tool, call.arguments)` and requires equality (call_id aside).
Mirrors that loop (owner: the real `_verify_calls_reads`; financial: its inline loop).
Exit 1 if any retained call of a frame fails replay (sealed receipt would be unverifiable)."""
import sys
from types import SimpleNamespace
from common_run import run, GOOD
import deploy_workflow.owner_workflow as ow
import deploy_workflow.financial_workflow as fw
from deploy_workflow.host import SourceSession
from deploy_workflow.workflow import WorkflowError

frames = {
    "surrogate_tool": '{"operation":"invoke","tool":"\\ud800","arguments":{"query":"x"}}',
    "surrogate_tool_bad_args": '{"operation":"invoke","tool":"\\udfff","arguments":[1]}',
    "surrogate_tool_good_name_like": '{"operation":"invoke","tool":"read_pages\\ud800","arguments":{"source_id":"identity","first_page":1,"last_page":1}}',
    "control_int_tool": '{"operation":"invoke","tool":5,"arguments":{"query":"x"}}',
    "control_surrogate_query": '{"operation":"invoke","tool":"search_pack","arguments":{"query":"\\ud800"}}',
}

def replay_financial(store, calls):
    replayed = {}
    for call in calls:
        key = call.binding.content_hash()
        if key not in replayed:
            replayed[key] = SourceSession.from_execution(fw._historical(store, call.binding), call.binding.ticket_id, call.binding.step_id)
        exp = fw._parse(fw.FinancialCall, replayed[key].invoke(call.tool, call.arguments))
        if exp.model_copy(update={"call_id": call.call_id}) != call:
            return ("MISMATCH", call.tool, call.error_code, "replayed->", exp.tool, exp.error_code)
    return ("REPLAYS",)

def replay_owner(store, calls):
    try:
        ow._verify_calls_reads(store, SimpleNamespace(calls=tuple(calls), input_reads=()), ow.OWNER_SPECS)
        return ("REPLAYS",)
    except WorkflowError as e:
        return ("MISMATCH", e.code, [(c.tool, c.status, c.error_code) for c in calls])

bad = 0
for kind in ("owner", "financial"):
    for name, frame in frames.items():
        states, _, w = run(kind, [frame, GOOD])
        res = (replay_owner if kind == "owner" else replay_financial)(w._store, w._calls)
        bad |= res[0] != "REPLAYS"
        print(kind, name, states, res)
sys.exit(1 if bad else 0)
