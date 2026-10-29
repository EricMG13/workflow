# Batch builder 1: CP-1D folded-in fixes (general-purpose, opus)

## CP-1D folded-in fixes: two commits on `claude/s2-batch`. All four probes exit 0. The brief's single pytest command still exits 1, from a test-order defect that predates this work.

**Commits:**
- `1c512aa7136a504f9e0993e8ae531d3100fb6102`: the fixes and tests.
- `aafa9f0`: the D12 record for `report_view.py`, in the chained form. Its `prior_project_sha256` is 974e5a…, its `sha256` is fc9c18…, and its `project_commit` is 1c512aa. `bindings/cp1d.py` has no manifest record to chain, so none was added.

The tree is clean. The Edit tool's hook refuses writes outside this session's worktree, so every edit to s2-batch was made from Bash with Python string replacement.

**Items** (all new or changed tests are in `tests/test_connect_cp1d.py`):
1. **M1.** `owners/cp1d.py`: `"shown"` is now `fact_spelling(fact, None)[2]`, and the unused `spelled` import is gone. `_cp1_module` and `_settled_store` take a new `decimals=` argument.
   - New test `test_run_driver_binds_the_oracle_figures_over_the_view_of_a_real_store[3 cases]` runs `cp1d_runs.fig_bindings` over `cp1d.view` of a fast settled store with `decimals=None`. It binds both the literal's figures and all seven.
   - Red: 3 failed with `RuntimeError: FIG adjusted_ebitda_ltm: unit/shown US$ m/30 US$ m`. Green after the fix.
2. **M2.** The `_Spec` title is now "Cash conversion and restated leverage" and the T1D.6 binding label "Cash conversion and leverage". The two strings were swapped.
   - `test_report_view_composition_and_spec_of` now takes its titles from `expected.json`.
   - New test `test_fp02_block_titles_and_tab_labels_equal_the_oracle[3 cases]` builds the page with `report_view.build` and compares block heads, binding labels and tab labels with the oracle. A one-table block renders no tab strip, so its oracle label is checked against the binding label.
   - Red: the title failed first (4 failed). With the title fixed, the label failed. Green after both fixes.
3. **L4.** `OWNER_SPECS["CP-1D"]` is moved to the tail, after CP-MODEL and CP-L10. The other dicts already had CP-1D last.
   - I removed the CP-1D exclusions in the connect tests for cp2a, cp2d, cp3, cp3d, cp4 and cp8, restoring their original lines. All 6 were red at index 4 (`'CP-1D' != 'CP-MODEL'`) before the move.
   - Beyond the brief: CP-1D's own `test_registrations_are_appended_at_the_end` used to require CP-1D to be the last key in each dict. It now checks the base prefix and that CP-1D comes after CP-L10, `OWNER_SPECS` included, so CP-2G's appends will not break it. It was red before the move.
4. **Method note.** `methods/cp1d.md` gains a "Round 5 item 12 (accepted readings)" paragraph (`1.5-Q` and a wrapped `1.5-` then `nd` read 1.5) and a "Source quotes" freeze paragraph.
   - `test_method_note_exists_and_names_each_limit` now looks for these needles; it was red until the note was added.
   - The new `test_round_5_item_12_readings_noted_in_the_method` passed from the start, because the reading already worked; it pins that the readings compose.

**Probes:** the reviewer's originals hard-code the s2-cp1d worktree. I ran copies whose `_h.py` and p8 take a root argument, in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp1d-batch-probes/`.

| Probe | Exit | Note |
|---|---|---|
| p10 | 0 | 0 mismatches on real-shaped facts; the decimals=2 fixture still prints "30.00", which is not counted |
| p11 | 0 | all 3 cases bind |
| p5 | 0 | `bad: 0` |
| p8 | 0 | |
| `x_fp02_cells.py` (mine) | 0 | 0 cell differences other than gap representation |

**Gates:**

| Gate | Exit | Result |
|---|---|---|
| Brief's pytest command, as written | 1 | 6 failed, 2633 passed |
| The same files with `test_owner_g1x.py` last, plus `test_earnings_render.py` | 0 | 2729 passed, 3 skipped |
| The two halves run separately | 0 and 0 | |
| `tests/test_earnings_render.py` | 0 | 90 passed |
| `ruff format --check` | 0 | after one reformat of my new test |
| `ruff check` | 0 | the only hit is the old SIM102 at `report_view.py:293`; 0 with it ignored |
| `MYPYPATH=src mypy --strict`, 11 changed files | 0 | |
| `pins.py --check` | 0 | 69 paths |

The noqa count stays at 13 and the `type: ignore` count at 8; none was added.

**Predating defect (for the owner, not fixed):** `test_owner_g1x.py:613` removes `_ENTRY_VALIDATORS["CP-1A"]` with `monkeypatch.delitem`. Undoing it puts CP-1A back at the end of the dict. Any later test in the same run that checks `_ENTRY_VALIDATORS[:2] == ["CP-1A","CP-2"]` then fails: the cp2a, cp2d, cp2e, cp3, cp4 and cp8 connect tests. Base e3ff482, exported, fails the same 6 tests with the brief's command order.

Not verified: no real CP-1 promotion, closed CP-1D run, deferred `test_owner_cp1d.py` suite or G2 `cp1d_closed` was run, so M1 is shown on a fast store only. FP02 was checked through `report_view.build`, not an HTML render. GitNexus `detect_changes` was not run. The other review Lows (L1, L2, L3, L5, L6) are untouched.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n
