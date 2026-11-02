# NATL portfolio_decision golden: prepare report

Case `natl-portfolio-decision`; cutoff and as_of 2025-11-06; preparer: mx-feature (Sonnet).

## Coverage
- CP-1 (restatement text only; history is in financial_gold): 15 known. Nature, causes, periods revised, Q1/Q2 2025 not yet revised, material weakness, line items affected (income statement, balance sheet, debt items), cash-flow effect, clawback.
- CP-2 (debt stack and liquidity at 2025-09-30): 46 known (8 derived by derive.py), 6 missing. Per-tranche outstanding (A-1, A-2, B) and per-instrument carrying amounts (term loans, notes) are missing; the Subsidiary Guarantor names are known (see Fix round 1).
- CP-4 terms (Exhibit 10.1 and Q3 10-Q): 48 known, 3 missing. Dates, maturities, Term B margins, the Term A/revolver grid (5 levels), amortization, covenant levels, covenant definition. Missing: pricing level, achieved ratio and compliance at 2025-09-30, and the revolver commitment per the agreement text.
- CP-3: no facts; quotes are user input. CP-1 (values), CP-MODEL, CP-5, CP-6, CP-8 are in `not_golden`.

## Period labelling
Calendar fiscal year. Context uses q3-2025 (current) and q2-2025 (prior); fiscal years are fy-YYYY.

## Judgment calls
- The restatement is tagged module CP-1, topic `restatement`, as text facts only; values stay in financial_gold.
- Exhibit 10.1 is a refinancing agreement with an attached conformed credit agreement. Its extracted text merges deleted and added wording, so only self-identifying post-amendment clauses were quoted. The effective date comes from the defined term "2025 Refinancing Facility Effective Date".
- Term B at 2025-09-30: the 10-Q gives only the aggregate term loan outstanding (1,334). The New Term B commitment (320,000,000, scale units) is recorded as a commitment, not as a balance.
- Revolver commitment 600 comes from the 10-Q; the agreement text does not print it, so that fact is missing for the agreement.
- Principal and carrying amounts are kept apart: 2,912 principal vs 2,869 carrying (derived difference 43 equals the printed discount and fees).
- Sector: the unsourced "Technology" label was replaced by the filing's own wording ("financial technology company providing self-directed banking solutions"), cited by CP-0 business_description.
- `valuation` keeps the form defaults (cp_dr_public, auto) with empty issuer_market; ratings left empty.

## Open questions
See `needs_user_input` in module_golden.json: prior_case, portfolio_workbook, quotes, valuation.issuer_market, ratings, assumptions (guarantors resolved in fix round 1).

## Fix round 1 (review NATL-R1..R4, controller G-8)
- G-8: CP-0 removed from `not_golden`; 13 CP-0 facts added: identity (legal_name, ticker, exchange, state_of_incorporation, principal_executive_offices, commission_file_number, filer_status, fiscal_year_end December 31, business_description), `CP-0.identity.Credit_Agreement.borrower_entity`, and documents (10-Q and 10-K/A period_covered, Exhibit 10.1 agreement_date 2025-09-18). context.json `identity.sector` now "Financial technology (self-directed banking solutions)" from the filing's description.
- R1: `CP-2.obligor_structure.subsidiary_guarantors.names` is known (seven Loan Parties from the signature pages, with the Section 9 "Reaffirming Loan Parties" clause); `identity.guarantors` filled in context.json; guarantor entry removed from `needs_user_input`; limitation added that completeness is not shown by the source.
- R2: Term B 2025-09-30 balance stays missing; gap_reason now cites $320,000,000 on 2025-09-18 (Exhibit 10.1, Schedule I) and no amortization (10-Q Note 4).
- R3: total-debt principal_stated subject and a limitation state that 2,912 is the "our debt totaled" figure (funded borrowings, finance leases excluded) and that Codex marks FY2025Q3 total_debt missing for that reason.
- R4: added `CP-2.debt_stack.other_debt_atmaas_financing_program.master_loan_agreement_capacity` = 20 (USD millions).

## Checks
`python3 -I cases/goldens/check.py cases/goldens/natl-portfolio-decision` exit 0; `python3 -I derive.py` exit 0 (re-run after fix round 1).

Not verified: no model run against these goldens; the choice of post-amendment clauses in Exhibit 10.1 rests on reading the merged text, not the strike/underline markup; Q1/Q2 2025 and Q3 2024 10-Qs were not mined for module facts; no other source corroborates the figures.

## Batch fixes
NATL-RR1 Low wording: CP-2.obligor_structure.subsidiary_guarantors.names subject and limitation now say Loan Party status of the seven is inferred from Section 9 (Reaffirming Loan Parties), the parties clause, and their being the only signatories besides the Company, Administrative Agent and Lenders; list-completeness note was already in limitations only.

## Step 4 re-tag (2026-11-02)

Oracle preparer: mx-feature (Step 4 preparer). Files changed: this case's `module_golden.json` and `cases/goldens/line-exceptions.json`. Values, evidence and statuses of every kept fact are unchanged. Target module for every re-tag is CP-1 (in this pathway plan: `deploy_vii.contracts.PATHWAY_MODULES`).

