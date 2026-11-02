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

## Re-run (2026-11-02, after steps 2-4; base 6da4c9f1)

Re-make every case's mapping against the new keys and locators. Use base `6da4c9f1` in place of
9c018f76 for commits; the module code is unchanged since 9c018f76.

6. **Re-tagged goldens (step 4).** Many facts now carry a new module and `fact_id` (mostly CP-1,
   T4.18 Debt Facility Register), and many moved to `not_golden`. Load the current
   `module_golden.json`; every fact in it is accounted once.
7. **CP-1 financial facts (step 2).** `load_case` adds one golden fact per `financial_gold.json`
   fact: `fact_id` `CP-1.fin.<financial fact id>`, `subject` and `field` = the metric, `period_end`
   from the gold `periods`, value in the gold `canonical_unit` (see
   `src/deploy_workflow/model_testing/cases.py` `financial_gold_facts`). Map each to the CP-1 result
   fact holding that metric and period, the same way as any entry. If CP-1 writes no such metric or
   period, use unmapped with the reason.
8. **Row-key locator (step 3).** For a fact in a register whose `row_id` is chosen at run time
   (`r01..`, `m01..`), use `locator: {"table_id", "row_id": null, "row_key": {"field": <key cell
   field id in the same row>, "aliases": [...]}, "field", "period"}`. The scorer picks the row whose
   key cell text equals the golden `subject` or an alias, both through `scoring._text`. Use it only
   when that row's key cell is meant to name the fact's subject, such as an instrument, covenant,
   agency or class name. Add aliases only for spellings the module would plausibly print: source
   names, or context names it copies. The key text is often model-written, so be honest. A
   `row_key` entry where the model will write its own wording still scores `missing_in_output` when
   the wording differs, which is a fair result, not a mapping error. Rows keyed by nothing
   meaningful stay unmapped.
9. Set `preparer` to `mx-feature (Task 6 preparer, re-run)`. Keep `reviewer` as
   `mx-precise (Task 6 review)`.
10. **Period reference (step 2b, commit c92dc5c6).** When a register's `period` is a model-declared
    id (CP-1 T4.15 and T4.18 carry `period_id`), set `"period": null` and
    `"period_ref": {"table_id": "T4.14", "id_field": "period_id", "match": {"end_date": "<YYYY-MM-DD>", "period_type": "<value CP-1 writes>"}}`.
    The scorer finds the T4.14 row whose cells equal every `match` value (through `_text`) and uses
    that row's `period_id` as the period.
    - Take `end_date` and the period kind from the golden fact. For `CP-1.fin.*` facts these come
      from the financial_gold `periods` entry for its `period_id`.
    - Write `period_type` exactly as CP-1 writes it: QUARTER, YTD, FY, LTM or PERIOD_END (src/deploy_vii/financial_contracts.py:122; read the T4.14 builder and the
      book's period model).
    - Use `start_date` too when end_date and period_type alone cannot tell two periods apart, such
      as YTD or LTM.
    - For T4.15, use `row_key` with field `metric_id`. Aliases are CP-1's code-fixed metric ids
      (`ACCOUNT_FIELDS` and friends), which differ from the gold metric names; cite the mapping.
    - For T4.18, use `row_key` with field `facility_name`. That text is model-written, so aliases are
      only the source's facility names.
    - A gold metric CP-1 has no metric id for stays unmapped, with the reason.
    - Ruling (2026-11-02): balance-sheet and other instant values (cash, debt, assets,
      liabilities, equity, T4.18 balances) sit on `PERIOD_END` periods
      (src/deploy_vii/statement_validation.py:235); flows use QUARTER, YTD, FY or LTM by the gold
      period kind. Never match on `end_date` alone: a QUARTER and a YTD period can share one end
      date, so the entry would resolve two rows and always score a mismatch.

## Outputs

- `cases/goldens/<case>/mapping.json`
- `work/model-testing/mapping/output/<case>-report.md`, containing:
  - per module: its files and commit, then entries / unmapped / facts;
  - the unmapped reasons, grouped;
  - any module with more than 20% of its known facts unmapped, and why;
  - a closing line starting `Not verified:`.

The controller runs `load_mapping` on each file, because preparers do not run the venv.
