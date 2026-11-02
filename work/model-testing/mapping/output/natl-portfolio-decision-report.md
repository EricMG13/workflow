# Mapping report: natl-portfolio-decision

Base 9c018f76. Preparer: mx-feature (Task 6 preparer).

## Per module (entries / unmapped / facts)

| Module | Entries | Unmapped | Facts | Commit |
|---|---|---|---|---|
| CP-0 | 1 | 12 | 13 | 0c39637aeb31cdc31892c61878e29264411e79a7 |
| CP-1 | 0 | 15 | 15 | 6c81d0bae47e515fec33f3c048f594b9e6de5e47 |
| CP-2 | 0 | 53 | 53 | cffdf9f47dd4f6bab5269df290d2bcd9b1171618 |
| CP-4 | not mapped (see below) | | 51 | none |

Files per module:
- CP-0: src/deploy_vii/readiness.py (`build_readiness`), src/deploy_vii/cp0_workflow.py, src/deploy_workflow/context.py (`issuer_name` into `Run`).
- CP-1: src/deploy_vii/cp1_workflow.py, src/deploy_vii/financial_contracts.py, src/deploy_workflow/financial_workflow.py, src/deploy_vii/financial_adapter.py.
- CP-2: src/deploy_vii/cp2_synthesis.py, src/deploy_vii/bindings/cp2.py, src/deploy_workflow/owners/cp2.py.

The one entry: CP-0 legal_name -> T1 / run / issuer / period null. `build_readiness` writes `pack.run.issuer_name`, which `context.py` copies from the context file's `identity.issuer_name` ("NCR Atleos Corporation"); the golden is "NCR ATLEOS CORPORATION", equal under the scorer's casefolded text compare.

## Unmapped reasons
- CP-0 identity attributes (ticker, exchange, state, offices, file number, filer status, fiscal year end, business description, borrower entity; 9 facts): CP-0 holds no field for them.
- CP-0 documents (3 facts): period is model free text at a P3 row keyed by the pack's source_id, which neither module code nor the golden fixes; the agreement date has no field.
- CP-1 restatement narrative (15 facts): the CP-1 result holds financial statement and debt-schedule facts, not narrative text.
- CP-2 (53 facts): `credit_synthesis` is judgments only; it stores no debt-stack, liquidity or obligor figures. It copies CP-1 facts into `cp1_references` at model-chosen indices (`ref{NN}`), so no fixed locator exists.

## Modules over 20% unmapped
- CP-0: 12/13 (92%): the module is a source-readiness review, not an identity extractor.
- CP-1: 15/15 (100%): golden holds only restatement text, which CP-1 does not write.
- CP-2: 53/53 (100%): golden facts are debt/liquidity figures that CP-2 never writes. The golden's module tagging follows the Codex split, not this code's CP-2. These will score as unmapped regardless of model output; the controller may want to re-tag them (e.g. to CP-1) or accept.

## CP-4 (out of plan)
CP-4 facts are not in `GoldenCase.facts` (in-plan only, cases.py:69). `_check_against_case` rejects any entry or unmapped item for a fact outside that set, so adding CP-4 would make `load_mapping` fail. CP-4 is therefore omitted from mapping.json and module_commits, contrary to CONTEXT step 5; the scorer reports it as `out_of_plan` anyway.

Not verified: `load_mapping` was not run (no Python by instruction); the T1/run/issuer locator was read from code, not from a real CP-0 result; casefold equality of the issuer text rests on reading `_text`, not a test; whether a model run's CP-0 pack source ids could be pinned to the golden source ids was not established.
