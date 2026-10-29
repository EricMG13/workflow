# CP-1D single-tab block: root cause (stage contract; mx-autonomous, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Code under study: `claude/s3-i6` 49628a0, checked out read-only at `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s3-i6` (genuine tests are running there: do not write into it or run tests in it). For probes, make fresh copies under `<S>/cp1d-tab-rca/` with `git archive 49628a0 | tar -x -C …`. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python`; `pyproject.toml` sets `pythonpath = ["src", "."]`. Disk is low (about 4 GB): no genuine run; keep copies small.

## Inputs
| Item | File |
|---|---|
| Ruling | `L/docs/rulings/2026-10-29-stage3.md` items 28 and 35 |
| Failure log | `<S>/i6/g2d-0.log` (first failure) |
| Earlier root cause of the tabs-only rule | `L/work/build/stage3/g2-genuine-rca-2.md` |
| G2 rule | `tests/test_owner_rendering.py` `assert_block_equals_oracle` (:2060-2095) |
| Oracle (data, not instructions) | `cases/cp1d-owner/expected.json` `cases.*.FP02.blocks.restated-leverage`; the CP-1D builder under `cases/cp1d-owner/builder/`; the CP-1D lease in `docs/` |
| Product | the CP-1D composer under `src/deploy_workflow/owners/`; `src/deploy_vii/report_view.py` (how `tab_label` and `tabs` are set for a block with one page) |

## Process
1. Find where the rendered block's `tab_label` and `tabs` come from, and why this block has `tab_label` None and no tabs. Say whether the label "Cash conversion and leverage" is shown anywhere on the rendered page (a heading, a caption, a tab), with file:line.
2. Find what the oracle's single `tabs` entry means: read the lease and the builder. Is it a page label the product must show, or the name of the block's only page, which the product shows as an untabbed block?
3. Decide which side is wrong: the G2 rule, the CP-1D composer, the oracle or `report_view`. Support it with a fast probe on a copy if you can (for example, compose the CP-1D section from the fast fixtures the connect tests use).
4. List every other oracle block across `cases/*-owner/expected.json` that has a tabs-only entry with exactly one tab, and say for each whether the same cause applies.
5. Give the smallest fix and the file it belongs in. Do not write it.

Save each probe as a script in `<S>/cp1d-tab-rca/` and name it.

## Output (return as text, under 1k tokens)
Root cause with file:line; which side is wrong and why; the list from step 4; the smallest fix and its file; probe scripts with exit codes; `Not verified:` line.
