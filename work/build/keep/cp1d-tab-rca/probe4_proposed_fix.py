"""Apply the proposed 3-line fix to assert_block_equals_oracle in memory (a copy of 49628a0's
source with the one-page rule inserted), then check: the existing fast test still passes; CP-1D
fast FP02 passes for all cases; mutants are refused (wrong rows, a one-tab oracle vs a tabbed
block, a two-tab oracle vs an untabbed block). Exit 0 when all hold."""
import inspect, sys, textwrap, copy
from pathlib import Path
root = Path(sys.argv[1])
sys.path[:0] = [str(root / "src"), str(root), str(root / "tests")]
import test_connect_cp1d as c  # noqa: E402
import test_owner_rendering as g  # noqa: E402

src = inspect.getsource(g.assert_block_equals_oracle)
old = '        wants = [(t["label"], t["rows"]) for t in oracle["tabs"]]\n'
new = old + ('        if len(wants) == 1:  # one register renders untabbed (report_view tab_structure)\n'
             '            wants = [(None, wants[0][1])]\n')
assert src.count(old) == 1
exec(compile(src.replace(old, new), "patched", "exec"), g.__dict__)
fails = 0
def expect(ok, label, fn):
    global fails
    try: fn(); got = True
    except AssertionError: got = False
    print(("ok  " if got == ok else "BAD ") + label); fails += got != ok

expect(True, "existing fast test", g.test_fast_block_rule_handles_s_chip_gap_placeholder_and_tabs_only_oracle)
for case in c.CASES:
    blocks = c._fp02(case)
    want = c.EXPECTED["cases"][case]["FP02"]["blocks"]
    for bid, w in want.items():
        b = blocks[bid].model_dump(mode="json")
        expect(True, f"{case}/{bid}", lambda b=b, w=w: g.assert_block_equals_oracle(b, w))
    rl = blocks["restated-leverage"].model_dump(mode="json")
    w = want["restated-leverage"]
    bad = copy.deepcopy(w); bad["tabs"][0]["rows"] = bad["tabs"][0]["rows"][:2]
    expect(False, f"{case} mutant: rows dropped", lambda: g.assert_block_equals_oracle(rl, bad))
    eq = blocks["earnings-quality"].model_dump(mode="json")
    expect(False, f"{case} mutant: one-tab oracle vs tabbed block", lambda: g.assert_block_equals_oracle(eq, {**w}))
    two = copy.deepcopy(want["earnings-quality"]); two["tabs"] = two["tabs"][:2]
    expect(False, f"{case} mutant: two-tab oracle vs untabbed block", lambda: g.assert_block_equals_oracle(rl, two))
    swap = copy.deepcopy(w); swap["tabs"] = [want["earnings-quality"]["tabs"][2]]
    expect(False, f"{case} mutant: other register's rows", lambda: g.assert_block_equals_oracle(rl, swap))
sys.exit(1 if fails else 0)
