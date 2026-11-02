# Mapping brief: tdg-credit-snapshot

Stage contract: `work/model-testing/mapping/CONTEXT.md` (read it first). Base: `codex/checkpoint` @ 9c018f76
(Phases 2-8, O1, O3, O4 and O6 landed). One batch maps every module of this case.

- Case: `cases/goldens/tdg-credit-snapshot/module_golden.json` (178 facts), pathway `credit_snapshot`
- Pathway plan (`deploy_vii.contracts.PATHWAY_MODULES`): CP-0, CP-1, CP-MODEL, CP-1A, CP-2, CP-4, CP-3, CP-5, CP-6
- Output: `cases/goldens/tdg-credit-snapshot/mapping.json`; report: `work/model-testing/mapping/output/tdg-credit-snapshot-report.md`

| Golden module | Facts | In plan |
|---|---|---|
| CP-0 | 17 | yes |
| CP-1A | 32 | yes |
| CP-2 | 116 | yes |
| CP-3 | 1 | yes |
| CP-4 | 12 | yes |
