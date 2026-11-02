# tdg-credit-snapshot prepare report

Pathway credit_snapshot, issuer TransDigm Group Incorporated, cutoff 2025-02-04. Periods use the issuer's fiscal labelling: current_period q1-2025 (quarter ended 2024-12-28), FY ends 30 September. Sources: Q2FY24, Q3FY24 10-Qs, FY2024 10-K, Q1FY25 10-Q.

## Fact counts per module (178 total)
- CP-0: 17
- CP-1A: 32 (includes the two Amendment No. 15 and No. 16 term-loan events added in fix round 1)
- CP-2: 116
- CP-3: 1
- CP-4: 12
- Not golden: CP-1 (financial_gold), CP-MODEL, CP-5, CP-6.

## Judgment calls
- Borrower is TransDigm Inc. (10-K exhibit index 10.37), parent TransDigm Group Incorporated; borrower and parent are kept distinct.
- Revolver drawn balance is derived (commitments - letters of credit - availability), as no drawn amount is printed.
- Covenant ratio_definition is conflicting: the covenant paragraph says net debt to EBITDA As Defined; the non-GAAP paragraph says secured indebtedness to Consolidated EBITDA. Value is null with both quotes.
- The acquisition amount is recorded as purchase_price (source: "total purchase price"), not cash paid.
- attachments.legal_documents is "executed" (ruling G-6).

## Limitations
- The Credit Agreement, indentures and Exhibit 22.1 are not in the corpus; CP-4 rests on 10-K/10-Q descriptions only.
- Guarantors: the full list is in Exhibit 22.1; only classes named in the debt note are filled. "TransDigm UK" is as printed; its legal name is unconfirmed.
- Covenant text was identical in all four filings; only 2024-12-28 is cited.
- Debt-stack total excludes the securitization facility; the maturity schedule excludes finance leases and securitization.
- Hedging, swaps and other leases are not covered.

Not verified: the FY2024 annual-report PDF; the legal name of TransDigm UK; the Q2/Q3 FY2024 filings for each financing event; about 124 facts covered only by the checker's quote match; Exhibit 22.1 guarantor list; the credit agreement text.

## Step 4 re-tag (2026-11-02)

Oracle preparer: mx-feature (Step 4 preparer). Files changed: this case's `module_golden.json` and `cases/goldens/line-exceptions.json`. Values, evidence and statuses of every kept fact are unchanged. Target module for every re-tag is CP-1 (in this pathway plan: `deploy_vii.contracts.PATHWAY_MODULES`).

### Counts per module (as tagged before this step)

| Module | Re-tagged | Removed | Covered by financial_gold |
|---|---|---|---|
| CP-0 | 0 | 12 | 0 |
| CP-2 | 61 | 36 | 3 |
| total | 61 | 48 | 3 |

Facts before: 178; after: 127. not_golden items added: 51.

### Re-tagged to CP-1 (old fact_id -> new fact_id; CP-1 column)

Where CP-1 builds them: T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation). The rows are written by `_facilities` (model_interface.py:465-497); row ids are the model's `facility_id`, so a row-key locator finds them.

