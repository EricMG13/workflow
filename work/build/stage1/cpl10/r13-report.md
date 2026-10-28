CP-L10 round 13 item 6 (R2 L1) is done. Commit d688c6b on `claude/r13-cpl10`, cut at d2cb626. Step 0 passed: the worktree was clean and HEAD was d2cb626.

**Change** (only `src/deploy_workflow/owners/cpl10.py` and `tests/test_method_cpl10.py`):
- Added `_EXACT = Context(prec=200, traps=[Inexact, Rounded, InvalidOperation])`, the same as cp1d's.
- `screen_topic` now stores `change` as `_EXACT.subtract(close, start)`, in both the zero-base branch and the known branch. It is never rounded.
- `_q38` stays for `pct`. The 2 dp display is untouched, and the materiality rating and rank still use the exact Fraction.
- No new strings. The `change` field comment was updated.

**Ruling clause and tests:**
- **Reviewer's pair:** `test_change_is_stored_exactly_not_rounded_to_38_digits` uses 5/3 and 100/7 at 38 digits. It expects `12.6190476190476190476190476190476190473` and asserts that `pct` is unchanged (`_q38` of the exact quotient).
- **Bound magnitudes:** `test_change_is_exact_at_the_bound_magnitudes_and_after_a_zero_base` covers four checks.
  - ±999999999999999999.9999999999 gives an exact change.
  - A zero base with a 76-digit close stores it whole, with no `E+38` form.
  - A start of 1 against that same 76-digit close stores `9…9.0…01` exactly.
  - None of these traps.
- **TDD:** both tests were red before the fix, for the ruled cause (the stored value was `…047` instead of `…0473`, and the 76-digit close was rounded to 38 digits). My first draft of the tests had two mistakes of my own (an ambient-context subtraction and a wrong expected string). I corrected those and then showed the tests red against the unchanged source.
- **Frozen cases:** all pass, including the 60 frozen quarter pairs.

**Gates:**
- `pytest tests/test_method_cpl10.py tests/test_defect_classes_selfcheck.py`: 365 passed, exit 0.
- `ruff check`, `ruff format --check` and `mypy --strict` on both files: all exit 0.

**Mutant and probe:**
- **Mutant:** I reverted `change` to `_q38(change)` in a full temporary copy (`<S>/cpl10-r13/tree`, `PYTHONDONTWRITEBYTECODE=1`). Both new tests fail (2 failed, 158 passed). I ran one mutant that reverts both branches together, not one per branch. The zero-base test and the known-pair test each target one branch, but I did not run them separately.
- **Probe:** `p13_cpl10_exact.py` is copied to `<S>/cpl10-r13/` with LANE pointed at my worktree. Exit code 1.
  - **Part A:** the probe's expectation assumes the pre-change code. It asserts that the lane's `_q38` result differs from the exact difference, so it reports `A: does not reproduce` once the fix is in. That is the expected result of the fix.
  - **Parts B and C:** B and C both pass. 60 frozen pairs checked, none moved. The bound-magnitude pairs are exact.
  - The probe cannot exit 0 on the fixed code as written.

`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`

Not verified: the full fast lane and the other modules' tests; a real CP-1 head pair at Stage 2; operands wider than 200 digits, which would raise `Inexact` by design; the zero-base and known-pair branches mutated separately; gitleaks, bandit and the other project gates beyond ruff, mypy and pytest.

Ledger: agent=mx-feature fix-rounds=0 gates-first-pass=y