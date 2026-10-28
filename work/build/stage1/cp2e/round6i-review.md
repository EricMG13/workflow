# CP-2E round 6i scoped review (mx-feature; controller-saved)

**Verdict: APPROVE.** One Low finding rides with the next fix. It doesn't reopen review.

**Check results (diff 93fa796..aed93b3)**
1. **Pass.** `_floor_limitation` (cp2e.py ~1297-1310) returns `None` for `rate_type == "FIXED"` before it looks at the floor. `own_limitations` then skips the line. The raise for fixed rate is gone. `test_round6i_no_floor_limitation_on_fixed_rate_debt[0]` and `[25]` assert that neither `_LIM_FLOOR` nor `_LIM_FLOOR_ABOVE` appears.
2. **Pass in the code, with one test gap.**
   - Floating floor of 0 gives `_LIM_FLOOR`.
   - Floating floor above 0 gives `_LIM_FLOOR_ABOVE`, and I saw no edit to the A4 text itself. `test_a4_floor_above_zero_limitation` still pins it.
   - A negative floating floor still raises `ValueError`, now with a new message ("Floor limitation: a floor of N basis points is not a quoted floor"). The old message named "no ruled wording".
   - No test exercises that raise (see Low below).
3. **Pass.** The fixed-rate test compares the limitations with the positive case's own limitations minus its floor line (`positive[2]`). That check covers the static, cash, remainder and other lines. The `positive` case I compared against is the floating one, so the comparison also holds for the other lines.
4. **Pass.** The new tests fail without the change. The runner `mutants_6i.sh` killed `a4_fixed_check_off`, `a4_fixed_gets_floor_line`, `a4_floor_line_skipped`, `e8_no_trailing_b` and `e8_no_leading_b`. `mutants_review.sh` also killed `e8_no_trailing_b` and `e8_no_leading_b`. The anchor tests are `test_e8_word_boundaries_are_pinned` with "fixed rates" and "prefixed rate".
5. **Pass.** Nothing in the diff is a stub or a fake value, and there is no catch-all. The raise that remains is specific and fail-closed.

**Findings**
- **Low** (cp2e.py ~1303-1308; tests/test_method_cp2e.py, no test): the negative-floor fail-closed raise has no test. The mutant `a4_floor_gt_to_ne` (`floor > 0` changed to `floor != 0`) survives, so a negative floating floor would silently get the above-zero text. The report calls the mutant equivalent because validation only allows digits. That is true for validated input, but the raise exists for directly built inputs, and a test could build one. Fix: add a test that builds a `FacilityTerms` with a floating rate and a floor of -5 and expects `ValueError` matching "Floor limitation". Probe: `mutants_6i.sh`, mutant `a4_floor_gt_to_ne`.
- **Info:** a fixed-rate facility with a negative floor, built directly, now emits no line and does not raise. This matches the ruling ("any floor value"). No action needed.
- **Info:** `e7_word_guard_off` survives. The review already accepted it.

**Gate exit codes** (all from the target root)
- pytest `tests/test_method_cp2e.py`: **0**, 87 passed. This matches the report.
- ruff check: **0**.
- ruff format --check: **0**.
- `MYPYPATH=src mypy --strict`: **0**, no issues in 2 files.
- `mutants_6i.sh`: **1**, with one survivor (`a4_floor_gt_to_ne`). This matches the report.
- `mutants_review.sh`: **3**. This matches the report. The three counted failures are:
  - `a4_no_rate_check` and `a4_floor_gt_to_ne`: both APPLY-FAILED, because the targeted lines were replaced by this change.
  - `e7_word_guard_off`: survived. The Info above.

**Not verified:** the full test suite and any module other than CP-2E, since I was told to run no other tests. Mutants beyond the two runners were not run. I did not check the report's claim that the older probes still exit 0 or 1. Whether the downstream Stage 2 or CP-3C consumers handle a facility with no floor line was not exercised. No test builds a negative floor.
