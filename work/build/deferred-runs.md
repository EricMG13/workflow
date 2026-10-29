
## CP-L10 (Stage 2 fix1, 1ec5ba8)
- `PYTHONPATH=src:tests PY -m pytest -q -p no:cacheprovider tests/test_owner_cpl10.py` (one CP-1 promotion; passed once in fix1, ~23 min under load)

## CP-2D (Stage 2 fix1, ab7671a)
- `CP2D_STORE_RUNS=1 PYTHONPATH=src:tests PY -m pytest -q -p no:cacheprovider tests/test_owner_cp2d.py` (9 store-run tests, never executed)
- `tests/test_financial_render.py` unfinished in fix1 (runs in the batch final gates)

## Stage 2 close release (W2/W3 on `claude/s2-release`)
Genuine owner runs that W2 stopped or deferred (each needs one or more CP-1 promotions, 11-26 min each):
- `PYTHONPATH=src:tests PY -m pytest -q -p no:cacheprovider tests/test_owner_cp4.py tests/test_probe_cp4.py` (A1 stopped it before it finished)
- `PYTHONPATH=src:tests PY -m pytest -q -p no:cacheprovider tests/test_owner_cp1d.py tests/test_owner_cp2e.py tests/test_owner_cp3d.py tests/test_owner_cpl10.py` (A2 stopped it at about 55%, no failures)
- `PYTHONPATH=src:tests PY -m pytest -q -p no:cacheprovider tests/test_owner_cp1c.py tests/test_owner_cp2g.py tests/test_owner_cp2h.py tests/test_owner_cp4c.py` (D added genuine view-tree checks; never run)
- `PYTHONPATH=src:tests PY -m pytest -q -p no:cacheprovider tests/test_owner_cp2d.py tests/test_owner_cp3c.py` (store-run groups skipped; set `CP2D_STORE_RUNS=1` for CP-2D)
- Real-store `drive_cp1` through the shared driver (C): S1a, CP-3C and CP-4 owner runs above cover it.

## Stage 3 (rulings items 19, 23, 26-28)
- **CZR, after Stage 5** (item 19, "Stop at pack"): the full CP-1 run on the filings needs gaps 3 and 4 (`_column_periods` mapping of the filed 10-Q headers, and caption-to-statement mapping), plus the `czr_closed` driver in `tests/czr_runs.py`, which has never run.
- **CP-3C:** `tests/test_owner_cp3c.py` has 11 skipped "needs a real CP-1 promotion (Stage 5)" tests. With the item 23 driver fix (`claude/s3-cp3c-driver`), the run reaches G2, and the G2 `cp3c-fp04-refinancing` genuine cases pass (3, 77 min).
- **G2 coverage gaps; these go to the user** (item 28):
  - (i) The lease R2.5 secondary-pointer assertions for cp3d, cp4 and cp8: `#/cases/<c>/tables`, `displayed_literals` and `lines_positive`. A preparer must first state what "equal" means for G2.
  - (ii) The lease body Acceptance 1 `cites` normaliser (Source and Locator from the passports).
- **G2 genuine deferred set:** `PYTHONPATH=src:tests PY -m pytest -q -p no:cacheprovider tests/test_owner_rendering.py -k genuine_deferred`. That is 48 tests, each 10 to 23 min under load. They are run in shards on the Stage 3 integration tip.
- **Done at the Stage 3 close (2026-10-29):** the G2 genuine deferred set is 51/51 green (35 on I6 49628a0, the 16 that failed there pass on I8 3429790); the CZR earnings shards all pass (first 155 and source 167, ab 36, ac 35 on I5; aa 36 on I8; no CZR file changed I5 to I8).
- **Latent, flagged (item 35):** cp2d `liquidity-runway` and `funding-gap` oracles use plain-string `tabs`; `assert_block_equals_oracle` would raise TypeError if cp2d were added to G2's `DEFERRED`.
