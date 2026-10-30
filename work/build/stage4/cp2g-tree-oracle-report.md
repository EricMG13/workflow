CP-2G view-tree oracle: the six `limitation` leaves now follow genuine CP-1 heads. The genuine `a1_one_ok_read` test passes on the new tip, but I did not run the probe.

**Worktree and tip:** `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-aeb0053d0b2b0d047`, branch `claude/s4-cp2g-tree`, tip `cb66e6c`, one commit on `ff9070e`. The `.venv` link is removed and the tree is clean.

**Producer evidence:**
- A genuine CP-1 run notes a cell `SIGN_NORMALISED` ("sign normalised") in two places. `src/deploy_vii/statement_history.py:75` does it when `value_class == "normalized"`. `src/deploy_vii/model/history.py:222` does it for an outflow written positive.
- `src/deploy_workflow/owners/cp2g.py:2996-3001` (`_cell`) emits `fact.limitation` as the view's `limitation` leaf.
- I did not trace the code path from the CP-1 note to `fact.limitation`. I inferred it from the RCA and the passing genuine test.
- `cases/cp2g-owner/expected.json` has `cash_interest` and `cash_taxes` as `known`, `calculated`, `limitation: null` in all three cases (positive, gap, cp1d_blocked). I treated all three as carrying the genuine CP-1 head. The cause-C Not-verified item says this was an assumption for gap and cp1d_blocked, and no genuine gap or cp1d_blocked run covers it.

**What moved:**
- The tree is a recorded observation, so I edited it directly.
  - In `cases/cp2g-owner/cp2g-view-tree.json`, `base.operands.cash_interest.limitation` and `base.operands.cash_taxes.limitation` changed from `NoneType` to `str` in positive, gap and cp1d_blocked.
  - That is lines 44, 50, 267, 273, 473 and 479.
  - I added a cause-C sentence to `_note`.
- In `tests/test_method_cp2g.py`, a new helper `_limitation(metric, rec)` gives known `cash_interest` and `cash_taxes` the limitation "sign normalised". `_cp1_fact` uses it, and every other fact keeps `rec["limitation"]`.
- Exactly one pin moved in `cases/PINS.json`, regenerated with `python3 -I cases/pins.py`: `cases/cp2g-owner/cp2g-view-tree.json`, `b72a352d…` to `f0e5e0e2…`.

**Gates (all exit 0):**
- `tests/test_method_cp2g.py tests/test_connect_cp2g.py`: 580 passed, 12 s.
- `tests/test_owner_rendering.py -k "fast and cp2g"`: 10 passed, 1 s.
- `python3 -I cases/pins.py --check`: exit 0, 86 paths.
- `ruff check` and `ruff format --check` on `tests/test_method_cp2g.py`: exit 0.
- `tests/test_owner_cp2g.py -k a1_one_ok_read` (genuine, background): 1 passed, 366 s. It checks the genuine body against the tree. The background run has finished and nothing of mine is still running.

**Not run:** the probe. `probe_cp2g_viewtree.py` needs a saved `owner-receipt.json` as argv[1], and I had none. The genuine test is the equivalent check for the positive case. I did not run it a second time just to save a receipt.

I had no Monitor tool, so I waited with a Python polling loop in a foreground Bash call rather than a Monitor.

Not verified: the probe's two-leaf diff; genuine gap and cp1d_blocked CP-1 heads carrying "sign normalised" (positive only, through the genuine test); the other fast cp2g tests beyond those listed; the full suite.

agent=mx-feature fix-rounds=0 gates-first-pass=y
