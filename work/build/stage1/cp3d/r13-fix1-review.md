**CP-3D round 13 fix1 scoped re-review (543376c, diff a212da3..543376c). Verdict: APPROVE. M1 is closed. No High or Medium findings, one Low.**

**Spec: M1 is closed.**
- `<S>/cp3d-r13-review/p_comma_edge.py` exit 0. All six M1 cases are now refused, and the `.` control is still refused.
- `<S>/cp3d-r13-review/p_fuzz_join.py` exit 0, with 0 violations (`{'comma_edge': 0, 'other': 0}`, 300k pages). The earlier review found 6,217 violations.

**Nothing broader opens and no edge is lost.** Probe: `<S>/cp3d-r13-fix1-review/p_diff_old_new.py`, exit 0. It loads a212da3 and 543376c side by side and runs `quoted` + `_token_once` + `_whole_on_page` on both.
- **Fixed cases: 20 of 20 as expected.** Results are the same as a212da3 except the two M1 cases (`, 250 per` on `1, 250`, and `fee of 1,` on `1,\n250`), which are now refused.
  - Index-0 start edge: `25 bps` is still accepted on `margin 25 bps` and still refused on `125`, `1.25` and `1,25`/`1, 25`.
  - W and minus starts: `-25`, `- 25` and U+2212 `25` are still refused. `A-25` and `95-25` are still accepted.
  - Accounting `(25)` and `( 25 )` are still refused.
  - Letter-after-comma twins are still accepted: `fee of 1,` on `1, payable` and on `1,a`, and `,250`/`, 250` after `up`.
- **Differential fuzz: 200k pages, 2,690 outcome changes.** Every change makes the result stricter (0 looser). Every one has the quote's prefix before the figure in {`,`, `, `} or a trailing `,` after it (0 outside that class).
- This matches the code. The fix only turns `at_start`/`at_end` true in more cases, which can only add refusals.

**Mutants and frozen data.**
- `<S>/cp3d-r13/mutants.py` exit 0: 18 of 18 killed, including the 4 new edge mutants and `delta-table-emptied`.
- The test diff only adds `test_r13_m1_a_quote_edge_at_a_comma_beside_the_figure_is_an_edge` (`tests/test_method_cp3d.py:1897-1927`, 6 refused cases and 2 accepted twins).
- `STAGE2_REFUSAL_DELTA` (:232) is unchanged and still holds only `amortisation_nonzero`. The frozen-triple and refusal-mutation tests are unchanged and pass in the gate.

**Quality.**
- **Low:** the `_whole_on_page` docstring is out of date at `src/deploy_workflow/owners/cp3d.py:258` and `:260-261`. It still says "The start edge is nothing before the figure" and "The end edge is nothing or only `.`". It should name `_EDGE_BEFORE` and the comma. This can ride with the end-of-branch Low batch.
- No stub, fake value or catch-all in the diff.

**Exit codes.** All ran from fresh `git archive` copies with PYTHONDONTWRITEBYTECODE=1: 543376c at `<S>/cp3d-r13-fix1-review/copy` and a212da3 at `<S>/cp3d-r13-fix1-review/old`.

| Check | Exit | Result |
|---|---|---|
| Gate pytest (`test_method_cp3d.py` + `test_defect_classes_selfcheck.py`) | 0 | 1091 passed |
| `p_comma_edge.py` | 0 | M1 cases refused |
| `p_fuzz_join.py` | 0 | 0 violations |
| `mutants.py` | 0 | 18 of 18 killed |
| `p_diff_old_new.py` | 0 | 20/20 fixed cases; 0 looser, 0 out of class |

Outputs are saved as `.out` files next to each probe in `<S>/cp3d-r13-fix1-review/`.

`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`

Not verified: I did not re-run ruff, mypy, the full suite, CP-8, CP-2E or CP-1D. I did not check whether the other owners (CP-8, CP-2E, CP-1D) now agree on comma edges. I did not drive the fix through `submission_issues` on a full frozen-shape submission. I did not run GitNexus `impact` or `detect_changes`. The differential fuzz used a random substring of the plain normalised page as the quote, so quotes that exist only in the joined wrap reading were covered only by `p_fuzz_join.py`.