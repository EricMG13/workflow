import json, sys
from pathlib import Path
d = Path(sys.argv[1])
cur = (d/"current").read_text().strip()
snap = json.loads((d/"snapshots"/(cur+".json")).read_bytes())
print("pack bytes", (d/"blobs"/snap["pack_sha256"]).stat().st_size)
for a in snap["attempts"]:
    for s in a.get("steps", []):
        ps = (d/"blobs"/s["payload_sha256"]).stat().st_size
        os_ = (d/"blobs"/s["output_sha256"]).stat().st_size if s.get("output_sha256") else None
        print(a["module_id"], s["step_id"], "payload", ps, "output", os_)
for h in snap["heads"]:
    m = json.loads((d/"blobs"/h["result_sha256"]).read_bytes())
    print("head", h["module_id"], "bytes", (d/"blobs"/h["result_sha256"]).stat().st_size, "facts", len(m.get("facts",[])), "claims", len(m.get("claims",[])))
