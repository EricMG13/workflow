**Verdict: APPROVE.** The diff is correct against the ruling, and every spec check passes. I found two Low test gaps (surviving mutants). Neither needs a review round; they can ride with the next fix.

Target: dae85ed, round diff `2806635..dae85ed`. The worktree was clean.

**Checks**
1. **`_token_once`** (cp8.py:397-402) is correct.
   - It reads the normalised quote. The caller passes the normalised quote, as the report says; I did not re-read the callers.
   - The lookbehind `(?<!{_SIGN})` sits right after `(?<![0-9.])`.
   - The parenthesis reading is `(?!(?<=\(){v}\)){v}`. It is measured at the first digit: `(` directly before the value and `)` directly after its last digit.
   - Analyst values are shaped `N.NN`, so a signed analyst text such as `(-1.80)` cannot reach this function. It keeps today's refusal, so the CP-3D L1 problem does not arise here. For the quote `(-1.80)` with value `1.80`, the result is "does not occur", which is the pinned issue.
   - `(1.80, 2.00)`, `(see 1.80)`, `(1.80x)` and `(1.80) and 1.80` all read as expected.
2. **`_labelled`**
   - `_MULTIPLE` and `_DECIMAL` take the prefix `(?:(?<![A-Za-z0-9])-)?` and the parenthesis forms.
   - `total leverage -0.50x and 0.50x` gives False, which is the pinned "is not labelled" issue. The same holds for `bid -98.00 against 98.00` and `bid (98.00) or 98.00`.
   - The implementer reads a parenthesised multiple as `(1.80)x`. That is consistent with "`)` directly after the last digit".
   - `(1.80x)` is left unsigned: `_labelled` returns True.
   - `(98.00 percent of par)` is unaffected.
3. **Issues and frozen cases**
   - No new string is added. The diff only changes regexes, so the pinned issues fire at their existing positions.
   - The new tests assert the exact issue strings.
   - All 175 tests pass, including the frozen cases.
4. **Mutants**
   - The implementer's `mutate_r5.py` exits 0. All mutants are killed, including the 8 new R10 ones.
   - My own mutants, run from a full temp copy with `PYTHONDONTWRITEBYTECODE=1`, gave two survivors.

**Findings**
- **Low-1: a guard-letter-case mutant survives (cp8.py:121).**
  - Changing `_SIGN` to `(?<![A-Z0-9])-` leaves the suite green, so no test uses a lowercase letter before the dash.
  - The same mutant survived in CP-2E.
  - Suggested fix: add `s-1.80x` and a `_token_once("350", "s-350")` case to the non-sign tests.
  - Probe: /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp8-r10-review/mutate_own.sh, mutant `guard-case`.
- **Low-2: a close-only parenthesis mutant survives (cp8.py:401).**
  - Changing `(?!(?<=\(){v}\)){v}` to `(?!{v}\)){v}` also survives. The mutant refuses any value followed by `)`, such as `(see 1.80)`.
  - No test pins "`)` after the digits, but no `(` directly before the value, is still unsigned".
  - Suggested fix: add `_token_once("1.80", "(see 1.80)")` to the parenthesis test. It should be True.
  - Probe: the same `mutate_own.sh`, mutant `paren-close-only`. `p_edges.py` shows the correct behaviour is True.
- **Info:** the implementer's "Not verified" says LEAD's `p_sign_rule.py` and `p_signed_frozen.py` were not re-run. I did not run them either. The test file does cover the frozen cases.
- No stub or fake value, and no catch-all that hides a failure.

**Probes** (all under `<S>/cp8-r10-review/`, where `<S>` is the scratchpad path given in the brief)
- `p_edges.py`: 24 edge checks, exit 1.
  - The one deviation is my own wrong expectation, not a defect. I expected `a --1.80` to be unsigned, but under the ruling the second dash follows a non-alphanumeric character, so it is a sign. The code is right.
  - Every other check passed.
- `mutate_own.sh`: exit 0.
  - The script prints one line per mutant: a pytest exit of 0 means the mutant survived, 1 means it was killed.
  - `guard-case` and `paren-close-only` survived (pytest exit 0).
  - `guard-no-digit`, `guard-no-letter`, `paren-open-only`, `multiple-paren-xinside` and `decimal-paren-loose` were killed.
- `<S>/cp8-r5/mutate_r5.py`: exit 0.
  - It needs the arguments `"$PWD" "<venv python>"`; run bare, it exits 1 with an IndexError.
  - The output is saved at `<S>/cp8-r10-review/mutate_r5.out`.

**Gates** (venv binaries, from the target root)
- pytest on `tests/test_method_cp8.py`: 175 passed, exit 0.
- `ruff check`: exit 0.
- `ruff format --check`: exit 0.
- `MYPYPATH=src mypy --strict` with the cache in scratch: exit 0.

Not verified: LEAD's `p_sign_rule.py` and `p_signed_frozen.py` against this build (the 711 token/quote pairs); the Stage 2 `methods/cp8.md` text (not written); other callers of `_norm` and `_token_once` beyond the tests; and signs in the default-statement and decision-text readers, which read no figure.
