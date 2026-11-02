# Mapping report: ihrt-distressed-restructuring (re-run, period_ref)

Base 6da4c9f1 (period_ref per step 10). Preparer: mx-feature (Task 6 preparer, re-run). Output: `cases/goldens/ihrt-distressed-restructuring/mapping.json`.
197 in-plan facts: 63 entries (2 fixed row id, 61 row-key; 59 of them CP-1 with period_ref, 2 CP-2H), 134 unmapped. Fix round 1 applied (mapping-rerun-fix-r1.md).

## Per module

| Module | Files read | Commit (`git log -1 6da4c9f1 -- files`) | Entries (row-id / row-key) | Unmapped | Facts |
|---|---|---|---|---|---|
| CP-0 | `src/deploy_vii/readiness.py`, `cp0_workflow.py`, `src/deploy_workflow/context.py` | 0c39637aeb31cdc31892c61878e29264411e79a7 | 1 / 0 | 0 | 1 |
| CP-1 | `src/deploy_vii/model_interface.py` (T4.14-T4.18), `canonical_tables.py`, `financial_adapter.py`, `cp1_workflow.py`, `src/deploy_workflow/financial_workflow.py` | 9a85a6942ca4a63bf4a6a1c49bf03efe1910f3d6 | 0 / 59 | 56 | 115 |
| CP-1A | `src/deploy_vii/business_context.py`, `src/deploy_workflow/owners/cp1a.py` | 0daac2cc5ba33d477b8143d3373bc75f622de5a4 | 1 / 0 | 3 | 4 |
| CP-2 | `src/deploy_vii/cp2_synthesis.py`, `owners/cp2.py` | cffdf9f47dd4f6bab5269df290d2bcd9b1171618 | 0 / 0 | 7 | 7 |
| CP-2H | `src/deploy_workflow/owners/cp2h.py` | 5149ddadf64d5b9be4f327750db39a928ff66a23 | 0 / 2 | 0 | 2 |
| CP-4 | `src/deploy_vii/cp4_legal.py`, `owners/cp4.py` | a2243308037a6bc6b86536ce5c801b0c73f01271 | 0 / 0 | 68 | 68 |

## CP-1 entries (69)

- 45 `CP-1.fin.*` facts -> T4.15 field `value`, row_key `metric_id` with the code-fixed id as alias (`ACCOUNT_FIELDS`):
  revenue; operating_profit->ebit; reported_EBITDA->ebitda; adjusted_EBITDA->adjusted_ebitda; DA->depreciation_amortization;
  CFO->cfo_ncfo; capex_signed_cashflow->capex_and_intangible_investment; cash->cash_and_equivalents; total_debt->total_debt.
  `period: null` with `period_ref` T4.14 `period_id` matching `end_date` from the gold period and `period_type` QUARTER (FY for FY2023).
- 24 debt-register facts -> T4.18 fields principal, drawn_amount, maturity_date, fixed_rate, spread_bps, floor_bps, commitment,
  row_key `facility_name` (golden subject; no aliases, the key text is model-written) with `period_ref` end_date 2024-09-30, QUARTER.
  Time-invariant terms (maturity, coupon, margin, floor) use the same Q3 2024 row because T4.18 always writes a `period_id`.

## Unmapped reasons (grouped)

- CP-1 (46): 8 gold metrics x 5 periods with no T4.15 metric id (net_income_total, net_income_attributable_parent, principal,
  current_assets, current_liabilities, total_assets, total_liabilities, total_equity); capex_payment_amount x 5 (shares the
  capex_and_intangible_investment id, outflow-negative, with capex_signed_cashflow, which is mapped); 1 net debt fact (no CP-1 cell).
  Total 45 + 1.
- CP-1A (3): transaction rows are `r01..` in model order; the figure sits inside prose, and the key cell is the value itself.
- CP-2 (7): model judgments only; no debt-stack total or maturity year.
- CP-2H (2): rating rows come from context ratings (empty here); a missing rating has no row.
- CP-4 (68): covenant registers are header-keyed (header is not a fact field), no row_key; exchange amounts, dates, TSA support, credit-agreement terms have no fixed table or field.

## Over 20% unmapped

CP-2, CP-2H, CP-4 (100%), CP-1A (75%): reasons above. CP-1 is 40% unmapped (46 of 115): no CP-1 metric or cell exists.

Not verified: `load_mapping` not run (no Python). No real CP-1 run output was inspected, so these were read from code only: T4.14 `period_type` vocabulary (QUARTER, FY) and ISO `end_date` text; that operating_profit equals CP-1 `ebit` and reported_EBITDA equals `ebitda`; that balance metrics (cash, total_debt) sit on the QUARTER row; and the scorer's treatment of spread_bps and floor_bps (basis points) and fixed_rate (decimal_percent) against percent goldens.

## Fix round 1 changes

- DA x5 unmapped (CP-1 writes outflows as -abs; the gold is positive).
- cash and total_debt at the four quarters now match period_type PERIOD_END; all T4.18 entries PERIOD_END (instants). The FY2023
  cash and total_debt twins are unmapped ("same locator as" the FY2023Q4 fact). Model convention: balances on PERIOD_END periods (revisit after the pilot).
- Counts now: CP-1 entries 59 (T4.15 38, T4.18 21), CP-1 unmapped 56 (the per-module table above is updated).
- Unmapped as bps vs percent golden: TLF2026 and ITLF2026 margin_over_term_sofr, ITLF2026 term_sofr_floor.
- CP-2H Moody and S&P ratings now row-key entries: T2R.2, key field `agency`, aliases "Moody's" / "S&P", field `rating`, period null (code-fixed agency names). CP-2H is 0 unmapped.

Not verified (added): the PERIOD_END convention is a model convention, not forced by code; the CP-2H register carries Moody's and S&P rows only when context ratings supply them.
