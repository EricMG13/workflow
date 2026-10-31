"""T5 review probe 3: depth at/over the bound as dicts vs lists vs mixed, empty containers at
depth 101, and write_receipt after a retained depth-100 call (compared with a baseline).
Exit 1 if any bound-or-below frame desynchronises or the receipt outcome differs from baseline."""
import json, sys
from common_run import run, GOOD, RECEIPT

def s(args_json):
    return '{"operation":"invoke","tool":"search_pack","arguments":' + args_json + '}'

def lists(n): return "[" * n + "0" + "]" * n
def dicts(n): return '{"a":' * n + "0" + "}" * n
def mixed(n):
    opens = ["[" if i % 2 == 0 else '{"a":' for i in range(n)]
    closes = ["]" if i % 2 == 0 else "}" for i in range(n)][::-1]
    return "".join(opens) + "0" + "".join(closes)
def empty_lists(n): return "[" * n + "]" * n

frames = {}
for d in (100, 101):
    frames[f"lists_{d}"] = s('{"query":"x","e":' + lists(d - 1) + '}')
    frames[f"dicts_{d}"] = s('{"query":"x","e":' + dicts(d - 1) + '}')
    frames[f"mixed_{d}"] = s('{"query":"x","e":' + mixed(d - 1) + '}')
    frames[f"empty_{d}"] = s('{"query":"x","e":' + empty_lists(d - 1) + '}')
frames["lists_5000"] = s('{"query":"x","e":' + lists(5000) + '}')
frames["lists_100000"] = s('{"query":"x","e":' + lists(100000) + '}')
bad = 0
for kind in ("owner", "financial"):
    base, base_r, _ = run(kind, [GOOD, RECEIPT])
    print(kind, "baseline", base)
    for name, frame in frames.items():
        states, replies, w = run(kind, [frame, GOOD, RECEIPT])
        args = replies[0].get("arguments")
        retained = None if args is None else ("{}" if args == {} else "full")
        ok = states[1] == ("ok", None) and states[2][0] == base[1][0]
        bad |= not ok
        print(kind, name, states, "args", retained, "host_seq", getattr(w._session, "_sequence", None),
              "epoch", len(w._epoch_calls), "OK" if ok else "BROKEN")
sys.exit(1 if bad else 0)
