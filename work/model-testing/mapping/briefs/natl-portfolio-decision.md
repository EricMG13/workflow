# Mapping brief: natl-portfolio-decision

Stage contract: `work/model-testing/mapping/CONTEXT.md` (read it first). Base: `codex/checkpoint` @ 9c018f76
(Phases 2-8, O1, O3, O4 and O6 landed). One batch maps every module of this case.

- Case: `cases/goldens/natl-portfolio-decision/module_golden.json` (132 facts), pathway `portfolio_decision`
- Pathway plan (`deploy_vii.contracts.PATHWAY_MODULES`): CP-0, CP-1, CP-MODEL, CP-2, CP-3, CP-5, CP-6, CP-8
- Output: `cases/goldens/natl-portfolio-decision/mapping.json`; report: `work/model-testing/mapping/output/natl-portfolio-decision-report.md`

| Golden module | Facts | In plan |
|---|---|---|
| CP-0 | 13 | yes |
| CP-1 | 15 | yes |
| CP-2 | 53 | yes |
| CP-4 | 51 | no (out of plan) |
