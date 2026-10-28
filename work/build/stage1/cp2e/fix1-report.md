# CP-2E fix round 1 report (round 10 review M1 and L1)

M1 and L1 are fixed and committed as **`a1b50c8`** on `worktree-agent-a219254fe68cc1c2d`. One deviation: Step 0's ff merge was impossible, so I used a plain merge (details below). 105 tests pass, all gates exit 0, and every mutant is killed except `count_ge_one`, which the brief permits.

## Step 0 deviation
- `git merge --ff-only claude/module-dev-status-review-0981b6` was refused. The lane tip is now `e0d527a` (it was `82a0070` when I first checked), and it does not contain my round 10 commit `c050f57`, so a fast-forward can't happen. That fits: round 10 for CP-2E came back CHANGES REQUIRED and was never merged into the lane.
- `git merge-tree` showed the merge was clean, and the lane's copies of my two files are still at `7fdddbf`. So I ran a plain `git merge`, giving merge commit `5b406c4`, with no conflicts.
- HEAD therefore contains lane tip `e0d527a` but is not equal to it. Nothing outside my two files was touched.

## Findings and their tests
Each M1 test failed before the fix for the reported cause. The fix is in `src/deploy_workflow/owners/cp2e.py`, with no new wording.
- **M1-A, `code`:** the currency-code search now reads `normalise(ref["quote"])`.
  - Test: `test_m1_code_is_read_on_the_normalised_quote`. `EUR­IBOR` with `code_text EUR` now gets `fx.debt_currency: code_text EUR does not occur in the quote`.
- **M1-B, E5/E8 rate phrase:** `_RATE_PHRASE.findall` now reads the normalised quote.
  - Test: `test_m1_rate_phrase_is_read_on_the_normalised_quote`. A hidden `fi­xed rate` stem now gets `rate_exposure.rate_basis: the quote states neither a floating nor a fixed rate`.
- **M1-C, `labelled` adjacency:** the label regex now runs on the normalised quote instead of `_squash`.
  - Test: `test_m1_label_adjacency_is_read_on_the_normalised_quote`. `spread 25­0` with `bps_text 25` now gets `rate_exposure.spread: bps_text 25 is not labelled spread in the quote`.
- **M1-D, the `reference_rate in quote` check:** it now uses the same normalised quote.
  - Test: `test_m1_reference_rate_is_read_on_the_normalised_quote`. `SO­FR` validates, because the page names SOFR. Before the fix this was a false refusal.
- **Clean-up:** `_squash` had no callers left, so it is removed.
- **Not changed, `row`:** statement-row reads compare the raw quote with raw page lines exactly, so a hidden character fails "not a whole page line". The class can't occur there.
- **L1 (riding Low):** `mid-25` (a lowercase letter before the hyphen) is added to `test_round10_non_sign_forms_still_validate`. It passed already, because the code was correct; it is there to kill `guard_upper_only`, and it does.

## Probe and mutant exit codes
All mutants run from full rsync copies with `PYTHONDONTWRITEBYTECODE=1`.
- **`<S>/cp2e-r10-review/p_raw_after_normalised.py <root>`:** exit **0** (it was 1 before the fix). Cases A, B and C each get their pinned refusal while `quoted` still accepts the quote.
- **`<S>/cp2e-r10-review/mutants_review.sh`:** exit **1**. 10 of 11 are killed, including `guard_upper_only`. Only `count_ge_one` survives; that is I2, which the brief allows to survive.
- **`<S>/cp2e-r10/mutants_r10.sh`:** exit **0**, 7 of 7 killed. One of those kills no longer means anything: since `_squash` was removed, `on_page_squash` fails with a NameError rather than reverting the behaviour. `on_page_args_swapped` in the reviewer's runner still checks `on_page` properly, and is killed.
- **`<S>/cp2e-r10/mutants_fix1.sh`:** exit **0**, 5 of 5 killed. This is a new runner that reverts each M1 read to the raw quote (`m1_code_raw`, `m1_labelled_raw`, `m1_rate_phrase_raw`, `m1_reference_rate_raw`) plus `l1_guard_upper_only`.

## Gates
- `PYTHONPATH=src …/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_method_cp2e.py`: **105 passed**, exit 0.
- `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both files: all exit 0.
- No gate failed on its first run.

Not verified: I1 (a quote cut at the digit drops the page's sign; that goes to LEAD) and I2 (`_once` `== 1`; that goes to the owner); `readiness.citation_issues` end to end on these quotes; the hyphen-wrap join (`-\n`) interacting with the sign reading or the new normalised reads; Module/Fact assembly; rendering; any settled run.

Ledger line:
`2026-10-28T15:02Z cp2e-stage1-fix1 pytest tests/test_method_cp2e.py exit=0 105 passed 0 failed agent=general-purpose(opus) fix-rounds=1 gates-first-pass=y`
