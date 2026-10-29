# Credit Snapshot: Front Page content

## 1. Purpose

Question: **should we own this issuer, in which instrument, and why?** The Front Page of the Full Credit Assessment Pathway. A PM states the Recommendation, the main risk and the Valuation within a minute; an analyst follows each block to its module. Data: `data/rbot-data-base.json` (base); Portfolio Fit from `data/front-pages-data.json` (FP). Caesars (CZR), Q2 2026, analysis date 2026-10-02, Full depth, **Primary run: the Fertitta merger financing**. The owner no longer requires the Excel template (17 Oct 2026): this document gives content only. All judgements are **illustrative**; Test CLO I is **synthetic**.

## 2. The call

Title: "Analyst recommendation", by Credit Research (illustrative), 2026-10-02 (`meta.analyst`, `meta.analysisDate`).

| Item | Value (base `illustrative`) |
|---|---|
| Recommendation, CLO | 3 - MW |
| Recommendation, Indexed Loans | 3 - MW |
| Recommendation, Indexed HY | 2 - Modest OW |
| Valuation | V2 - Attractive |
| Credit Score | 3 - Fair |
| Credit Direction | Deteriorating |

Lines:
- **Portfolio Fit**: Test CLO I (synthetic) from FP `fit`, not base `portfolio.fit`: proposed US$5,000,000 of the 6.50% secured 2032s Fits, max US$15,773,213 under C-01; loans and unrated notes Watch, max US$883,300 under C-04 (no issue rating, G35). Report A's illustrative Fit line read the C-01 headroom of the largest existing issuer (Asurion, 0.13%) and is **superseded** by `fit`, which tests Caesars' own exposure (none).
- **Instrument**: Indexed HY: prefer the 6.50% secured 2032s over the unsecured notes until the merger financing is known (illustrative); eligibility of the bond as a CLO asset is unconfirmed (G40).

## 3. Blocks (page order; nothing here needs a click)

**Key findings and main risk** (model-written). Base `illustrative.keyFindings`: total leverage 3.29x before any merger debt; interest cover 1.57x including lease obligations, 4.63x on debt cash interest; no final maturity before 31 January 2028; unsecured 2032s at 84.94 (Caa1), secured at 93.28 (B1). Main risk: merger debt unknown, the committed financing has no stated amount (G8).

**Company and operating model** (CP-1A). Base `tables.operatingModel`: a geographically diversified gaming and hospitality company, founded 1973; Regional 50.1% and Las Vegas 35.3% of FY2025 net revenues; 54 properties in 20 jurisdictions.

**Chart strip** (MODEL). Base `charts.leverage` (total 3.29x, net 3.02x LTM; FY2023-24 n/a, G15), `charts.coverage` (1.57x and 4.63x), `charts.liquidity` (2,928 at 30 June 2026 only, G16), `charts.maturityWall` (US$ m, stacked by rank; 2030 heaviest). Projected Base and Downside series appear only if a projection ran (none here).

**Capital structure** (MODEL) with multiples and % EV. Base `tables.capitalStructure`: eleven facilities; senior secured 9,468 (2.64x, 53.8% EV), unsecured 2,300 (3.28x, 66.9%), other 39, total debt 11,807 (3.29x, 67.1%), cash 965, net debt 10,842, EV 17,600 at the merger value, 4.90x. Recommendation per instrument joins by facility (`illustrative.byInstrument`). PF interest and PF-LTM n/a (G21); equity market value n/a (G27). GLPI and VICI obligations (13,157) shown apart.

**EBITDA adjustments** (MODEL). Base `tables.ebitdaAdjustments`: Q2 2026 Reported 868, transaction costs 29, stock-based compensation 23, Structuring and SSIM EBITDA 920; LTM Structuring 3,592; LTM Reported n/a (G20); unrealized add-backs n/a (G22).

**Financials and credit metrics** (MODEL). Base `tables.financials`, `tables.creditMetrics`, `charts.revenueEbitda`: FY2023 to LTM Q2 2026; LTM revenue 11,648, Adjusted EBITDA 3,592, FCF 610.

**Strengths and weaknesses with thesis** (CP-2, CP-6; model-written, illustrative). Base `illustrative.thesis`, `strengths`, `weaknesses` (four each).

**Relative value** (CP-3; collapsed). Loan and HY blocks from `tables.trace` and the capital structure loan rows: CZR 6.50% secured 2032 at 93.28, 8.063520%; 6.00% unsecured 2032 at 84.94, 9.318398%; MGM 6.125% 2029 at 98.42, 6.722997%. Index statistics, loan marks, spreads, FIGI n/a (G18, G19, G28). HY block hidden if no HY rows.

**Company profile** (CP-1A; collapsed). Ticker CZR; CEO Thomas R. Reeg, CFO Bret Yunker; Sponsor Quality Medium (illustrative); issue ratings B1/BB-; Morningstar Issuer ID n/a (G24); corporate ratings n/a (G25, G10); outlooks n/a (G11).

**Transaction summary and new debt issues** (Primary only; collapsed). Base `illustrative.transactionSummary`: US$31.00 in cash per share, about US$17.6bn including about US$11.9bn assumed debt, new committed debt from 10 banks. The new-debt table (tranche size, price talk, OID, maturity, expected ratings, CR Score) is **n/a**, G8.

**Valuation per instrument** (CP-3). Base `illustrative.byInstrument`, FP `blocks.instrumentLevels`: Valuation V2 on the secured 2032s, V4 on the unsecured; no level for the rest (G18).

**Portfolio Fit** (FIT, synthetic). FP `fit.instruments`, `charts.fig-fit-limits` (one bullet per binding limit); shown when portfolios attach.

**Committee challenge** (CP-6; illustrative). Three questions: do the secured 2032s hold value if the merger adds unknown debt (G8); is Las Vegas Adjusted EBITDA falling to 410 from 469 cyclical or structural; do the GLPI and VICI obligations of 13,157 belong in leverage.

## 4. First viewport priority

The call (three Strategy Recommendations, Valuation, Credit Score, Direction, the Fit line, the Instrument line); key findings with the main risk; company and operating model; the chart strip.

## 5. Page-specific states

- **What changed since the last Report**: not shown, no Prior Case accepted (condition: Prior Case accepted).
- Primary run: transaction summary shown; new debt n/a (G8). For a non-Primary run it is replaced by "Transaction summary: not a Primary run".

## 6. Module views behind it

Six modules in v1 (Report A): CP-0 Source readiness; CP-1 Financial analysis and capital structure; CP-1B Earnings delta; CP-2 Forecast, liquidity and cash flow; CP-3 Credit score and relative value; CP-4 Documentation and covenants (base `modules`; names as served in the base set, CP-5 folded into Evidence, CP-6 into Portfolio Fit). The full scope has 17 (see `00-app-shell.md`). Each block links to its owning module's view.

## 7. Real CAOS output

The live Full Credit Assessment run of 6 October 2026 (`data/caos-runs/full-credit-assessment-2026-10-06/`) completed 17 modules and stopped before CP-5 and CP-6, so it produced no Recommendation per Strategy, no Valuation and no instrument call: its CP-3 (confidence 44) marks no security Preferred, and every module is With limitations. CP-2 calls the profile "adequate but cyclical", with liquidity "Average". Use its findings and headlines in the module views and key findings; the Snapshot's call band would, in a real run of this state, show the Recommendation as not yet produced. Design both: the illustrative full call and that honest state.
