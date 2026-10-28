# CP-1D owner fail-open fix (mx-feature) — report

Commit 0ef0e32 on claude/cp1d-owner-fix (base 3f3eba4); files cp1d.py, test_method_cp1d.py.

- `_one_whole_run`, per reading: any non-ASCII digit (`isdigit()` or `unicodedata.digit`) fails; a letter (`isalpha`) directly before or after a run makes it not whole. Pinned issue unchanged.
- Red on 3f3eba4: 9 tests (fullwidth, Arabic-Indic, superscript, `2.5m`, `25bps` real path; 4 direct rows). Q2/A1/2nd+2.5 lines already refused (two runs); single-figure variants added.
- Frozen: p5_frozen_compare exit 0, moved 0 (19 refusals byte-identical, 3 cases identical; frozen basis quote `...saving of 1.80.` still accepted).
- Probes p3, p4, p8, p9 exit 0; p1, p2 scripts not found, not run. Outputs `<S>/cp1d-owner-fix/`.
- Mutants `<S>/cp1d-owner-fix/p_r13_mutants2.py`: 3 new killed; 2 equivalent survivors (isdigit vs unicodedata.digit agree on all code points); 3 older survivors also survive on 3f3eba4 (`run no comma join`, `run no comma-space join`, `one reading only`).
- Gates: pytest 693 passed 1 skipped; ruff check, format --check, mypy --strict exit 0.
- Cost: refuses `2.5m`, `25bps`, `2nd`, `FY25`, `Q2`/`A1` adjacent, any non-ASCII digit.
- Not verified: p1/p2; NFKC; `Q.5`; full suite.
- agent=mx-feature fix-rounds=0 gates-first-pass=y
