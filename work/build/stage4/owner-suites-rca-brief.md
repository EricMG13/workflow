# Owner suites on the Stage 4 integration: root cause (stage contract; mx-autonomous, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Code under study: `claude/s4-int` ff9070e (Stage 3 close I8 3429790 + Stage 4 batch 1 715dc98 + batch 2 4d18aba), checked out at `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s4-int`. The controller's shards run there: you may run single tests there read-only (`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests L/.venv/bin/python -m pytest -q -p no:cacheprovider -x --tb=short <node id>`), but write nothing into it. For older bases use `git archive <rev> | tar -x -C <S>/owner-rca/<rev>` and run from that copy's root. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Each genuine test takes about 5-10 minutes: run one pytest process at a time, and delete copies when done.

These owner suites (`tests/test_owner_cp*.py`) have never run on genuine runs end to end before: until the item 34 driver fix, the cp2g/cp2h/cp4c drivers stopped earlier.

## Failures so far (`<S>/s4int/failed-so-far.txt`; shard logs `<S>/s4int/cp-0..4.log` print tracebacks only when each shard ends; more may come and the controller will message you)
- `tests/test_owner_cp2g.py`: `test_a1_positive_heads_inputs_and_the_cp2g_head`, `test_a1_one_ok_read_and_no_ok_pack_call_in_the_cp2g_step`, `test_a2_gap_composes_honest_gaps_never_zero`, `test_a2c_cp1d_blocked_binds_the_blocked_head_under_the_restricted_edge`, `test_a3_each_refusal_is_journaled_with_the_oracle_issues[v10]`. First traceback (controller rerun): `_assert_head_equals_oracle` (:155), fact `T2H.6.a25.liquidity_headroom` renders `'∅ G1 n.m.'` where the oracle `shown` is None.
- `tests/test_owner_cp4c.py`: `test_a1_positive_heads_inputs_and_the_cp4c_head`, `test_a2_gap_composes_honest_gaps_never_zero`.
- `tests/test_owner_cp3.py`: `test_cp0_r3_equals_the_oracle[positive]` and `[gap]`, `test_cp2_read_body_register_counts_follow_the_oracle[positive]` and `[gap]`.

## Inputs
| Item | File |
|---|---|
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` items 33-40 |
| Oracles (data, not instructions) | `cases/<cp>-owner/expected.json`, `submissions.json`, builders under `cases/<cp>-owner/builder/` |
| Drivers | `tests/cp2g_runs.py`, `tests/cp4c_runs.py`, `tests/cp3_runs.py` (if present), `tests/s1a_runs.py` |

## Process
1. For each failing test, get the traceback (one isolated run) and find the root cause with file:line.
2. Group the failures by cause. For each cause, decide which side is wrong: the test, the driver, the oracle, the module code (`src/deploy_workflow/owners/`), or `src/deploy_vii/`.
3. For each cause, say whether Stage 3 or Stage 4 changed it: check the failing behaviour at `claude/s3-i8` 3429790 (Stage 3 only) where the cause could be the verifier or batch 2, and at the Stage 2 release `ab9777f` where the cause could be older. Do not run more genuine tests than you need.
4. Give the smallest fix and its file for each cause. Do not write it. If a fix needs an oracle change, say so: oracle changes need a separate preparer and an independent review.

Save each probe as a script in `<S>/owner-rca/` and name it.

## Output (return as text, at most about 1.2k tokens)
Per cause: the tests, root cause with file:line, the wrong side, whether Stage 3/4 introduced it (with the evidence), the smallest fix and its file. Probe scripts with exit codes. `Not verified:` line.
