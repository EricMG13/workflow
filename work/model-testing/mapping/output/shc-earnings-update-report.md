# Mapping report: shc-earnings-update (re-run with period_ref, base 6da4c9f1 / scorer c92dc5c6)

Preparer: mx-feature (Task 6 preparer, re-run). Output: `cases/goldens/shc-earnings-update/mapping.json`.
222 in-plan facts, each once: 55 entries, 167 unmapped. Fix round 1 applied (mapping-rerun-fix-r1.md).

| Module | Entries | of which row-key + period_ref | Unmapped | Facts | Unmapped % |
|---|---|---|---|---|---|
| CP-0 | 2 | 0 | 0 | 2 | 0 |
| CP-1 | 46 | 46 | 119 | 165 | 72 |
| CP-1B | 7 | 0 | 18 | 25 | 72 |
| CP-1D | 0 | 0 | 30 | 30 | 100 |

## Files and commits
- CP-0: `src/deploy_vii/readiness.py`, `cp0_workflow.py`; eeab0b8fecda6ee1a74b16c66711503e12928583.
- CP-1: `src/deploy_vii/model_interface.py` (T4.14/T4.15/T4.18 rows; ACCOUNT_FIELDS; T4.18 columns), `financial_periods.py`, `bindings/cp1.py`, `src/deploy_workflow/financial_workflow.py`; 9a85a6942ca4a63bf4a6a1c49bf03efe1910f3d6.
- CP-1B: `src/deploy_workflow/earnings_workflow.py` (`compose_delta`), `bindings/cp1b.py`, `owners/cp1b.py`; 438317d342f7e0f93808d3d8c769887182162be2.
- CP-1D: `src/deploy_workflow/owners/cp1d.py`; 5d5b6861247f4165d23e46a05b935b1f16325d97.

## CP-1 entries (fix round 1)
- 38 T4.15 `CP-1.fin.*` facts, field `value`, row_key `metric_id`, period_ref on T4.14. Flows (QUARTER, or FY for FY2024): revenue, adjusted_EBITDA -> adjusted_ebitda, CFO -> cfo_ncfo, operating_profit -> ebit, reported_EBITDA -> ebitda, capex_signed_cashflow -> capex_and_intangible_investment (5 periods each, 30 facts). Instants (period_type PERIOD_END, never end_date alone): cash -> cash_and_equivalents and total_debt_carrying -> total_debt, 4 quarter-ends each (8 facts).
- FY2024 cash and total_debt_carrying are unmapped as the Q4 twin: same locator as the FY2024Q4 fact.
- DA (5) unmapped: CP-1 writes outflow metrics as -abs, the gold is positive.
- 8 T4.18 facts (term loan principal, carrying value, maturity; secured notes principal, coupon, maturity; revolver drawn, maturity): row_key `facility_name` with source-name aliases, period_ref end_date 2025-06-30 plus period_type PERIOD_END. Period-less facts use that row.
- Other modules unchanged.

## Unmapped reasons, grouped
- CP-1 (119): no T4.15 metric id for debt, lease or liquidity components and totals (66); net income and balance-sheet totals are statement lines (35); DA sign (5); capex_payment_amount sign (5); gold total_debt (5; its locator, T4.15 total_debt PERIOD_END, is taken by the total_debt_carrying entries for the same periods, FY2024 via CP-1.fin.SHC:total_debt_carrying:FY2024Q4); FY2024 twins of cash and carrying debt (2); the T4.18 rate floor, basis points vs a percent golden (1).
- CP-1B segment revenue and income (12): T1B.1 has consolidated rows only. CP-1B debt terms and revolver (6): no debt-terms table.
- CP-1D (30): management-bridge rows (none in this case), 10-Q lines, one LTM period.

## Modules over 20% unmapped
CP-1 (72%): most gold metrics have no CP-1 account id (see above). CP-1B (72%) and CP-1D (100%): outside the T1B/T1D tables.

Not verified: `load_mapping` was not run (no Python by rule); coverage (222, unique, none missing) checked with jq. Instants (cash, carrying debt, T4.18) assume the model declares PERIOD_END periods (a model convention, revisited after the pilot). Facility aliases are plausible source names, not seen in a result. Period-less facts are scored on the 2025-06-30 facility row.