- `CP-2.debt_stack.5_50_2027_Notes.principal_outstanding.2024-12-28` -> `CP-1.debt_stack.5_50_2027_Notes.principal_outstanding.2024-12-28`: T4.18 column principal
- `CP-2.debt_stack.5_50_2027_Notes.carrying_amount_net.2024-12-28` -> `CP-1.debt_stack.5_50_2027_Notes.carrying_amount_net.2024-12-28`: T4.18 column carrying_value
- `CP-2.debt_stack.5_50_2027_Notes.maturity_date.2024-12-28` -> `CP-1.debt_stack.5_50_2027_Notes.maturity_date.2024-12-28`: T4.18 column maturity_date
- `CP-2.debt_stack.5_50_2027_Notes.interest_rate.2024-12-28` -> `CP-1.debt_stack.5_50_2027_Notes.interest_rate.2024-12-28`: T4.18 column fixed_rate
- `CP-2.debt_stack.2028_Secured_Notes.principal_outstanding.2024-12-28` -> `CP-1.debt_stack.2028_Secured_Notes.principal_outstanding.2024-12-28`: T4.18 column principal
- `CP-2.debt_stack.2028_Secured_Notes.carrying_amount_net.2024-12-28` -> `CP-1.debt_stack.2028_Secured_Notes.carrying_amount_net.2024-12-28`: T4.18 column carrying_value
- `CP-2.debt_stack.2028_Secured_Notes.maturity_date.2024-12-28` -> `CP-1.debt_stack.2028_Secured_Notes.maturity_date.2024-12-28`: T4.18 column maturity_date
- `CP-2.debt_stack.2028_Secured_Notes.interest_rate.2024-12-28` -> `CP-1.debt_stack.2028_Secured_Notes.interest_rate.2024-12-28`: T4.18 column fixed_rate
- `CP-2.debt_stack.4_625_2029_Notes.principal_outstanding.2024-12-28` -> `CP-1.debt_stack.4_625_2029_Notes.principal_outstanding.2024-12-28`: T4.18 column principal
- `CP-2.debt_stack.4_625_2029_Notes.carrying_amount_net.2024-12-28` -> `CP-1.debt_stack.4_625_2029_Notes.carrying_amount_net.2024-12-28`: T4.18 column carrying_value
- `CP-2.debt_stack.4_625_2029_Notes.maturity_date.2024-12-28` -> `CP-1.debt_stack.4_625_2029_Notes.maturity_date.2024-12-28`: T4.18 column maturity_date
- `CP-2.debt_stack.4_625_2029_Notes.interest_rate.2024-12-28` -> `CP-1.debt_stack.4_625_2029_Notes.interest_rate.2024-12-28`: T4.18 column fixed_rate
- `CP-2.debt_stack.2029_Secured_Notes.principal_outstanding.2024-12-28` -> `CP-1.debt_stack.2029_Secured_Notes.principal_outstanding.2024-12-28`: T4.18 column principal
- `CP-2.debt_stack.2029_Secured_Notes.carrying_amount_net.2024-12-28` -> `CP-1.debt_stack.2029_Secured_Notes.carrying_amount_net.2024-12-28`: T4.18 column carrying_value
- `CP-2.debt_stack.2029_Secured_Notes.maturity_date.2024-12-28` -> `CP-1.debt_stack.2029_Secured_Notes.maturity_date.2024-12-28`: T4.18 column maturity_date
- `CP-2.debt_stack.2029_Secured_Notes.interest_rate.2024-12-28` -> `CP-1.debt_stack.2029_Secured_Notes.interest_rate.2024-12-28`: T4.18 column fixed_rate
- `CP-2.debt_stack.4_875_2029_Notes.principal_outstanding.2024-12-28` -> `CP-1.debt_stack.4_875_2029_Notes.principal_outstanding.2024-12-28`: T4.18 column principal
- `CP-2.debt_stack.4_875_2029_Notes.carrying_amount_net.2024-12-28` -> `CP-1.debt_stack.4_875_2029_Notes.carrying_amount_net.2024-12-28`: T4.18 column carrying_value
- `CP-2.debt_stack.4_875_2029_Notes.maturity_date.2024-12-28` -> `CP-1.debt_stack.4_875_2029_Notes.maturity_date.2024-12-28`: T4.18 column maturity_date
- `CP-2.debt_stack.4_875_2029_Notes.interest_rate.2024-12-28` -> `CP-1.debt_stack.4_875_2029_Notes.interest_rate.2024-12-28`: T4.18 column fixed_rate
- `CP-2.debt_stack.2030_Secured_Notes.principal_outstanding.2024-12-28` -> `CP-1.debt_stack.2030_Secured_Notes.principal_outstanding.2024-12-28`: T4.18 column principal
- `CP-2.debt_stack.2030_Secured_Notes.carrying_amount_net.2024-12-28` -> `CP-1.debt_stack.2030_Secured_Notes.carrying_amount_net.2024-12-28`: T4.18 column carrying_value
- `CP-2.debt_stack.2030_Secured_Notes.maturity_date.2024-12-28` -> `CP-1.debt_stack.2030_Secured_Notes.maturity_date.2024-12-28`: T4.18 column maturity_date
- `CP-2.debt_stack.2030_Secured_Notes.interest_rate.2024-12-28` -> `CP-1.debt_stack.2030_Secured_Notes.interest_rate.2024-12-28`: T4.18 column fixed_rate
- `CP-2.debt_stack.2031_Secured_Notes.principal_outstanding.2024-12-28` -> `CP-1.debt_stack.2031_Secured_Notes.principal_outstanding.2024-12-28`: T4.18 column principal
- `CP-2.debt_stack.2031_Secured_Notes.carrying_amount_net.2024-12-28` -> `CP-1.debt_stack.2031_Secured_Notes.carrying_amount_net.2024-12-28`: T4.18 column carrying_value
- `CP-2.debt_stack.2031_Secured_Notes.maturity_date.2024-12-28` -> `CP-1.debt_stack.2031_Secured_Notes.maturity_date.2024-12-28`: T4.18 column maturity_date
- `CP-2.debt_stack.2031_Secured_Notes.interest_rate.2024-12-28` -> `CP-1.debt_stack.2031_Secured_Notes.interest_rate.2024-12-28`: T4.18 column fixed_rate
- `CP-2.debt_stack.2032_Secured_Notes.principal_outstanding.2024-12-28` -> `CP-1.debt_stack.2032_Secured_Notes.principal_outstanding.2024-12-28`: T4.18 column principal
- `CP-2.debt_stack.2032_Secured_Notes.carrying_amount_net.2024-12-28` -> `CP-1.debt_stack.2032_Secured_Notes.carrying_amount_net.2024-12-28`: T4.18 column carrying_value
- `CP-2.debt_stack.2032_Secured_Notes.maturity_date.2024-12-28` -> `CP-1.debt_stack.2032_Secured_Notes.maturity_date.2024-12-28`: T4.18 column maturity_date
- `CP-2.debt_stack.2032_Secured_Notes.interest_rate.2024-12-28` -> `CP-1.debt_stack.2032_Secured_Notes.interest_rate.2024-12-28`: T4.18 column fixed_rate
- `CP-2.debt_stack.2033_Secured_Notes.principal_outstanding.2024-12-28` -> `CP-1.debt_stack.2033_Secured_Notes.principal_outstanding.2024-12-28`: T4.18 column principal
- `CP-2.debt_stack.2033_Secured_Notes.carrying_amount_net.2024-12-28` -> `CP-1.debt_stack.2033_Secured_Notes.carrying_amount_net.2024-12-28`: T4.18 column carrying_value
- `CP-2.debt_stack.2033_Secured_Notes.maturity_date.2024-12-28` -> `CP-1.debt_stack.2033_Secured_Notes.maturity_date.2024-12-28`: T4.18 column maturity_date
- `CP-2.debt_stack.2033_Secured_Notes.interest_rate.2024-12-28` -> `CP-1.debt_stack.2033_Secured_Notes.interest_rate.2024-12-28`: T4.18 column fixed_rate
- `CP-2.debt_stack.Term_loan_Tranche_I.principal_outstanding.2024-12-28` -> `CP-1.debt_stack.Term_loan_Tranche_I.principal_outstanding.2024-12-28`: T4.18 column principal
- `CP-2.debt_stack.Term_loan_Tranche_I.maturity_date.2024-12-28` -> `CP-1.debt_stack.Term_loan_Tranche_I.maturity_date.2024-12-28`: T4.18 column maturity_date
- `CP-2.debt_stack.Term_loan_Tranche_I.interest_rate_terms.2024-12-28` -> `CP-1.debt_stack.Term_loan_Tranche_I.interest_rate_terms.2024-12-28`: T4.18 column margin_or_coupon
- `CP-2.debt_stack.Term_loan_Tranche_J.principal_outstanding.2024-12-28` -> `CP-1.debt_stack.Term_loan_Tranche_J.principal_outstanding.2024-12-28`: T4.18 column principal
- `CP-2.debt_stack.Term_loan_Tranche_J.maturity_date.2024-12-28` -> `CP-1.debt_stack.Term_loan_Tranche_J.maturity_date.2024-12-28`: T4.18 column maturity_date
- `CP-2.debt_stack.Term_loan_Tranche_J.interest_rate_terms.2024-12-28` -> `CP-1.debt_stack.Term_loan_Tranche_J.interest_rate_terms.2024-12-28`: T4.18 column margin_or_coupon
- `CP-2.debt_stack.Term_loan_Tranche_K.principal_outstanding.2024-12-28` -> `CP-1.debt_stack.Term_loan_Tranche_K.principal_outstanding.2024-12-28`: T4.18 column principal
- `CP-2.debt_stack.Term_loan_Tranche_K.maturity_date.2024-12-28` -> `CP-1.debt_stack.Term_loan_Tranche_K.maturity_date.2024-12-28`: T4.18 column maturity_date
- `CP-2.debt_stack.Term_loan_Tranche_K.interest_rate_terms.2024-12-28` -> `CP-1.debt_stack.Term_loan_Tranche_K.interest_rate_terms.2024-12-28`: T4.18 column margin_or_coupon
- `CP-2.debt_stack.Term_loan_Tranche_L.principal_outstanding.2024-12-28` -> `CP-1.debt_stack.Term_loan_Tranche_L.principal_outstanding.2024-12-28`: T4.18 column principal
- `CP-2.debt_stack.Term_loan_Tranche_L.maturity_date.2024-12-28` -> `CP-1.debt_stack.Term_loan_Tranche_L.maturity_date.2024-12-28`: T4.18 column maturity_date
- `CP-2.debt_stack.Term_loan_Tranche_L.interest_rate_terms.2024-12-28` -> `CP-1.debt_stack.Term_loan_Tranche_L.interest_rate_terms.2024-12-28`: T4.18 column margin_or_coupon
- `CP-2.debt_stack.Trade_receivable_securitization_facility.principal_outstanding.2024-12-28` -> `CP-1.debt_stack.Trade_receivable_securitization_facility.principal_outstanding.2024-12-28`: T4.18 column principal
- `CP-2.debt_stack.Trade_receivable_securitization_facility.carrying_amount_net.2024-12-28` -> `CP-1.debt_stack.Trade_receivable_securitization_facility.carrying_amount_net.2024-12-28`: T4.18 column carrying_value
- `CP-2.debt_stack.Trade_receivable_securitization_facility.maturity_date.2024-12-28` -> `CP-1.debt_stack.Trade_receivable_securitization_facility.maturity_date.2024-12-28`: T4.18 column maturity_date
- `CP-2.debt_stack.Trade_receivable_securitization_facility.interest_rate_terms.2024-12-28` -> `CP-1.debt_stack.Trade_receivable_securitization_facility.interest_rate_terms.2024-12-28`: T4.18 column margin_or_coupon
- `CP-2.debt_stack.Government_refundable_advances.principal_outstanding.2024-12-28` -> `CP-1.debt_stack.Government_refundable_advances.principal_outstanding.2024-12-28`: T4.18 column principal
- `CP-2.debt_stack.Government_refundable_advances.carrying_amount_net.2024-12-28` -> `CP-1.debt_stack.Government_refundable_advances.carrying_amount_net.2024-12-28`: T4.18 column carrying_value
- `CP-2.debt_stack.Finance_lease_obligations.principal_outstanding.2024-12-28` -> `CP-1.debt_stack.Finance_lease_obligations.principal_outstanding.2024-12-28`: T4.18 column principal
- `CP-2.debt_stack.Finance_lease_obligations.carrying_amount_net.2024-12-28` -> `CP-1.debt_stack.Finance_lease_obligations.carrying_amount_net.2024-12-28`: T4.18 column carrying_value
- `CP-2.revolver.Revolving_credit_facility.commitments.2024-12-28` -> `CP-1.revolver.Revolving_credit_facility.commitments.2024-12-28`: T4.18 column commitment
- `CP-2.revolver.Revolving_credit_facility.drawn_balance.2024-12-28` -> `CP-1.revolver.Revolving_credit_facility.drawn_balance.2024-12-28`: T4.18 column drawn_amount
- `CP-2.revolver.Revolving_credit_facility.maturity_date.2024-12-28` -> `CP-1.revolver.Revolving_credit_facility.maturity_date.2024-12-28`: T4.18 column maturity_date
- `CP-2.revolver.Revolving_credit_facility.drawn_rate_terms.2024-12-28` -> `CP-1.revolver.Revolving_credit_facility.drawn_rate_terms.2024-12-28`: T4.18 column margin_or_coupon
- `CP-2.debt_stack.Finance_lease_obligations.principal_outstanding.2024-09-30` -> `CP-1.debt_stack.Finance_lease_obligations.principal_outstanding.2024-09-30`: T4.18 column principal

