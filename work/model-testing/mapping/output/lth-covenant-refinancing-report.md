# Mapping report: lth-covenant-refinancing (re-run, base 6da4c9f1)

File: `cases/goldens/lth-covenant-refinancing/mapping.json` (51 entries, 180 unmapped, 231 in-plan facts; 44 CP-1 entries use `row_key` + `period_ref`).
Preparer `mx-feature (Task 6 preparer, re-run)`; reviewer `mx-precise (Task 6 review)`. The module code is unchanged since 9c018f76.

## Per module

| Module | Files read | Commit (`git log -1 6da4c9f1 -- files`) | Entries (row-id / row-key) | Unmapped | Facts |
|---|---|---|---|---|---|
| CP-0 | `src/deploy_vii/readiness.py`, `src/deploy_vii/cp0_workflow.py`, `src/deploy_workflow/context.py` | 0c39637aeb31cdc31892c61878e29264411e79a7 | 1 / 0 | 3 | 4 |
| CP-1 | `src/deploy_vii/canonical_tables.py`, `model_interface.py`, `statement_view.py`, `cp1_workflow.py` | df26ea82249fc062a8beb8dba3d51f1caf5fdf23 | 0 / 47 | 75 | 122 (111 `CP-1.fin.*`, 11 module) |
| CP-1A | `src/deploy_vii/business_context.py`, `src/deploy_workflow/owners/cp1a.py` | 0daac2cc5ba33d477b8143d3373bc75f622de5a4 | 2 / 0 | 8 | 10 |
| CP-2 | `src/deploy_vii/cp2_synthesis.py`, `src/deploy_workflow/owners/cp2.py` | cffdf9f47dd4f6bab5269df290d2bcd9b1171618 | 0 / 0 | 11 | 11 |
| CP-2D | `src/deploy_workflow/owners/cp2d.py` | 0898948fe3e709c91d1137d7e232bffb4bd410cb | 1 / 0 | 1 | 2 |
| CP-4 | `src/deploy_vii/cp4_legal.py`, `src/deploy_workflow/owners/cp4.py` | a2243308037a6bc6b86536ce5c801b0c73f01271 | 0 / 0 | 82 | 82 |

## Entries and their basis

- CP-0 `legal_name` -> `T1/run/issuer`, period null (`build_readiness` writes `pack.run.issuer_name`, the context `identity.issuer_name`).
- CP-1A `business_sector` -> `company_description/company/sector`; `geography_of_centers.countries` -> `company_description/company/country` (period null; fixed by `COMPANY_ROW` and the register columns; the text is model-written and carries a category label, so exact equality may fail).
- CP-2D `minimum_cash_m` -> `T2E.5/r04/value/2025-06-30` (`_number` positional row id, read by `cp2d_reader`; golden is `missing`, so a module that writes a value is scored invented, and a gap carries no period and scores `gap_ok`).

## Unmapped reasons, grouped

- CP-1 `fin.*` (111): CP-1 holds account metrics in T4.15 as rows (metric_id, period_id), field `value`, and statements in T4.4-T4.6 with the period id as the field. The metric ids are code-fixed, but `Fact.period` (and the T4.4-T4.6 field) is the `period_id` the model chose in its financial review. That id has no fixed format (`context_periods.resolve` matches T4.14 rows by fiscal fields, not by id), so a literal period string would be a guess. Metrics with a T4.15 id (revenue, adjusted_EBITDA, CFO, DA, cash, total_debt) say so; the other metrics (net income, operating profit, capex, finance leases, principal, reported EBITDA, balance-sheet totals) have no T4.15 account id either.
- CP-1 module facts (11): T4.18 (Debt Facility Register) holds the principal, commitment, drawn, maturity and rate fields in rows `(facility_id, period_id)`; `facility_name` is a real fact cell and would serve as a `row_key`, but the row period is the same model-chosen `period_id` (never null), so the period cannot be tied. The two margin facts have no CP-1 field (T4.18 holds `spread_bps` per facility, not a margin step-down at a date).
- CP-0 (3): no borrower-entity field; document `period_covered` appears only as model-assessed `P3/<source_id>/period` text.
- CP-1A (8): the owner name is the row header of `ownership_register` and T2D.2 (the first column is the row label, not a fact cell), so `row_key` cannot find it; the other profile details have no fixed slot.
- CP-2 (11): credit synthesis writes only model-judgment text and `cp1_references/refNN` copies; no debt-stack, cash or obligor field.
- CP-2D (1): `horizon_months` is always written as a known int 1-60 (cp2d.py:121), so the golden status missing cannot be met (golden ruling, step 4).
- CP-4 (82): cells are model-judgment text in rows numbered `rNN` by model list order; the covenant or document name is the row header, not a fact cell, so neither a row id nor a `row_key` works; there is no per-amendment table.

