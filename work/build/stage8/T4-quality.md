# T4: serve the narrowed `quality_scope` for the CP-1 quality read (stage contract; mx-feature, test first)

Include `work/build/stage8/common.md`. Read:
- the plan, `L/work/build/stage8/T4-plan.md`;
- rulings items 85 and 87 in `L/docs/rulings/2026-10-29-stage3.md`.

## Setup
In your isolated worktree, run `git checkout -b claude/s8-quality 88fbda46`. That is T6's tip, `claude/s8-speed`, which has the speed branch's `earnings_workflow.py`.

## Commits
1. **`test: RED T4`.** Write the plan's RED 1 (`tests/test_financial_workflow.py`) and RED 2 (`tests/test_earnings_workflow.py`, beside :1093). Change `test_financial_workflow.py:1013-1014` to the cell-group coverage count the plan gives.
   - The narrowed scope is the expected value. Build it independently in the test: call `deploy_vii.live.prompts.quality_scope(registers, inputs)`, then replace each `evidence[i]["record"]` with `{k: v for k in ("kind", "reference")}`. Do not import the product helper.
   - The body must equal `json.dumps(expected, sort_keys=True, separators=(",", ":"))` exactly.
   - Keep the :977 no-`record_json`/no-`"quote"` assertion as it is.
2. **`fix: T4`.** Code:
   - add `_quality_read` in `src/deploy_workflow/financial_workflow.py`, as in the plan, with a short comment citing item 87;
   - change both `_projection` quality sites;
   - in earnings, import the helper through its existing import block.

   Keep the binding hash as `inputs.content_hash()`. Add no new try/except.
3. **`docs: T4`.**
   - In `docs/CP1-MODEL-SLICE.md:83-85`, replace "Quality exposes only the actual QualityInputs JSON. Do not expose prompts.quality_scope, which includes raw record_json/citations." with a statement that quality serves `prompts.quality_scope` with each evidence record narrowed to kind and reference (no record_json, citations or quotes), and stays bound to the full QualityInputs hash (item 87).
   - Make the same change to `docs/handoffs/cp1-model.md:87-89`.

## Rules
- Do not touch `src/deploy_vii/**`, `owner_workflow.py`, `host.py` or `promote_cp1`.
- If a driver or test outside the plan's list reads the quality body's `coverage`, `references` or `ceilings`, list it in your report with file:line. Fix it only if it is in the tests folder.
