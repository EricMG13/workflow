Stage 5.2 navfix is done: `.module-list` now carries `flex-shrink:0`, with a RED test, and the manifest records the patch. The probe fails only on the three predating records, as the brief expected.

**Worktree:** `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a3ed59a423cbfd432`, branch `claude/s5-navfix`, based on `64cfca9`.
**Tip:** `3c90773`. I removed the `.venv` link and the tree is clean.

**Commits**
- `150cc66`: RED test, new file `tests/test_shell_css.py`.
  - It parses the `.module-list{...}` rule from the inlined `assets/app.css` and asserts `flex-shrink` is `0`.
  - It failed at `64cfca9` because the declaration was absent.
- `71782af`: GREEN, one line in `src/deploy_vii/assets/app.css:72`, now `...min-height:0;flex-shrink:0}`.
- `3c90773`: new `post_import_patches` entry for `src/deploy_vii/assets/app.css` in `docs/reuse/manifest.json`.
  - It is the last entry of `post_import_patches`, with `imported_sha256` and `prior_project_sha256` both `ea3a8198…` (no earlier patch).
  - Its `sha256` is `14aa4a82…`, `project_commit` is `71782af`, and `review` is `docs/rulings/2026-10-29-stage3.md`. The reason cites item 61.
- My first manifest edit landed in `local_patch_lineage`, because that is the last array in the file. The probe flagged it as MISPLACED. I reset it and moved the entry into `post_import_patches`.

**Gates**
- **New test:** 1 passed, exit 0, about 0.1 s.
- **Render set plus the new test** (`test_connected_render`, `test_chart_seam`, `test_earnings_render`, `test_legal_render`, `test_cp1_chart_render`, `test_owner_rendering`, `-k "not genuine"`): 446 passed, 59 deselected, 8 s. Exit 0 is read from the pass summary; my `$?` captured `tail`'s exit.
- **`python3 -I cases/pins.py --check`:** exit 0, "matches 86 paths". No pins moved.
- **`ruff check` and `ruff format --check`** on the test file: both exit 0.
- **Suppressions:** `noqa` is 13 and `type: ignore` is 5 (1+2+2), both within the limits.
- **`probe_d12_strict.py <worktree> 697fe8a HEAD`:** exit 1, and the only failures are `3e5b537`, `8aef58d` and `24f879a`.
  - The app.css chain shows `pip @71782af prior=ea3a8198 -> 14aa4a82 chain=ok item19=ok`.

**Not verified:** the native browser check (the controller's), that the pointer click now reaches a module row with a long outline, and the narrow-screen drawer `.navigator.open` layout. The test checks the declaration in the CSS text, not the computed layout. The full test suite and `-k genuine` tests were not run.

**Ledger:** agent=mx-feature fix-rounds=0 gates-first-pass=y (one manifest placement slip corrected before any gate reported it)