## Modules over 20% unmapped

CP-0 3/4, CP-1 122/122, CP-1A 8/10, CP-2 11/11, CP-2D 1/2, CP-4 82/82. The cause is the same throughout: golden facts follow filing content, while the module writes model-chosen row ids or period ids, or has no such field. A ruling that fixes the CP-1 period id convention (for example the context `qN-YYYY` / `fy-YYYY` strings, set by Python) would let T4.15 (about 60 metrics with an account id) and T4.18 (11 facts, via `row_key` on `facility_name`) be mapped; I did not assume it.

Not verified: `load_mapping` was not run (no Python by instruction); no CP-1 result was inspected, so the T4.15 and T4.18 layouts are read from `model_interface.py`, not from a run; the CP-2D period `2025-06-30` and the CP-0 issuer text were read from code and context; text equality for the CP-1A category-labelled cells was not tested.

## Update: period_ref ruling (CONTEXT step 10, scorer c92dc5c6)

CP-1 now has 44 `row_key` + `period_ref` entries and 78 unmapped; the other modules are unchanged. The Entries and CP-1 paragraphs above that call the period id unfixed are superseded for these facts.

- 36 `CP-1.fin.*` entries use T4.15, `row_key` field `metric_id`, field `value`, `period: null` and `period_ref` on T4.14 (`end_date`, `period_type` QUARTER/FY, plus `start_date` and YTD for the FY2024YTD operand). Gold metric -> CP-1 id (ACCOUNT_FIELDS) in the alias: revenue -> revenue; adjusted_EBITDA and adjusted_EBITDA_ytd_operand -> adjusted_ebitda; CFO -> cfo_ncfo; DA -> depreciation_amortization; cash -> cash_and_equivalents; total_debt -> total_debt; reported_EBITDA -> ebitda.
- 8 T4.18 entries use `row_key` field `facility_name` (aliases only Term Loan Facility / 2024 New Term Loans, Revolving Credit Facility / Revolver, the 6.000% notes name), `period_ref` end_date 2025-06-30 with period_type QUARTER (the balance-date quarter that CP-2D reads from T4.18). Fields: principal, drawn_amount, commitment, maturity_date, fixed_rate. The two facts with a null golden period (notes maturity, coupon) use the same balance-date quarter, an assumption.
- Unmapped in CP-1 (78): 75 `fin` facts whose metric has no code-fixed id or an unequal definition (operating_profit vs ebit, net_income_total, capex payment/signed vs capex_and_intangible_investment, current/total assets and liabilities, equity, finance leases, financing debt, principal, net income attributable); 2 margin facts (no CP-1 field); `drawn_usd_millions` (same locator as `drawn_principal`).

Not verified: `load_mapping` and the scorer were not run; the T4.14 `period_type` values (QUARTER, FY, YTD) and the QUARTER choice for the T4.18 balance date were read from code (`FinancialPeriod`, cp2d), not from a CP-1 result; the metric equivalences (ebitda for reported_EBITDA, cfo_ncfo for CFO) are by name, not tested.

## Update: fix round 1 (mapping-rerun-fix-r1.md)

CP-1 is now 47 entries / 75 unmapped (file: 51 entries, 180 unmapped). Changes:
- DA x5 unmapped: CP-1 writes outflow metrics as -abs; the gold is positive.
- `cash` and `total_debt` entries moved to `period_type` PERIOD_END (end_date per quarter); the FY2024 twins are unmapped as "same locator as CP-1.fin.LTH:FY2024Q4:<metric>".
- The 8 T4.18 entries moved to PERIOD_END (end_date 2025-06-30); none is a bps cell (`fixed_rate` is decimal_percent).
- New entries: operating_profit x5 -> `ebit`; capex_signed_cashflow x5 -> `capex_and_intangible_investment` (QUARTER/FY periods).
- The earlier statements that T4.18 uses QUARTER and that operating_profit and capex are unmapped are superseded. PERIOD_END for balances is a model convention (financials.json:66), not forced by code; a model that puts balances on QUARTER periods scores missing for them.

Not verified: `load_mapping` and the scorer were not run; the PERIOD_END convention was not checked against a real T4.14 output.