### Counts per module (as tagged before this step)

| Module | Re-tagged | Removed | Covered by financial_gold |
|---|---|---|---|
| CP-0 | 0 | 10 | 0 |
| CP-2 | 7 | 13 | 0 |
| total | 7 | 23 | 0 |

Facts before: 132; after: 109. not_golden items added: 23.

### Re-tagged to CP-1 (old fact_id -> new fact_id; CP-1 column)

Where CP-1 builds them: T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation). The rows are written by `_facilities` (model_interface.py:465-497); row ids are the model's `facility_id`, so a row-key locator finds them.

- `CP-2.debt_stack.term_a_1.principal_outstanding.2025-09-30` -> `CP-1.debt_stack.term_a_1.principal_outstanding.2025-09-30`: T4.18 column principal
- `CP-2.debt_stack.term_a_2.principal_outstanding.2025-09-30` -> `CP-1.debt_stack.term_a_2.principal_outstanding.2025-09-30`: T4.18 column principal
- `CP-2.debt_stack.term_b.principal_outstanding.2025-09-30` -> `CP-1.debt_stack.term_b.principal_outstanding.2025-09-30`: T4.18 column principal
- `CP-2.debt_stack.revolving_credit_facility.maturity` -> `CP-1.debt_stack.revolving_credit_facility.maturity`: T4.18 column maturity_date
- `CP-2.debt_stack.9_500_senior_secured_notes_due_2029.coupon` -> `CP-1.debt_stack.9_500_senior_secured_notes_due_2029.coupon`: T4.18 column fixed_rate
- `CP-2.debt_stack.9_500_senior_secured_notes_due_2029.maturity` -> `CP-1.debt_stack.9_500_senior_secured_notes_due_2029.maturity`: T4.18 column maturity_date
- `CP-2.debt_stack.9_500_senior_secured_notes_due_2029.carrying_amount.2025-09-30` -> `CP-1.debt_stack.9_500_senior_secured_notes_due_2029.carrying_amount.2025-09-30`: T4.18 column carrying_value

### Removed (no module in the pathway plan writes the fact as a field or register cell)

