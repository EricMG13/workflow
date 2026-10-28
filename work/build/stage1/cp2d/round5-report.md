# CP-2D rulings round 5 report (controller-saved)

- **Commit:** `b8a5751` on `worktree-agent-a69f2394899aee6d5`, on top of the lane merge f0e4a6d.
- **Tests:** 124 passed. The layer reviewer's pin test still passes unchanged.
- **Gates:** all three exit 0. The first run failed (ISC004 and a mypy error), so this is not a first-pass green.
- **Re-pinned for behaviour that moved:**
  - the empty-schedule reason (now SCHEDULE_EMPTY);
  - the MAT-01 FX text (L5);
  - `submission_issues` and `Cp2dInputs`, which now take `maturity_date_refs` (D-5).

## Rulings and their tests (each red first)
- **D-1:**
  - `test_d1_facility_term_rows_are_gaps`
  - `test_d1_d3_empty_schedule_row_and_reason`
- **D-2:** GAP_MISSING `({reason})` is removed.
  - `test_d2_l5_gap01_facility_forms`
  - `test_d2_facility_causes_in_the_ruled_order`
  - `test_d2_facility_cause_beats_a_missing_operand`
  - `test_d2_missing_operand_form`
  - `test_d2_missing_operand_beats_the_revolver_form`
  - `test_d2_schedule_form_carries_no_bare_figure`
- **D-3:**
  - `test_d3_term_reasons_use_the_not_stated_frame`
  - `test_d3_empty_schedule_with_zero_total_debt_is_known_zero`
  - `test_d3_absent_schedule_keeps_schedule_missing`
- **D-4:** `test_d4_negative_total_debt_reason`
- **D-5:** `test_d5_wall_assessment_must_cite_the_maturity_date`. Every frozen payload still passes.
- **D-6:** no change.
- **L1:** `test_l1_commitment_known_drawings_missing`
- **L3:**
  - `test_l3_differences_are_spelled_exactly`
  - `test_l3_difference_is_not_rounded_to_the_default_context`
- **L5:** covered by the D-2 forms test and the MAT-01 test.

**Defect fixed by confidence review (L3).** `exact_amount_text` used `Decimal.normalize()`, which rounds to 28 digits. It now strips trailing zeros from the exact `format(..., "f")` text instead. The failing test landed with the fix.

## Probes (scratchpad)
| Probe | Exit | Note |
|---|---|---|
| `probes/probe1-3.py` | 1 each | TypeError: they call the old `submission_issues` signature |
| `probes/r5_probe1-3.py` | 0 each | The same probes with the new argument |
| `probes/mutate.py` | 0 | M2–M9 match the source and all are killed; 13 patterns are stale and skip |
| `mutate_r5.py` | 0 | 39 of 39 killed |
| `probes/r5_probe_sweep.py` | 0 | No raise in 6000 valid inputs |
| `r5_confidence.py` | 0 | |
| `r5_prose.py` | 1 | 6 hits, see below |

## Prose and bare figures
- Claims: 0 hits.
- `bare_figures` hits fall only in ruled or pinned non-claim text:
  - `0.25` and `(0.4)`: the L3 differences;
  - `T4.18`: the D-3 own line and reason, SCHEDULE_MISSING, and the D-5 issue.

## For LEAD
- **New wording (not ruled):** the GAP-01 form-4 schedule labels.
  - "the facility schedule" when the schedule is absent.
  - "a facility in the facility schedule" when it is empty.
- **Readings:**
  - Form 3 adds "with its annual amortisation stated" for a facility maturing after the horizon.
  - The claim and the cell can name different true causes: the claim follows the ruled order (principal), the cell follows formula order (annual amortisation).
  - Form 3 goes facility by facility in wall order, then by cause.
  - An unstated currency on MAT-01 takes MAT_FX.
  - In the drawings case, the ratio and resources use REV_RATIO and RUNWAY_NO_DRAWINGS.
  - The exact spelling has no thousands separators.
  - The D-6 builder sync is optional.

## Stage 2 notes
- `methods/cp2d.md`: the D-6 guard limit.
- Stage 2 fills `maturity_date_refs` from the view's T4.18 maturity_date facts. An empty set fails closed.

## Next CP-2D round
It waits for LEAD's oracle batch:
- round 6 A1 (months, with the cp2d builder sync) and A5 (currency and name from the T4.18 text facts);
- LEAD's answers to the points above.

One scoped review then covers b8a5751 and that round.

Not verified:
- L4 (Stage 2);
- real CP-1 heads and views;
- the facts in the prose probe were built in the probe;
- rendering of the new T2E.7 Gap rows.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n
