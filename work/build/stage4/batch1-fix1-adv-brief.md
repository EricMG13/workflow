# Stage 4 batch 1 fix round 1: scoped adversary re-review (stage contract; mx-adversary, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Change under attack: `claude/s4-batch1-fix1` `515a8c6..715dc98` (read with `git show`/`git diff` from `L`). Work only in fresh copies under `<S>/s4-batch1-fix1-adv/`, made with `git archive 715dc98 | tar -x -C …`; never write into any worktree. Delete large copies when done (disk is low). `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python`. `pyproject.toml` sets `pythonpath = ["src", "."]`: to test a mutated `src`, pass `-o pythonpath=<copy>/src .` or run from the copy's root. One genuine pytest process at a time.

This is a re-review: check only that High 1 and Medium 1 from your earlier audit are closed, and that the Medium 1 rule cannot refuse a genuine run.

## Inputs
| Item | File |
|---|---|
| Your earlier audit and probes | `L/work/build/stage4/batch1-adversary.md`; `<S>/s4-batch1-adv/probes/` |
| Ruling | `L/docs/rulings/2026-10-29-stage3.md` item 33 |
| Fixer's report | `L/work/build/stage4/batch1-fix1-report.md` |
| Producer rule | `src/deploy_vii/execution.py` `Execution.begin`, `finish`, `interrupt` (read only) |

## Process
1. **Medium 1.** Rerun P-A. Then try to get past the new `_verify_transition` equality: change any of `module_id`, `inputs`, `number`, `repair_of`, `repair_issues` in a valid step, a rejected step, an interrupt, the final snapshot, or a step of another ticket; and the case where the attempt does not exist before the step. Report each verdict.
2. **No genuine refusal.** Check by code reading, with a fast-harness probe where you can, that no producer path changes those five fields after `begin` (finish, interrupt, a within-attempt repair, CP-MODEL's second attempt after a failed first publication). Name each field write in `execution.py` with file:line.
3. **High 1.** Judge the rebuilt tests: the forged receipt reaches `verify_owner_run_receipt`; each fails when the check it targets is made lenient (the fixer's evidence: P-M tests need both checks lenient, the P-F test the publication-path check alone); and patching `execution.current_inputs` does not also weaken the verifier's own replay (the verifier must not call the patched function). Run the three `forgery_cp_model` tests once.
4. **Info.** Check that the new `PACK_TOOL_MODULES` assertion in `test_tool_use_sections_match_registrations` is not vacuous (a mutant of `host._SOURCE_STEPS` makes it fail).

Save every probe as a script in `<S>/s4-batch1-fix1-adv/` and name it in its finding.

## Output (return as text, at most about 1k tokens)
Verdict (PASS / FINDINGS); findings ranked High, Medium, Low and Info. Each finding gives file:line, the forged input, the verifier's verdict, and the probe script with its exit code. End with a `Not verified:` line.
