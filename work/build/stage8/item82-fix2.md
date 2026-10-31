# Item 82 fix round 2: the cash-scope blocker stays BLOCK (stage contract; mx-feature, test first)

Include `work/build/stage8/common.md`. There is one exception to its rule against editing `src/deploy_vii/**`: you may edit `src/deploy_vii/canonical_audit.py`, plus its D12 record in `docs/reuse/manifest.json`. This change is inside the user's item 82 approval. The ruling is item 88 in `L/docs/rulings/2026-10-29-stage3.md`.

## Setup
In your isolated worktree, run `git checkout -b claude/s7-absent-input-3 81e224f1`.

## Commits
1. **`test: RED item 82 cash-scope blocker`**, in `tests/test_cp1_absent_input.py`. Add one unit test beside the L1 and L2 helper tests: a public BLOCK `PeriodCheck` with difference None, whose explanation contains `"Cash scope differs across source periods: fy-2025"` exactly as `period_reconciliation.py:310` on `claude/s8-vii` builds it. Assert that `absent_input_limitation(...)` returns None.
   - Build the check the way the existing L1/L2 tests build theirs.
   - Import the new constant inside the test.
2. **`fix: item 82 cash-scope blocker`**, in `canonical_audit.py`:
   - Add `CASH_SCOPE_BLOCKER = "Cash scope differs across source periods: "` with a comment naming its source line (claude/s8-vii `period_reconciliation.py:310`, arriving with the s8-vii merge).
   - Add it to the child-difference refusal in `absent_input_limitation`.
   - Update the docstring's list of what stays BLOCK.
3. **`docs: D12 record for item 82 fix 2`.** Append a new `post_import_patches` record for `canonical_audit.py` to the top-level `post_import_patches` array (not `local_patch_lineage`), chained from the last canonical_audit.py record's `sha256`:
   - `prior_project_sha256` is the file at the fix commit's first parent, and `sha256` is the file at the fix commit (use `shasum -a 256`);
   - `project_commit` is the fix commit;
   - `review` is the item 88 ruling.
