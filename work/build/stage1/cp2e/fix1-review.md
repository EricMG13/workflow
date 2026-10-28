CP-2E fix round 1 re-review (target a1b50c8, fix diff 5b406c4..a1b50c8: 2 files, +74/-9, only cp2e.py and test_method_cp2e.py)

**Verdict: APPROVE.** M1 and L1 are both fixed, no wording was added, and the diff introduces no new High or Medium finding.

Probes are in /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2e-fix1-review/ (called `<F>` below). My copy of the base file is `<F>/cp2e_5b406c4.py`.

## Spec verdict, by finding id

**M1: fixed.**
- All four reads now use `normalise(ref["quote"])`, the same text the `quotes.quoted` match used:
  - `code`: src/deploy_workflow/owners/cp2e.py:542-543
  - the `labelled` adjacency: cp2e.py:555
  - `_RATE_PHRASE.findall`: cp2e.py:610-611
  - `reference_rate in quote`: cp2e.py:617
- Your probe `cp2e-r10-review/p_raw_after_normalised.py <target>` exits **0**. Cases A, B and C each get their pinned refusal: "code_text EUR does not occur", "states neither a floating nor a fixed rate" and "bps_text 25 is not labelled spread".
- **No other raw read after a normalised match.**
  - The remaining quote reads are `_once` (it already normalises, cp2e.py:504) and `row` (cp2e.py:560-580).
  - The implementer's `row` claim holds. `quote.strip() not in lines` (cp2e.py:566) compares the raw quote with raw stripped page lines, so every later `startswith` and `split()[-1]` read is on literal page text.
  - Probe `<F>/p_row_raw_claim.py <target>` exits **0**. It tries a soft hyphen inside the value, a soft hyphen inside the label and collapsed double spaces. `quoted` accepts all three and each gets `earnings.ebitda: quote is not a whole page line`.
  - `inputs_from_submission` (cp2e.py:397-415) reads only submitted fields, never the quote.
- **SOFR is the page's own text, not a widening.** In `test_m1_reference_rate_is_read_on_the_normalised_quote` (tests/test_method_cp2e.py:900-906), the page line literally contains `SOFR`. The quote differs from it only by U+00AD, which `normalise` deletes. The base refusal there was a false refusal.
- **Removing `_squash` changes nothing else.** The label pattern needs `\s+`, so `normalise`'s extra work (mapping dashes, trimming the ends) cannot change a match. The only real difference is deleting U+00AD, which is the intended fix. `_squash` has no callers left in src or tests.
  - Probe `<F>/p_squash_removal.py <target>` exits **0**: 50 quote, label and value combinations, including newlines, tabs, NBSP and CRLF, with no differences.
- `cp2e-r10/mutants_fix1.sh` exits **0**. All four reverts to the raw quote (`m1_code_raw`, `m1_labelled_raw`, `m1_rate_phrase_raw`, `m1_reference_rate_raw`) are killed.

**L1: fixed.** `mid-25` is added at tests/test_method_cp2e.py:795. `guard_upper_only` is killed in `cp2e-r10-review/mutants_review.sh` and `l1_guard_upper_only` in `mutants_fix1.sh`.

**No wording added: holds.** Probe `<F>/p_no_new_wording.py <F>/cp2e_5b406c4.py <target>` exits **0**. The 30 `add(...)` templates are identical before and after the fix, none added or removed.

## Quality verdict
- No stub, fake value or catch-all in the diff.
- **Info, no action:** a side effect of M1 that follows the class method. A page that prints `floating–rate` (en dash), quoted verbatim, now validates as FLOATING. At the base it was refused "states neither". Since `normalise` maps the dash to `-`, which `_RATE_PHRASE`'s `[\s-]+` accepts, the result matches the page's own text. Probe `<F>/p_dash_rate_phrase.py <F>/cp2e_5b406c4.py <target>` exits **0** and shows the base and target results.
- **Info, outside this diff:** `quoted` also matches with hyphen line wraps joined (`_joined`), so "the text the match used" is exactly `normalise` only when the quote has no `-\n` wrap. The class method prescribes `normalise`, and I did not probe the wrap path.

## Mutants
Both runners used full rsync copies with PYTHONDONTWRITEBYTECODE=1.
- `cp2e-r10-review/mutants_review.sh`: exit **1**. 10 of 11 killed. Only `count_ge_one` survives; that is I2 and goes to the owner.
- `cp2e-r10/mutants_fix1.sh`: exit **0**, 5 of 5 killed.

## Gates
Run from the target root with the .venv binaries; the target tree was clean at a1b50c8.
- `PYTHONPATH=src … -m pytest -q -p no:cacheprovider tests/test_method_cp2e.py`: 105 passed, exit 0.
- `ruff check` on both files: exit 0.
- `ruff format --check` on both files: exit 0.
- `MYPYPATH=src mypy --strict` on both files, with the cache in `<S>/mypycache-fix1rev`: exit 0.

Not verified: I ran nothing outside tests/test_method_cp2e.py, so `readiness.citation_issues` was not checked end to end on these quotes. I did not probe the hyphen-wrap (`-\n`) path, where `quoted`'s joined reading differs from `normalise`. I1 (with LEAD) and I2 (with the owner) were not examined. I did not rerun `cp2e-r10/mutants_r10.sh`, whose `on_page_squash` mutant the implementer says now fails as a NameError. Fact assembly, rendering and settled runs were not exercised.
