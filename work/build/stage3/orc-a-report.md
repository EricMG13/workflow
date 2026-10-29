# Chart oracle preparer A report (mx-feature a17dc994, claude/s3-orc-a 6c4475d)

Group A oracles are done and committed in one commit, tip `6c4475d` on `claude/s3-orc-a`. The double fresh-copy rebuild, the pins check, `ruff check` and `ruff format --check` all exited 0. I did not touch `src/`, `tests/`, group B files or any other frozen oracle, so no value moved.

**Files** (under `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s3-orc-a`): `cases/charts/builder/build_a.py`, `cases/charts/{s5,rv3,cr1,s4fp04}-expected.json`, `cases/pins.py` (two new patterns plus docstring) and a regenerated `cases/PINS.json` (+5 paths). Values come only from the module oracles; the builder holds only form literals with source lines. It spells values with the display.py rules. I checked those rules against `display.format_value`, and the module oracles' own `shown` strings are asserted equal.

**Per figure**
- **S.5:** 8 points (revenue and adjusted_ebitda over Q1-Q4 2025), 0 gaps. Design `fp-01:66,124`, brief `01:36`. Revenue 30 each quarter. Adjusted EBITDA is exactly 7.5, so it spells "8" at 0 dp under display.py. The mark carries the exact 7.5.
- **RV.3:** two panels (percent: margin and FFO to debt; multiple: leverage and coverage). Positive case has 24 points, 0 gaps; gap case has 20 points, 2 gaps. Peer p05 is excluded and contributes no mark. Design `fp-03:53-54`, brief `03:36`.
- **CR.1:** 3 points per case (Threshold, Current, Headroom). The gap case has 1 gap (`T4.9.r01.headroom`). `gap_false_same_definition` is a refusal, so nothing is drawn. Design `fp-04:34,58`, brief `04:27`.
- **FP-04 S.4:** 1 point, 50 at 2029-12-31, plus the T2E.4 tab cells copied from the CP-2D oracle. Design `fp-04:42`, brief `04:31`.

CP-1 fact ids exist only at run time, so S.5 and S.4 pin fact coordinates instead. These are the T4.10 row `field_1` with the QUARTER basis id (it equals `tests/test_financial_series.py` `BASES`), or the T4.18 row with its period, plus companion coordinates.

**Moved values in other oracles:** none. S.4 needs no `contracts.py` or CP-MODEL edit. The `render-expected.json:1956` pin stays with the Q-C1 check.

**Builder targets:** each file's `builder_targets` lists the tests and assertions. Highlights:
- **S.5:** a producer test, and `report_view.build` on a `credit_snapshot` run showing S.5 with placement `beside` in `financials-credit-metrics`.
- **RV.3:** a CP-1C producer plus a render test (two figures; `ChartKind` gains `range`).
- **CR.1:** a CP-4 producer plus a render test (`ChartKind` gains `bullet`).
- **S.4:** remove the xfail on `tests/test_connect_cp2d.py:1179`, make the changes below, and make the `maturity-wall` spec row `chart` with T4.18 bound in `bindings/cp1.py`.

**Wiring problems in the S.4 tripwire** (the brief asked that it be made passable):
- Its assertion `tabs == ["T2E.4"]` cannot pass. A tab label is the binding label, so the T2E.4 tab is labelled "Maturity wall". The oracle uses `["Maturity wall"]` and primary label "Capital structure".
- Its CP-1 fixture (`cp1_module`) lacks the T4.14 fields and the T4.18 `facility_type`, `period_id` and `lease_classification`. `cp1_chart_series` raises `ValueError` on it, so the wiring builder must extend the fixture or give S.4 its own entry point.

**Questions**
1. S.5 draws the four quarters only. FY2025 and LTM Q4 25 have the same value and end date, and the design's FY2023-LTM Q2 2026 axis has no data. Is that acceptable?
2. The pack and inventory name T4.5 for S.5, but T4.5 is the cash-flow statement. I used T4.10 `revenue` and `adjusted_ebitda`.
3. `T4.9.r01.threshold` is a settled text cell "4.00x", not an amount. The oracle reads it as 4.00 with no arithmetic. The alternative amends CP-4, which is a user decision.
4. `ChartSpec` has one `unit_class`, so RV.3 is split into two panels with the same `fig_id` "RV.3". Is that acceptable, or should the panels get distinct ids?
5. The FP-04 primary tab label "Capital structure" is my inference from brief `04:31`.
6. The 4-decimal check for adjusted EBITDA: four quarters of "8" sum to 32 against an FY of 30. Is that display result acceptable?

**Gates:**
- Double fresh-copy rebuild of `build_a.py`: both copies equal each other and the tree for all four files, exit 0.
- `python3 -I cases/pins.py --check`: exit 0 ("matches 80 paths").
- `ruff format --check` and `ruff check` on `build_a.py`: exit 0 each.
- No pytest was run, as no owner oracle moved.

The commit is over 800 changed lines (about 4.4k), almost all generated JSON. The builder is 926 formatted lines.

Not verified: nothing was run against `src/` code, so whether the wiring is feasible is untested, including the `range` and `bullet` chart kinds and the two-panel `ChartSpec`. The CP-1 head's T4.10, T4.14 and T4.18 coordinates are taken from the producer source and `BASES`, not observed on a promoted head (that is Stage 5). Companion label texts for CP-1 are run-time and not pinned. G# numbers are patterns. The design pages and pack were read for form only. Placements (`beside` or `above`) are inference. The oracles have had no mx-precise review yet.
