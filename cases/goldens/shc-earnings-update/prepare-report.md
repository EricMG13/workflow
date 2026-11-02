# SHC earnings_update gap-layer preparation report

Case `shc-earnings-update`; cutoff and as_of 2025-08-08; preparer mx-feature.

## Coverage
- CP-0: 16 known facts (registrant identity, ticker, file number, shares at 2025-07-29, sponsors from the FY2024 10-K, borrower Sotera Health Holdings, LLC vs listed parent, guarantor class, segments, document dates, unit).
- CP-1B: 49 known + 2 missing. Current (3 months to 2025-06-30) vs prior (3 months to 2024-06-30) for consolidated revenue, Sterigenics/Nordion/Nelson Labs revenue and segment income, net income, Adjusted EBITDA; 9 derived changes (`derive.py`, printed $ change used as cross-check only). Debt facts: Refinancing Term Loans gross 1,498,030 vs net 1,470,889 (thousands), original principal $1,509,350,000, margins/floor/step-down, weighted average rates, maturity; secured notes; revolver commitments $600.0m, drawn nil, LCs $14.2m, availability $585.8m. Missing: margin tier in force at 2025-06-30; FY2025 guidance.
- CP-1D: 30 known facts: 15 reconciliation lines x 2 periods (net income to Adjusted Net Income to Adjusted EBITDA).
- not_golden: CP-1 (financial_gold), CP-MODEL, CP-5.

## Period labelling
Calendar fiscal year. Context uses q2-2025 / q2-2024. Prior is q2-2024 because the 10-Q prints the two quarters side by side; same kind and earlier, as the form requires. Codex cp1b_delta_inputs.json uses Q1-2025 vs Q2-2025 instead; that sequential pair is not covered.

## Judgment calls
- Amounts printed in USD thousands are stored as printed (e.g. "294341", scale thousands); millions-printed amounts stay millions. derive.py converts mixed scales exactly.
- Brief dates Amendment No. 4 at 2024-08-05; that is the filing date of the 10-Q carrying it. The amendment is dated 2024-05-30.
- The revolver commitment of $600.0m is from Amendment No. 5 (2025-04-30), after Amendment No. 4.
- Printed dash recorded as 0 (Illinois EO settlements, Q2 2024).
- Guidance recorded missing; the 2024-05-30 8-K 2024 interest outlook is stale and noted only in gap_reason.
- Context: peer_source left at the form default; `basis` is `auto` by choice because no market data exists (the form default for a listed issuer is `issuer_trading`); listed_equity true with market data empty; management_bridge false; guarantors lists only the parent; sponsor from the 10-K risk factor.
- Debt facts are tagged module CP-1B (no debt module in this pathway).

## Checks run
`python3 -I derive.py` exit 0 (all derivations and subtotal checks agree). `python3 -I cases/goldens/check.py cases/goldens/shc-earnings-update` exit 0.

## Open questions
See `needs_user_input` in module_golden.json (market data, ratings, quotes, guarantor names, guidance, bridge).

Not verified: Q2 2024 as-originally-filed values vs the recast prior-year column: only the CP-1D Business optimization / Secondary offering costs split (593 + 20 = 613) is recorded as a limitation; other lines were not compared; the margin tier at 2025-06-30; no independent re-extraction of quotes beyond the checker; nothing live-run against a model.

## Step 4 re-tag (2026-11-02)

Oracle preparer: mx-feature (Step 4 preparer). Files changed: this case's `module_golden.json` and `cases/goldens/line-exceptions.json`. Values, evidence and statuses of every kept fact are unchanged. Target module for every re-tag is CP-1 (in this pathway plan: `deploy_vii.contracts.PATHWAY_MODULES`).

### Counts per module (as tagged before this step)

| Module | Re-tagged | Removed | Covered by financial_gold |
|---|---|---|---|
| CP-0 | 0 | 14 | 0 |
| CP-1B | 9 | 15 | 2 |
| total | 9 | 29 | 2 |

Facts before: 97; after: 66. not_golden items added: 31.

