# Mapping report: natl-portfolio-decision (re-run, fix round 1)

Base 6da4c9f1, scorer c92dc5c6, rulings in .superpowers/sdd/2026-10-31-model-testing-framework/mapping-rerun-fix-r1.md. Preparer: mx-feature (Task 6 preparer, re-run). Module code unchanged since 9c018f76.

## Per module

| Module | Entries | Unmapped | Facts | Commit |
|---|---|---|---|---|
| CP-0 | 1 (row-id) | 2 | 3 | 0c39637aeb31cdc31892c61878e29264411e79a7 |
| CP-1 | 36 (row-key + period_ref) | 76 | 112 | 6c81d0bae47e515fec33f3c048f594b9e6de5e47 |
| CP-2 | 0 | 33 | 33 | cffdf9f47dd4f6bab5269df290d2bcd9b1171618 |

CP-4 (51) is out of plan: no entry, no unmapped item, no commit key.

Files: CP-0: src/deploy_vii/readiness.py, cp0_workflow.py, src/deploy_workflow/context.py. CP-1: src/deploy_vii/model_interface.py (T4.14, T4.15, T4.18), canonical_tables.py, cp1_workflow.py, financial_contracts.py, financial_adapter.py, src/deploy_workflow/financial_workflow.py. CP-2: src/deploy_vii/cp2_synthesis.py, bindings/cp2.py, src/deploy_workflow/owners/cp2.py.

## CP-1 entries (36)
- 25 flow facts in T4.15 (row_key `metric_id`, period_ref T4.14 `end_date` + `period_type` QUARTER, or FY for FY2024): revenue, CFO (cfo_ncfo), adjusted_EBITDA (adjusted_ebitda), reported_EBITDA (ebitda; gold is missing), operating_profit (ebit).
- 4 cash facts (cash_and_equivalents), period_type PERIOD_END: FY2025Q1-Q3 and FY2024Q4 (2024-12-31). Per the period rule this is a model convention (financials prompt, rule i); a model that puts balances on QUARTER periods scores missing for them, to be revisited after the pilot.
- 7 T4.18 facts, row_key `facility_name` (aliases: source spellings), period_ref `end_date` 2025-09-30 + PERIOD_END. Undated terms (maturity, coupon) read the current-period row. Fields: principal, maturity_date, fixed_rate (decimal_percent; scorer converts), carrying_value.

## Unmapped reasons
- DA (5): CP-1 writes outflow metrics as -abs, the gold is positive.
- total_debt (5): gold includes finance leases; CP-1 keeps lease_obligations separate.
- capex_signed_cashflow (5): gold is capitalized software and IP purchases, which capex_and_intangible_investment includes.
- FY2024:cash: same locator as FY2024Q4:cash.
- capex_payment_amount, net income, balance-sheet totals, principal: no ACCOUNT_FIELDS id (or sign differs).
- CP-1 restatement text (15): no CP-1 field for narrative.
- CP-2 (33): `credit_synthesis` is judgments only; no figures.
- CP-0 documents (2): period is free text at a P3 row keyed by the pack's source_id.

## Modules over 20% unmapped
CP-0 2/3, CP-1 76/112 (68%), CP-2 33/33, for the reasons above.

Not verified: `load_mapping` was not run (no Python); no real CP-1 result was read, so PERIOD_END as the period type of balances, facility_name wording and the T4.18 rows present at 2025-09-30 are inferred from code and the ruling; the T1/run/issuer locator was not exercised.
