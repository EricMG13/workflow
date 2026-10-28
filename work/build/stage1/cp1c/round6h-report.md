# CP-1C round 6h report (controller-saved from the implementer's hand-back)

# CP-1C round 6h: report

**Commit:** `0ef2dc8` on `worktree-cp1c-stage1` (parent 6ba071b). It touches only `src/deploy_workflow/owners/cp1c.py` and `tests/test_method_cp1c.py` (+37/−8).

## Step 0
- `git merge claude/module-dev-status-review-0981b6` was a **fast-forward** from 50da1c9 to 6ba071b, because the lane already contained 50da1c9. There were no conflicts.
- **No oracle sha moved.** The merge did not touch `cases/cp1c-owner/`. `shasum -a 256` matches every `PINS` value, and `test_oracle_pins` passes. Current values:
  - manifest.json `0b4d4f046a085fc9be91c6ef051d5db3dd1ea46335bfea71ea851b188cb62db3`
  - submissions.json `13be79735066cd58bdcc4cfa7eebddc0eedbe0abb784153a2950ee38455a8912`
  - expected.json `e786acb384007d8a4111a7d572b50744cbcd70ee44954a3730b8703f6752fded`
  - builder/build.py `6c7018dcb31ca1d8abd6e324e7d9048fcfc20ab27501cfb4b4b239dd65fca8b0`

## Rulings → tests
- **6h (a), wording.**
  - New constant: `ISSUER_CONFLICTING = "Not calculable: the issuer's CP-1 value is conflicting"`.
  - `_flag_operands` now returns `Unsettled("missing", ISSUER_CONFLICTING)` for a conflicting value. It used to return `NOT_COMPARED`.
  - The docstring now states the order: excluded, median missing, value conflicting/missing/not_applicable, median zero.
  - Test: `test_6g_conflicting_cp1_fact_takes_the_b1_path`, updated. The T1C.5 issuer deviation and flag now assert status missing, `ISSUER_CONFLICTING`, unit PERCENT/None, `MIXED_PERIOD` and value_class None, and the peer flag stays known. T1C.4 and T1C.6 still assert `NOT_COMPARED`.
  - This test failed first on the old text (`'Not compared: one side is not available' != "Not calculable: the issuer's CP-1 value is conflicting"`), then passed after the fix.
- **6h (a), order.** Test: `test_6h_conflicting_issuer_cells_keep_the_median_missing_reason_first` (new). In the gap case, the coverage CP-1 value is conflicting and the median is missing, so the issuer cells must keep the frozen `NO_MEDIAN` limitation.
  - It passes before and after the fix, because the order already held. It is the only test that kills `conflicting_before_median_missing`.
  - The excluded step can't be told apart for this case: a conflicting value only reaches the issuer row (peer None), which is never excluded. A mutant that moves the check ahead of excluded is equivalent, so it was not added.
- **6h (b):** confirmed, no change. `test_b1_copies_carry_cp1_status_and_limitation` already asserts currency None and scale 1.

## Probes (`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`)
- **`<S>/cp1c-r6h-8/mutants_6h.py`: exit 0.** The baseline passes and all 20 mutants are killed.
  - It is a copy of `<S>/cp1c-r6-fix1/mutants_6g.py`, updated for the new wording. I left the original in place because `fix1-review.md` cites it.
  - It runs against a fresh base, `<S>/cp1c-r6h-8/base` (`git archive 0ef2dc8`). `diff -rq` against the worktree's src, tests, cases and pyproject.toml exited 0.
  - `conflicting_issuer_cells_reworded` was re-targeted at the new branch text.
  - Three mutants were added, all killed: `conflicting_uses_1c2_not_compared` (the old wording), `conflicting_status_not_applicable`, and `conflicting_before_median_missing`.
  - The other 17 mutants are unchanged from 6g and all killed.
- **`<S>/cp1c-r6h-8/new_strings.py`: exit 0.**

## Gates
All exit 0 on the first run:
- pytest on `tests/test_method_cp1c.py`: 125 passed.
- `ruff check` and `ruff format --check` on both files.
- `MYPYPATH=src mypy --strict` on both files.

## Prose and bare-figure hits
None. The new string, as composed on both T1C.5 issuer cells, gives `prose.issues=()` and `bare_figures=()`.

## Stage 2 notes
None new from this round.

## For LEAD
Nothing. No `_unpinned` call was added or removed, and no optional builder sync applies.

Not verified: no oracle case pins a conflicting CP-1 value, so the new cells are checked against the ruling text only. The full suite was not run, because the brief limits pytest to this file. GitNexus `detect_changes` was not run, because the implementer has no MCP tools. How Stage 2 renders a conflicting copied cell is also not checked.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y
