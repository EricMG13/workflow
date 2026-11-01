# T6: speed-branch merge, D12 records, F1, F2 (stage contract; mx-feature, test first)

Include `work/build/stage8/common.md`. There is one exception to its rule against editing `src/deploy_vii/**`: you may add records to `docs/reuse/manifest.json`. You still edit no `src/deploy_vii` file. Rulings: item 86 in `L/docs/rulings/2026-10-29-stage3.md`.

## Setup
In your isolated worktree:
- `git checkout -b claude/s8-speed aea66d84`, the lane tip.
- `git merge --no-ff --no-commit codex/checkpoint` (3aaeb355; it has no conflicts).
- `git checkout aea66d84 -- AGENTS.md`, because the lane's AGENTS.md is kept (item 85).
- Commit as `merge codex/checkpoint 3aaeb355 (speed branch P1-P3); keep the lane's AGENTS.md`.

## Commits after the merge, in this order
1. **`docs: D12 records for the speed branch`.** Edit only `docs/reuse/manifest.json`. Append one `post_import_patches` record per speed commit that changed a reused file:
   - `src/deploy_vii/contracts.py` at 2ded26ca3ff8a81cc952f4dae4f1386d5c999880;
   - `src/deploy_vii/execution.py` at 4af08ceb9e41804caa4de81af4fd8637d1f53be7;
   - `src/deploy_vii/execution.py` at 66cce2a3293216fd324e0e5f578287acc60bc37b, after 4af08ceb.

   Fill each record as follows:
   - `prior_project_sha256` is the file's sha256 at the commit's first parent (`git show <c>^1:<path> | shasum -a 256`), and `sha256` is the file's sha256 at the commit.
   - `imported_sha256` is that destination's `files[].sha256`.
   - `project_commit` is the full sha.
   - `reason` is one line taken from the commit subject.
   - `review` is `docs/rulings/2026-10-29-stage3.md item 86`.

   Copy the field order of the last existing record. The chain must link: the first new record's prior must equal the last existing record's `sha256` for that file. If it does not, stop and report.
2. **`test: RED F1`.** Write a test, in a new `tests/test_host_parse_cache.py`, that fails today because the host keeps a second parsed copy of a settled module:
   - build a store with one settled result (reuse helpers from `tests/test_source_tools.py` or `tests/test_execution_result_cache.py`);
   - assert `host._ParsedExecution(d).result(h) is Execution(d).result(h)`, which means one parse per blob per process;
   - assert that a tampered blob still refuses through `_ParsedExecution` (it must raise, as `Execution` does). Name the exception and message you expect.
3. **`fix: F1`.** In `src/deploy_workflow/host.py`:
   - delete `_ParsedExecution.result` and `_PARSED_MODULES`, so `Execution.result` (`deploy_vii.execution._canonical_result`, an lru_cache of 4) is the only result parse cache;
   - keep the `pack` cache and `_PARSED_PACKS`;
   - rewrite the cache comment above `_PARSED_LIMIT` to describe only the pack cache;
   - in `tests/test_source_tools.py` `fresh_cp1_cache`, drop the `_PARSED_MODULES` line.
   `_RecordingExecution` must still record every digest read: `Execution.result` calls `self._load`.
4. **`fix: F2`.** The pin `src/deploy_vii/contracts.py` in `cases/cpos-owner/builder/build.py` (PINS) and `cases/cpos-owner/manifest.json` changes from `3b33bfc2…` to the file's current sha256 (compute it with `shasum -a 256`). Edit those two lines only. The controller will rerun the builder, check that every generated file other than `manifest.json` is byte-identical, and regenerate `cases/PINS.json`.

## Report
Follow common.md, plus:
- the merge SHA;
- each D12 record's prior → sha;
- the old and new contracts.py pin.
