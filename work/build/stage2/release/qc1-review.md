# Q-C1 oracle review (mx-precise a66dbdc5)

## Q-C1 oracle review (diff 5a6a746..67b8a23, `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2r-qc1`)

**Verdict: REQUEST CHANGES.**

The not-run oracle values are correct and reproducible. Two problems remain. The builder target does not fix the `_Spec` kind, and the kind the preparer validated with (`chart`) crashes every populated FP-04 render. Separately, the populated CP-2D `fp04_render` pin describes a shape that only the Stage 3 wiring can produce.

### Spec verdict (scope and the controller's ruling)
- Every moved value is within scope:
  - `render-expected.json:1956`: CP-MODEL goes from `not_in_pathway` to `unrun`.
  - The `maturity-wall` block pin at :3501-3509.
  - The `responsibility_context_only` text.
  - cp2d `build.py:1056` and `expected.json:2541-2569`.
  - cp4 `build.py:1162` and `expected.json:318`.
  - The three lease amendments.
- These changes are pure sha re-pins, confirmed in the diff: `PINS.json`, cp3c `build.py:30-31` and `manifest.json`, cp4c `build.py:38-39` and `manifest.json`.
- No value comes from the pack's numbers.
- No stub, fake value or catch-all.

### Findings

**High: the builder target is ambiguous, and `kind="chart"` crashes any populated FP-04 render.** (`src/deploy_vii/report_view.py:1653`, `:1583`, `:1280`; the target is in `work/build/stage2/release/qc1-preparer-report.md`, under "Failing tests")
- The preparer checked the pins with `_Spec("MODEL","chart",("CP-1",))`. The failing-test list names owner and producers but not the kind. The brief's "reuses the built S.4" also points toward `chart`.
- `_STRIP_FIGURES` has no `maturity-wall` key, so with CP-2D's T2E.4 shown, `_block` ends in `KeyError('maturity-wall')` either way:
  - CP-1 settled: in `_cp1_strip` at :1653.
  - CP-1 not settled: in `_na_strip` / `_strip_note` (degraded path).
- No test renders a populated FP-04 run (`cp2d_runs.py` / `cp3c_runs.py` do not call `report_view.build`). A `chart` builder would therefore ship this crash with every gate green.
- The not-run pins pass under both kinds, so they cannot catch it.
- Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/qc1-review/probe_chart_kind_keyerror.py`. Exit 1: the CP-1-unrun and the CP-1-restricted paths both raise `KeyError 'maturity-wall'`.
- Fix: the brief must pin `kind="dense"` until the Stage 3 S.4 task adds the `_STRIP_FIGURES` entry and the CP-1 binding.

**Medium: the interim populated render is misleading, and the CP-2D populated pin cannot be reached in the release.** (`cases/cp2d-owner/builder/build.py:1056`, `cases/cp2d-owner/expected.json:2541-2548`; `report_view.py:1786-1838`)
- With `kind="dense"`, a populated FP-04 run (CP-1 restricted, CP-2D positive) renders `maturity-wall` like this:
  - owner MODEL, state populated;
  - CP-2D's T2E.4 rows as the **primary** content, `tab_label` None, `tabs` [];
  - no figures, `full_analysis_route` "CP-1".
- So CP-2D-derived cells sit under a MODEL / "Fig. S.4" attribution, with a route into CP-1. That is misattribution.
- The oracle pins `primary_tab: null, tabs: ["T2E.4"]`, a shape only the Stage 3 S.4 wiring can produce. That goes beyond the controller's ruling (ownership flip and not-run states only).
- No test consumes the pin today (`DELIVERY_SCOPES` / the G2 renderer is not built), so it is latent.
- Fix, either of:
  - (a) mark `fp04_render.blocks["maturity-wall"]` as Stage-3-pending in the cp2d oracle and pin only the owner flip;
  - (b) have the controller rule what the interim block shows (for example, keep T2E.4 as a tab and show the MODEL not-run note as the primary), with a test the builder must write.
- Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/qc1-review/probe_interim_populated.py`. Exit 1: dense gives MODEL, populated, T2E.4 as primary; chart crashes. Its chart branch fails earlier on the test fixture's CP-1 ("Incomplete T4.14 chart identity"); the other probe shows the real KeyError.

**Low: the cp2d note names a route the approved page does not show.** (`cases/cp2d-owner/expected.json:2569`)
- The `maturity_wall_note` says "route Open in Model". The approved page `rbot-fp-04-covenant-refinancing.dc.html:42` shows no route link in the maturity-wall header, while the other blocks do.
- `route_label` is pinned nowhere else, so the builder needs a ruling on it.

