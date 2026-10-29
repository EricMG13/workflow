The driver fix is committed and the CP-3C driver now runs end to end, but the three genuine tests still fail on a later, separate problem in the product render. I stopped there because the cause is in `src/`.

Worktree: /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a84136ec315fffe56. Branch `claude/s3-cp3c-driver`, tip 3ac979c (f80d2d3 plus one commit). The `.venv` link is removed and no background process is left running.

**Change** (only `tests/cp3c_runs.py`):
- New `cp1a_text(pack)` appends `submissions.json#cp1a_consumer_deltas` to the CP-1A consumers, serialised like `cp0_text`.
- `reach_cp2d` now submits that text. It raises immediately if the CP-1A or CP-2 outcome is not valid.
- The three PINS are set to the frozen digests.

**Gates**
- `tests/test_connect_cp3c.py`: exit 0, 136 passed, 7 s.
- `tests/test_owner_cp3c.py` in full: exit 0, 13 passed, 11 skipped, 9 s. The skips are the "needs a real CP-1 promotion (Stage 5)" tests, so none of them ran.
- `ruff check` and `ruff format --check` on `tests/cp3c_runs.py`: both exit 0.
- Suppressions over `src` and `tests`: `noqa` 13 and `type: ignore` 5, both at the limit.
- `test_owner_rendering.py -k "test_genuine_deferred_complete_cases and cp3c-fp04-refinancing"`: exit 1, 3 failed (positive, gap_minimum_cash, gap_no_repricing), 3352 s. The CP-1A failure is gone and the runs now reach rendering.

**Remaining failure** (the same in all three cases)
- `tests/test_owner_rendering.py:2160`, in `_assert_cp3c_blocks`: block `lme-creditor-exposure` renders `collapsed`, but the oracle `cp3c-owner#/fp04_render` expects `populated`.
- The block is built in `src/deploy_vii/report_view.py` (spec at :1249) and `src/deploy_vii/bindings/cp3c.py`, which binds T3D.5 and T3D.4 to it. Both are `src/`, so I did not touch them.
- I did not check whether `refinancing-paths` and `funding-gap` pass. The failing check is not the first one in its loop, but the loop's order is not confirmed.
- Likely cause, not confirmed: the T3D.4 or T3D.5 bindings are empty or unbound in the real CP-3C output. The other possibility is that the oracle's `fp04_render` expectation does not match the product. Next step: inspect that block's binding state in a real run.

Ledger: `agent=mx-feature fix-rounds=0 gates-first-pass=n`. The driver fix is done; the genuine tests are BLOCKED on this `src`/oracle finding.

Not verified: why `lme-creditor-exposure` renders collapsed; whether `refinancing-paths` and `funding-gap` pass; the 11 skipped genuine tests in `test_owner_cp3c.py`; `blocked_cp3c` and `begin_refused_cp2d_blocked`; the sealed receipt and `verify_receipt`.
