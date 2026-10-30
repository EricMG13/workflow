Round 4 is built: three commits on `claude/s5-round4`, cut from ca17721. Every gate you listed exits 0 or shows the expected result.

Worktree: `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a286aba8db659bd39`
Tip: `9d6b70bee40807ea0c6e4c1242ec64934e69b26f`. I removed the `.venv` link and the tree is clean.

Changes, one commit per step:
1. **RED, `8d0d455`:** tests added to `tests/test_connect_cpl10.py` and `tests/test_connect_cp2h.py` only.
   - At ca17721, 15 tests fail for the stated cause, and every guard passes.
   - CP-L10 TL10.3: the raw token in `assessment`, `credit_transmission` and the overall row, and no raise on a typo'd or unbalanced reference.
   - CP-2H T2R.10: the raw token in `gap`, `why_it_matters`, `affected_analysis` and `action`.
   - `_carries_reference` unit test: false for the registered CP-L10 and CP-2H keys.
   - Guards that already pass:
     - A `[sic]` in TL10.3 `source_refs` shows as written.
     - A `[sic]` in T2R.10 `id` shows as written.
     - The CP-8 key is registered.
     - `_carries_reference` is false for `(CP-L10, TL10.3, source_refs)`, `(CP-2A, T2B.9, gap)`, `(CP-1C, T1C.7, gap)` and `(CP-2H, T2R.10, id)`.
   - The `_carries_reference` unit test sits in `test_connect_cpl10.py`, not `test_connect_cp8.py`, so that file is untouched.
2. **GREEN, `7598805`:** `src/deploy_vii/report_view.py` only.
   - `_RUN_TEXT_TABLES` becomes `_RUN_TEXT_FIELDS`, keyed by `(module, table, field)`, with the 7 keys from the plan.
   - `_carries_reference` tests `(module_id, fact.table_id, fact.field)`.
   - The comment and docstring now name the sources with their file:line references. There is no try/except and the signature is unchanged.
   - I applied the prototype script first, then rewrote the comment.
3. **D12, `9d6b70b`:** one `post_import_patches` record in `docs/reuse/manifest.json`.
   - `prior_project_sha256` is `c2040a50…`, `imported_sha256` is `c934d501…`, `project_commit` is `7598805`.
   - `sha256` is `9b152b587f6f32cf3407175127766391291d4f9166725df7f854cadc632983a3`.

Gates:
- **Probes:** the 7 listed probes (copies under `<S>/round4/`) each exit 0. These are `probe_cpl10_all_fields`, `probe_cp2h_gap_reference`, `probe_cpl10_analyst_reference`, `probe_c1_free_text_bracket_render`, `probe_rule`, `probe_scope_markers_round3` and `probe_e_report_data_payload`.
- **Tests:** the 15 listed files with `-m "not genuine"` gave 1884 passed, 1 skipped (the existing G2 skip) and 1 xfailed (the existing seam xfail), exit 0, about 21 s.
- **`ruff format --check`:** exit 0 on `report_view.py` and the 2 test files. A repo-wide `ruff format --check src` also flags `src/deploy_vii/methods/cp1d.md`, a file I did not touch.
- **`mypy --strict`:** no issues in `report_view.py`.
- **`ruff check`:** only SIM102 at `report_view.py:312`, as expected.
- **Suppressions:** `noqa` 13, `type: ignore` 5. Both are at the ceiling, with no increase.
- **D12 strict probe (`probe_d12_strict.py`):** only 3e5b537, 24f879a and 8aef58d fail. The new record at `7598805` shows `chain=ok item19=ok`. I did not read the probe's exit code, only its output.

Not verified: no genuine, G2 or owner-suite reruns (plan step 5: `test_owner_cpos`, `test_owner_cp8`, `test_owner_cpl10`, `test_owner_cp2h` and the G2 reruns), and no full suite. The prose-block path (`_prose_lines`) for the new keys was not exercised. The survey claims for CP-DR and CP-3D, and for the core composers (cp2_synthesis, cp6_committee, business_context), were not re-run. No `mypy` or `ruff` was run on the test files beyond `ruff check` and `ruff format`. The `ruff format` result on the `.md` file was not investigated.

Ledger: agent=mx-feature fix-rounds=0 gates-first-pass=y (the fast affected set ran and exited 0 first time; genuine suites deferred, so the task is built, not done).
