# Stage 3 chart questions

Source: `work/build/stage3/charts-inventory.md` (read it for the full rows, design line numbers and the exact titles). Pattern: `docs/CP1-CHART-SLICE.md`.

For every "in Stage 3" figure the pattern needs, in this order (`CP1-CHART-SLICE.md:131-139`): a literal source-first oracle frozen before code; a reviewed typed producer API per module (`CP1-CHART-SLICE.md:66`: immutable records `fig_id`, `title`, `kind`, `unit_class`, `unit`, `series`, `points`, `reason`, points carrying `fact_id` and companion fact ids from the same settled module view); a renderer seam in `report_view.py`; exact table twins; missing or `not_meaningful` facts shown as gaps with their G# reference, never as 0.

## Chart oracles to freeze (one batch, following docs/CP1-CHART-SLICE.md)

Suggested layout for the batch: one contract `docs/STAGE3-CHART-SLICE.md`, and one literal oracle file per figure group under `cases/charts/`, each with the `cases/charts/expected.json` shape (`source_authority`, `chart_series`, `adversarial_cases`, `scope_limits`). Every oracle is calculated from the module's frozen `cases/<cp>-owner/expected.json` before candidate code. No chart may recompute a value; marks carry the settled fact.

1. **S.5 "Net revenues and Adjusted EBITDA"**
   - Module: CP-1 (CP-MODEL publishes).
   - Block: `financials-credit-metrics` (credit_snapshot).
   - Series facts: revenue and adjusted EBITDA by period from CP-1 T4.5 and T4.10 (values in `cases/financial/manifest.json:128-133,176-186,1948-1953`). The oracle freeze must read the T4.5/T4.10 row ids from a promoted CP-1 head; I did not list them.
   - Oracle file: `cases/charts/s5-expected.json`, built beside `cases/charts/expected.json` and reusing its `source_authority`. Extends `cp1_chart_series` or adds a second producer function; Modules decides at the freeze.

2. **RV.3 "Peer positioning"**
   - Module: CP-1C.
   - Block: `peer-positioning` (relative_value).
   - Series facts: `T1C.3.issuer.*` and `T1C.3.pNN.*` for `adjusted_ebitda_margin`, `total_leverage_adjusted`, `interest_coverage_adjusted`, `ffo_to_debt`; `T1C.4.<metric>.median`; `T1C.1.pNN.included` (p05 excluded, so no range contribution); `T1C.5.pNN.<metric>_flag` for outlier marking.
   - Oracle file: `cases/charts/rv3-expected.json` (positive case; the `gap` case from `cases/cp1c-owner/expected.json` for the gap path).

3. **CR.1 "Covenant tests and headroom"**
   - Module: CP-4.
   - Blocks: `covenant-tests-headroom` (covenant_refinancing). The same series feeds FP-05 "Covenant levers" only after that block is assigned (deferred, below).
   - Series facts: `T4.9.rNN.threshold`, `.comparison`, `.current`, `.headroom` (`T4.9.r01`: 4.00x, "Not more than", 1, 3.00).
   - Oracle file: `cases/charts/cr1-expected.json` (positive; `gap` where `T4.9.r01.headroom` is `missing`; `gap_false_same_definition`).

4. **CR.2 "Liquidity runway"**
   - Module: CP-2D.
   - Blocks: `liquidity-runway` (covenant_refinancing and distressed_restructuring; one `_Spec`, `report_view.py:1166-1169`).
   - Series facts: `T2E.2.r01` cash; `T2E.3.r05` flow over horizon; `T2E.3.r06` amortisation; `T2E.3.r07` maturities; `T2E.3.r08` cash at horizon end. Cases `positive` (all flows 0) and `long_horizon` (maturities 50, cash at horizon end negative), `cases/cp2d-owner/expected.json`.
   - Oracle file: `cases/charts/cr2-expected.json`. The oracle must pin the bridge arithmetic from the settled ids only (closing = opening + flow - amortisation - maturities).

5. **S.4 "Maturity wall" (FP-04)**
   - Module: CP-2D (Q-C1 ruled, user, 2026-10-29).
   - Block: `maturity-wall`.
   - Series facts: `T2E.4.rNN.c1` principal, `T2E.4.rNN.c2` maturity date, `.c4` inside horizon. One mark per facility, no aggregation (Q-C1 ruled).
   - Oracle file: `cases/charts/s4-fp04-expected.json`.

6. **CR.3 "Funding gap" (FP-04)**
   - Module: CP-3C, drawn in block `funding-gap`, with a T3D.1 read added to the CP-3C binding (Q-C2 ruled, user, 2026-10-29).
   - Series facts: `T3D.1.rNN.c6` principal payable at maturity and `T3D.1.rNN.c7` resources at maturity (positive `T3D.1.r01`: 50 and 10), `T3D.1.rNN.c2` date. Negative resources are possible and must plot below zero (design: "Columns with negatives").
   - Oracle file: `cases/charts/cr3-expected.json`.

