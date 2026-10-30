"""Probe: an answer carrying a well-formed reference (each token kind, in any question of a
two-question gap) is refused by ENTRY_VALIDATOR (no output), so _candidate/compose is never
reached. Exit 0 = refused in every case."""
import copy, json, sys
from pathlib import Path
ROOT = Path.cwd()
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
import test_connect_cpdr as c
from deploy_workflow.owners import cpdr
fail = 0
base = c.SUBMISSIONS["cpdr"]["partial"]
for qi, q in enumerate(base["gaps"][0]["questions"]):
    if not q.get("answer"):
        continue
    for tok in ("{fact_a|x}", "{fact_a}", "[fact_a]", "[G1]"):
        p = copy.deepcopy(base)
        p["gaps"][0]["questions"][qi]["answer"] = q["answer"] + " " + tok
        attempt, store = c.attempt_of(c.cp0_module(empty=False), json.dumps(p))
        out = cpdr.ENTRY_VALIDATOR(store, store.pack(), attempt)
        want = f"gaps[0].questions[{qi}].answer: text carries a reference"
        ok = out.output is None and want in out.issues
        print("OK " if ok else "BAD", qi, tok, out.issues)
        fail |= not ok
sys.exit(1 if fail else 0)
