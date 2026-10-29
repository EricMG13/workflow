# CP-4C fix round 1 report

M1 is fixed: a source-row claim now reads only the line that starts with its quote, and a quote that names no single line is refused. The Lows and round 10's ASCII cell grammar are applied too. All 170 tests and every gate exit 0, A-1 is unchanged, and every fix's revert is killed. One addition beyond Q1 needs your ruling: a quote that starts two different lines is now refused.

**Commit:** `3b9c3dc81d33330df067cdf278083e035c554c6d`, `fix(cp4c): fix round 1 (cited row, row shape, ASCII cell grammar, CP-1 EBITDA invariant, mutant tests)`. It is on `worktree-agent-a2c15c441717ec41c`. It changes only `src/deploy_workflow/owners/cp4c.py` and `tests/test_method_cp4c.py`.

## Step 0
- `git merge claude/module-dev-status-review-0981b6` was a clean merge with no conflicts. It produced merge commit `25c1a9b`, whose parents are `bdde577` and `6d98bd81a5a93189d83277ec3e8055aef4c94608`. That second parent is the lane tip you named.
- The lane has since moved to `5b64a741`, which another session committed after my merge. I did not merge it.
- After the merge, the tree differs from 6d98bd8 only in my two files. The 9 oracle pins are unchanged, so nothing was re-pinned.

## Findings and their tests
Red runs: 9 tests failed before the fix:
- the 3 M1 tests;
- L1;
- Q4 for `1E+1`, `1_000`, `٥` and `5.`. The other 5 Q4 cells were already refused.
- L2.

The L3 and L4 tests passed against the current code, as expected. Each one is there to kill its mutant.

**M1 / Q1 (the cited row).** `_row_amount` reads the one page line that starts with the quote. If no line starts with it, the claim gets the existing #11 text.
- `test_m1_source_row_reads_the_cited_line_not_the_first_label_match`: with duplicate `Other` rows and the second one quoted, it reads 9, the cited line's value.
- `test_m1_a_quote_no_line_starts_with_is_refused`: `Provisions` against `Other Provisions`.
- `test_m1_a_quote_starting_two_different_lines_is_refused`: this is the addition beyond Q1. A quote such as `Other  9` that starts two different lines names no single row, so it gets the #11 text. Identical duplicate lines count as one. **Please confirm**, or drop it; it uses no new wording.

**L1 / Q2.** `test_l1_a_row_whose_cells_do_not_match_the_header_has_no_number`: a row whose cell count differs from the header's gets #11.

**Round 10 / Q4.** The cell must fully match `-?[0-9]+(\.[0-9]+)?`. This removed the `InvalidOperation` catch and the `is_finite` check.
- `test_q4_a_cell_outside_the_ascii_grammar_has_no_number`, over `(5.00)`, `−5.00`, `1,234.00`, `1E+1`, `1_000`, `٥`, `Infinity`, `NaN` and `5.`.
- `test_q4_a_signed_ascii_cell_is_read`: `-5.00` is read and then refused by #7 with "reads -5".

**L2 / Q3.** `test_l2_known_cp1_ebitda_without_an_amount_is_an_invariant`: a known CP-1 EBITDA with no amount now raises a ValueError invariant.

**L3.** `test_l3_state_14_on_a_payment_over_38_digits`: a 41-digit EV partly paying rank 1 gives state 14. This kills `state_14_claims_only`, which is no longer listed as justified.

**L4.** One test each:
- `test_l4_claims_through_carry_the_first_missing_rank`
- `test_l4_a_rank_carries_its_first_missing_claim`
- `test_l4_a_zero_rank_total_or_negative_claim_is_an_invariant` (2 mutants)
- `test_l4_partial_equity_for_a_zero_recovery_does_not_fit`
- `test_q4_…[Infinity]` (covers `row_amount_infinite_ok`)
- `test_l4_cp2g_ebitda_of_another_period_is_an_invariant`
- `test_l4_a_downside_year_on_another_cp2a_scenario_is_an_invariant`

## Probe exit codes
The probes are in `<S>/cp4c-adversary/`, all run with `PYTHONDONTWRITEBYTECODE=1`. A "finding holds" probe now exiting 1 means the finding is fixed.

| Probe | Exit | What it shows |
|---|---|---|
| `probe_quote_row.py` | 1 | Reproduced 0: the duplicate-label row reads the cited 9, the suffix label is refused, and all five odd cells give None |
| `probe_cp1_known_text.py` | 1 | It stops with a traceback at the new ValueError invariant, which is the fixed behaviour; the probe expected a "missing" reason |
| `probe_state14_paid_mutant.py` | 0 | The mutant is still distinguishable through the public `waterfall()`; it is now killed by the L3 test |
| `probe_survivors.py` | 0 | All 8 checks ok |
| `mutants_adversary.py` | 1 | See below |
| My runner `<S>/cp4c-r6h-8/mutants.py` | 0 | See below |

**`mutants_adversary.py` (exit 1):**
- The baseline passes. All 8 L4 targets are killed.
- The exit 1 comes from two sites the fix removed:
  - `row_amount_infinite_ok`: the `is_finite` check no longer exists; the `Infinity` case is covered by the Q4 test.
  - `cp1_ebitda_known_text_raises`: the code now does what that mutant did. The reverse mutant is in my runner and is killed.
- Four mutants survive, and the review classed all four as equivalent (review table, line 95): `later_block_overrides_reason`, `balance_only_positive`, `fulcrum_unchecked_at_compose`, `recovery_after_allocation`.
- Output: `<S>/cp4c-fix1/mutants_adversary.out`.

**My runner (exit 0):** the baseline passes, 25 are killed and 2 survive with justifications.
- Killed includes `state_14_claims_only` and five revert-the-fix mutants:
  - `revert_m1_first_label_match`
  - `revert_m1_ambiguous_quote_accepted`
  - `revert_l1_short_row_read`
  - `revert_q4_prefix_grammar`
  - `revert_l2_known_without_amount_is_missing`
- The 2 justified survivors are the same as before, and the review agrees they are equivalent:
  - `exact_sum_without_80_floor`: the computed precision always holds the sum.
  - `no_balance_invariant`: the balance is 0 by construction.
- Output: `<S>/cp4c-fix1/mutants_implementer.out`.

## Gates
All on both files:

| Gate | Exit |
|---|---|
| pytest: 170 passed in 1.89s, hypothesis properties included | 0 |
| `ruff check` | 0 |
| `ruff format --check` | 0 |
| `MYPYPATH=src mypy --strict` | 0 |

Nothing else was run.

Not verified: the lane commits after 6d98bd8 (5b64a741) were not merged or tested; B1–B6 are left with LEAD as the brief says, including the builder `row_cells` sync for Q1 and Q2; the ambiguous-quote refusal is my addition beyond Q1 and needs your confirmation; the full repo suite and Stage 2 quote matching were not run.

agent=general-purpose(opus) fix-rounds=1 gates-first-pass=n
