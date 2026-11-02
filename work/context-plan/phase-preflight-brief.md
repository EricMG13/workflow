# Pre-flight for Phases 2 and 5 (controller, 2026-11-01)

You are the pre-flight reviewer for one phase plan, which your dispatch names. Its oracle (Task 0) is already frozen. The plan was written on 2026-10-31 at 28ad7934, and the branch has moved on a long way since. Your job is to find every place where the plan's text no longer matches HEAD, before any builder starts. This is the most common source of avoidable fix rounds.

## Inputs

- The plan, and the ledger at `.superpowers/sdd/2026-10-31-phase-<n>-<slug>/progress.md`.
- The parent plan's row for your phase: `docs/superpowers/plans/2026-10-31-context-file-consumption.md` :326-334.
- Rulings:
  - `docs/rulings/2026-10-31-context-plan.md`, all of it, including B17, B19, B28-B31a;
  - `work/context-plan/reviews/phases-2-8-questions.md`.
- The precedent: `.superpowers/sdd/2026-10-31-phase-3-market-evidence/preflight.md`, for format and depth.

## Check, task by task

1. Every file, function, constant, line number, test name and interface the plan cites. Does it exist at HEAD, and does it still mean what the plan says? Quote the HEAD line for each drift.
2. Code written out verbatim in the plan, diffed against the target's current text.
3. File overlap with in-flight lanes:
   - **O3 Task 6, now building:** `owner_workflow.py`, `replay.py`, `model/loop.py`, `tests/test_owner_guards.py`, `tests/model/test_loop.py`, `tests/test_owner_replay.py`.
   - **B30, now building:** `src/deploy_vii/live/prompts.py`, `methods/cp3.md`, `cp3_relative_value.py`, `tests/prompts/*`, `docs/reuse/manifest.json`, the rule lists and the golden.
   - **Next on `owner_workflow.py`, serial (P21):** O3 Task 7, then O6 Task 6 (`run_pathway.py`).
4. Dependencies the plan names, for example Phase 2 Task 4 "needs O1 Task 3", Phase 5 Task 3 "after O1's branch lands", and O7's manifest entries. Are they now met at HEAD?
5. `src/deploy_vii` edits. Name each one, and say whether a ruling approves it. Under B31a the controller now decides these by recommendation, so give a recommendation for each.
6. Sensitive tasks (money, figures, ordering, security), and the reviewer each one needs.

## Output

Write `.superpowers/sdd/2026-10-31-phase-<n>-<slug>/preflight.md`. It contains:

- Numbered items `P<n>-P1…`. Each item gives the plan text, the HEAD truth, a recommended ruling, and the cost if that ruling is wrong.
- A table with one row per task: the files it writes, its overlap with the in-flight lanes, "can start now" or "waits for <X>", and its reviewer.
- A recommended dispatch order that maximises parallel work without two writers on one file. Treat the golden and `docs/reuse/manifest.json` as single-writer files.

## Rules

- **Read-only, except for your `preflight.md`.** Never edit `src/`, `tests/`, `cases/` or the plan. Never commit.
- **Git.** Never set GIT_DIR or GIT_WORK_TREE to the shared repo, never run `git config`, and never run git stash, reset, amend or rebase.
- **Tests.** Fast only, by node id, each under 300 s. Never `RUN_PROMOTION=1` or the full suite.

Reply with only:
- the path of your preflight file;
- the item count;
- the tasks that can start now;
- any item that blocks the phase.
