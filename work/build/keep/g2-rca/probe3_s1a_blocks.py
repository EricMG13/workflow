"""Probe 3: replay assert_block_equals_oracle (tests/test_owner_rendering.py@ee95ffb :1975-2014)
on the delivered s1a positive page WITHOUT stopping at the first mismatch; dump line runs.
Usage: python -I probe3_s1a_blocks.py <code-root> <report.html> <oracle-case-key> [block...]
Exit 1 if any check fails (the current test would fail), 0 otherwise."""
import json, re, sys
from pathlib import Path
code, report, case = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
sections = sys.argv[4:] or ["key-findings", "company-operating-model", "company-profile",
                            "strengths-weaknesses", "transaction-summary"]
text = report.read_text(encoding="utf-8")
m = '<script id="report-data" type="application/json">'
payload = json.loads(text.split(m, 1)[1].split("</script>", 1)[0])
blocks = {b["block_id"]: b for b in payload["report"]["blocks"]}
oracle = json.loads((code / "cases/snapshot/expected.json").read_text())[case]["FP01"]
fails = []
def check(ok, what):
    if not ok: fails.append(what); print("FAIL", what)
for sid in sections:
    b, o = blocks[sid], oracle[sid]
    print(f"== {sid}: oracle keys {sorted(o)}; block keys {sorted(b)}")
    for k in ("title", "owner", "kind", "state", "numbered", "summary"):
        if k in o: check(b.get(k) == o[k], f"{sid}.{k}: {b.get(k)!r} != {o[k]!r}")
    if "primary" in o:
        check(b["tab_label"] == o["primary"]["tab"], f"{sid}.primary.tab")
        pr, orow = b["rows"], o["primary"]["rows"]
        check([r["label"] for r in pr] == [r["label"] for r in orow], f"{sid}.primary labels")
        for g, w in zip(pr, orow):
            if len(g["cells"]) != len(w["cells"]): check(False, f"{sid} row {w['label']} ncells"); continue
            for gc, wc in zip(g["cells"], w["cells"]):
                if wc["state"] == "known" and wc.get("shown") is not None:
                    check(gc["text"] == wc["shown"], f"{sid} {w['label']} cell {gc['text']!r} != {wc['shown']!r}")
                else:
                    check(bool(re.fullmatch(r"∅ G\d+( n\.m\.)?", gc["text"])), f"{sid} {w['label']} gap {gc['text']!r} state={wc['state']}")
    for g, w in zip(b["tabs"], o.get("tabs", [])):
        check(g["label"] == w["tab"], f"{sid} tab {g['label']!r} != {w['tab']!r}")
    if len(b["tabs"]) != len(o.get("tabs", [])): print(f"   note: {sid} tabs payload {len(b['tabs'])} oracle {len(o.get('tabs', []))} (zip strict=False)")
    if "lines" in o:
        got = ["".join(r["text"] for r in ln["runs"]) for ln in b["lines"]]
        want = [ln["text"] for ln in o["lines"]]
        check(len(got) == len(want), f"{sid} nlines {len(got)} != {len(want)}")
        for i, (ln, w) in enumerate(zip(b["lines"], o["lines"])):
            if "".join(r["text"] for r in ln["runs"]) != w["text"]:
                check(False, f"{sid} line {i}")
                print("   runs:", [(r.get("kind"), r["text"][-40:], {k: v for k, v in r.items() if k not in ("text",)}) for r in ln["runs"]])
                print("   oracle line keys:", {k: v for k, v in w.items() if k != "text"})
print(len(fails), "failures")
sys.exit(1 if fails else 0)
