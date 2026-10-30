# Resume after the PC restart (2026-10-29, paused at about 21:50)

The user paused the work to restart the PC. Everything below was stopped on purpose. Nothing is lost: every code change is committed on its branch. Probes, runner scripts and logs from the scratchpad (cleared on reboot) are copied to `work/build/keep/`; briefs that name `<S>/…` paths now resolve to `work/build/keep/…`.

## Branches (local)
| Branch | Tip | State |
|---|---|---|
| `claude/s3-i7` | a020996 | Stage 3 integration: I6 49628a0 + `claude/s3-low-s4`. I6 checks: fast 10247 passed, G2 fast 153, pins/mypy 0, D12 owner-only. |
| `claude/s3-cp2g-driver` | 419295e | Item 34 fix (cp2g 864a24e; cp2h + cp4c 419295e). Agent a7b022fb stopped before its report: its gates and genuine reruns are **unverified**. |
| `claude/s3-fix4-g2` | 65e233c | Item 36, G2 round 4 (one-register rule). Agent a46a5b1a stopped before its report: gates, probes and the 3 cp1d genuine cases are **unverified**. |
| `claude/s4-batch1-fix1` | 715dc98 | Batch 1 fix round 1 (item 33), gates and probes passed (report `work/build/stage4/batch1-fix1-report.md`). Adversary re-review was interrupted. |
| `claude/s4-batch2` | 4d18aba | Batch 2, approved. |

## Interrupted work, to restart in this order
1. **Verify the two Stage 3 fix branches** (each agent committed; rerun its gates):
   - `claude/s3-cp2g-driver`: `tests/test_cp2g_driver.py`; ruff, ruff format, mypy --strict on `tests/cp2g_runs.py tests/cp2h_runs.py tests/cp4c_runs.py tests/test_cp2g_driver.py`; suppressions noqa ≤ 13, type: ignore ≤ 5. Then a scoped mx-feature review (test drivers, item 34).
   - `claude/s3-fix4-g2`: `tests/test_owner_rendering.py -k fast`; `work/build/keep/cp1d-tab-rca/probe3_cp1d_fast_block_rule.py` and `probe4_proposed_fix.py` on a `git archive 65e233c src tests cases docs pyproject.toml` copy; ruff, mypy. Then a scoped mx-feature review (G2 round 4 is a small test fix).
2. **Build I8** = I7 + `claude/s3-cp2g-driver` + `claude/s3-fix4-g2` (commit-tree merges; trial with `git merge-tree --write-tree`).
3. **Genuine reruns on I8** (one worktree, parallel shards, `work/build/keep/i6/shard.sh` pattern): the 16 failed G2 deferred cases in `work/build/keep/i6/g2d-failed.txt` (`tests/test_owner_rendering.py -k "genuine_deferred and (cp1d or cp2g or cp2h or cp4c)"`), and CZR shard aa (36 tests, list `work/build/keep/i5/czr-shard-aa`; it ran 3.5 h on I5 without finishing). CZR source 167, ab 36 and ac 35 already passed on I5.
4. **Close Stage 3**: tick the plan boxes; release I8 to the PR manager with the exact tip; tell the user the item 28 Stage 5 gaps (R2.5 secondary pointers for cp3d/cp4/cp8; the `cites` normaliser) and the cp2d plain-string `tabs` latent issue (item 35).
5. **Stage 4 batch 1**: redispatch the scoped adversary re-review (brief `work/build/stage4/batch1-fix1-adv-brief.md`; its `<S>/s4-batch1-adv/probes/` are in `work/build/keep/s4-batch1-adv/probes/`). Rerun the batch 1 deferred lane on 715dc98: full `tests/test_owner_s1a.py`, then `tests/test_owner_workflow.py` (worktree `../s4-b1`, detached at 715dc98; runner `work/build/keep/s4b1/lane.sh`). `tests/test_owner_cp*.py` runs on the Stage 4 integration after I8 (cp2g/cp2h/cp4c need the item 34 fix).
6. **Stage 4 integration**: I8 + `claude/s4-batch1-fix1` + `claude/s4-batch2`; then the Fable Stage 4 review.
7. **Stage 5** per the plan.

## Worktrees made by the controller
`../s3-i4` (I5 18dc1fa), `../s3-i6` (I6 49628a0), `../s4-b1` (715dc98, detached). Test runs use `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests <lane>/.venv/bin/python -m pytest -q -p no:cacheprovider`.

## Rules to keep
Ledger times from `date +%H:%M`. At most 10 subagents, 6 Opus. One genuine pytest process per agent while the machine is loaded. Before deleting anything to make room, ask the user (the user allowed the 2026-10-29 pytest temp cleanup only).
