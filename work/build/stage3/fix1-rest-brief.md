# Stage 3 fix round 1, group F2: CP-OS cache, D12, legal test, format (stage contract)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python`.

You run in your own isolated worktree. Before any edit, run `git checkout -b claude/s3-fix1-rest 18dc1fa` (`claude/s3-i5`) and confirm the tip. Edit only the files named below. Never edit `owner_rendering.py`, `tests/test_owner_rendering.py`, a lease, an oracle value, or another worktree.

## Inputs
| Item | File |
|---|---|
| Ruling | `L/docs/rulings/2026-10-29-stage3.md` item 22 (F2); `L/docs/rulings/2026-10-28-stage2.md` :345-348 (round 5 item 19) |
| Findings | `L/work/build/stage3/review-precise.md` M2, M3, M4, L3; `L/work/build/stage3/review-arch.md` L1 |
| Probes | `<S>/stage3-review/precise/probe_cpos_cache_path_key.py`, `probe_d12_strict.py`, `probe_legal_cr1_twin_labels.py` |
| Legal targets | `cases/legal/render-expected.json` `cr1_builder_target` |

## Process (test first where a test exists; commit after each step)
1. **CP-OS cache** (`tests/test_owner_cpos.py`). Key the verifier cache on a content digest of the store and publication trees (with the receipt hash), so an in-place edit misses the cache. Show the probe hides nothing after the change.
2. **D12** (`docs/reuse/manifest.json`). Move the `src/deploy_vii/statement_extract.py` record from `local_patch_lineage` to the end of `post_import_patches`, values unchanged. Do not touch other records.
3. **Legal CR.1** (`tests/test_legal_render.py`). Assert every `cr1_builder_target` rule: twin row labels start with `label_parts[0]` and contain each later part in order; mark texts equal `mark_texts` one by one; the fact is reached through the T4.9 fact id. Show the probe's "WRONG" labels now fail.
4. **Format** (arch L1). `ruff format` on `cases/cp1c-owner/builder/build.py`, `cases/cp3c-owner/builder/build.py`, `cases/cp4c-owner/builder/build.py`, `cases/pins.py`, `src/deploy_workflow/financial_series.py`. Rebuild each of the three builders twice in two fresh copies: outputs byte-identical to each other and to the committed oracle files. Then `python3 -I cases/pins.py` and `--check`; only builder entries may move in `cases/PINS.json`.
Each commit ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates (report each exit code)
- `ruff check` (report only findings on changed lines) and `ruff format --check` on every changed file; `MYPYPATH=src mypy --strict src/deploy_workflow/financial_series.py`.
- `PYTHONPATH=src:tests L/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_legal_render.py tests/test_financial_series.py tests/test_chart_series_cr1.py`.
- `tests/test_owner_cpos.py` in full (about 40 minutes; run it in the background, report exit code and duration).
- Probes rerun: `probe_cpos_cache_path_key.py` (must no longer pass the hidden edit), `probe_d12_strict.py <your worktree> 697fe8a HEAD` (Stage 3 records must pass; list any remaining failure and whether it predates Stage 3), `probe_legal_cr1_twin_labels.py` (must reject the forged labels).
- `python3 -I cases/pins.py --check`; suppressions `noqa` ≤ 13, `type: ignore` ≤ 5.

## Outputs (return as text, at most about 1k tokens)
Worktree path and tip SHA; what changed per finding; gate and probe exit codes; `Not verified:` line; ledger line `agent=… fix-rounds=1 gates-first-pass=…`.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged. Never use bare `git stash`. Stop any background process before you hand back.
