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
   - Module: CP-2D (repo) or MODEL (design); see the question below.
   - Block: `maturity-wall`.
   - Series facts: `T2E.4.rNN.c1` principal, `T2E.4.rNN.c2` maturity date, `.c4` inside horizon. One mark per facility. Aggregating facilities by year or facility type would be new arithmetic, so the oracle either pins one mark per facility or the user rules an aggregation owner.
   - Oracle file: `cases/charts/s4-fp04-expected.json`.

6. **CR.3 "Funding gap" (FP-04)**
   - Module: CP-3C (design) with block `funding-gap` (repo spec owner CP-2D); see the question below.
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

## Open chart questions

For the user (AGENTS.md "Chart oracles", c62004e: a deferred figure that needs an owner, or a chart that would change another module's frozen oracle, goes to the user; Modules freezes the oracles through a separate preparer and an mx-precise review). Each deferred figure that needs an owner ruling, plus the three rulings the in-Stage-3 rows depend on.

**Rulings the in-Stage-3 rows depend on**

- **Q-C1. Who owns the FP-04 maturity wall?** The design prints "MODEL · Fig. S.4" (`rbot-fp-04-covenant-refinancing.dc.html:42`); the repo binds `maturity-wall` to CP-2D (`report_view.py:1171`, `CP2D-OWNER-LEASE.md:126`). The CP-1 S.4 producer needs a CP-1 view and covenant_refinancing has no CP-MODEL (`contracts.py:51`). Recommend: CP-2D owns it, series from `T2E.4`.
- **Q-C2. Who hosts the FP-04 funding-gap chart?** The design says CP-3C Fig. CR.3 (`:43`); the `funding-gap` block is a CP-2D spec (`report_view.py:1174`, bound to T2E.5, a single-horizon number); CP-3C's per-maturity series is `T3D.1`, bound to `refinancing-paths` (`CP3C-OWNER-LEASE.md:193`). Recommend: CP-3C produces the series, drawn in `funding-gap`, with a cross-module read of T3D.1 added to the CP-3C binding.
- **Q-C3. CR.2 bridge steps.** The design bridge is accessible liquidity plus inflow minus mandatory uses minus discretionary capex (`rbot-fp-04-covenant-refinancing.dc.html:38`). CP-2D settles opening cash, flow over horizon, amortisation, maturities and cash at horizon end, with no lease or capex split. Recommend: draw the CP-2D steps and state the difference in the figure note; do not add a lease or capex step.
- **Q-C4. Scenario names in DR.2 and DR.3-5.** The design uses "Merger value (cited EV)", "Downside 5.0x", "Stress 4.0x"; CP-4C settles Base (4.00x), Downside (3.00x), Stress (2.00x) with CP-2G EBITDA (`cases/cp4c-owner/expected.json`). Recommend: label by the settled scenario names and multiples.

**Deferred figures**

- **Q-C5. RV.1 "Yield against maturity" (CP-3D).** Missing input: a dated reference-rate level or curve (`T3E.3.r04`, `T3E.3.r05` are gaps; `CP3D-OWNER-LEASE.md:34`). Options: add a rate source to the CP-3D pack and amend the oracle; or rule that the chart plots discount margin (`T3E.3.r03`) instead of yield; or keep deferred. Peer yields are also not CP-3D facts.
- **Q-C6. S.6 "Debt stack by rank, cumulative multiple" (CP-1).** Missing: a typed seniority rank in the credit_snapshot modules and an EV input. Options: rule that rank may be derived from T4.18 `facility_type`; or add CP-4C to the credit_snapshot preset and read `T4E.2.cNN.rank`; or defer.
- **Q-C7. EU.1 "Headline results" (CP-1B).** Waits on the CP-1B owner settlement (`MODULES.csv` line 5). Needs a period-pair oracle (Q2 2025 against Q2 2026) beyond the flat sequential A1 case.
- **Q-C8. EU.2 "KPI changes" (CP-1B).** Missing: a segment-margin series. Options: rule a substitute (EBITDA margin from `cases/earnings/expected.json`), or defer until a segment source exists.
- **Q-C9. EU.3 "EBITDA adjustments" (CP-1).** Missing: confirmed item-level adjustment facts (only the `ADJUSTED_EBITDA_BRIDGE` reconciliation kind and the totals were found). Confirm whether CP-1 settles adjustment line items; if not, rule a two-bar reported against adjusted bridge or defer.
- **Q-C10. FP-05 CR.3 "Funding gap and LME capacity" and CR.1 "Covenant levers".** The blocks `funding-gap-lme` and `covenant-levers` are in the preset (`report_view.py:574-575`) but have no `_Spec` and no lease. Rule which module owns each (CP-3C and CP-4 per the design headers), then the figure rides on items 6 and 3.
- **Q-C11. DR.6 "Rating triggers" (CP-2H).** Missing: a real agency source. Pack facts exist only in the synthetic fictional-agency source (`CP2H-OWNER-LEASE.md:29`). Options: draw the n/a frame now (design's own state; the `gap` shape of `cases/cp2h-owner/expected.json`), draw `T2R.4`/`T2R.5` from the synthetic source, or keep deferred until a real source (`CP2H-OWNER-LEASE.md:166`).
- **Q-C12. PD.1 "Portfolio Fit" (CP-3B).** No module, lease or portfolio input exists (`MODULES.csv` line 15; `CP3-OWNER-LEASE.md:191`). Needs a CP-3B lease before any oracle.
