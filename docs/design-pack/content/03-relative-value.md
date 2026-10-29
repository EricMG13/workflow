# Relative Value: Front Page content

## 1. Purpose

Question: **which instrument is best compensated for its risk, and at what level?** A PM uses it to choose between the secured and unsecured notes and the loans; an analyst checks the levels and the compensation judgement. Data: `data/front-pages-data.json` (FP) and `data/rbot-data-base.json` (base). Caesars (CZR), Q2 2026.

## 2. The call

Title: "Analyst recommendation". Every judgement is **illustrative**.

| Item | Value |
|---|---|
| CLO | 3 - MW |
| Indexed Loans | 3 - MW |
| Indexed HY | 2 - Modest OW |
| Valuation | V2 - Attractive |
| Credit Score | 3 - Fair |
| Credit Direction | Deteriorating |

(Base `illustrative.recommendation`, `valuation`, `creditScore`, `creditDirection`.)

One-line facts:
- **Preferred**: the 6.50% secured 2032s at 93.28, yield 8.063520%: Preferred. The 6.00% unsecured 2032s at 84.94: Avoid, 1.25 pp more yield for a claim behind US$9,468m of secured debt (`calcs.K146`, `K57`; base `tables.trace`). Judgement words illustrative; prices and yields cited (last trade, FINRA TRACE, 1 October 2026, not a bid).
- **Portfolio Fit** (`fit`, synthetic Test CLO I): proposed US$5,000,000 of the secured 2032s Fits, max US$15,773,213 under C-01; loans and unrated notes Watch, max US$883,300 under C-04. Link: Details in Portfolio Fit.

## 3. Blocks (page order)

**Instrument levels** (CP-3). `blocks.instrumentLevels`: per facility, level basis, date, price, yield, spread, Valuation, Recommendation. Only the two TRACE notes have levels: 6.50% SSN 2032 at 93.28, 8.063520% (V2 Attractive, 2 Modest OW); 6.00% SN 2032 at 84.94, 9.318398% (V4 Unattractive, 4 Modest UW). Every other row: price, yield, date n/a (G18); every spread n/a (G19). Valuation and Recommendation illustrative; talk rows only for a Primary run with a stated talk (none: new debt unstated, G8). Eleven rows; the table must take more.

**Spread against maturity** (CP-3D). Base `charts.yieldCurve` (scatter, yield % against maturity; CZR secured 8.063520, CZR unsecured 9.318398, MGM 6.125% 2029 at 6.722997, PENN 4.125% 2029 at 6.644415). Spreads are n/a (G19), so the plot is yield to maturity. Table twin: `tables.trace`.

**Compensation against risk; security preference** (CP-3; illustrative). `blocks.compensation` and `blocks.securityPreference`: 6.50% SSN 2032 rank 1, Attractive, Preferred; 6.00% SN 2032 rank 2, recovery sensitivity High, Inadequate, Avoid; term loans Unclear / Requires more work (G18); 7.00% SSN 2030 Neutral; 4.625% SN 2029 Avoid. Each preference has a key reason and monitoring trigger.

**Market against fundamentals** (CP-3D; illustrative alignment). `blocks.marketVsFundamental`: unsecured priced for distress against net leverage 3.02x: Divergent (market prices the unstated merger debt, G8); secured below par at 93.28 against secured leverage 2.64x: Aligned. Market-implied default is **n/a** (G37: needs spreads and a recovery assumption) with an n/a frame in the module view.

**Peer positioning** (CP-1C). Base `charts.peerRange` (range strip): Adjusted EBITDA margin CZR 30.7% against MGM 13.7% and PENN 16.8% (`K71`, `K69`, `K70`); revenue growth 3.0% in a range 1.0 to 5.2; TRACE yield range 6.644415 to 9.318398. Peers are partial comparables (illustrative), EBITDAR definitions differ (G14). Peer set: `blocks.peerSet`.

**Capital structure** (Model). Base `tables.capitalStructure` at 30 June 2026: senior secured 9,468 (2.64x, 53.8% EV), unsecured 2,300 (3.28x, 66.9%), other 39, total debt 11,807 (3.29x, 67.1%), cash 965, net debt 10,842, EV 17,600 at the merger value, 4.90x. Financing obligations to GLPI and VICI of 13,157 are shown apart from debt. Pro forma interest n/a (G21); equity market value n/a (G27).

**Loan and high-yield relative value** (CP-3; collapsed). Base `tables.trace`, capital-structure loan rows; index statistics, peer loan marks, FIGI and OAS all n/a (G18, G19, G28). The HY block is hidden if there are no HY rows.

**Recommendation per instrument** (CP-6). Base `illustrative.byInstrument`: 6.50% SSN 2032 Modest OW; 7.00% SSN 2030, Term Loan B, B-1 MW; both unsecured notes Modest UW; revolver, Term A, CVA DDTL, SID bonds, other payables N/A. Rationale per row is model-written.

**Portfolio Fit** (`fit.instruments`): per instrument, verdict, max size, binding limit. Secured 2032s: Fits, US$15,773,213, C-01. Loans, 7.00% 2030 notes, 4.625% 2029 and 6.00% 2032 notes: Watch, US$883,300, C-04 (CCC bucket; no issue rating in the sources, G35), capped at 3 - MW. Revolver, Term A, DDTL, SID bonds, payables: "Not evaluated: bank or other facility". The proposed bond's CLO eligibility is unconfirmed (G40). Synthetic.

**Credit view line** (collapsed). Credit Score 3, Direction Deteriorating, Sector Outlook Neutral, Sponsor Quality Medium (illustrative); issue ratings B1/BB- and Caa1/B-; sector, country, issuer ratings n/a.

## 4. First viewport priority

The call with its Preferred line and Fit line; the instrument levels table; the yield chart.

## 5. Page-specific states

- **What changed since the last Report**: not shown, no Prior Case accepted.
- Loans carry no level: shown as n/a with G18, never zero.
- Forecast cases (CP-2G) show an n/a frame in the module view (no guidance, no rate deck, G13, G30).

## 6. Module views behind it

CP-0, CP-1, CP-1A as in Earnings Update; CP-1D (no add-back assessment); CP-1C Peer benchmark: peer set, peer positioning; CP-2 Credit synthesis: credit view, strengths and weaknesses; CP-2A Downside paths: `blocks.downsidePaths`, risk matrix (base `charts.risk`); CP-4 Covenants and legal: covenant tests, red flags, capacity; CP-2G Forecast cases: n/a frame with reasons; CP-3D Market-implied risk: observations, spread curve, implied risk (n/a frame), market against fundamentals; CP-3 Relative value: levels, compensation, preference, RV blocks, recommendation per instrument. Folded: CP-6 (portfolio recommendation, thesis challenge) and CP-5. 11 modules, plan order in FP `pathways.RELATIVE_VALUE.nav`.

## 7. Real CAOS output

The live Relative Value run of 12 October 2026 (`data/caos-runs/relative-value-2026-10-12/`) concluded **"Requires More Work" for both priced 2032 bonds; relative value "Unclear"; fundamental score "Not Scorable"** (no factor weights), citing the same TRACE levels (93.28 / 8.063520% secured; 84.94 / 9.318398% unsecured). The illustrative "Preferred / Avoid" call in this doc is a design placeholder; design the honest state too, in which the call band says the preference is not yet established and why.
