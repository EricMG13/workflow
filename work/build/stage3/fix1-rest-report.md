F2 done. Worktree: /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a1265e43ff00ad378, branch claude/s3-fix1-rest, tip 19dc540 (base 18dc1fa confirmed). Four commits: 9f49c48, 0df768b, a PROBE-fixed legal test commit, 19dc540. An untracked `.venv` symlink to the lane venv sits in the worktree and is NOT committed.

Changes per finding
- M2 (CP-OS cache), tests/test_owner_cpos.py: the cache key is now a content digest of the store tree and the publication tree, plus the receipt hash and the publication path (new `tree_digest`). `probe_cpos_cache_path_key.py` now fails with "ValueError: store changed", so the in-place edit is no longer hidden.
- M3 (D12), docs/reuse/manifest.json: the `statement_extract.py` record moved from `local_patch_lineage` to the end of `post_import_patches`, values unchanged. JSON still parses. `probe_d12_strict.py <worktree> 697fe8a HEAD` exits 1. The Stage 3 records pass: statement_extract, bindings/cp1 and charts are all ok. Three failures remain in `report_view.py` records at @3e5b537 (item19 BAD), @24f879a (item19 BAD) and @8aef58d (chain GAP). Those commits are not in 697fe8a..HEAD, so they predate Stage 3. I left them for the owner.
- M4 (legal CR.1), tests/test_legal_render.py: the test now asserts:
  - each mark's `ref_id` is in the report-index entry for its T4.9 fact id;
  - mark texts equal `mark_texts` one by one (gap marks match the `gap_ref_pattern`);
  - each twin row label starts with `label_parts[0]` and contains each later part in order (`#` matches `\d+`).
  `probe_legal_cr1_twin_labels.py` now refuses the "WRONG" labels in both cases (exit 1, meaning the defect is not reproduced).
- L3 / arch L1 (format): `ruff format` applied to the three builders, `cases/pins.py` and `financial_series.py`. Each builder was rebuilt in two fresh copies (c and d): the outputs are byte-identical to each other and to the committed manifest, submissions and expected files. `pins.py` then `--check` exits 0. Only the three builder entries moved in `cases/PINS.json`.

Gate exit codes
- `ruff format --check` on all 7 changed files: 0.
- `ruff check`: pre-existing findings only (F841, B023, FURB167, C408, RUF100 and similar, 26 in the builders; one C408 in `tests/test_legal_render.py`). The format pass changed no code, so none sit on lines I changed logically.
- `MYPYPATH=src mypy --strict financial_series.py`: 0.
- pytest on `test_legal_render.py`, `test_financial_series.py` and `test_chart_series_cr1.py`: 130 passed, exit 0.
- `tests/test_owner_cpos.py` in full: 44 passed in 2316 s (38m36s), exit 0. No background process is left running.
- `python3 -I cases/pins.py --check`: 0.
- Suppressions: `# noqa` 13 in src and tests (cases builders excluded); `# type: ignore` 5.

Not verified: the `cases/PINS.json` re-pin was written while the CP-OS run was in progress; the run passed, but it may have read old or new pins. `test_owner_cpos.py` ran from commit 9f49c48's code plus the later tree edits, not a clean 19dc540 checkout. The two new builder pins were not run through the other owner suites (cp1c, cp3c, cp4c tests). `ruff check` findings in the builders were not triaged. No test covers the D12 manifest move beyond the probe.

Ledger: agent=mx-feature fix-rounds=1 gates-first-pass=y
