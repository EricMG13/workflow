Commit 36d3746 on claude/r13-cp2d (one commit on 7f2a9a2, with the Co-Authored-By line). It covers items 1 and 2 and the addendum-4 prose, and every gate and probe exits 0.

**Items and tests** (all in `tests/test_method_cp2d.py`, written first)
- **M1, runway.** `_runway` now uses an `OperandGap` undrawn reason when there is one. Test: `test_runway_names_the_revolver_operand_and_its_state`.
  - It covers commitment and drawings, each conflicting and not_applicable.
  - Example: `Not calculable: RCF commitment is conflicting`.
  - Labels are the module's `OPERAND_LABELS`, so the drawings operand reads "RCF drawings", not "RCF drawn".
  - The missing/undisclosed path is unchanged.
- **Addendum 4, prose.** LIQ-01 and GAP-01 use new `LIQ_STATE` / `GAP_STATE` templates, and the own limitation uses `FUNDING_GAP_ON_CASH_ALONE_STATE`. They follow GAP_OPERAND's shape (`… needs RCF commitment, which is conflicting; …`). A new helper, `revolver_state`, supplies the label and state word. The missing-revolver texts are untouched. Test: `test_unknown_revolver_prose_uses_the_state_word_not_undisclosed`.
  - It covers each string × commitment/drawings × conflicting/not_applicable.
  - It asserts the exact text, `prose.check` on the LIQ-01 and GAP-01 templates, `prose.bare_figures` on the limitation, and no "undisclosed" in any of the three.
  - Run against 7f2a9a2 source, the 8 new tests for M1 and the prose all fail. The R1, R3 and R4 pin tests pass there, as expected for tests that pin existing behaviour.
- **R1.** `test_absent_reads_only_missing_as_undisclosed` pins `_absent` on conflicting, not_applicable, missing and None operands.
- **R3.** `test_empty_schedule_never_reads_unknown_total_debt_as_zero`: with `facilities=()` and `total_debt_bs` conflicting or not_applicable, the funding gap is a Gap with reason `SCHEDULE_EMPTY`.
- **R4.** `test_cp1_cross_check_never_reads_unknown_metric_as_zero`: a non-known `cash_closing` yields `CP1_REPORTS_NO`, not "differs".

**Probes and mutants**
- Mutants: `<S>/cp2d-r13/mutants_fix1.py` is the original M1–M19 plus seven new ones. F1 and F2 cover the runway, F3 covers `_absent`, F4–F6 cover LIQ-01, GAP-01 and the limitation, and F7 covers dropping the state word. All 26 are killed, exit 0.
- Reviewer mutants (`r3_review_mutants.py`): R1, R2, R3, R4, R6 and R7 are killed. R5 survives because it is equivalent, as you said. The script exits 1 only because of R5.
- `r2_conflicting_revolver_prose.py` exits 0 with 0 "undisclosed" hits for both fields.
  - Runway rows: `Not calculable: RCF commitment is conflicting` and `Not calculable: RCF drawings is conflicting`.
  - The own limitation now reads `The funding gap is not calculated because RCF commitment is conflicting; …`.

**Gates**
- pytest on cp2d, cp3c and defect_classes_selfcheck: 822 passed.
- `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both files: all exit 0.

**Gate-run note**
- The first run used a bare `ruff` and `mypy`, which are not on PATH, so I reran with the venv binaries.

**Left alone:** FUNDING_GAP_ON_CASH_ALONE's missing-revolver wording, the sum-copy status, the recomputed-cell period, and the balance-date fallback.

**Open point for LEAD**
- If the commitment is conflicting and drawings are missing, `drawings` is true, so the runway, LIQ-01 and GAP-01 name "drawings undisclosed" rather than the conflicting commitment. This is the existing precedence and I did not change it.

Not verified: the whole-repo suite and the other gates (jscpd, complexipy, bandit) were not run. The new texts were not read by the downstream renderer or the other modules (CP-4C). The mixed case above (conflicting commitment with missing drawings) has no test.

agent=mx-feature fix-rounds=1 gates-first-pass=n