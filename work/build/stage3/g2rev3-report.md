# G2 rev 3 preparer report (mx-feature a69493a7, claude/s3-g2rev3 4a9649f)

G2 rev 3 is written and committed. I only appended the new section to `docs/OWNER-RENDERING-LEASE.md` (65 lines added), as one commit. Nothing was run through G2.

- **Worktree:** `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a69493a77a57f921f`
- **Branch:** `claude/s3-g2rev3`, cut from `b6730b7`
- **Tip:** `4a9649f`

**`cp1-model` sections, in pathway order:** `model-chart-strip`, `capital-structure`, `financials-credit-metrics`.
- **Where they come from:** the CP-1/CP-MODEL run is `slice-cp1-model-positive`. `tests/test_financial_render.py:127-128` asserts CP-1 and CP-MODEL both read "With limitations" (gap: "Not run", `:108-122`). The page comes from `core_render.render` (`financial_rendering.py:158`).
- **CP-1 bindings:** `bindings/cp1.py:42-58` binds those three blocks. They are the only credit_snapshot blocks whose producers are `("CP-1",)` alone (`report_view.py:1098-1108`).
- **CP-MODEL:** it binds the Evidence rail only (`bindings/cp_model.py:5-20`), so it adds no section.
- **`model-chart-strip` is a section.** The builder left it out only because rev 1 L1 forced `figures == ()`. The strip is bound (`bindings/cp1.py:52`) and drawn for a restricted CP-1 (`report_view.py:1645-1660`). Its payload is asserted at `tests/test_cp1_chart_render.py:405-410` and `:439-441`.

**Figure rule (replaces rev 1 L1).** An assigned block's `figures` equal the frozen chart oracle's render expectation for that block, pathway and case. Otherwise they are `()`, and a refused outcome keeps `()`. Comparison is field by field against the oracle's literals, never recomputed. A mark's fact ids are resolved at run time from the oracle's coordinates. Gap marks are `∅ G#`. A missing or extra figure fails.

**Rows with a chart expectation.** In the oracle paths below, `E` is `cases/charts/` at `731059f`.

| row | block | figures | oracle path and pointer |
|---|---|---|---|
| `cp1-model` | `model-chart-strip` | S.1-S.4 | `E/expected.json` `#/chart_series`, `#/quarters`, `#/current_maturity_wall` |
| `cp1-model` | `financials-credit-metrics` | S.5 | `E/s5-expected.json` `#/render`, `#/chart_series/0` |
| `cp1c-fp03-peers` | `peer-positioning` | RV.3a, RV.3b | `E/rv3-expected.json` `#/cases/<c>/chart_series` for positive and gap; `no_peers` and `refused` give `()` |
| `cp4-fp04-covenants` | `covenant-tests-headroom` | CR.1 | `E/cr1-expected.json` `#/cases/<c>/chart_series`; `gap_false_same_definition` uses the gap chart |
| `cp2d-fp04-liquidity` | `liquidity-runway` | CR.2 | `E/cr2-expected.json` `#/chart_series/CR.2/<c>` for positive, `long_horizon`, `gap_minimum_cash` |
| `cp2d-fp04-liquidity` | `funding-gap` | `()` | no CP-3C in the run (`cr3` adversarial `cp3c_not_in_the_run`) |
| `cp3c-fp04-refinancing` | `funding-gap` | CR.3 | `E/cr3-expected.json` `#/chart_series/CR.3/<c>` for positive, `gap_minimum_cash`, `gap_no_repricing` |
| `cp4c-fp05-recovery` | `recovery-by-class` | DR.2 | `E/dr2-expected.json` `#/chart_series/DR.2/<c>` for positive and gap |
| `cp4c-fp05-recovery` | `value-allocation-claims` | DR.3, DR.4, DR.5 | `E/dr345-expected.json` `#/chart_series/DR.3-5/<c>/DR.n` for positive and gap |
| `cp2h-fp05-ratings` | `rating-triggers` | DR.6 (n/a frame) | `E/dr6-expected.json` `#/chart_series/DR.6`, `#/render/distressed_restructuring/frame_texts/per_case/<c>` |

- **S.5 is `cp1-model` only.** It is the only credit_snapshot row that assigns `financials-credit-metrics`.
- **No row uses these:** S.4 on FP-04 (`maturity-wall`), CR.2 on distressed, and `fixture_*` oracle entries.
- **All other assigned blocks:** `figures == ()`, asserted.
- **Acceptance:** the section adds four acceptance items, including a perturbation negative.

**Questions:** none that block the freeze.
- **Check one thing in the review:** `cases/charts/expected.json` is the CP-1 S.1-S.4 oracle and predates Stage 3. I used it for the strip because `s5` says S.1-S.4 stay unchanged.
- **Skipped on purpose:** I did not add a `cp1-model` case for S.4's `current_maturity_wall`, and the section's `Not verified:` line notes that.

Not verified: no `report_view.build` or G2 output was compared to any oracle pointer, and the pointers were read as JSON keys only. I did not confirm that `build` already emits S.5, RV.3, CR.1-3 or DR.2-6; that is the wiring builders' work. The claim that a restricted CP-1 run populates `model-chart-strip` rests on `tests/test_cp1_chart_render.py`, which uses a typed-seam fixture rather than a genuine G1 run. The S.1-S.4 pointers in `expected.json` were not matched to marks. This is a docs-only change, so no test applies.
