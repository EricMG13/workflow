Stage 4 batch 2 review (`claude/s4-batch2` 766ca1e..133e2ec). I checked it in a fresh copy at `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch2-review/tree` and edited no repo file.

**Verdict: REVISE.** Spec: REVISE, because of H1. Quality: REVISE, because of H1 and M1.

**High**
- **H1. `src/deploy_vii/report_view.py:1600-1610`, called from :1657.** The `except ValueError` in `_carries_reference` hides a failure, and it is neither logged nor limited to the case it was written for.
  - A known text fact that holds a well-formed token plus any non-token bracket is shown raw instead of being resolved or failing closed.
  - This includes the case item 30 requires to fail closed. The text `Outside [T9.9.nope.value] and [Insufficient Information].` renders as plain text with no `ValueError`.
  - `... [T7.3.window.realized_value] see [note 1].` also shows the raw token on the page.
  - Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch2-review/probe_mixed_bracket.py`. It exits 1: all three mixed texts render raw.
  - **Smallest fix:** decide by a match for a well-formed token, not by trying a parse, and remove the try/except: `return prose._TOKEN.search(text) is not None`.
    - CP-3's `[Insufficient Information]` has no well-formed token (`_ID` allows no spaces), so it stays literal.
    - Any text that does hold a token goes to `resolve()`, which fails closed on a stray bracket or an unknown token.
    - Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch2-review/probe_token_match_rule.py`. It exits 0: both mixed cases fail closed, and `test_connect_cp3.py` plus `test_connect_cp8.py` give 783 passed, 1 skipped under that rule.
    - `_TOKEN` is private to `prose`. The fixer can either expose a small public `prose.has_reference(text)` or use the private name, but `prose.py` may be a reused file that needs its own D12 record. Your ruling.
  - The fix also needs a RED test for the mixed case: a known token plus a label must fail closed or resolve.

**Medium**
- **M1. `tests/test_connect_cp8.py:605-614`.** The positive render test makes two assertions that cannot fail, so the "known window renders the figure" case from item 21 and plan §5 is not really checked.
  - :605 asserts `line[1][1].startswith(f["text"] or "")`. The oracle's `text` for `T7.3.window.realized_value` is `None`, so the prefix is `""` and the check always passes. Any figure text would pass. It should compare against the oracle's `shown` (`109 days`).
  - :614 asserts `not any("G" == run[0] ...)`, but a run kind is never `"G"`. It should check `"gap"`.
  - Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch2-review/probe_vacuous_positive.py`. It exits 1: the prefix is `''`.

**Low**
- **L1. `tests/test_method_cp8.py:189-192`.** `oracle_cell` replaces the oracle's `shown` with its `text` for any known fact whose text contains `[`. Item 21 asks for exactly one fact, `cp8.what_changed.outcome.value`, to be compared directly. As written, any later bracketed known fact would skip its `shown` check without anyone noticing. Limit the condition to that fact id.

**Info**
- **Scope (process step 2):** the `report_view.py` diff only adds `_carries_reference` and `_token_runs` and changes the text-fact branch of `_prose_lines`. `resolve()` (:1096-1135) is unchanged.
- **RED tests (step 3):** the no-`G#` test meets item 21 except for M1. It checks the product's facts, guards against a vacuous pass by requiring the outcome fact with `text == claims[0].text`, and asserts that `GAP_PLACEHOLDER` is gone. The test for a fact outside the module is real, but H1 shows it can be bypassed.
- **D12 (step 4):** the record at 8abfb0c gives chain=ok and item19=ok (prior 1f50c7b9, new cbb4c368). The strict probe (`.../stage3-review/precise/probe_d12_strict.py <L> 766ca1e 133e2ec`) still exits 1, on records that predate this work and belong to the owner: 3e5b537 and 24f879a (item19=BAD) and 8aef58d (chain=GAP). The builder said 8aef58d was not in the output, but it is.
- **E2 (step 5):** it holds. `GAP_PLACEHOLDER` is gone from `src`. The only known fact in an owner oracle holding `G#` is CP-8's outcome `shown`. Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch2-review/probe_e2_grep.py`, exit 0. The remaining `∅ G#` strings in cp3c, cp3d, cp2e and liquidity_series are the spellings for gap-status cells, which is allowed.
- **Fake values:** none found apart from H1's fail-open path. `_what_changed_view` injects a `calculation_id` that matches the oracle's own `calc:T7.3.window.realized_value`, so it is not a fake.
- **Gates on the fresh copy:** `pytest` on `test_method_cp8.py`, `test_connect_cp8.py`, `test_connected_render.py` and `test_connect_cp3.py` exits 0 (1419 passed, 1 skipped).

Not verified: `tests/test_owner_cp8.py` and the full suite were not run; I did not check whether the owner-rendered CP-8 page (owner_rendering `_capture`) now shows `∅ G<n>`; mypy and ruff were not run on the fresh copy; I did not check whether `prose.py` is a reused file (it affects the fix's D12 needs).
