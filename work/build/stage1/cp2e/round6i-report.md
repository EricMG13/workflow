# CP-2E round 6i report (controller-saved from the implementer's hand-back)

# CP-2E round 6i report

Round 6i and the round 5–6 review Low are both done: fixed-rate debt no longer gets a floor limitation, and the E8 word boundaries are now pinned by a test. Committed as **`aed93b3`** on `worktree-agent-a219254fe68cc1c2d`.

## Step 0
- **Merge:** `git merge claude/module-dev-status-review-0981b6` was a clean fast-forward to `93fa796`; the lane already held `af23f7f`. No conflicts.
- **Pins:** no oracle sha this test asserts moved, and the test asserts none, so nothing was re-pinned. Checked with `shasum -a 256`:
  - `cases/cp2e-owner/expected.json`: `8f507e108ac3d75e4fcc3f524dcf1c31ad8ceedb2e2359fcb9de02b56f25bc86`
  - `cases/cp2e-owner/builder/build.py`: `de0d14fcb431a965452d91311f150e7e527f7f6f877b1da19065acd93a848adf`

## Rulings and their tests
- **Round 6i, CP-2E A4, fixed rate with a floor above zero.**
  - `_floor_limitation` returns no line for fixed-rate debt, whatever the floor, and neither floor line is emitted. The fail-closed raise is gone.
  - Floating-rate debt keeps `_LIM_FLOOR` for a known 0 floor and the A4 text for a floor above zero.
  - A negative floor still fails closed; it can only come from directly built inputs.
  - Tests:
    - `test_round6i_no_floor_limitation_on_fixed_rate_debt[0]` and `[25]`: the limitations equal the positive case's own limitations minus its floor line, and the claims are prose-clean.
    - `test_valid_inputs_settle_with_clean_claims`: all 648 grid combinations now compose with no raise.
  - All three failed before the change.
- **Round 6i, A4 floor not stated:** per the ruling, nothing is built.
- **Round 5–6 review Low, the E8 `\b` anchors:** `test_e8_word_boundaries_are_pinned["fixed rates"]` and `["prefixed rate"]` each expect the neither-stem issue. The code was already correct, so these pass on it; their job is to kill the two reviewer mutants, and they do.

## Probes and exit codes
`<S>` is the scratchpad path from your brief.
- **`<S>/cp2e-r6-review/mutants_review.sh` (reviewer):** exit **3**.
  - **Killed:** `e8_no_trailing_b` and `e8_no_leading_b`, as required, plus `neg_word`, `zero_word`, `a4_text`, `e8_no_ignorecase`, `e8_len_ge1`, `e7_no_known_cov`, `e7_text`, `e6_reason`, `a3_lev_after_label` and `a3_share_label`.
  - **APPLY-FAILED (counted as survivors by the runner):** `a4_no_rate_check` and `a4_floor_gt_to_ne`. The lines they target were replaced by the round 6i change.
  - **Survived:** `e7_word_guard_off`, the guard the review marked Info and accepted, since nothing can reach it.
- **`<S>/cp2e-r6h-8/mutants_6i.sh` (new; it aims at the new A4 lines, each mutant run from a full rsync copy):** exit **1**.
  - **Killed:** `a4_fixed_check_off`, `a4_fixed_gets_floor_line`, `a4_floor_line_skipped`, `e8_no_trailing_b` and `e8_no_leading_b`.
  - **Survived:** `a4_floor_gt_to_ne` (`floor > 0` changed to `!= 0`). The mutant is equivalent on validated input, because a quoted floor is digits only and so never negative. This is the same Info the review already accepted.
- **`<S>/cp2e-r6-review/probe_fixed_floor_reachable.py`:** exit **1**, the expected change. It exits 0 only while compute raises for a fixed rate with floor 25. It now prints `compute: no raise`, the added interest stays a known 0, and validation returns no issues.
- **Older probes:**
  - `<S>/cp2e-r6/probe_new_strings.py`: exit 0, 20 claims, no hits.
  - `<S>/probe3.py`: exit 0.
  - `<S>/stage1-review-A/probe_cp2e_negative_denominator.py`: exit 1, unchanged since A3.

## Tests and gates
- **Tests:** `PYTHONPATH=src …/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_method_cp2e.py` gives **87 passed** in 1.61 s, exit 0, with no xfail.
- **Gates:** `ruff check` 0, `ruff format --check` 0, `MYPYPATH=src mypy --strict` on both files 0. All passed on the first run.

## Other output the brief asks for
- **Prose and bare-figure hits:** none. This round adds no new strings; it only removes a floor line for fixed-rate debt. The fixed-rate tests and the grid run every claim through `prose.issues`, and `probe_new_strings.py` finds no bare figures.
- **Stage 2 notes:** none new. A4's floor-not-stated text stays unbuilt until a schema change makes the floor optional.
- **Builder syncs for LEAD:** none.

Not verified: A4's floor-not-stated path (none exists); E7 with validated inputs (only directly built inputs reach it); the equivalent `a4_floor_gt_to_ne` mutant; any test suite other than `tests/test_method_cp2e.py`; Module/Fact assembly with real Citations; inherited limitations; `RULES`, tool-use refusals, tamper and probe; rendering; any settled run.

Ledger line:
`2026-10-28T14:20Z cp2e-stage1-round6i pytest tests/test_method_cp2e.py exit=0 87 passed 0 failed agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y`
