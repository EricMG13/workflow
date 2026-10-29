# Stage 3 chart inventory

Built 2026-10-29 for the Stage 3 Charts step (`docs/superpowers/plans/2026-10-28-verified-module-builds.md:140`). Docs only. Figure ids and titles are quoted from the design; owner codes are the codes printed in each design block header. All design paths are under `/Users/ericguei/Documents/DEPLOY VII/design/reference/` (read only).

## Sources

Design files read: `README.md`; `rbot-fp-01-credit-snapshot.dc.html`, `rbot-fp-02-earnings-update.dc.html`, `rbot-fp-03-relative-value.dc.html`, `rbot-fp-04-covenant-refinancing.dc.html`, `rbot-fp-05-distressed-restructuring.dc.html`, `rbot-fp-06-portfolio-decision.dc.html`; `rbot-report.dc.html`; `rbot-design-system.dc.html` (DS-05 chart kit, `:299-312`); `direction-c-workbench.dc.html` (superseded per `README.md`); `lib/charts.js` (chart kinds); `lib/vm.js`, `lib/vm-fp.js`; `screens/` (PNGs, not opened; only FP-01 and FP-02 exist there).

Limit: figure titles that come from `data/rbot-data.js` (`hl.title` for EU.1, `bridge.title` for EU.3, `yc`, `peerStrip` summaries) cannot be quoted, because that file is deliberately not stored (`README.md`, supporting-files table). Where a title is data-driven the row quotes the block header instead and says so.

Ruling and contract sources: `docs/CP1-CHART-SLICE.md` (chart-contract pattern; `:66` the producer API, `:131-139` oracle-first order); `docs/rulings/2026-10-28-stage1.md` and `docs/rulings/2026-10-28-stage2.md`; the owner leases `docs/CP*-OWNER-LEASE.md`; `docs/MODULES.csv`; `src/deploy_vii/report_view.py` (`_PRESETS` `:469-598`, `_Spec` rows `:1092-1260`, `_STRIP_FIGURES` `:1264`); `src/deploy_vii/contracts.py:46-62` (pathway module presets); the frozen oracles `cases/<cp>-owner/expected.json` and `cases/charts/expected.json`.

"Settled today" means: the module's Stage 1 core is merged in the lane (`work/build/ledger.md`) and its frozen oracle holds the fact ids (`cases/<cp>-owner/expected.json`). It does not mean the Stage 2 run driver or any rendering exists. Fact ids below are the ids that appear in those oracles; where I could not find the row ids the row says so.

Block ids are the `report_view._PRESETS` ids for the pathway. `owner_workflow.py` registers modules, not blocks; the block-to-module map is `report_view._Spec` plus each lease's "Rendered sections" (D7).

## Figures by pathway

Status words are exactly: **in Stage 3**, **deferred** (reason, named owner), **out of scope** (reason).

### FP-01 Credit Snapshot (`credit_snapshot`)

