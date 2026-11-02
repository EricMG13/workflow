# Mapping brief: shc-earnings-update

Stage contract: `work/model-testing/mapping/CONTEXT.md` (read it first). Base: `codex/checkpoint` @ 9c018f76
(Phases 2-8, O1, O3, O4 and O6 landed). One batch maps every module of this case.

- Case: `cases/goldens/shc-earnings-update/module_golden.json` (97 facts), pathway `earnings_update`
- Pathway plan (`deploy_vii.contracts.PATHWAY_MODULES`): CP-0, CP-1, CP-MODEL, CP-1B, CP-1D, CP-5
- Output: `cases/goldens/shc-earnings-update/mapping.json`; report: `work/model-testing/mapping/output/shc-earnings-update-report.md`

| Golden module | Facts | In plan |
|---|---|---|
| CP-0 | 16 | yes |
| CP-1B | 51 | yes |
| CP-1D | 30 | yes |
