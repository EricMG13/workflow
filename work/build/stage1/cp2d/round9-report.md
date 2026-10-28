# CP-2D round 9 report (controller-saved from the implementer's hand-back)

CP-2D round 9 is committed as **e3e1277** on `worktree-agent-a69f2394899aee6d5`, on top of the merge of `claude/module-dev-status-review-0981b6`. 146 tests pass, all three gates exit 0, and every Low's surviving mutant is now killed.

I skipped `EnterWorktree` because the session was already in this worktree.

**Items and their tests**
- **Item 1** (test written first, red seen): in the drawings-undisclosed case, T2E.2.r09 now carries `Available liquidity not calculable: revolver drawings undisclosed`. I deleted the 6f (e) override and kept the REV_RATIO override that the builder pins. Test: `test_6f_e_drawings_case_carries_only_the_l1_strings`, updated. No frozen value moves.
- **D-1:** the code already matched the Round 9 text and kinds, so nothing changed. A stated non-USD currency gives one `Facility currency (<id>)` row with kind Limitation and FX_LIMITATION. An unstated currency gives one row with the same label, kind Gap, and `Facility <id> currency is not stated; maturity-wall figures that need it are not calculated.` Test: `test_r9_d1_currency_rows_by_kind`.

**Riding Lows L1–L6**
These tests pin behaviour that was already correct, so they passed when written. The red evidence is the reviewer's surviving mutants, all now killed.

| Low | Test | Kills |
|---|---|---|
| L1 | `test_r9_l1_first_facility_in_wall_order_picks_the_mat01_form` (unstated then EUR gives MAT_CURRENCY; EUR then unstated gives MAT_FX) | K1, K2 |
| L2 | `test_r9_l2_amortisation_cause_only_after_the_horizon` | K5 |
| L3 | `test_r9_l3_cash_reason_wins_over_the_drawings_strings` (T2E.2.r07, T2E.5.r03 and T2E.2.r09 all carry the cash reason) | K8, K9, K18r |
| L4 | `test_r9_l4_form4_names_the_first_operand_in_formula_order` | K12, K16, K17 |
| L5 | `test_r9_l5_only_a_known_zero_debt_makes_an_empty_schedule_known` | K14 |
| L6 | `test_r9_l6_wall_date_issue_follows_basis_issue` (exact order: horizon, then basis, then the wall date) | K11, K11b |

For L3 after item 1: the guards on available liquidity and resources still matter, and the ratio now takes the cash reason through `_ratio`, with no override.

**Mutant runs** (all from a full copy of the worktree; files are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/`)
- **`cp2d-r6-review/mutate_review.py`** (reviewer's, unchanged): exit 1. 18 of 18 run are killed; K18 skips because item 1 deleted the line it targets. No mutant survives, and the review called none equivalent.
- **`r9_mutate_review.py`**: the reviewer's runner with K18 re-targeted (restore a drawings override with no cash guard) and K11b added. Exit 0, 20 of 20 killed.
- **`mutate_r6.py`** (unchanged): exit 1. 41 killed; its 6f (e) mutant skips for the same reason as K18.
- **`mutate_r9.py`**: `mutate_r6.py` with that mutant re-targeted (restore the undrawn-string override). Exit 0, 42 of 42 killed.
- **`cp2d-r6-review/probe_untested_paths.py`**: exit 0 on the new code.

**Gates:** `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both files exit 0 on the first run. pytest on `tests/test_method_cp2d.py` gives 146 passed.

**Prose and bare-figure hits:** no new string was added; item 1 reuses DRAWINGS_AVAILABLE. `r5_prose.py` exits 1 on the same 6 non-claim hits accepted under 6f item 3, with 0 claim hits.

Not verified: real CP-1 heads, T4.18 row facts and the A5 reader (Stage 2); L4 "shows both" through T2E.9 (Stage 2); A1's effect on CP-3C; how the T2E.7 Gap rows render; and any test suite other than `tests/test_method_cp2d.py`.

Ledger: `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y`