| Figure | Owning module | Pathway / block | Series and facts needed | Settled Stage 1 facts today? | Status |
|---|---|---|---|---|---|
| S.1 "Leverage" (FP-01 `:49`; Model chart strip header `:47`) | CP-1 series, CP-MODEL publication | credit_snapshot / `model-chart-strip` (`report_view.py:1098`) | Total and net reported leverage by QUARTER: CP-1 T4.10, T4.14 (`CP1-CHART-SLICE.md:38-40`, `cases/charts/expected.json` `chart_series.S.1`) | Yes. CP-1 and CP-MODEL: `cases/charts/expected.json`, `cases/financial/manifest.json` | out of scope: built and verified by Task3-C (`MODULES.csv` CP-1 and CP-MODEL rows, lines 3 and 26; `CP1-CHART-ACCEPTANCE.md`); nothing left to wire |
| S.2 "Interest cover" (`:50`) | CP-1 / CP-MODEL | `model-chart-strip` | Reported interest coverage, T4.10 + T4.14 (`expected.json` `chart_series.S.2`) | Yes (same oracle) | out of scope: built and verified by Task3-C |
| S.3 "Liquidity" (`:51`) | CP-1 / CP-MODEL | `model-chart-strip` | cash_closing, undrawn_rcf, liquidity, T4.10 (`expected.json` `chart_series.S.3`) | Yes (same oracle) | out of scope: built and verified by Task3-C |
| S.4 "Maturity wall" (`:52`) | CP-1 / CP-MODEL | `model-chart-strip` | T4.18 facility snapshot (`financial_series.py:195-215`; `CP1-CHART-SLICE.md:48-53`) | Yes (same oracle; one facility) | out of scope: built and verified by Task3-C |
| S.5 "Net revenues and Adjusted EBITDA" (`:66`) | CP-1 (block producers `("CP-1",)`, `report_view.py:1102-1108`) | `financials-credit-metrics` | Revenue and adjusted EBITDA by period: CP-1 T4.5 statement history and T4.10 (`CP2D-OWNER-LEASE.md:104`, `CP2G-OWNER-LEASE.md:111`). Quarter and FY values exist in `cases/financial/manifest.json:128-133,176-186,1948-1953` (`revenue`, `adjusted_ebitda`). I did not enumerate the T4.5 row ids; the oracle freeze must. | Yes. CP-1, `cases/financial/manifest.json`. `cases/charts/expected.json` covers S.1-S.4 only, so S.5 has no chart oracle. | in Stage 3 |
| S.6 "Debt stack by rank, cumulative multiple" (`:59`) | CP-1 (block `capital-structure`, `report_view.py:1101`) | `capital-structure` | Per-facility principal by seniority rank, divided by LTM adjusted EBITDA, plus markers for secured, total and "EV 4.90x" | Partly. T4.18 principal and LTM adjusted EBITDA are settled; seniority rank is a free-text `facility_type` ("senior secured term loan", `cases/charts/expected.json` `current_maturity_wall`), not a typed rank fact. The only typed rank is CP-4C `T4E.2.cNN.rank`, a module not in the credit_snapshot preset (`contracts.py:46-50`). The "EV" marker needs a transaction value the pack does not state. | deferred: no settled rank fact in the pathway's modules and no EV input. Owner: user ruling (rule whether rank may be read from CP-1 facility type, or whether CP-4C joins the preset) |

### FP-02 Earnings Update (`earnings_update`)

| Figure | Owning module | Pathway / block | Series and facts needed | Settled Stage 1 facts today? | Status |
|---|---|---|---|---|---|
| EU.1 "Headline results" (header `:38`; title is `hl.title`, data file not stored) | CP-1B | earnings_update / `headline-results` (`report_view.py:1130`) | Grouped columns of prior against current period per measure. A1 oracle `cases/earnings/expected.json` `positive.points`: `revenue`, `ebitda`, `adjusted_ebitda` (prior, current, delta). The design's period pair is Q2 2025 against Q2 2026. | Partly. CP-1B A1 core accepted; the owner settlement is open (`MODULES.csv` line 5: "A2 fix pending ... owner settlement remains open"). The oracle is a flat sequential synthetic case (`expected.json` `scope`). | deferred: CP-1B owner settlement and period-pair oracle open. Owner: user ruling (CP-1B owner checkpoint) |
| EU.2 "KPI changes" (header `:46`; data `fpCharts['fig-kpi-margins']`) | CP-1B | `kpi-changes` (`report_view.py:1136`) | Dumbbell of segment margins, reference against current | No. I found no segment-margin fact in `cases/earnings/expected.json` or `cases/financial/manifest.json` (A1 has margin delta only, `CP1B-OWNER-LEASE.md:468-473`). | deferred: missing input is a segment-margin series. Owner: user ruling (rule a substitute such as EBITDA margin, or defer to a segment-reporting source) |
| EU.3 "EBITDA adjustments" (header `:52`; title is `bridge.title`, data file not stored) | CP-1 (block owner printed as MODEL, `report_view.py:1142`) | `ebitda-adjustments` | Waterfall from reported EBITDA through adjustment items to adjusted EBITDA | Partly. CP-1 holds the reconciliation kind `ADJUSTED_EBITDA_BRIDGE` (`cases/financial/manifest.json:250`) and reported/adjusted totals; I did not find typed adjustment line items. | deferred: item-level adjustment facts not confirmed. Owner: user ruling (confirm CP-1 line items or accept a two-bar bridge) |
| S.1 "Leverage" (FP-02 `:57`) | CP-1 / CP-MODEL | `metric-strip` (`report_view.py:1145`) | Same series as FP-01 S.1 | Yes | out of scope: already drawn for earnings_update (`tests/test_cp1_chart_render.py:395-399` asserts S.1-S.3 in `metric-strip`) |
| S.2 "Interest cover" (`:58`) | CP-1 / CP-MODEL | `metric-strip` | Same as FP-01 S.2 | Yes | out of scope: already drawn (same test) |
| S.3 "Liquidity" (`:59`) | CP-1 / CP-MODEL | `metric-strip` | Same as FP-01 S.3 | Yes | out of scope: already drawn (same test) |

