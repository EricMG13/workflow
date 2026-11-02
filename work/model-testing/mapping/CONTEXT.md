# Stage: golden mapping (Plan B Task 6)

One job: write `cases/goldens/<case>/mapping.json`, which ties each golden fact to the one fact a
module result holds for it, so the scorer (Task 7) can compare them. This is oracle work, not
code. The preparer, the reviewer and the scorer builder are different agents, and their ids go
in the ledger.

## Inputs

| Layer | File | Section | Why |
|---|---|---|---|
| L2 | `work/model-testing/mapping/briefs/<case>.md` | all | case, pathway plan, modules, output paths |
| L3 | `cases/goldens/<case>/module_golden.json` | `facts` | the golden facts: `fact_id`, `module`, `subject`, `field`, `period_end`, `value_type` |
| L3 | `src/deploy_workflow/model_testing/mapping.py` | `Locator`, `MappingEntry`, `Unmapped`, `Mapping`, `load_mapping` | the contract the file must load under |
| L3 | `src/deploy_workflow/model_testing/scoring.py` | `_locate` (~:162), `_equal` (~:174) | a locator matches a result fact only on equal `(table_id, row_id, field, period)` |
| L3 | `src/deploy_vii/contracts.py` | `Fact` (~:165), `PATHWAY_MODULES` | result fact fields and their defaults (`summary`/`summary`/`value`) |
| L3 | module code: `src/deploy_workflow/owners/<module>.py`, `financial_workflow.py`, `earnings_workflow.py`, `owner_workflow.py` (`OwnerSpec` table) | where each module builds its `Fact`s | which `table_id`/`row_id`/`field`/`period` each module writes |
| L3 | `cases/<module>-owner/expected.json`, `cases/*-context-owner/`, `tests/*_runs.py` | real result layouts | written ids, period strings, row ids |

## Process

1. For each golden module in the brief, find the files that build its result facts: its owner core
   plus any binding or workflow file that sets `table_id`, `row_id`, `field` or `period`. Record
   `git log -1 --format=%H 9c018f76 -- <those files>` as `module_commits[<module>]`, and list the
   files in the report.
2. For each golden fact of that module, add exactly one of the following:
   - An **entry**, when the module's code fixes all four ids of the locator. Fixed means set by the
     schema or code, or derived deterministically from the source or context data. `period` uses
     the exact string the module writes (`null` when it writes none).
   - An **unmapped** item with a specific reason. Use this when no module output can hold the
     fact, when the row id or field is chosen by the model at run time, or when the module writes
     the value only inside prose. Never guess a locator.
3. Two entries in one module never share a locator. Add `subject_aliases` only for a text fact
   the module would print under a different name ("Term Loan B" vs "Term B Loans").
   `depends_on` lists the golden fact_ids of upstream operands that this fact's value is computed
   from.
4. Set `schema_version` to `golden-mapping/1`. Set `preparer` to `mx-feature (Task 6 preparer)` and
   `reviewer` to `mx-precise (Task 6 review)`. Every `module_commits` key must be a module that has
   golden facts in this case.
5. Facts of a module outside the pathway plan are not in `GoldenCase.facts` (`out_of_plan`, Task
   4), so they get no entry, no unmapped item and no `module_commits` key; `load_mapping` refuses
   them (ruling 2026-11-02, NATL CP-4).

## Outputs

- `cases/goldens/<case>/mapping.json`
- `work/model-testing/mapping/output/<case>-report.md`, containing:
  - per module: its files and commit, then entries / unmapped / facts;
  - the unmapped reasons, grouped;
  - any module with more than 20% of its known facts unmapped, and why;
  - a closing line starting `Not verified:`.

The controller runs `load_mapping` on each file, because preparers do not run the venv.
