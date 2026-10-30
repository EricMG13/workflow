# Stage 4 batch 2 review (stage contract; mx-precise, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Change under review: `claude/s4-batch2` `766ca1e..133e2ec` (read with `git show`/`git diff` from `L`; check out only into a fresh copy under `<S>/s4-batch2-review/` with `git archive`; never write into any worktree). `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python`.

`src/deploy_vii/report_view.py` is the user's code. The user allowed only `_prose_lines` (item 30). Spec compliance first, then quality.

## Inputs
| Item | File |
|---|---|
| Plan | `L/work/build/stage4/plan.md` §5 |
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` items 19 (E1, E2), 21 (RED-test rule), 30 (scope of the user's approval) |
| Builder's contract and report | `L/work/build/stage4/batch2-brief.md`; `L/work/build/stage4/batch2-report.md` |
| D12 rule and probe | `L/docs/rulings/2026-10-28-stage2.md` :345-348; `<S>/stage3-review/precise/probe_d12_strict.py` |

## Process
1. **First, the fallback.** `_carries_reference` catches `ValueError` to treat bracketed non-reference text, such as CP-3's `[Insufficient Information]`, as literal prose. The builder says a fact with a valid token plus a stray bracket also renders raw. Judge whether this hides a failure, the rule that forbids a catch-all unless it is documented and logged. Write a probe for the mixed case. Say what the smallest rule is that keeps CP-3's literal and fails closed on any text that holds a well-formed token. For example, decide by a well-formed-token match, not by trying a parse.
2. Check that the `report_view.py` diff stays inside `_prose_lines` and its new helpers, and that `resolve()` is unchanged.
3. Check the RED tests against item 21: they cover product facts, they are not vacuous, and the fail-closed case is real.
4. Check the D12 record against round 5 item 19 (run the strict probe on a fresh copy at 133e2ec).
5. Check that the E2 grep result holds, and that no stub, fake value or `GAP_PLACEHOLDER` remains.

Save each probe as a script in `<S>/s4-batch2-review/` and name it in the finding.

## Output (return as text, under 900 tokens)
Verdict (APPROVE / REVISE); findings ranked High, Medium, Low, Info, each with file:line, failure scenario and probe script; `Not verified:` line.
