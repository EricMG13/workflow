# Fix batch, fixer 2: test strength (mx-feature)

Fixer 2 is done on `claude/s2-fix-tests` in one commit, `ca9457e` (base a1a0574). Every mutant the reviewers named is now killed, and all gates exit 0. I changed no `src` file and found no defect there. The Edit tool worked on these paths, so I did not use the Bash/Python fallback for edits.

**Items and tests** (the reviewers' mutant scripts, re-pointed at `git archive ca9457e` copies under `<S>/s2-fix-tests/`)
- **CP-3C M1** (`tests/test_connect_cp3c.py`), all 8 survivors of `b5_cp3c_mutants.py` killed:
  - A10 (alias presence): `test_adapter_refuses_an_alias_only_facility` builds a facility with a fy-2025 row and no q4-2025 row.
  - A11, A12 and A13 (alias currency, rate_type, scale): `test_adapter_compares_every_alias_term` is parametrized over currency, rate_type, scale, amount, name and secured_status.
  - A4 (CP-2D scale): `test_cp2d_fact_refuses_a_scale_that_is_not_millions` uses a real fact from a CP-2D head settled by the CP-2D core, with scale 1e3.
  - A5 (view run-id): `test_view_refuses_a_bound_module_of_another_run`, for CP-1 and for CP-2D.
  - R1 and R2 (reader constants): `test_reader_principal_and_base_claims_follow_the_head` sets CP-1's facility principal to 62.5 instead of the oracle's 50.
  - I also updated the module docstring.
- **CP-3C Low:** `test_the_gap_currency_delta_is_still_needed` fails once the CP-2D oracle's T2E.5.r04 and r07 carry a currency. I also corrected the `GAP_CURRENCY` comment.
- **CP-2G M1** (`tests/test_connect_cp2g.py`): `seed()` gets a `cp1d_facts` argument. `test_the_forecast_follows_the_cp1d_facts` seeds a CP-1D head with 40.0, 2.5 and 1.25, where the oracle has 31.8, 1.57 and 0.94. It asserts that `T2H.2.*_supported`, `T2H.8.{base,down}.ebitda_fy26_vs_supported` and the `cp1d_reader` result follow it. The docstring is fixed.
- **CP-4C M2** (`tests/test_connect_cp4c.py`): `seed()` gets `cp2a`, `cp4` and `cp2g_facts` arguments. `test_the_copies_follow_the_cp2g_cp2a_and_cp4_heads` uses:
  - T2H.4 b26 and d26 EBITDA scaled to ×1.1 and ×0.9;
  - the s03 decline raised by 1;
  - a different CP-4 facility text.

  It asserts that the T4E.3 EBITDA and decline copies and T4E.2.c01.facility follow. The docstring is fixed.
- **CP-4C Low:** `test_a_blocked_required_head_is_refused[CP-1|CP-2A|CP-4]` uses real heads blocked by two refused settlements. It calls `_required_module`, plus `cp2a_reader` and `cp4_reader` for CP-2A and CP-4.
- **CP-1C A1** (`tests/test_owner_cp1c.py`): the input ids equal `[prepared-pack, CP-0, CP-1]`, and the pack sha equals `store.read().pack_sha256`.
- **Method notes:** `src/deploy_vii/methods/cp2g.md` and `src/deploy_vii/methods/cp4c.md` each get a bullet on the derived-fact citation rule and the round 5 item 17 hold. I wrote the "31 facts" and "56 facts" counts from `review-A` L1.

**Mutants, before and after** (before: from the reviews; after: my runs)

| Mutant | Before | After |
|---|---|---|
| A10, A11, A12, A13, A4, A5, R1, R2 (`b5_cp3c_mutants.py`) | survived | killed |
| m1 (`p4_d3_status_only_mutants.sh`) | survived | killed |
| m3, m7, m8b (`p4_d3_status_only_mutants.sh`) | survived | killed |
| m9 (`p5_cp4c_required_head_refusal.sh`) | survived | killed |

The full `b5_cp3c_mutants.py` run reports `survivors: []`, 19 of 19 killed. That includes E1 and E2, which the reviewer had marked equivalent. A10 and A13 are what kill the "8 survivors" count; the original b5 log was not re-read, so the mapping of the 8 is from the review text.

**Exit codes**
- The gate-1 pytest command: exit 0 (2672 passed, 11 skipped).
- `pytest --collect-only tests/test_owner_cp1c.py`: exit 0 (47 tests collected).
- `ruff check` and `ruff format --check` on the 4 changed test files: exit 0.
- `MYPYPATH=src:tests mypy --strict` on those 4 files: exit 0.
- `b5_cp3c_mutants.py`: exit 0.
- `p4_d3_status_only_mutants.sh`: exit 0.
- `p5_cp4c_required_head_refusal.sh`: exit 0.
- `b9_cp3c_alias_untested.py` on the tip: exit 0 (all three refuse).
- `b12_gap_currency_target.py`: not run. It reports the mis-aimed target as a state of the oracles, not a test result. The new tripwire test covers the Low.

Not verified:
- The deferred store-run suites were not run (`test_owner_cp1c` was only collected, and `test_owner_cp3c`, `test_owner_cp2g` and `test_owner_cp4c` were not run in full).
- The new tests have not been re-run against the other two fixers' branches.
- The method-note wording was not checked against the close-release text.
- The full suite, mutation runs on the deferred suites and the slow render gates were not run.
- No MCP or library docs were needed.

agent=mx-feature fix-rounds=1 gates-first-pass=y
