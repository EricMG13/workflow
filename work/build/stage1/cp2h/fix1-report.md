# CP-2H fix round 1 report

F1–F4 are fixed and committed as **87f2d9d**. The test file now has 171 tests and all pass (1.34 s). All 29 refusal mutants are still killed. The ten mutants left alive are the two equivalents and four LEAD/Stage 2 items the review already named, plus the four C20, C21, C45, C50 mutants whose code sites the fix rewrote. Two of the reviewer's probes don't run cleanly against the new grammar:
- **p02** exits 1 because it uses a threshold form the new grammar refuses, not because of a rounding fault.
- **p01** exits 0 because it now refuses every form it tries, which is the intended result.

## Step 0: merge
`git merge claude/module-dev-status-review-0981b6` was clean (merge a7b135b). The merge parent `HEAD^2` is 53f30d7, which equals the lane tip. The merge brought no changes to the oracle, CP-2H or CP-2G files. Before the fix, the 154 existing tests passed.

## Findings and the tests that cover them
I wrote the tests first:
- The F1 grammar tests failed red, with `DID NOT RAISE SourceIssue`.
- The F3 test failed red: the stored value was `…456.79` instead of `…456.789`.
- The F2 and F4 tests describe behaviour that was already correct, so they passed before the fix. Their job is to kill the mutants.

| Finding | Change | Test |
|---|---|---|
| F1 (Q1) | `_THRESHOLD` is now `[0-9]+\.[0-9]{2}x\|[0-9]+\.[0-9]%`. Any other form gets `Trigger terms not found`. | `test_threshold_grammar[...]`, 10 forms: `4x`, `2.7x`, `2.755x`, `10%`, `10.05%`, a 30-place percent, `-2.75x`, `+2.75x`, `2,75x`, fullwidth digits |
| F3 (Q2) | The percent threshold is converted with an exact exponent shift, `Decimal((sign, digits, exp - 2))`, with no rounding context. | `test_percent_threshold_is_an_exact_shift`: `1234567890123456789012345678.9%` stores exactly as `12345678901234567890123456.789` |
| F2 | none | `test_issue_order_on_one_payload`: the 19-issue p06 order on one payload |
| F4 C25, C26 | none | `test_unsettled_reasons_take_the_first_year`: mixed missing and not_applicable years, both orders; the tightest headroom, tightest year and T2R.6 |
| F4 C27 | none | `test_root_reason_puts_the_threshold_first` |
| F4 G1 | none | `test_publication_dates_are_read_from_the_lines`: March 3, 2026 and February 29, 2024 |
| F4 C45, C46 | none | C45 is covered by `test_threshold_grammar[minus]`; C46 by `test_scale_position_sign_is_refused` |
| Info C47, C48 (optional) | none | `test_input_invariants`: a wrong CP-2G unit raises; a CP-1 fact with the same label from table `T4.9` is ignored |

## Mutation runners
`runner.py` ran each spec on a full temporary copy with `PYTHONDONTWRITEBYTECODE=1`. The canary failed the run as it should, so each run was mutating the copy.

**`spec_refusals.py`: 29 of 29 killed, exit 0.**

**`spec_other.py`: 44 of 50 killed, exit 1.** C25–C35 and C46–C48 are now killed. The six not killed:
- **C20, C21, C45, C50: the code site no longer exists.** F1 and F3 rewrote the old regex and the `scaleb(-2)` line. I retargeted C20, C45 and C50 at the new code in `spec_fix1_retarget.py`. C21's site is also gone; it was already rated equivalent.
- **C44: equivalent**, as the review says.
- **C49: a Stage 2 item for LEAD (B6).** It mutates the `str` current path.

**`spec_more.py`: 1 of 4 killed, exit 1.** G1 is killed. G2, G3 and G4 survive; these are B5 and B6, out of scope this round.

**`spec_fix1_retarget.py`: 5 of 5 killed, exit 0.** It covers:
- C45′: the leading minus;
- C50′ and C50″: any number of decimal places, and the old optional-point grammar;
- F3′: `scaleb(-2)` in the default context;
- C20′: a one-place shift.

## Reviewer probes
- **p01: exit 0.**
- **p02: exit 1.** This is expected. p02 feeds `_threshold` a 30-place percent, which F1 now refuses as `Trigger terms not found`. The F3 test covers the same rounding risk with a valid `N.N%` value longer than 28 digits.
- **p03, p06, p09, p12: exit 0.**

## Gates
All four exit 0 on the first run after the fix:
- pytest on `tests/test_method_cp2h.py`: 171 passed;
- `ruff check` on both files;
- `ruff format --check` on both files;
- `MYPYPATH=src mypy --strict` on both files.

## Files
- `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a52b5ec0919986ddb/src/deploy_workflow/owners/cp2h.py`
- `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a52b5ec0919986ddb/tests/test_method_cp2h.py`
- Probes and logs: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2h-r6h-8/` (`run_fix1.py`, `run_probes.py`, `spec_fix1_retarget.py`, `fix1_*.log`, `fix1_*.json`).

Not verified: the builder still uses the looser threshold pattern and the 28-digit `scaleb` (B1, a builder sync for LEAD); the B2–B6 items (block truncation, blank limitation, first-year lineage, T2R.1 status sources, stale-issue order and wording) are not tested this round; the full suite was not run (only this test file).

agent=general-purpose(opus) fix-rounds=1 gates-first-pass=y
