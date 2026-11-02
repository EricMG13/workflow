# Mapping brief: bgs-relative-value

Stage contract: `work/model-testing/mapping/CONTEXT.md` (read it first). Base: `codex/checkpoint` @ 9c018f76
(Phases 2-8, O1, O3, O4 and O6 landed). One batch maps every module of this case.

- Case: `cases/goldens/bgs-relative-value/module_golden.json` (108 facts), pathway `relative_value`
- Pathway plan (`deploy_vii.contracts.PATHWAY_MODULES`): CP-0, CP-1, CP-MODEL, CP-1C, CP-2, CP-2D, CP-3, CP-3C, CP-3D, CP-5
- Output: `cases/goldens/bgs-relative-value/mapping.json`; report: `work/model-testing/mapping/output/bgs-relative-value-report.md`

| Golden module | Facts | In plan |
|---|---|---|
| CP-0 | 2 | yes |
| CP-2 | 55 | yes |
| CP-3 | 26 | yes |
| CP-3C | 13 | yes |
| CP-3D | 12 | yes |
