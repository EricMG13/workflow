# Stage 3 fix round 1 re-review (stage contract; mx-precise, read-only, scoped)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Read with `git show`/`git diff` from `L`. You may check a branch out only into a fresh copy under `<S>/fix1-rereview/` (`git archive <sha> | tar -x -C …`); never write into any worktree. Python: `L/.venv/bin/python`.

Check **only the findings fixed**, against item 22's rulings. Do not re-review unchanged code.

| Branch | Diff | Findings it fixes |
|---|---|---|
| `claude/s3-fix1-g2` | `18dc1fa..ee95ffb` | arch M1 (the `cp3c-fp04-refinancing` row), precise M1 (the DR.6 suffix), precise L1 / arch L2 (the S.4 title) |
| `claude/s3-fix1-rest` | `18dc1fa..2823590` | precise M2 (the CP-OS cache), M3 (D12), M4 and L3 (the legal CR.1 targets), arch L1 (format; the cp3c builder deliberately left unformatted) |
| `claude/s3-mypy-chart` | `18dc1fa..e43aad9` | mypy on the G2 test pair (annotations only) |

## Inputs
- Rulings: `L/docs/rulings/2026-10-29-stage3.md` item 22.
- Findings: `L/work/build/stage3/review-arch.md` and `review-precise.md`.
- Fix reports: `L/work/build/stage3/fix1-g2-report.md`, `fix1-rest-report.md` and `mypy-chart-report.md`.
- Reviewers' probes: `<S>/stage3-review/arch/` and `<S>/stage3-review/precise/`. Use `probe_g2_title_and_reason_fix1.py` for the new G2 API.

## Process
1. For each finding, confirm the fix meets item 22, and that the reviewer's probe now fails to reproduce the defect. Run each probe in a fresh copy of its branch and report its exit code.
2. **G2 deviation.** The composer fixture `tests/test_cp1_chart_render.py:150` spells the S.4 title "current principal", and F1 compares it exactly. Judge which is right: that fixture's title, or the producer and the ruled regex ("principal at").
3. Check that no fix weakened another assertion, and that the CP-OS cache key now covers the store and publication content.
4. Confirm that the three branches touch disjoint files, apart from `cases/PINS.json`, which is regenerated on merge.

The CP-OS genuine suite passed on the F2 tree (44 passed). Do not rerun it.

## Output (return as text, under 900 tokens)
Verdict per branch (APPROVE / REVISE); findings ranked High, Medium, Low and Info, each with its probe and exit code; the S.4 fixture ruling; `Not verified:` line.
