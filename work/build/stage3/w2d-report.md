# W2 group d report (mx-feature aba2601f, claude/s3-w2d 2943d7b)

W2 group d report. Worktree: /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-aba2601f6bf888beb. Branch claude/s3-w2d, tip 2943d7b25427b48837f6b29bbcacb0e3a99431bd (from 423f92e). The .venv symlink is removed, no background process is left, and the tree is clean.

**Open question: the DR.6 "Not computable" chip is not built.** No `Figure` or `Block` field carries a status chip, and `block_state_display` has no such word. Adding one is a seam change (a `Figure` or `Block` field plus `app.js`), outside group d. I left a strict-xfail tripwire, `test_the_block_shows_the_not_computable_chip`, in `tests/test_chart_render_dr6.py`. It XPASSes, and fails strict, once the seam gains the field. Every other DR.6 target is met.

**Figures done**
- **DR.2** (`recovery-by-class`): grouped chart, above the tabs.
  - Series labels read "Base 4.00x", and a missing multiple leaves the bare scenario name.
  - Equity drops out of the marks and the twin and is listed in the record.
  - Hatching follows the multiple's `value_class`. Only `source` is not hatched. A missing multiple hatches by default.
- **DR.3, DR.4, DR.5** (`value-allocation-claims`): waterfall build-up, classes by (rank, id), then residual, then the EV total.
  - Marks keep the two-decimal texts; the decimals come from the W1 seam.
  - The T4E.9 checks (total claims, creditor distributions, balance) are companion ids of the EV mark, not steps.
  - A chart with no known point is kind na and takes the module's own limitation as its reason.
- **DR.6** (`rating-triggers`, CP-2H): an n/a frame with no marks and an empty absent twin.
  - Positive reason is the oracle text and carries no G#.
  - When T2R.4 or T2R.5 facts are missing, the reason starts with the gap text and appends "(∅ G<n>, …)", read from the report index.
  - It fails closed if CP-2H stops stating a synthetic agency source.
- **Refused or blocked:** a refused, blocked or cp2g_blocked producer gives no figure and keeps its honest state. The blocked case quotes the first limitation. This is tested for all three blocks.

**Files**
- New `src/deploy_workflow/restructuring_series.py` holds `cp4c_chart_series(module)`, which returns DR.2 and then DR.3-5 as typed records.
- New `src/deploy_vii/distressed_figures.py` builds the `Figure`s and holds `PRODUCERS`.
- `src/deploy_vii/report_view.py` gets one appended block, `_register_group_d()`, which registers the three producers for `distressed_restructuring` only. The integration pass can merge by appending.
- New `tests/chart_dr_support.py`, `test_chart_series_dr2.py`, `test_chart_series_dr345.py`, `test_chart_render_dr2.py`, `test_chart_render_dr345.py`, `test_chart_render_dr6.py`.
- Edited `tests/test_chart_seam.py`: `test_the_registry_ships_empty…` could not survive any registration, so I replaced it with `test_the_registry_holds_only_producers_registered_for_table_blocks`. The other groups will hit the same line.
- No bindings, `cases/`, leases or manifest touched.

**Gates (all exit 0)**
- One run of the group d tests, `test_chart_seam.py`, `test_method_cp4c.py`, `test_connect_cp4c.py`, `test_method_cp2h.py`, `test_connect_cp2h.py`, `test_legal_render.py`, `test_connected_render.py` and `test_cp1_chart_render.py`: 2155 passed, 1 xfailed (the chip tripwire).
- The group d new tests alone are 119, and the RED commit failed before the code.
- `cases/pins.py --check` matches 86 paths.
- `mypy --strict` is clean on the three changed `src` files.
- `ruff check` on my files shows only the known SIM102 at `report_view.py:312`.
- `ruff format --check` fails only on four files I did not touch: `cp1d.md`, `earnings.py`, `financial_series.py` and `tools/upstream.py`.
- Suppressions are unchanged: noqa 13, type: ignore 5.

**Rulings and interpretations**
- **CP-4C re-pins:** none were needed. No CP-4C test literal referenced the reworded `d7_rendering` prose.
- **Missing-fact dimensions:** `_chart_fact_cell` rejects a missing fact whose currency is None (a missing EV), so the producers use it for known facts only and read gaps through `_cell`. I did not touch the seam.
- **DR.3-5 hatching:** the oracle gives `hatched: true` per figure only. I hatch every mark on the scenario's multiple basis, as in DR.2, EV total included.
- **DR.6 gap citation:** the oracle says only that the reason "carries" the ∅ G<n>, so the "(∅ G3, …)" suffix format is mine.

Not verified: browser appearance of hatched DR.2 bars, DR.3-5 waterfalls and the DR.6 frame (SVG strings only); the full `render()` HTML path for these figures; the real Stage 5 owner runs (`cp4c_runs`/`cp2h_runs`; the tests use composer modules and seeded stores); the chip; whether "hatched" on DR.3-5 gap and total marks matches the intended design; mutation testing; the full suite beyond the listed files; GitNexus impact and detect_changes; and no test or fixture for a CP-2H head that is not synthetic.

Ledger: agent=mx-feature fix-rounds=0 gates-first-pass=y (the one first-run failure was the W1 empty-registry test, a known consequence, fixed in-task).
