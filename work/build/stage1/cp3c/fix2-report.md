CP-3C fix round 2 (tests only): R08, R09 and R12 are now killed, and every gate exits 0. Commit b0d77a2 is on top of b9972fd, and the lane is not merged. Worktree: /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-aa5a4817fa00cd287. Only `tests/test_method_cp3c.py` changed; no test exposed a defect, so `cp3c.py` is untouched.

**Finding → test:**
- **N1 (Medium), R08.** `test_b1_a_maturity_on_the_balance_date_is_zero_months` now also asserts, for a maturity exactly on D0:
  - no `("Facility maturity date (term-loan)", "Limitation")` ledger row;
  - no own line containing "before the balance date";
  - the B1 reason appears in no table cell.
- **N1 (Medium), R09.** New `test_b1_the_day_before_the_balance_date_is_a_gap[False]`: 2025-12-30 (D0 − 1 day) gives the B1 gap for months and the inside flag, plus the B1 Limitation ledger row.
- **N2 (Low), R12.** The same test with `[True]` runs that case with the CP-2D horizon missing. Months and the flag still take the B1 gap, not the horizon gap.
- **N3 (Info).** The B5 parameter now sends `blank` as given, so `""` is tested as `""` rather than `None`.

**Mutants** (each run from a full temp copy at `<S>/cp3c-fix2/copy`, with `PYTHONDONTWRITEBYTECODE=1`; restored by sha both times):
- `review_mutants.py`: exit 0. All 17 are killed, R08, R09 and R12 included.
- My fix 1b runner, rerun:
  - Survivors are A19 and A44, both Info as before.
  - A39 is listed because its pattern no longer exists: Q3 removed the reason-string comparison it targeted.

**Gates:** pytest 168 passed, exit 0; `ruff check` 0; `ruff format --check` 0; `MYPYPATH=src mypy --strict` 0. All passed on the first run.

Not verified: none of these was run: the full repository suite, GitNexus `detect_changes`, or the reviewer's other probes in `<S>/cp3c-fix1b-review/`. The CP-2D side of B1 and Stage 2 MC-2 are not built.

agent=general-purpose(opus) fix-rounds=2 gates-first-pass=y
