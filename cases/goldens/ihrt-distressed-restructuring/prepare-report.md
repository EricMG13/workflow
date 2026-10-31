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
- Remnant principals use the new credit agreement definitions (units); the Existing Term Loan remnant is not stated and not derived (mixed scales), so it is missing.
- 2028 notes' post-exchange lien rank is not stated: missing.
- Market value of debt printed as "$3.9 billion": stored as text (no billions scale).
- Derived facts only over same-scale operands (checker does not rescale); participation recompute and combined post-exchange total therefore omitted.
- Section 7.11 recorded as a maturity-tested leverage covenant; whether the Repurchase Trigger has occurred (2028 notes only 44.6% exchanged) is not asserted.
- context: basis "auto", peers default, valuation market fields empty (listed issuer; user must supply).

## Open questions (needs_user_input)
ratings; valuation.issuer_market; assumptions.cp4c.ev_multiple; assumptions.cp2a; research_questions.

## Checks
`python3 -I cases/goldens/check.py cases/goldens/ihrt-distressed-restructuring` exits 0. derive.py exits 0 (0 mismatches).

Not verified: quotes are checked against the checker's visible text, not against the rendered filings; no second-person review of values; Section 7.11 and rating-grid readings were not checked against the full credit agreement exhibits (omitted); no financial_gold cross-agreement check of period labels beyond ids.
