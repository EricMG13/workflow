# W1 attempt 1 (mx-feature a23964be): blocked by the cross-worktree write guard; read-only design

W1 is not built. I stopped before changing any file, because the harness blocked my first write.

**What blocked it.** My first `Write` call, for `tests/test_chart_seam.py` in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s3-wire`, was rejected by a PreToolUse hook. The hook's message: "This session is running in an isolated git worktree at `.../module-dev-status-review-0981b6`, but `.../s3-wire/tests/test_chart_seam.py` belongs to a different worktree. Do not write to other worktrees' files from this session."

The brief tells me to work in `s3-wire`, but a message from another agent can't lift a permission guard. I could probably have written the files with Bash heredocs, but that would sidestep the guard, so I did not.

**State.** `s3-wire` is clean on branch `claude/s3-wire` at 731059f. There are no commits, no gates run, no background processes, and no D12 records. Tip SHA is unchanged. Ledger line: `agent=mx-feature fix-rounds=0 gates-first-pass=n/a`, task not built.

**What would unblock it.** One of these:
- Launch me with `s3-wire` as the session's primary worktree.
- Have the user allow cross-worktree writes for this session.
- Take the design below and run the build from a session rooted in `s3-wire`.

**Read-only findings** (for whoever builds it; I read the brief, the oracles, `report_view.py`, `charts.py`, `display.py` and the design `charts.js`):
- All seam changes fit in `report_view.py`, `charts.py` and `display.py`. I found nothing that needs `render.py`, `app.js` or `bindings/`.
- `display.format_value` already takes `decimals`, so it needs no change.
- Planned `report_view.py` changes:
  - `ChartKind` gains `range` and `bullet`.
  - `ChartMark` gains `decimals: int | None` (0..6) and `hatched: bool`. The `ChartSpec` text check passes `mark.decimals` to `format_value`.
  - `_chart_fact_cell` gains a percent branch: `fact.unit in _PERCENT_UNITS` and scale 1.
  - `_chart_fact_cell` also gains `strict_text: re.Pattern | None`. `MULTIPLE_TEXT = \d+(\.\d+)?x` is read with `fullmatch`, and the mark's `decimals` is the number of fractional digits in the text, so `format_value` reproduces the text. A rejected text becomes a gap cell using the `G#` found in `refs`.
  - A new `_chart_mark(fact, cell, series=, label=, strict_text=)` takes `decimals` from the fact and sets `hatched = (value_class == "analyst_judgment")`.
  - `_na_strip(..., reason=None)` and a `_strip_reason(block_id)` helper. The `maturity-wall` reason is a `CP1_NOT_SETTLED` text, and the `maturity-wall` entry is added to `_STRIP_FIGURES`.
  - In `_block`, replace `modules["CP-1"]` with `modules.get("CP-1")` so a view with no CP-1 takes the degraded path instead of raising `KeyError`.
  - A registry `_FIGURE_PRODUCERS` plus `register_figure_producer(block_id, producer, pathways=None)`. It ships empty, refuses a duplicate registration, and is gated by pathway. `_block` calls it for non-chart kinds, including `period_grid`.
  - Split the per-figure loop out of `_cp1_strip` into a shared helper, and add `_cp1_period_figures(block_id, module, refs, supplied)` as the S.5 entry point. It uses form `grouped`, `amount`, `US$m`, placement `beside`. Add `revenue` and `adjusted_ebitda` to `_CP1_CHART_LABELS` with the oracle captions "Net revenues" and "Adjusted EBITDA".
- `charts.py`:
  - `_is_synthetic` also returns true for `mark.hatched`, which drives hatch patterns, hollow markers and the waterfall stripes.
  - Add `_range` and `_bullet` renderers and their `_size` entries.
  - `range` draws one strip per metric. The row key is the label before " · ", because the oracle's Peers marks are labelled "<metric> · <peer>".
  - `bullet` draws a threshold tick and a current bar from the first two series. Headroom is text only, because direction is not on a `ChartMark`.
- Test design: `tests/test_chart_seam.py` would import the `chart_case` fixture from `tests/test_cp1_chart_render.py`. It would take marks and texts from the `cr1`, `rv3` and `s5` oracles, and the degraded-path test would use `test_legal_render._seed`.

**Open questions for the caller:**
1. **`G#` for a rejected text** (CR.1 threshold, item 5.3). `build_index` allocates a `G#` only for unsettled facts, so a known text that fails the strict parse has no `G#` in `refs`. My seam fails closed with `ValueError("... G# reference")`. Either W2 or a later seam change must make `build_index` allocate a `G#` for strict-parse facts.
2. **`maturity-wall` spec kind.** I would leave it `dense` in W1, because W2 flips it to `chart` with the binding. I would test the degraded path by monkeypatching a spec to `chart`.
3. **Gate counts not checked.** I did not run `git grep noqa` or `git grep "type: ignore"`, so I can't say whether the suppression baselines (≤13 and ≤5) have room for a test-file import suppression.

Not verified: everything. No code was written, no test or gate was run, and the oracle-derived design above is from reading only.
