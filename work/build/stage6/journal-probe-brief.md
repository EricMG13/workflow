# Stored CP-1 journals vs the new blank checks (stage contract; mx-precise, read-only)

The lane is `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`, tip ef37a3f; the same code is in `codex/checkpoint` b6c7053. The open-items merge added two refusals to `src/deploy_vii/source_context.py` `validate_source_context`:
- OI-14: a blank (`is_blank`) scope, source, entity or review limitation is refused;
- OI-20: a blank `event_scan_explanation` is refused for every assessed source.
The open-items note says a CP-1 journal written before these changes that holds such a blank value would now make `source_context()` raise when it is rebuilt (canonical gaps, rendering, narrative). None exists in `cases/` or `tests/`. Stored journals elsewhere were never checked.

Write probes only under the lane's `work/build/keep/journal-probe/`. Run Python as one plain command, for example `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests "<lane>/.venv/bin/python" -I <probe>`, from the lane root. If it is refused, stop and report it; do not work around it. Run no test suite.

## Process
1. **Find stored CP-1 source-context payloads** (stores written by `OwnerWorkflow`, `FinancialWorkflow` or `EarningsWorkflow`, and any saved `source_context` submission JSON). Look in:
   - every worktree under `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/`, excluding `.venv`;
   - the lane's `work/build/keep/`, including `s5-final2/czr-root`;
   - the scratchpads under `/private/tmp/claude-501/`, whose folder names start with `-Users-ericguei-Documents-Deploy-Workflow` (the Workflow Test and Modules sessions' CZR and G2 runs);
   - `cases/**`, as the control.
   Learn the store layout from `deploy_vii` and `deploy_workflow` first, so the search is exact rather than a grep guess.
2. For each payload found, run the current `validate_source_context` (and the `source_context()` rebuild where it can be reached without a model). Record which ones now fail, and with which issue.
3. Report the counts by location, and every failing payload with its path and issue. Say which ones belong to live, frozen or reused material (a case oracle, a recorded submission such as `cases/czr-2026q2-earnings-update/submissions-partial.json`, a G2 delivery) and which are throwaway run output.

## Output (text, under 500 tokens)
- the locations searched and the payload counts;
- every failing payload, with its path, issue and kind;
- the probe path and its exit code;
- a `Not verified:` line.
