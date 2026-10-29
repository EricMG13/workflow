# Stage 3 integration I3: charts and CP-OS (stage contract)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). You run in your own isolated worktree. Before any edit, run `git checkout -b claude/s3-int 697fe8a`, the lane tip with the Stage 2 release and PF-1 merged, and confirm the tip. Write only inside your own worktree. Python: `L/.venv/bin/python`. Symlink `.venv` if needed, and remove the link before you hand back.

## Inputs
| Item | File |
|---|---|
| Branch reports | `L/work/build/stage3/w1-report.md`, `w2a-report.md`, `w2b-report.md`, `w2c-report.md`, `w2d-report.md`, `cpos-report.md` |
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` items 8-15 |
| D12 rule | `docs/reuse/manifest.json`; `L/docs/rulings/2026-10-28-stage2.md` round 5 item 19; probe `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-review-B/probe_d12_chain.py <repo> <rev> <files…>` |

## Process
1. **Merge** with `--no-ff`, in this order:
   - `claude/s3-oracles` 731059f
   - `claude/s3-wire` 423f92e
   - `claude/s3-w2a` aad1480
   - `claude/s3-w2b` 04fb724
   - `claude/s3-w2c` 278992b
   - `claude/s3-w2d` 2943d7b
   - `claude/s3-cpos` 5af00fe
2. **Conflict rules:**
   - `cases/PINS.json`: regenerate it with `python3 -I cases/pins.py`, never hand-merge it.
   - The `report_view.py` group registration blocks: keep all four, appended in group order a, b, c, d.
   - The `tests/test_chart_seam.py` registry test: replace the four group variants with one test asserting the exact registered set (every block id and pathway each group registered).
   - `tests/test_connect_cp2d.py` (groups a and c): keep both changes.
   - `tests/test_legal_render.py`: keep group c's temporary producer and note handling for now, and mark it with the comment `# Stage 3 item 13: temporary until the legal oracle move` (rulings item 13; a separate preparer moves the oracle next).
   - `docs/reuse/manifest.json`: keep every record from both sides.
3. **D12.** For each reused file that a merge changed, append one `post_import_patches` record per merge commit, following round 5 item 19. The files to check are the `docs/reuse/manifest.json` entries among `report_view.py`, `charts.py`, `bindings/*.py`, `financial_series.py`, `distressed_figures.py` and any other. Then run the probe over every reused file the merges touched, until it exits 0.
4. **Method notes.** Update the stale method text that says a Stage 3 chart is deferred or tables-only, for example `src/deploy_vii/methods/cp1c.md:23`. Search `src/deploy_vii/methods/` for each figure id (RV.3, CR.1, CR.2, CR.3, DR.2, DR.3, DR.6, S.4, S.5) and reword only sentences that are now false.
5. Commit after each step. Each commit ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates (report each exit code)
- `python3 -I cases/pins.py --check`.
- **The fast set,** with `PYTHONPATH=src:tests L/.venv/bin/python -m pytest -q -p no:cacheprovider`:
  - `tests/test_method_*.py`, `tests/test_connect_*.py`;
  - `test_cp1b_registration`, `test_owner_g1x`, `test_host_h1`, `test_schema_normalise_escapes`;
  - `test_defect_classes_selfcheck`, `test_defect_classes_shared`, `test_defect_classes_cp1`;
  - `test_engine_blank_text`, `test_rule_issue_bounds`, `test_owner_blank`, `test_owner_order`;
  - `test_stage2_classes`, `test_stage2_classes_batch`;
  - `test_legal_render`, `test_connected_render`, `test_citation_blank_quote`, `test_readiness_linear`;
  - `test_chart_seam` and every `tests/test_chart_series_*.py` and `tests/test_chart_render_*.py`;
  - `tests/test_financial_series.py`, `tests/product`.

  It must exit 0. The only xfail allowed is the DR.6 chip tripwire (rulings item 12).
- **Render suites:** `tests/test_financial_render.py`, `tests/test_earnings_render.py`, `tests/test_cp1_chart_render.py`. They take about 48 minutes; run them in the background and report the exit code. `cp1_chart_series` now requires the S.5 rows, so watch for any CP-1 fixture that lacks them.
- `ruff format --check` and `ruff check` on the files the merges changed. Report only new findings beyond the known ones: SIM102 in `report_view.py`, C408 in `test_legal_render.py:220` and `test_financial_series.py`, and the release's known list.
- `MYPYPATH=src mypy --strict` on the changed `src/` files.
- Suppressions: `git grep noqa -- src tests | wc -l` ≤ 13; `git grep "type: ignore" -- src tests | wc -l` ≤ 5.

## Outputs (report as text, at most about 1.5k tokens)
- Your worktree path and tip SHA; each conflict and how you resolved it; the D12 records; the method notes changed; gate exit codes; anything that failed and why; `Not verified:` line; ledger line.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged. Do not change an oracle or a lease. If a gate fails for a reason a merge cannot fix, stop and report it. Stop any background process before you hand back.
