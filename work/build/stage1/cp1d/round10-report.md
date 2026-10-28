CP-1D now applies LEAD round 10: basis amounts are read with their printed sign. The CP-1D test file passes (143 passed, 1 skipped) and all three gates exit 0.

**Commit:** b7cd02e on `claude/cp1d-stage1`. Before the change the branch was fast-forwarded from 7c88a98 to the lane tip 7fdddbf. There were no conflicts, and no pinned sha moved (`test_oracle_is_the_pinned_revision` passes), so nothing was re-pinned.

**What changed** (only `src/deploy_workflow/owners/cp1d.py` and `tests/test_method_cp1d.py`):
- **Reading the sign:** a new pattern, `_SIGNED_AMOUNT`, runs over `normalise(quote)`.
  - A `-` is a minus when it starts the quote or follows a character that is neither a letter nor a digit (`(?<![A-Za-z0-9])-`).
  - A `+` is ignored.
  - `(N)`, with the brackets directly around the digits, reads as `-N`. `(4.30 percent)` still reads as 4.30.
  - `_basis_amounts` returns these signed strings, so step 5 counts signed tokens. Counts on unsigned text are unchanged.
- **Bounds check:** in `_shape_issue`, a basis of 0 or less now returns the pinned `Accepted basis must be above 0 and below the proposed amount: <label>`. This comes before the exactness test, and it also fires when the proposed amount is unstated (the Recurring path, 5b Y4).
- **Unchanged:** `_bridge_amount` keeps the unsigned `_AMOUNT` full match, and no new string was added.

**Tests** (each new one failed for the reported cause before the fix):
- `test_signed_basis_figure_meets_the_bounds_rule`: the bridge page prints U+2212, ASCII `-`, U+2013 or `(1.80)` before the figure, and a01 quotes it. The quote still matches the page, and a01 gets the bounds text.
- `test_basis_amount_at_or_below_zero_is_the_bounds_issue`:
  - With a stated proposed amount: `-1.80`, `(1.80)`, `-0.00000000001` (now ahead of the exactness text), `-1e18`, and a03 `-0.50`.
  - With an unstated amount on the gap pack's Recurring row 3: `0`, `-1.80`, `(1.80)` and a negative long decimal, all ahead of the exactness text.
- `test_hyphen_after_a_letter_or_digit_is_not_a_sign`:
  - `1-December`, `S-1.80`, `+1.80` and `(1.80 million)` pass validation.
  - `2024-2025` and `95-96` still get the "exactly one amount" text. They hold two numbers, so step 5 refuses them before and after the change.
- `test_basis_amounts_read_the_printed_sign`: a direct check of what `_basis_amounts` reads for each sign and non-sign form.
- Two guard rows in `UNUSABLE_PAGES` (bridge `-1.00` and `(1.00)` give `Bridge table not found`) passed before and after the change.
- The bounds test was split into a shared helper, `_basis_issues`; the existing Y4 cases are unchanged.
- Every frozen case still passes as it did.

**Probe:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp1d-r10/p_r10_mutants.py`, exit 0. It mutates a full temporary copy for each mutant, with `PYTHONDONTWRITEBYTECODE=1`. The unmutated copy passes, and all seven mutants are killed:
- lookbehind removed;
- sign not read;
- parentheses not read;
- parentheses read as positive;
- the "0 or less" check removed;
- `<=` changed to `<`;
- the bounds check moved after the exactness test.

**Gates:** `ruff check` exit 0, `ruff format --check` exit 0, `MYPYPATH=src mypy --strict` exit 0, all on both files.

**Prose and bare-figure hits:** none, because no new string was added.

**Decision for review:** ruling 1D7 (an accepted assessment with an unstated amount skips step 6 and gets `Cannot accept an unstated amount`) still comes before the new "0 or less" check. I read the round 10 ruling as covering only the Recurring path on an unstated amount.

**Stage 2 notes (listed, not written):**
- `methods/cp1d.md` needs the sign rule (minus, `+` ignored, parentheses) and the extended "above 0" check.
- The builder text in `cases/cp1d-owner/expected.json $.refusal_rules.partly_supported` ("a digit run with an optional decimal part") is superseded and should be fixed at the next CP-1D oracle batch. No value changes.

Not verified: only the CP-1D test file ran (no full suite and no G1 run). The rule was not exercised against any non-synthetic source text. I did not check by tests that every frozen basis quote reads the same; that rests on the frozen tests passing and on LEAD's `p_sign_rule.py`.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y
