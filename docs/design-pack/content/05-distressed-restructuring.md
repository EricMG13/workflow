# Distressed & Restructuring: Front Page content

## 1. Purpose

Question: **is the distress gate met, which path and fulcrum are most credible, and what recoveries follow?** A PM uses it to see where value breaks and which instrument to hold; an analyst checks the claims, scenarios and paths. Data: `data/front-pages-data.json` (FP). Caesars (CZR), Q2 2026. Every gate status, multiple and recovery below the merger value is **illustrative**; recoveries are calculated from illustrative multiples, so they are illustrative too.

## 2. The call

Title: "Distress view and recommendation".

| Item | Value |
|---|---|
| Distress gate | Unclear (steps Not met, Unclear, Met; illustrative) |
| CLO / Indexed Loans / Indexed HY | 3 - MW / 3 - MW / 2 - Modest OW (illustrative) |
| Credit Score | 3 - Fair (illustrative) |

One-line facts:
- **Fulcrum**: senior unsecured in the 5.0x downside (72.9% recovery); senior secured in the 4.0x stress (94.2%); none at the merger value (`calcs.K205`, `K211`).
- **Instrument**: prefer the 6.50% secured 2032s; avoid the unsecured notes (illustrative).
- **Portfolio Fit**: Test CLO I, synthetic (`fit`): proposed US$5,000,000 of the secured 2032s Fits, max US$15,773,213 under C-01; loans and unrated notes Watch, max US$883,300 under C-04.

## 3. Blocks (page order)

**Distress gate** (CP-4C). `blocks.distressGate`: six triggers with evidence and status, then Overall. Market prices debt at distressed levels: unsecured 2032s at 84.94, yield 9.318398%: Not met. Rating in Caa or below: Caa1, rated 28 Sep 2026: **Met**. Liquidity runway under 12 months: 13.5 months (12 months from 30 June 2026, lease payments included): Not met. Maturity within 24 months without a path: next large maturity 2028, US$767m: Not met. Leverage after the merger debt: unstated (G8): Unclear. Missed payment, covenant breach or LME: none in the sources: Not met. Overall: Unclear. Evidence cited or calculated; statuses illustrative.

**Recoveries** (CP-4C). `blocks.evScenarios` then `blocks.recoveries`, chart `charts.fig-recovery-by-class` (columns, %; Merger value, Downside 5.0x, Stress 4.0x; illustrative bars for the last two). Scenarios, EBITDA after rent 2,229: Merger value EV 17,600 (7.90x, from the cited transaction value); Downside EV 11,145 (5.0x illustrative); Stress EV 8,916 (4.0x illustrative). Recovery by class: Merger value 100.0 / 100.0 / 100.0 (secured, unsecured, other); Downside 100.0 / 72.9 / 0.0; Stress 94.2 / 0.0 / 0.0. Fulcrum Yes: unsecured (Downside), secured (Stress). Residual to equity 5,793 at the merger value. Value allocation waterfalls per scenario: `charts.fig-value-allocation-merger`, `-downside`, `-stress` (EV, then per-class allocation, then residual). The strip names the gate: it is shown because the gate is Unclear. Lease claims excluded (G38). Hidden if the gate is Not met, replaced by "Recoveries: not shown, the distress gate is Not met".

**Claims** (CP-4C). `blocks.claims` (US$ m): senior secured 9,468 (CEI and CVA, rank 1; CVA a separate borrower treated pari); senior unsecured 2,300 (rank 2); other debt 39 (priority not stated, ranked last); lease financing obligations 13,157, excluded (G38). Cited or calculated.

**Liquidity runway** (CP-2D). `blocks.runway` with `charts.fig-liquidity-bridge`: 2,928 opening (12 months from 30 June 2026, lease payments included), mandatory uses 2,601, headroom 327, 13.5 months, 3,348 closing at 30 June 2027 before refinancing (operating cash flow held at the LTM level of 3,436, an assumption; G13).

