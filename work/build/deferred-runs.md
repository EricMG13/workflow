
## CP-L10 (Stage 2 fix1, 1ec5ba8)
- `PYTHONPATH=src:tests PY -m pytest -q -p no:cacheprovider tests/test_owner_cpl10.py` (one CP-1 promotion; passed once in fix1, ~23 min under load)

## CP-2D (Stage 2 fix1, ab7671a)
- `CP2D_STORE_RUNS=1 PYTHONPATH=src:tests PY -m pytest -q -p no:cacheprovider tests/test_owner_cp2d.py` (9 store-run tests, never executed)
- `tests/test_financial_render.py` unfinished in fix1 (runs in the batch final gates)