### Removed, covered by financial_gold

- `CP-2.debt_totals.Current_portion_of_long_term_debt.carrying_amount_net.2024-12-28`: financial_gold long_term_debt_current FY2025Q1 (same metric, period and value)
- `CP-2.debt_totals.Long_term_debt.carrying_amount_net.2024-12-28`: financial_gold long_term_debt_noncurrent_carrying FY2025Q1 (same metric, period and value)
- `CP-2.debt_totals.Total_debt_per_MD_A_includes_issuance_costs_and_OID_effect.total_debt_net.2024-12-28`: financial_gold total_debt FY2025Q1 (same metric, period and value)

### Removed (no module in the pathway plan writes the fact as a field or register cell)

- `CP-0.identity.TransDigm_Group_Incorporated.ticker`: CP-0 identity/document fact (identity / TransDigm Group Incorporated / ticker) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.TransDigm_Group_Incorporated.exchange`: CP-0 identity/document fact (identity / TransDigm Group Incorporated / exchange) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.TransDigm_Group_Incorporated.state_of_incorporation`: CP-0 identity/document fact (identity / TransDigm Group Incorporated / state_of_incorporation) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.TransDigm_Group_Incorporated.principal_executive_offices`: CP-0 identity/document fact (identity / TransDigm Group Incorporated / principal_executive_offices) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.TransDigm_Group_Incorporated.fiscal_year_end`: CP-0 identity/document fact (identity / TransDigm Group Incorporated / fiscal_year_end) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.TransDigm_Group_Incorporated.filer_status`: CP-0 identity/document fact (identity / TransDigm Group Incorporated / filer_status) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.TransDigm_Group_Incorporated.commission_file_number`: CP-0 identity/document fact (identity / TransDigm Group Incorporated / commission_file_number) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.TransDigm_Inc.relationship_to_listed_parent`: CP-0 identity/document fact (identity / TransDigm Inc. / relationship_to_listed_parent) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.TD_Group.holding_company_status`: CP-0 identity/document fact (identity / TD Group / holding_company_status) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.Subordinated_Notes.issuer_entity`: CP-0 identity/document fact (identity / Subordinated Notes / issuer_entity) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.2031_Secured_Notes.issuer_entity`: CP-0 identity/document fact (identity / 2031 Secured Notes / issuer_entity) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.Term_Loans_Facility_and_revolving_credit_facility.borrower_entity`: CP-0 identity/document fact (identity / Term Loans Facility and revolving credit facility / borrower_entity) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-2.debt_stack.5_50_2027_Notes.fair_value.2024-12-28`: debt_stack / 5.50% 2027 Notes / fair_value @ 2024-12-28: no module field; CP-1 T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation) has no fair-value column
- `CP-2.debt_stack.5_50_2027_Notes.security_and_ranking.2024-12-28`: debt_stack / 5.50% 2027 Notes / security_and_ranking @ 2024-12-28: no module field; CP-1 writes the enums secured_status/seniority, not this prose (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-2.debt_stack.2028_Secured_Notes.fair_value.2024-12-28`: debt_stack / 2028 Secured Notes / fair_value @ 2024-12-28: no module field; CP-1 T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation) has no fair-value column
- `CP-2.debt_stack.2028_Secured_Notes.security_and_ranking.2024-12-28`: debt_stack / 2028 Secured Notes / security_and_ranking @ 2024-12-28: no module field; CP-1 writes the enums secured_status/seniority, not this prose (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-2.debt_stack.4_625_2029_Notes.fair_value.2024-12-28`: debt_stack / 4.625% 2029 Notes / fair_value @ 2024-12-28: no module field; CP-1 T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation) has no fair-value column
- `CP-2.debt_stack.4_625_2029_Notes.security_and_ranking.2024-12-28`: debt_stack / 4.625% 2029 Notes / security_and_ranking @ 2024-12-28: no module field; CP-1 writes the enums secured_status/seniority, not this prose (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-2.debt_stack.2029_Secured_Notes.fair_value.2024-12-28`: debt_stack / 2029 Secured Notes / fair_value @ 2024-12-28: no module field; CP-1 T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation) has no fair-value column
- `CP-2.debt_stack.2029_Secured_Notes.security_and_ranking.2024-12-28`: debt_stack / 2029 Secured Notes / security_and_ranking @ 2024-12-28: no module field; CP-1 writes the enums secured_status/seniority, not this prose (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-2.debt_stack.4_875_2029_Notes.fair_value.2024-12-28`: debt_stack / 4.875% 2029 Notes / fair_value @ 2024-12-28: no module field; CP-1 T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation) has no fair-value column
- `CP-2.debt_stack.4_875_2029_Notes.security_and_ranking.2024-12-28`: debt_stack / 4.875% 2029 Notes / security_and_ranking @ 2024-12-28: no module field; CP-1 writes the enums secured_status/seniority, not this prose (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-2.debt_stack.2030_Secured_Notes.fair_value.2024-12-28`: debt_stack / 2030 Secured Notes / fair_value @ 2024-12-28: no module field; CP-1 T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation) has no fair-value column
- `CP-2.debt_stack.2030_Secured_Notes.security_and_ranking.2024-12-28`: debt_stack / 2030 Secured Notes / security_and_ranking @ 2024-12-28: no module field; CP-1 writes the enums secured_status/seniority, not this prose (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-2.debt_stack.2031_Secured_Notes.fair_value.2024-12-28`: debt_stack / 2031 Secured Notes / fair_value @ 2024-12-28: no module field; CP-1 T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation) has no fair-value column
- `CP-2.debt_stack.2031_Secured_Notes.security_and_ranking.2024-12-28`: debt_stack / 2031 Secured Notes / security_and_ranking @ 2024-12-28: no module field; CP-1 writes the enums secured_status/seniority, not this prose (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-2.debt_stack.2032_Secured_Notes.fair_value.2024-12-28`: debt_stack / 2032 Secured Notes / fair_value @ 2024-12-28: no module field; CP-1 T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation) has no fair-value column
- `CP-2.debt_stack.2032_Secured_Notes.security_and_ranking.2024-12-28`: debt_stack / 2032 Secured Notes / security_and_ranking @ 2024-12-28: no module field; CP-1 writes the enums secured_status/seniority, not this prose (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-2.debt_stack.2033_Secured_Notes.fair_value.2024-12-28`: debt_stack / 2033 Secured Notes / fair_value @ 2024-12-28: no module field; CP-1 T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation) has no fair-value column
- `CP-2.debt_stack.2033_Secured_Notes.security_and_ranking.2024-12-28`: debt_stack / 2033 Secured Notes / security_and_ranking @ 2024-12-28: no module field; CP-1 writes the enums secured_status/seniority, not this prose (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-2.debt_stack.Term_loans.carrying_amount_net.2024-12-28`: debt_stack / Term loans / carrying_amount_net @ 2024-12-28: no module field; CP-1 writes per-tranche rows in T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation), no aggregate term-loan row
- `CP-2.debt_stack.Term_loans.fair_value.2024-12-28`: debt_stack / Term loans / fair_value @ 2024-12-28: no module field; CP-1 writes per-tranche rows in T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation), no aggregate term-loan row
- `CP-2.debt_stack.Term_Loans_Facility.sofr_floor.2024-12-28`: debt_stack / Term Loans Facility / sofr_floor @ 2024-12-28: no module field; CP-1 writes floor_bps as a number or gap, not this text (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-2.debt_stack.Term_Loans_Facility.security_and_ranking.2024-12-28`: debt_stack / Term Loans Facility / security_and_ranking @ 2024-12-28: no module field; CP-1 writes the enums secured_status/seniority, not this prose (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-2.debt_stack.Term_Loans_Facility.scheduled_quarterly_amortization.2024-12-28`: debt_stack / Term Loans Facility / scheduled_quarterly_amortization @ 2024-12-28: no module field; CP-1 writes annual_amortisation (annual), not this quarterly figure (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-2.debt_stack.Trade_receivable_securitization_facility.fair_value.2024-12-28`: debt_stack / Trade receivable securitization facility / fair_value @ 2024-12-28: no module field; CP-1 T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation) has no fair-value column
- `CP-2.debt_stack.Trade_receivable_securitization_facility.drawn_and_capacity_status.2024-12-28`: debt_stack / Trade receivable securitization facility / drawn_and_capacity_status @ 2024-12-28: no module field; CP-1 writes numeric drawn_amount/commitment/fixed_rate/margin_or_coupon, no such cell (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation)); CP-2 writes judged prose rows T2.1/T2.7/T2.10-T2.12 (src/deploy_vii/cp2_synthesis.py:501-536) and refNN copies of CP-1 facts (cp2_synthesis.py:839)
- `CP-2.debt_stack.Trade_receivable_securitization_facility.applicable_interest_rate.2024-12-28`: debt_stack / Trade receivable securitization facility / applicable_interest_rate @ 2024-12-28: no module field; CP-1 writes numeric drawn_amount/commitment/fixed_rate/margin_or_coupon, no such cell (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation)); CP-2 writes judged prose rows T2.1/T2.7/T2.10-T2.12 (src/deploy_vii/cp2_synthesis.py:501-536) and refNN copies of CP-1 facts (cp2_synthesis.py:839)
- `CP-2.debt_stack.Trade_receivable_securitization_facility.security_and_ranking.2024-12-28`: debt_stack / Trade receivable securitization facility / security_and_ranking @ 2024-12-28: no module field; CP-1 writes the enums secured_status/seniority, not this prose (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-2.debt_stack.Government_refundable_advances.repayment_terms.2024-12-28`: debt_stack / Government refundable advances / repayment_terms @ 2024-12-28: no module field; CP-1 writes numeric drawn_amount/commitment/fixed_rate/margin_or_coupon, no such cell (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation)); CP-2 writes judged prose rows T2.1/T2.7/T2.10-T2.12 (src/deploy_vii/cp2_synthesis.py:501-536) and refNN copies of CP-1 facts (cp2_synthesis.py:839)
- `CP-2.debt_totals.Debt_excluding_securitization_facility.carrying_amount_net.2024-12-28`: debt_totals / Debt excluding securitization facility / carrying_amount_net @ 2024-12-28: no module field; aggregate: CP-1 writes per-facility carrying_value rows and the total_debt account, no sub-total (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-2.debt_totals.Accrued_interest.amount.2024-12-28`: debt_totals / Accrued interest / amount @ 2024-12-28: no module field; no CP-1 account or facility cell holds it (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation)); CP-2 writes judged prose rows T2.1/T2.7/T2.10-T2.12 (src/deploy_vii/cp2_synthesis.py:501-536) and refNN copies of CP-1 facts (cp2_synthesis.py:839)
- `CP-2.debt_totals.Gross_debt.fixed_rate_share.2024-12-28`: debt_totals / Gross debt / fixed_rate_share @ 2024-12-28: no module field; no CP-1 account or facility cell holds it (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation)); CP-2 writes judged prose rows T2.1/T2.7/T2.10-T2.12 (src/deploy_vii/cp2_synthesis.py:501-536) and refNN copies of CP-1 facts (cp2_synthesis.py:839)
- `CP-2.revolver.Revolving_credit_facility.unused_commitment_fee.2024-12-28`: revolver / Revolving credit facility / unused_commitment_fee @ 2024-12-28: no module field; CP-1 writes commitment and drawn_amount (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation)) and CP-1 KPI undrawn_rcf = rcf_commitment - rcf_drawn with no letters-of-credit deduction (src/deploy_vii/model/debt.py:293-301, src/deploy_vii/canonical_kpis.py:220); no LC, fee, sublimit, availability or ranking-prose cell
- `CP-2.revolver.Revolving_credit_facility.multicurrency_commitments_up_to.2024-12-28`: revolver / Revolving credit facility / multicurrency_commitments_up_to @ 2024-12-28: no module field; CP-1 writes commitment and drawn_amount (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation)) and CP-1 KPI undrawn_rcf = rcf_commitment - rcf_drawn with no letters-of-credit deduction (src/deploy_vii/model/debt.py:293-301, src/deploy_vii/canonical_kpis.py:220); no LC, fee, sublimit, availability or ranking-prose cell
- `CP-2.revolver.Revolving_credit_facility.security_and_ranking.2024-12-28`: revolver / Revolving credit facility / security_and_ranking @ 2024-12-28: no module field; CP-1 writes commitment and drawn_amount (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation)) and CP-1 KPI undrawn_rcf = rcf_commitment - rcf_drawn with no letters-of-credit deduction (src/deploy_vii/model/debt.py:293-301, src/deploy_vii/canonical_kpis.py:220); no LC, fee, sublimit, availability or ranking-prose cell
- `CP-2.liquidity.Term_loans_and_notes.earliest_maturity_statement.2024-12-28`: liquidity / Term loans and notes / earliest_maturity_statement @ 2024-12-28: no module field; CP-1 writes maturity_date per facility (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation)), no maturity statement; CP-2 writes judged prose rows T2.1/T2.7/T2.10-T2.12 (src/deploy_vii/cp2_synthesis.py:501-536) and refNN copies of CP-1 facts (cp2_synthesis.py:839)
- `CP-2.maturity_schedule.Maturity_schedule_at_2024_12_28.scheduled_maturity_by_year.2024-12-28`: maturity_schedule / Maturity schedule at 2024-12-28 / scheduled_maturity_by_year @ 2024-12-28: no module field; CP-1 writes maturity_date per facility (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation)), no year-by-year ladder; CP-2 writes judged prose rows T2.1/T2.7/T2.10-T2.12 (src/deploy_vii/cp2_synthesis.py:501-536) and refNN copies of CP-1 facts (cp2_synthesis.py:839)

