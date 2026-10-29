# CP-4C round 8 Part A report (controller-saved from the implementer's hand-back)

# CP-4C report: round 8 Part A, with its re-pin addendum (the controller saves this as work/build/stage1/cp4c/report.md)

Round 8 Part A is applied and committed. 148 tests pass, every gate exits 0, and the hand mutation of the allocation code ended with 19 mutants killed and 3 justified as equivalent. **One thing outside my two files:** the lane merge conflicted on `docs/CP4C-OWNER-LEASE.md`, and I resolved it by taking the lane's file unchanged.

**Commit:** `bdde577281e99c7c5efd1c161aaea6f8f72223b5`, `fix(cp4c): round 8 Part A (A-1 exact allocation, A-2 states, A-4 conflicting copies)`, with the Co-Authored-By line. It is on branch `worktree-agent-a2c15c441717ec41c`, on top of merge `c04946f` of lane `claude/module-dev-status-review-0981b6` (93fa796). The diff touches only `src/deploy_workflow/owners/cp4c.py` and `tests/test_method_cp4c.py`.

## Step 0 and the re-pin addendum
- **EnterWorktree:** it refused because the session is already in this worktree, so nothing changed.
- **The conflict:** the lane adds the round 8 A-1 header above the round 6 header, which my branch already had from cherry-picking 3674158. Git conflicted there. I took the lane's side; it is byte-identical to the lane (`git diff --quiet <lane> -- docs/CP4C-OWNER-LEASE.md` exit 0). After the merge, the tree equals the lane plus my two files.
- **Re-pin:** after the merge, no sha my test pins moved, and the round 8 header says nothing is re-pinned. I checked each one with `shasum -a 256`:

| File | sha256 |
|---|---|
| `cases/cp4c-owner/manifest.json` | `9cf100831af87c3972656a858588b50a3b77ac30422bd17664b82e1740592a93` |
| `cases/cp4c-owner/submissions.json` | `1f76a1d193e04db56a2917b30a4cdc470be54a259858a2c8712e0e4bf1feea68` |
| `cases/cp4c-owner/expected.json` | `61ddb316372469ce74920147423000a2f4ee846fc9c9f94a9f58f990d9ad9fcc` |
| `cases/cp4c-owner/builder/build.py` | `806252b5d3913ad4cfcedcd024f0c89cace83958ec96c989212202b30e30762f` |
| `cases/cp2g-owner/expected.json` | `97328745be246b3bf67fe5840f291afb3da3cbae99b51db1ba7bd24d2eef406c` |
| `cases/cp2a-owner/expected.json` | `ad5531da7cff4eca8e9c8e9a23cef6526a982537597e6830610877bec994ff89` |
| `cases/cp4-owner/expected.json` | `154fc2d09a4c8a06232a489e5a047e947ee098507969e5e11cdb1ca7f6f4f6a0` |
| `cases/financial/manifest.json` | `6b3eeffe0871923f9f3ed9b6fd6739c86be2ee4dd8a7d35e8a6a516581b93432` |
| `cases/legal/manifest.json` | `d6a8ec15285dbe16a6e2ff3f167c26a295b675decfb4df7231901b0243305168` |

## Each ruling and its test
I wrote the tests first. The red run gave **23 failed, 125 passed**, each failing on the cited raise or the old result: the CP-3C, T4.18, EBITDA and total-debt raises, `Inexact` escaping, the 38-digit shares, and so on. I added three test extensions after the code was green, so they never had a red run; the mutation run shows each one kills its mutant:
- the state 13 cases for "claims through" and "value left";
- the 92-digit exact sum;
- the EV-0 unpaid case, which replaced my first unpaid case because that one tripped state 13.

