# CP-8 round 10 report (figure signs in quote readers)

`_token_once` and `_labelled` now read figure signs, committed as `dae85ed`, test-first. All 175 tests pass, all three gates exit 0 first time, and every mutant is killed.
- **Commit:** `dae85ed` "feat(cp8): read figure signs in quotes (LEAD round 10 item 1)", ending with the Co-Authored-By line.
- **Base:** `fa55df5`, left unchanged.
- **Files:** `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a3cc9818386e8861a/src/deploy_workflow/owners/cp8.py` and `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a3cc9818386e8861a/tests/test_method_cp8.py` only.

## Step 0
- `git merge claude/module-dev-status-review-0981b6` gave merge commit `2806635`, up to lane tip `44f6c0c`, which contains `7fdddbf` and round 10. There were no conflicts.
- No sha moved and none was re-pinned; no case or frozen file is touched.

## Change (`cp8.py`)
- **Sign pattern:** `_SIGN = r"(?<![A-Za-z0-9])-"`.
- **`_token_once`:** the pattern is now ``rf"(?<![0-9.])(?<!{_SIGN})(?!(?<=\(){v}\)){v}(?![0-9]|\.[0-9])"``.
  - It adds the ruled lookbehind after `(?<![0-9.])`.
  - The parenthesis reading skips a value with `(` directly before it and `)` directly after it.
  - A signed or parenthesised printing therefore does not count. The pinned `observations[<i>]: value_text <v> does not occur in the quote` and `thesis.downside_sizes[<i>]: level_text <l> does not occur in the quote` fire at their existing positions.
- **`_labelled`:**
  - `_MULTIPLE = rf"(?:{_SIGN})?[0-9]+\.[0-9]+x|\([0-9]+\.[0-9]+\)x"`
  - `_DECIMAL = rf"(?:{_SIGN})?[0-9]+\.[0-9]+|\([0-9]+\.[0-9]+\)"`
  - So `-1.80x against 1.80x` and `(1.80)x against 1.80x` get the pinned `… value_text 1.80 is not labelled total_leverage in the quote`. The same holds for `bid -98.00 against 98.00` and `loan_bid`.
  - `(98.00 percent of par)` is unaffected.
- **Interpretation (mine):** the brief gives no form for a parenthesised multiple. I read it as `(1.80)x`, since `)` must directly follow the last digit. Under the rule `(1.80x)` is not a sign.
- **No new string.** Both `_norm` callers already pass the normalised quote, so U+2212 and the en dash arrive as `-`.

## Tests

Red came first, for the reported cause: 17 failed before the change. Today's behaviour was:
- the signed figure validated;
- or the sign was counted as a second occurrence;
- or the size check got the statement issue instead of the token issue;
- or `as -N` counted.

| Test | What it checks |
|---|---|
| `test_r10_a_signed_observation_figure_does_not_occur` | `observations[4]` (multiple) and `observations[6]` (bid) get "does not occur". |
| `test_r10_a_signed_first_figure_after_the_label_is_not_the_value` | The same two observations get "is not labelled". |
| `test_r10_a_signed_size_level_does_not_occur` | `downside_sizes[0]` gets "does not occur". |
| `test_r10_a_dash_that_is_not_a_sign_still_validates` | `1.75-1.80x`, `S-1.80x` and `+1.80x` validate `()`. |
| `test_r10_the_rules_non_signs_are_read_unsigned` | `1-December`, `2024-2025`, `95-96` and `S-350` read unsigned; `as -N` does not. |
| `test_r10_a_parenthesis_around_a_unit_is_not_a_sign` | `(4.30 percent)` and `bid (98.00 percent of par)` read as figures; `bid (98.00) or 98.00` is not labelled. |

- The first three tests run each of U+2212, ASCII `-`, en dash and `(N)`.
- The new `edited()` helper applies the same edit to the page (hash recomputed) and to the literal.
- Every frozen case and pinned refusal passes unchanged.

## Mutants

`/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp8-r5/mutate_r5.py` exits 0.
- It runs from a full temporary copy, now with `PYTHONDONTWRITEBYTECODE=1`, a baseline check and a control mutant.
- All 59 mutants are killed, plus the control.
- The 8 new round 10 mutants:
  - the token minus reading reverted;
  - the token parenthesis reading reverted;
  - the token taking any dash as a sign;
  - `_SIGN` without its lookbehind;
  - the `_MULTIPLE` minus reading reverted;
  - the `_MULTIPLE` parenthesis reading reverted;
  - the `_DECIMAL` minus reading reverted;
  - the `_DECIMAL` parenthesis reading reverted.

## Gates (both files)

All exit 0 on the first run.

| Gate | Exit |
|---|---|
| `ruff check` | 0 |
| `ruff format --check` | 0 |
| `MYPYPATH=src mypy --strict` | 0 |
| pytest (`../../../.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_method_cp8.py`) | 0, 175 passed |

## Prose
No new issue or claim string was added, so nothing new went through `prose.issues` or `bare_figures`.

## Stage 2 notes (methods/cp8.md, not written)
- **The sign rule.** A figure read from a quote is the signed numeral the normalised quote prints.
  - A `-` is a minus sign when it starts the quote or follows a character that is neither a letter nor a digit.
  - Accounting `(N)` reads as negative; `+` is ignored.
- **The unsigned-grammar limitation.** CP-8 cannot record a negative net leverage or a negative bid or offer; such a figure fails closed with "does not occur".

Not verified: LEAD's `p_sign_rule.py` and `p_signed_frozen.py` were not re-run against this build (the frozen cases are covered by the test file only); no `<S>/cp8-r10/` probe was written; the default-statement and decision-text readers were not changed or tested for signs (no figure is read there).

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y
