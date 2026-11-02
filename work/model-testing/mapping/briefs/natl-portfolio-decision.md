# Mapping brief: natl-portfolio-decision (re-run)

Stage contract: `work/model-testing/mapping/CONTEXT.md`, including the "Re-run" section. Base
`6da4c9f1`: the step 4 goldens, the step 2 CP-1 financial facts and the step 3 row-key locator.

- Case: `cases/goldens/natl-portfolio-decision/module_golden.json`, pathway `portfolio_decision`
- Pathway plan: CP-0, CP-1, CP-MODEL, CP-2, CP-3, CP-5, CP-6, CP-8
- In-plan golden facts after `load_case`: 148, of which 90 are CP-1 financial_gold
  facts (`CP-1.fin.*`). Out of plan, not mapped: CP-4 51
- Output: `cases/goldens/natl-portfolio-decision/mapping.json` (replace the step 1 file); report
  `work/model-testing/mapping/output/natl-portfolio-decision-report.md` (replace)

| Module | In-plan facts |
|---|---|
| CP-0 | 3 |
| CP-1 | 112 |
| CP-2 | 33 |
