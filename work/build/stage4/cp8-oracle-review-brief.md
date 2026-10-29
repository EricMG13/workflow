# Stage 4 CP-8 oracle re-pin review (stage contract; mx-precise, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Change under review: `claude/s4-cp8-oracle` f4d1f93 against 18dc1fa (read with `git show` / `git diff` from `L`; never write into any worktree). `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. You did not prepare this change and you will not build the code that follows it.

## Inputs
| Item | File |
|---|---|
| Preparer's contract and report | `L/work/build/stage4/cp8-oracle-brief.md`, `L/work/build/stage4/cp8-oracle-report.md` |
| Scope | `L/work/build/stage4/plan.md` §5; `L/docs/rulings/2026-10-29-stage3.md` item 19 |
| A7 precedent | `cases/cp2d-owner/builder/build.py`, `cases/cp2d-owner/expected.json`; `L/docs/rulings/2026-10-28-stage1.md` around :490-:505 |

## Process
1. Check the moved `text` against its source (`claims[0].text`) and that every other oracle byte is unchanged. Check that leaving `shown` at `∅ G#` is the A7 form and within item 19's two-field allowance.
2. Rebuild the oracle twice in two fresh copies of the tree at f4d1f93 (under `<S>/stage4-cp8-review/`); the outputs must be identical and equal the committed files. Run `python3 -I cases/pins.py --check` in a fresh copy.
3. Judge the preparer's open point: the planned RED test (no `G#` literal in any settled CP-8 fact) must apply to product facts, while the oracle's `shown` keeps the A7 `∅ G#` pattern. State the exact rule the builder should follow.
4. Run the plan §5 E2 grep: every `cases/*-owner/expected.json` fact with status `known` whose `text` or `shown` holds `∅ G#`. List hits other than CP-8 (they go to the owner).

Save each probe as a script in `<S>/stage4-cp8-review/` and name it in the finding.

## Output (return as text, under 800 tokens)
Verdict (APPROVE / REVISE); findings ranked High, Medium, Low, Info with probe scripts; the RED-test rule; the E2 hits; `Not verified:` line.
