# CP-2A fix 1 scoped re-review (mx-precise; controller-saved)

## CP-2A fix round 1: scoped re-review (worktree agent-a34fec3e9469279cd, `git diff 7ba456e 88526a1`)

**Verdict: APPROVE.** All four findings are fixed, and I found no new findings.

**1. M1: fixed.** `tests/test_method_cp2a.py:899` `test_p1w_gate_precedes_the_short_circuits_and_the_zero_check` kills both mutants, and it is the only test that fails for each:
- `break_gate_after_short_circuit`: exit 1. The test fails for the reason the review gave. On a quarter base with interest -1, b02 gives the short-circuit outcome instead of the P1-W outcome. The test also covers total debt 0.
- `stress_gate_after_zero`: exit 1. A 100% decline (E' = 0) and a base with I < 0 and D = 0 must give `not_applicable` with the P1-W reason on all four ratios.

**2. L1: fixed.** `quarter_line_points_only` is killed (exit 1), only by `tests/test_method_cp2a.py:924` `test_p1w_own_line_from_rows_alone`.
- I agree that `quarter_line_rows_only` is equivalent. It still survives (exit 0), which is why the runner exits 1.
- Why it is equivalent: a break gets the P1-W outcome (`cp2a.py:443-444`) only when its gate ratio is in `not_meaningful`, has no missing operand and has no A6 gate. The break and the stressed ratio use the same operands for every kind: coverage uses `("interest",)`, total leverage `("total_debt",)` and net leverage `("total_debt","cash")` (`:500`, `:517`, `:524` against `:332-334`). The fcf kind has no gate. The s00 row is always built at 0/0 (`:1367`), and with no interest increase I' = I. So s00 marks that ratio `not_applicable` (`:319-321`), and the row clause is already true.

**3. L2: fixed.** `control_cc_only` and `reserved_unstripped` are both killed (exit 1), only by `tests/test_method_cp2a.py:944` `test_round5_names_line_separators_and_padded_reserved_label`.

**4. L3: fixed.** The only code change is `src/deploy_workflow/owners/cp2a.py:643`, `if label.strip() and labels.count(label) > 1`.
- It mirrors the scenario-name guard at `:618` (`sc.name.strip() and ...`).
- Two blank labels now give only their two `empty text` issues. This is tested at `tests/test_method_cp2a.py:959`.
- Two identical padded labels (`" Watch "` twice) are still reported as `thresholds:  Watch  appears more than once`.
- Two tab-only labels give only `empty text`.
- Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2a-fix1-review/probe_padded_duplicate.py`, exit 0.
- `" Watch "` and `"Watch"` are still not counted as duplicates, because labels are compared unstripped. That was already true before this fix and matches the scenario check, so it is not a finding.

**5. Nothing else changes behaviour.** The diff touches 2 files (+89/-1). Apart from line 643, it only adds tests and the test helper `_quarter_base` (`tests/test_method_cp2a.py:881`).

**6. No stub, fake value or catch-all was added.** `_quarter_base` is a test fixture with real operand values. It is not standing in for production behaviour.

### Runner and probes
- Runner `cp2a-r6-review/mutants.py`, re-run through a copy that also prints which tests failed: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2a-fix1-review/mutants_failed_tests.py`, output in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2a-fix1-review/out/`.
  - It exits 1: 12 of 13 mutants are killed. The only survivor is `quarter_line_rows_only`, which is equivalent.
  - Before the fix, 6 survived.
- `cp2a-r6-review/probe_p1w_order.py`: exit 0.
- `cp2a-r6-review/probe_names_edges.py`: exit 0. It now prints only the two `empty text` issues for the blank labels.

### Gates (from the target root, HEAD 88526a1, clean tree)
- pytest `tests/test_method_cp2a.py`: exit 0, 108 passed and 1 skipped.
- `ruff check` on both files: exit 0.
- `ruff format --check` on both files: exit 0.
- `MYPYPATH=src mypy --strict` on both files: exit 0.

Not verified: no mutant or test proves `quarter_line_rows_only` is equivalent; that rests on my reading of the code. A scenario list that leaves out s00 cannot be built from `compute`, and `stress` or `break_points` called directly with mismatched operands were not checked. I did not run any suite other than `tests/test_method_cp2a.py`, and did no rendering or Stage 2 checks.
