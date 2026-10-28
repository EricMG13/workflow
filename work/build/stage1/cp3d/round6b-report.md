# CP-3D follow-up (round 6b C1–C3): controller-saved

- **Commit:** `f72a8bf` on `claude/cp3d-stage1`, after merging lane a35ec2c.
- **Tests:** 199 passed. No pin moved, and the reviewer's pin test is kept.
- **Gates:** all three exit 0. The first `ruff check` failed (ISC004), so not on the first pass.

## Rulings and their tests
- **C1:** `test_c1_single_dealer_limitation_follows_the_observations`, covering bid and offer, bid only, offer only, and talk only.
- **C2:** occurrence is checked before shape.
  - Margin: `test_c2_margin_token_that_occurs_gets_the_shape_issue`.
  - Reference rate: `test_c2_reference_rate_token_that_occurs_gets_the_shape_issue`, with frame `reference_rate: level percent_text <x> must have at most three integer digits and four decimal places`.
  - Level: `test_c2_level_token_that_occurs_gets_the_shape_or_bound_issue`. The pinned bound is kept. More than four decimals gives `<path>: level_text <x> must have at most four decimal places`.
- **C3:** tests:
  - `test_c3_prohibited_conclusions_in_the_widened_fields`
  - `test_c3_market_absence_is_checked_and_comes_first`
  - `test_c3_quotes_are_never_checked`
  - `test_c3_only_the_pinned_summary_refusal_hits_among_frozen_literals`

## Reviewer probes (`stage1-review-C/`)
| Probe | Before | After |
|---|---|---|
| single_dealer | 1 | 0 |
| unpinned_level_bound | 0 | 1 |
| prohibited_scope | 0 | 1 |

All three changed as expected; the second and third documented the old gap. `cp3d/prose_6b.py` exits 0.

## Prose
- The C1 lines and the C3 frame give no hits.
- The C2 issue frames repeat the submitted token, so they hit `Bare figure`, as the pinned "does not occur" frames do.

## Choices (to LEAD)
1. **Non-numerals.** A numeral check runs before the occurrence check, so pinned refusal [1] `level_text ninety is not a decimal number` is kept.
2. **Amortisation** shares the margin check. It gets `amortisation: value_text <x> must have at most three integer digits and four decimal places`, a frame no ruling names.
3. **Digit check only.** `reference_rate.name`, the term absences and `reference_rate.absence` are not in C3's list, so they still get only the digit check.

## Stage 2
`methods/cp3d.md` gets the C1 limit: "no trade" restates the frozen sheet.

Not verified:
- Stages 2–4;
- prose on real Facts;
- no search was made for 4-digit numerals in frozen quotes;
- complexipy is not installed.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n
