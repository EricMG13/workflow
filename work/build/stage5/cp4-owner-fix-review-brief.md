# Stage 5.1 CP-4 owner test fix: scoped review (stage contract; mx-feature, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Change: `claude/s5-cp4-owner` `48e6c91..98800a0` (`tests/test_owner_cp4.py` only). Read with `git show`/`git diff` from `L`. Probes: only under `<S>/cp4-fix-review/`, never into any worktree. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python` with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests`. No genuine pytest; the controller is running it. The genuine stores in `<S>/cp4-rca/stores` and the probe `L/work/build/keep/cp4-rca/probe_metric_fix.py` may be read.

## Inputs
| Item | File |
|---|---|
| Ruling and root cause | `L/docs/rulings/2026-10-29-stage3.md` item 53; `L/work/build/stage5/cp4-owner-rca.md` |
| Fixer's report | `L/work/build/stage5/cp4-owner-fix-report.md` |

## Process
1. Check that cause 1 binds the metric exactly as `cp4_runs.metric_ref` does (`s1a.figure_fact`), and that cause 2 builds the inherited list word for word from the oracle rule, using the store's CP-1 head. Nothing may be read from the module under test as the expected value.
2. Check that no comparison was loosened: table order, the bound counts 11, 9 and 9, claims, settled limitations and inputs all stay as strict as before.
3. Show that the edited test would fail if CP-4's inherited limitations dropped one CP-1 entry, using the stores and a probe.

## Output (return as text, under 500 tokens)
Verdict (APPROVE / REVISE); findings with file:line and the probe with its exit code; `Not verified:` line.
