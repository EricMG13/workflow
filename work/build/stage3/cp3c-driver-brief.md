# CP-3C run driver: root cause and fix (stage contract)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). Python: `L/.venv/bin/python`.

You run in your own isolated worktree. Before any edit, run `git checkout -b claude/s3-cp3c-driver ee95ffb` (`claude/s3-fix1-g2`, which adds the `cp3c-fp04-refinancing` G2 row) and confirm the tip. Use `superpowers:systematic-debugging`: root cause before any fix.

## The failure
`PYTHONPATH=src:tests L/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_owner_rendering.py -k "test_genuine_deferred_complete_cases and cp3c-fp04-refinancing and positive"` fails after about 200 s. The failure is inside `tests/cp3c_runs.py` `reach_cp2d` (:131) → `s1a.read_cp2` (`tests/s1a_runs.py:387`) → `workflow.read_inputs()`, which raises `WorkflowError: not_permitted` (`src/deploy_workflow/financial_workflow.py:593-594`: phase not `analytical`, or the read limit reached). The driver was never run before: its docstring defers it to Stage 5. `reach_cp2d` differs from S1a's chain in its own `drive_cp1` (the CP-1 downstream review, `cases/cp3c-owner/submissions.json#cp1_downstream_review`, and the CP-0 readiness deltas).

## Inputs
| Item | File |
|---|---|
| Driver | `tests/cp3c_runs.py`; `tests/cp2d_runs.py`; `tests/s1a_runs.py` |
| Lease and oracle | `docs/CP3C-OWNER-LEASE.md`; `cases/cp3c-owner/` (`manifest.json#upstream_literals`, `submissions.json`) |
| Workflow | `src/deploy_workflow/owner_workflow.py`, `src/deploy_workflow/financial_workflow.py` (read only) |

## Process
1. Find which step leaves the workflow outside `analytical` (or exhausts the read) before `read_cp2`, and why. Cut the reproduction down to the shortest call sequence and save it as a script under `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3c-driver/`.
2. **If the cause is in the driver or its literals** (`tests/`), fix it test first: the failing genuine test above is the RED test. Do not change an oracle value, a lease, or `src/`. If a literal in `cases/cp3c-owner/` is wrong, stop and report it, because an oracle change needs a separate preparer.
3. **If the cause is in `src/`**, stop and report the root cause with the reproduction. Do not change product code.
4. Commit each step, ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates (report each exit code)
- The genuine test above, then the same selection for `gap_minimum_cash` and `gap_no_repricing`.
- `tests/test_connect_cp3c.py` (the driver's pure parts).
- `ruff check` and `ruff format --check` on changed files; suppressions `noqa` ≤ 13, `type: ignore` ≤ 5.

## Outputs (return as text, at most about 1k tokens)
Worktree path and tip SHA; root cause with file:line evidence; the fix (or the stop reason); gate exit codes and durations; `Not verified:` line; ledger line.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged. Never use bare `git stash`. Stop any background process before you hand back.
