# CP-2A fix round 2 report (mx-feature)

CP-2A fix round 2 is committed as `fbe2d3c`, on top of ac97894. The tree was clean at the start. Only `tests/test_owner_cp2a.py` and `tests/test_connect_cp2a.py` changed, and `src` and `cases/` are untouched.

**Items**
1. **M1 (fixed).**
   - `_find_rows` is replaced by `cp2a_consumer_rows(report)`. It reads `report["consumers"]` and keeps rows with `canonical_module == "CP-2A"`.
   - `test_a2e_cp1_readiness_row_for_cp2a_is_ready_with_limitations` now runs `DownstreamReport.model_validate_json(output)` on the real CP-1 readiness step output before selecting. It asserts exactly one row, status `ready_with_limitations`.
   - New fast test `test_cp2a_consumer_rows_ignore_the_request_and_the_assessment` passes. It builds the three places that name CP-2A, using the oracle review literal. It also checks the `ConsumerRequest`, `ConsumerRow` and `DownstreamReport` field names.
   - It does not use a frozen full `DownstreamReport` literal: a full one needs narrative, model and financial book inputs, which is not cheap to build. The real-shape check runs in the deferred test instead.
   - `r1_a2e_find_rows.py` hard-coded `t._find_rows`. I repointed it to `cp2a_consumer_rows` (edited in the scratchpad) and it now exits 0. It would fail unedited because that function no longer exists.
   - No other deferred test uses `_find_rows`. I read the remaining ones and found no multi-match selector.
2. **A3 Low (fixed).**
   - Both `test_a3_unreplaced_figure_is_invalid` in `tests/test_owner_cp2a.py` and `test_a3_an_unreplaced_figure_is_invalid` in `tests/test_connect_cp2a.py` now assert `status == "invalid"` and an issue containing "Malformed run text".
   - `r2_gap_and_fig.py` exits 0 and shows that issue.
   - The fast one runs and passes. The deferred one is only collected.
3. **Info (fixed).** The claim-check FIG id lookup in `_assert_head_equals_oracle` now filters `f.table_id == "T4.10"`, as `cp2a_runs` does. No fast test covers it.

**Exit codes**
- Gate set (`test_connect_cp2a`, `test_method_cp2a`, `test_owner_g1x`, `test_host_h1`, `test_defect_classes_selfcheck`): 613 passed, exit 0.
- `--collect-only tests/test_owner_cp2a.py`: exit 0, 16 tests collected (15 plus the new fast one).
- ruff check, ruff format --check and `mypy --strict` on both files: all exit 0. No new `noqa`.
- `mutants.py HEAD`: exit 0, control passes. The only survivor is `validator step[0]`, the equivalent mutant the reviewer already named.

Not verified: none of the 15 deferred tests in `tests/test_owner_cp2a.py` has run (11 to 26 minutes each, Stage 5). That includes the real-shape `DownstreamReport` validation, the T4.10 filter against a genuine CP-1 head, and the deferred A3 "Malformed run text" assertion. The reviewer's earlier Info that the A4 read-body test does not isolate the view replay is unaddressed. FP05 is G2's. I did not re-run `mutants_reg.py`.

agent=mx-feature fix-rounds=2 gates-first-pass=y