### Re-tagged to CP-1 (old fact_id -> new fact_id; CP-1 column)

Where CP-1 builds them: T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation). The rows are written by `_facilities` (model_interface.py:465-497); row ids are the model's `facility_id`, so a row-key locator finds them.

- `CP-1B.debt_context.Term loan due 2031 (Refinancing Term Loans).principal_outstanding_gross.2025-06-30` -> `CP-1.debt_context.Term loan due 2031 (Refinancing Term Loans).principal_outstanding_gross.2025-06-30`: T4.18 column principal
- `CP-1B.debt_context.Term loan due 2031 (Refinancing Term Loans).carrying_amount_net.2025-06-30` -> `CP-1.debt_context.Term loan due 2031 (Refinancing Term Loans).carrying_amount_net.2025-06-30`: T4.18 column carrying_value
- `CP-1B.debt_context.Secured notes due 2031.principal_outstanding_gross.2025-06-30` -> `CP-1.debt_context.Secured notes due 2031.principal_outstanding_gross.2025-06-30`: T4.18 column principal
- `CP-1B.debt_context.Term loan due 2031 (Refinancing Term Loans).rate_floor` -> `CP-1.debt_context.Term loan due 2031 (Refinancing Term Loans).rate_floor`: T4.18 column floor_bps
- `CP-1B.debt_context.Term loan due 2031 (Refinancing Term Loans).maturity_date` -> `CP-1.debt_context.Term loan due 2031 (Refinancing Term Loans).maturity_date`: T4.18 column maturity_date
- `CP-1B.debt_context.Secured notes due 2031.coupon_fixed` -> `CP-1.debt_context.Secured notes due 2031.coupon_fixed`: T4.18 column fixed_rate
- `CP-1B.debt_context.Secured notes due 2031.maturity_date` -> `CP-1.debt_context.Secured notes due 2031.maturity_date`: T4.18 column maturity_date
- `CP-1B.debt_context.Revolving Credit Facility.drawn_balance.2025-06-30` -> `CP-1.debt_context.Revolving Credit Facility.drawn_balance.2025-06-30`: T4.18 column drawn_amount
- `CP-1B.debt_context.Revolving Credit Facility.maturity_date` -> `CP-1.debt_context.Revolving Credit Facility.maturity_date`: T4.18 column maturity_date

### Removed, covered by financial_gold

- `CP-1B.period_comparison.Consolidated.net_income.2025-06-30`: financial_gold net_income_total FY2025Q2 (same metric, period and value)
- `CP-1B.debt_context.Total long-term debt (term loan + secured notes).principal_outstanding_gross.2025-06-30`: financial_gold total_debt_principal FY2025Q2 (same metric, period and value)

### Removed (no module in the pathway plan writes the fact as a field or register cell)