### FP-03 Relative Value (`relative_value`)

| Figure | Owning module | Pathway / block | Series and facts needed | Settled Stage 1 facts today? | Status |
|---|---|---|---|---|---|
| RV.1 "Yield against maturity" (`:45`) | CP-3D | relative_value / `yield-against-maturity` (preset only, `report_view.py:532`; no `_Spec`) | Scatter of yield against maturity for CZR and peer instruments. CP-3D holds `T3E.1.r01-r03` (dealer levels) and `T3E.3.r03` (simple discount margin), but `T3E.3.r04` (reference rate level) and `T3E.3.r05` (all-in yield) are gaps (`cases/cp3d-owner/expected.json`, `T3E.7.r01`: "No reference rate level or forward curve appears in any source of the pack"). | No. CP-3D lease `:34` already defers it. The design's peers' yields are not CP-3D facts either. | deferred: missing input is a dated reference-rate level or curve in the pack (and peer instrument levels). Owner: user ruling (supply a rate source, or rule a different y-axis) |
| RV.3 "Peer positioning" (`:53`) | CP-1C | relative_value / `peer-positioning` (`report_view.py:1203`) | Range strip, one row per metric, issuer against peer range: `T1C.3.issuer.*` and `T1C.3.pNN.*` for `adjusted_ebitda_margin`, `total_leverage_adjusted`, `interest_coverage_adjusted`, `ffo_to_debt`; `T1C.4.<metric>.median`; inclusion flag `T1C.1.pNN.included` (peer p05 is Excluded, so it must not widen the range). The design's second row "Last-trade yield" has no CP-1C fact and is left out. | Yes. CP-1C Stage 1 merged (`ledger.md`), oracle `cases/cp1c-owner/expected.json` positive case | in Stage 3 (lease `CP1C-OWNER-LEASE.md:152` item 9 deferred it without an owner; this inventory names Modules as freezer (separate preparer, mx-precise review) and `mx-feature` as wirer) |
| "Market-implied default" n/a frame (`:49`, `:104`; no Fig. id; gap G37) | CP-3D | `market-against-fundamentals` (`report_view.py:1195`) | None drawn; the design shows a `naFrame`, not a series. CP-3D settles `T3E.5.r01` and `T3E.5.r02` as table values. | n/a | out of scope: not a series chart and has no figure id; CP-3D shows T3E.5 as a table (`CP3D-OWNER-LEASE.md:168`) |

### FP-04 Covenant & Refinancing (`covenant_refinancing`)