7. **DR.2 "Recovery by class"**
   - Module: CP-4C.
   - Block: `recovery-by-class` (distressed_restructuring).
   - Series facts: `T4E.5.v0Nc0M.recovery` (Base, Downside, Stress by class), `T4E.3.v0N.multiple` (hatching input). Equity rows are `not_meaningful` and drop out.
   - Oracle file: `cases/charts/dr2-expected.json`.

8. **DR.3-5 "Value allocation"**
   - Module: CP-4C.
   - Block: `value-allocation-claims`.
   - Series facts: `T4E.3.v0N.ev`, `T4E.4.v0Nc0M.distribution`, `T4E.9.v0N.equity_residual` (`T4E.9.v0N.total_claims`, `.creditor_distributions` as checks), one waterfall per scenario.
   - Oracle file: `cases/charts/dr345-expected.json`.

9. **CR.2 "Liquidity runway" (FP-05 instance)**
   - Module: CP-2D.
   - Block: `liquidity-runway`.
   - Series facts and oracle: item 4. No new oracle; the wiring task only asserts the distressed pathway renders the same figure.

10. **DR.6 "Rating triggers" (n/a frame, Q-C11)**
    - Module: CP-2H.
    - Block: `rating-triggers` (distressed_restructuring).
    - Series facts: none drawn. The frame is the design's own n/a state (G31); the oracle pins the frame text and the `gap` shape of `cases/cp2h-owner/expected.json`. No `T2R.4`/`T2R.5` mark is drawn.
    - Oracle file: `cases/charts/dr6-expected.json`.

Not in this batch (ruled): EU.3 stays deferred (Q-C9), RV.1, S.6 and EU.1 wait until after Stage 5, EU.2 (Q-C8) and PD.1 (Q-C12) wait for new data and leases, FP-05 CR.3 and CR.1 wait for their FP-04 versions (Q-C10).

## Open chart questions

