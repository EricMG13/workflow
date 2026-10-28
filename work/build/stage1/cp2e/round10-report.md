# CP-2E round 10 report

Round 10 is applied to CP-2E and committed as **`c050f57`** on `worktree-agent-a219254fe68cc1c2d`. 100 tests pass, the gates exit 0, and every mutant in my runner is killed, including the riding `a4_floor_gt_to_ne`.

## Step 0
- **Merge:** `git merge --ff-only claude/module-dev-status-review-0981b6` fast-forwarded cleanly to `7fdddbf`, with no conflict.
- **Pins:** none moved; the test asserts no oracle sha.

## Rulings and their tests
- **Round 10 §1, figure signs, and the Parentheses ruling (`_once`).**
  - `_once` now reads on `quotes.normalise(quote)`, which maps U+2212 and the dashes to `-`.
  - It counts only unsigned occurrences. Signed means a `-` directly before the figure (lookbehind `(?<!(?<![A-Za-z0-9])-)`) or accounting parentheses with `(` directly before and `)` directly after. A `+` is ignored.
  - An unsigned `*_text` against a signed printed figure now gets the pinned "does not occur" issue at its existing position. No new strings.
  - Tests:
    - `test_round10_signed_share_does_not_occur[minus_sign|ascii_hyphen|en_dash|parentheses]`: each fails before the change and now returns `fx.foreign_ebitda_share: percent_text 25 does not occur in the quote`. That reader was the real gap.
    - `test_round10_signed_labelled_operand_does_not_occur`: `spread −5` gives `rate_exposure.spread: bps_text 5 does not occur in the quote`.
    - `test_round10_non_sign_forms_still_validate`: `1-December`, `95-96`, `S-25`, `2024-2025`, `+25` and `(25 percent)` all still validate. These pass before and after the change; the mutants below prove they guard the rule.
  - `row` and `_row_decimal` are unchanged.
- **Round 10 Stage 1 defect (`on_page`).**
  - It now matches with the product `quotes.quoted`, the function `citation_issues` uses, instead of `_squash`.
  - Test: `test_round10_on_page_uses_the_product_quote_match`. An en-dash basis quote of page:1's hyphenated `1-December` matches; it failed before the change.
- **Riding Low (`a4_floor_gt_to_ne`).**
  - Test: `test_negative_floor_fails_closed`. A directly built floor of −25 must raise `Floor limitation`.
  - It passes before and after the change; the mutant below shows it kills `a4_floor_gt_to_ne`.
  - No `cp2e-r6i-review/` folder exists under `<S>`, so I used my own runner.

## Probes and exit codes
- **`<S>/cp2e-r10/mutants_r10.sh` (new):** exit **0**, 7 of 7 killed. Each mutant runs from a full rsync copy with `PYTHONDONTWRITEBYTECODE=1`. The mutants are:
  - `once_no_normalise` (reading on the raw quote);
  - `once_no_sign_lookbehind`;
  - `once_any_hyphen_is_sign` (dropping the alphanumeric guard);
  - `once_no_parentheses`;
  - `once_open_paren_only`;
  - `on_page_squash` (reverting to `_squash`);
  - `a4_floor_gt_to_ne`.
- **`<S>/probe3.py`:** exit 0. The oracle claims are equal and the frozen tokens agree.
- **`<S>/cp2e-r6/probe_new_strings.py`:** exit 0, no hits.

## Tests and gates
- **Tests:** `PYTHONPATH=src …/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_method_cp2e.py` gives **100 passed** in 1.63 s, exit 0. Every frozen case passes unchanged.
- **Gates:** `ruff check` 0, `ruff format --check` 0, `MYPYPATH=src mypy --strict` on both files 0, all on the first run.

## For LEAD and Stage 2
- **Prose and bare-figure hits:** none. This round adds no strings.
- **Stage 2 note:** the sign rule (signed numeral read on the normalised quote, minus lookbehind, accounting parentheses, `+` ignored, `row` keeps its own grammar) belongs in `methods/cp2e.md`. Listed, not written.

Not verified:
- `labelled`'s label-adjacency regex still uses `_squash`. Its `_once` check now runs first on the normalised quote, so a label written with a mapped character is not tested.
- Other quote checks still read the raw quote, and no test covers mapped characters in them: `code` (the currency code) and the E8 rate phrase.
- Module/Fact assembly with real Citations; inherited limitations; `RULES`, tool-use refusals, tamper and probe; rendering; any settled run.

Ledger line:
`2026-10-28T14:52Z cp2e-stage1-round10 pytest tests/test_method_cp2e.py exit=0 100 passed 0 failed agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y`
