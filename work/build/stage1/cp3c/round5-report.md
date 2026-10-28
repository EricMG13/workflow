# CP-3C rulings round 5 report (controller-saved)

- **Commit:** `196b174` on `worktree-agent-aa5a4817fa00cd287`, on top of merge e215c1d (lane f02637c). The diff is +983/−300.
- **Re-pinned in `PINS`:** manifest d5ca731c… and builder b461d897…. No oracle edits.
- **Tests:** 129 passed. Every ruling test was seen failing (RED) first.
- **Gates:** ruff check, ruff format --check and `mypy --strict` all exit 0. mypy failed on the first run with 4 errors.
- **Design:** a value that is not calculated is now `Gap(reason, applicable)`, where the reason is the first missing operand in formula order. There is also an `UnmatchedFacility` list. The old `NOT_APPLICABLE`/`Ratio` types are removed.

## Rulings and their tests
- **C-1:** four `test_c1_cost_claim_*` tests.
- **C-2:** `test_c2_*`. They cover:
  - amortisation;
  - minimum cash before amortisation;
  - the first missing operand;
  - run-rate;
  - EBITDA and interest;
  - not-meaningful states;
  - ranking.
- **C-3:** `test_c3_need_claim_*`, `test_c3_lme_claim_names_the_unstated_ranking` and `test_c3_burden_claim_with_non_positive_ebitda`.
- **C-4:** `test_c4_facilities_order_by_maturity_date_not_months`, plus two order tests.
- **C-5:** a Stage 2 note.
- **C-6:** `test_c6_*`. They cover:
  - non-USD;
  - an empty register;
  - zero principal;
  - the unknown-flag invariant;
  - a wall row off CP-2D's rule;
  - unmatched facilities.
- **C-7:** `test_c7_a_gap_copy_keeps_the_upstream_class_period_and_reason`. This test caught a real defect: gap copies dropped the upstream period. It is fixed.
- **C-8:** `test_c8_a_repeated_issue_is_reported_each_time`.
- **Precedence:** five tests, including `test_unruled_claim_slots_take_the_chip_form`.

## Probes (scratchpad)
- `mutate.py` exits 0. It applies 15 hand mutants in place, then restores the file by sha. All 15 are killed after one extra assertion was added.
- `prose_probe.py` exits 0.
- `bare_figures` gives no hits. `prose.issues` reports only "Figure reference has no citation or calculation" on figure slots, because Stage 1 cells carry no citations.

## For LEAD: choices beyond the rulings
1. **Claim forms for unnamed causes.**
   - Every slot takes the figure-or-chip form: HORIZON-01 r04, BURDEN-01 r08/r09 (missing EBITDA, or unstated amortisation), and COST-01 r06.
   - The NEED-01 and LME-01 cause is the reason without "Not calculable: ". This form extends to FX, no facility, and "is not in the".
   - The LME-01 FX form stacks semicolons.
2. **T3D.8 labels and kinds**, mirrored from CP-2D D-1. They sit after the fixed tail and before the path lines.
   - "Facility currency (<id>)": Limitation
   - "Facility schedule": Gap
   - "CP-2D maturity wall cross-check (<id>)": Limitation
   - "Facility register and wall (<id>)": Gap
3. **The unmatched-facility own line** uses the reason verbatim. A facility missing from the register is labelled by its id.
4. **Precedence.**
   - An unmatched facility counts as unranked.
   - An unranked row names its own facility first.
   - An empty register overrides everything else.
   - Amortisation comes before FX.
   - A pro forma cover that is not meaningful uses the cash-interest reason.
   - The FX reason prints the run currency.
5. **Still raising "(not pinned)":**
   - a USD facility whose wall principal is missing;
   - a missing maturity date, months, inside flag, horizon or name;
   - a negative total principal;
   - a T4.18 principal with no currency.
6. **"Shows both" on a wall disagreement:** the T3D.1 copies show CP-2D's values, and the composer uses the recomputed ones. This is a Stage 2 issue, like CP-2D L4.
7. **Builder syncs:** none.

## Next round
After LEAD's oracle batch, the next round applies:
- round 6 A1: the largest-n months, so 30 months, superseding lease :218;
- A5: currency and name from the T4.18 text facts;
- the oracle-batch re-pin;
- LEAD's answers to the points above.

The first mx-adversary review follows that round.

## Stage 2 notes
- `methods/cp3c.md`: the C-4 headers and the C-5 trace locator.
- C-7: the currency binding.

Not verified:
- Stage 2 binding;
- `prose.issues` with citations;
- "shows both";
- `cites_from` for unmatched facilities;
- the full suite;
- mutmut;
- the size: the branch is past the 800-line PR cap. That is for the whole-branch review.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n
