# CP-8 rulings round 5 report (controller-saved)

- **Commit:** `63237ad` on `worktree-agent-a3cc9818386e8861a`, on top of the lane merge ad4c3a6 (f02637c). No methodology re-pin was needed.
- **Tests:** 125 passed. Every ruling test was seen failing at the cited raise or on the old wording before the fix.
- **Gates:** ruff check, ruff format --check and `mypy --strict` all exit 0. None passed on the first run (ISC004, format, a typing error).

## Rulings → tests
| Ruling | Tests |
|---|---|
| 8-1 | `test_8_1_partial_outcome_settles`, `test_8_1_two_measures_not_compared` |
| 8-2 | `test_8_2_missing_expected_settles`. Under `outcome_absence` it still fails closed (`test_8_2_missing_expected_under_outcome_absence_still_fails_closed`, see LEAD item 2) |
| 8-3 | `test_8_3_unchanged_measure_claim` |
| 8-4 | `test_8_4_overall_process_judged_unsound` |
| 8-5 | `test_8_5_compared_measure_without_a_recorded_size` |
| 8-6 | `test_8_6_partly_unrecorded_fields` |
| 8-7 | `test_8_7_bid_and_offer_dated_differently`; `test_derive_property` (hypothesis, 300 examples) |
| 8-8 | Kept as an invariant, unreachable, no test |
| 8-9 | `test_8_9_prior_case_authority_from_cp0` |
| 8-10 | `test_8_10_text_without_its_quote`, `test_8_10_quote_beside_an_absence` |
| 8-11 | `test_8_11_repeated_confidence` |
| 8-12 | `test_8_12_no_cp0_authority_is_an_invariant` |
| 8-13, 8-14 | Confirmations that pass unchanged |
| 8-16 | `test_8_16_prohibited_phrases_match_at_word_start` |
| 8-17 | `test_8_17_exit_trigger_absent`, `test_8_17_exit_trigger_stating_a_figure` |
| 8-20 | `test_8_20_cp6_states_insufficient_information` |

Raises that became invariants (unreachable after validation):
- the T7.3 default and window rows without `outcome_absence`;
- a known mid with two dates;
- a breach decision without a recorded size;
- the `_PROCESS_SAID` raise.

`LedgerInputs` gains `expected_as_of`.

## Probes (scratchpad)
- `cp8-r5/probe_prose.py` exits 1 on one hit, described below.
- `cp8-r5/mutate_r5.py` exits 0: 16 of 16 mutants killed.
- `cp8_mutate.py` exits 0: 2 of 2 killed.

## Prose and bare figures
- The 8-3 rails line "Total leverage was recorded at 1.67x and is now 1.67x, unchanged." gives `Bare figure: 1.67x`.
- The frozen pinned rails line hits the same way, because rails text is Python-resolved by design.
- The 8-3 claim itself is clean.

## Stage 2 notes (`methods/cp8.md`)
- **8-15:** defines "first figure".
- **8-16:** guard limit: matching at word start still catches "buyer" and "seller", and "calibrat" matches anywhere.

## For LEAD
1. 8-14: the builder sync is optional and not done.
2. Unruled points that still fail closed:
   - a T7.4 evidence cell with no cited quote. This happens when there is no expected value under `outcome_absence`, or neither value without it.
   - the T7.8 follow-up when both values are missing. It is unreachable while the case above fails first.
3. Interpretations, which the controller confirmed (see the ledger):
   - (a) the T7.3 bid and offer rows use the mid's `<name>`;
   - (b) 8-7 adds no T7.8 `not_compared_loan_mid` row, but does add the "Measures not compared" limitation;
   - (c) the 8-7 reason lists the bid date, then the offer date;
   - (d) under `outcome_absence`, only expected-side 8-1 rows are added;
   - (e) the 8-20 limitation takes LIM_NO_CP6's last position;
   - (f) "digit" is tested with `str.isdigit`.

Not verified:
- no frozen case exercises any round 5 state, so the expected strings come from the ruling text alone;
- 8-8 is untested;
- the Stage 2 and Stage 4 sections;
- the command was run with pyproject `pythonpath` rather than `PYTHONPATH=src`.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n