| Figure | Owning module | Pathway / block | Series and facts needed | Settled Stage 1 facts today? | Status |
|---|---|---|---|---|---|
| CR.1 "Covenant tests and headroom" (`:34`; twin "Fig. CR.1 Covenant tests", `:58`) | CP-4 | covenant_refinancing / `covenant-tests-headroom` (`report_view.py:1150`; bound to T4.9, `CP4-OWNER-LEASE.md:190`) | Bullet rows: `T4.9.rNN.threshold`, `.comparison` (ceiling or floor), `.current`, `.headroom`. Positive case `T4.9.r01`: threshold 4.00x, comparison "Not more than", current 1, headroom 3.00 (`cases/cp4-owner/expected.json`). In the gap case `T4.9.r01.headroom` is `missing`, so the bullet must render that row as a gap, not zero. | Yes. CP-4 Stage 1 merged, oracle `cases/cp4-owner/expected.json` | in Stage 3 (the CP-4 lease never mentions a chart) |
| CR.2 "Liquidity runway" (`:38`) | CP-2D | covenant_refinancing / `liquidity-runway` (`report_view.py:1168`; `CP2D-OWNER-LEASE.md:126`) | Waterfall: opening cash `T2E.2.r01`; `T2E.3.r05` run-rate flow over horizon; `T2E.3.r06` amortisation; `T2E.3.r07` maturities; closing `T2E.3.r08` cash at horizon end. The design's steps (mandatory uses, discretionary capex) are not CP-2D facts; see questions. | Yes. CP-2D Stage 1 merged, oracle `cases/cp2d-owner/expected.json` (positive is degenerate: all flows 0; `long_horizon` has maturities 50 and is the non-trivial case) | in Stage 3 |
| S.4 "Maturity wall" (`:42`; header owner printed as MODEL) | CP-2D in the repo; MODEL in the design | `maturity-wall` (`report_view.py:1171`; `T2E.4` bound to it, `CP2D-OWNER-LEASE.md:126`) | One mark per T4.18 facility: `T2E.4.rNN.c1` principal, `.c2` maturity date (positive: `T2E.4.r01.c1` = 50, `.c2` = 2029-12-31) | Yes. CP-2D oracle. The CP-1 S.4 producer needs a CP-1 ModuleView and covenant_refinancing has no CP-MODEL (`contracts.py:51`). | in Stage 3 (owner conflict, see questions: repo says CP-2D, design says MODEL) |
| CR.3 "Funding gap" (`:43`, owner CP-3C) | CP-3C in the design; the block is CP-2D's in the repo (`report_view.py:1174`) | `funding-gap` | Columns of maturing against liquidity left per maturity: `T3D.1.rNN.c6` principal payable at maturity and `T3D.1.rNN.c7` resources at maturity (positive `T3D.1.r01`: 50 and 10). CP-2D's `T2E.5.r07` is a single-horizon gap, not a per-maturity series. | Yes. CP-3C Stage 1 merged, oracle `cases/cp3c-owner/expected.json`. Binding of T3D.1 is to `refinancing-paths` (`CP3C-OWNER-LEASE.md:193`), not `funding-gap`. | in Stage 3 (host block and owner need a ruling, see questions) |
| "Lender protection score" meters (`:48`; no Fig. id) | CP-4 | `lender-protection-score` | Five-segment score glyph inside a table (`T4.13`) | n/a | out of scope: in-table glyph with no figure id, not a series chart |

### FP-05 Distressed & Restructuring (`distressed_restructuring`)

| Figure | Owning module | Pathway / block | Series and facts needed | Settled Stage 1 facts today? | Status |
|---|---|---|---|---|---|
| DR.2 "Recovery by class" (`:37`; twin "Fig. DR.2 Recovery, %", `:71`) | CP-4C | distressed_restructuring / `recovery-by-class` (`report_view.py:1230`) | Columns of recovery % per scenario and class: `T4E.5.v0Nc0M.recovery` (N = 1 Base, 2 Downside, 3 Stress; M = class), plus `T4E.3.v0N.multiple` for the hatching. Equity rows are `not_meaningful` and are not plotted. | Yes. CP-4C Stage 1 merged, oracle `cases/cp4c-owner/expected.json` positive (recoveries 100%, 18.7%, 74.2%, 0%) | in Stage 3 (the CP-4C lease never mentions a chart) |
| DR.3-5 "Value allocation" (`:40`; three waterfalls: Merger value, Downside 5.0x, Stress 4.0x) | CP-4C | `value-allocation-claims` (`report_view.py:1233`) | Waterfall per scenario: `T4E.3.v0N.ev` (enterprise value), `T4E.4.v0Nc0M.distribution` per class, `T4E.9.v0N.equity_residual` (`T4E.9` also holds `total_claims`, `creditor_distributions`) | Yes (same oracle). The design's "merger value (cited EV)" scenario is not a CP-4C scenario; CP-4C has Base, Downside, Stress. | in Stage 3 |
| CR.2 "Liquidity runway" (FP-05 `:45`) | CP-2D | `liquidity-runway` (same block id, shared spec, `report_view.py:1166-1169`) | Same as FP-04 CR.2 | Yes | in Stage 3 (same wiring as FP-04 CR.2) |
| CR.3 "Funding gap and LME capacity" (`:48`) | CP-3C | `funding-gap-lme` (preset only, `report_view.py:574`; no `_Spec`, no lease) | Same T3D.1 series as FP-04 CR.3 plus `T3D.5` LME capacity | Yes for the facts; the block has no producer | deferred: block has no `_Spec` and no owner lease. Owner: user ruling (assign the block to CP-3C, then wire) |
| CR.1 "Covenant levers" (`:51`) | CP-4 | `covenant-levers` (preset only, `report_view.py:575`; no `_Spec`, no lease) | Same T4.9 series as FP-04 CR.1 | Yes for the facts; the block has no producer | deferred: block has no `_Spec` and no owner lease. Owner: user ruling (assign the block to CP-4, then wire) |
| DR.6 "Rating triggers" (`:54`; design draws an n/a frame, gap G31) | CP-2H | `rating-triggers` (`report_view.py:1226`) | Rating-trigger headroom: `T2R.4.tNN.headroom`, `T2R.5.*` (forward headroom). Thresholds exist only in the synthetic fictional-agency source CP-2H added (`CP2H-OWNER-LEASE.md:29`). | Partly. CP-2H Stage 1 merged, oracle `cases/cp2h-owner/expected.json`; no real agency source, and the design's own frame says thresholds are unstated. | deferred: lease `CP2H-OWNER-LEASE.md:166` item 9 ("a later chart lease once an agency source is a real pack source"). Missing input: a real agency source. Owner: user ruling |

