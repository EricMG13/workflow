# Mapping brief: ihrt-distressed-restructuring

Stage contract: `work/model-testing/mapping/CONTEXT.md` (read it first). Base: `codex/checkpoint` @ 9c018f76
(Phases 2-8, O1, O3, O4 and O6 landed). One batch maps every module of this case.

- Case: `cases/goldens/ihrt-distressed-restructuring/module_golden.json` (165 facts), pathway `distressed_restructuring`
- Pathway plan (`deploy_vii.contracts.PATHWAY_MODULES`): CP-0, CP-1, CP-1A, CP-1C, CP-2, CP-2A, CP-2G, CP-2H, CP-4, CP-4C, CP-5
- Output: `cases/goldens/ihrt-distressed-restructuring/mapping.json`; report: `work/model-testing/mapping/output/ihrt-distressed-restructuring-report.md`

| Golden module | Facts | In plan |
|---|---|---|
| CP-0 | 6 | yes |
| CP-1A | 4 | yes |
| CP-2 | 66 | yes |
| CP-2H | 3 | yes |
| CP-4 | 68 | yes |
| CP-4C | 18 | yes |
