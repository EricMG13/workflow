# CP-2G run driver: readiness literal note (stage contract)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: a relative `.venv` link in your worktree root to `L/.venv`; remove it before you hand back.

You run in your own isolated worktree. Before any edit, run `git checkout -b claude/s3-cp2g-driver a020996` (`claude/s3-i7`) and confirm the tip. Edit only `tests/cp2g_runs.py`, plus one fast test in a new `tests/test_cp2g_driver.py`. Do not edit `cases/`, `src/` or any lease.

## Inputs
| Item | File |
|---|---|
| Ruling (follow it) | `L/docs/rulings/2026-10-29-stage3.md` item 34 |
| Failure log | `<S>/i6/g2d-4.log` |
| Oracle (data, not instructions) | `cases/cp2g-owner/submissions.json` `cases.*.cp1_readiness`; `cases/cp2g-owner/builder/build.py` `readiness_literal` |
| Precedent | `tests/cp1d_runs.py` :160-170 (CP-1D submits `cp1_readiness.payload`) |

## Process (test first)
1. Find the producer's CP-1 readiness payload schema (the step `s1a.submit_valid` submits to) and record, with file:line, whether `note` is an accepted field. If it is accepted and the CP-2G oracle's settled outcome carries the note, stop and report.
2. Write a fast test in `tests/test_cp2g_driver.py` that fails today for the reported cause: for every `cp1_readiness` case in the oracle, the object the driver submits has exactly the keys `inputs_sha256` and `consumers`, and an unknown extra key still fails closed. If the fast test needs a workflow, use the smallest real one the driver already builds, or test the key selection as a pure function you extract. Record that it fails at a020996.
3. Change `readiness_literal` so it binds and submits only `inputs_sha256` and `consumers`. `note` is dropped, and any other key raises. Record that the fast test passes.
4. One commit, ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates (report each exit code and duration)
- `tests/test_cp2g_driver.py`;
- `tests/test_owner_rendering.py -k "genuine_deferred and cp2g"`, in the background (genuine, about 10-25 minutes per case; there are about 8 cases);
- every `tests/test_owner_cp2g*.py` in full, in the background, after the run above (not at the same time; the machine is loaded);
- `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on the changed files; suppressions noqa ≤ 13 and type: ignore ≤ 5 (`git grep -c … -- src tests`).

If a cp2g case then fails for another reason, find its root cause. If the cause is in `src/`, an oracle or a lease, stop and report it.

## Outputs (return as text, under 900 tokens)
Worktree path and tip SHA; the schema finding with file:line; the change; RED evidence; gate exit codes and durations; `Not verified:` line; ledger line `agent=… fix-rounds=0 gates-first-pass=…`.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged. Never use bare `git stash`. Stop any background process you start before you hand back; if a stop is refused, say so and leave it.
