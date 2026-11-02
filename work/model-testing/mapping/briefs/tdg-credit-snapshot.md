# Mapping brief: tdg-credit-snapshot (re-run)

Stage contract: `work/model-testing/mapping/CONTEXT.md`, including the "Re-run" section. Base
`6da4c9f1`: the step 4 goldens, the step 2 CP-1 financial facts and the step 3 row-key locator.

- Case: `cases/goldens/tdg-credit-snapshot/module_golden.json`, pathway `credit_snapshot`
- Pathway plan: CP-0, CP-1, CP-MODEL, CP-1A, CP-2, CP-4, CP-3, CP-5, CP-6
- In-plan golden facts after `load_case`: 235, of which 108 are CP-1 financial_gold
  facts (`CP-1.fin.*`). Out of plan, not mapped: none
- Output: `cases/goldens/tdg-credit-snapshot/mapping.json` (replace the step 1 file); report
  `work/model-testing/mapping/output/tdg-credit-snapshot-report.md` (replace)

| Module | In-plan facts |
|---|---|
| CP-0 | 5 |
| CP-1 | 169 |
| CP-1A | 32 |
| CP-2 | 16 |
| CP-3 | 1 |
| CP-4 | 12 |
