# Stage 3 chart wiring W1: the chart seam (stage contract)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). Worktree: the agent's own isolated worktree (the harness creates it). Before any edit, run `git checkout -b claude/s3-wire 731059f` there (the frozen oracle tip of `claude/s3-oracles`); confirm `git log --oneline -1` shows 731059f. Write only inside that worktree. Python: `L/.venv/bin/python`.

You build the shared chart seam that every Stage 3 figure needs. Per-figure producers and block wiring come next, in W2, from your tip. You prepared and reviewed none of the oracles. You never edit `cases/`.

## Inputs
| Item | File |
|---|---|
| Frozen oracles (every expected value) | `cases/charts/{s5,rv3,cr1,s4fp04,cr2,cr3,dr2,dr345,dr6}-expected.json`: their `scope_limits` and `builder_targets` name each seam change |
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` items 3, 5, 6, 8 and 9. The chart-seam scope is item 8. |
| Pattern | `docs/CP1-CHART-SLICE.md` (producer records :66) |
| Seam code | `src/deploy_vii/report_view.py` (`ChartKind` :56, `ChartSpec` and its text check :252-325, `_chart_fact_cell` :1610-1620, `_STRIP_FIGURES`, `_cp1_strip` :1650-1700, `_na_strip`, `_block` :1800-1830), `src/deploy_vii/charts.py`, `src/deploy_vii/display.py` (`format_value`) |
| Attempt 1 read-only design (use it; verify each claim) | `L/work/build/stage3/w1-attempt1-report.md` |
| Design geometry (form only) | `/Users/ericguei/Documents/DEPLOY VII/design/reference/lib/charts.js` (`rangeStrip`, `bullet`, `waterfall`, `naFrame`); read only |

## Scope (the seam changes the oracles name, and nothing else)
1. `ChartKind` gains `range` (RV.3) and `bullet` (CR.1). Add their SVG geometry and table twins in `charts.py`, following the existing kinds.
2. A `ChartMark` carries the fact's declared decimals. The `ChartSpec` text check passes them to `format_value`. Without a declared value, behaviour is unchanged.
3. `_chart_fact_cell` accepts the percent unit class, plus a strict-parse mark path for settled text amounts (CR.1 threshold, rulings item 5.3). A rejected text becomes a gap, never 0.
4. Hatching follows the fact basis (analyst judgment, DR.2), not only `S` refs.
5. `_na_strip` takes a reason, so the S.4 frame can name CP-1 as not settled. A view with no CP-1 entry takes the degraded path and never raises `KeyError`.
6. A per-producer figure dispatch in `_block`: a registry keyed by block id that W2 fills one producer at a time. It must also cover `period_grid` blocks (S.5). Include the S.5 entry point beside `_cp1_strip`. Its dispatch holds no figure of its own until W2 registers producers, and is gated by pathway (S.5 is not drawn on `earnings_update`).
7. Test first: `tests/test_chart_seam.py` covers each seam rule, using marks, units and texts taken from the oracles. A CP-1 chart regression check: `tests/test_cp1_chart_render.py` and `tests/test_financial_series.py` must stay green unchanged.

**Answers to attempt 1's questions (Modules):** (1) a settled text that fails the strict parse is a chart gap: allocate its `G#` where `build_index` allocates gap references (a named seam change); if `build_index` lives outside the three files below, stop and report. (2) `maturity-wall` stays `dense` in W1; W2 flips it with the binding; a unit test may monkeypatch a spec to `chart` to prove the degraded path. (3) Check the suppression counts before adding any suppression; add none if the baseline has no room.

If a needed change falls outside `report_view.py`, `charts.py` and `display.py` (for example `render.py`, `app.js` or `bindings/`), stop and report it.

## Gates (report each exit code)
Run with `PYTHONPATH=src:tests L/.venv/bin/python -m pytest -q -p no:cacheprovider`:
- `tests/test_chart_seam.py`;
- `tests/test_financial_series.py`;
- `tests/test_legal_render.py`, `tests/test_connected_render.py`;
- `tests/test_cp1_chart_render.py` (slow; run it in the background).

Also:
- `python3 -I cases/pins.py --check`.
- `ruff check` and `ruff format --check` on changed files; `MYPYPATH=src mypy --strict` on changed `src/` files.
- Suppressions: `git grep noqa -- src tests | wc -l` ≤ 13; `git grep "type: ignore" -- src tests | wc -l` ≤ 5.
- D12: for each edited file listed in `docs/reuse/manifest.json`, append a `post_import_patches` record (rulings `L/docs/rulings/2026-10-28-stage2.md` round 5 item 19).

Commit after the RED tests and after each seam rule. Each commit ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Outputs (report as text, at most about 1.5k tokens)
- Tip SHA; the seam API W2 will call (names and signatures); tests and counts; D12 records; questions; `Not verified:` line; ledger line.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged. Stop any background process before you hand back.
