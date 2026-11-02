# Mapping report: bgs-relative-value (re-run with period_ref, base 6da4c9f1 + c92dc5c6)

Preparer: mx-feature (Task 6 preparer, re-run). Commits are `git log -1 --format=%H 6da4c9f1 -- <files>`.

## Per module

| Module | Files read | Commit | Entries (all row-key unless noted) | Unmapped | Facts |
|---|---|---|---|---|---|
| CP-0 | src/deploy_vii/readiness.py, src/deploy_workflow/owner_workflow.py | 9abad5b6d071e6d297366d0d1777689bfa2ec82e | 1 (row-id) | 0 | 1 |
| CP-1 | src/deploy_vii/model_interface.py, canonical_tables.py, statement_history.py, statement_validation.py (account ids), financial_contracts.py, financial_periods.py | d6ca9b631717913fed168d809de9343aeaa35fac | 65 (47 T4.15, 18 T4.18) | 60 | 125 |
| CP-2 | src/deploy_vii/cp2_synthesis.py, src/deploy_workflow/owners/cp2.py | cffdf9f47dd4f6bab5269df290d2bcd9b1171618 | 0 | 15 | 15 |
| CP-3 | src/deploy_vii/cp3_relative_value.py, src/deploy_workflow/owners/cp3.py | 68ebc369347121ce505488a8808661e643751d52 | 0 | 1 | 1 |

CP-1 entries: 47 T4.15 (key cell `metric_id`, field `value`) + 18 T4.18 (key cell `facility_name`). All use `period: null` and `period_ref` T4.14 (`id_field` period_id) matching `end_date` and `period_type`. Total: 66 entries, 76 unmapped, 142 facts.

## Locator choices

- Period kind from financial_gold `periods`: quarter -> QUARTER, annual -> FY, year_to_date_operand -> YTD plus `start_date`. CP-1's vocabulary is QUARTER, YTD, FY, LTM, PERIOD_END (FinancialPeriod.period_type). Balance metrics (cash, total_debt) and T4.18 facts at 2025-06-28 use QUARTER too, because T4.15 writes every account for every declared period; a model that books balances on a separate PERIOD_END period would score missing_in_output (fair result, noted as a risk).
- T4.15 aliases are CP-1's code-fixed ids (ACCOUNT_FIELDS, model_interface.py): operating_profit -> ebit; reported_EBITDA (and the YTD operand) -> ebitda; adjusted_EBITDA (and operand) -> adjusted_ebitda; DA -> depreciation_amortization; CFO -> cfo_ncfo; capex_signed_cashflow -> capex_and_intangible_investment; cash -> cash_and_equivalents; revenue, total_debt same name.
- T4.18: field map principal_outstanding -> principal, carrying_amount -> carrying_value, maturity_date, coupon_fixed -> fixed_rate (decimal_percent, a percentage-point unit), sofr_floor -> floor_bps (golden is a gap), commitment, drawn_balance -> drawn_amount. Aliases are source facility names only.
- ebit and operating income are treated as the same account; the ytd-operand periods may not be declared by the model (then missing_in_output).

## Unmapped reasons (grouped)

- CP-1 (60): net income total/attributable (10: no net-income id in ACCOUNT_FIELDS); current/total assets, liabilities, equity (25: not in ACCOUNT_FIELDS); finance-lease liability and financing debt incl. leases (10: no id); aggregate principal (5: no id, no sum cell); capex_payment_amount (5: shares the capex account with capex_signed_cashflow, and T4.15 writes outflows negative); principal_component (4: identical subject text would collide row keys); margin_sofr (1: T4.18 holds spread_bps in basis points, golden is percent; scorer rejects the unit).
- CP-2 (15): credit-synthesis prose at model-chosen rows; no cell keyed by item.
- CP-3 (1): no quotes, so an Insufficient Information preference; no fixed observed-quotes row.

## Over 20% unmapped

CP-1: 60 of 125 (48%), reasons above. CP-2 and CP-3: 100%, as before.

Not verified: `load_mapping` and the scorer were not run; period_type values and the QUARTER choice for balance items rest on reading FinancialPeriod and the T4.14/T4.15 builders, not on a live CP-1 result; whether the model declares YTD operand periods or names facilities as aliased is untested.

## Fix round 1 (rulings in .superpowers/sdd/2026-10-31-model-testing-framework/mapping-rerun-fix-r1.md)

- Balance items (`cash`, `total_debt`) and all 18 T4.18 entries now match `period_type` PERIOD_END (instants), replacing QUARTER. Flows stay QUARTER, FY or YTD (with start_date).
- Five `DA` entries unmapped: CP-1 writes outflow metrics as -abs, the gold is positive.
- `cash` and `total_debt` for FY2024 unmapped as "same locator as" the FY2024Q4 fact.
- margin_sofr stays unmapped (bps cell vs percent golden). `sofr_floor` entries are kept: the golden is a gap and BGS's list does not unmap them.
- reported_EBITDA_ytd_operand stays on `ebitda` (the table row "*_ytd_operand -> adjusted_ebitda" is read as adjusted_EBITDA's operand only; the reported operand is a reported-EBITDA value).
- Counts now: CP-1 58 entries (40 T4.15, 18 T4.18) and 67 unmapped of 125; total 59 entries, 83 unmapped of 142.

Not verified: `load_mapping` and the scorer were not run; PERIOD_END for instants is a model convention (financials.json rule i), not forced by code.