**Funding gap and LME capacity** (CP-3C). `charts.fig-funding-gap`, `blocks.maturityPressure` (liquidity left turns to (138) in 2028), `blocks.lmeCapacity`, `blocks.creditorExposure` (pari capacity 6,696; claims at or ahead of the unsecured notes 11,768 Base, 18,464 LME; Stress n/a, G8).

**Covenant levers** (CP-4). `charts.fig-covenant-headroom` (Total Leverage 3.02x against 6.50x; FCCR 4.63x against 2.00x; pari 2.64x against 4.50x) with a compact `blocks.redFlags` list (illustrative severity).

**Rating triggers** (CP-2H). `blocks.ratingTriggers`: current issue ratings cited (Moody's Caa1 and S&P B- on the unsecured; B1 and BB- on the secured); thresholds n/a (G31); status Not computable; the bullet chart is an **n/a frame** (no agency report in the Source Pack). `blocks.migrationView` (illustrative, confidence Low): downgrade if new debt ranks ahead of the unsecured notes, earliest at merger close.

**Restructuring paths** (CP-4C; illustrative). `blocks.restructuringPaths`: merger closes and new debt layered pari (out of court; High); amend-and-extend with secured lenders (Medium); distressed exchange of the unsecured notes (Low); Chapter 11 with master leases assumed (Low, G38). Each: process, consent, new money, class treatment, milestones, blockers.

**Instrument decision**. `blocks.instrumentLevels` (6.50% SSN 2032 at 93.28, 8.063520%; 6.00% SN 2032 at 84.94, 9.318398%; other levels n/a, G18, spreads n/a, G19), `blocks.securityPreference` (Preferred, Neutral, Requires more work, Avoid), Recommendation per instrument and Strategy.

**Portfolio Fit**. `fit.instruments` as in the call; synthetic.

## 4. First viewport priority

The call with the gate and the fulcrum line; the gate table with its six triggers; the recovery chart.

## 5. Page-specific states

- Gate Unclear: EV scenarios and recoveries appear (they are required when the gate is Met or Unclear).
- **What changed since the last Report**: not shown, no Prior Case accepted.
- Rating trigger bullets and stress-case exposure: n/a frames with reasons.
- Downside and stress rows carry the illustrative mark in every cell derived from the multiples.

## 6. Module views behind it

CP-0, CP-1, CP-1A, CP-1D, CP-2 as in Covenant & Refinancing; CP-2A Downside paths: `blocks.downsidePaths`, risk matrix; CP-4: covenant tests, red flags, capacity; CP-2D: liquidity sources, cash uses, runway; CP-2G Forecast cases: n/a frame; CP-2H Rating triggers: triggers, migration view; CP-3D Market-implied risk: observations, spread curve, implied risk, market against fundamentals; CP-3C: funding gap, LME capacity, refinancing paths, creditor exposure; CP-4C Recovery and fulcrum: distress gate, claims, EV scenarios, recoveries, value allocation (three waterfalls), restructuring paths; CP-3 Relative value: levels, compensation, preference, recommendation. Folded: CP-6, CP-5. Fourteen modules, order in FP `pathways.DISTRESSED_RESTRUCTURING.nav`.

## 7. Real CAOS output, and the conflict to design for

The real CP-4C outputs (`data/caos-runs/full-credit-assessment-2026-10-06/CP-4C.md`, `data/caos-runs/lite-screen-with-recovery-2026-10-05/CP-4C.md`) say **"Not Applicable: no named distress trigger"**; covenant compliance is reported at 30 June 2026, and no paths, valuation, waterfall or fulcrum were produced. The illustrative gate here is **Unclear** so the full page can be shown. Design both states: (a) the illustrative Unclear page as described above, and (b) the real Not met page, in which the EV, recovery and fulcrum block is replaced by its condition line and the page leads with the gate, liquidity runway and maturity pressure. No real distressed issuer has been run (the Spirit Airlines sets never ran).
