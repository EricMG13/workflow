# Shared defect test fix2 re-review (mx-precise)

**Re-review, fix round 2 (292b1d2): mutant A**

**Verdict: APPROVE.** The worktree is at 292b1d2 and is clean.

**Mutant A is closed.** Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/defect-classes-review/fix1/p5_verbatim_mutants.py`, exit 0.
- **Mutant A** (adding `analysis.*.text`, which is `Claim.text`, to the CP-0 allowlist) now fails with `analysis.*.text: listed verbatim but refused every value`. The check is at `tests/defect_classes.py:782` and `:789-793`.
- **Mutant B** (`allowed = True`) is still caught: the selfcheck gives 2 failed, 242 passed.
- **Citation paths:** none of CP-0's 28 citation paths is on the allowlist.
- **A pattern that refuses every value** fails with the expected message, and `test_defect_classes_selfcheck.py:523` asserts that exact list.
- **The real CP-0 and CP-1 allowlists** still pass inside the gate run.

**Ruling on a pattern that spans several paths.** The check counts a pattern as used once any one of its paths accepts a value. It does not check each path separately.
- **Whether it matters:** it does not today.
  - `path_matches` lets `"*"` stand only for a list index, so every path a pattern covers is the same field of the same model.
  - Each pattern therefore has a single schema type. A plain-text path and a `RunText` path cannot share one pattern.
  - The only exception would be a list of mixed model types that both have a field with the same name. I found no such field on any allowlisted path. I reasoned this from the model definitions I read and did not scan the schemas for it.
  - Different list items of one field can still give different results, for example through a cross-field rule. But they all end up in the same kind of stored field, so this does not reopen M1.
- **Info:** `test_a_verbatim_pattern_needs_only_one_accepted_value_on_one_path` (`test_defect_classes_selfcheck.py:529`) makes the same call and the same check as the test at `:519`. Its comment says the fake has a `parts.1.note` that is missing, but the test never shows that a second, refusing path is excused. It adds nothing new. It can be fixed in the end-of-branch batch, with no review round of its own.

**Gates**
- The three test files: 280 passed, exit 0 (50.8 s).
- `git grep noqa -- src tests | wc -l` gives 13. That is within the ceiling of 13.
- The `p5` probe: exit 0.

Not verified: I did not re-run ruff or mypy. I did not scan for list fields that mix model types. Owner-core `submit` paths are untested because no core is registered yet. Timings come from one run.
