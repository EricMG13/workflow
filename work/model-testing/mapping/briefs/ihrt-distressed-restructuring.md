# Mapping brief: ihrt-distressed-restructuring (re-run)

Stage contract: `work/model-testing/mapping/CONTEXT.md`, including the "Re-run" section. Base
`6da4c9f1`: the step 4 goldens, the step 2 CP-1 financial facts and the step 3 row-key locator.

- Case: `cases/goldens/ihrt-distressed-restructuring/module_golden.json`, pathway `distressed_restructuring`
- Pathway plan: CP-0, CP-1, CP-1A, CP-1C, CP-2, CP-2A, CP-2G, CP-2H, CP-4, CP-4C, CP-5
- In-plan golden facts after `load_case`: 197, of which 90 are CP-1 financial_gold
  facts (`CP-1.fin.*`). Out of plan, not mapped: none
- Output: `cases/goldens/ihrt-distressed-restructuring/mapping.json` (replace the step 1 file); report
  `work/model-testing/mapping/output/ihrt-distressed-restructuring-report.md` (replace)

| Module | In-plan facts |
|---|---|
| CP-0 | 1 |
| CP-1 | 115 |
| CP-1A | 4 |
| CP-2 | 7 |
| CP-2H | 2 |
| CP-4 | 68 |
