# Task 1 brief — P2 then P1 (two commits)

Read `work/perf-sweep/product-plan.md` sections P1 and P2 for the evidence. This brief is the
requirement; exact values are here.

## Setting

- Worktree (work only here): `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/vigilant-mendel-070f6d`,
  branch `claude/vigilant-mendel-070f6d`, base commit `b0ac40c`. Check `git rev-parse --short HEAD`
  equals `b0ac40c` before you start; stop and report if not.
- Python: `"/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python"` run from the worktree root
  (pytest config already puts `src` on the path). Never `uv sync`, never install anything.
- Authority: the user approved P1–P3 in the controller's session. Edit only the files named below.
  Never edit DEPLOY VII, `pyproject.toml`, `cases/`, or any other `src/` file.
- Goal: speed only. Every hash, byte output, error message, error order and public API stays exactly
  the same.

## Commit 1 — P2: `validate_tables` groups canonical fact ids once

File: `src/deploy_vii/contracts.py`, function `validate_tables` (line 254).

1. Test first. New file `tests/test_validate_tables.py`. Build a small real input with the real
   `Fact`, `ReportTable`, `TableRow`, `TableColumn` contracts (read their definitions in
   `contracts.py`; build real instances, no mocks): two tables, each with one or two rows whose
   `fact_ids` reference facts with matching `(table_id, row_id, field)`. Parametrized cases, each
   asserting the exact message with `pytest.raises(ValueError, match=f"^{re.escape(message)}$")`,
   or no error:
   - valid input → no error; tables `()` with facts present → no error (undeclared tables allowed)
   - duplicate table id → `Duplicate report table`
   - duplicate `interface_id` → `Duplicate table interface identity`
   - duplicate fact id → `Duplicate fact identity`
   - interface table whose column label differs from its field → `Interface table requires exact field headings without an extra row header`
   - duplicate column field → `Duplicate report column`
   - duplicate row id → `Duplicate report row`
   - row with fewer fact ids than columns → `Report row does not match its columns`
   - row referencing an unknown fact id → `Report cell repeats or references an unknown fact`
   - fact whose coordinates differ from the cell → `Report cell differs from its canonical fact coordinates`
   - an extra fact with the table's `table_id` that no row references → `Declared report table omits canonical facts`
   Where a contract validator stops you from building an input, build the nearest input that
   reaches the message, and say so in the report. Run it on the unchanged code: it must pass
   (it pins today's behaviour). Record that run.
2. Change: before `for table in tables:`, build
   `ids_by_table: dict[str, set[str]] = {}` with one pass
   `for fact in facts: ids_by_table.setdefault(fact.table_id, set()).add(fact.fact_id)`.
   Replace the line
   `canonical_fact_ids = {fact.fact_id for fact in facts if fact.table_id == table.table_id}`
   and its comparison with
   `if referenced_fact_ids != ids_by_table.get(table.table_id, set()):`.
   Nothing else in the function changes. Exact reference text: `validate_tables_grouped` in
   `work/perf-sweep/probes/micro_trial.py`.
3. Run the new test again (pass), plus these existing fast callers:
   `tests/test_method_cp2a.py tests/test_method_cp8.py tests/test_method_cpdr.py tests/test_method_cp2h.py tests/test_method_cpl10.py`
   — use the Bash tool timeout 600000; if any file runs over 10 minutes, stop it and list it as
   deferred in the report rather than waiting.
4. Probe: `"/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python" -I work/perf-sweep/probes/micro_trial.py "$PWD" .superpowers/sdd/product-plan/blobs/7278c6378add2c49c6fe020f209fde4695ba1fa6d1c63e9453987f4dae4a12f5`
   → report its exit code and the two `P2 validate_tables` lines (after the change both should
   show ≈ 0.03 s).

## Commit 2 — P1: hash the CP-1 producer once per `_operands` call

File: `src/deploy_workflow/earnings_workflow.py`, `_reference` (line 1685) and `_operands` (line 1696).

1. Test first, in `tests/test_earnings_workflow.py` (append near the other unit tests; do not use
   the module-scoped owner fixtures, they take many minutes). Build a small real producer `Module`
   (`deploy_vii.contracts.Module`, real `Fact`s with `period` and `basis` set) and a real
   `EarningsDeltaReport` (`src/deploy_workflow/earnings.py:42`; read how `_grant`/`point_data` in
   the test file build one) with at least two points, one with a prior fact and one with a
   companion fact. Wrap `Module.content_hash` with `monkeypatch` so it counts calls whose `self`
   is the producer and returns the original result. Call the module's `_operands(producer, report)`
   and assert: the producer was hashed exactly once; every `FactReference.producer_sha256` in the
   result (current, prior, companions) equals `producer.content_hash()`. Run it on unchanged code
   and record that it fails on the count only.
2. Change: `_reference(producer_sha256: str, fact: Fact) -> FactReference` uses
   `producer_sha256=producer_sha256`; in `_operands`, compute `producer_sha256 = producer.content_hash()`
   once (before `operand` is defined) and pass it at both call sites (lines 1704 and 1725). Nothing
   else changes.
3. Run the new test (pass). The heavy earnings tests that reach `_operands` run later in the
   controller's timing phase: list them as deferred, do not run them.

## Gates (both commits)

- `ruff check` and `ruff format --check` on every changed file → exit 0.
- `MYPYPATH=src mypy --strict src/deploy_vii/contracts.py src/deploy_workflow/earnings_workflow.py`:
  no error that is not also present at `b0ac40c` (run it on base first if it is not clean; compare).
- No new `# noqa` or `type: ignore` (baseline: 13 and 5).
- No stub or fake value standing in for real behaviour; no catch-all that hides a failure.
- Stage only the files you changed, by name (never `git add -A`). Commit messages:
  `perf(contracts): group canonical fact ids once in validate_tables` and
  `perf(earnings): hash the CP-1 producer once per _operands call`, each body one or two lines
  citing `work/perf-sweep/product-plan.md`, ending with the line
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Report

Write the full report to `.superpowers/sdd/product-plan/task-1-report.md`: per commit the sha,
files, the test-first run (command, exit, counts), the after run, gate commands with exit codes,
probe output, and a final `Not verified:` line. Return only: status (DONE / DONE_WITH_CONCERNS /
NEEDS_CONTEXT / BLOCKED), the two commit shas, a one-line test summary, concerns.
You do not dispatch subagents or reviewers.
