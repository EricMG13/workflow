# Stage 3 chart wiring W2: producers and block wiring (stage contract; groups a-d)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). You run in your own isolated worktree. Before any edit, run `git checkout -b claude/s3-w2<g> 423f92e` there, where `<g>` is your group letter. 423f92e is the W1 seam tip on `claude/s3-wire`, on top of the frozen oracles 731059f. Write only inside your own worktree. Python: `L/.venv/bin/python`. If `.venv` is needed in the worktree, symlink it and remove the link before you hand back.

You prepared and reviewed none of the oracles. You never edit `cases/`, the leases or `docs/reuse/manifest.json` (the integration pass adds the D12 records).

## Inputs
| Item | File |
|---|---|
| Your oracles (every expected value, and your `builder_targets`) | `cases/charts/<fig>-expected.json` for your group |
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` items 3, 5, 6, 8, 9 and 11 |
| Seam API (W1) | `L/work/build/stage3/w1-report.md`; `src/deploy_vii/report_view.py` (`register_figure_producer`, `FigureProducer`, `_chart_fact_cell`, `_chart_mark`, `strict_multiple`, `_cp1_period_figures`) |
| Producer record shape | `docs/CP1-CHART-SLICE.md:66` (`fig_id`, `title`, `kind`, `unit_class`, `unit`, `series`, `points`, `reason`; points carry `fact_id` and companion fact ids) |

## Groups
- **a: S.5 and the FP-04 S.4.**
  - Register `_cp1_period_figures` for `financials-credit-metrics` on `credit_snapshot` only.
  - Make `maturity-wall` kind `chart`, with the CP-1 T4.18 binding in `bindings/cp1.py`.
  - Turn the strict-xfail tripwire at `tests/test_connect_cp2d.py:1179` into a passing test with the frozen labels (rulings item 5, last bullet), and extend the CP-1 fixture or give S.4 its own entry point.
  - Cover the `s4fp04` cases, including `cp2d_settled_cp1_not_settled` and a view with CP-1 present but unsettled.
- **b: RV.3 (CP-1C) and CR.1 (CP-4).**
  - Write the producers. RV.3 has panels `RV.3a` and `RV.3b`, with the `range` kind and the percent unit. CR.1 uses the `bullet` kind and the strict parse on the T4.9 threshold.
  - Register the producers on their blocks.
  - Re-pin any CP-1C test literal that the item 9 prose move invalidated.
- **c: CR.2 (CP-2D) and CR.3 (CP-3C).**
  - Write the producers. CR.2 is the bridge from settled ids only, on both pathways; the FP-05 render test requests CP-2D explicitly (rulings item 6.2). CR.3 draws negatives below zero, and facility rows are its categories.
  - Move the T3D.1 binding from `refinancing-paths` to `funding-gap` in `bindings/cp3c.py`, and add CP-3C to the `funding-gap` `_Spec` producers (item 6.1).
  - Re-pin the CP-3C test literals (`tests/cp3c_runs.py`, `tests/test_method_cp3c.py`) to the frozen oracle.
- **d: DR.2, DR.3-5 (CP-4C) and DR.6 (CP-2H).**
  - Write the producers. DR.2 hatching follows the basis. DR.3-5 is a build-up waterfall that keeps the two-decimal texts.
  - DR.6 is the n/a frame, with the reason set per case (item 8 M1 and its Low).
  - Each figure gets its refused-or-blocked case.
  - Re-pin the CP-4C test literals (`tests/test_method_cp4c.py`, `tests/test_connect_cp4c.py`) to the frozen oracle.

## Process
1. **Test first.** For each figure, write `tests/test_chart_series_<fig>.py` and `tests/test_chart_render_<fig>.py` as its `builder_targets` say, reading every expected value from the oracle. Confirm they fail.
2. **Producers.** Build each producer where its `builder_targets` place it. Values come only from the settled module view. No chart recomputes a value, and a missing or `not_meaningful` fact is a gap with its G#, never 0. Register with `register_figure_producer`. Put the registration in one module-level block that names your group, so the integration pass can merge the four groups by appending.
3. If you need a change outside the W1 seam API, your producers, your bindings and your tests (for example a new seam rule), stop and report it.
4. Commit after the RED tests and after each figure. Each commit ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates (report each exit code)
Run with `PYTHONPATH=src:tests L/.venv/bin/python -m pytest -q -p no:cacheprovider`:
- your new chart tests;
- `tests/test_chart_seam.py`;
- `tests/test_method_<cp>.py` and `tests/test_connect_<cp>.py` for each module your group touches;
- `tests/test_legal_render.py` and `tests/test_connected_render.py`.

Also:
- `python3 -I cases/pins.py --check`.
- `ruff check` (the known SIM102 at `report_view.py` `ChartSpec.coherent` predates this work), `ruff format --check`, and `MYPYPATH=src mypy --strict` on changed `src/` files.
- Suppressions: `git grep noqa -- src tests | wc -l` ≤ 13; `git grep "type: ignore" -- src tests | wc -l` ≤ 5.

## Outputs (report as text, at most about 1.5k tokens)
- Your worktree's absolute path and the branch tip SHA; files changed; figures done; tests and counts; questions; `Not verified:` line; ledger line `agent=mx-feature fix-rounds=0 gates-first-pass=<y|n>`.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged. Stop any background process before you hand back.
