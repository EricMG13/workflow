"""T5 review probe 1: a lone surrogate in the TOOL NAME (not arguments), and a non-str tool.
Exit 1 if any frame desynchronises the session (good frame after it is not ok)."""
import json, sys
from common_run import run, GOOD

frames = {
    "surrogate_tool": '{"operation":"invoke","tool":"\\ud800","arguments":{"query":"x"}}',
    "surrogate_tool_bad_args": '{"operation":"invoke","tool":"\\udfff","arguments":[1]}',
    "int_tool": '{"operation":"invoke","tool":5,"arguments":{"query":"x"}}',
    "list_tool": '{"operation":"invoke","tool":["search_pack"],"arguments":{"query":"x"}}',
    "nul_tool": '{"operation":"invoke","tool":"search_pack\\u0000","arguments":{"query":"x"}}',
}
bad = 0
for kind in ("owner", "financial"):
    for name, frame in frames.items():
        states, _, w = run(kind, [frame, GOOD])
        ok = states[-1] == ("ok", None)
        bad |= not ok
        print(kind, name, states, "host_seq", getattr(w._session, "_sequence", None),
              "epoch", len(w._epoch_calls), "OK" if ok else "DESYNC")
sys.exit(1 if bad else 0)
