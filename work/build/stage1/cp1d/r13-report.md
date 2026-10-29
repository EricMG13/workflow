CP-1D round 13 is done in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/r13-cp1d`. Commit 80cccb1 on `claude/r13-cp1d` (cut at d2cb626, clean at Step 0). It touches only `src/deploy_workflow/owners/cp1d.py` and `tests/test_method_cp1d.py`. Rule W from round 12 is kept.

**Ruling clauses and tests** (all in `tests/test_method_cp1d.py`):
- **Item 7, digits arm.** `_SIGNED_AMOUNT` takes the amended pattern, with the comma and comma-space guards added. Test: new rows in `test_basis_amounts_read_the_printed_sign`. `.25`, `-.25`, `(.25)` and `1.2.5` read `[]`, and `section 4.2.1 a saving of 25` reads `['25']`.
- **Item 8, LEAD comma-space join in the token** (lookbehinds `(?<![0-9],)` and `(?<![0-9], )`, trailing guard `(?![0-9]|[.,][0-9]|, [0-9])`). Same test: `1,250`, `1, 250`, `1,\n250`, `-1,250` and `(1,250)` read `[]`. Controls read `25, and 30` as `['25','30']`, `savings, 250 a year` as `['250']`, `25, which holds` as `['25']` and `25. It holds` as `['25']`.
- **Item 8, `_cut` and `_CONTINUES`.** `_CONTINUES` is now `[0-9]|[.,][0-9]|, [0-9]`. A new `_COMMA_BEFORE` makes a start edge cut when the page has `<digit>,` or `<digit>, ` before the digits. Test: new rows in `test_edge_cut_is_read_in_every_reading`:
  - start edge: `1,250`, `1, 250` and `1,\n250` on the page, quote `250 per year.`;
  - end edge: `25,250` and `25, 250` on the page, quote `The level is 25`.
  - A twin set in `test_edge_figure_whole_on_the_page_is_counted` stays counted: `25, a rise`, `2025, up from 25 percent` and `1,a25`.
- **Riding Low, `\Z` anchors.** Counted twins `The level is -a25 percent.` with quote `25 percent.`, and `The level is (a25) percent.` with quote `25) percent.`.

**Red first.** After the tests and before the fix, 15 cases failed for the ruled cause (10 token rows, 5 edge-cut rows). The anchor twins and the `1,a25` twin pass by design, because they are pins. Their mutants are the proof.

**Gates**, all exit 0:
- pytest on `test_method_cp1d.py` and `test_defect_classes_selfcheck.py`: 613 passed, 1 skipped (the existing Stage 2/4 skip);
- `ruff check` and `ruff format --check` on both files;
- `MYPYPATH=src mypy --strict` on both files.

**Mutants.** Script: `<S>/cp1d-r13/p_r13_mutants.py`. It runs on full temporary copies with `PYTHONDONTWRITEBYTECODE=1` and exits 0 here. The unmutated copy passes, and all 12 mutants are killed:
- drop the point lookbehind;
- drop the digit-comma lookbehind;
- drop the digit-comma-space lookbehind;
- drop the trailing-guard comma;
- drop the trailing-guard comma-space;
- drop the trailing-guard point;
- revert `_CONTINUES`;
- `_CONTINUES` without the comma-space arm;
- remove `_COMMA_BEFORE`;
- `_COMMA_BEFORE` without the space;
- `_W_MINUS` without `\Z`;
- `_OPEN_PAREN` without `\Z`.

One extra mutant, `_COMMA_BEFORE` without its `\Z` anchor, first survived. I added the `1,a25` twin and it is now killed.

**Probes** (copied to `<S>/cp1d-r13/`, LANE pointed at the worktree):
- `p_anchor_survivors.py` exits 0. HEAD reads `['25']` for both anchor pages, and the mutants read `[]`.
- `p13_quote_classes.py` exits 1. Its "F" checks assert that the lane still equals the pre-change reference, which no longer holds after this change. I re-pointed that check at the rule reader in `p13_quote_classes_lane_is_rule.py`. It also exits 1, but only on three checks:
  - **CP-1D control list and control year comma.** The probe's rule is the draft without the comma-space join. LEAD's narrower wording refuses these (`1, 2 and 3` reads `['3']`, `2025, 250` reads `[]`), as the ruling's cost note says.
  - **CP-3D quote-wrap line.** This is another module.
  - Every other CP-1D case, items 7 and 8, equals the rule. The frozen CP-1D triples (4 of 4) did not move.
- `p13_comma_space_join.py` exits 1. Part (a) fails only on "CP-8 labelled moved by cs: 279". That is the literal `, ?` join in `_labelled`, which LEAD narrowed away. Variant (a') for CP-8 moves 0, CP-1D frozen triples move none, and the (c) closure shows 0 disagreements. Part (d) holds: `1,\n250` is refused at the edge, inside the quote, and typed as `1, 250`.

**Wording.** No new issue strings. The pinned exactly-one issue is unchanged.

Not verified: only the CP-1D test file and the selfcheck ran, not the full suite, other modules or `cases/`. GitNexus `impact` and `detect_changes` were not run. A quote that ends in `1,` is not treated as an end edge, because the existing `at_end` condition admits only `""` or `.` after the digits; the ruling does not extend it and I did not. The `cases/` recipe text, PINS.json and `methods/cp1d.md` guard-limit notes are not in this diff. CP-1D's frozen full-case end-to-end behaviour was checked only through the existing test file and the probe's frozen triples.

agent=mx-feature fix-rounds=0 gates-first-pass=y