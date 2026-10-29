CP-8 round 12 fix 1 is done in commit f99db43 on worktree-agent-a3cc9818386e8861a, with the Co-Authored-By line. It follows LEAD's ruling, not the controller decision.

Step 0: the worktree was clean and HEAD was 8cecd09.

I had removed the exemption before your message arrived. I reverted that with `git checkout -- src tests` and restarted from 8cecd09, so none of the removal is in the commit.

**Files changed:** only `src/deploy_workflow/owners/cp8.py` and `tests/test_method_cp8.py`.

**Steps**
1. **Tests first, red on 8cecd09.** I added `test_r12_w_a_wrap_at_the_value_edge_or_off_a_figure_is_b3_refused`, run on instrument, flag span and size span.
   - The reviewer's two rows, `- 1.25 notes` (page `…A-\n1.25 notes.`) and `- 2025 notes` (page `…2024-\n2025 notes.`), failed 6 of 6 on 8cecd09. Each is pinned to its B3 issue.
   - The two LEAD refusal rows, `A- 25 notes` and `a - b notes`, passed already on 8cecd09, so they are not red-then-green.
   - I also added `test_r12_w_a_minus_wrap_inside_the_value_is_accepted`, which takes `is - 1.25 notes` on a page with `is -\n1.25 notes`.
2. **Fix.** In cp8.py, `_W_MINUS` became `(?<=.){_SIGN} (?=[0-9])`. The exemption now needs a character of the value before the `- `, so a `- ` at value index 0 stays a wrap split and fails closed. It still uses CP-8's `_SIGN` and nothing broader.
3. **Kept** `test_r12_w_a_wrapped_minus_is_not_a_wrap_split`. It passes unchanged.
4. **LEAD's three cases.**
   - Accepted and signed: `is -\n1.25`. I covered it with the `is - 1.25 notes` value in the accepted test above, on all three fields.
   - B3-refused: `A-\n25`, as `A- 25 notes`, and `a - b`, as `a - b notes`. These are in the refused test.
   - I did not edit `tests/defect_classes.py`.

**Probes.** These ran on a fresh `git archive HEAD` copy with PYTHONDONTWRITEBYTECODE=1. The scripts are in `<S>/cp8-r12-fix1/`.
- `<S>/cp8-r12-fix1/p_wrap_split_edge.py` exits 0, with all 4 rows refused by B3. I copied the script unchanged, since it hardcodes no `R/copy` path.
- `<S>/cp8-r12-fix1/mutate.py` exits 0. The unmutated copy passes, and all 10 mutants are killed. I kept the `_wrap_split` mutant and added "W minus exemption at value index 0 (guard dropped)", which is also killed.

**Gates**
- pytest on `tests/test_method_cp8.py`, `tests/test_defect_classes_selfcheck.py` and `tests/test_host_h1.py`: 802 passed, exit 0. The frozen cases are included.
- `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both files: all exit 0.

Not verified: the full suite and CI; GitNexus impact; the `methods/cp8.md` note; text fields other than instrument, flag span and size span (same code path, not run); chained `- - 1` values; the library case `w-minus-wrap-1.25` on the size level, which still passes unchanged with the exemption restored.

agent=mx-feature fix-rounds=1 gates-first-pass=y