**A-1 (exact largest-remainder allocation):**
- `test_a1_worked_example_three_equal_classes_share_100` gives 33.33…333 / 33.33…333 / 33.33…334.
- `test_a1_leftover_unit_goes_to_the_largest_remainder`.
- `test_a1_fully_paid_rank_pays_each_claim_exactly`.
- `test_a1_unpaid_rank_pays_zero`.
- `test_a1_state_14_claim_not_a_multiple_of_the_rank_quantum`: state 14 raises a ValueError.
- `test_a1_exact_sum_is_never_rounded`.
- `test_a1_t4e9_balances_exactly_with_three_equal_classes`: this replaces the old `test_unconserved_waterfall_fails_closed`. The balance is now exactly 0 and the raise is an invariant.
- `test_property_conservation` (hypothesis, 400 examples, ties and 7-decimal claims) checks:
  - each rank sums to `paid` exactly;
  - every share is the floor or the floor plus q, within q of its exact value, between 0 and its claim;
  - the leftover count, and that the units go to the largest remainders with ties to the later class;
  - full and zero payments are exact;
  - shortfall and recovery are rounded at 38 digits;
  - Σ distributions + residual = EV exactly.
- The frozen v02 values (3.7466666666666666666666666666666666667 and 1.8733333333333333333333333333333333333) are unchanged, via `test_facts[positive]` and `test_waterfall_summary[positive]`.

**A-2 (the 13 states):**

| # | Test |
|---|---|
| 1 | `test_a2_1_bound_cp3c_shows_its_input_status` (only `T4E.1.u_cp3c.status` changes, and the own lines are unchanged) |
| 2 | `test_a2_2_term_loan_not_secured_senior_is_a_validator_issue` (UNSECURED, SUBORDINATED and a missing status, plus the order after v02) |
| 3 | `test_a2_3_other_period_column_is_a_validator_issue` (v05 still comes first) |
| 4 | `test_a2_4_other_cp4_rating_or_conditions_stays_fail_closed`: the message now cites "round 8 A-2 #4" with no "LEAD to". The existing `test_lender_protection_other_than_insufficient_fails_closed` also still covers it. |
| 5 | `test_a2_5_cp1_ebitda_not_a_known_positive[missing, conflicting, zero, negative]`: only the three implied-multiple cells change, and no own line is added |
| 6 | `test_a2_6_conflicting_total_debt_is_a_missing_claim`: the output equals the fixture_debt_missing oracle with "missing" reworded to "conflicting", and the reference row keeps `conflicting` with CP-1's limitation. Also `test_a2_6_total_debt_of_another_period_stays_an_invariant`. |
| 7 | `test_a2_7_negative_cp2g_ebitda_makes_the_enterprise_value_missing`, `test_a2_7_claim_not_above_zero_is_a_validator_issue` (a source row and CP-1 total debt), `test_negative_enterprise_value_stays_an_invariant` |
| 8 | Covered by A-1: the balance is an explicit `raise AssertionError`, so it holds under `-O` |
| 9 | `test_a2_9_blank_or_multiline_names_are_text_issues`: the issues come in the per-field step, after HIGH |
| 10, 12 | Invariant raises, unchanged; no new test |
| 11 | `test_a2_11_quoted_row_without_a_number_is_a_validator_issue` |
| 13 | `test_a2_13_more_than_38_digits_is_a_value_error_naming_the_operation`: the rank total, claims through, value left and the v01 enterprise value |

**A-3:** no change, and CP-2G is untouched.

**A-4:**
- `_copy_status` now accepts `conflicting`, and `_valuation` takes the upstream limitation for any unsettled CP-2G EBITDA: `test_a4_conflicting_copies_keep_their_status` (only the two T4E.3 ebitda copies change status).
- T4E.1 showing the bound status is confirmed by the A-2 #1 test.

**A-5:** the masking `_RATIO` sum is gone; T4E.9 now uses `_exact_sum`.

