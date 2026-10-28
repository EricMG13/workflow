## CP-3D round 10 (figure signs in quote readers): commit `a1de97d` on `claude/cp3d-stage1`

I applied the round 10 sign rule to CP-3D, writing the tests first. All gates passed first time and all five new-reading mutants are killed.

**Step 0:** `git merge --ff-only claude/module-dev-status-review-0981b6` moved the worktree from 0b0835f to 7fdddbf with no conflict. The merge did not touch the CP-3D files, and no pinned sha moved, so nothing was re-pinned. The commit changes only `src/deploy_workflow/owners/cp3d.py` (+14/−3) and `tests/test_method_cp3d.py` (+120).

**Change:** the fix is in `_token_once` in `src/deploy_workflow/owners/cp3d.py`. It still reads `normalise(quote)`.
- It adds the ruled lookbehind `(?<!(?<![A-Za-z0-9])-)` after `(?<![0-9.])`.
- It adds the parenthesis reading: a match with `(` directly before it and `)` directly after it does not count as an occurrence.
- `_labelled` is unchanged. No new string was added; every issue is an existing pinned frame.
- This covers `level_text` (bid, offer and talk), `margin.bps_text`, `amortisation.value_text` and `reference_rate.level.percent_text`.

**Rulings and their tests (all in `tests/test_method_cp3d.py`):**
- **Round 10 item 1, minus sign, and the Parentheses ruling:** `test_r10_unsigned_text_against_a_signed_figure_does_not_occur`. That is 6 readers × 4 forms (U+2212, ASCII `-`, en dash, `(N)`), 24 cases.
  - Each one gets exactly the pinned `<key>: <label> <text> does not occur in the quote`, at the occurrence check.
  - Red before the fix, for the reported cause: bid and offer got `… is not labelled bid/offer in the quote` (one check too late). Talk, margin, amortisation and reference rate validated.
- **Non-sign forms still validate:** `test_r10_non_sign_forms_still_validate`.
  - `95-96`, and `95–96` with an en dash, for talk `96`.
  - `S-350` for margin `350`.
  - `+425` (the `+` is ignored).
  - `(set at 425)`, where only the `)` is adjacent.
  - `(4.30 percent)`, where only the `(` is adjacent.
- **`2024-2025`:** `test_r10_a_hyphen_after_a_digit_leaves_the_token_to_its_shape_check`. The `2025` occurs and gets the existing shape issue. No CP-3D field can hold a four-digit value, so this case cannot validate.
- **`1-December` was not tested.** Its hyphen follows the digit, so the lookbehind never sees it. Only the existing trailing lookahead applies.
- **Signed analyst text keeps its old refusal:** `test_r10_signed_analyst_text_keeps_its_refusal`. `-98.50` gets "is not a decimal number". `-425`, `-0` and `-4.30` get the shape issue.
- **Frozen cases:** every earlier test passes unchanged, 234 before and 269 after. There are no oracle edits.

**Probes:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3d-r10/mutants_r10.py` exits 0. It runs on a full temporary copy with `PYTHONDONTWRITEBYTECODE=1`.

| Mutant | Exit | Killed by |
|---|---|---|
| control | 0 | — |
| minus lookbehind removed | 1 | the 18 dash cases |
| lookbehind reduced to `(?<!-)` | 1 | the `95-96`, `95–96`, `S-350` and `2024-2025` cases |
| parenthesis reading removed | 1 | the 6 parenthesis cases |
| the reading checks only the `(` | 1 | the `(4.30 percent)` case |
| the reading checks only the `)` | 1 | the `(set at 425)` case |

**Gates, all exit 0:**
- pytest on `tests/test_method_cp3d.py`: 269 passed.
- `ruff check` on both files.
- `ruff format --check` on both files.
- `MYPYPATH=src mypy --strict` on both files.

**Prose and bare-figure hits:** none. No new string was added, so nothing went through `prose.issues` or `bare_figures`.

**Stage 2 notes for `methods/cp3d.md` (listed, not written):**
1. The sign rule: a figure is the signed numeral the quote prints, read on `normalise(quote)`. The pattern is `(?<![A-Za-z0-9])-`, a `+` is ignored, and `(N)` reads as negative.
2. The unsigned-grammar limitation: CP-3D cannot record a negative reference rate, or any other negative figure. It fails closed with "does not occur".

GitNexus `detect_changes` was not run; I have no MCP tools for it.

Not verified: no full suite or Stage 2 run, per the rules. No frozen-quote probe of my own: frozen coverage rests on the existing oracle tests and LEAD's `p_sign_rule.py`. A signed analyst text inside parentheses, such as `(-425)`, was not tested; it gets the "does not occur" issue rather than the shape issue. The mx-precise review is pending.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y
