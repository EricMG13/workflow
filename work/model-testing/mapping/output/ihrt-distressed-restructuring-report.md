# Mapping report: ihrt-distressed-restructuring

Base 9c018f76. Preparer: mx-feature (Task 6 preparer). Output: `cases/goldens/ihrt-distressed-restructuring/mapping.json`.

## Per module

| Module | Files read | Commit (`git log -1 9c018f76 -- files`) | Entries | Unmapped | Facts |
|---|---|---|---|---|---|
| CP-0 | `src/deploy_vii/readiness.py` (`build_readiness`), `src/deploy_vii/cp0_workflow.py`, `src/deploy_workflow/context.py` | 0c39637aeb31cdc31892c61878e29264411e79a7 | 1 | 5 | 6 |
| CP-1A | `src/deploy_vii/business_context.py`, `src/deploy_workflow/owners/cp1a.py` | 0daac2cc5ba33d477b8143d3373bc75f622de5a4 | 1 | 3 | 4 |
| CP-2 | `src/deploy_vii/cp2_synthesis.py`, `src/deploy_workflow/owners/cp2.py` | cffdf9f47dd4f6bab5269df290d2bcd9b1171618 | 0 | 66 | 66 |
| CP-2H | `src/deploy_workflow/owners/cp2h.py` | 5149ddadf64d5b9be4f327750db39a928ff66a23 | 0 | 3 | 3 |
| CP-4 | `src/deploy_vii/cp4_legal.py`, `src/deploy_workflow/owners/cp4.py` | a2243308037a6bc6b86536ce5c801b0c73f01271 | 0 | 68 | 68 |
| CP-4C | `src/deploy_workflow/owners/cp4c.py` | e995c5ddc57ac3e7840855a6ccaaa175a189ccd8 | 0 | 18 | 18 |

Only entry: `CP-0.identity.Registrant.legal_name` -> `T1 / run / issuer / null`. CP-0 writes `pack.run.issuer_name`
there, and `context.py:767` sets that from `identity.issuer_name`, which is "iHeartMedia, Inc." in this case's `context.json`.

## Unmapped reasons (grouped)

- CP-0 (5): identity facts for ticker, borrower, parent guarantor, Capital I relationship and fiscal year end. `build_readiness`
  writes only T1 run objective/issuer/reporting_period/identity_gate, per-source P3/P5/T2/T3/T6 and per-consumer T4/T8 facts.
- CP-1A (4): rows are numbered `r01..` in the order the model submits them and the cell text is model prose; no fixed row id.
- CP-2 (66): the module holds model judgments (T2.1, T2.7, T2.10-T2.12, cp2.* front tables) and `ref01..` references to CP-1/CP-1A
  figures. Debt stack, liquidity, new-instrument terms have no fixed table, row id or field.
- CP-2H (3): T2R.2 rating rows come from context ratings (empty in this case), numbered `r01..`; a missing agency rating has no row,
  and the coupon step-down term has no field.
- CP-4 (68): covenant registers (T4.x, T4C.x, T4D.x, T4F.x) with `r01..` rows in model-submitted order. Exchange offer amounts,
  participation, dates, TSA support and credit-agreement terms (Section 7.11, Applicable Rate levels) have no fixed table, row id or
  field. Ratios and totals such as `TotalTendered` are not computed by CP-4.
- CP-4C (18): T4E.x waterfall tables use model-chosen class rows (`r01..`) with period at the balance date, not 2024-12-20.
  No table holds post-exchange lien rank, guarantee status, intercreditor text or remaining principal.

## Modules over 20% unmapped

All except CP-0 are 100% unmapped (CP-0: 5 of 6, 83%). The cause is shared: these golden facts describe the filings, and the
modules' registers either hold model-written judgments or number their rows by submission order, so no locator is fixed by code.
Mapping them would require guessing a row id. The scorer will report them as unmapped, not as module errors.

Not verified: `load_mapping` was not run (no Python by contract); the CP-0 issuer-name equivalence to the golden legal name was read from code and `context.json`, not exercised by a run; no real result layout of CP-1A, CP-2, CP-4, CP-4C or CP-2H for this case was inspected beyond module code.
