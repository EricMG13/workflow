
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
