# Earnings Update: Front Page content

## 1. Purpose

Question: **what did the period change, and does the credit view move?** A credit research analyst reads it the day results are out; a PM reads the first screen to learn whether to revisit the existing view. All data below: `data/front-pages-data.json` (FP) unless stated; Caesars Entertainment (CZR), period Q2 2026, analysis date 2026-10-02.

## 2. The call

Title: "Credit view". Every item is **illustrative** (`illustrative.judgements.creditView`, `illustrative.callBand`).

| Order | Item | Value |
|---|---|---|
| 1 | Credit Score | 3 - Fair (illustrative) |
| 2 | Credit Direction | Deteriorating (illustrative) |
| 3 | Sector Outlook | Neutral (illustrative) |
| 4 | Since last Report | "No Prior Case" (`illustrative.callBand.priorCase`): none was accepted at Approval; this is the first RBOT Report on Caesars. Shown as n/a, not as "Unchanged" |
| 5 | Sponsor Quality | Medium (illustrative; base `illustrative.sponsorQuality`) |

One-line facts, in order:
- **The quarter**: net revenues US$2,993m, up 3.0%; Adjusted EBITDA US$920m, (3.7)%; margin 30.7%, (2.1) pp. Regional includes Caesars Windsor from 3 March 2026. (`calcs.K74`, `K112`, `K114`; base `figures.net_revenues_q2_2026`, `adj_ebitda_q2_2026`)
- **Watch**: merger debt terms (G8); Las Vegas margin 40.3%, down (4.2) pp (`K134`, `K136`).
- **Recommendation**: stated as absent. This Pathway runs no CP-3, CP-6 or Portfolio Fit, so it produces **no Recommendation, no Valuation and no Portfolio Fit**: the page answers whether the credit view moves, not whether to own the issuer.

## 3. Blocks (page order)

**Headline results** (CP-1B Earnings delta). Period comparison table, `blocks.periodComparison`, with chart `charts.fig-headline-results` (grouped columns, US$ m; Q2 2025 against Q2 2026 for Adjusted EBITDA 955 to 920, Interest expense net 579 to 573, D&A 364 to 355, Capex net 230 to 167). Table twin: the same rows. Net revenues 2,907 to 2,993 (change 86, 3.0%), Net debt 11,018 to 10,842, Net leverage 3.04x to 3.02x (LTM against FY). Calculated with cited inputs. Not meaningful change % cells show n/a G41 with the reason; the cash-flow row is six months only (G3). Perimeter column: Windsor consolidated from 3 March 2026.

**Variance drivers** (CP-1B). `blocks.varianceDrivers`: management says (cited quotes, Las Vegas, Regional, Caesars Digital, Interest expense); analyst view and credit implication are model-written and illustrative (the implication column shows in full-depth runs only).

**KPI changes** (CP-1B; hidden when no rows). `blocks.kpiChanges` with `charts.fig-kpi-margins` (dumbbell, %, Q2 2025 to Q2 2026): Las Vegas 44.5 to 40.3; Regional 30.6 to 31.1; Caesars Digital 23.3 to 19.4; Managed and Branded 23.0 to 28.1. Calculated; trend word Down/Up.

**Guidance against delivery; early signals** (CP-1B). `blocks.guidance` is one row, all n/a: no guidance and no conference call because of the pending merger (G13). `blocks.signals`: four signals with illustrative severity (Las Vegas margin compression High; Windsor flattering Regional Medium; Digital revenue up, EBITDA down Medium; unsecured 2032s priced for distress High, at 84.94 rated Caa1).

**EBITDA adjustments** (Model). Base `tables.ebitdaAdjustments` and `charts.ebitdaBridge`: Reported 868, add-backs 29 and 23, Structuring EBITDA 920 (Q2 2026); LTM Structuring 3,592; LTM Reported and PF-LTM n/a (G20, G21); unrealized add-backs n/a (G22).

**Metric strip** (Model; historical only). Base `charts.leverage`, `coverage`, `liquidity`: net leverage 3.04x FY2025, 3.02x LTM; interest cover 1.57x LTM, 4.63x debt-only; liquidity US$2,928m at 30 June 2026 only (G16). FY2023-24 leverage n/a (G15). No projected series (no forecast ran).

**Financials and credit metrics** (Model). Base `tables.financials`, `tables.creditMetrics`, FY2023 to LTM Q2 2026 (LTM revenue 11,648, Adjusted EBITDA 3,592, margin 30.8%, FCF 610).

**Watch items** (CP-2; illustrative). `blocks.watchItems`: merger debt terms; Las Vegas margin below 40.3% for a second quarter; CEI revolver maturity 31 January 2028 (72.7% of liquidity); merger End Date 27 May 2027, ticking fee from 26 June 2027.

**Historical performance** (CP-1B; model-written). Base `illustrative.historicalPerformance` with `charts.revenueEbitda`.

**Company profile** (compact, collapsed by default). Sector and country n/a, issue ratings B1/BB- (secured 2032s), Caa1/B- (unsecured 2032s), issuer ratings, outlooks and Fitch n/a (G25, G11, G10), Sponsor Quality.

## 4. First viewport priority

Visible at 1440x900 with no scroll: the call (Credit Score, Direction, Outlook, the quarter line, the watch line, the no-Recommendation line); the headline results table with its chart; the variance drivers.

## 5. Page-specific states

- **What changed since the last Report**: not shown; one line: "no Prior Case was accepted at Approval; this is the first RBOT Report on Caesars".
- Portfolio Fit is **absent in this Pathway**: shown as "Not in this Pathway", not hidden.
- Steps not run, listed under Limitations: Deep Research (CP-DR) and What changed (CP-8).
- Notable n/a: guidance, quarterly cash flow (six-month only), LTM Reported EBITDA, pro forma LTM.

## 6. Module views behind it (navigation order)

CP-0 Source readiness (Restricted): source inventory, company profile. CP-1 Financials and debt (Pass): financials, capital structure. CP-1A Business and events (Restricted): company profile, operating model, transactions and events (`blocks.transactionsEvents`). CP-1B Earnings delta (Restricted): headline results, segment changes (`blocks.segmentChanges`), variance drivers, KPI changes, guidance and signals, historical performance. CP-1D Earnings quality (Restricted): EBITDA adjustments, add-back assessment, cash conversion, debt-like items. CP-2 Credit synthesis (Restricted): credit view, strengths and weaknesses, watch items. Folded: CP-5 into Evidence. Module reader questions, reasons and gaps: FP `modules` and `pathways.EARNINGS_UPDATE`.

## 7. Real CAOS output

The live Earnings Update run of 5 October 2026 (`data/caos-runs/earnings-update-2026-10-05/`: CP-0, CP-1, CP-1B, CP-2, CP-5) supplies real earnings-delta and credit-synthesis text (CP-1B confidence 56, CP-2 59, all With limitations). Prefer its wording for variance drivers, signals and the credit view; the management drivers in this doc are cited from the 10-Q either way.