### Checks confirmed
- **Check 2.** With `_Spec` owner MODEL and producers `("CP-1",)`, plus CP-MODEL right after CP-1 in the preset, `tests/test_legal_render.py` passes 76 of 76 for both `chart` and `dense`. Unpatched `src` fails exactly `[0]` and `[1]`. Kind `dense` comes from the spec kind or the chart→dense fallback at :1858; `not_run` and "Not run: CP-1 has not run." come from the unrun fixture; route is null on the honest-state path. Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/qc1-review/probe_notrun_pin.py <chart|dense>` (76 passed each).
- **Check 3.** Keeping T2E.4 bound is consistent:
  - `validate_bindings` (`bindings/__init__.py:111`) reports any shown fact without a binding.
  - A single block placement is not a double binding.
  - It matches the CP-2D lease's "stays as it is" and `test_bindings_follow_the_lease`.
- **Check 5.**
  - `python3 -I cases/pins.py --check` exits 0 (75 paths).
  - Two `fresh_copy.py` + `chain.sh` rebuilds: both exit 0, `diff -r` between them is 0, and both equal the committed `cases/`.
- **Sources.** Page :42 says "MODEL · Fig. S.4". Pack brief :31 says "Maturity wall and capital structure (Model)".

### Builder targets (confirmed, once the High is resolved)
1. `src/deploy_vii/report_view.py:1171-1173`: `_Spec("Maturity wall", "MODEL", "dense", ("CP-1",), ...)`. Use kind `dense`, not `chart`; `route_label` needs a ruling (Low).
2. `src/deploy_vii/contracts.py:53`: insert `"CP-MODEL"` right after `"CP-1"` in `covenant_refinancing`.
3. Turn green `tests/test_legal_render.py::test_core_html_full_fact_fields_sources_passports_and_honest_states[0]` and `[1]`.
4. Update `tests/test_connect_cp2d.py:1150-1164` (`test_spec_rows_serve_the_three_blocks`) for the MODEL row.
5. Re-pin `tests/cp2d_runs.py:27` and the `expected.json` entry to `f8b6f607…` / `969f3013…`.
6. Re-pin `tests/cp3c_runs.py:35` and the `manifest.json` entry to `42b1685a…` / `45dacc7b…`.
7. Plus the interim-render test from the Medium, once the controller rules on it.

Not verified: the populated MODEL S.4 render (Stage 3); the real `cp1_chart_series` output for a full CP-1 under a MODEL `maturity-wall` (the probe stubs it); `tests/test_connect_cp2d.py`, `test_connect_cp3c.py`, `test_method_cp4.py`, `test_connect_cp4.py` and the full suite (not re-run); the `cp2d_runs.py` / `cp3c_runs.py` re-pin hashes (not run); the ruff format baseline of the builders.

---

## Q-C1 oracle review (diff 5a6a746..67b8a23, `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s2r-qc1`)

**Verdict: REQUEST CHANGES.**

The not-run oracle values are correct and reproducible. Two problems remain. The builder target does not fix the `_Spec` kind, and the kind the preparer validated with (`chart`) crashes every populated FP-04 render. Separately, the populated CP-2D `fp04_render` pin describes a shape that only the Stage 3 wiring can produce.

### Spec verdict (scope and the controller's ruling)
- Every moved value is within scope:
  - `render-expected.json:1956`: CP-MODEL goes from `not_in_pathway` to `unrun`.
  - The `maturity-wall` block pin at :3501-3509.
  - The `responsibility_context_only` text.
  - cp2d `build.py:1056` and `expected.json:2541-2569`.
  - cp4 `build.py:1162` and `expected.json:318`.
  - The three lease amendments.
- These changes are pure sha re-pins, confirmed in the diff: `PINS.json`, cp3c `build.py:30-31` and `manifest.json`, cp4c `build.py:38-39` and `manifest.json`.
- No value comes from the pack's numbers.
- No stub, fake value or catch-all.

### Findings

**High: the builder target is ambiguous, and `kind="chart"` crashes any populated FP-04 render.** (`src/deploy_vii/report_view.py:1653`, `:1583`, `:1280`; the target is in `work/build/stage2/release/qc1-preparer-report.md`, under "Failing tests")
- The preparer checked the pins with `_Spec("MODEL","chart",("CP-1",))`. The failing-test list names owner and producers but not the kind. The brief's "reuses the built S.4" also points toward `chart`.
- `_STRIP_FIGURES` has no `maturity-wall` key, so with CP-2D's T2E.4 shown, `_block` ends in `KeyError('maturity-wall')` either way:
  - CP-1 settled: in `_cp1_strip` at :1653.
  - CP-1 not settled: in `_na_strip` / `_strip_note` (degraded path).
- No test renders a populated FP-04 run (`cp2d_runs.py` / `cp3c_runs.py` do not call `report_view.build`). A `chart` builder would therefore ship this crash with every gate green.
- The not-run pins pass under both kinds, so they cannot catch it.
- Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/qc1-review/probe_chart_kind_keyerror.py`. Exit 1: the CP-1-unrun and the CP-1-restricted paths both raise `KeyError 'maturity-wall'`.
- Fix: the brief must pin `kind="dense"` until the Stage 3 S.4 task adds the `_STRIP_FIGURES` entry and the CP-1 binding.

