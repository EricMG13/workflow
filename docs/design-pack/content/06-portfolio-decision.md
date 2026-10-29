# Portfolio Decision: Front Page content

## 1. Purpose

Question: **should each portfolio own it, how much, and which instrument?** A PM uses it to read the Recommendation per Strategy, then per portfolio after the Portfolio Fit cap, with the size and the binding limit. Data: `data/front-pages-data.json` (FP) and `data/rbot-data-base.json` (base). Caesars (CZR), Q2 2026. The only attached portfolio is **Test CLO I, synthetic**. All judgements are **illustrative**.

## 2. The call

Title: "Portfolio decision".

| Item | Value |
|---|---|
| CLO / Indexed Loans / Indexed HY | 3 - MW / 3 - MW / 2 - Modest OW (illustrative, base `illustrative.recommendation`) |
| Test CLO I final Recommendation | 2 - Modest OW for the proposed instrument, sub-line "Secured 2032s, Fits, no cap" (illustrative; `fit.instruments[3]`) |
| Valuation | V2 - Attractive (illustrative) |
| Credit Score | 3 - Fair (illustrative) |

One-line facts:
- **Test CLO I** (synthetic): proposed US$5,000,000 par of the 6.50% secured 2032s (0.7925% of NAV, `fit.proposed`): Fits, max US$15,773,213 under C-01. Loans and unrated notes: Watch, max US$883,300 under C-04, because no issue rating is in the sources (G35).
- **Other books**: Indexed Loans and Indexed HY have no portfolio attached; Fit not run.

## 3. Blocks (page order)

**Portfolio recommendation** (CP-6). One row per portfolio and instrument: portfolio, Strategy, instrument, uncapped Recommendation, cap, final Recommendation, verdict. From `fit.instruments`: 6.50% SSN 2032 uncapped Modest OW, no cap, final Modest OW, Fits; Term Loan B, Term Loan B-1 and 7.00% SSN 2030 uncapped MW, cap 3 - MW, final MW, Watch; 4.625% SN 2029 and 6.00% SN 2032 uncapped Modest UW, cap 3 - MW, final Modest UW, Watch. Rule (`fit.rule`): Breaches caps at Avoid, Watch caps at 3 - MW, Fits does not cap; final is the weaker of the uncapped call and the cap. Uncapped and final calls illustrative; verdict and cap calculated on synthetic limits. Revolver, Term A, CVA DDTL, SID bonds and other payables: "Not evaluated: bank or other facility" (`fit.notEvaluated`).

**Portfolio Fit** (FIT). Chart `charts.fig-fit-limits` (bullet, % NAV; synthetic): C-01 single issuer (Caesars exposure none), limit 2.5, current 0, headroom 2.50; Leisure Facilities & Services sector, limit 10.0, current 4.57, headroom 5.43; C-04 CCC bucket, limit 7.5, current 7.36, headroom 0.14 (binds unrated instruments); C-05 Unrated, limit 5.0, current 3.73, headroom 1.27. Table twin: `fit.limits` (also C-10 second lien and unsecured, headroom 9.39). Per instrument: verdict, max size, binding limit. Portfolio facts: Test CLO I Ltd, NAV US$630,928,502, one percent of NAV 6,309,285 (`fit.portfolio`). Caveat chips: the workbook NAV and compliance check are dated 29 May 2026, the price 1 October 2026 (S50); the CLO indenture 7.11 is its own indenture, not the Caesars notes indenture (S51); bond eligibility unconfirmed (G40).

**Instrument decision** (CP-3, CP-6). `blocks.instrumentLevels`, `blocks.securityPreference`, Recommendation per instrument: 6.50% SSN 2032 at 93.28, 8.063520%, V2 Attractive, Preferred; 6.00% SN 2032 at 84.94, 9.318398%, V4 Unattractive, Avoid; term loans and 7.00% SSN 2030 no level (G18). Levels cited (TRACE last trade); Valuation, preference, Recommendation illustrative.

**Capital structure** (Model). Base `tables.capitalStructure`: senior secured 9,468 (2.64x), unsecured 2,300 (3.28x), total debt 11,807 (3.29x), cash 965, net debt 10,842, EV 17,600 (4.90x), GLPI and VICI obligations 13,157 shown apart. Pro forma interest n/a (G21).

**Strengths and weaknesses** (CP-2). Credit view line (Score 3 Fair, Direction Deteriorating, Sector Outlook Neutral, Sponsor Quality Medium; illustrative) above the model-written lists (base `illustrative.strengths`, `weaknesses`): four each, e.g. strength "LTM Adjusted EBITDA of 3,592 on net revenues of 11,648"; weakness "The committed debt financing has no stated amount". Figures inside stay clickable to their sources.

**Thesis, catalysts and challenge** (CP-6). Base `illustrative.thesis`, `illustrative.catalysts` (go-shop ended 11 July 2026; End Date 27 May 2027, extendable to 27 August and 27 November 2027; ticking fee from 26 June 2027; disclosure of the committed financing), and `blocks.challenge` (three claims, counter-evidence, resolution, what would change the view). Model-written, illustrative.

**Limitations that bind the decision** (CP-5). `blocks.bindingLimitations`: merger debt (G8); loan prices (G18); issue ratings (G35: the loans count as Unrated in the CCC bucket, which sets the 0.14% headroom); spreads (G19); bond eligibility (G40). Each: effect on the decision and the source that would lift it.

## 4. First viewport priority

The call (three Strategies, the Test CLO I final Recommendation, Valuation, Credit Score and the two lines); the per-portfolio table; the Fit bullets.

## 5. Page-specific states

- **What changed since the last Report**: not shown, no Prior Case accepted.
- Portfolio Fit **is** in this Pathway; a run with no attached portfolio would show it as absent with the reason.
- Strategies without a portfolio: "Fit not run".
- The capped final may differ from the uncapped call; show both and the cap's source limit.

## 6. Module views behind it

CP-0, CP-1, CP-1A, CP-1D, CP-2 as in Covenant & Refinancing; CP-2A Downside paths: downside paths, risk matrix; CP-4 Covenants and legal: covenant tests, red flags, capacity; CP-3D Market-implied risk: observations, spread curve, market against fundamentals; CP-3 Relative value: levels, compensation, preference, recommendation per instrument. Folded: CP-6 (portfolio recommendation, thesis challenge) into Portfolio Fit; CP-5 (binding limitations) into Evidence. Nine modules, order in FP `pathways.PORTFOLIO_DECISION.nav`.

## 7. Real data notes

No CP-6 (decision) output exists from any real run; the live portfolio screen of 6 October 2026 (`data/caos-runs/lite-portfolio-screen-2026-10-06/`) concludes **"MIXED", Full upgrade required**. A real fund now in the corpus, the Federated Hermes Sustainable High Yield Bond Fund, holds four Caesars positions at 30 June 2026 (US$2.9m of value across the 6.000% 2032, 6.500% 2032 secured, 7.000% 2030 secured and 4.625% 2029 notes; net assets US$491.6m; `data/README.md`). It carries no single-name limit or compliance monitor, so Fit arithmetic stays on the synthetic Test CLO I; the page may show the real fund as an existing holder alongside it.
