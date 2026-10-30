import json
def parse(path):
    rows = []; kind = None
    for l in open(path).read().splitlines():
        if l.startswith("kind="):
            kind = l.split()[0][5:]; cols = json.loads(l.split(" columns=", 1)[1])
        elif l.startswith("[") and kind:
            rows.append({**dict(zip(cols, json.loads(l))), "kind": kind})
    return rows
