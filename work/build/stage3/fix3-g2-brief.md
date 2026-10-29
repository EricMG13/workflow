# G2 fix round 3: genuine cp1-model test defects (stage contract)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python` (or a relative `.venv` link in your worktree root, removed before you hand back).

You run in your own isolated worktree. Before any edit, run `git checkout -b claude/s3-fix3-g2 ee95ffb` and confirm the tip. Edit only `tests/test_owner_rendering.py`, and only `test_genuine_cp1_model_positive_delivery` and `test_genuine_cp1_model_extra_attempt_is_refused`, plus imports. Another branch is editing `_assert_cp3c_blocks` (about :2140-2160), so do not touch it.

## Inputs
| Item | File |
|---|---|
| Ruling | `L/docs/rulings/2026-10-29-stage3.md` item 27 |
| Root cause and plan (follow it) | `L/work/build/stage3/g2-genuine-rca.md` |
| Probes | `<S>/g2-rca/probe1_model_diff.py`, `<S>/g2-rca/probe2_extra_attempt.py` |
| Failure log | `<S>/i5/g2cp1.log` |
| Forging precedent | `tests/test_financial_render.py:285` |

## Process
1. **Failure 1.** Replace the cross-run byte comparison with the item 27 reading:
   - each delivery's `model/` equals its own publication;
   - `model.html` and `calculation.json` are equal across the two runs;
   - `receipt.json` is equal once `ticket_id` is removed, and each `ticket_id` equals its own store's CP-MODEL attempt ticket.
   The test must still fail if G2 delivers the financial run's publication instead of its own.
2. **Failure 2.** Assert that `Execution(store).begin("CP-1")` raises `ValueError` ("settled"). Then forge a pending CP-1 repair attempt through `_write`, as the plan says. Assert that the store reads back with that attempt pending, then that G2 refuses it with no destination left behind.
3. Make one commit with the Sonnet Co-Authored-By trailer.

## Gates (report each exit code and duration)
- `ruff check`, `ruff format --check`, and `MYPYPATH=src mypy --strict tests/test_owner_rendering.py src/deploy_workflow/owner_rendering.py`. The annotations branch is not merged here; report what mypy prints.
- `tests/test_owner_rendering.py -k fast`.
- `tests/test_owner_rendering.py -k genuine_cp1_model`, all 8 tests, in the background. The last run took 86 minutes.
- Both probes rerun, with their exit codes.
- Suppressions: noqa ≤ 13, type: ignore ≤ 5.

If another assertion in these tests fails after the fix, find its root cause. If the cause is in `src/`, the lease or an oracle, stop and report.

## Outputs (return as text, under 900 tokens)
Worktree path and tip SHA; the change per failure; gate and probe exit codes and durations; `Not verified:` line; ledger line `agent=… fix-rounds=3 gates-first-pass=…`.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged. Never use bare `git stash`. Stop any background process before you hand back.
