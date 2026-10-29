**CP-8 oracle re-pin review (claude/s4-cp8-oracle f4d1f93 vs 18dc1fa)**

**Verdict: APPROVE, both on spec and on quality.** No High, Medium or Low findings.

**Spec**
- Info, `cases/cp8-owner/expected.json:8164`. `text` at `cases.no_outcome.tables[8].rows[1].facts[0]` (`cp8.what_changed.outcome.value`, status known) now holds the token form. It equals `cases.no_outcome.claims[0].text` byte for byte. A structural diff of the whole oracle shows that this path is the only change. `shown` and `claims[0].resolved` are unchanged and equal each other. Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/stage4-cp8-review/p1_field_diff.py` (exit 0).
- Info, `shown` left at `…decision ∅ G# and every…` (`expected.json:8165`). This is within item 19 (`docs/rulings/2026-10-29-stage3.md:152`): two fields may move, and moving one is a subset of that. Plan §5:62 asks for `shown` to be "the pattern `∅ G#` bound at run time", and it already was. It matches the CP-2D A7 binding (`cases/cp2d-owner/expected.json:1061`: the `∅ G#` pattern matches `∅ G` plus digits, and tests apply `.replace("G#", GAP_REF)`).
  - One difference from CP-2D: there, A7 covers whole gap cells. Here the pattern sits inside a known text sentence.
  - CP-8's own manifest describes the pattern only for gap cells (`build.py:2084`, `:2194`), so this known-text use is not written in the manifest. The plan and item 19 explicitly permit it and the manifest cannot be edited here, so I am not raising it as a finding.
- Diff size: 12 lines added, 7 deleted, in 3 files. The preparer touched only `cases/cp8-owner/builder/build.py`, `expected.json` and `cases/PINS.json`, as the brief requires. Nothing under `src/` or `tests/` changed.

**Quality**
- Info, `cases/cp8-owner/builder/build.py:969-970,985,1299-1304`.
  - `T()` takes a new optional `shown`, and `fact()` falls back to `text` when it is None. Only the outcome row passes it.
  - The rebuilt output differs from 18dc1fa only in the one `text` field, so the new key does not leak into any other fact.
  - No stub, fake value or catch-all.
- Gates: two fresh `git archive` copies of f4d1f93 rebuilt with exit 0 each. `expected`, `manifest` and `submissions` are byte-identical across the two copies and match the committed files. `python3 -I cases/pins.py --check` in a fresh copy exited 0 (86 paths). Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/stage4-cp8-review/p2_rebuild.sh` (exit 0).

**RED-test rule for the builder** (`tests/test_method_cp8.py::test_no_settled_cp8_fact_carries_a_gap_placeholder_literal`)
1. Check the product's settled CP-8 facts, which `cp8` emits for every case, `no_outcome` included. Do not check the oracle file. For every fact, `"G#"` must not appear in `text` or in any stored `shown`/display string. `GAP_PLACEHOLDER` must not exist.
2. Guard against a vacuous pass: in `no_outcome`, the fact `cp8.what_changed.outcome.value` must exist with `text == expected claims[0].text`, which contains `[T7.3.window.realized_value]`.
3. The oracle keeps `∅ G#` only in `shown`, as an A7 pattern. A test may use it only to compare rendered output, binding it with `.replace("G#", GAP_REF)` or the regex `∅ G\d+`, where n is the gap reference the page gives `T7.3.window.realized_value`. Never assert it against product facts.
4. The `oracle_cell` comparison of `text` at :184-189 and :247 must compare the token form directly, with no `G#` substitution for this known fact.

**E2 hits**
None outside CP-8. Across all 17 `cases/*-owner/expected.json` files, the only known fact whose `text` or `shown` holds `∅ G#` is CP-8 `cp8.what_changed.outcome.value` (`shown`). The other files that contain `∅ G#` have it only on non-known gap cells, which are out of scope. Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/stage4-cp8-review/p3_e2_grep.py` (exit 0).

Not verified: no pytest was run (build-first rule), so the effect on `tests/test_method_cp8.py` and `tests/test_connect_cp8.py` is read from the code, not executed; the builder ran with system `python3 -I`, not the lane `.venv`; the E2 scan covered only facts with status `known` in `cases/*-owner/expected.json`, not `cases/snapshot` or claim `resolved` strings; I did not check that the `owner_rendering.py` renderer exists or can resolve the token.
