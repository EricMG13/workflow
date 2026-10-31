import json, sys
def walk(o, path, out):
    if isinstance(o, dict):
        if "module_id" in o and isinstance(o.get("facts"), list):
            out.append((path, o["module_id"], len(o["facts"]), len(o.get("claims", []) or []), len(json.dumps(o))))
        for k, v in o.items(): walk(v, path+"/"+k, out)
    elif isinstance(o, list):
        for i, v in enumerate(o[:200]): walk(v, path+f"[{i}]", out)
for f in sys.argv[1:]:
    out = []
    walk(json.load(open(f)), "", out)
    best = {}
    for p, m, n, c, b in out:
        if n > best.get(m, (0,))[0]: best[m] = (n, c, b, p)
    print(f.split("cases/")[-1], {m: v[:3] for m, v in best.items()})
