**Verdict: APPROVE.** Fix 1 closes M1, L1 ×2 and L2 from my class-round review, and cp1d.py is unchanged.

Commit cacd98e (diff 48267a0..cacd98e) adds 14 lines, all in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/cp1d-stage1/tests/test_method_cp1d.py`. `git diff --quiet 48267a0 cacd98e -- src/` exits 0.

**M1 (start edge in a joined quote).**
- The cut row is in `test_edge_cut_is_read_in_every_reading` (~:1136): page `"The level is 425 first-priority points."`, quote `"25 first-\npriority points."`. It asserts the quote is found on its page (no citation issue), that exactly-one fires, and that the reading is `[]`.
- The whole twin is in `test_edge_figure_whole_on_the_page_is_counted`. It asserts `["25"]` is read and exactly-one does not fire.
- Both are what I specified.

**L1 (accounting parentheses need both sides).** Two twin rows assert `["25"]` with no exactly-one:
- `"25 percent over) holds."` on `"The level (25 percent over) holds."`;
- `"The level is 25"` on `"The level is 25) percent."`.

**L2 (second gap).**
- `TEXT_FIELDS` gains `gaps[1].gap`, `gaps[1].action`, `assessments[1].rationale` and `assessments[1].limitation`.
- The `gaps[1]` copy does not weaken the other blank paths:
  - `_text_inputs` appends the copy only when `keys[:2] == ("gaps", 1)`, so every other path builds its payload as before.
  - On the `gaps[1]` paths the test asserts the issues equal exactly `(frame,)`. So the copied gap is valid on its own, and a mutant that always uses index 0 or only the first gap would fail.

**Probe exit codes** (probes in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp1d-class-review/`):
- **`p_review_mutants.py`: exit 1.** It ran from a full temporary copy with PYTHONDONTWRITEBYTECODE=1, and the output is in `review_mutants_fix1.out`.
  - The unmutated copy passes (exit 0).
  - M1 (`shift applied at start edge too`), L1 ×2 (`'(' alone cuts`, `')' alone cuts`) and L2 (`first gap only`) are now killed.
  - The exit 1 comes only from the survivors you accepted: I2 (cited-text first source and last span), I3 (end test at a start-only edge), `placed first` and `with bridge-not-found`.
  - All the other mutants stay killed.
- **`p_survivor_effects.py`: exit 0.** HEAD reads every scenario correctly.
- **`p_blank.py`: exit 0.**

**Gates** (cp1d-stage1 worktree, venv binaries; all exit 0):

| Gate | Result | Exit |
|---|---|---|
| `PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/test_method_cp1d.py` | 287 passed, 1 skipped | 0 |
| `ruff check` (both files) | clean | 0 |
| `ruff format --check` (both files) | clean | 0 |
| `MYPYPATH=src mypy --strict` (both files) | clean | 0 |

Not verified: I did not read the fix report (class-fix1-report.md) and checked the diff only; I re-checked only M1, L1 and L2, and I1 (the round 10 quote-wrap sign drop, sent to owner/LEAD) is still open and outside this fix; I did not run the full suite or the CP-2G/CP-2H suites; GitNexus `detect_changes` was not run.
