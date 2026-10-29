Addendum 3 is applied and committed as a212da3 on `claude/r13-cp3d`. The branch also merged `claude/round12` at d193096 (clean). Everything in my previous report stands, including the earlier commits fcd7db2, a7dea76 and d96448b.

What a212da3 adds, all in `tests/` (no source change):
- **Shared class cases:** four text cases in `tests/defect_classes.py`.
  - `b3-index-0-letter-wrap-text`: `- 1.25 notes` on `A-\n1.25`, refused with B3's "does not occur in the quote".
  - `b3-index-0-digit-wrap-text`: `- 2025 notes` on `2024-\n2025`, refused with the same B3 issue.
  - Each has an accepted joined-spelling twin: `b3-index-0-letter-joined-text` and `b3-index-0-digit-joined-text`.
- **Selfcheck:** `tests/test_defect_classes_selfcheck.py` lists both pairs in `test_round_13_wrap_cases_follow_the_w_exemption`.
- **`_name_occurs` tests:** `test_r13_w_minus_is_no_b3_wrap_split` in `tests/test_method_cp3d.py` gains `index-0-digit`, which is `- 2025 notes` on `2024-\n2025`. The letter case `- 1.25 notes` on `A-\n1.25` was already there as `index-0`.

Gates all exit 0:
- pytest on `tests/test_method_cp3d.py` and `tests/test_defect_classes_selfcheck.py`: 1083 passed.
- `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on the four edited files.
- Mutants: all 14 still KILLED (exit 0).

Only `amortisation_nonzero` carries a delta, as the addendum confirms. The new cases make CP-2E and CP-8 more red in the shared-class tests (two more cases each of the new text cases run through their name readers). I did not re-run those two files after this commit, so their counts are not re-measured.

Not verified: the full suite and `test_host_h1`; the CP-8 and CP-2E counts after a212da3; the 121 CP-8 failures that predate this change (cause not examined); GitNexus `impact` and `detect_changes`; the `methods/cp3d.md` guard-limit notes (controller's Stage 2 notes).

agent=mx-feature fix-rounds=0 gates-first-pass=n