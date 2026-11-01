# Builder-Verifier ledger

UTC time | run | command | exit | counts | agent fix-rounds gates-first-pass
2026-11-01 | user OK (this session): controller runs ruff/mypy/new pytest files in builder worktrees; draft PR after review
2026-11-01 | t1 | docs batch | n/a | - | agent=mx-scaffold fix-rounds=1 gates-first-pass=n/a
2026-11-01 | t2 | ruff, format, mypy, pytest tests/test_prove_scope.py; key row 1 | 0 | 6 passed | agent=mx-feature fix-rounds=0 gates-first-pass=y
2026-11-01 | t3 | ruff, format, mypy, pytest tests/test_prove_affected.py; key rows 3-5 | 1 (ruff) | 7 passed | agent=mx-feature fix-rounds=0 gates-first-pass=n
