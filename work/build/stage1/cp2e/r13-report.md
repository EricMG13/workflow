CP-2E round 13 is done and committed as `ccdeeeb` on `claude/r13-cp2e`. The change is in `src/deploy_workflow/owners/cp2e.py` and `tests/test_method_cp2e.py` only. The gates pass and all 8 mutants are killed. Two LEAD probes exit 1; both failures come from probe expectations that assume other code (below).

**Step 0.** The worktree was clean at bb0190e, and `git merge --no-edit claude/r13-cp3d` went through (merge commit 5fa075e). Before my change, `tests/test_method_cp2e.py` showed 484 passed and 1 red: `test_class_reference_rate_text[w-minus-wrap-text]`. The `b3-*` text cases were already green. They are refusals, so the old code satisfied them.

**Item 8 (R3 M4).**
- **Code:** `_unsigned` adds the lookbehinds `(?<![0-9],)(?<![0-9], )` and the trailing guard `(?![0-9]|[.,][0-9]|, [0-9])`. Rule W is kept.
- **Tests:** `test_round13_comma_join_before_the_figure_in_the_quote`, `..._at_the_page_edge` and `test_round13_comma_join_after_the_figure`. They cover `1,25`, `1, 25` and `1,\n25`, in a quote and at a page edge. The before-the-figure tests run through the share reader and the spread (labelled) reader. The after-the-figure test uses the share reader only.
- **Twins:** `test_round13_comma_twins_with_a_letter_stay_figures` covers `25, a` and `up, 25`, both accepted.

**B3 exemption (addenda 1 and 3).**
- **Code:** `_split` now exempts a `"- "` in `normalise(value)` that matches W's minus, `(?<![A-Za-z0-9])- (?=[0-9])` (new `_W_SIGN`), only when its index is above 0. Any other `"- "` still gets the existing issue. This matches CP-3D's `_name_occurs`.
- **Tests:** `test_round13_b3_exempts_only_rule_w_minus_inside_the_value` has six cases:
  - `is - 1.25` on `is -\n1.25` is accepted.
  - A `- ` at index 0 is refused, with a letter before it, a digit before it, and a bare `- 1.25`.
  - `A- 1.25` (after a letter) is refused.
  - `a - b` (no digit) is refused.
- **Library cases:** `w-minus-wrap-text` and the `b3-*` cases pass.
- **U+2212:** I dropped one test I had drafted, a value spelled with U+2212. The existing `reference_rate not in quote` check compares the raw value with the normalised quote, so a U+2212 value never occurs. That is the same check CP-3D has, and it is not part of this change.

**Red first.** After the tests were written and before any code change, 11 failed: `w-minus-wrap-text`, 9 comma-join cases, and the U+2212 draft. All fail for the intended cause (nothing refused, or the minus case refused). The U+2212 draft was later deleted, so 10 of the red tests remain in the file.

**Gates.**
- pytest on `tests/test_method_cp2e.py`, `tests/test_defect_classes_selfcheck.py` and `tests/test_host_h1.py`: 762 passed, exit 0.
- `ruff check`: pass.
- `ruff format --check`: clean (I ran `ruff format` once on the two files).
- `MYPYPATH=src mypy --strict` on both files: no issues.
- gates-first-pass=n: the first full run had the draft U+2212 test failing, and I deleted it. The gates above are the final run.

**Mutants.** I ran one per clause from a full temp copy with `PYTHONDONTWRITEBYTECODE=1`. The script is `<S>/run_mutants.py`. All eight are killed (exit 1).

| Mutant | First failing test |
|---|---|
| M1 drop `(?<![0-9],)` | `comma_join_before_the_figure_in_the_quote[comma]` |
| M2 drop `(?<![0-9], )` | `comma_join_before_the_figure_in_the_quote[comma-space]` |
| M3 trailing `[.,]` becomes `\.` | `comma_join_after_the_figure[comma]` |
| M4 drop trailing `, [0-9]` | `comma_join_after_the_figure[comma-space]` |
| M5 no B3 exemption | `w-minus-wrap-text` |
| M6 no index-0 guard | `b3-index-0-letter-wrap-text` |
| M7 W minus without the letter/digit lookbehind | `b3-letter-wrap-text` |
| M8 W minus without the digit lookahead | `b3-no-digit-wrap-text` |

**Probes.** Copies are in `<S>/cp2e-r13/`, with LANE pointed at `r13-cp2e`.
- **`p13_refusal_mutations.py`: exit 0.** It ran 28 CP-2E mutations. The only change is CP-3D `amortisation_nonzero`. No CP-2E mutation moves.
- **`p13_quote_classes.py`: exit 1.** Every CP-2E failure is a check that assumes the pre-change code:
  - **`lane == OFF`:** the probe asserts the lane reader equals `OFF`, its old model with no guards. Item 8 and rule W are meant to change CP-2E, so the CP-2E lane differs from `OFF` on thousands interior, thousands start edge, thousands end edge, decimal comma and "quote wrap before page minus". The CP-2E lane equals the probe's rule column (`RULE`, the comma-only model) in all of those. The 15 CP-2E frozen triples are unchanged.
  - **Control cases:** "control list" and "control year comma" expect accept under `RULE`, the comma-only model. The ruled comma-space join refuses them, so CP-2E refuses `1, 2` and `2025, 250`. This is the ruled cost, and `p13_comma_space_join.py` prints it as "cost list/year comma: under cs refused".
  - **CP-3D and CP-1D:** the CP-3D and CP-1D rows fail the same way. They are not part of this change.
- **`p13_comma_space_join.py`: exit 1.** It prints "a frozen moved" because its `moved_strings` list is non-empty: 1956 frozen strings have a figure reading that moves under the comma-space join (CP-8 labelled check: 279 of 563 move, all on `Month D, YYYY` dates). That list comes from the probe's own model, not from CP-2E code. The probe's frozen-triples line shows "moved: none", with CP-2E at 15.

**Not verified:** the full suite and the other modules' tests (only the CP-2E, selfcheck and H1 gates ran). `detect_changes`/GitNexus was not run. The CP-3D library cases come from the branch under review. Nothing checked the comma and wrap joins in rows other than the share, labelled and `reference_rate` readers. The page-edge test for the labelled reader covers the leading side only; the trailing side runs through the share reader only. A U+2212 spelling in `reference_rate` is untested, since it never occurs in a normalised quote.

Ledger: agent=mx-feature fix-rounds=0 gates-first-pass=n