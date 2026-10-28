CP-8 round 13 items 7 and 8 are done and committed as 0de521a on claude/r13-cp8. It sits on the merge commit 7f71516 (claude/r13-cp3d into bb0190e). Only `src/deploy_workflow/owners/cp8.py` and `tests/test_method_cp8.py` changed.

**Step 0:** the worktree was clean at bb0190e and the merge of claude/r13-cp3d was clean. `tests/test_method_cp8.py` was fully green after the merge (596 passed), so no library case was red.

**Check B3:** the library cases `w-minus-wrap-text` and all eight `b3-*` cases pass through CP-8's readers on all four text fields, so none failed. The existing exemption (f99db43 with the index-0 guard) already covers them, and I changed nothing there. The library has no comma cases.

**Item 7 (`_labelled` run rule)**
- After the label, the code scans numeral runs `\.?[0-9](?:[0-9]|[.,][0-9])*` up to the `_MULTIPLE`/`_DECIMAL` match. If a run starts before the match and does not fullmatch `[0-9]+(?:\.[0-9]+)?`, the value is not labelled.
- Plain integer runs are still skipped, and the join is on `,<digit>` only.
- Tests: `test_r13_labelled_a_malformed_run_after_the_label_ends_the_search` covers `.75`, `-.75`, `(.75)`, `1.2.5`, `1,250` and `1,250.50`. Where the figure has the N.NN shape, end to end the only issue is the pinned `observations[6]: loan_bid value_text 0.50 is not labelled loan_bid in the quote`.
- The other r13 tests for this item are `test_r13_labelled_a_plain_integer_run_is_still_skipped` (including the `April 29, 2026` date twin), `test_r13_labelled_joins_only_on_comma_digit` and `test_r13_labelled_the_run_rule_holds_for_a_multiple`.

**Item 8 (`_whole`)**
- Added lookbehinds `(?<![0-9],)(?<![0-9], )` and the trailing guard `(?![0-9]|[.,][0-9]|, [0-9])`. `_on_page` uses the same pattern, so the page edge is covered.
- Tests:
  - `test_r13_whole_no_figure_reads_from_a_thousands_comma_run` covers `1,25`, `1, 25` and `1,\n25`.
  - `test_r13_whole_comma_twins_still_read` covers `25, a`, `up, 25`, `up,\n25` and `2025, then 25`.
  - `test_r13_whole_the_page_edge_reads_the_comma_run` covers the page edge.
  - `test_r13_a_comma_run_in_the_quote_or_at_the_page_edge_is_no_figure` is end to end on the size level, with value 1.25 because the field's shape rule refuses shorter figures.

**Red first:** the r13 tests were run before the fix, with 17 red and 8 green. The green ones are twins, plus `1.2.5` and the multiple `1.2.5x`, which the old code already refused. After the fix all pass.

**Mutants:** eight mutants, one per ruled clause, each applied to a full temporary copy with `PYTHONDONTWRITEBYTECODE=1`. All eight were killed (script exit 0). The mutants, in `<S>/cp8-r13/mutants.py`:
- run rule dropped
- plain integers not skipped
- `_labelled` joining `, ?`
- leading point not a run
- no `(?<![0-9],)` lookbehind
- no `(?<![0-9], )` lookbehind
- trailing `[.,][0-9]` weakened to `\.[0-9]`
- trailing `, [0-9]` removed

**Probes** (copied to `<S>/cp8-r13/`, LANE pointed at r13-cp8):
- `p13_cp8_labelled_e2e.py` exits 0 (it was 1 on old code), and both cases are now refused with the not-labelled issue.
- `p13_quote_classes.py` exits 1 and `p13_comma_space_join.py` exits 1. Both are expected, and the red lines do not come from CP-8:
  - The `F` lines compare the lane to the pre-change reference, so they assume the old code. This covers CP-8's thousands, decimal-comma and `_labelled` lines, and the CP-3D lines that moved with the r13-cp3d merge.
  - The control list and control year comma are refused under item 8's comma-space join, which is the ruled cost.
  - The CP-1D `-0.25` line and the CP-2E lines are not mine; CP-1D and CP-2E are not changed in this worktree.
  - `p13_comma_space_join.py` fails on "a frozen moved". That comes from its `, ?` variant moving 279 labelled checks. The narrowed `,<digit>`-only variant prints "moved 0", and 0 of the frozen triples move (CP-2E 15, CP-3D 15, CP-8 40, CP-1D 4).
- I also ran a copy of `p13_quote_classes.py` with the CP-8 comparison pointed at the rule model, as `p13_quote_classes_vs_rule.py` in the same folder. Every CP-8 `F` line left was a comma-space control, so CP-8 matches the rule model apart from item 8's ruled comma-space cost. The 563 frozen labelled checks are unchanged, and the frozen cases all pass.

**Gates** (all exit 0):
- pytest on `tests/test_method_cp8.py`, `tests/test_defect_classes_selfcheck.py` and `tests/test_host_h1.py`: 880 passed.
- `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both files.

Not verified: the `methods/cp8.md` guard-limit notes (not my file; the controller records them), the comma-space cost on frozen refusal mutations (CP-8's frozen refusal tests pass, but I did not run LEAD's `p13_refusal_mutations.py`), the other three readers (CP-1D, CP-2E, CP-3D), and any behaviour on unfrozen real-world quotes. There is no `tests/test_host_h1.py` change to cover; it passes as it stood.

Ledger: agent=mx-feature fix-rounds=0 gates-first-pass=y