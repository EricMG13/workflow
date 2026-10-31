# IHRT goldens prepare report (ihrt-distressed-restructuring)

Cutoff and as_of 2024-12-23. Sources: five 10-K/10-Q filings (only Q3 2024 10-Q and FY2023 10-K cited), exchange 8-K, closing release (Ex. 99.1), new credit agreement (Ex. 10.2). No other source used.

## Coverage
- CP-0 (6 facts): registrant, ticker, borrower, Holdings/parent guarantor, fiscal year.
- CP-1A (4): business, transaction, stated effects.
- CP-2 (64): pre-exchange stack at 2024-09-30 per instrument (principal in USD thousands, maturity, coupon/margin, ranking), carrying vs principal vs market value kept apart, cash, ABL size/LCs/availability/liquidity, new-instrument terms.
- CP-4 (60): exchange pairs (principal exchanged, participation, new principal, cash), dates, TSA support, credit-agreement terms (borrower, Holdings, guarantors, closing, commitment vs 8-K funded principal, maturity, amortisation, pricing grid, floors, Section 7.11 maturity-tested leverage covenant), derived totals and exchange ratios.
- CP-4C (14 known, 2 missing): lien classes after the exchange, remnant principal per old instrument (credit-agreement definitions), intercreditor positions.
- CP-2H (1 known, 2 missing): no agency rating disclosed; rating-linked pricing triggers recorded.
- not_golden: CP-1 (financial_gold), CP-2A, CP-2G, CP-5.

## Period labelling
Calendar fiscal year. context.json uses q3-2024 (current), q2-2024 (prior); the financial_gold ids FY2023Q4, FY2024Q1-Q3, FY2023 map to q4-2023, q1..q3-2024, fy-2023.

## Judgment calls
- Pre-exchange ranking and maturities come from the FY2023 10-K (pre-cutoff); the Q3 10-Q gives balances only.
- Exhibit index says Second Lien Notes "due 2029"; body and release say 2030. Used 2030 (explicit date), noted as limitation.
- Remnant principals use the new credit agreement definitions (units); the Existing Term Loan remnant is not stated, so `TLremainDisclosed` stays missing; an approximate remnant (6.552 millions) is derived separately.
- 2028 notes' post-exchange lien rank is not stated: missing.
- Market value of debt printed as "$3.9 billion": stored as 3.9, scale billions.
- Derived facts may mix scales; derive.py converts operands to units like check.py.
- Section 7.11 recorded as a maturity-tested leverage covenant; whether the Repurchase Trigger has occurred (2028 notes only 44.6% exchanged) is not asserted.
- context: basis "auto", peers default, valuation market fields empty (listed issuer; user must supply).

## Fix round 1 (review IHRT-R1..R5, controller G-7)
- R1: `springing_trigger_availability_floor` replaced by `..._fixed_component` (40.0 millions), `..._pct_of_commitments_component` (10 percent) and `..._rule` (text, greater-of quote). No effective-floor derived fact: check.py reads a percent operand as 10 (scale null), so product(450.0, 10) would give 4500, not 45.0.
- G-7: market value is decimal 3.9 billions. Added `participation_pct_recomputed` (five instruments, 2 dp, plus total 92.21), `CP-4C...TLN.principal_outstanding_derived` (6.552 millions, approximate), `CP-4C...AllFive.principal_outstanding_derived` (407.434767 millions), `CP-4.exchange_total.ProForma.principal_total_rolled_forward` (4790.876 millions, gross principal at 2024-09-30 less the exchange reduction only). derive.py rewritten to unit conversion and percent ratios; default path now beside the script.
- R2: `N8375_2027.ranking` quote extended with the "(including the 6.375% ... Term Loan Facility)" text; one occurrence in the 10-K, at offset 306925 (section starts 305805).
- R3: `announcement_and_8k_filing_date` split into `8k_filing_date` (2024-12-23, signature date) and `press_release_date` (conflicting: release dateline December 23 vs 8-K Item 8.01 "On the Settlement Date" = December 20).
- R4: `identity.sector` is now "audio media company". Source wording: "iHeartMedia is the number one audio media company in the U.S. based on consumer reach" (10-K Item 1).
- R5: `Rem2028Class.lien_rank` stays missing; gap_reason cites credit agreement Section 2.05(b).

## Open questions (needs_user_input)
ratings; valuation.issuer_market; assumptions.cp4c.ev_multiple; assumptions.cp2a; research_questions.

## Checks
`python3 -I cases/goldens/check.py cases/goldens/ihrt-distressed-restructuring` exits 0. derive.py exits 0 (0 mismatches).

Not verified: the effective ABL floor (45.0 millions) is not a fact; derived percentages and the rolled-forward total rest on 2024-09-30 balances and the 8-K's approximate amounts; quotes are checked against the checker's visible text, not against the rendered filings; no second-person review of values; Section 7.11 and rating-grid readings were not checked against the full credit agreement exhibits (omitted); no financial_gold cross-agreement check of period labels beyond ids.
