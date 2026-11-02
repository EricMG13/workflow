# Mapping brief: bgs-relative-value (re-run)

Stage contract: `work/model-testing/mapping/CONTEXT.md`, including the "Re-run" section. Base
`6da4c9f1`: the step 4 goldens, the step 2 CP-1 financial facts and the step 3 row-key locator.

- Case: `cases/goldens/bgs-relative-value/module_golden.json`, pathway `relative_value`
- Pathway plan: CP-0, CP-1, CP-MODEL, CP-1C, CP-2, CP-2D, CP-3, CP-3C, CP-3D, CP-5
- In-plan golden facts after `load_case`: 142, of which 106 are CP-1 financial_gold
  facts (`CP-1.fin.*`). Out of plan, not mapped: none
- Output: `cases/goldens/bgs-relative-value/mapping.json` (replace the step 1 file); report
  `work/model-testing/mapping/output/bgs-relative-value-report.md` (replace)

| Module | In-plan facts |
|---|---|
| CP-0 | 1 |
| CP-1 | 125 |
| CP-2 | 15 |
| CP-3 | 1 |
