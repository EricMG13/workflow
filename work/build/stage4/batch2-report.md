Batch 2 is built and committed. The one thing to confirm is that the `_prose_lines` fallback for malformed brackets (below) is acceptable. The `.venv` link is removed and the tree is clean.

**Worktree and tip:** `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a7e48f47956c9ff2e`, branch `claude/s4-batch2`, tip 133e2ec.
- 766ca1e is 4c69ebc plus the merge of the frozen CP-8 oracle.
- 8abfb0c carries the code and tests.
- 133e2ec is the `docs/reuse/manifest.json` record.
- I did not edit `cases/`, a lease, `tests/test_owner_rendering.py` or `owner_rendering.py`.

**Changes**
- `src/deploy_workflow/owners/cp8.py`: removed `GAP_PLACEHOLDER`. `_resolved` now spells known figures only, so the outcome fact keeps its `[T7.3.window.realized_value]` token.
- `src/deploy_vii/report_view.py`, `_prose_lines` only: a known text fact that carries a well-formed `[ref]` or `{ref|unit}` token goes through the unchanged `resolve()`. New helpers are `_carries_reference` and `_token_runs`. A known fact gives its figure run, a gap gives the page's `∅ G<n>` run, and a token naming a fact outside the module raises `ValueError`.
- Text whose brackets are not reference syntax (for example CP-3's `[Insufficient Information]`) stays literal prose. This is a documented narrow `except ValueError` in `_carries_reference`, not logged.
  - Edge: a fact mixing a valid token with a stray bracket also renders raw.
  - Without the fallback, `tests/test_connect_cp3.py` broke on that label.
- `tests/test_method_cp8.py`: the item 21 RED test (no `G#` in any product fact, a non-vacuous guard on the `no_outcome` outcome fact, `GAP_PLACEHOLDER` absent). `oracle_cell` now compares this fact's token `text` directly.
- `tests/test_connect_cp8.py`: three render tests. The outcome cell shows `∅ G<n>`, with `n` taken from `gap_refs(build_index(view))`. A known window token renders as a figure. A token outside the module fails closed.
- `docs/reuse/manifest.json`: one `post_import_patches` record for `report_view.py` (prior 1f50c7b9, new cbb4c368, project commit 8abfb0c).

**RED evidence:** before the code change, the placeholder test failed (2 cases), and the three render tests failed with the raw token on the page and no `ValueError`. After it, 1301 passed in the two CP-8 files.

**Gates**
- `pytest tests/test_method_cp8.py tests/test_connect_cp8.py tests/test_connected_render.py`: 0 (1315 passed).
- `pytest tests/test_connect_*.py` (full) plus the first three files: 0 (3113 passed, 2 skipped).
- `tests/test_owner_rendering.py -k fast`: 0 (152 passed).
- `tests/test_chart_seam.py`, `test_earnings_render.py`, `test_legal_render.py`, `test_cp1_chart_render.py`: 0 (261 passed).
- `python3 -I cases/pins.py --check`: 0.
- `MYPYPATH=src mypy --strict` on `report_view.py`, `cp8.py` and `owner_rendering.py`: 0.
- `ruff format --check`: clean after formatting.
- `ruff check`: one SIM102 at `report_view.py:312`, in code I did not touch; none in my lines.
- Suppressions: none added.
- E2 grep: the only known fact with `∅ G#` is the oracle's own `shown` pattern on `cp8.what_changed.outcome.value`.
- `probe_d12_strict.py ... 697fe8a HEAD`: my record passes (chain=ok, item19=ok). Failures it still reports predate this work and belong to the owner:
  - 3e5b537 and 24f879a (`report_view`);
  - the `statement_extract.py` c81932f entry, which is misplaced and has a sha mismatch. I did not see 8aef58d in the output.
- No test outside the CP-8 files moved after the `_carries_reference` fallback. There are no `tests/test_report_view*.py` files.

**Deferred:** `cd <worktree> && .venv/bin/python -m pytest tests/test_owner_cp8.py` (needs the `.venv` link to the lane, which I removed).

**Ledger:** agent=mx-feature fix-rounds=0 gates-first-pass=n (the CP-3 break fixed before commit).

Not verified: `tests/test_owner_cp8.py` (deferred); the full suite; whether the real owner-rendered CP-8 page (`_capture`'s page and payload equality) now carries `∅ G<n>`, since no owner-run render was exercised; a `report_view.py` edit that leaves the owner's older D12 failures; the mixed valid-token plus stray-bracket text.
