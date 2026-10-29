# W2 group c report (mx-feature a695f893, claude/s3-w2c 278992b)

W2 group c (CR.2 and CR.3) is built and committed. Every gate you listed exits 0 except `ruff check` (2 existing findings, below).

Worktree: /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a695f893ea6bd29bd
Branch: claude/s3-w2c, based on 423f92e. Tip: 278992bde3cb1e23caf38bdf5924b792a699b3a7
Commits: b7a51c0 (RED tests), then the feature commit (producers and binding move), then 278992b (re-pins).

**Figures**
- **CR.2** is in block `liquidity-runway` on both pathways. It is a waterfall drawn above the tables, with five points: total, value, value, value, total.
  - The summary is the oracle note.
  - The FP-05 test requests CP-2D explicitly. The figure equals FP-04 field by field.
  - A run without CP-2D has no figure.
- **CR.3** is in block `funding-gap`, drawn beside the tables, with one category per facility row.
  - Negatives plot below zero with the bracket spelling.
  - A gap mark is spelled `∅ G<n>`, with n from the report's gap ledger.
  - If every point is a gap, the chart is kind `na` with a reason.
- **T3D.1 binding** moved from `refinancing-paths` to `funding-gap` in `bindings/cp3c.py`. CP-3C is added to the `funding-gap` `_Spec` producers, which are now `("CP-2D", "CP-3C")`. `validate_bindings` is clean for the three CP-3C pack cases.

**Files**
- New: `src/deploy_workflow/liquidity_series.py`. It holds `cp2d_chart_series` and `cp3c_chart_series`, read from settled facts only.
  - A fact that is not known becomes a gap point, never 0.
  - A fact the module does not carry raises `ValueError`.
- `src/deploy_vii/report_view.py`: the `_Spec` change and a new section appended at the end of the file. It has `_liquidity_figure`, `_cr2_figures`, `_cr3_figures` and one registration block labelled "group c". Integration should merge by appending.
- `src/deploy_vii/bindings/cp3c.py`.
- New tests: `tests/chart_wiring_c.py` (helpers), `test_chart_series_cr2.py`, `test_chart_render_cr2.py`, `test_chart_series_cr3.py`, `test_chart_render_cr3.py`. All expected values are read from the oracles.
- Re-pinned tests: `tests/cp3c_runs.py` (two oracle hashes), `test_connect_cp3c.py` (bindings test), `test_connect_cp2d.py` (funding-gap producers), `test_chart_seam.py` (the "registry ships empty" assertion, now "only callable producers"), `test_legal_render.py`.
- `tests/test_method_cp3c.py` needed no change. It already reads `PINS.json`.

**Gates (exit codes)**
- `PYTHONPATH=src:tests .venv/bin/python -m pytest -q -p no:cacheprovider` over the 4 new chart test files, `test_chart_seam.py`, `test_method_cp2d.py`, `test_connect_cp2d.py`, `test_method_cp3c.py`, `test_connect_cp3c.py`, `test_legal_render.py` and `test_connected_render.py`: 1083 passed, 1 xfailed, exit 0. The xfail is group a's S.4 tripwire, which I did not touch. 48 of the passes are the new CR.2 and CR.3 tests (28 series, 20 render).
- RED before the code: the series tests failed at import, and 19 of the 20 render tests failed.
- `python3 -I cases/pins.py --check`: exit 0, 86 paths match.
- `ruff format --check` on changed files: clean.
- `ruff check` on changed files: 2 findings, both in code I did not touch.
  - SIM102 at `report_view.py:312`, the known one.
  - C408 at `test_legal_render.py:220`, existing.
- `MYPYPATH=src mypy --strict` on `liquidity_series.py`, `report_view.py` and `bindings/cp3c.py`: success.
- Suppressions: noqa is 13 and type: ignore is 5. No change.

**Questions and flags for you**
1. **Frozen legal oracle is stale.** `cases/legal/render-expected.json` has funding-gap producers `["CP-2D"]`. Its Not-run note is "CP-2D was not requested", and it now reads "CP-2D · CP-3C was not requested". I cannot edit `cases/`, so `test_legal_render.py` takes the producers from the CR.3 oracle and rewrites the note's producer list from that oracle. The legal oracle needs a regenerate or an owner ruling.
2. **Forged view.** The CR.2 oracle says a forged view "drops" r07 and r08. I read that as the two facts present with status `missing` and a limitation (the lease's missing rule). A fact absent from the module fails closed, since no G# can exist for it.
3. **Companion ids and `axis_sublabel`.** They are carried on the producer record (`sublabel`, `companion_fact_ids`) and checked against the module. Neither is drawn: `ChartMark` has no sublabel field, and the oracle's twin rows are the bare category. Showing them would need a seam change.
4. **Fixture T3D.1 registers.** The CR.3 composer fixtures carry no tables. The test helper `fixture_register` lays out T3D.1 from `cp3c.compose_refinancing` rows. Fixture shown texts (4.5 gives "5", -8.5 gives "(9)") match the oracle.
5. **Left alone.** The `docs/CP3C-OWNER-LEASE.md` and `docs/reuse/manifest.json` D12 records are for the integration pass. I wrote no D12 record for `liquidity_series.py` or the report_view section.

I removed the `.venv` symlink and killed the background run I started. The `test_owner_*` run was too slow to finish. No process is left.

Not verified: `test_owner_cp2d.py` / `test_owner_cp3c.py` / `cp3c_runs.py` real-run suites (a combined run was killed at the timeout; they are deferred); browser or visual rendering of the new figures (structure only); `render()` HTML for CR.2 and CR.3; the full test suite; mutation testing; `jscpd`; GitNexus `impact` and `detect_changes`; CR.3 on FP-05 (deferred, Q-C10); the interaction with the other three W2 groups' registrations (appended blocks not yet merged); the `ChartMark` text check for a fact with declared `decimals` on CR.2 or CR.3 (all test facts have `decimals` None).

Ledger: agent=mx-feature fix-rounds=0 gates-first-pass=n
