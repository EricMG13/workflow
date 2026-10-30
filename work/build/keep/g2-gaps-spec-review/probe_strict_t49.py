"""Does any oracle fact in T4.9/threshold get a strict-parse G# (report_view._strict_text_rejected) that the
revision-1 required-entry rule does not predict? Exit 1 if so."""
import json
from deploy_vii.report_view import strict_multiple
bad = 0
d = json.load(open("cases/cp4-owner/expected.json"))
for k in ("positive", "gap"):
    for t in d[k]["CP-4"]["tables"]:
        if t["table_id"] != "T4.9": continue
        for r in t["rows"]:
            for f in r["facts"]:
                if f["fact_id"].endswith(".threshold") or f["column"].lower().startswith("threshold"):
                    rej = f["status"] == "known" and f["text"] is not None and strict_multiple(f["text"]) is None
                    req = f["status"] != "known" or bool(f.get("cites") if isinstance(f.get("cites"), list) else False) or bool(f.get("calculation_id"))
                    print(k, f["fact_id"], f["status"], repr(f["text"]), "rejected=", rej, "required=", req)
                    bad += rej and not req
raise SystemExit(1 if bad else 0)