### FP-06 Portfolio Decision (`portfolio_decision`)

| Figure | Owning module | Pathway / block | Series and facts needed | Settled Stage 1 facts today? | Status |
|---|---|---|---|---|---|
| PD.1 "Portfolio Fit · Test CLO I limits a Caesars position touches" (`:42`; twin "Fig. PD.1 · % NAV", `:72`) | CP-3B (block printed as FIT) | portfolio_decision / `portfolio-fit` (`report_view.py:1119`, producers `()`) | Bullet of current exposure against each portfolio limit, % NAV. No fact ids exist: no portfolio-fit module has a lease. | No. `MODULES.csv` line 15: "Later exact lease in PLAN.md"; `CP3-OWNER-LEASE.md:191` and `:276` say portfolio blocks belong to the deferred CP-3B/CP-6A owners. | deferred: no module, no lease and no portfolio input. Owner: user ruling (CP-3B lease) |

## Other design files

| File | Figures | Status |
|---|---|---|
| `direction-c-workbench.dc.html` (`:131,166,170,174,175`) | S.1, CR.1, CR.2, S.4, CR.3, S.3 | out of scope: superseded phase 1 (`README.md`); the same figures are in the FP rows |
| `rbot-design-system.dc.html` DS-05 (`:299-312`) and `rbot-report.dc.html` | Chart-kit catalogue of S.1, EU.1, S.4, CR.2, CR.1, EU.2, RV.1, RV.3, S.6, DR.2, DR.6, CR.3 | out of scope: specimen sheet of the figures already listed per pathway; no additional figure |

## Counts

27 figure rows over the six pathways (plus 2 other-file rows that add no figure).

| Status | Rows |
|---|---|
| in Stage 3 | 9: S.5; RV.3; CR.1 (FP-04); CR.2 (FP-04); S.4 (FP-04); CR.3 (FP-04); DR.2; DR.3-5; CR.2 (FP-05) |
| deferred | 9: S.6; EU.1; EU.2; EU.3; RV.1; CR.3 (FP-05); CR.1 (FP-05); DR.6; PD.1 |
| out of scope | 9: S.1-S.4 (FP-01); S.1-S.3 (FP-02); market-implied default frame; lender protection meters |

## Modules with no figure

Every module in `docs/MODULES.csv` (26 rows) not named as an owner above. The check is the design headers: every block header with a "Fig." id names one of CP-1B, CP-3D, CP-1C, CP-4, CP-2D, CP-3C, CP-4C, CP-2H, MODEL or FIT (grep of the six FP files above).

| Module | Result |
|---|---|
| CP-0 | no figure in design |
| CP-1A | no figure in design |
| CP-1D | no figure in design (its blocks `earnings-quality` and `restated-leverage` are tables, `report_view.py:1241-1250`) |
| CP-2 | no figure in design |
| CP-2A | no figure in design |
| CP-2E | no figure in design |
| CP-2G | no figure in design (`CP2G-OWNER-LEASE.md:158`: "CP-2G has no Front Page block") |
| CP-3 | no figure in design |
| CP-5 | no figure in design |
| CP-6 | no figure in design |
| CP-6A | no figure in design |
| CP-8 | no figure in design |
| CP-DR | no figure in design |
| CP-L10 | no figure in design |
| CP-OS | no figure in design |

15 modules have no figure. The other 11 own at least one row: CP-1, CP-MODEL, CP-1B, CP-1C, CP-2D, CP-2H, CP-3B, CP-3C, CP-3D, CP-4, CP-4C. Of the eight modules the brief says never mention charts, CP-4 and CP-4C do own design figures (CR.1, DR.2, DR.3-5); CP-2A, CP-1D, CP-8, CP-5, CP-3 and CP-OS own none.