**Medium: the interim populated render is misleading, and the CP-2D populated pin cannot be reached in the release.** (`cases/cp2d-owner/builder/build.py:1056`, `cases/cp2d-owner/expected.json:2541-2548`; `report_view.py:1786-1838`)
- With `kind="dense"`, a populated FP-04 run (CP-1 restricted, CP-2D positive) renders `maturity-wall` like this:
  - owner MODEL, state populated;
  - CP-2D's T2E.4 rows as the **primary** content, `tab_label` None, `tabs` [];
  - no figures, `full_analysis_route` "CP-1".
- So CP-2D-derived cells sit under a MODEL / "Fig. S.4" attribution, with a route into CP-1. That is misattribution.
- The oracle pins `primary_tab: null, tabs: ["T2E.4"]`, a shape only the Stage 3 S.4 wiring can produce. That goes beyond the controller's ruling (ownership flip and not-run states only).
- No test consumes the pin today (`DELIVERY_SCOPES` / the G2 renderer is not built), so it is latent.
- Fix, either of:
  - (a) mark `fp04_render.blocks["maturity-wall"]` as Stage-3-pending in the cp2d oracle and pin only the owner flip;
  - (b) have the controller rule what the interim block shows (for example, keep T2E.4 as a tab and show the MODEL not-run note as the primary), with a test the builder must write.
- Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/qc1-review/probe_interim_populated.py`. Exit 1: dense gives MODEL, populated, T2E.4 as primary; chart crashes. Its chart branch fails earlier on the test fixture's CP-1 ("Incomplete T4.14 chart identity"); the other probe shows the real KeyError.

**Low: the cp2d note names a route the approved page does not show.** (`cases/cp2d-owner/expected.json:2569`)
- The `maturity_wall_note` says "route Open in Model". The approved page `rbot-fp-04-covenant-refinancing.dc.html:42` shows no route link in the maturity-wall header, while the other blocks do.
- `route_label` is pinned nowhere else, so the builder needs a ruling on it.

### Checks confirmed
- **Check 2.** With `_Spec` owner MODEL and producers `("CP-1",)`, plus CP-MODEL right after CP-1 in the preset, `tests/test_legal_render.py` passes 76 of 76 for both `chart` and `dense`. Unpatched `src` fails exactly `[0]` and `[1]`. Kind `dense` comes from the spec kind or the chart→dense fallback at :1858; `not_run` and "Not run: CP-1 has not run." come from the unrun fixture; route is null on the honest-state path. Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/qc1-review/probe_notrun_pin.py <chart|dense>` (76 passed each).
- **Check 3.** Keeping T2E.4 bound is consistent:
  - `validate_bindings` (`bindings/__init__.py:111`) reports any shown fact without a binding.
  - A single block placement is not a double binding.
  - It matches the CP-2D lease's "stays as it is" and `test_bindings_follow_the_lease`.
- **Check 5.**
  - `python3 -I cases/pins.py --check` exits 0 (75 paths).
  - Two `fresh_copy.py` + `chain.sh` rebuilds: both exit 0, `diff -r` between them is 0, and both equal the committed `cases/`.
- **Sources.** Page :42 says "MODEL · Fig. S.4". Pack brief :31 says "Maturity wall and capital structure (Model)".

### Builder targets (confirmed, once the High is resolved)
1. `src/deploy_vii/report_view.py:1171-1173`: `_Spec("Maturity wall", "MODEL", "dense", ("CP-1",), ...)`. Use kind `dense`, not `chart`; `route_label` needs a ruling (Low).
2. `src/deploy_vii/contracts.py:53`: insert `"CP-MODEL"` right after `"CP-1"` in `covenant_refinancing`.
3. Turn green `tests/test_legal_render.py::test_core_html_full_fact_fields_sources_passports_and_honest_states[0]` and `[1]`.
4. Update `tests/test_connect_cp2d.py:1150-1164` (`test_spec_rows_serve_the_three_blocks`) for the MODEL row.
5. Re-pin `tests/cp2d_runs.py:27` and the `expected.json` entry to `f8b6f607…` / `969f3013…`.
6. Re-pin `tests/cp3c_runs.py:35` and the `manifest.json` entry to `42b1685a…` / `45dacc7b…`.
7. Plus the interim-render test from the Medium, once the controller rules on it.

