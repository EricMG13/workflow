# Owner-suite test and driver fixes: scoped review (stage contract; mx-feature, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Change under review: `claude/s4-owner-tests` `ff9070e..18f1845` (4 commits; `tests/test_owner_cp2g.py`, `tests/test_owner_cp4c.py`, `tests/cp2g_runs.py`, `tests/cp4c_runs.py`, `tests/test_owner_cp3.py`, `tests/test_owner_cpl10.py`). Read with `git show`/`git diff` from `L`. For probes, make a fresh copy under `<S>/owner-tests-review/` with `git archive 18f1845 | tar -x -C …` and delete it when done; never write into any worktree. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Run no genuine (real-data) tests; the fixer ran them (cp3 4, cpl10 2, cp4c 37, cp2g 39 passed) and the controller reruns them on the integration branch.

## Inputs
| Item | File |
|---|---|
| Ruling | `L/docs/rulings/2026-10-29-stage3.md` item 41 |
| Root cause and fixes | `L/work/build/stage4/owner-suites-rca.md` causes A, B, D, E, F |
| Fixer's brief and report | `L/work/build/stage4/owner-tests-fix-brief.md`, `L/work/build/stage4/owner-tests-fix-report.md` |

## Process
For each cause, check that the change is the one the root cause gives and that it does not loosen the test:
- **A:** the unsettled-spelling branch runs only when the oracle `shown` is None, and picks `∅ G#` or `∅ G# n.m.` from the fact's status; a settled fact is still compared exactly. The two strings are hard-coded because the manifest's `cell_notation` is prose: confirm they match it word for word.
- **B:** the bound placeholder keeps the payload's unit token (`{<fact_id>|<payload token>}`), as the manifest rule and `tests/test_method_cp2g.py:252` say, and an unknown figure name still stays unbound (and so refused).
- **D, E:** the pack-hash marker is replaced by the real hash before comparing, and only that marker; the signal check compares a count with the frozen count.
- **F:** copied cells keep CP-1's own citations; derived cells use `one_per_page`; nothing else in the citation check changes.
Report anything that hides a failure, a stub or a fake value.

## Output (return as text, under 600 tokens)
Verdict (APPROVE / REVISE); findings ranked High, Medium, Low, Info, each with file:line and a probe script with its exit code; `Not verified:` line.