- `CP-2.debt_stack.term_loan_facilities_aggregate.weighted_average_rate_long_term_portion.2025-09-30`: debt_stack / Term loan facilities (aggregate) / weighted_average_rate_long_term_portion @ 2025-09-30: no module field; CP-1 T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation) has no weighted-average-rate cell
- `CP-2.debt_stack.current_portion_of_senior_secured_credit_facility.weighted_average_rate.2025-09-30`: debt_stack / Current portion of Senior Secured Credit Facility / weighted_average_rate @ 2025-09-30: no module field; CP-1 T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation) has no weighted-average-rate cell
- `CP-2.debt_stack.term_loan_facilities_aggregate.carrying_amount.2025-09-30`: debt_stack / Term loan facilities (aggregate) / carrying_amount @ 2025-09-30: no module field; aggregate: CP-1 writes per-facility carrying_value rows, no aggregate term-loan cell (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-2.debt_stack.revolving_credit_facility.availability_stated.2025-09-30`: debt_stack / Revolving Credit Facility / availability_stated @ 2025-09-30: no module field; CP-1 writes enums secured_status/seniority and commitment/drawn_amount only, no prose ranking, payment-date, LC or availability cell (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-2.debt_stack.revolving_credit_facility.weighted_average_rate.2025-09-30`: debt_stack / Revolving Credit Facility / weighted_average_rate @ 2025-09-30: no module field; CP-1 T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation) has no weighted-average-rate cell
- `CP-2.debt_stack.9_500_senior_secured_notes_due_2029.ranking_and_security`: debt_stack / 9.500% Senior Secured Notes due 2029 / ranking_and_security: no module field; CP-1 writes enums secured_status/seniority and commitment/drawn_amount only, no prose ranking, payment-date, LC or availability cell (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-2.debt_stack.9_500_senior_secured_notes_due_2029.interest_payment_dates`: debt_stack / 9.500% Senior Secured Notes due 2029 / interest_payment_dates: no module field; CP-1 writes enums secured_status/seniority and commitment/drawn_amount only, no prose ranking, payment-date, LC or availability cell (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-2.debt_stack.other_debt_atmaas_financing_program.weighted_average_rate.2025-09-30`: debt_stack / Other debt (ATMaaS financing program) / weighted_average_rate @ 2025-09-30: no module field; CP-1 T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation) has no weighted-average-rate cell
- `CP-2.debt_stack.long_term_debt.fair_value_level_2.2025-09-30`: debt_stack / Long-term debt / fair_value_level_2 @ 2025-09-30: no module field; CP-1 T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation) has no fair-value column
- `CP-2.obligor_structure.borrower.legal_name`: obligor_structure / Borrower / legal_name: no module field; no module in the portfolio_decision plan writes obligor, guarantor, ticker or collateral fields; CP-2 writes judged prose rows T2.1/T2.7/T2.10-T2.12 (src/deploy_vii/cp2_synthesis.py:501-536) and refNN copies of CP-1 facts (cp2_synthesis.py:839)
- `CP-2.obligor_structure.listed_issuer.ticker_and_exchange`: obligor_structure / Listed issuer / ticker_and_exchange: no module field; no module in the portfolio_decision plan writes obligor, guarantor, ticker or collateral fields; CP-2 writes judged prose rows T2.1/T2.7/T2.10-T2.12 (src/deploy_vii/cp2_synthesis.py:501-536) and refNN copies of CP-1 facts (cp2_synthesis.py:839)
- `CP-2.obligor_structure.credit_facility_collateral_and_guarantors.collateral_and_guarantors`: obligor_structure / Credit facility collateral and guarantors / collateral_and_guarantors: no module field; no module in the portfolio_decision plan writes obligor, guarantor, ticker or collateral fields; CP-2 writes judged prose rows T2.1/T2.7/T2.10-T2.12 (src/deploy_vii/cp2_synthesis.py:501-536) and refNN copies of CP-1 facts (cp2_synthesis.py:839)
- `CP-2.obligor_structure.subsidiary_guarantors.names`: obligor_structure / Subsidiary Guarantors (Loan Parties other than the Company signing the 2025-09-18 Refinancing Facility Agreement; Loan Party status inferred, see limitations) / names: no module field; no module in the portfolio_decision plan writes obligor, guarantor, ticker or collateral fields; CP-2 writes judged prose rows T2.1/T2.7/T2.10-T2.12 (src/deploy_vii/cp2_synthesis.py:501-536) and refNN copies of CP-1 facts (cp2_synthesis.py:839)
- `CP-0.identity.NCR_Atleos_Corporation.ticker`: CP-0 identity/document fact (identity / NCR Atleos Corporation / ticker) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.NCR_Atleos_Corporation.exchange`: CP-0 identity/document fact (identity / NCR Atleos Corporation / exchange) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.NCR_Atleos_Corporation.state_of_incorporation`: CP-0 identity/document fact (identity / NCR Atleos Corporation / state_of_incorporation) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.NCR_Atleos_Corporation.principal_executive_offices`: CP-0 identity/document fact (identity / NCR Atleos Corporation / principal_executive_offices) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.NCR_Atleos_Corporation.commission_file_number`: CP-0 identity/document fact (identity / NCR Atleos Corporation / commission_file_number) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.NCR_Atleos_Corporation.filer_status`: CP-0 identity/document fact (identity / NCR Atleos Corporation / filer_status) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.NCR_Atleos_Corporation.fiscal_year_end`: CP-0 identity/document fact (identity / NCR Atleos Corporation / fiscal_year_end) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.NCR_Atleos_Corporation.business_description`: CP-0 identity/document fact (identity / NCR Atleos Corporation / business_description) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.Credit_Agreement.borrower_entity`: CP-0 identity/document fact (identity / Credit Agreement / borrower_entity) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.documents.Refinancing_Facility_Agreement_and_conformed_Credit_Agreement.agreement_date`: CP-0 identity/document fact (documents / Refinancing Facility Agreement and conformed Credit Agreement / agreement_date) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)

### Kept although the rules above would move them

- `CP-2.debt_stack.revolving_credit_facility.commitment.2025-09-30` (would be re-tagged to CP-1): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-2.debt_stack.revolving_credit_facility.drawn_principal.2025-09-30` (would be re-tagged to CP-1): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-2.debt_stack.revolving_credit_facility.letters_of_credit_outstanding.2025-09-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-2.debt_stack.9_500_senior_secured_notes_due_2029.principal_outstanding.2025-09-30` (would be re-tagged to CP-1): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-2.debt_stack.other_debt_atmaas_financing_program.principal_outstanding.2025-09-30` (would be re-tagged to CP-1): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-2.liquidity.cash_and_cash_equivalents.balance.2025-09-30` (would be removed as covered by financial_gold): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-0.identity.NCR_Atleos_Corporation.legal_name` (would be removed): mapping.json entry (scored; leave it)

### For the controller

- `mapping.json` still lists 30 of the moved fact_ids under `unmapped` (preparer may not edit it); `load_mapping` will refuse it until they are dropped or renamed.
- `line-exceptions.json` updated: entries of removed facts dropped, entries of re-tagged facts renamed (quote_misses 83 -> 52, printed_unplaced 2 -> 1 across all cases); `MAX_QUOTE_EXCEPTIONS` in tests/test_goldens_lines.py stays 83 (shrink-only constant, may be lowered by its owner).

- derive.py reads the kept facts listed above by id or by topic/subject/field; they stay tagged to the old module until derive.py is updated.

Not verified: no module run (the mapping is read from code, not from a result); the pytest suite (no venv); that a model's CP-1 T4.18 carries a row for each re-tagged facility (the scorer reports a missing row as missing); unit agreement for margin/floor/rate re-tags (golden percent vs CP-1 basis points or decimal_percent; the scorer reports unit problems rather than a match); `mapping.json` against the changed goldens (not edited, not loaded).
