CP-3C round 13 is done and committed as `6373602` on `claude/r13-cp3c`. The worktree was clean at d2cb626 for Step 0. Files touched: `src/deploy_workflow/owners/cp3c.py` and `tests/test_method_cp3c.py` only.

**Ruling clauses and tests** (all new tests are named `test_r13_*`, in `tests/test_method_cp3c.py`)
- **Item 4, `Status` and `CellStatus` take all four statuses.** `test_r13_cell_status_holds_the_four_product_statuses`. `GAP_SHOWN` gains `conflicting` as `∅ G#`, spelled as a gap like the product.
- **Item 4, `_amount` and `_stated_text` return no value for an unknown status.** `test_r13_an_unknown_status_gives_no_amount_or_text_and_does_not_raise`. Red before the fix: `ValueError: CP-3C adjusted_ebitda: expected a MILLIONS amount`.
- **Item 4, `_op` uses the C-2 frame.** `test_r13_op_names_the_state_of_an_unsettled_operand_in_the_c2_frame`, over cash, undrawn, EBITDA, cash interest and the CP-2D run-rate, for both statuses. The wording is `Not calculable: <label> is conflicting` and `... is not applicable`. `_op` takes a status. `Operands` gains `statuses`, filled in `compose_operands`, with `missing` as the default.
- **Item 4, `_copy` keeps the status and CP-1's limitation verbatim.** `test_r13_copies_keep_the_status_with_the_limitation_verbatim`, for a CP-1 copy (`T3D.2.r07`) and a CP-2D copy (`T3D.2.r11`). `test_r13_the_trace_spells_an_unsettled_upstream_fact_as_a_gap` covers the T3D.9 trace.
- **Item 4, `_check_value` requires a reason and no value for every unknown status.** `test_r13_check_value_requires_a_reason_and_no_value_for_every_unknown_status`, for CP-1 and CP-2D facts.
- **Item 5, `currency` is `cash_closing`'s `Fact.currency`.** `Cp1Fact` and `Cp2dFact` gain `currency`. A new `check_currency` runs first in `compute`. Wordings, all in the `CP-3C …` frame:
  - `CP-3C cash_closing: currency is not set` (None, empty or blank).
  - `CP-3C: reporting currency 'EUR' is not cash_closing's 'USD'`.
  - `CP-3C <name>: currency 'X' is not 'USD'`, for every other known MILLIONS fact read:
    - CP-1 undrawn, EBITDA, interest and each facility amortisation.
    - CP-2D run-rate, minimum cash, funding gap and each wall principal.
  - Tests: `test_r13_currency_is_cash_closings_and_must_be_set`, `test_r13_the_reporting_currency_is_the_cash_closing_currency`, `test_r13_every_millions_cp1_fact_read_has_the_same_currency`, `test_r13_every_millions_facility_and_cp2d_fact_read_has_the_same_currency`, `test_r13_a_missing_cash_closing_needs_no_currency`.
  - The test helpers `_cp1_fact` and `_cp2d_fact` now set `currency=USD` on MILLIONS facts.
  - The new `currency` fields were added before the currency tests, so those tests fail for the ruled cause and not on a missing field. Before the fix they ended in "DID NOT RAISE ValueError".

**Tests first.** 27 of 28 new tests were red for the ruled causes before the fix; the 28th (`test_r13_a_missing_cash_closing_needs_no_currency`) passed against the pre-fix code by design. The unknown-status tests failed with `expected a MILLIONS amount`, the `Status` test with a set mismatch, and the currency tests with no raise.

**Mutants** (`<S>/cp3c-r13/mutants.py`, full temporary copy, `PYTHONDONTWRITEBYTECODE=1`): exit 0. All 16 are killed, one or more per ruled clause:
- `_amount`, `_stated_text`, `_op`, the operand statuses, and `_copy` (two mutants).
- `_check_value`, the `conflicting` spelling, the trace, and `Status`.
- Currency: cash unset allowed, reporting currency vs cash not checked, other facts not checked, facility amortisation unread, CP-2D principal unread, check not called.

**Probes** (copied to `<S>/cp3c-r13/`, LANE pointed at the worktree)
- `p13_l2_sources.py`: exit 0. It is about CP-2A `base_period`, `name` and the manifest, so it does not touch CP-3C code.
- `p13_status_prose.py`: exit 0 on its own checks. Its reproduction legs `p1`, `p3` and `p4` expect the pre-change code to still show the defect, so they report A failures on the fixed tree. `p3_cp3c_cp1_status.py` now exits 1 ("composed" on all four legs), meaning the defect is gone. `p1` and `p4` are CP-2D reproductions and are not mine.

**Gates**
- pytest (`test_method_cp3c.py` and `test_defect_classes_selfcheck.py`): 536 passed, exit 0.
- `ruff check`: exit 0.
- `ruff format --check`: exit 0.
- `MYPYPATH=src mypy --strict` on both files: exit 0.

**CP-2D oracle.** My tests build CP-3C inputs from the frozen CP-2D oracle. They do not run CP-2D code, so I added no delta table or Stage 2 re-pin test. Frozen cases still pass unchanged.

**Judgement calls**
- The currency check applies to known MILLIONS facts only. A gap fact carries no value, and its currency in a real head is not observed.
- A missing `cash_closing` has no currency to read, so the reporting currency is then unchecked rather than refused. This keeps a missing cash a gap. Decision for you: the alternative is to refuse, which would make a missing `cash_closing` unrunnable.
- The mismatch message uses the fact id for CP-2D facts, for example `T2E.3.r01`.
- `_op`, `check_currency` and `_STATE_WORD` follow the cp4c pattern. `_STATE_WORD` is a copy and does not import from cp4c.

Not verified: a real promoted head's T4.10 `currency` (read from code only, per the ruling). Dependants other than `_op` for a conflicting or not_applicable operand: minimum cash still gives its fixed "not assessed" reason, and facility text terms (secured status, seniority, amortisation) still give the "not stated" frames. A gap fact's currency. The Stage 2 binding and render of a conflicting cell through the product. Whole-suite and other-module tests were not run.

agent=mx-feature fix-rounds=0 gates-first-pass=y