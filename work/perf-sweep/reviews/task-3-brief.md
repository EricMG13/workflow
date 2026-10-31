# Task 3 brief — Low-findings batch (one commit, comment + one test)

Worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/vigilant-mendel-070f6d`, branch
`claude/vigilant-mendel-070f6d`; HEAD must be `4af08ce` (stop if not). Python:
`"/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python"` from the worktree root. Edit only the
two files below. No behaviour change.

## 1. `src/deploy_vii/execution.py` — replace the comment above `_canonical_result`

Replace exactly these five lines:

```
# Parsed settled modules, memoised per (hash, bytes) for this process only. `Execution._load`
# still reads and hash-checks the blob on every call, so a missing or tampered blob refuses as
# before; only the parse of bytes already proven identical is skipped. Exceptions are not cached.
# ponytail: 4 entries, and one parsed CP-1 Module keeps about 233 MiB alive (about 1 GiB worst
# case); upgrade path is to cap by summed blob size instead of entry count.
```

with exactly these seven lines:

```
# Parsed settled modules, memoised per (hash, bytes) for this process only. `Execution._load`
# still reads and hash-checks the blob on every call, so a missing or tampered blob refuses as
# before; only the parse of bytes already proven identical is skipped. Exceptions are not cached.
# Every caller of the same blob gets the same Module object: never write through it.
# ponytail: 4 entries; one parsed CP-1 Module measured about 322 MiB RSS and its key keeps the
# 42 MiB blob alive, so about 1.4 GiB worst case (host._ParsedExecution keeps its own 4). Upgrade
# path is to cap by summed blob size instead of entry count.
```

## 2. `tests/test_validate_tables.py` — pin the no-facts table default

Below `test_undeclared_tables_are_allowed`, add:

```python
def test_declared_table_without_facts_passes() -> None:
    validate_tables((*TABLES, table("tc", ())), FACTS)
```

Run it on the current code (it must pass), and confirm it fails with `KeyError` if
`ids_by_table.get(table.table_id, set())` at `src/deploy_vii/contracts.py:287` is temporarily
changed to `ids_by_table[table.table_id]` — revert that temporary edit before committing and do not
commit it. If `table("tc", ())` is rejected by a contract validator before `validate_tables` runs,
report NEEDS_CONTEXT.

## Gates

`pytest tests/test_validate_tables.py tests/test_execution_result_cache.py -q` exit 0; `ruff check`
and `ruff format --check` on both files exit 0; `git diff --stat` shows only these two files. No new
`# noqa` / `type: ignore`. Stage the two files by name. Commit message:
`chore(perf): correct the result-cache memory note; pin validate_tables empty-table default`, body
one line citing the review findings in `.superpowers/sdd/product-plan/` is NOT allowed (ignored
path) — cite `work/perf-sweep/product-plan.md` instead, then
`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Report

Write `.superpowers/sdd/product-plan/task-3-report.md` (commit sha, commands with exits, the
mutant check result, `Not verified:` line). Return only status, commit sha, one-line summary,
concerns. You do not dispatch subagents or reviewers.
