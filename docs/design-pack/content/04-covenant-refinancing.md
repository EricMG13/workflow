# Covenant & Refinancing: Front Page content

## 1. Purpose

Question: **which provisions protect creditors, and can the issuer refinance?** A credit research analyst reads it for the document stack, the tests and the maturity profile; a PM reads the call for how exposed lenders are to the merger. Data: `data/front-pages-data.json` (FP); base set `data/rbot-data-base.json` (base). Caesars (CZR), Q2 2026, a Primary run (Fertitta merger financing).

## 2. The call

Title: "Covenant and refinancing view". Judgements **illustrative** except the covenant status, which is calculated.

| Item | Value |
|---|---|
| Credit Score | 3 - Fair (illustrative) |
| Covenant tests | Headroom, "Maintenance, 2 tests" (calculated, not illustrative; `illustrative.callBand.covenantTests`) |
| Lender protection | 2 of 5 (illustrative; weakest area of the protection score) |
| Refinancing pressure | High (illustrative; highest year of the maturity pressure table) |
| Credit Direction | Deteriorating (illustrative) |

One-line facts:
- **Covenants**: Total Leverage 3.02x against a 6.50x ceiling; FCCR 4.63x against a 2.00x floor; tested for the revolver and Term A only, Term B-1 has no maintenance test. Ratios are on RBOT's basis (G34).
- **Liquidity**: US$2,928m against mandatory uses of US$2,601m over 12 months from 30 June 2026, lease payments included: 13.5 months; the revolver matures 31 January 2028.
- **New tranches**: merger debt unstated; CR Score n/a (G39, G8).
- The Pathway produces **no Recommendation, no Valuation and no Portfolio Fit** (it runs no CP-3, CP-6 or Fit): it describes protection and refinancing capacity, not whether to own.

## 3. Blocks (page order)

**Covenant tests and headroom** (CP-4). `blocks.covenantTests` with `charts.fig-covenant-headroom` (bullet, unit x, ceilings and floors, current against threshold). Rows, threshold / current / headroom: Total Leverage Ratio (maintenance, ceiling) 6.50 / 3.02 / 3.48; Fixed Charge Coverage Ratio (maintenance, floor) 2.00 / 4.63 / 2.63; Pari secured incremental (incurrence, ceiling) 4.50 / 2.64 / 1.86; Ratio debt, 2032 indenture (incurrence, floor) 2.00 / 4.63 / 2.63. Thresholds cited, currents and headroom calculated; status Headroom (rule: Breached below zero, Tight under 10% of threshold). Note under it: maintenance tests spring after Term A is repaid only when revolver use exceeds 25% of commitments; use is 5.3%.

**Liquidity runway** (CP-2D). `blocks.runway`, `blocks.liquiditySources`, `blocks.cashUses`; chart `charts.fig-liquidity-bridge` (waterfall US$ m): opening 2,928 (30 June 2026); operating cash flow before cash interest and rent at the LTM level 3,436 (an assumption, not a forecast; G13); then the uses over the 12 months from 30 June 2026, lease payments included: debt service H2 2026 (425); interest H1 2027 (375); maturities H1 2027 (57); lease payments H2 2026 (687) and H1 2027 (682); maintenance capex H2 2026 (185) and H1 2027 (190); growth and digital capex H2 2026 (205) and H1 2027 (210); closing 3,348 at 30 June 2027 before refinancing. First-half 2027 rows are straight-line halves of FY2027 estimates; 2027 capex is a synthetic test value (G29). Runway rows: mandatory uses 2,601, headroom 327, months 13.5. Pinch point: 31 January 2028, the CEI revolver (net capacity 2,130, 72.7% of liquidity).

**Maturity wall and capital structure** (Model). Base `charts.maturityWall` (stacked by rank, US$ m: 2028 RCF 120, Term A 619; 2029 CVA DDTL 376, unsecured 1,200; 2030 Term B 2,018, secured notes 2,000; 2031 Term B-1 2,835; 2032 secured 1,500, unsecured 1,100; 2037 other 38) with the capital structure summary (total debt 11,807, 3.29x; EV 17,600).

