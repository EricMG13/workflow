"""Probe: build the cp3 closed run for one case (argv[1]) under argv[2], diff the two failing tests.
Run from the code root with PYTHONPATH=src:tests. Exit 0 = both match; 1 = a mismatch printed."""
import json, sys, traceback
from pathlib import Path
import test_owner_cp3 as t

case, root = sys.argv[1], Path(sys.argv[2])
closed = t.Closed(case, root)
rc = 0
# CP-0
want = closed.expected["upstream"]["CP-0"][t.runs.RUN]
module = t.head_module(closed.store, "CP-0")
got_facts = [{"fact_id": f.fact_id, "text": f.text, "cites": [[c.source_id, c.locator] for c in f.citations]} for f in module.facts]
head = next(h for h in closed.store.read().heads if h.module_id == "CP-0")
checks = {
    "status": (module.status, want["status"]),
    "facts": (got_facts, want["facts"]),
    "limitations": (list(module.limitations), want["limitations"]),
    "commands": ({c.row_id: c.text for c in head.commands}, want["exact_commands"]),
    "plan": (list(closed.receipt.plan), want["plan_order"]),
}
for k, (g, w) in checks.items():
    if g != w:
        rc = 1
        print(f"CP0 MISMATCH {k}")
        if isinstance(g, list) and isinstance(w, list):
            for i in range(max(len(g), len(w))):
                gi = g[i] if i < len(g) else None; wi = w[i] if i < len(w) else None
                if gi != wi:
                    print("  got ", json.dumps(gi, ensure_ascii=False)[:600]); print("  want", json.dumps(wi, ensure_ascii=False)[:600])
        else:
            print("  got ", json.dumps(g, ensure_ascii=False)[:1500]); print("  want", json.dumps(w, ensure_ascii=False)[:1500])
    else:
        print(f"CP0 ok {k}")
for name in ("test_cp2_read_body_register_counts_follow_the_oracle", "test_cp0_r3_equals_the_oracle"):
    try:
        getattr(t, name)(closed); print(name, "PASS")
    except Exception:
        rc = 1; print(name, "FAIL"); traceback.print_exc()
# CP-2 body detail
body, frozen = t.cp2_read_body(closed), t.S1_TREE["positive"]
counts = t.EXPECTED["execution"]["tool_use"]["CP-2"]["register_counts_by_case_and_run"][case][t.runs.RUN]
wanted = {r["ref_prefix"]: r["rows"] for r in frozen["cp1a_registers"]}
for key in ("source_classification", "T2D.1", "downstream_readiness", "T2D.10"):
    wanted[key] = counts[key]
got = {p: 0 for p in wanted}; stray = []
for row in body["cp1a_rows"]:
    ps = [p for p in wanted if row["ref"].startswith(p + ".")]
    if len(ps) == 1: got[ps[0]] += 1
    else: stray.append(row["ref"])
print("CP2 keys", list(body) == frozen["top_level_keys"], list(body))
shape = t.s1a_tests._shape(body)
print("CP2 shape diffs", [k for k, v in frozen["tree"].items() if k != "cp1a_rows" and shape.get(k) != v])
print("CP2 counts got ", got); print("CP2 counts want", wanted); print("CP2 stray", stray[:20])
print("CP2 rows", len(body["cp1a_rows"]), counts["cp1a_rows"])
print("CP2 signals eq", body["cp1a_signals"] == frozen["cp1a_signals"])
if body["cp1a_signals"] != frozen["cp1a_signals"]:
    print(" got", json.dumps(body["cp1a_signals"])[:800]); print(" want", json.dumps(frozen["cp1a_signals"])[:800])
print("CP2 upstream", body["upstream"])
sys.exit(rc)
