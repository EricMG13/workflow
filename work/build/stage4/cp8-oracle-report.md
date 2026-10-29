CP-8 oracle re-pin is committed, but only one field moved, not two.

**Worktree and tip**
- Worktree: /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-af35a9f8d4d312259
- Branch `claude/s4-cp8-oracle`, created from 18dc1fa.
- Tip: f4d1f93, with the Co-Authored-By trailer.
- Changed files: `cases/cp8-owner/builder/build.py`, `cases/cp8-owner/expected.json`, `cases/PINS.json`.

**Moved values** (`cases.no_outcome.tables[8].rows[1].facts[0]`, `fact_id` `cp8.what_changed.outcome.value`)
- `text` moved from "…the window since the decision ∅ G# and every variance are missing." to "…the window since the decision [T7.3.window.realized_value] and every variance are missing." The source is `cases.no_outcome.claims[0].text`, which is the CP-8-OUT-01 claim text in `build.py`.
- `shown` did not move. It is already "No realized outcome is recorded, so the window since the decision ∅ G# and every variance are missing.", which is exactly the CP-2D A7 pattern. The only difference from the plan is that `text` and `shown` were identical before; now only `text` differs.
- `claims[0].resolved` and every other value are byte-identical.
- The CP-2D A7 mechanism fits this cell. CP-2D stores `shown="∅ G#"` and tests bind it with `.replace("G#", GAP_REF)`. No new form was needed.

**Builder change**
- `T()` takes an optional `shown`.
- `fact()` uses `c["shown"]` when it is set.
- The outcome line in `cp8.what_changed` now calls `T(c["text"], …, shown=c["resolved"])`.
- The builder's `claims` line still resolves the `[T7.3…]` chip to `∅ G#` from the T7.3 fact's `shown`, so it needed no change.

**Builder targets** (for the builder, after the `mx-precise` review)
- `tests/test_method_cp8.py:184-189`, `oracle_cell`. It only substitutes `G#` when `status != "known"`. This fact is known, so the `text` comparison at :247 (`cell(...) == oracle_cell(...)`) will now see the token form in the oracle and the product text with `∅ G#`. Either `oracle_cell` binds `G#` into `shown` for this fact and the `text` assertion expects the token form, or the product keeps `text` as the token form. The second option is the intended end state, since `cp8._what_changed` will store the token form. The cell dict at :173 (`"text": fact.text`) then also needs the token form.
- `tests/test_method_cp8.py:60`, `GAP_REF`, stays. :269 stays as `exp["resolved"].replace("G#", GAP_REF)`.
- `tests/test_connect_cp8.py` has no assertion on the outcome cell today. Add the plan §5 render test next to `test_the_what_changed_block_is_cp8s` (:537). The outcome cell shows `∅ G<n>` where `n` is the gap reference the page gives `T7.3.window.realized_value`. The positive case shows the window figure unchanged.
- RED test: `tests/test_method_cp8.py::test_no_settled_cp8_fact_carries_a_gap_placeholder_literal`. It must check that no fact `text` or `shown` contains the literal `G#`. This is the point to resolve before the builder starts. The oracle's `shown` legitimately keeps `∅ G#`, so the test applies to product facts, not oracle cells.

**Gates**
- `python3 -I cases/pins.py` exit 0 (wrote 86 paths).
- `python3 -I cases/pins.py --check` exit 0.
- Double rebuild (build.py run twice) exit 0 both times; sha256 of `expected.json`, `manifest.json` and `submissions.json` identical across the runs. This was run twice in place, not in two fresh copies.
- `git diff 18dc1fa -- cases/cp8-owner/expected.json` shows exactly one line changed, the `text` field.

**Not verified:** no pytest was run (the build-first rule); no fresh-copy rebuild; the `tests/test_method_cp8.py` effect of the moved `text` is read from the code, not executed; the plan §5 grep for other owner modules storing a literal `∅ G#` (E2) was not run; the build ran with system `python3 -I`, not the lane `.venv`.
