# CP-3C fix round 2 (tests only; round 2 of 2)

Review: `work/build/stage1/cp3c/fix1b-review.md`. Probes are in `<S>/cp3c-fix1b-review/` (R below), where `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Re-review: mx-precise, by finding id. This is the last round; anything High or Medium left after it goes to the owner.

## Step 0
Use the worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-aa5a4817fa00cd287`, which is at b9972fd. Do not merge the lane.

## Fix (tests; the code is right, so `cp3c.py` changes only if a test exposes a defect)
1. **N1 (Medium).** Pin the B1 D0 boundary.
   - In `test_b1_a_maturity_on_the_balance_date_is_zero_months`, also assert that no `Facility maturity date (<id>)` row and no B1 reason appear anywhere. This must kill R08 (`cp3c.py:1533`, `<` → `<=`).
   - Add a case where the maturity is D0 − 1 day (2025-12-30). It must get the B1 gap. This must kill R09 (the boundary moved to the 1st of D0's month).
2. **N2 (Low).** Add a pre-D0 maturity case with the CP-2D horizon missing. It must kill R12.
3. **N3 (Info).** At `tests/test_method_cp3c.py:1620`, make the `""` parameter send `""` and not `None`.

## Rules
- Files you may change: `tests/test_method_cp3c.py`. Change `src/deploy_workflow/owners/cp3c.py` only if a test exposes a real defect, and report it if so.
- No stub or fake value, and no catch-all.
- Gates, each exiting 0:
  - `PYTHONPATH=src "/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_method_cp3c.py`
  - `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both files.
- Run mutants only from a full temporary copy, with `PYTHONDONTWRITEBYTECODE=1`. Rerun `R/review_mutants.py`: R08, R09 and R12 must be killed.

## Report (as text)
- the commit;
- each finding and its test;
- the `review_mutants.py` exit code and any survivors;
- the gates;
- `Not verified:`;
- the ledger line `agent=general-purpose(opus) fix-rounds=2 gates-first-pass=<y|n>`.