## Probes
Both are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-r6h-8/`:
- **`probe_prose.py`: exit 0.** It runs the new strings through `prose.issues` and `bare_figures`; the hits are below.
- **`mutants.py`: exit 0.** It copies src, cases, the test and `pyproject.toml` into a temporary tree and mutates only the copy, using `pytest -x --hypothesis-seed=0`. The baseline passed (rc 0), and there are 22 mutants.
  - **19 killed:** tie to the earlier class, smallest remainder first, no leftover units, ceil, round, quantum digit ±1 (×2), no state 14, no full-payment branch, no zero-payment branch, leftover off by one, one division per share, shares to the wrong classes, exact sum in the rounding context, exact sum without carry digits, canonical form capped at 80 digits, T4E.9 summed at 38 digits, balance adds the residual, value left rounds. Each kill names its test.
  - **3 survive, justified as equivalent:**
    - `state_14_claims_only`: `paid` always has 38 digits or fewer, so it is a multiple of its own quantum.
    - `exact_sum_without_80_floor`: the computed precision always holds the sum.
    - `no_balance_invariant`: the balance is 0 by construction; two other mutants test it independently.

## Gates
All on both files, run with the `.venv` bin:

| Gate | Exit |
|---|---|
| `ruff check` | 0 |
| `ruff format --check` | 0 |
| `MYPYPATH=src mypy --strict` | 0 |
| pytest: **148 passed in 1.90s** | 0 |

## Prose and bare-figure hits (reported, not reworded)
- **Validator issues** (#2, #3, #7, #9, #11): the path tokens read as "Unresolved reference: N" or bare figures (`claims[0].kind`, `T4.18`, `0`). They sit outside the claim prose check (6f item 3), like the pinned v01–v14 issues.
- **#5 and #6 reasons and the #6 own line:** "Bare figure: 25" from the pinned CP-1 frame "LTM Q4 25: …". This is the same frame as the already-pinned total-debt-missing reason. Cell limitations and own lines sit outside the claim prose check.
- **#7 negative-EBITDA reason and own line:** no hits.

## Choices for LEAD to confirm
- **Implied multiple:** when EV and CP-1 EBITDA are both unknown, EV's reason wins. This follows the numerator-first order of T4E.6/T4E.7. CP-1 EBITDA `not_applicable` takes the "missing" reason.
- **#7:**
  - `<amount>` is spelled in canonical exact form ("0", "-3.5").
  - For the secured class (CP-1 total debt ≤ 0), the issue sits after its #2 check, since #3 doesn't apply to that class.
  - A negative EV means a product below 0: negative EBITDA × 0 gives a known 0, and with "not assessed" the reason is R_EV_NA.
- **Source-row order:** v05 → #3 → #11 → #7, each only when the one before passes.
- **#2:** it is raised for every class whose kind is secured_debt.
- **#9:**
  - Names and labels get only the empty and one-line checks; neither the guard nor prose is applied.
  - They sit before the field's rationale, in schema order.
  - "One line" means `splitlines() == [text]`.
- **CP-1 total debt `not_applicable`:** still a fail-closed ValueError, because A-2 #6 words only missing and conflicting.
- **Latent bug fixed:** `_exact` normalized at a fixed 80 digits, which would silently round longer values. It now uses `max(80, digits)`; no frozen value was affected.

## Stage 2 notes (not written now)
- `methods/cp4c.md` should record:
  - the A-1 allocation rule and the A-1 #6 note that claim = distribution + shortfall is not an invariant;
  - that T4E.1 shows the bound Input status (A-4).
- A-2 #4 (another CP-4 rating or conditions) is a Stage 2 lease item.
- LEAD's builder sync: the `waterfall_rules.recipe` text at the next CP-4C oracle batch.

Not verified: the A-2 #10 and #12 invariant raises have no new tests, since their behaviour is unchanged; the full repo suite and the other modules' tests after the lane merge were not run (only my test was run, as the brief says); Stage 2 readers of the new issue strings; and the three test extensions added after green had no red run, only the mutation run.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n

## Controller rulings on the choices (2026-10-28, before the first review)
- Confirmed: implied multiple takes EV's reason first (numerator-first, as T4E.6/T4E.7); #7 canonical amount form, secured-class position, and negative-EV reading; source-row order v05, #3, #11, #7; #2 for every secured_debt class; #9 names and labels get the empty and one-line checks only, before the rationale, `splitlines() == [text]`; the `_exact` 80-digit fix.
- To LEAD: CP-1 total debt `not_applicable` stays a fail-closed ValueError (A-2 #6 words only missing and conflicting).
