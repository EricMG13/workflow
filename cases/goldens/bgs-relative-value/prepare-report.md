# BGS relative_value golden: prepare report

Source: only the 10-Q for the quarter ended 2025-06-28, filed 2025-08-04 (the cutoff). Checker: `python3 -I cases/goldens/check.py cases/goldens/bgs-relative-value` exits 0 (re-run after fix round 1, along with `derive.py`).

## Coverage
- CP-0: legal name, ticker and exchange.
- CP-2: debt stack per instrument (revolver, Tranche B, 5.25% 2027 notes, 8.00% secured 2028 notes) at 2025-06-28: principal, carrying amount, maturity, coupon or margins, weighted average rates, ranking. Also revolver commitment, drawn, letters of credit, availability, cash, the maturity schedule, financial covenants and the Q2 note repurchase. Derived: sum of the four principals, and total principal less unamortized costs and discount (both match the printed totals; see `derive.py`).
- CP-3: fair value per instrument at 2025-06-28 and 2024-12-28 (Note 7), hierarchy level, and the Q2 repurchase price. Dated market quotes are `missing`.
- CP-3C: call, redemption, make-whole, equity clawback, change-of-control and prepayment terms.
- CP-3D: guarantors, collateral and priority per instrument.
- not_golden: CP-1 (financial_gold), CP-1C, CP-2D, CP-MODEL, CP-5.

## Period labelling
Fiscal quarters ending late December. context uses q2-2025 (2025-06-28) as current and q1-2025 as prior; the golden facts carry period_end dates, not period ids.

## Judgment calls
- Only the Q2 10-Q is cited; the December 28, 2024 comparatives come from it.
- Revolver commitment 475.0 (balance sheet date) and 430.0 (effective 2025-07-01, Note 18) are separate facts.
- Carrying amounts are taken from Note 7. Principal is the Note 6 face amount. Fair value is never a quote.
- Hierarchy level: only the revolver is tagged Level 2. The term loan and notes say "quoted market prices" with no level, so level is `missing`, not assumed.
- Facts printed in USD thousands carry scale `thousands`, values as printed (derived facts too); facts printed in millions carry `millions`. Ratios carry unit null.
- The open-market repurchase at 89.98% of principal is a transaction, kept under CP-3 `repurchase_transactions`, not a quote.
- Floors are `missing`: not disclosed in the corpus filings.
- context: peer_source is the form default `cp_dr_public` because no peers are supplied; basis stays `auto` because there is no market data to choose a basis from; sector "Consumer and retail" and country are my labels; guarantors left empty.

- Codex disagreement (BGS-R1): Codex's financial_gold marks `BGS:FY2025Q2:principal` missing ("do not disclose a complete outstanding-principal balance by instrument"), but Note 6 prints each instrument's face amount and a total of 2,011,375 (USD thousands). This golden carries those facts; the Codex gap should be reported upstream.
- Added in fix round 1: leverage covenant step-downs (7.25x from the quarter ending 2027-01-02; 7.00x from the quarters ending 2027-04-03), mandatory prepayment triggers under CP-3C, and ranking items (3) and (4) on the 8.00% notes priority fact.

## Open questions (needs_user_input)
quotes; valuation.peers; valuation.issuer_market; assumptions.cp2d, cp3c, cp3d; identity.guarantors; ratings.

## Limitations
Quotes keep zero-width spaces (U+200B) from the filing HTML. The credit agreement and indentures are not in the corpus.

Not verified: the 8-K or other documents behind the July 1, 2025 amendment; the four other corpus filings were not cross-read against these facts; no re-check against a live market.
