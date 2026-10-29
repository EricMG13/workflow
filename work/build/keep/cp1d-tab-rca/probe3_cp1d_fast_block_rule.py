"""Compose CP-1D FP02 from the connect-test fast fixtures (tests/test_connect_cp1d._fp02) and run
(a) the 49628a0 G2 rule `assert_block_equals_oracle` unchanged, and (b) the candidate fix (a
one-page tabs-only oracle matches an untabbed block). Exit 1 when (a) fails on a block where (b)
passes, i.e. the failure reproduces and the candidate clears it; exit 2 on any other outcome."""
import sys, traceback
from pathlib import Path
root = Path(sys.argv[1])
sys.path[:0] = [str(root / "src"), str(root), str(root / "tests")]
import test_connect_cp1d as c  # noqa: E402
import test_owner_rendering as g  # noqa: E402

def why(e):
    tb = traceback.extract_tb(e.__traceback__)[-1]
    return f"FAIL test_owner_rendering.py:{tb.lineno} {tb.line}"[:110]

def candidate(block, oracle):
    if "primary" not in oracle and "tabs" in oracle and len(oracle["tabs"]) == 1 and not block["tabs"]:
        assert block["tab_label"] is None
        g._register_ok(block["rows"], oracle["tabs"][0]["rows"])
        oracle = {k: v for k, v in oracle.items() if k != "tabs"}
    g.assert_block_equals_oracle(block, oracle)

reproduced, other = 0, 0
for case in c.CASES:
    blocks = c._fp02(case)
    for bid, want in c.EXPECTED["cases"][case]["FP02"]["blocks"].items():
        b = blocks[bid].model_dump(mode="json")
        try:
            g.assert_block_equals_oracle(b, want); cur = "pass"
        except AssertionError as e:
            cur = why(e)
        try:
            candidate(b, want); new = "pass"
        except AssertionError as e:
            new = why(e)
        print(f"{case}/{bid}: tab_label={b['tab_label']!r} tabs={len(b['tabs'])} rows={len(b['rows'])} current={cur} candidate={new}")
        if cur != "pass" and new == "pass": reproduced += 1
        elif new != "pass" or (cur != "pass"): other += 1
sys.exit(2 if other else (1 if reproduced else 0))