**Funding gap** (CP-3C). `charts.fig-funding-gap` (columns) and `blocks.maturityPressure`: Maturing 55 / 114 / 767 / 1,574 / 3,962 / 5,335 (2026 rest to Thereafter); liquidity left before refinancing 2,873 / 2,759 / (138) / (1,712) / (5,674) / (11,009); pressure Low, Low, High, High, High, Medium (illustrative). Calculated, before operating cash flow.

**Capacity** (CP-4). `charts.fig-basket-capacity` (stacked: used, remaining) and `blocks.capacity`: pari secured to 4.50x, used 9,468, remaining 6,696; junior secured to 4.75x, remaining 7,594 (an alternative, not additive); free-and-clear size 3,592, used and remaining n/a (G33); unsecured ratio debt n/a (G21); restricted payments n/a (G32). Severity illustrative.

**Red flags** (CP-4). `blocks.redFlags`: seven provisions with illustrative severity (Term B-1 Non-Covenant Facility High; springing tests Medium; asset-sale sweep ends at 3.00x or below High, Caesars at 2.64x; equity cure Medium; pro forma synergies Medium; pari capacity 6,696 could rank ahead of the unsecured notes High). Last row is protective: change of control put at 101% on the 2032 secured notes (Low).

**EBITDA definition; protection score** (CP-4). `blocks.ebitdaDefinition` (cited clauses, capacity effect); `blocks.protectionScore` (illustrative five-point: maintenance covenants 2, debt and lien capacity 2, change of control 4, asset-sale protection 2, disclosure 3).

**Refinancing paths, LME capacity, creditor exposure** (CP-3C). `blocks.refinancingPaths` (merger closes with committed financing: High; revolver and Term A extended before 2028: Medium; Term Loan B amend-and-extend: Medium; unsecured exchange into secured: Low; all illustrative); `blocks.lmeCapacity` (five indicators; drop-down capacity Unclear, G32); `blocks.creditorExposure` with `charts.fig-lme-exposure` (claims at or ahead, Base to LME: secured 9,468 to 16,164; unsecured 11,768 to 18,464; Stress rows n/a, G8).

**Document register** and **structure map** (CP-4; collapsed). `blocks.documentRegister` (eight documents, dates cited; the Merger Agreement is "Signed, pending close"; parties mostly n/a, tagged G36); `blocks.structureMap` (restricted and guarantor columns n/a, G36).

## 4. First viewport priority

The call; the covenant bullets with the springing note; the liquidity bridge with the runway rows.

## 5. Page-specific states

- **What changed since the last Report**: not shown, no Prior Case accepted.
- **Portfolio Fit and Recommendation**: absent in this Pathway, shown as such.
- CR Score per new tranche: n/a with G39 (Primary run, tranches unstated).

## 6. Module views behind it

CP-0, CP-1, CP-1A, CP-1D as in Earnings Update; CP-2 Credit synthesis: credit view, strengths and weaknesses; CP-4 Covenants and legal: document register, covenant tests, capacity, structure map, red flags, EBITDA definition, protection score; CP-2D Liquidity bridge: liquidity sources, cash uses, runway; CP-3C Refinancing and LME: funding gap, LME capacity, refinancing paths, creditor exposure. Eight modules, order in FP `pathways.COVENANT_REFINANCING.nav`.

## 7. Real CAOS output

The live Covenant & Refinancing run of 5 October 2026 (`data/caos-runs/covenant-refinancing-2026-10-05/`: CP-0, 1, 2, 2D, 3C, 4, 5) and the Full Credit Assessment's CP-4 give real legal and refinancing text. CP-4's overall lender-protection score is **4 (negative)**: debt and lien capacity, restricted payment and investment leakage, and no maintenance test on the notes are the most creditor-adverse areas, which matches this doc's red flags. Prefer its wording for the red flags and protection areas.
