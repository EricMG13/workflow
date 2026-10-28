# CP-2A round 9 report (controller-saved from the implementer's hand-back)

CP-2A round 9 (choice 5) report

Commit: aa4ab01 on worktree-agent-a34fec3e9469279cd. It builds on the merge of claude/module-dev-status-review-0981b6 at a1d367e. Only two files changed: src/deploy_workflow/owners/cp2a.py and tests/test_method_cp2a.py.

Frozen-value check: none of the frozen gap texts contains a `{`. I checked the positive, gap and fixture_quarter_known cases, and interest_undisclosed has no gaps. No frozen value changed: every oracle test still passes, and cases/ is untouched.

Items and their tests (all covered by tests/test_method_cp2a.py::test_round9_gap_texts_are_stored_spelled):
1. T2B.9 gap texts are stored spelled. The gap, why_it_matters, affected_analysis and action cells all go through `_spelled`. The cells keep value_class analyst_judgment. id and severity are unchanged.
   - Red first: `Debt of {interface-fact:9a9d…|US$ m} has no maturity schedule.` != `Debt of 50 US$ m has no maturity schedule.`
2. The own line is `Gap (<severity>): <spelled gap>`. The test asserts `Gap (Material): Debt of 50 US$ m has no maturity schedule.` is in the limitations, and that no `{` remains in any T2B.9 cell or limitation.
3. `_spelled` is generalised.
   - It now takes `str` and returns `str`. The two optional limitation callers check for None themselves.
   - The docstring now covers all stored text. The raise stays as an invariant, with the message `Stored text reference <id> does not name a known CP-1 figure`.
   - `_gaps` now receives `bound` from compute.
4. The facts stay in cp1_references. `_references` already reads the gap texts, and the test asserts total_debt_ltm and total_leverage_reported are among the copied ids.

Mutants: 8 of 8 killed, runner exit 0. The runner is /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2a-r9/mutants.py. Each mutant runs in a full copy of the worktree, and each killed mutant made the suite exit 1.
- gap_cell_raw, why_raw, affected_raw and action_raw each store one gap field raw.
- own_line_unspelled uses `g.gap` in the own line instead of the spelled text.
- spelled_identity makes `_spelled` return its input unchanged.
- scenario_limitation_raw and assessment_limitation_raw check that the round 5 paths still hold after the signature change.

Gates (all exit 0):
- pytest tests/test_method_cp2a.py: 109 passed, 1 skipped (v17, Stage 2).
- ruff check.
- ruff format --check.
- MYPYPATH=src mypy --strict on both files.

prose.issues / bare_figures hits:
- Raw test gap texts with bound refs: prose.issues returns () for all four. bare_figures flags the ref token itself in all four, for example `{interface-fact:9a9d…|US$` and `{interface-fact:c11f…|x}`. That is how bare_figures treats unrendered refs; it is not prose.
- Stored spelled texts show the expected spelled-figure hits:
  - `Debt of 50 US$ m has no maturity schedule.`: Bare figure 50.
  - `Leverage of 1.67x may breach a test.`: Bare figure 1.67x.
  - `Break-point ranking at 50 US$ m of debt`: Bare figure 50.
  - `Compare 1.67x with the lenders' tests.`: Bare figure 1.67x.
  - `Gap (Material): Debt of 50 US$ m has no maturity schedule.`: Bare figure 50.
- The new error message has no hits.

Not verified:
- Rendering of the spelled T2B.9 cells through report_view or the shell (Stage 2).
- The reading order of gap-text refs within cp1_references when they are not already named earlier. `_references` was not changed, and the test checks membership only.
- A refusal on a gap text with a ref to an unknown fact. That is the validator's job, unchanged; `_spelled`'s raise is only an invariant and is not exercised.
- CP-2G T2H.9, which was not touched.

Ledger: CP-2A round 9 agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y
