# G2 rev 3 review (mx-precise a6a7d04d, 4a9649f)

**G2 lease rev 3 (`4a9649f`) review: REVISE.** One Medium finding blocks: the comparison rule asks for mark fields that the S.1-S.4 strip oracle does not hold. Line refs are to the rev 3 section of `docs/OWNER-RENDERING-LEASE.md` in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a69493a77a57f921f`.

**What checks out**
1. **`cp1-model` sections (R3.1).** The three blocks are the only credit_snapshot `_Spec` rows whose producers are `("CP-1",)` alone (`report_view.py:1098-1108`). Each is bound by `bindings/cp1.py:42-58`. There is no financial render oracle with blocks: `cases/financial` has only `manifest.json`, and `test_financial_render.py` asserts module statuses only. So deriving the sections from the bindings is the right method.
2. **Every R3.2 pointer resolves in the `731059f` oracles.** `probe_rev3_pointers.py` exits 0 over 49 pointers and 2 adversarial ids.
   - Block id, pathway and placement match each oracle: S.5 beside on credit_snapshot; RV.3a/b above; CR.1 beside; CR.2 above; CR.3 beside; DR.2 above; DR.3-5 in order; DR.6 n/a frame.
   - `cr1` `gap_false_same_definition` reads "identical to cases.gap.chart_series", as rev 3 says.
   - `s5#/render/earnings_update` has `figures: []`, so S.5 is drawn only on credit_snapshot.
   - S.4 on FP-04 and CR.2 on distressed apply to no row, which is right.
   - No row is missing a chart and none has an extra one.
3. **Comparison.** For the Stage 3 oracles the test can read each mark's `shown`, `fact_id`/coordinates, `amount_exact`/`value` and `state` from the oracle, so nothing is recomputed and no stub is needed.

**Findings**

**M1 (Medium): the comparison rule cannot be met for S.1-S.4 without deriving values.** R3.2 table row `cp1-model`/`model-chart-strip`, and the "Comparison" paragraph.
- `cases/charts/expected.json` predates Stage 3. It pins only titles, units, series names, per-quarter raw amounts (`quarters[*]`, e.g. `"cash_millions": "16.25"`, ratios `{"amount": null, "state": "unavailable"}`) and the maturity-wall rows.
- It has no mark `text`/`shown`, no fact coordinates, no refs and no table twin.
- Failure scenario: to meet "text … equal the oracle" and "twin cells equal the oracle's twin", the builder would have to spell marks from raw amounts. That is the derivation R3.2 forbids. Otherwise the builder quietly asserts less than the rule requires.
- Fix: list the S.1-S.4 fields separately and state what is left unpinned.
  - From the oracle: fig_id order S.1-S.4; title; unit and currency; series names in order; one category per quarter; each value equal to the oracle amount, or null with a `∅ G#` ref where the state is unavailable; S.4 marks equal to the `current_maturity_wall` rows.
  - Mark text and twin: assert only that the twin cells equal the mark texts (`test_cp1_chart_render.py:405-410`). Record under Not verified that they are not checked against an oracle.

**L1 (Low): ref and fact-id wording does not match the oracles.**
- The rule compares "report reference" from the oracle, but no oracle pins refs; they are assigned at run time. Fix: require that refs exist and agree with the SVG's `data-ref`.
- The fact-id lookup names `fact_coordinate`/`companion_coordinates`/`fact_id_rule`, but `rv3`, `cr1`, `cr2` and `dr2` pin `fact_id`/`companion_fact_ids`. Fix: add those two keys to the rule.

**L2 (Low): the build base is not named.** No chart producer exists in `src/` at `731059f` or at `b6730b7`. The wiring is on `claude/s3-int` (`f048dca`), where S.5, RV.3, CR.1-3 and DR.2-6 are present. Fix: state that G2 builds on the integrated wiring tip, so the figure assertions are not met by `figures == ()` stand-ins.

**Probe:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/g2scope-review/probe_rev3_pointers.py` exits 0. It reads oracle copies I extracted from `731059f` into the `charts731/` folder next to it.

Not verified: nothing was rendered, and I did not compare `build` output on `s3-int` to the oracles. I did not run the `cp1-model` positive run, so I have not seen that `capital-structure` gets non-empty bound facts (T4.17 has 0 facts per the Q-C9 note; it rests on T4.18 and `pro-forma`). I did not check that S.5 renders for a `("CP-1","CP-MODEL")` run on `s3-int`.
