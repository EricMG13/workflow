# Stage 2 Lows: one batch at the end of the stage, or riding with the module's next fix

- **[G1-X guards] Low, test gap.** No test covers a step that has a scope row while its `sources` is `False`. The mutant `==` → `<=` at owner_workflow.py:614 survives. Probe: `<S>/s2-g1x-review/p_one_direction.sh`. Source: stage2/g1x-guards-review.md.
- **[G1-X guards] Info.** The docstring lines at owner_workflow.py:563, :565 and :566 are longer than 100 characters.
- **CP-DR (fix1 re-review) Low:** reader refusals for a negative count (L2b) and a per-gap share not known (L2f) are untested; `<S>/cpdr-s2-review/review_mutants_fix1.py`.
- **CP-2E (fix1 re-review) Info:** `tests/test_owner_cp2e.py` docstring :5-6 still says tamper/stale/blocked/begin-refused are not written; `Cite` breaks `copy.deepcopy`/`asdict` (no src path does it; also CP-3D `Cites`); empty summary gets two issues.
- **CP-2A (close release, lease text).** Round 5 item 1's unit rule checks settled operands only; an unsettled operand carries no amount and no currency. Lease text "every operand fact it reads" narrows to "every settled operand". Source: cp2a/fix1-review.md M2; `<S>/cp2a-s2-review/r3_unsettled_stamp.py`.
- **CP-2A Low (unchanged).** Public-API caller-built `Upstream` with forged facts composes (`r4`); not reachable through submit, probe or view.
- **Shared defect test Info.** `test_a_verbatim_pattern_needs_only_one_accepted_value_on_one_path` (`test_defect_classes_selfcheck.py:529`) repeats `:519`; it never shows a second refusing path excused. End batch. Source: defect-classes/fix2-review.md.
