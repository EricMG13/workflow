# Task 1 report

Base b0ac40c confirmed. Note: work/perf-sweep/register.md and probes/time_tests.sh showed as modified after commit 2; not mine, not staged.

## Commit 1 (2ded26c) perf(contracts): group canonical fact ids once in validate_tables
Files: src/deploy_vii/contracts.py, tests/test_validate_tables.py (new, 12 cases; real contracts, validate_tables called directly so no Module validator blocked inputs).
- Test-first on unchanged code: pytest tests/test_validate_tables.py -> 12 passed, exit 0.
- After: same file plus test_method_cp2a/cp8/cpdr/cp2h/cpl10 -> 1426 passed in 8.9s, exit 0.
- Deviation: the loop variable is `canonical`, not `fact` as in the reference text, because `fact` is reused later in the function and mypy --strict flagged an assignment error (Fact | None vs Fact). Behaviour identical.
- Probe micro_trial.py exit 0; "P2 validate_tables current: min 0.032s max 0.045s", "P2 validate_tables grouped: min 0.034s max 0.046s"; all equivalence rows "same".
- Gates: ruff check 0, ruff format --check 0, mypy --strict (both files) 0 (clean, "Success"), no new noqa/type: ignore.

## Commit 2 (17e07ba) perf(earnings): hash the CP-1 producer once per _operands call
Files: src/deploy_workflow/earnings_workflow.py, tests/test_earnings_workflow.py (appended test_operands_hash_the_producer_once; real Module, EarningsDeltaReport, two points: prior+companion, and no-prior).
- Test-first on unchanged code: failed on the count only: `assert 4 == 1`.
- After: 1 passed (-k operands_hash_the_producer), exit 0.
- Also reformatted the one changed `companions=` line to ruff style.
- Gates: ruff check 0, ruff format --check 0, mypy --strict 0, no new suppressions.
- Deferred: heavy earnings tests that reach _operands (controller's timing phase).

Not verified: heavy owner-fixture earnings tests reaching _operands; the full test suite; base-commit timing of P2 on the blob (probe only run after the change); mutation/property tests.
