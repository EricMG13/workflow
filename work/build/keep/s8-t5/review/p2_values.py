"""T5 review probe 2: values in arguments: NUL, valid surrogate pair, huge int, overflow float,
NaN literal, -0.0, tiny float, wide-but-shallow list. Exit 1 if any desynchronises."""
import json, sys
from common_run import run, GOOD

def s(args_json):
    return '{"operation":"invoke","tool":"search_pack","arguments":' + args_json + '}'

frames = {
    "nul_value": s('{"query":"a\\u0000b"}'),
    "nul_key": s('{"query":"x","\\u0000":1}'),
    "pair_escaped": s('{"query":"\\ud83d\\ude00"}'),
    "pair_raw": s('{"query":"\U0001F600"}'),
    "reversed_pair": s('{"query":"\\ude00\\ud83d"}'),
    "big_int_4000": s('{"query":"x","n":' + "9" * 4000 + '}'),
    "big_int_4301": s('{"query":"x","n":' + "9" * 4301 + '}'),
    "neg_big_int": s('{"query":"x","n":-' + "9" * 4000 + '}'),
    "float_overflow": s('{"query":"x","n":1e400}'),
    "nan_literal": s('{"query":"x","n":NaN}'),
    "neg_zero": s('{"query":"x","n":-0.0}'),
    "tiny_float": s('{"query":"x","n":1e-400}'),
    "u64_plus": s('{"query":"x","n":18446744073709551616}'),
    "wide_list": s('{"query":"x","n":[' + ",".join(["0"] * 1_500_000) + ']}'),
    "wide_dict": s('{"query":"x","n":{' + ",".join(f'"k{i}":0' for i in range(200_000)) + '}}'),
}
bad = 0
for kind in ("owner", "financial"):
    for name, frame in frames.items():
        states, _, w = run(kind, [frame, GOOD])
        ok = states[-1] == ("ok", None)
        bad |= not ok
        print(kind, name, len(frame), states, "host_seq", getattr(w._session, "_sequence", None),
              "epoch", len(w._epoch_calls), "OK" if ok else "DESYNC")
sys.exit(1 if bad else 0)
