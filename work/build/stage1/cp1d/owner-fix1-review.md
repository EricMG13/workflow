# CP-1D owner fix round 1 re-review (mx-adversary)

**CP-1D fix round 1 (a1aa19d on 0ef0e32): scoped re-review**

**Verdict: APPROVE.** No High or Medium findings. Everything below is Low or Info and can ride with the end batch. I edited nothing, and the worktree is clean at a1aa19d.

Probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp1d-owner-fix-review/` (called `<R>` below).

**Exit codes**
- pytest on the two files: 0 (730 passed, 1 skipped).
- a1 (`<R>/a1_residual_bypass.py`): 1. Every M1 row and every before-side L1 row is refused. The lines that still compose are all outside this round's rulings:
  - Cf or Mn after the run (L1 is before-side only);
  - circled or squared letters (my earlier I2);
  - the rule W forms (`Q-1.5`, `1.5-Q`, wrapped), which match the pinned accepted row `S-1.80`.
- a3 (`<R>/a3_digit_clauses_equiv.py`): 0.
- p4: 0.
- p9: 0.
- p5 compare: 0. 19 refusals and 3 cases, moved 0; the frozen quote `...saving of 1.80.` still composes 1.80.
- a4b (`<R>/a4b_clause_mutants_r1.py`, which replaces a4 because a4's match strings fit the old source): 0.
- a7 (`<R>/a7_r1_ordinal_identifier.py`): 0.

**The items you asked about**
- **M1: closed.** The fix uses `isnumeric()`, and a3 shows that matches `unicodedata.numeric` on every code point. ½, ¼, ⑩, Ⅻ, 〇, 一二 and `2½` are all refused.
- **L1 before-side: closed.**
  - Refused through the real path: U+200B, ZWJ, WJ and BOM before the run; a Mongolian vowel separator and a tag character (Cf); a combining grapheme joiner and VS16 (Mn); a combining acute; and U+20DD (Me).
- **L2: killed.** The isupper and islower mutants are both killed. Of 23 mutants in a4b, these are also killed:
  - numeric→isdigit and numeric→isdecimal;
  - no Cf, no Mn, no Me;
  - the ordinal check off, unanchored, or matched at the run start;
  - each of st, nd, rd and th removed;
  - case-sensitive matching;
  - no guard against a letter after the suffix;
  - letters after a run refused again.
  - Two survive: "ASCII-only suffix guard", which still fails closed, and "one reading only", which predates 3f3eba4.
- **Addendum 5: matches the ruling exactly.**
  - Refused: `2nd`, `1ST`, `3rD`, `4th.`, `2nd_` and `2nd` followed by a combining mark.
  - Read as 2: `2nds` and `2ndly`. The ruling says "no letter after", so these are correct.
  - Refused as identifiers: `A1`, `FY25`, `x1.5` and `é1.5`.
- **Letter-after: restored without reopening the fail-open.** `1.5m`, `1.5M` and `1.5x` compose 1.5. `Q2`, `A1` and `2nd` stay refused (p9).
- **Wording:** the issue text is untouched.

**Findings**

**L3 (Low; outside the ruling's wording, fail-open in spirit).** Ordinals that are not plain ASCII letters still read as the figure. All of these compose the run as the basis (a7 "note" rows):
- superscript-letter suffixes: `2ⁿᵈ` reads 2, `1ˢᵗ` reads 1;
- fullwidth letters: `2ｎｄ`;
- U+200B or a combining mark between the run and the suffix: `2​nd`, `2́nd`;
- U+200B inside the suffix: `2n​d`.

These all need unusual page text. A possible remedy is to NFKC-fold the suffix window and skip Cf, Mn and Me characters before matching. Whether to extend the ruling is a question for LEAD.

**L4 (Low; test comments).** Two test comments contradict addendum 5:
- the docstring at `tests/test_method_cp1d.py:1279` says "`2nd` reads 2";
- the comment at line 1321 says "an ordinal suffix is a whole run".

**I1 (Info).** The fixer's report gives a1 as exit 0, but a1 exits 1 on a1aa19d. The rows that compose are the per-ruling or out-of-scope ones listed above.

**I2 (Info).** These still compose and the rulings do not name them: an Mc vowel sign before the run (`का1.5`) and circled letters (So).

Not verified: the full suite, ruff and mypy (I did not rerun them); Python builds with a different Unicode database version; how often real PDF extraction produces Unicode superscript-letter ordinals.
