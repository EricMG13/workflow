# Mapping report: bgs-relative-value

Preparer: mx-feature (Task 6 preparer). Base 9c018f76. Commits are `git log -1 --format=%H 9c018f76 -- <the module files listed>` (fix round 1: the first draft wrongly used the merge for all).

## Per module

| Module | Files read | Commit | Entries | Unmapped | Facts |
|---|---|---|---|---|---|
| CP-0 | src/deploy_vii/readiness.py (`build_readiness`), src/deploy_workflow/owner_workflow.py | 9abad5b6d071e6d297366d0d1777689bfa2ec82e | 1 | 1 | 2 |
| CP-2 | src/deploy_vii/cp2_synthesis.py, src/deploy_workflow/owners/cp2.py | cffdf9f47dd4f6bab5269df290d2bcd9b1171618 | 0 | 55 | 55 |
| CP-3 | src/deploy_vii/cp3_relative_value.py, src/deploy_workflow/owners/cp3.py | 68ebc369347121ce505488a8808661e643751d52 | 0 | 26 | 26 |
| CP-3C | src/deploy_workflow/owners/cp3c.py | 0898948fe3e709c91d1137d7e232bffb4bd410cb | 0 | 13 | 13 |
| CP-3D | src/deploy_workflow/owners/cp3d.py | 5e859cd137c662462c898c1b8311b2766e0d9fd2 | 0 | 12 | 12 |

Entry: `CP-0.identity.Registrant.legal_name` -> T1 / run / issuer / period null. `readiness.build_readiness` writes the fact from `pack.run.issuer_name`, which is the context `identity.issuer_name` ("B&G Foods, Inc."). The golden is "B&G FOODS, INC."; the scorer compares casefolded and normalised, so the case difference is the scorer's matter, not a locator matter.

## Unmapped reasons (grouped)

- CP-0 ticker_exchange (1): the readiness result has no exchange or ticker field.
- CP-2 (55): the module is credit synthesis. It writes judged prose in T2.1, T2.7, T2.10, T2.11, T2.12 at model-chosen row ids, and CP-1 references at refNN rows numbered by citation order. It writes no debt-stack, revolver, liquidity, maturity-schedule or covenant fact at a fixed locator. The golden "CP-2" facts are filing data that CP-1 (financials) or the prose would carry.
- CP-3 (26): relative-value judgment; T3.1/T3.3/T3.4/T3.9/T3.10 rows are model-submitted text with submission-order row ids. No fair-value, hierarchy or repurchase fact is written at a fixed locator. The missing `observed_quotes` fact has no fixed output row (an empty register writes a placeholder row id `none`, shared by whatever register is empty, not an observed-quotes fact).
- CP-3C (13): the module computes maturity burden, refinancing need, step-up cost, creditor position and LME capacity (T3D.1-T3D.9). It writes no call, redemption, clawback, make-whole, change-of-control or prepayment-trigger terms.
- CP-3D (12): market-implied risk from quotes (T3E.1-T3E.9). It writes no guarantor, collateral or priority text.

## Over 20% unmapped

All of CP-2 (100%), CP-3 (100%), CP-3C (100%), CP-3D (100%), CP-0 (50%). The cause is structural: the golden facts are filing-derived data points, while these modules emit judgment tables or computed risk metrics, so no fixed locator exists. This is a golden-to-module mismatch the controller should look at (scoring will report these as unmapped).

Not verified: `load_mapping` was not run (no venv by rule); the CP-0 issuer_name path from context to `pack.run.issuer_name` was read in context.py (lines ~521, 767, 810) but not executed; no live module result was inspected for the actual T1/run/issuer period string (code sets none, so null).
