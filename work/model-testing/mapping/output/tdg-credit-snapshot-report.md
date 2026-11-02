# tdg-credit-snapshot mapping report (re-run, base 6da4c9f1, with period_ref)

Output: `cases/goldens/tdg-credit-snapshot/mapping.json`. Preparer mx-feature (Task 6 preparer, re-run). 235 in-plan facts: 95 entries (1 row-id, 94 row-key + period_ref), 140 unmapped (fix round 1).

## Per module

| Module | Files | Commit | Row-id entries | Row-key entries | Unmapped | Facts |
|---|---|---|---|---|---|---|
| CP-0 | `src/deploy_vii/readiness.py` | eeab0b8fecda6ee1a74b16c66711503e12928583 | 1 | 0 | 4 | 5 |
| CP-1 | `src/deploy_vii/canonical_tables.py`, `model_interface.py`, `statement_view.py`, `cp1_workflow.py` | df26ea82249fc062a8beb8dba3d51f1caf5fdf23 | 0 | 94 (34 T4.15, 60 T4.18) | 75 | 169 |
| CP-1A | `src/deploy_vii/business_context.py`, `src/deploy_workflow/owners/cp1a.py` | 0daac2cc5ba33d477b8143d3373bc75f622de5a4 | 0 | 0 | 32 | 32 |
| CP-2 | `src/deploy_vii/cp2_synthesis.py`, `src/deploy_workflow/owners/cp2.py` | cffdf9f47dd4f6bab5269df290d2bcd9b1171618 | 0 | 0 | 16 | 16 |
| CP-3 | `src/deploy_vii/cp3_relative_value.py`, `src/deploy_workflow/owners/cp3.py` | 68ebc369347121ce505488a8808661e643751d52 | 0 | 0 | 1 | 1 |
| CP-4 | `src/deploy_vii/cp4_legal.py`, `src/deploy_workflow/owners/cp4.py` | a2243308037a6bc6b86536ce5c801b0c73f01271 | 0 | 0 | 12 | 12 |

## Entries
- CP-0 legal_name -> `T1 / run / issuer / null`.
- CP-1 `CP-1.fin.*`, 34 facts -> `T4.15`, field `value`, `row_key` on `metric_id` with the code-fixed account id as alias, `period_ref` T4.14 `{end_date, period_type}` (flows: QUARTER, FY for FY2024; cash: PERIOD_END; end dates from financial_gold `periods`). Metric mapping (gold -> `ACCOUNT_FIELDS`): CFO -> cfo_ncfo; adjusted_EBITDA -> adjusted_ebitda; reported_EBITDA -> ebitda; revenue -> revenue; cash -> cash_and_equivalents (PERIOD_END, per the period rule); operating_profit -> ebit (IS `ebit` line); capex_signed_cashflow -> capex_and_intangible_investment (CFS `capex_total` link, prompt rule g).
- CP-1 debt and revolver goldens at 2024-12-28, 60 facts -> `T4.18`, `row_key` on `facility_name` (aliases: the golden subject and the source's note names), `period_ref` `{2024-12-28, PERIOD_END}`. Field map: principal_outstanding -> principal; carrying_amount_net -> carrying_value; maturity_date -> maturity_date; interest_rate -> fixed_rate; interest_rate_terms and drawn_rate_terms -> margin_or_coupon; commitments -> commitment; drawn_balance -> drawn_amount.

## Unmapped reasons (grouped)
- CP-1, 5 DA (sign: CP-1 writes -abs, gold positive), 5 total_debt (gold includes finance leases; CP-1 keeps lease_obligations separate), 1 cash FY2024 (same locator as CP-1.fin.TDG:cash:FY2024Q4).
- CP-1, 63 `CP-1.fin.*` (original group): capex_payment_amount (positive; CP-1 has one signed capex account); principal and total_financing_debt_including_finance_leases (no account id); and the balance-sheet, equity, net-income and long-term-debt metrics (not in `ACCOUNT_FIELDS`; their statement-view cells key the model period_id in `field`).
- CP-1, 1 debt fact: finance lease at 2024-09-30 (10-K balance): QUARTER, FY or PERIOD_END period could hold it, so `period_type` would be a guess.
- CP-0, 4 `period_covered`: row id is the staged source_id and P3 has no key cell naming the filing.
- CP-1A, 32: rows numbered `r01..`; keyed registers drop the row-header column; transaction_summary and events_timeline keep their first column but have no numeric field; values sit in prose.
- CP-2, 16: synthesis prose only; figures live in CP-1.
- CP-3, 1: `T3.3/none` exists only for an empty register.
- CP-4, 12: numbered covenant rows without a key fact; thresholds are text cells.

## Modules over 20% unmapped
CP-0 (4/5), CP-1A (32/32), CP-2 (16/16), CP-3 (1/1), CP-4 (12/12): reasons above. CP-1 is 75/169 (44%): mostly balance-sheet and net-income gold metrics that CP-1 holds only as statement-view cells keyed by the model's period id.

Not verified: `load_mapping` was not run (no Python); T4.14 `period_type` PERIOD_END for instants (cash, T4.18) is a model convention (financials.json:66), not forced by code; sign and unit agreement between gold and CP-1 for DA, capex and `fixed_rate` (decimal_percent) is left to the scorer; the source note names used as aliases were taken from golden evidence quotes, not from a real CP-1 run; no real CP-1 result layout was inspected.