### Kept although the rules above would move them

- `CP-0.identity.TransDigm_Group_Incorporated.legal_name` (would be removed): mapping.json entry (scored; leave it)
- `CP-2.liquidity.Cash_and_cash_equivalents.balance.2024-12-28` (would be removed as covered by financial_gold): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-2.liquidity.Cash_liquidity_cash_plus_revolver_availability.amount.2024-12-28` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-2.debt_stack.Term_loans.principal_outstanding.2024-12-28` (would be removed): operand of a kept derived fact
- `CP-2.revolver.Revolving_credit_facility.letters_of_credit_outstanding.2024-12-28` (would be removed): operand of a kept derived fact
- `CP-2.revolver.Revolving_credit_facility.availability.2024-12-28` (would be removed): operand of a kept derived fact

### For the controller

- `mapping.json` still lists 112 of the moved fact_ids under `unmapped` (preparer may not edit it); `load_mapping` will refuse it until they are dropped or renamed.
- `line-exceptions.json` updated: entries of removed facts dropped, entries of re-tagged facts renamed (quote_misses 83 -> 52, printed_unplaced 2 -> 1 across all cases); `MAX_QUOTE_EXCEPTIONS` in tests/test_goldens_lines.py stays 83 (shrink-only constant, may be lowered by its owner).

- derive.py reads the kept facts listed above by id or by topic/subject/field; they stay tagged to the old module until derive.py is updated.

Not verified: no module run (the mapping is read from code, not from a result); the pytest suite (no venv); that a model's CP-1 T4.18 carries a row for each re-tagged facility (the scorer reports a missing row as missing); unit agreement for margin/floor/rate re-tags (golden percent vs CP-1 basis points or decimal_percent; the scorer reports unit problems rather than a match); `mapping.json` against the changed goldens (not edited, not loaded).
