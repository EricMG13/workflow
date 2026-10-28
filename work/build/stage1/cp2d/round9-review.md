# CP-2D round 9 scoped review (mx-feature; controller-saved)

Verdict: APPROVE

Findings: none.

1. Item 1 matches the ruling. In `src/deploy_workflow/owners/cp2d.py` (about line 533), the diff deletes only the `DRAWINGS_AVAILABLE` to `DRAWINGS_UNDRAWN` override. The `REV_AVAILABLE` to `REV_RATIO` override is unchanged, and only the comment around it is new. The updated test `test_6f_e_drawings_case_carries_only_the_l1_strings` asserts `T2E.2.r09` reads `Available liquidity not calculable: revolver drawings undisclosed`. It still asserts `T2E.5.r03` is `Not calculable: revolver drawings undisclosed`. The mutant `R9-1 drawings ratio takes the undrawn string again` is KILLED.
2. D-1 is covered by `test_r9_d1_currency_rows_by_kind`. An unstated currency gives `("Facility currency (term-loan)", "Gap")` and the own limitation `Facility term-loan currency is not stated; maturity-wall figures that need it are not calculated.` A stated EUR gives `Limitation`. The commit makes no source change for D-1, so the existing code already satisfies it. Mutants K3 and K4 (kind flipped to Limitation) are KILLED.
3. The tests for L1 to L6 are `test_r9_l1_…`, `test_r9_l2_…`, `test_r9_l3_…`, `test_r9_l4_…`, `test_r9_l5_…` and `test_r9_l6_…`. All the runner mutants are KILLED. I did not map each of L1 to L6 to its own mutant one by one. I read the runner output lines for K1, K2, K9, K10, K11, K11b, K12 to K17, K19, R6 to R11, R13, R14, A1 and R12, plus the 6f-d one. The output also had K3, K4 and K18r. The mutants relevant to the new tests are KILLED:
   - L1 (first facility in wall order): K1, K2, K15, and the 6f-d mutant.
   - L3: K13, R8, R14.
   - L4: K16, K17.
   - L5: K14.
   - L6: K11, K11b, K19.
4. No frozen value changed. The diff is the one deleted override, its comment, and test changes only.
5. There is no stub, fake value or catch-all. The added tests assert exact strings.

Gate and runner results:
- pytest on `tests/test_method_cp2d.py`: 146 passed. The pytest exit code itself was not captured, because `$?` came after a pipe to `tail`. The "146 passed" line is the evidence.
- `ruff check`: exit 0.
- `ruff format --check`: exit 0.
- `mypy --strict` on both files: exit 0.
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/r9_mutate_review.py`: exit 0.
- `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/mutate_r9.py`: exit 0.
- Both runners need an output-directory argument, so I passed `<scratchpad>/copy_<name>`.
- `HEAD` of the target worktree is `e3e1277`.

Not verified: tests beyond `tests/test_method_cp2d.py` (the brief said to run nothing else), including frozen-oracle suites, so "no frozen value changed" rests on diff reading only. I also did not read `round9-report.md`, and the mutant-to-L-test mapping above is inferred from mutant names rather than run mutant by mutant against each test.
