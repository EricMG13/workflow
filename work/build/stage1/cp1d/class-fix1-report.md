CP-1D class round fix 1 is committed as **cacd98e** on `claude/cp1d-stage1`, on top of 48267a0. I did not merge the lane. The fix is test-only: the new tests found no code defect. M1, L1 ×2 and L2 are all killed, and every gate exits 0.

**What changed** (`tests/test_method_cp1d.py` only, +14 lines; `src/deploy_workflow/owners/cp1d.py` is unchanged):
- **M1 (Medium):**
  - `test_edge_cut_is_read_in_every_reading` has a new row: quote `"25 first-\npriority points."` on page `"The level is 425 first-priority points."`. It reads `[]` and gets the exactly-one text.
  - `test_edge_figure_whole_on_the_page_is_counted` has the twin: the same quote on `"The level is 25 first-priority points."` reads `["25"]`.
  - Together they kill "shift applied at start edge too".
- **L1:** two new rows in `test_edge_figure_whole_on_the_page_is_counted`, each reading `["25"]` with no exactly-one text:
  - `"25 percent over) holds."` on `"The level (25 percent over) holds."`;
  - `"The level is 25"` on `"The level is 25) percent."`.
  - These kill "'(' alone cuts" and "')' alone cuts".
- **L2:**
  - `TEXT_FIELDS` gains `gaps[1].gap`, `gaps[1].action`, `assessments[1].rationale` (positive pack) and `assessments[1].limitation` (gap pack).
  - The fixtures hold only one gap, so `_text_inputs` appends a copy of `gaps[0]` for the `gaps[1]` paths.
  - Each path runs every `BLANK_CASES` case. Whitespace-only text gets exactly `(<path>: empty text,)`.
  - This kills "blank: first gap only".
- Decisions (a) and I1 are unchanged; they are with LEAD.

**Mutants** (full temporary copies, `PYTHONDONTWRITEBYTECODE=1`):
- **Reviewer's `p_review_mutants.py`: exit 1.** The unmutated copy passes (exit 0).
  - Killed: M1, L1 ×2, L2, "start tests at end-only edge", "first assessment only" and the informational "LEAD not-on-page".
  - Still surviving, as the review expected: I3 "end test at start-only edge" (equivalent), I2 "cited text: first source" and "cited text: last span", and the two blank-position mutants under (c), "placed first" and "with bridge-not-found".
  - Exit 1 comes only from those five; they were out of scope for this fix.
  - Output: `<S>/cp1d-class/fix1_review_mutants.out`.
- **My `p_class_mutants.py`: exit 0.** The unmutated copy passes, and all 21 mutants are still killed (`<S>/cp1d-class/fix1_class_mutants.out`).
- **`p_frozen_readings.py`: exit 0.** 45 readings, none moved.

**Gates** (all exit 0, first time):
- `PYTHONPATH=src …/python -m pytest -q -p no:cacheprovider tests/test_method_cp1d.py`: 287 passed, 1 skipped (Stage 2/4).
- `ruff check` and `ruff format --check` on both files.
- `MYPYPATH=src mypy --strict` on both files.

`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`

Not verified:
- Only the CP-1D test file ran this round: no full suite, no CP-2G/CP-2H suites, no G1 or Stage 2 run.
- No real (non-synthetic) source text.
- I2 (duplicate source ids or locators), I3 and the blank-position mutants are not pinned, as the review left them.
- I1 (a quote's own `-\n` before the figure) is still present, pending LEAD.
- GitNexus `detect_changes` was not run.

agent=general-purpose(opus) fix-rounds=1 gates-first-pass=y
