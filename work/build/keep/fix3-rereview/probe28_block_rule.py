"""Ruling 28 mutation probe: each mutated block must be refused. Run from the copy root."""
import copy, sys
sys.path[:0] = ["src", ".", "tests"]
import test_owner_rendering as t

def run(kind, text, ref=None): return {"kind": kind, "text": text, "ref_id": ref}
block = {
    "tab_label": "Peers",
    "rows": [{"label": "A", "cells": [{"text": "7.5x"}]}],
    "tabs": [{"label": "Other", "rows": [{"label": "B", "cells": [{"text": "∅ G12 n.m."}]}]}],
    "lines": [
        {"runs": [run("text", "Deal value"), run("fig", "S110", "S110")]},
        {"runs": [run("text", "Date / window:"), run("text", "∅ G7 n.m.")]},
        {"runs": [run("text", "Leverage"), run("fig", "4.0x", "S5"), run("fig", "C12", "C12")]},
    ],
}
oracle = {
    "tabs": [
        {"label": "Peers", "rows": [{"label": "A", "cells": [{"state": "known", "shown": "7.5x"}]}]},
        {"label": "Other", "rows": [{"label": "B", "cells": [{"state": "known", "shown": "∅ G# n.m."}]}]},
    ],
    "lines": [
        {"text": "Deal value", "synthetic_ref": True},
        {"text": "Date / window: ∅ G# n.m."},
        {"text": "Leverage 4.0x C12"},
    ],
}
t.assert_block_equals_oracle(block, oracle)  # baseline must pass

def mut(f):
    b = copy.deepcopy(block); o = copy.deepcopy(oracle); f(b, o); return b, o
cases = {
    "S chip ref swapped to K chip": lambda b, o: b["lines"][0]["runs"].__setitem__(1, run("fig", "K110", "K110")),
    "S chip removed": lambda b, o: b["lines"][0]["runs"].pop(),
    "extra S chip": lambda b, o: b["lines"][1]["runs"].append(run("fig", "S9", "S9")),
    "real C chip dropped": lambda b, o: b["lines"][2]["runs"].pop(),
    "synthetic fig value dropped": lambda b, o: b["lines"][2]["runs"].pop(1),
    "oracle literal vs rendered gap": lambda b, o: o["lines"][1].__setitem__("text", "Date / window: 2024"),
    "rendered literal ∅ G#": lambda b, o: b["lines"][1]["runs"].__setitem__(1, run("text", "∅ G# n.m.")),
    "rendered ∅ Gx": lambda b, o: b["lines"][1]["runs"].__setitem__(1, run("text", "∅ Gx n.m.")),
    "rendered gap with trailing text": lambda b, o: b["lines"][1]["runs"].__setitem__(1, run("text", "∅ G7 n.m. 5")),
    "known cell rendered as gap": lambda b, o: b["rows"][0]["cells"].__setitem__(0, {"text": "∅ G3"}),
    "placeholder cell rendered literal": lambda b, o: b["tabs"][0]["rows"][0]["cells"].__setitem__(0, {"text": "1.0x n.m."}),
    "missing tab": lambda b, o: b.__setitem__("tabs", []),
    "extra tab": lambda b, o: b["tabs"].append({"label": "X", "rows": []}),
    "tab label swapped": lambda b, o: b.__setitem__("tab_label", "Other2"),
    "missing line": lambda b, o: b["lines"].pop(),
    "extra line": lambda b, o: b["lines"].append({"runs": [run("text", "x")]}),
    "lines reordered": lambda b, o: b["lines"].reverse(),
}
bad = 0
for name, f in cases.items():
    b, o = mut(f)
    try:
        t.assert_block_equals_oracle(b, o); print("ACCEPTED", name); bad += 1
    except (AssertionError, KeyError) as e:
        print("refused", name, type(e).__name__)

node = {"owner": "CP-3D", "tabs": [["T3E.5", "Market-implied default"], ["T3E.4", "Assumptions"]]}
rb = {"owner": "CP-3D", "kind": "tabs", "tab_label": "Market-implied default", "tabs": [{"label": "Assumptions"}]}
t.assert_render_node_owner(rb, node, "cp3d-fp03-market")
for name, (b, n, s) in {
    "wrong owner": ({**rb, "owner": "CP-3C"}, node, "cp3d-fp03-market"),
    "cp3d tab missing": ({**rb, "tabs": []}, node, "cp3d-fp03-market"),
    "cp3d tabs reordered": ({**rb, "tab_label": "Assumptions", "tabs": [{"label": "Market-implied default"}]}, node, "cp3d-fp03-market"),
    "wrong kind cp4": ({"owner": "CP-4", "kind": "a"}, {"owner": "CP-4", "kind": "b"}, "cp4-fp04-covenants"),
    "wrong owner cp8": ({"owner": "CP-7"}, {"owner": "CP-8"}, "cp8-fp01-what-changed"),
}.items():
    try:
        t.assert_render_node_owner(b, n, s); print("ACCEPTED", name); bad += 1
    except (AssertionError, KeyError) as e:
        print("refused", name, type(e).__name__)
print("accepted mutants:", bad); sys.exit(1 if bad else 0)
