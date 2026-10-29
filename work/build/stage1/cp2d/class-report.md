CP-2D round 11 is committed as **4a0607e** on branch `worktree-agent-a69f2394899aee6d5` (worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a69f2394899aee6d5`). It covers the blank-text class and the pre-D0 maturity rule. All gates exit 0, and all 14 mutants are killed.

**Step 0:** passed. The merge fast-forwarded e3e1277 → 4dfc5ff. HEAD equals the lane tip (4dfc5ff), and `git diff 4dfc5ff HEAD -- src tests cases docs/rulings` is empty.

Only `src/deploy_workflow/owners/cp2d.py` and `tests/test_method_cp2d.py` changed (+295/−41).

**Class by class**
- **Quote cases (B1 edge cut, B3 wrap):** do not apply. CP-2D reads no figure, name or label from an analyst quote; the inventory and probe adapter agree. No quote cases were added.
- **Blank text: fixed.**
  - **Before:** 44 of 55 cases were red (11 fields × 4 whitespace-only values). `""` already passed through the schema's `min_length` refusal, or through LIMITATION_ISSUE / INSUFFICIENT_ISSUE for a limitation.
  - **Fields (11):**
    - `assessments[0..2].text` and `.credit_implication`
    - `assessments[0].limitation` (positive) and `assessments[2].limitation` (gap_minimum_cash)
    - `minimum_cash.rationale`
    - `minimum_cash_absence.reason` and `.follow_up`
  - **Frame:** none is pinned for CP-2D, so the fallback `<path>: empty text` is used (`cp2d.EMPTY_TEXT`, matching `defect_classes.EMPTY_TEXT`).
  - **Fix:** a new public `analyst_text_fields(submission)` returns (path, text) pairs and replaces `_texts`. In `submission_issues`, the empty-text issues are placed after SECTION_ISSUE and before DIGIT_ISSUE, one per path, in field order.
  - A blank limitation still also gets its existing LIMITATION_ISSUE or INSUFFICIENT_ISSUE.
  - **Tests:**
    - `test_r11_blank_text_is_refused`: `BLANK_CASES` × `BLANK_FIELDS` through `blank_failure`.
    - `test_r11_blank_text_twin_is_not_refused_as_empty`
    - `test_r11_blank_fields_cover_every_analyst_text_field`: the module's paths, with indices normalised, equal the test's field set.
    - `test_r11_blank_issue_sits_with_the_text_checks_in_field_order`
  - Every frozen case passes unchanged.

**Riding item: a maturity before D0 (the CP-3C B1 rule, in CP-2D's wording)**
- **Reason:** a new `PRE_D0` reason, `Not calculable: facility <id> maturity date is before the balance date`, comes from a new `_position_gap` that sits in the unstated date's slot.
- **Cells that become missing with that reason:**
  - the wall's months (c3) and inside-horizon (c4);
  - amortisation and maturities inside the horizon (T2E.3.r06/r07);
  - cash at horizon end (T2E.3.r08);
  - T2E.5.r01/r03/r05/r06/r07;
  - `maturity_inside_horizon`, unless another facility is known to fall inside the horizon.
- **What stays known:** the maturity date, principal, share, cumulative share, the runway and the undrawn term commitment.
- **Own line:** `Facility <id> maturity date is before the balance date; maturity-wall figures that need it are not calculated.`, labelled `Facility maturity date (<id>)`, kind Limitation. It sits in the maturity-date slot of the facility's lines, after the FX line and before the principal line.
- **GAP-01 claim (D-2 form 3, maturity-date slot):** `The funding gap is not calculated: [T2E.5.r07] needs every facility to mature on or after the balance date, and one does not.` It comes after the FX and currency causes and before principal. It passes `prose.check(..., gaps={"T2E.5.r07"})`, and the cause phrase passes `bare_figures`. `_facility_need` is now `_facility_cause`.
- **Tests:**
  - `test_r11_a_maturity_before_d0_is_a_gap`, parametrised on 2025-06-30 and **D0 − 1 day (2025-12-30)**. It checks every cell above, the own line, the ledger row, the GAP-01 text and that no "Interest after maturity" line appears.
  - **On D0:** `test_r11_a_maturity_on_d0_is_zero_months_and_inside`. It checks months 0, inside "Yes", the principal counted in maturities, no pre-D0 reason or line, "Interest after maturity" present, and that GAP-01 with cfo missing gives form 4, not the pre-D0 cause.
  - `test_r11_pre_d0_takes_the_maturity_date_slot_in_d2_order`
  - `test_r11_pre_d0_own_line_takes_the_maturity_date_slot`
  - `test_r11_a_known_inside_facility_keeps_the_flag_known`
- **Choices I made where the ruling is silent:**
  - Cumulative share stays known. The wall order is known from the date, and CP-3C keeps shares known.
  - MAT-01 keeps its chip form, as an unstated maturity date does in CP-2D. The L5-frame cause is applied to GAP-01 only.

**Mutants** (script `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2d-class/mutants.py`). Each ran from a full temporary copy with `PYTHONDONTWRITEBYTECODE=1`; the script exits 0.

| Mutant | Exit |
|---|---|
| blank: rule reverted | 1 |
| blank: no strip | 1 |
| blank: frame without path | 1 |
| blank: always | 1 |
| pre-D0: whole rule reverted | 1 |
| pre-D0: on D0 counts as before | 1 |
| pre-D0: wall cells reverted | 1 |
| pre-D0: schedule reverted | 1 |
| pre-D0: inside flag reverted | 1 |
| pre-D0: own line removed | 1 |
| pre-D0: own line kind Gap | 1 |
| pre-D0: claim cause removed | 1 |
| pre-D0: claim cause on D0 | 1 |
| pre-D0: claim cause after principal | 1 |

**Gates** (all exit 0)

| Gate | Result |
|---|---|
| `PYTHONPATH=src …/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_method_cp2d.py` | 220 passed |
| `ruff check` on both files | 0 |
| `ruff format --check` on both files | 0 |
| `MYPYPATH=src mypy --strict` on both files | 0 |

`ruff format --check` failed once on the test file before I committed, so I ran `ruff format`. Every other gate passed on its first run.

**Stage 2 notes for `methods/cp2d.md`.** That file is outside my scope, so nothing was written.
- Every analyst text field refuses whitespace-only text as `<path>: empty text` (0-based paths, `analyst_text_fields` order), placed after the section issue and before the digit issue. The schema refusal of `""` stands.
- CP-2D is outside the quote-reader class.
- A maturity before D0 follows the CP-3C B1 rule:
  - the date stays known;
  - months, inside-horizon and their dependants take the pre-D0 reason;
  - cumulative share stays known;
  - the own line is a Limitation;
  - the GAP-01 form 3 cause sits in the maturity date's slot;
  - MAT-01 uses the chip form.

Not verified: CP-2D's full Stage 2 path and other modules' suites were not run (only the module test file, per the brief). The new claim string was checked with `prose.check` and `bare_figures`, but not with `prose.issues` against a bound CP-2D fact set. The two calls on the ruling (cumulative share stays known; MAT-01 keeps its chip form) are mine and were not confirmed by LEAD. Blank cases ran at the listed indices on the positive and gap_minimum_cash payloads only. No GitNexus `detect_changes` was run (no MCP use here).

Ledger: `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y`
