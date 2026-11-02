# Mapping brief: lth-covenant-refinancing (re-run)

Stage contract: `work/model-testing/mapping/CONTEXT.md`, including the "Re-run" section. Base
`6da4c9f1`: the step 4 goldens, the step 2 CP-1 financial facts and the step 3 row-key locator.

- Case: `cases/goldens/lth-covenant-refinancing/module_golden.json`, pathway `covenant_refinancing`
- Pathway plan: CP-0, CP-1, CP-MODEL, CP-1A, CP-2, CP-2D, CP-4, CP-3C, CP-5
- In-plan golden facts after `load_case`: 231, of which 111 are CP-1 financial_gold
  facts (`CP-1.fin.*`). Out of plan, not mapped: none
- Output: `cases/goldens/lth-covenant-refinancing/mapping.json` (replace the step 1 file); report
  `work/model-testing/mapping/output/lth-covenant-refinancing-report.md` (replace)

| Module | In-plan facts |
|---|---|
| CP-0 | 4 |
| CP-1 | 122 |
| CP-1A | 10 |
| CP-2 | 11 |
| CP-2D | 2 |
| CP-4 | 82 |