- `CP-1B.period_comparison.Sterigenics.net_revenues_change.2025-06-30`: period_comparison / Sterigenics / net_revenues_change @ 2025-06-30: no module field; CP-1B writes T1B.1 consolidated paired results, T1B.2 cash_closing/total_debt/net_debt and T1B.3 evidence rows (src/deploy_vii/bindings/cp1b.py:25-53); segment rows and net income are not written (T1B.1 holds consolidated revenue and adjusted EBITDA only)
- `CP-1B.period_comparison.Nordion.net_revenues_change.2025-06-30`: period_comparison / Nordion / net_revenues_change @ 2025-06-30: no module field; CP-1B writes T1B.1 consolidated paired results, T1B.2 cash_closing/total_debt/net_debt and T1B.3 evidence rows (src/deploy_vii/bindings/cp1b.py:25-53); segment rows and net income are not written (T1B.1 holds consolidated revenue and adjusted EBITDA only)
- `CP-1B.period_comparison.Nelson Labs.net_revenues_change.2025-06-30`: period_comparison / Nelson Labs / net_revenues_change @ 2025-06-30: no module field; CP-1B writes T1B.1 consolidated paired results, T1B.2 cash_closing/total_debt/net_debt and T1B.3 evidence rows (src/deploy_vii/bindings/cp1b.py:25-53); segment rows and net income are not written (T1B.1 holds consolidated revenue and adjusted EBITDA only)
- `CP-1B.period_comparison.Sterigenics.segment_income_change.2025-06-30`: period_comparison / Sterigenics / segment_income_change @ 2025-06-30: no module field; CP-1B writes T1B.1 consolidated paired results, T1B.2 cash_closing/total_debt/net_debt and T1B.3 evidence rows (src/deploy_vii/bindings/cp1b.py:25-53); segment rows and net income are not written (T1B.1 holds consolidated revenue and adjusted EBITDA only)
- `CP-1B.period_comparison.Nordion.segment_income_change.2025-06-30`: period_comparison / Nordion / segment_income_change @ 2025-06-30: no module field; CP-1B writes T1B.1 consolidated paired results, T1B.2 cash_closing/total_debt/net_debt and T1B.3 evidence rows (src/deploy_vii/bindings/cp1b.py:25-53); segment rows and net income are not written (T1B.1 holds consolidated revenue and adjusted EBITDA only)
- `CP-1B.period_comparison.Nelson Labs.segment_income_change.2025-06-30`: period_comparison / Nelson Labs / segment_income_change @ 2025-06-30: no module field; CP-1B writes T1B.1 consolidated paired results, T1B.2 cash_closing/total_debt/net_debt and T1B.3 evidence rows (src/deploy_vii/bindings/cp1b.py:25-53); segment rows and net income are not written (T1B.1 holds consolidated revenue and adjusted EBITDA only)
- `CP-1B.period_comparison.Consolidated.net_income.2024-06-30`: period_comparison / Consolidated / net_income @ 2024-06-30: no module field; CP-1B writes T1B.1 consolidated paired results, T1B.2 cash_closing/total_debt/net_debt and T1B.3 evidence rows (src/deploy_vii/bindings/cp1b.py:25-53); segment rows and net income are not written (T1B.1 holds consolidated revenue and adjusted EBITDA only)
- `CP-1B.period_comparison.Consolidated.net_income_change.2025-06-30`: period_comparison / Consolidated / net_income_change @ 2025-06-30: no module field; CP-1B writes T1B.1 consolidated paired results, T1B.2 cash_closing/total_debt/net_debt and T1B.3 evidence rows (src/deploy_vii/bindings/cp1b.py:25-53); segment rows and net income are not written (T1B.1 holds consolidated revenue and adjusted EBITDA only)
- `CP-1B.debt_context.Term loan due 2031 (Refinancing Term Loans).original_principal_at_amendment_no4`: debt_context / Term loan due 2031 (Refinancing Term Loans) / original_principal_at_amendment_no4: no module field; CP-1B writes T1B.1 consolidated paired results, T1B.2 cash_closing/total_debt/net_debt and T1B.3 evidence rows (src/deploy_vii/bindings/cp1b.py:25-53): T1B.2 holds cash_closing/total_debt/net_debt only; CP-1 writes no weighted-average rate, amendment, step-down or LC cell (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-1B.debt_context.Term loan due 2031 (Refinancing Term Loans).amendment_no4_date`: debt_context / Term loan due 2031 (Refinancing Term Loans) / amendment_no4_date: no module field; CP-1B writes T1B.1 consolidated paired results, T1B.2 cash_closing/total_debt/net_debt and T1B.3 evidence rows (src/deploy_vii/bindings/cp1b.py:25-53): T1B.2 holds cash_closing/total_debt/net_debt only; CP-1 writes no weighted-average rate, amendment, step-down or LC cell (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-1B.debt_context.Term loan due 2031 (Refinancing Term Loans).margin_step_down`: debt_context / Term loan due 2031 (Refinancing Term Loans) / margin_step_down: no module field; CP-1B writes T1B.1 consolidated paired results, T1B.2 cash_closing/total_debt/net_debt and T1B.3 evidence rows (src/deploy_vii/bindings/cp1b.py:25-53): T1B.2 holds cash_closing/total_debt/net_debt only; CP-1 writes no weighted-average rate, amendment, step-down or LC cell (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-1B.debt_context.Term loan due 2031 (Refinancing Term Loans).margin_step_down_threshold_senior_secured_leverage`: debt_context / Term loan due 2031 (Refinancing Term Loans) / margin_step_down_threshold_senior_secured_leverage: no module field; CP-1B writes T1B.1 consolidated paired results, T1B.2 cash_closing/total_debt/net_debt and T1B.3 evidence rows (src/deploy_vii/bindings/cp1b.py:25-53): T1B.2 holds cash_closing/total_debt/net_debt only; CP-1 writes no weighted-average rate, amendment, step-down or LC cell (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-1B.debt_context.Term loan due 2031 (Refinancing Term Loans).weighted_average_interest_rate_three_months.2025-06-30`: debt_context / Term loan due 2031 (Refinancing Term Loans) / weighted_average_interest_rate_three_months @ 2025-06-30: no module field; CP-1B writes T1B.1 consolidated paired results, T1B.2 cash_closing/total_debt/net_debt and T1B.3 evidence rows (src/deploy_vii/bindings/cp1b.py:25-53): T1B.2 holds cash_closing/total_debt/net_debt only; CP-1 writes no weighted-average rate, amendment, step-down or LC cell (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-1B.debt_context.Term loan due 2031 (Refinancing Term Loans).weighted_average_interest_rate_three_months.2024-06-30`: debt_context / Term loan due 2031 (Refinancing Term Loans) / weighted_average_interest_rate_three_months @ 2024-06-30: no module field; CP-1B writes T1B.1 consolidated paired results, T1B.2 cash_closing/total_debt/net_debt and T1B.3 evidence rows (src/deploy_vii/bindings/cp1b.py:25-53): T1B.2 holds cash_closing/total_debt/net_debt only; CP-1 writes no weighted-average rate, amendment, step-down or LC cell (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-1B.debt_context.Term loan due 2031 (Refinancing Term Loans).amortization_rate_per_annum`: debt_context / Term loan due 2031 (Refinancing Term Loans) / amortization_rate_per_annum: no module field; CP-1B writes T1B.1 consolidated paired results, T1B.2 cash_closing/total_debt/net_debt and T1B.3 evidence rows (src/deploy_vii/bindings/cp1b.py:25-53): T1B.2 holds cash_closing/total_debt/net_debt only; CP-1 writes no weighted-average rate, amendment, step-down or LC cell (T4.18 Debt Facility Register (src/deploy_vii/model_interface.py:75-85 columns, :465-497 rows written; src/deploy_vii/financial_contracts.py:227-258 FacilityObservation))
- `CP-0.identity.Registrant.ticker_exchange`: CP-0 identity/document fact (identity / Registrant / ticker_exchange) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.Registrant.state_of_incorporation`: CP-0 identity/document fact (identity / Registrant / state_of_incorporation) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.Registrant.commission_file_number`: CP-0 identity/document fact (identity / Registrant / commission_file_number) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.Registrant.filer_category`: CP-0 identity/document fact (identity / Registrant / filer_category) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.Registrant.shares_outstanding_2025-07-29`: CP-0 identity/document fact (identity / Registrant / shares_outstanding_2025-07-29) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.Registrant.principal_executive_office`: CP-0 identity/document fact (identity / Registrant / principal_executive_office) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.Registrant.sponsors`: CP-0 identity/document fact (identity / Registrant / sponsors) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.Credit borrower.borrower_name`: CP-0 identity/document fact (identity / Credit borrower / borrower_name) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.Listed parent (Holdings).parent_name`: CP-0 identity/document fact (identity / Listed parent (Holdings) / parent_name) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.Credit borrower.guarantors`: CP-0 identity/document fact (identity / Credit borrower / guarantors) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.identity.Registrant.reportable_segments`: CP-0 identity/document fact (identity / Registrant / reportable_segments) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.documents.Q2 2025 Form 10-Q.signature_date`: CP-0 identity/document fact (documents / Q2 2025 Form 10-Q / signature_date) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.documents.Registrant.fiscal_year_end`: CP-0 identity/document fact (documents / Registrant / fiscal_year_end) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)
- `CP-0.documents.Q2 2025 Form 10-Q.reporting_unit`: CP-0 identity/document fact (documents / Q2 2025 Form 10-Q / reporting_unit) has no CP-0 field; CP-0 build_readiness writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run (src/deploy_vii/readiness.py:474)

### Kept although the rules above would move them

- `CP-1B.period_comparison.Sterigenics.net_revenues.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1B.period_comparison.Sterigenics.net_revenues.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1B.period_comparison.Nordion.net_revenues.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1B.period_comparison.Nordion.net_revenues.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1B.period_comparison.Nelson Labs.net_revenues.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1B.period_comparison.Nelson Labs.net_revenues.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1B.period_comparison.Sterigenics.segment_income.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1B.period_comparison.Sterigenics.segment_income.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1B.period_comparison.Nordion.segment_income.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1B.period_comparison.Nordion.segment_income.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1B.period_comparison.Nelson Labs.segment_income.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1B.period_comparison.Nelson Labs.segment_income.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Net income (loss).amount.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Net income (loss).amount.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Amortization of intangible assets.amount.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Amortization of intangible assets.amount.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Share-based compensation.amount.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Share-based compensation.amount.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Loss on refinancing of debt.amount.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Loss on refinancing of debt.amount.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.(Gain) loss on FX and derivatives not designated as hedges, net.amount.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.(Gain) loss on FX and derivatives not designated as hedges, net.amount.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Business optimization expenses.amount.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Business optimization expenses.amount.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Professional services relating to EO sterilization facilities.amount.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Professional services relating to EO sterilization facilities.amount.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Illinois EO litigation settlements.amount.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Illinois EO litigation settlements.amount.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Accretion of asset retirement obligations.amount.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Accretion of asset retirement obligations.amount.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Income tax benefit associated with pre-tax adjustments.amount.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Income tax benefit associated with pre-tax adjustments.amount.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Adjusted Net Income.amount.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Adjusted Net Income.amount.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Interest expense, net.amount.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Interest expense, net.amount.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Depreciation.amount.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Depreciation.amount.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Income tax provision applicable to Adjusted Net Income.amount.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Income tax provision applicable to Adjusted Net Income.amount.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Adjusted EBITDA.amount.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1D.ebitda_reconciliation.Adjusted EBITDA.amount.2024-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1B.debt_context.Revolving Credit Facility.total_commitments.2025-06-30` (would be re-tagged to CP-1): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1B.debt_context.Revolving Credit Facility.letters_of_credit_issued.2025-06-30` (would be removed): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-1B.debt_context.Revolving Credit Facility.availability.2025-06-30` (would be removed as covered by financial_gold): derive.py reads this fact by id or by topic/subject/field (derive.py is outside the preparer's file list)
- `CP-0.identity.Registrant.legal_name` (would be removed): mapping.json entry (scored; leave it)

### For the controller

- `mapping.json` still lists 40 of the moved fact_ids under `unmapped` (preparer may not edit it); `load_mapping` will refuse it until they are dropped or renamed.
- `line-exceptions.json` updated: entries of removed facts dropped, entries of re-tagged facts renamed (quote_misses 83 -> 52, printed_unplaced 2 -> 1 across all cases); `MAX_QUOTE_EXCEPTIONS` in tests/test_goldens_lines.py stays 83 (shrink-only constant, may be lowered by its owner).

- derive.py hard-codes CP-1B/CP-1D fact ids, so CP-1D reconciliation lines and CP-1B segment lines (c-facts), plus the revolver commitment/LC/availability ids (re-tag/cover targets) stay as they are until derive.py is updated.

Not verified: no module run (the mapping is read from code, not from a result); the pytest suite (no venv); that a model's CP-1 T4.18 carries a row for each re-tagged facility (the scorer reports a missing row as missing); unit agreement for margin/floor/rate re-tags (golden percent vs CP-1 basis points or decimal_percent; the scorer reports unit problems rather than a match); `mapping.json` against the changed goldens (not edited, not loaded).
