"""Probe: the positive render test's figure check is vacuous: oracle text for the window fact is None,
so startswith('') is always True; and run kind is never 'G'. Exit 1 = vacuous."""
import json, sys
d = json.load(open(sys.argv[1] + "/cases/cp8-owner/expected.json"))
f = next(f for t in d["cases"]["positive"]["tables"] for r in t["rows"] for f in r["facts"]
         if f["fact_id"] == "T7.3.window.realized_value")
prefix = f["text"] or ""
print("prefix used by test:", repr(prefix), "oracle shown:", f["shown"])
print("'anything'.startswith(prefix) =", "anything".startswith(prefix))
sys.exit(1 if prefix == "" else 0)
