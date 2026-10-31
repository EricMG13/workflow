# NATL portfolio_decision golden: prepare report

Case `natl-portfolio-decision`; cutoff and as_of 2025-11-06; preparer: mx-feature (Sonnet).

## Coverage
- CP-1 (restatement text only; history is in financial_gold): 15 known. Nature, causes, periods revised, Q1/Q2 2025 not yet revised, material weakness, line items affected (income statement, balance sheet, debt items), cash-flow effect, clawback.
- CP-2 (debt stack and liquidity at 2025-09-30): 46 known (8 derived by derive.py), 6 missing. Per-tranche outstanding (A-1, A-2, B) and per-instrument carrying amounts (term loans, notes) are missing; the Subsidiary Guarantor names are missing.
- CP-4 terms (Exhibit 10.1 and Q3 10-Q): 48 known, 3 missing. Dates, maturities, Term B margins, the Term A/revolver grid (5 levels), amortization, covenant levels, covenant definition. Missing: pricing level, achieved ratio and compliance at 2025-09-30, and the revolver commitment per the agreement text.
- CP-3: no facts; quotes are user input. CP-0, CP-1 (values), CP-MODEL, CP-5, CP-6, CP-8 are in `not_golden`.

## Period labelling
Calendar fiscal year. Context uses q3-2025 (current) and q2-2025 (prior); fiscal years are fy-YYYY.

## Judgment calls
- The restatement is tagged module CP-1, topic `restatement`, as text facts only; values stay in financial_gold.
- Exhibit 10.1 is a refinancing agreement with an attached conformed credit agreement. Its extracted text merges deleted and added wording, so only self-identifying post-amendment clauses were quoted. The effective date comes from the defined term "2025 Refinancing Facility Effective Date".
- Term B at 2025-09-30: the 10-Q gives only the aggregate term loan outstanding (1,334). The New Term B commitment (320,000,000, scale units) is recorded as a commitment, not as a balance.
- Revolver commitment 600 comes from the 10-Q; the agreement text does not print it, so that fact is missing for the agreement.
- Principal and carrying amounts are kept apart: 2,912 principal vs 2,869 carrying (derived difference 43 equals the printed discount and fees).
- Sector set to "Technology" (the filings say financial technology); free text, change if preferred.
- `valuation` keeps the form defaults (cp_dr_public, auto) with empty issuer_market; ratings left empty.

## Open questions
See `needs_user_input` in module_golden.json: prior_case, portfolio_workbook, quotes, valuation.issuer_market, ratings, guarantors, assumptions.

## Checks
`python3 -I cases/goldens/check.py cases/goldens/natl-portfolio-decision` exit 0; `python3 -I derive.py` exit 0.

Not verified: no model run against these goldens; the choice of post-amendment clauses in Exhibit 10.1 rests on reading the merged text, not the strike/underline markup; Q1/Q2 2025 and Q3 2024 10-Qs were not mined for module facts; the sector label is my own classification; no other source corroborates the figures.
