# Release fix 1 report (mx-feature)

Tip SHA: a50efb2 (branch claude/s2r-f1, on 5a6a746). Everything in scope is done and the gates exit 0.

Each new test failed before the fix for the reported cause.

**Items**
1. **CP-L10.** `cpl10.py` `_unique` now calls `one_per_page`. `_Cells.add` and `_claim` both go through `_unique`, so derived cells and claims get one citation per (source, page). Copied cells keep CP-1's own citations.
   - Rule text updated in `build.py`: `CLAIM_CITATION_RULE` and `lineage_citations`.
   - `tests/test_method_cpl10.py` now pins `one_per_page` instead of the concatenation. The `_citations` oracle helper does the same. The test's copied-cell expectation reads CP-1's own citations.
   - New test `test_derived_cells_cite_one_quote_per_page`.
2. **CP-2A.** `lineage` now returns `one_per_page(cited)`, with a new test `test_lineage_cites_one_quote_per_page_the_first`.
3. **CP-2D.** A sum copy (an operand with `+`) did carry two quotes from one page. `_Composer._copy_citations` now applies `one_per_page` to sum copies only. Single-fact copies are unchanged. New test `test_sum_copy_cites_one_quote_per_page_the_first`.
   - The claims `_citations` union is left as is.
4. **CP-1D.** The private `_one_per_page` is removed and the shared helper is imported. The connect test now also asserts `cp1d.one_per_page is blank.one_per_page`.

**Oracle values moved:** none. The only literal change in `expected.json` and `manifest.json` is the rule wording. The citation markers are unchanged, and the tests apply `one_per_page` when they bind them.

**Pinned or builder files changed:**
- `cases/cpl10-owner/builder/build.py`
- `cases/cpl10-owner/expected.json`
- `cases/cpl10-owner/manifest.json`
- `cases/PINS.json`

I changed no other `cases/*`, no lease, and none of the other off-limits files. The `src/` files are `cp1d.py`, `cp2a.py`, `cp2d.py` and `cpl10.py`. The test files are `test_connect_cp1d.py`, `test_connect_cp2d.py`, `test_method_cp2a.py` and `test_method_cpl10.py`.

**Rebuild:** I ran `chain.sh` twice on this tree. Both runs exited 0, and all `expected.json` and `manifest.json` shas were identical across the two runs. `pins.py` then `pins.py --check` gave 75 paths and exit 0.

**Gate exit codes**
- Method and connect tests for CP-L10, CP-2A, CP-2D and CP-1D, plus `test_owner_blank`: 1977 passed, 2 skipped, exit 0. No `test_owner_<cp>` file was run.
- The c8 probe: exit 0.
- `ruff check` and `ruff format --check` on the 8 touched files: exit 0.
- `mypy --strict` on the 4 touched `src/` files: exit 0.
- `noqa` count is 13 (same as HEAD). `type: ignore` is 5.

Not verified: the `test_owner_<cp>` genuine runs, the full test suite, and the coverage, jscpd, complexipy and bandit gates. No real CP-1 head was exercised for a sum copy or a CP-L10 cell whose two quotes share a page. That behaviour is covered only by the fixtures and the stubbed `_Composer` selection.

agent=mx-feature fix-rounds=1 gates-first-pass=y
