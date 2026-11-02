# Mapping report: lth-covenant-refinancing

Base 9c018f76. File: `cases/goldens/lth-covenant-refinancing/mapping.json` (4 entries, 183 unmapped, 187 facts).
Preparer `mx-feature (Task 6 preparer)`; reviewer `mx-precise (Task 6 review)`.

## Per module

| Module | Files read | Commit (`git log -1 9c018f76 -- files`) | Entries | Unmapped | Facts |
|---|---|---|---|---|---|
| CP-0 | `src/deploy_vii/readiness.py` (`build_readiness`), `src/deploy_vii/cp0_workflow.py`, `src/deploy_workflow/context.py` | 0c39637aeb31cdc31892c61878e29264411e79a7 | 1 | 14 | 15 |
| CP-1A | `src/deploy_vii/business_context.py` (`_fact_registers`, `Register`), `src/deploy_workflow/owners/cp1a.py` | 0daac2cc5ba33d477b8143d3373bc75f622de5a4 | 2 | 8 | 10 |
| CP-2 | `src/deploy_vii/cp2_synthesis.py`, `src/deploy_workflow/owners/cp2.py` | cffdf9f47dd4f6bab5269df290d2bcd9b1171618 | 0 | 55 | 55 |
| CP-2D | `src/deploy_workflow/owners/cp2d.py` (`_runway_table`, `_funding_table`, `_number`, `cp2d_reader`) | 0898948fe3e709c91d1137d7e232bffb4bd410cb | 1 | 2 | 3 |
| CP-3C | `src/deploy_workflow/owners/cp3c.py` | 0898948fe3e709c91d1137d7e232bffb4bd410cb | 0 | 22 | 22 |
| CP-4 | `src/deploy_vii/cp4_legal.py`, `src/deploy_workflow/owners/cp4.py` | a2243308037a6bc6b86536ce5c801b0c73f01271 | 0 | 82 | 82 |

## Entries and their basis

- CP-0 `legal_name` -> `T1/run/issuer`, period null. `build_readiness` writes `pack.run.issuer_name`, which is the context `identity.issuer_name` ("Life Time Group Holdings, Inc."), deterministic.
- CP-1A `business_sector` -> `company_description/company/sector`; `geography_of_centers.countries` -> `company_description/company/country`. Both cells are fixed by `COMPANY_ROW` and the register columns (Issuer, Business description, Country, Sector). The text is model-written and `out.tagged` appends a category label, so exact text equality may fail even when the slot is right; the slot itself is code-fixed.
- CP-2D `horizon_months` -> `T2E.3/r03/value/2025-06-30` and `minimum_cash_m` -> `T2E.5/r04/value/2025-06-30`. Row ids come from `_number` (positional, fixed by code); `cp2d_reader` reads exactly `T2E.3.r03` and `T2E.5.r04`. Period is the balance date (q2-2025 basis). Both goldens are `missing`; with period `2025-06-30` a module that invents a value is found and scored as invented, while a module that writes a gap (which carries no period) is not found and scores `gap_ok`.

## Unmapped reasons, grouped

- CP-0 (14): no registrant-identity field exists (ticker, exchange, state, offices, file number, filer status, fiscal year end, business description, borrower entity: 9 facts); document period/date facts (5) land only in model-assessed `P3/<source_id>/period` free text.
- CP-1A (8): ownership/voting facts (4) sit in `ownership_register`/T2D.2 rows numbered by model list order; legal form, centers count, offices, listing and borrower vs parent (4) have no fixed slot.
- CP-2 (55): CP-2 is the credit-synthesis module and writes only model-judgment prose plus `cp1_references/refNN` copies numbered by order of reference; it holds no debt-stack, liquidity, swap or obligor field.
- CP-2D (1): the 10-Q maturity-ladder bucket is not a field; T2E.4 is one row per facility.
- CP-3C (22): T3D tables hold refinancing-need arithmetic; no field for soft call, repricing, MFN, margin grid, notes redemption terms or market quotes.
- CP-4 (82): all cells are model-judgment text in rows numbered `rNN` by the order of the model's own lists (documents, covenants, baskets); no per-amendment table.

## Modules over 20% unmapped

- CP-0 14/15 (93%), CP-1A 8/10 (80%), CP-2 55/55, CP-3C 22/22, CP-4 82/82 (100%), CP-2D 2/3 (67%). Cause is the same in each: the golden facts follow the filing content (debt stack, call terms, amendment terms), while the module code in this base writes model-chosen or differently shaped tables. CP-2, CP-3C and CP-4 can score only as judgment/gap checks until the golden or module shape changes; the controller should decide whether that is acceptable for this case.

Not verified: `load_mapping` was not run (no Python by instruction); the CP-2D period `2025-06-30` and the CP-0 issuer text were read from code and context, not from a run output; the CP-1A text equality given the appended category label was not tested.

Fix round 1: CP-2D horizon_months moved to unmapped (always written as a known int 1-60, cp2d.py:121; golden missing cannot be met). CP-2D now 1 entry (minimum cash) / 2 unmapped. CP-0 files now include context.py; commit 0c39637aeb31cdc31892c61878e29264411e79a7.
