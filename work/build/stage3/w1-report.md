# W1 chart seam report (mx-feature a37a7472, claude/s3-wire 423f92e)

W1 chart seam is built and committed. Every gate you listed exits 0 except one: ruff check still reports SIM102 on pre-existing code.

Worktree: /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a37a74727a9ca2184
Branch: claude/s3-wire, based on 731059f. Tip SHA: 423f92e1 (full: run `git rev-parse HEAD`). Commits, oldest first:
- 74ed027: RED tests
- 80ab9f5: the seam code
- 423f92e: D12 records

Only report_view.py, charts.py and tests changed. display.py needed no change, since `format_value` already takes `decimals`. Nothing outside the three files was needed: render.py and app.js already draw figures generically, and app.css already had classes for the new kinds. No suppressions were added (noqa 13, type: ignore 5).

**Seam API for W2** (all in `report_view.py`):
- `ChartKind` gains `range` and `bullet`. `ChartMark` gains `decimals: int | None` (0..6) and `hatched: bool`. `ChartSpec` passes `mark.decimals` to `format_value`.
- `strict_multiple(text) -> tuple[Decimal, int] | None` is the strict parse. It uses `\d+(\.\d+)?x` with ASCII digits, at most 6 decimals. The text must also round-trip through `format_value`, so "04.00x" and "1000.00x" are rejected.
- `_chart_fact_cell(fact, unit_class, refs, *, strict_text=False) -> Cell` now accepts `percent`. With `strict_text`, a rejected text gives a gap cell using the `G#` in `refs`. With no `G#` it raises. It never returns 0.
- `_chart_mark(fact, cell, *, series, label, role="value") -> ChartMark`. It takes `value` and `decimals` from the fact (or the parse), and sets `hatched` when the fact's `value_class` is `analyst_judgment`.
- `build_index` allocates a `G#` for a known text fact in `_STRICT_MULTIPLE_FIELDS` (only `("T4.9","threshold")`) when the parse rejects its text. The passport does not echo the text.
- `_na_strip(block_id, owner, scale, reason=None)` and `_strip_reason(block_id)`. `_STRIP_FIGURES["maturity-wall"] = (("S.4","Maturity wall",None),)` is added, with a "CP-1 is not settled" reason. In `_block`, `modules.get("CP-1")` replaces the indexing, so a view with no CP-1 degrades without `KeyError`.
- `FigureProducer = Callable[[block_id, View, refs], tuple[Figure, ...]]` and `register_figure_producer(block_id, producer, pathways: frozenset[str] | None = None)`. It refuses a duplicate, an unknown block, an unknown pathway, and a chart-kind block. The registry `_FIGURE_PRODUCERS` ships empty. `_block` calls `_registered_figures(...)` for every non-chart block, period_grid included, in the populated branch only.
- S.5 entry point: `_cp1_period_figures(block_id, view, refs)` has the `FigureProducer` signature. W2 registers it directly with `register_figure_producer("financials-credit-metrics", _cp1_period_figures, pathways=frozenset({"credit_snapshot"}))`.
- `_cp1_strip` now shares `_cp1_figures` with the S.5 entry point, driven by a `_CP1_FORMS` table (S.5 is grouped, amount, "beside"). `cp1_chart_series` may now return S.5 after S.4. The labels "Net revenues" and "Adjusted EBITDA" are added.
- `charts.py`: `_range` and `_bullet` renderers. The `hatched` flag drives the existing hatching and stripes. The waterfall running-total label uses the mark's decimals.

**Answers to attempt 1's questions:**
1. `build_index` is in `report_view.py`, so the rejected-text `G#` is allocated there as above.
2. `maturity-wall` stays `dense`. The degraded-path test monkeypatches `_spec_of` to `chart`.
3. The suppression baseline had no room, so none were added.

**Tests:** `tests/test_chart_seam.py` has 55 tests, all green. Marks come from the rv3, cr1, s5 and dr345 oracles.
- Gates run (each exit 0): `test_chart_seam.py`, `test_financial_series.py`, `test_legal_render.py`, `test_connected_render.py` together (167 passed). `test_cp1_chart_render.py` ran separately (36 passed, unchanged).
- Also run: `cases/pins.py --check` (86 paths match), `ruff format`, `mypy --strict` on the two src files.
- The `earnings_update` test confirms S.5 is absent there because of the pathway gate. An ungated control registration does draw it.
- Wider run: 682 passed and 1 xfailed (the S.4 tripwire, still strict-xfail), then `-x` stopped it at one failure. The last batch I started ran past the timeout and I killed it. The `test_owner_*` and `test_method_*` files were not run.

**D12:** two `post_import_patches` records are appended to `docs/reuse/manifest.json`, for `charts.py` and `report_view.py`, with `project_commit` 80ab9f5. `display.py` is not edited. The `review` field points at `docs/rulings/2026-10-29-stage3.md`, which exists in the lane but not in this branch. Fix the path at merge if you want one that resolves.

**For W2 and the controller:**
- `ruff check` reports SIM102 at `report_view.py` (the debt-stack check in `ChartSpec.coherent`). It was already present at 731059f and I left it.
- `tests/test_connect_cp3c.py::test_bindings_follow_the_lease` fails. It expects T3D.1 out of `refinancing-paths`, which is the W2 binding move (ruling item 6.1). I did not touch bindings, so it is not caused by this change.
- The `bullet` renderer reads series order: threshold, current, headroom. It draws headroom as text plus a dashed span, and no direction or verdict. The `range` band spans all plotted marks of a row, as in the design. Row labels are the part before " · ".
- The `.venv` symlink I created for running gates is removed. No background process is left.

Not verified: browser appearance of the range, bullet and S.5 beside-layout (SVG structure and aria labels only); the full `render()` HTML path for a period_grid figure; the 10 untested files in `test_owner_*`/`test_method_*`; real producer data for S.5 (`cp1_chart_series` has no S.5 yet, so the test injects it); mutation testing; the full suite; GitNexus `impact` and `detect_changes` (not run); no test or fixture for a view where CP-1 is present but unsettled (only the no-CP-1 case is covered). Ledger: agent=mx-feature fix-rounds=0 gates-first-pass=n/a (seam tests failed as intended before the code, then passed first time).
