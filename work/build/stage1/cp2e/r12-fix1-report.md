M1 is fixed with one test-only commit, and every gate and probe passes. Worktree was clean at 3c883e5 (Step 0 OK).

**Commit:** `cfd6e3e` (touches only `tests/test_method_cp2e.py`; ends with the Co-Authored-By line).

**Test:** `test_class_non_blank_limitation_off_insufficient_information`, parametrized over `"a limit"` (plain) and `"a​"` (cf-bearing). It sets the value on `assessments[0]`, asserts that assessment is not Insufficient Information, and expects `_issues_with(raw) == ("assessments[0]: limitation is required for Insufficient Information and only for it",)`. It passed against the current code, so there is no code defect. No product code was changed.

**Probes:** I ran them in copies under `<S>/cp2e-r12-fix1/`, against fresh `git archive` copies of HEAD (`head/`) and 128c3ca (`base/`), with PYTHONDONTWRITEBYTECODE=1.
- `mutants_review.py` exits 0. The baseline passes and all 8 mutants are killed, with 0 survivors. "Drop the 'only for it' half" is now killed by `test_class_non_blank_limitation_off_insufficient_information[plain]`.
- `p_only_for_it_base.py` exits 1. It exits 0 only if the mutant is killed at base and survives at head. Now it is killed at both: base fails on `...limitation_off_insufficient_information[spaces]`, and head fails on the new `[plain]` and `[cf-bearing]` tests. So the coverage loss is closed.

**Gates (all exit 0):**
- pytest on `tests/test_method_cp2e.py` and `tests/test_defect_classes_selfcheck.py`: 681 passed.
- `ruff check` on the test file.
- `ruff format --check` on the test file.
- `MYPYPATH=src mypy --strict` on the test file.

**Not verified:** The full suite and other test files were not run. The mutant set covers only the 8 reviewer mutants, so other mutations of the limitation rule were not tried. The Cf twin pins `not is_blank` only through the existing "stated uses strip" mutant, which is killed by the blank-limitation test as well. No test needed beyond M1, which is itself a test.

agent=mx-feature fix-rounds=1 gates-first-pass=y