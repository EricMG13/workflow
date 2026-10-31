# Task 2 brief — P3: memoise the parsed settled Module per verified blob

Read `work/perf-sweep/product-plan.md` section P3 for the evidence. This brief is the requirement.

## Setting

- Worktree (work only here): `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/vigilant-mendel-070f6d`,
  branch `claude/vigilant-mendel-070f6d`. Base = the HEAD the controller names in the dispatch;
  check `git rev-parse --short HEAD` first and stop if it differs.
- Python: `"/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python"` from the worktree root.
  Never install or sync anything.
- Authority: the user approved P3 in the controller's session. Edit only
  `src/deploy_vii/execution.py` and the test file named below. Do not edit
  `src/deploy_workflow/host.py` (its `_ParsedExecution` stays as is), `pyproject.toml`, `cases/`.
- Goal: speed only; every hash, byte, error message and API stays identical.

## Precedent to follow

`src/deploy_workflow/host.py:492-527` already does this in a subclass (`_ParsedExecution.result`,
reviewed in commit 7d0b671): re-read and hash-check the blob on every call via `self._load`,
skip only the pydantic parse of bytes already proven identical, cap 4 entries because one parsed
CP-1 result keeps ≈ 200–233 MiB alive. P3 gives the base `Execution.result` the same property with
the shortest code.

## Change

In `src/deploy_vii/execution.py`:

```python
@lru_cache(maxsize=4)
def _canonical_result(sha256: str, raw: bytes) -> Module:
    module = Module.model_validate_json(raw)
    if module.content_hash() != sha256:
        raise ValueError("Execution result blob is not the canonical module")
    return module
```

and `Execution.result` becomes `return _canonical_result(sha256, self._load(sha256))`, keeping its
docstring. Put a short comment above `_canonical_result` in the file's comment style: in-process
only; `_load` still reads and hash-checks the bytes on every call so missing/tampered blobs refuse
as before; exceptions are not cached; and a `ponytail:` line naming the ceiling (4 entries,
≈ 233 MiB per parsed CP-1 Module, so ≈ 1 GiB worst case) and the upgrade path (cap by summed
blob size). Import `lru_cache` from `functools`. Nothing else changes; `head_module` keeps
deriving the stale variant with `model_copy` (a new object; the cached one is never mutated —
`Contract` is `frozen=True`).

## Tests first

New file `tests/test_execution_result_cache.py` (real `Execution` store in `tmp_path`; read
`Execution.__init__`, `_store`, `_load` to see what a store directory needs; a small real
`Module` — e.g. a `candidate` status module with no facts, or one with a couple of facts — built
from the real contracts; no mocks of the code under test). Call `_canonical_result.cache_clear()`
at the start of each test so earlier tests cannot pre-warm it. Cases:

1. Two `store.result(sha)` calls parse once: wrap `Module.model_validate_json` with
   `monkeypatch` to count calls (return the original result) → count 1; both returns are equal to
   the module and to each other. This must FAIL on unchanged code (count 2) — record that run.
2. After a cached hit, overwrite the blob file with different bytes → next `store.result(sha)`
   raises `ValueError` matching `hash mismatch`; delete the blob → raises matching `is missing`.
   (Blobs may be written read-only; `chmod` first, as `tests/test_host_h1.py:752` does.)
3. Bytes that hash correctly but are not the canonical dump (e.g. the module's JSON with an extra
   space, stored via `store._store(...)` so the blob name is its sha256) → `store.result` raises
   `ValueError` with exactly `Execution result blob is not the canonical module`, on two
   consecutive calls (the failure is not cached).
4. A second `Execution` instance on a different `tmp_path` directory holding the same blob bytes
   returns an equal module; a different instance whose blob is missing still raises `is missing`
   even though the sha is cached.

## Verify

- New tests pass after the change.
- Existing fast tests that read results: `tests/test_host_h1.py` (Bash timeout 600000; if it runs
  over 10 minutes stop it and list it as deferred). Heavy earnings tests are deferred to the
  controller's timing phase: list them, do not run them.
- Memory is measured by the controller in the timing phase; you do not measure it.

## Gates

- `ruff check` and `ruff format --check` on changed files → exit 0.
- `MYPYPATH=src mypy --strict src/deploy_vii/execution.py`: no error not already present at your
  base (check base first if not clean).
- No new `# noqa` / `type: ignore` (baseline 13 and 5). No stub or fake standing in for real
  behaviour; no catch-all that hides a failure.
- Stage only your files by name. Commit message
  `perf(execution): parse each verified result blob once per process`, body one or two lines
  citing `work/perf-sweep/product-plan.md` P3, ending with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Report

Full report to `.superpowers/sdd/product-plan/task-2-report.md`: commit sha, files, the RED run
(command, exit, counts), GREEN run, gates with exit codes, and a final `Not verified:` line.
Return only: status, commit sha, one-line test summary, concerns. You do not dispatch subagents or
reviewers.
