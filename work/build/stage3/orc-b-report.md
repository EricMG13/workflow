# Chart oracle preparer B report (mx-feature a1775e03, claude/s3-orc-b 5735b06)

Group B oracles are written and committed on `claude/s3-orc-b`, tip `5735b06` (`f71a105` before it). Builds are byte-identical from two fresh copies, but a Q-C2 decision is open (see Questions). No pytest was run on the new oracles. The CP-3C tests I ran have 4 expected reds.

**Files** (worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s3-orc-b`)
- `cases/charts/builder/build_b.py`. It is stdlib only, reads the four module oracles (`cp2d`, `cp3c`, `cp4c`, `cp2h`), and writes the five JSON files.
- `cases/charts/{cr2,cr3,dr2,dr345,dr6}-expected.json`.
- `docs/CP3C-OWNER-LEASE.md` has a new amendment header.
- `cases/cp3c-owner/builder/build.py` and its `expected.json` were rebuilt through the builder.
- I did not touch `cases/pins.py` or `cases/PINS.json`.

**Per figure** (points / gap marks; design lines; brief lines)
- **CR.2:** 5 points and 0 gaps in each of `positive`, `long_horizon` and `gap_minimum_cash`.
  - The bridge steps are `T2E.2.r01` and `T2E.3.r05` to `r08`; the bridge identity is asserted in the builder.
  - Design: fp04 :38-40, fp05 :45-47. Brief: 04:29, 05:30.
  - The distressed instance is a render-equality block.
- **CR.3:** positive 2 / 0; `gap_minimum_cash` 2 / 1; `fixture_two_facilities` 4 / 0, `fixture_burn` 2 / 0 (both with negative resources); `fixture_amortisation_missing` 2 / 2, drawn as the n/a frame.
  - Design: fp04 :43-44. Brief: 04:33.
- **DR.2:** positive 9 / 0; gap 12 / 10; plus 3 fixtures.
  - Equity rows drop out. Series are Base 4.00x, Downside 3.00x, Stress 2.00x.
  - Design: fp05 :37-38, :71-72. Brief: 05:26.
- **DR.3-5:** three waterfalls per case, 5 points each (6 in `gap`). In `positive` each figure has 0 gaps, and in `gap` each has 4 or 6.
  - The `gap` case DR.5 is the n/a frame, because EV is missing.
  - Design: fp05 :40-41. Brief: 05:26.
- **DR.6:** n/a frame with 0 marks.
  - T2R.4/T2R.5 facts that must not be marks: 75 in `positive`, 45 in `gap`; the `gap` case has 12 missing facts.
  - Design: fp05 :54-56, :112; `charts.js` :166. Brief: 05:36.

**Moved values in another oracle** (Q-C2 only)
- In `cases/cp3c-owner/expected.json`, `fp04_render.blocks.refinancing-paths.tabs` changes from `[T3D.1,T3D.2,T3D.3]` to `[T3D.2,T3D.3]`, and the `other_FP04_blocks` prose is reworded.
- `expected.json` sha256 `168e3bee…` → `c5089cff…`; `build.py` `6353168e…` → `e62f8e88…`. `manifest.json` and `submissions.json` are unchanged.
- The controller needs to re-pin `PINS.json` and the literal pins in `tests/cp3c_runs.py` and `tests/test_method_cp3c.py`.

**Builder targets**
- Each oracle carries `builder_targets`: new files `tests/test_chart_series_<fig>.py` and `tests/test_chart_render_<fig>.py`.
- Series tests call a producer such as `cp2d_chart_series(module)`, `cp3c_chart_series`, or `cp4c_chart_series`, and assert that points equal the oracle.
- Render tests use `report_view.build(...).blocks[...].figures` and check marks, table twin, and tabs.
- DR.6 has a render test only.

**Questions for the controller**
1. **Q-C2 binding:** a second binding of T3D.1 to `funding-gap` is rejected. `validate_bindings` (`bindings/__init__.py:113`) flags a fact bound to two blocks of one Pathway, and FP04 composes both. I amended the lease as a move instead, with `funding-gap` producers gaining CP-3C. The alternative is to keep T3D.1 in `refinancing-paths` and have the figure read the CP-3C head without a binding.
2. **Distressed preset:** `contracts._PRESETS["distressed_restructuring"]` has no CP-2D (or CP-3C), so item 8 renders only if the run requests CP-2D explicitly. Adding it to the preset would move pins.
3. **CR.2 placement:** the FP04 page shows the chart beside a short table and FP05 shows it above, but the `_Spec` is shared. I pinned "above".
4. **DR.3-5 step order:** I build up to EV (classes, equity residual, EV total) so marks keep the settled non-negative texts. The brief's order, EV first then deductions, would need negated marks.
5. **DR.6:** the design reason "no agency report in the Source Pack" is false for the `positive` case, which has a synthetic agency source. The frame cites a G#, but no fact supplies it. I pinned the approved-page text.
6. **Inferences, each flagged in its oracle:**
   - CR.3 categories are facility rows, not the design's year buckets, and fixture texts use the display rule (0 dp half-up, negatives in brackets).
   - DR.2 bars are hatched because every multiple is `analyst_judgment`.
   - Companion fact ids for CR.2 are my choice.
7. **CP-4C prose:** the prose in `cases/cp4c-owner` `d7_rendering.decision` still says "no chart". I did not edit it.

**Gates**
- Double fresh-copy rebuild of `build_b.py`: both runs exit 0 and all five files are identical to each other and to the tree.
- Same check for the `cp3c-owner` builder (`expected.json`, `manifest.json`, `submissions.json`): identical.
- `ruff format --check` and `ruff check` on `build_b.py`: exit 0.
- `cases/cp3c-owner/builder/build.py` already failed `ruff format --check` and had 10 `ruff check` errors at HEAD. I left it unformatted so its pins don't move.
- `tests/test_method_cp3c.py` and `tests/test_connect_cp3c.py`: 463 passed, 4 failed, all expected.
  - `test_oracle_files_match_the_lease_pins`, `test_driver_reads_the_pinned_oracle_and_binds_every_literal_from_the_view`, and `test_driver_cp0_text_appends_both_consumer_deltas_in_order` fail on the stale hash pins.
  - `test_bindings_follow_the_lease` fails because it still expects T3D.1 in `refinancing-paths`; that is the wiring target.

Not verified: no producer or renderer code exists, so no oracle value was compared with product output. `display.py` spelling was not run (fixture-derived texts follow the stated rule). The G# numbering, the layout, and hatching were not exercised. Gap, n/a, and "missing bridge operand" cases for CR.2 and DR.6 have no executed test. The DR.6 G# source and the `T3D.1` move were not checked in the product (no `validate_bindings` run). Other CP-4C/CP-2D/CP-2H tests, and `PINS.json` with the re-pins, were not run (the controller regenerates them). No reviewer has read these oracles yet.

## Rulings 6.3, 6.5, 6.7 applied (0448be2)

All three rulings are applied through the builders and committed as one commit, tip `0448be2`. Both CP-4C test modules fail to collect (2 errors, the expected reds); nothing else was run.

**Moves**
- **6.7:** I changed the `d7_rendering.decision` text in `cases/cp4c-owner/expected.json` through `cases/cp4c-owner/builder/build.py`.
  - The old ending "; no chart" is now "; Stage 3 adds Fig. DR.2 to recovery-by-class and Figs. DR.3-5 to value-allocation-claims, drawn above the tabs (cases/charts/dr2-expected.json, dr345-expected.json)".
  - `expected.json` sha256 `66edecbb…` → `eb1a897bfbba83298171d82fb399d653d376d2597fecf99b71cfcbc38cd96ab6`.
  - `build.py` sha256 `e7628d4d…` → `45e3620f579d6165d2145a1806d2d22e4f596680175a6aa2bd5a3f6d36145dfd`.
  - `manifest.json` and `submissions.json` are unchanged.
- **6.5 (DR.6):** each case now has its own `frame_reason`, `g_ref_rule`, `cited_gap_fact_ids` and `departs_from_approved_page`.
  - `positive`: "agency source is synthetic; a headroom chart waits for a real agency report". It cites no G#, because no gap fact exists in that case.
  - `gap`: "a trigger threshold is not stated in the synthetic agency source; a headroom chart waits for a real agency report". It cites the 12 missing T2R.4/T2R.5 facts, with the G# bound at run time.
  - Departures from the approved page text: the reason text and the G31 reference. The title, the "n/a" form, the dashed frame and the "Not computable" chip are kept.
- **6.3:** the `scope_limits` in `cr2-expected.json` now records FP-04's "beside" layout as a Low design deviation.
- `dr2-expected.json` and `dr345-expected.json` changed only because they embed the new CP-4C `expected.json` sha256.

**Exit codes**
- Double fresh-copy rebuild of the `cp4c-owner` builder and `build_b.py`: both runs exit 0, and every output (`cp4c-owner` expected, manifest and submissions, plus the five chart oracles) is byte-identical across the two copies and to the tree.
- `ruff format --check` and `ruff check` on `build_b.py`: exit 0.
- `tests/test_method_cp4c.py` and `tests/test_connect_cp4c.py`: 2 collection errors, because both assert the `expected.json` sha256 literal. The wiring builder re-pins those literals. No test ran past collection.

Not verified: the product tests of CP-4C past collection; the renderer text for DR.6 (no code exists); `PINS.json` (the controller regenerates it).
