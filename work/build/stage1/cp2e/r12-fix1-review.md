**Verdict: APPROVE. M1 is closed.**

All four checks pass, on a fresh `git archive cfd6e3e` copy run with `PYTHONDONTWRITEBYTECODE=1`.

1. **The test expects exactly the pinned issue.** The new test is `test_class_non_blank_limitation_off_insufficient_information` at `tests/test_method_cp2e.py:1216-1224`. It asserts `_issues_with(raw) == (f"assessments[0]: {_ONLY_II}",)`, an exact one-element tuple. `_ONLY_II` (line 1189) is the literal message from `src/deploy_workflow/owners/cp2e.py:723`. The test also asserts its precondition: the positive submission's `assessments[0]` category is not Insufficient Information.
2. **The Cf twin is a real non-blank value.** The twin is `"a​"`, a letter followed by a zero-width space. Called directly, `deploy_workflow.owners.blank.is_blank("a​")` returns `False`, so the value is non-blank and reaches the rule as a stated limitation. It contains no digits.
3. **The reviewer's mutant is now killed.** `cp2e-r12-review/mutants_review.py` gives baseline exit 0 and all 8 mutants killed. "drop the 'only for it' half" now fails at `test_class_non_blank_limitation_off_insufficient_information[plain]`. The script reports 0 survivors.
4. **The diff changes nothing else.** `git diff --stat 3c883e5..cfd6e3e` shows only `tests/test_method_cp2e.py` changed, with 11 lines added and 0 removed: one parametrized test, no edits to existing tests and no source changes. It has no stub, fake value or catch-all.

**Exit codes:**
- Gate (`pytest -q -p no:cacheprovider tests/test_method_cp2e.py tests/test_defect_classes_selfcheck.py`): exit 0, 681 passed.
- Mutant script (`mutants_review.py <copy>`): exit 0.

The archive copy is at `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cfd6e3e-rerev`. The mutant script is `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2e-r12-review/mutants_review.py`.

Not verified: whether the Cf twin alone kills the "only for it" mutant, because the script stops at the first failure (`-x`) and the plain case fails first; I did not run the fixer's copy under `cp2e-r12-fix1/`; I did not run ruff or mypy on the changed test file; I did not run the full suite.