Not verified: the populated MODEL S.4 render (Stage 3); the real `cp1_chart_series` output for a full CP-1 under a MODEL `maturity-wall` (the probe stubs it); `tests/test_connect_cp2d.py`, `test_connect_cp3c.py`, `test_method_cp4.py`, `test_connect_cp4.py` and the full suite (not re-run); the `cp2d_runs.py` / `cp3c_runs.py` re-pin hashes (not run); the ruff format baseline of the builders.

---

## Q-C1 scoped re-review (`git diff 67b8a23..300fcdb`, s2r-qc1, tip 300fcdb, tree clean)

**Verdict: APPROVE.** All three findings are fixed and nothing new turned up.

- **High (kind): fixed in the brief.** Ruling 1 in `work/build/stage2/release/qc1-brief.md` ("Rulings after the mx-precise review") sets the target to `_Spec("Maturity wall", "MODEL", "dense", ("CP-1",), route_label=None)`. It forbids `chart` until Stage 3 S.4 lands. My earlier probe already showed the not-run pins hold with `dense` (`probe_notrun_pin.py dense`, 76 passed), so that result still applies.
- **Medium (populated pin): fixed.**
  - `cases/cp2d-owner/builder/build.py:1056` and `expected.json`: `fp04_render.blocks["maturity-wall"]` is now only `{owner: MODEL, stage3_pending: <note naming the Stage 3 S.4 task>}`. The unreachable `primary_tab`/`tabs`/`state` keys are gone.
  - No test reads the cp2d `fp04_render` block keys. The cp3c test at `test_connect_cp3c.py:1412` reads cp3c's own oracle. So dropping the keys breaks nothing.
  - Ruling 2 specifies the strict-xfail tripwire: on a populated FP-04 run, MODEL content comes first and T2E.4 is a non-primary tab, with reason "Stage 3 S.4 wiring".
  - The CP-2D lease amendment (`docs/CP2D-OWNER-LEASE.md:5`) now says the populated shape is Stage-3-pending. It names the new hashes `c60797a2…` and `6c707b4b…`, each found once.
- **Low (route): fixed.** "route Open in Model" is gone from `maturity_wall_note`. The note now states `route_label` is None and cites the approved page.
- **Re-pins are pure.** `PINS.json`, cp3c `build.py` and `manifest.json`, and cp4c `build.py` and `manifest.json` move only sha256 values.
- **Gates (re-run):**
  - `python3 -I cases/pins.py --check` exits 0 (75 paths).
  - Two fresh copies through `chain.sh` both exit 0.
  - The two rebuilt copies are byte-identical (`diff -r` exit 0), and both equal the committed `cases/` tree (exit 0).

## Final builder targets
1. `src/deploy_vii/report_view.py:1171-1173`: `_Spec("Maturity wall", "MODEL", "dense", ("CP-1",), route_label=None)`.
2. `src/deploy_vii/contracts.py:53`: put `"CP-MODEL"` right after `"CP-1"` in `covenant_refinancing`.
3. Turn green `tests/test_legal_render.py::test_core_html_full_fact_fields_sources_passports_and_honest_states[0]` and `[1]`.
4. Update `tests/test_connect_cp2d.py:1150-1164` (`test_spec_rows_serve_the_three_blocks`) so `maturity-wall` expects MODEL, dense, `("CP-1",)`, route_label None.
5. Re-pin `tests/cp2d_runs.py`: `builder/build.py` to `6c707b4bdc3b59629e8590f6e32760293aacfd9bccb5b337fc52e715f12a8e4c`, `expected.json` to `c60797a22c9700fb3ded9cb5de58d64349bf6672a445a6cbbc9c595bc3a124dc`.
6. Re-pin `tests/cp3c_runs.py`: `builder/build.py` to `72e41ad0c241272de234b13453f23ff39788ec877a5e8a772bde89f88610dcad`, `manifest.json` to `5cbe3f687eb853e7c84f3483cb5e5a6b2683361fe1c84a1b3e05a40285c10767`. The preparer's earlier `42b1685a…`/`45dacc7b…` values are superseded.
7. Add the strict-xfail tripwire from ruling 2.

Not verified: the tripwire test and the `cp2d_runs.py`/`cp3c_runs.py` re-pins, because they don't exist yet. I re-ran only the gates above in this round. The test files were not re-run against 300fcdb; the one cases file they read (`render-expected.json`) did not change in this diff.
