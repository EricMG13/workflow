# Builder-Verifier ledger

UTC time | run | command | exit | counts | agent fix-rounds gates-first-pass
2026-11-01 | user OK (this session): controller runs ruff/mypy/new pytest files in builder worktrees; draft PR after review
2026-11-01 | t1 | docs batch | n/a | - | agent=mx-scaffold fix-rounds=1 gates-first-pass=n/a
2026-11-01 | t2 | ruff, format, mypy, pytest tests/test_prove_scope.py; key row 1 | 0 | 6 passed | agent=mx-feature fix-rounds=0 gates-first-pass=y
2026-11-01 | t3 | ruff, format, mypy, pytest tests/test_prove_affected.py; key rows 3-5 | 1 (ruff) | 7 passed | agent=mx-feature fix-rounds=0 gates-first-pass=n
2026-11-01 15:55 UTC | t2 fix1 | RED 5e773408 4 failed/6 passed; ruff, format, mypy 0; pytest | 1 | 9 passed 1 failed (test setup) | agent=mx-feature
2026-11-01 15:55 UTC | t2 fix2 | ruff, format, mypy, pytest tests/test_prove_scope.py; reviewer probes | 0 | 10 passed; probes 0 | agent=mx-feature
2026-11-01 16:00 UTC | t2 fix3 | RED ade9aa45 3 failed/10 passed; ruff, format, mypy, pytest; key row 1 | 0 | 13 passed; KEY MATCH | agent=mx-feature
2026-11-01 16:00 UTC | t2 close | mx-precise scoped re-review PASS; merged at 18deaf89 | - | - | agent=mx-feature fix-rounds=2 gates-first-pass=y
2026-11-01 16:03 UTC | t3 fix1 | RED 8304577b 7 failed/7 passed; ruff 1 (SIM114 :172), format 0, mypy 0, pytest tests/test_prove_affected.py; YAML parse; key rows 3-5 | 1 (ruff) | 14 passed; rows 3-5 PASS | agent=mx-feature
2026-11-01 16:10 UTC | t3 fix2 | RED 455c8917 1 failed/14 passed; ruff, format, mypy 0; pytest tests/test_prove_affected.py; YAML parse; key rows 3-5; N1 probe | 0 | 15 passed; rows 3-5 PASS | agent=mx-feature
2026-11-01 16:10 UTC | t3 close | mx-precise scoped re-review PASS with notes (Q1 Low kept as documented limit); merged at 922bb227 | - | - | agent=mx-feature fix-rounds=2 gates-first-pass=n
2026-11-01 16:20 UTC | user ruling | one draft PR with an 800-line cap exception (1458 changed lines; code+tests+workflows 884) | - | - | -
2026-11-01 17:02 UTC | m1 (t3 round 3, mx-autonomous plan) | RED a9970789 5 failed/29 passed; ruff, format, mypy 0; pytest test_prove_affected+scope; scope self-check; key rows 1,3-5; pins --check | 0 | 34 passed; KEY MATCH; rows PASS | agent=mx-feature (fresh) fix-rounds=3 gates-first-pass=y
2026-11-01 17:02 UTC | t1 fix2 (branch review M2, I1) | docs | n/a | - | agent=mx-scaffold fix-rounds=2 gates-first-pass=n/a
