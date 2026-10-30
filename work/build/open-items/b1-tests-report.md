# B1 tests report

Branch claude/oi-b1-tests, base 559ba54. Ledger: agent=mx-feature fix-rounds=0 gates-first-pass=y

## Commits
- e585af3 change 1: functools.partial replaces two untyped lambdas in tests/defect_classes.py
- 81fd883 change 2: ruff C408/FURB157 in test_legal_render.py, test_cp1_chart_render.py (style only; no test applies)
- 89eb960 change 3: three always-skipped G2 placeholders removed (OI-8), comments name covering genuine cases
- a1d5c7b change 4: test_owner_cp3c.py docstring corrected (DEFERRED has cp3c-fp04-refinancing: positive, gap_minimum_cash, gap_no_repricing)
- 8139d49 change 5 RED: shell-css checker with HEAD first-block parser
- 71fc5a3 change 5 fix: all rules applying to .module-list, comments stripped, last flex-shrink must be 0 (OI-9)

## RED (controller-run)
- 8139d49 `pytest -q tests/test_shell_css.py`: 7 failed, 10 passed, exit 1; failed: later-override, later-descendant-override, later-compound-override, later-comma-override, later-media-override, earlier-bad-then-good, only-commented-out. Real app.css passes.
- mypy on the 559ba54 tests/defect_classes.py: exit 1, :858 and :863 "Cannot infer type of lambda [misc]"; on the branch: exit 0.

## Gates at 71fc5a3 (controller-run, all exit 0)
- 10-file pytest set: 747 passed (2m28s)
- ruff check, 8 changed files: All checks passed!
- ruff format --check: 8 files already formatted
- mypy tests/defect_classes.py tests/test_shell_css.py: no issues found in 2 source files
- suppressions: noqa 13 (<=13), type: ignore 5 (<=5)
- collect-only 559ba54 -> branch: cp2h 48->47, cp3c 24->24, cp4 38->37, cp4c 59->58, exit 0; all seven G2 ids named in comments exist in tests/test_owner_rendering.py.

## Deferred genuine runs
cp4c, cp4, cp2h each lose one always-skipped test; owner suites were collect-only. The a3 never-wedges tests using defect_classes are in the 747-passed set.

Not verified: owner suites were only collected, not run; the real-store/G2 genuine cases were not run on this branch; the coverage gate and full suite were not run.
