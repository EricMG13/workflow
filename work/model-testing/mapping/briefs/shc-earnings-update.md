# Mapping brief: shc-earnings-update (re-run)

Stage contract: `work/model-testing/mapping/CONTEXT.md`, including the "Re-run" section. Base
`6da4c9f1`: the step 4 goldens, the step 2 CP-1 financial facts and the step 3 row-key locator.

- Case: `cases/goldens/shc-earnings-update/module_golden.json`, pathway `earnings_update`
- Pathway plan: CP-0, CP-1, CP-MODEL, CP-1B, CP-1D, CP-5
- In-plan golden facts after `load_case`: 222, of which 156 are CP-1 financial_gold
  facts (`CP-1.fin.*`). Out of plan, not mapped: none
- Output: `cases/goldens/shc-earnings-update/mapping.json` (replace the step 1 file); report
  `work/model-testing/mapping/output/shc-earnings-update-report.md` (replace)

| Module | In-plan facts |
|---|---|
| CP-0 | 2 |
| CP-1 | 165 |
| CP-1B | 25 |
| CP-1D | 30 |
