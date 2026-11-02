# tdg-credit-snapshot mapping report

Base 9c018f76. Output: `cases/goldens/tdg-credit-snapshot/mapping.json`. Preparer mx-feature (Task 6 preparer).

## Per module

| Module | Files | Commit | Entries | Unmapped | Facts |
|---|---|---|---|---|---|
| CP-0 | `src/deploy_vii/readiness.py` (`build_readiness` sets every id; `financial_workflow._verify_cp0` only replays it) | eeab0b8fecda6ee1a74b16c66711503e12928583 | 1 | 16 | 17 |
| CP-1A | `src/deploy_vii/business_context.py`, `src/deploy_workflow/owners/cp1a.py` | 0daac2cc5ba33d477b8143d3373bc75f622de5a4 | 0 | 32 | 32 |
| CP-2 | `src/deploy_vii/cp2_synthesis.py`, `src/deploy_workflow/owners/cp2.py` | cffdf9f47dd4f6bab5269df290d2bcd9b1171618 | 0 | 116 | 116 |
| CP-3 | `src/deploy_vii/cp3_relative_value.py`, `src/deploy_workflow/owners/cp3.py` | 68ebc369347121ce505488a8808661e643751d52 | 0 | 1 | 1 |
| CP-4 | `src/deploy_vii/cp4_legal.py`, `src/deploy_workflow/owners/cp4.py` | a2243308037a6bc6b86536ce5c801b0c73f01271 | 0 | 12 | 12 |

## Entries (fix round 1: only CP-0 remains)
- CP-0 legal_name -> `T1 / run / issuer / null` (`field("T1","run","issuer", pack.run.issuer_name)`; issuer_name comes from context identity, equal to the golden).

## Unmapped reasons (grouped)
- CP-0, 12 facts (ticker, exchange, state, offices, FYE, filer status, file number, subsidiary/holding status, three issuer/borrower entities): CP-0 has no field for these attributes; it writes only T1 run, P3/P5/T2/T3/T6 per source, T4/T8 per consumer, T5 gaps, T7 run.
- CP-0, 4 facts (period_covered per filing): row id is the pack `source_id`, set by run staging. No module or repo code fixes the ids Q2FY24/Q3FY24/K24/Q1FY25, and the cell is reviewer text. If the harness stages sources under the golden `sources[].source_id`, these map to `P3 / <source_id> / period / null`; the controller can confirm and add them.
- CP-1A, 30 facts (segments, profile shares, acquisitions, financing events): registers number rows `r01..` in model submission order; the row id is model-chosen.
- CP-1A, 1 fact (sector_description): the golden is the Item 1 business description; `company_description/company/sector` is a separate cell, and the `business_description` cell is model-written prose compared by exact text, so it is not tied to the golden (fix round 1).
- CP-1A, 1 fact (sponsor_or_controlling_holder, missing): the absence may appear in any numbered ownership_register / T2D.2 row or in an empty-table `none` row; no fixed locator.
- CP-2, 116 facts: CP-2 writes only model prose (T2.1, T2.7, T2.10, T2.11, T2.12, cp2.* front rows) and `cp1_references/refNN` copies of CP-1 figures numbered by first prose reference. No debt-stack, revolver, liquidity or maturity row exists at a code-fixed id.
- CP-4, 12 facts: covenant rows (T4.3, T4.9, T4C.x) are numbered `r01..` by model submission order; row id and cell are model-chosen.

## Modules over 20% unmapped
- CP-0 (16/17): see reasons above; CP-0 is a source-readiness module, not an identity/facts register.
- CP-1A (32/32): row ids are model-numbered.
- CP-2 (116/116): synthesis prose only; the figures live in CP-1, which is not a golden module here.
- CP-4 (12/12): model-numbered covenant rows.
- CP-3 (1/1): T3.3 `none` exists only for an empty register; model rows are `m01..`, so no fixed locator (fix round 1).

Not verified: `load_mapping` was not run (no Python); row-id and field strings were read from code, not from a run result; whether the harness stages sources under the golden `source_id`s.
