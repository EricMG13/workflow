"""Stage 5.2: expected navigation per delivered page, from its own receipt.

Usage: python3 -I expect.py <deliveries root> <lane>  -> writes <root>/expect.json
Keyed by the page's URL path under the root. Words and titles come from the CP-OS
oracle's status and registry tables; statuses from the delivery's owner-run.json.
For the S1a positive run the CP-OS oracle case itself is attached.
"""

import json
import pathlib
import sys

root, lane = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
cpos = json.loads((lane / "cases/cpos-owner/expected.json").read_text())
words = {k: v["word"] for k, v in cpos["status_words"].items()}
titles = {r["module_id"]: f"{r['module_id']} · {r['title']}" for r in cpos["registry"]}
order = [r["module_id"] for r in cpos["registry"]]
out = {}
for rr in sorted(root.glob("dom*/*/out/*/render-receipt.json")):
    d = rr.parent
    run = json.loads((d / "owner-run.json").read_text())
    receipt = json.loads(rr.read_text())
    heads = {h["module_id"]: words[h["status"]] for h in run["heads"]}
    e = {
        "scope": receipt["scope_id"],
        "issuer": run["run"]["issuer_name"],
        "heads": heads,
        "plan": sorted(run["plan"], key=order.index),
        "titles": titles,
        "calc": "calculation.json" in ((receipt["model"] or {}).get("files") or {}),
        "calc_on_disk": (d / "calculation.json").is_file(),
    }
    case = cpos["cases"]["s1a_positive"]
    if run["run"]["run_id"] == case["run"]["run_id"] and not run["refusals"] and set(heads) == set(case["heads"]) and all(heads[m] == words[s] for m, s in case["heads"].items()):
        e["oracle"] = {
            "rows": {r["module_id"]: [r["group"], r["number"], r["target"]["page_title"], r["target"]["status_chip_word"], r["target"]["has_output"]] for r in case["rows"]},
            "destinations": {x["href"]: x["page_title"] for x in case["destinations"]},
            "blocks": [[b["link"]["href"], b["link"]["page_title"], b["link"]["status_chip_word"]] for b in case["block_links"] if b["link"]],
        }
    out["/" + str((d / "report.html").relative_to(root))] = e
# The CP-1/Model financial slice page (cp1-model-slice-render/1): statuses from its financial receipt.
for rr in sorted(root.glob("dom*/*/financial-delivery/render-receipt.json")):
    d = rr.parent
    fin = json.loads((d / "financial-slice.json").read_text())
    heads = {m: words[fin[k]["status"]] for m, k in (("CP-0", "cp0"), ("CP-1", "cp1")) if fin.get(k)}
    if fin.get("model"):
        heads["CP-MODEL"] = heads["CP-1"]  # published from the CP-1 head; the page's chip is compared with this
    out["/" + str((d / "report.html").relative_to(root))] = {
        "scope": "historical-financials",
        "issuer": fin["run"]["issuer_name"],
        "heads": heads,
        "plan": [m for m in order if m in heads],
        "titles": titles,
        "calc": "calculation.json" in ((fin.get("model") or {}).get("files") or {}),
        "calc_on_disk": (d / "calculation.json").is_file(),
    }
(root / "expect.json").write_text(json.dumps(out, ensure_ascii=False))
print(len(out), "pages;", sum("oracle" in e for e in out.values()), "with the CP-OS oracle case")
