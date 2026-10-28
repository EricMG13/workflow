CP-2E round 10 task review (target c050f57, diff 7fdddbf..c050f57; 2 files, +97/-4, within the brief's file list and well under the 800-line cap)

Verdict: CHANGES REQUIRED. One Medium finding.

## Spec verdict: the rulings are applied as written
1. `_once` (src/deploy_workflow/owners/cp2e.py:501-515)
   - It reads `normalise(quote)`.
   - The minus lookbehind is `(?<![0-9.])(?<!(?<![A-Za-z0-9])-)`, which is the ruling's pattern.
   - Parentheses count as a sign only when `(` sits directly before the token and `)` directly after it.
   - `+` is ignored.
   - `1-December`, `95-96`, `2024-2025`, `S-25` (in place of `S-350`; same shape, inside the 3-digit grammar), `+25` and `(25 percent)` still validate. Tests are at tests/test_method_cp2e.py:790-803.
   - An unsigned `percent_text` against `−25`, `-25`, `–25` or `(25)` gets the pinned `fx.foreign_ebitda_share: percent_text 25 does not occur in the quote` at its existing position (cp2e.py:637-639).
   - A signed labelled operand gets the pinned "does not occur" one check before adjacency, as the ruling allows.
   - No new string. All 100 tests pass, frozen cases included.
2. `on_page` (cp2e.py:537) calls `deploy_vii.quotes.quoted`, the same function `readiness.citation_issues` uses (src/deploy_vii/readiness.py:23, :141).
3. `test_negative_floor_fails_closed` (tests/test_method_cp2e.py:836-839) kills `a4_floor_gt_to_ne` when run alone (my mutant `a4_ne_only_floor_test`, pytest `-k`, exit 1).
4. No stub, fake value or catch-all in the diff. `_floor_limitation`'s raise is an existing, documented fail-closed.

## Quality verdict: findings

**M1 (Medium): this round's `on_page` change makes the raw-quote-after-normalised-match class reachable in CP-2E.**
- Locations:
  - cp2e.py:546: `code` searches the raw `ref["quote"]`.
  - cp2e.py:558: `labelled`'s adjacency check runs on `_squash(ref["quote"])`.
  - cp2e.py:613: E5/E8 `_RATE_PHRASE.findall(rb["quote"])` reads the raw quote.
  - cp2e.py:619: the `reference_rate in rb["quote"]` check reads the raw quote. This one only fails closed.
- Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2e-r10-review/p_raw_after_normalised.py` (argument: the target root), exit 1. In all three cases below, `quoted` (and so `citation_issues`) accepts the quote, and the validator returns `()` at c050f57:
  - **A.** The page prints only `EURIBOR`. Quote `priced off EUR­IBOR` with `code_text EUR` validates, so the debt currency is EUR although the page prints no EUR.
  - **B.** The page states both `floating rate` and `fixed rate`, which should get the pinned "states neither" refusal. Quote `... no fi­xed rate` hides the second stem, and the basis is accepted as FLOATING.
  - **C.** The page says `spread 250 basis points ... and 25 basis points is the fee`. Quote `The spread 25­0 ...` with `bps_text 25` validates. `_once` (normalised) counts only the second 25, and the raw adjacency matches the first.
- Does it predate this change? The raw reads do, but they were not reachable before. At 7fdddbf all three quotes are refused `quote not found on financial page:5`, because `_squash` matching made the raw quote equal the page up to whitespace. The probe runs the 7fdddbf file side by side to show this. The class is therefore introduced by this round's (mandated) `on_page` widening and belongs in this task, not with the owner.
- Fix, per work/build/stage1/quote-normalise-brief.md: run these reads on `normalise(ref["quote"])`, test-first with the three probe cases, adding no new wording.
- The implementer's `Not verified:` line named these reads, but not that they are now reachable.

**L1 (Low): the alphanumeric guard's lowercase half is untested** (cp2e.py:509).
- Probe: mutant `guard_upper_only`, which changes `[A-Za-z0-9]` to `[A-Z0-9]`, SURVIVES in `.../cp2e-r10-review/mutants_review.sh`.
- No test has a lowercase letter directly before `-` and a digit. `1-December` does not exercise the guard at all, because its hyphen follows the token.
- `.../cp2e-r10-review/p_truncated_sign.py` shows `x-25` validates correctly today. Add a case such as `mid-25` to `test_round10_non_sign_forms_still_validate`. This can ride with the M1 fix.

**I1 (Info, for LEAD; a gap in the rule, not in this implementation): the sign is read on the quote only.**
- A quote that starts at the digit (`25 percent of EBITDA.` cut from a page's `−25 percent of EBITDA.`, or `25) percent ...` from `(25) percent`) is a contiguous substring, so `quoted` accepts it. The unsigned `percent_text 25` then validates.
- Probe: `.../cp2e-r10-review/p_truncated_sign.py`, exit 1.
- This applies to all four owners in the class. The fix would be a rule change, such as reading the character before the quote's match on the page.

**I2 (Info, predates this change): `_once`'s "exactly once" (cp2e.py:515) is not pinned by any test.**
- Mutant `count_ge_one` (`== 1` to `>= 1`) SURVIVES in `mutants_review.sh`. The comparison is unchanged by this diff, so per the global rules this goes to the owner, not into this task.

## Probe exit codes (scratch `<S>` = /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad)
- `<S>/cp2e-r10/mutants_r10.sh` (implementer's, rerun): exit 0, 7 of 7 killed.
- `<S>/cp2e-r10-review/mutants_review.sh`: exit 2, 11 mutants from full rsync copies with PYTHONDONTWRITEBYTECODE=1.
  - Killed: guard_letters_only, guard_digits_only, plus_is_sign, norm_minus_only, paren_close_offset, paren_open_offset, paren_bracket, on_page_args_swapped, a4_ne_only_floor_test.
  - Survived: guard_upper_only (L1) and count_ge_one (I2, predates).
- `<S>/cp2e-r10-review/p_raw_after_normalised.py`: exit 1 (M1). It reads the old file from `<S>/cp2e-r10-review/old/cp2e_7fdddbf.py`.
- `<S>/cp2e-r10-review/p_truncated_sign.py`: exit 1 (I1, plus the L1 sanity check).

## Gates (target root, .venv binaries)
- pytest tests/test_method_cp2e.py: 100 passed, exit 0.
- ruff check: exit 0.
- ruff format --check: exit 0.
- `MYPYPATH=src mypy --strict` on both files, cache in `<S>/mypycache-r10rev`: exit 0.
- The target's working tree is clean at c050f57.

Not verified: I ran no tests outside tests/test_method_cp2e.py, so nothing checked `readiness.citation_issues` end to end on the M1 quotes; acceptance there is inferred from it calling the same `quoted`. I did not probe the hyphen-wrap join (`-\n`) interacting with the sign reading. I did not exercise Fact assembly, rendering or a settled run. The implementer's `probe3.py` and `probe_new_strings.py` were not rerun.