For the user (AGENTS.md "Chart oracles", c62004e: a deferred figure that needs an owner, or a chart that would change another module's frozen oracle, goes to the user; Modules freezes the oracles through a separate preparer and an mx-precise review). Each deferred figure that needs an owner ruling, plus the rulings the in-Stage-3 rows depend on. Rulings by the user on 2026-10-29 are recorded under each entry. Q-C13 and Q-C14 are new and open.

**Rulings the in-Stage-3 rows depend on**

- **Q-C1. Who owns the FP-04 maturity wall?** The design prints "MODEL · Fig. S.4" (`rbot-fp-04-covenant-refinancing.dc.html:42`); the repo binds `maturity-wall` to CP-2D (`report_view.py:1171`, `CP2D-OWNER-LEASE.md:126`). The CP-1 S.4 producer needs a CP-1 view and covenant_refinancing has no CP-MODEL (`contracts.py:51`). Recommend: CP-2D owns it, series from `T2E.4`.
  - **Ruled (user, 2026-10-29).** CP-2D owns the FP-04 maturity wall, series from T2E.4, one mark per facility, no aggregation. The oracle pins one mark per facility.
- **Q-C2. Who hosts the FP-04 funding-gap chart?** The design says CP-3C Fig. CR.3 (`:43`); the `funding-gap` block is a CP-2D spec (`report_view.py:1174`, bound to T2E.5, a single-horizon number); CP-3C's per-maturity series is `T3D.1`, bound to `refinancing-paths` (`CP3C-OWNER-LEASE.md:193`). Recommend: CP-3C produces the series, drawn in `funding-gap`, with a cross-module read of T3D.1 added to the CP-3C binding.
  - **Ruled (user, 2026-10-29).** CP-3C produces the funding-gap series (T3D.1), drawn in the `funding-gap` block. Add a read of T3D.1 to the CP-3C binding (a lease amendment, through LEAD).
- **Q-C3. CR.2 bridge steps.** The design bridge is accessible liquidity plus inflow minus mandatory uses minus discretionary capex (`rbot-fp-04-covenant-refinancing.dc.html:38`). CP-2D settles opening cash, flow over horizon, amortisation, maturities and cash at horizon end, with no lease or capex split. Recommend: draw the CP-2D steps and state the difference in the figure note; do not add a lease or capex step.
  - **Ruled (user, 2026-10-29).** Draw CP-2D's settled bridge steps (T2E.2.r01, T2E.3.r05-r08) and state the difference from the design in the figure note. Add no lease or capex step.
- **Q-C4. Scenario names in DR.2 and DR.3-5.** The design uses "Merger value (cited EV)", "Downside 5.0x", "Stress 4.0x"; CP-4C settles Base (4.00x), Downside (3.00x), Stress (2.00x) with CP-2G EBITDA (`cases/cp4c-owner/expected.json`). Recommend: label by the settled scenario names and multiples.
  - **Ruled (user, 2026-10-29).** Label DR.2 and DR.3-5 with the settled scenario names and multiples: Base 4.00x, Downside 3.00x, Stress 2.00x.

**Deferred figures**

- **Q-C5. RV.1 "Yield against maturity" (CP-3D).** Missing input: a dated reference-rate level or curve (`T3E.3.r04`, `T3E.3.r05` are gaps; `CP3D-OWNER-LEASE.md:34`). Options: add a rate source to the CP-3D pack and amend the oracle; or rule that the chart plots discount margin (`T3E.3.r03`) instead of yield; or keep deferred. Peer yields are also not CP-3D facts.
  - **Ruled (user, 2026-10-29).** Deferred until after all stages are complete (after Stage 5). Prepare no oracle now.
- **Q-C6. S.6 "Debt stack by rank, cumulative multiple" (CP-1).** Missing: a typed seniority rank in the credit_snapshot modules and an EV input. Options: rule that rank may be derived from T4.18 `facility_type`; or add CP-4C to the credit_snapshot preset and read `T4E.2.cNN.rank`; or defer.
  - **Ruled (user, 2026-10-29).** Deferred until after all stages are complete (after Stage 5). Prepare no oracle now.
- **Q-C7. EU.1 "Headline results" (CP-1B).** Waits on the CP-1B owner settlement (`MODULES.csv` line 5). Needs a period-pair oracle (Q2 2025 against Q2 2026) beyond the flat sequential A1 case.
  - **Ruled (user, 2026-10-29).** Deferred until after all stages are complete (after Stage 5). Prepare no oracle now.
- **Q-C8. EU.2 "KPI changes" (CP-1B).** Missing: a segment-margin series. Options: rule a substitute (EBITDA margin from `cases/earnings/expected.json`), or defer until a segment source exists.
  - **Ruled (user, 2026-10-29).** The KPIs must be operating statistics (for example same-store sales and volumes), not financial ratios. EBITDA margin is not an acceptable substitute. Timing: after the nine Stage 3 figures, until data and lease exist; it does not block Stage 3.
    Data check (2026-10-29): no operating statistics exist. `cases/earnings/expected.json` has measures `revenue`, `ebitda`, `adjusted_ebitda`, `ebitda_margin` only (`:16,32,48,64`); the only segment is "Consolidated Operations" revenue 30 per quarter (`cases/financial/manifest.json:40`, also cited `docs/CP1D-OWNER-LEASE.md:23` for the same pack). The pack states "Operational KPIs and source-reported unlevered free cash flow are not disclosed" (`cases/financial/manifest.json:40`) and lists `operational_kpis` under `unknown_not_zero` (`:168`, `:245`). `docs/CP1B-OWNER-LEASE.md` has no KPI, same-store or segment-margin text (grep, no match). The CP-1B cases reuse the financial manifest sources unchanged (`CP1B-OWNER-LEASE.md:57-76`), so there is no other source.
    Needed synthetic source (see new Q-C13): the design shows the dumbbell as `○ Q2 2025 · ● Q2 2026`, unit "%", a row per KPI with reference, current, change (pp) and trend (`rbot-fp-02-earnings-update.dc.html:46-48`). Inferred, not from the design: the metrics must be operating statistics named by the user (same-store sales, volumes), their exact names, units (percent change or absolute volume) and the two period values are not fixed by any file and the owner must set them.
- **Q-C9. EU.3 "EBITDA adjustments" (CP-1).** Missing: confirmed item-level adjustment facts (only the `ADJUSTED_EBITDA_BRIDGE` reconciliation kind and the totals were found). Confirm whether CP-1 settles adjustment line items; if not, rule a two-bar reported against adjusted bridge or defer.
  - **Ruled (user, 2026-10-29).** Check CP-1 for item-level adjustment facts; if settled, EU.3 joins Stage 3; if not, it stays deferred with no two-bar stand-in.
    Data check (2026-10-29): not settled, so EU.3 stays deferred, no two-bar stand-in. The frozen pack says "No EBITDA adjustments or add-backs occurred in any quarter or FY2025; this disclosure is complete" (`cases/financial/manifest.json:40`; `docs/CP1D-OWNER-LEASE.md:23`). `ADJUSTED_EBITDA_BRIDGE` is only a reconciliation kind listed per quarter (`cases/financial/manifest.json:250`). T4.17 (add-backs) is listed in `src/deploy_vii/methodology.json:42` and has 0 facts in a real CP-1 head (`docs/CP1D-OWNER-LEASE.md:23`). No `cases/financial/expected*.json` exists in this tree (the glob matched nothing; only `manifest.json` is present). The only itemised bridge is CP-1D's synthetic management-proposed items (`docs/CP1D-OWNER-LEASE.md:25`), a CP-1D source and not a CP-1 fact. EU.3 needs either a CP-1 pack with real recorded add-backs, or a ruling to draw from CP-1D; both go through LEAD and the user.
- **Q-C10. FP-05 CR.3 "Funding gap and LME capacity" and CR.1 "Covenant levers".** The blocks `funding-gap-lme` and `covenant-levers` are in the preset (`report_view.py:574-575`) but have no `_Spec` and no lease. Rule which module owns each (CP-3C and CP-4 per the design headers), then the figure rides on items 6 and 3.
  - **Ruled (user, 2026-10-29).** The owners are CP-3C (FP-05 funding gap and LME capacity) and CP-4 (covenant levers), as the design says. They reuse the Q-C2 and CR.1 series. Each is added after its FP-04 version lands, and after a small lease amendment.
- **Q-C11. DR.6 "Rating triggers" (CP-2H).** Missing: a real agency source. Pack facts exist only in the synthetic fictional-agency source (`CP2H-OWNER-LEASE.md:29`). Options: draw the n/a frame now (design's own state; the `gap` shape of `cases/cp2h-owner/expected.json`), draw `T2R.4`/`T2R.5` from the synthetic source, or keep deferred until a real source (`CP2H-OWNER-LEASE.md:166`).
  - **Ruled (user, 2026-10-29).** Draw the n/a frame now: the design's own state, using the existing CP-2H gap shape. A real chart waits for a real agency source. DR.6 (n/a frame) joins "Chart oracles to freeze".
- **Q-C12. PD.1 "Portfolio Fit" (CP-3B).** No module, lease or portfolio input exists (`MODULES.csv` line 15; `CP3-OWNER-LEASE.md:191`). Needs a CP-3B lease before any oracle.
  - **Ruled (user, 2026-10-29).** PD.1 uses related portfolio data from a synthetic test CLO. Timing: after the nine Stage 3 figures, until the data and lease exist; it does not block Stage 3. See the case spec under new Q-C14.
- **Q-C13 (new, open). Synthetic operating-statistics source for EU.2 (CP-1B), from Q-C8.** The earnings pack has none (Q-C8 data check). LEAD prepares a synthetic source and a CP-1B lease change; a source and lease change goes through LEAD, not this stage. Spec: operating statistics such as same-store sales and volumes, not financial ratios (user ruling); two periods, the design pair Q2 2025 and Q2 2026 (`rbot-fp-02-earnings-update.dc.html:47`); a row per statistic with reference, current and change. Names, units and values: not fixed by any file, to be set by LEAD (inferred: percent for growth statistics, a stated unit for volumes). The existing CP-1B period model is sequential quarters (`CP1B-OWNER-LEASE.md:57-62`), so the Q2 2025 reference period may also need a prior-year source. After the nine Stage 3 figures; does not block Stage 3.
- **Q-C14 (new, open). Synthetic CLO constraints and holdings case, and a CP-3B lease, for PD.1, from Q-C12.** No CP-3B lease or portfolio input exists (`MODULES.csv` line 15; `CP3-OWNER-LEASE.md:191`). LEAD prepares the case and the lease. What the design (`rbot-fp-06-portfolio-decision.dc.html`) shows, and no more (its values come from `data/rbot-data.js`, which is not stored):
  - Portfolio "Test CLO I", synthetic, flagged SYNTHETIC (`:42`, `:70`); fields: name, NAV, 1% of NAV, as-of date (`:46`).
  - Proposed position: par of the "6.50% SSN 2032", weight of NAV, cited price, market value (`:46`).
  - Limit table: per limit `id` (C-01 to C-04 are visible: C-01 and C-04 are highlighted, `:101`), `kind`, `label`, `limit`, `current`, `headroom`, `room US$`, and a `tight` flag (`:44-45`, `:101`). The figure is a bullet of current exposure (bar) against each limit (tick), unit % NAV (`:42`, `:72`; `lib/charts.js:89-100`: ceiling or floor direction, label with parenthetical).
  - One limit is stated: C-04 binds the unrated instruments at 0.14% of NAV, because no issue rating for the loans, 2030 notes or 2029 notes is in the sources (G35); bond eligibility unconfirmed (G40) (`:74`).
  - Not shown by the design, so inferred and for LEAD to set: which constraints exist (the user names concentration, rating-bucket and WARF-style limits as examples), their numeric limits, direction, and the holdings list (issuer, instrument, par, rating, price). The design's holdings fields are not visible.
  - Figure series for the oracle once the case exists: one row per limit that a Caesars position touches, `current` and `limit` in % NAV, `headroom`, direction; missing rating or eligibility shown as a gap with its G# reference, never as 0.
  After the nine Stage 3 figures; does not block Stage 3. The chart oracle is prepared from that case once it exists.
