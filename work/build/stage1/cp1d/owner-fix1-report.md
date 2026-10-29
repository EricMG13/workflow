# CP-1D owner fix round 1 report (mx-feature)

Fix round 1 is committed as a1aa19d on claude/cp1d-owner-fix, on top of 0ef0e32. It covers the original brief plus both later LEAD messages (letter-after restored; addendum 5 ordinal and identifier rules). Only cp1d.py and test_method_cp1d.py changed, and the issue wording is unchanged. `<R>/a4_clause_mutants.py` could not be run against the new code. It matches the old source text, so it fails on its own assertion before any mutant runs.

**Rules in `_one_whole_run`**
- **M1.** Any character outside `0-9` with `isnumeric()` now fails. This replaces both digit clauses. Red-first rows cover `2½`, `½`, `⑩`, `Ⅻ`, `〇` and `一二`.
- **L1.** The new `_touches_before` helper is the single revertable seam for the before-rule. It treats a letter, or a Cf/Mn/Me character, directly before a run as touching it. Rows cover U+200B, ZWJ, WJ, BOM, decomposed `Qú` (combining acute) and Me U+20DD. `Q2`, `A1` and `FY25` alone stay refused.
- **After a run.** No letter after a run is checked any more, so `2.5m` reads 2.5, `25bps` reads 25 and `2.5M` reads 2.5.
  - The `2.5M` row moved from refuse to accept.
  - A real-path test pins the amounts read for these.
  - `25bps` also gets a bounds issue, which is not the exactly-one text.
- **Ordinals (addendum 5).** `_ORDINAL_AFTER` is `(?:st|nd|rd|th)(?![^\W\d_])` with IGNORECASE, matched at the run end. `The 2nd saving.`, `The 21ST saving.`, `The 3rd saving.`, `The 4Th saving.` and `The 2nd.` are refused through the real path. `2nds`, `2.5x` and `2.5M` still read.
- **L2.** The `x2.5` row kills the isupper mutant, and the `2.5M` accept row kills the islower mutant.

**Exit codes**
- a1: 0.
- a3: 0.
- p4: 0.
- p9: 0.
- p5_frozen_compare: 0 (19 refusals and 3 cases, moved 0; the dump holds one frozen basis quote, and it is still accepted).
- Gates: pytest on the two files (730 passed, 1 skipped), ruff check, ruff format --check and `mypy --strict` on both files all exit 0.
- Mutant script `<S>/cp1d-owner-fix/p_r13_mutants2.py`: exit 1, because three mutants survive. All three predate this work and survive the same way on 3f3eba4 (`run no comma join`, `run no comma-space join`, `one reading only`).
  - 16 new mutants are all killed. They cover the numeric clause off, the ASCII guard off, `numeric->digit`, the before-seam off, the before slice, the isupper and islower swaps, no Cf, no Mn, no Me, the ordinal clause off, each of `st`, `nd`, `rd` and `th`, case-blind off, no letter-after-suffix guard, not anchored at the run end, and letter-after refused.
  - The ordinal-clause and "no letter after the suffix" mutants you asked for are among them. The Me mutant needed an extra row (U+20DD), which I added.

**Cost**
- `2nd`, `21ST`, `3rd`, `4Th` and `2.5th` are refused, so `The 2nd saving.` gives the pinned exactly-one issue.
- Identifier runs (`Q2`, `A1`, `FY25`, and anything with a letter or Cf/Mn/Me directly before the figure) are refused.
- Any non-ASCII numeral anywhere in the quote is refused.
- A Month D, YYYY date is still refused, which predates this work.

**Not verified:** `<R>/a4_clause_mutants.py`, which I did not run against the new code, because its source-matching strings fail on it; my mutant script stands in. I did not test the ordinal regex under IGNORECASE for odd Unicode case-folds (such as the long s), which would only fail closed. Cf, Mn and Me after a run are deliberately not checked. Circled and squared letters (the reviewer's I2 case) are not caught, and I did not test them. I did not run the full suite, other owners, or the recipe text in `expected.json`.

agent=mx-feature fix-rounds=1 gates-first-pass=y
