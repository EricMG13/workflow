# CP-1D owner fix review (mx-adversary)

**CP-1D owner fix 0ef0e32 (base 3f3eba4): adversarial review**

**Verdict: REQUEST CHANGES.** One Medium finding: the ruled class (a) is not fully closed.

All probes are saved in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp1d-owner-fix-review/` (called `<R>` below). I edited nothing, and the worktree is clean at 0ef0e32.

**Gates**
- pytest (test_method_cp1d.py and test_defect_classes_selfcheck.py): exit 0, 693 passed, 1 skipped.
- p4_unicode_digits.py on the worktree: exit 0. All 3 lines are refused.
- p9_run_in_word.py on the worktree: exit 0. All 3 lines are refused.
- p5_frozen_compare, using my own dump of a `git archive 3f3eba4` tree against the fix: exit 0, moved 0. My new dump is byte-identical to the implementer's p5_new.json.

**Findings**

**M1 (Medium; predates 3f3eba4 but falls inside ruling (a)).** A Unicode numeral with no digit value is still unseen.
- `isdigit()` and `unicodedata.digit` both miss 1,114 numeric code points: No 787, Nl 236, Lo 91. Examples are ½, ¼, ⑩, Ⅻ, 〇 and 一二.
- On the real a01 path:
  - `"A saving of 2½."` composes `T1D.2.a01.basis = 2`, but the page figure is 2.5.
  - `"A saving of 1.5 and ½ more."` composes 1.5. That is a two-figure quote, exactly the harm in (a).
  - ⑩, Ⅻ, 〇 and 一二 as a second figure also compose 1.5.
- So the report's claim "any non-ASCII digit fails" holds only for characters Unicode classes as digits.
- Probes: `<R>/a1_residual_bypass.py` (exit 1) and `<R>/a3_digit_clauses_equiv.py`.
- Feasible remedy: `char.isnumeric()`. It agrees with `unicodedata.numeric(c, None) is not None` on every code point and is a strict superset of both current clauses. In a scratch copy, `<R>/a5_remedy_check.py` gives exit 0 (693 passed) and p5 moved 0. Add a test row such as `"A saving of 2½."`.

**L1 (Low; predates).** An invisible or combining character between a letter and the run hides the letter.
- `"The Q​1.5 saving"` composes 1.5, and so do the same line with ZWJ, WJ or BOM in place of U+200B. A combining acute (`"Qué" + "1.5"`) and a trailing combining macron also compose.
- The soft hyphen is already closed, because `normalise` removes it.
- This only happens if the page itself carries the character.
- Remedy: count a Cf, Mn or Me character next to the run as touching. This is verified in the same scratch copy (green, frozen moved 0). It can ride with the M1 fix.
- Probe: `<R>/a1_residual_bypass.py`.

**L2 (Low; test strength).** Each new clause, reverted on its own, is killed: the non-ASCII clause off, the ASCII guard off, the before-check off, the after-check off, and both slice perturbations.
- Two mutants survive:
  - `before.isalpha` changed to `before.isupper`: no row has a lowercase letter before a run, such as `x2.5`.
  - `after.isalpha` changed to `after.islower`: no row has an uppercase letter after a run, such as `2.5M`.
- Probe: `<R>/a4_clause_mutants.py` (exit 1 only because of these two).

**I1 (Info).** The two digit clauses are equivalent. They disagree on 0 code points (Python 3.13.15, UCD 15.1.0), so one is dead code. Both are redundant once `isnumeric()` is used. Probe: `<R>/a3_digit_clauses_equiv.py` (exit 0).

**I2 (Info).** Circled and squared letters (ⓠ, 🄰; category So) are not caught by `isalpha`, and they compose. These are exotic.

**I3 (Info; per ruling, not a defect).**
- Rule W forms next to a letter compose 1.5: `Q-1.5`, `Q- 1.5`, `1.5-Q`, and the wrapped `Q-\n1.5`. This matches the pinned accepted row `S-1.80`.
- The parenthesis forms read as negative and get the bounds text.
- Both readings: the letter check behaves the same in each, because the wrap keeps the hyphen. The "first reading only" mutant is equivalent.

**I4 (Info; over-refusal).**
- Now refused: `£2.5m`, `1.8bn`, `2.5x`, and any superscript, for example `m²`.
- No frozen quote or oracle page uses these forms. The pages print bare figures, and the only frozen basis, `...saving of 1.80.`, is still accepted.
- The pinned recipe text `expected.json $.refusal_rules.partly_supported` does not describe the two new refusals. That belongs with the existing backlog row for the CP-1D recipe text (LEAD release).

**Attack results that passed**
- Runs split by a non-ASCII separator are all refused: thin space, narrow NBSP, Arabic thousands and decimal separators, middle dot, U+200B inside the run, apostrophe grouping.
- Characters in Nd, and in No with a digit value, are all refused: mathematical bold, Devanagari, subscript, circled 1.

**Implementer's claims checked**
- Frozen moved 0: verified.
- Two equivalent survivors: verified.
- Three older survivors predate the change: verified. All three survive on 3f3eba4; probe `<R>/a6_old_survivors_on_base.py` (exit 0).
- Issue wording: the diff does not touch it. It is pinned in `expected.json` lines 284 and 350 and by the `EXACTLY_ONE` equality in the tests.
- I found no stub, fake value or catch-all in the diff.

Not verified: the full test suite, ruff and mypy (not rerun by me); Python builds with a different Unicode database version; a real PDF extraction producing U+200B or decomposed accents (L1's likelihood); the model-facing builder text at line 1025.
