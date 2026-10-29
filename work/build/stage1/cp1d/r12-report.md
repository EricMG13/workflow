CP-1D Stage 1, round 12 (rule W, B10, move the :1154 row). Commit **aa7c15f** on `claude/cp1d-stage1`. Its parent is 2ca1676, and I confirmed HEAD = 2ca1676 after `git merge --ff-only claude/round12`. The commit changes only `src/deploy_workflow/owners/cp1d.py` and `tests/test_method_cp1d.py`.

**Before the change:** 71 failures in `tests/test_method_cp1d.py` (60 blank, 10 W, 1 not-applicable). My 14 new tests also failed for their cause before the code changed. **After:** 587 passed, 1 skipped (the existing Stage 2/4 skip).

**Rulings and their tests**
- **Rule W in `_SIGNED_AMOUNT`.** The sign group is now `(?P<sign>(?<![A-Za-z0-9])- ?)?` and the parenthesised arm is `\( ?(?P<parenthesised>…) ?\)`. The amount string is still `-<digits>` with no space (`'-' if match['sign']`).
  - Library tests: `test_defect_class_basis_quote[w-minus-space|w-minus-wrap|w-minus-nbsp|w-parens-wrap-{25,1.25}]`.
  - New rows in `test_basis_amounts_read_the_printed_sign`: `- 1.80`, `-\n1.80`, U+2212+NBSP, `-\r\n1.80`, `(\n1.80)`, `(1.80 )`, `( 1.80 )` all read `-1.80`.
  - Controls in the same test: `( 4.30 percent)`, `2024-\n2025`, `A-\n350` and `95- 96` read unsigned. `95 - 96` reads `["95","-96"]`, which is the accepted fail-closed cost.
  - `test_edge_with_a_stop_or_a_sign`: quote `- 25 …` reads `["-25"]` and gets the bounds text, as the ruling's edge definition says. LEAD's I1 case, quote `The level is -\n1.80` on a page printing `-1.80`, reads `["-1.80"]` and gets the bounds text.
- **Rule W in `_cut` (`_ROUND10_MINUS` is replaced).** `_ROUND10_MINUS` is replaced by `_W_MINUS = (?<![A-Za-z0-9])- ?\Z`, `_OPEN_PAREN = \( ?\Z` and `_CLOSE_PAREN = ` ?\)`. `_cut` now takes `(text, start, end)` and does its own lookups; the lookbehind still sees past the 2-character window.
  - Tests: `w-edge-minus-space-{25,1.25}`, plus new rows in `test_edge_cut_is_read_in_every_reading` for `( 25)`, `(25 )`, `( 25 )` (start edge) and `( 25 )` (end edge).
  - New counted twins: `4- 25`, `( 25 percent over)`, `25 )` with no open parenthesis.
- **Row :1154 moved to the refused list.** `("The level is - 25 percent; it was 425 before.", "25 percent;")` is now in `test_edge_cut_is_read_in_every_reading` (reads `[]`, exactly-one text).
- **`w-2024-2025-wrap` added to the pinned not-applicable set** in `test_defect_class_cases_not_applicable`. The existing reason applies: "the quote prints two figures".
- **B10.** `_blank_issues` calls `is_blank(text)` (imported from `deploy_workflow.owners.blank`) in place of `not text.strip()`, at the same position. `""` and None handling are unchanged. Tests: all 60 `test_defect_class_blank_text[*-blank-5..8]`.
- **Docstrings** updated for `_SIGNED_AMOUNT`, `_basis_amounts`, `_edge_cut`, `_cut` and `_blank_issues`.

**LEAD's note (R3 M3, missing `(?<![0-9.])` guard)**
- I did not add the guard, and no test pins `.25` or `-.25` as reading 25. No added row has a point that does not follow a digit (checked by grep on the diff).
- I applied the guard to `_SIGNED_AMOUNT` in a scratch copy and the whole gate still passed (587 passed). So no W case or other test depends on the defect.
- The worktree still reads `.25`, `-.25` and `- .25` as `25`. W does not change this: `- .25` reads `25` with or without W.

**Mutants** (each one a full copy with PYTHONDONTWRITEBYTECODE=1). Script: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp1d-r12/p_r12_mutants.py`, output in `mutants.out` in the same directory. Exit 0. The unmutated copy exits 0, and all 11 mutants are killed (pytest exit 1):
- W minus space reverted, in `_SIGNED_AMOUNT` and in `_W_MINUS`;
- the W minus lookbehind dropped, in both places;
- the amount string keeping the space;
- each of the 4 parenthesis-space reverts (open and close, in `_SIGNED_AMOUNT` and in `_cut`);
- the B10 call site reverted to `strip()`;
- the B10 `Cf` test removed in `blank.py`.

**Probes**
- **LEAD `p_sign_breaks.py`**, path-only copy (`…/scratchpad/cp1d-r12/p_sign_breaks_pathonly.py`): exit 1, as expected.
  - All 11 failures are CP-1D: "C fidelity" in 10 class cases, where the module now equals the reference with W on rather than W off, and "A expected CP-1D sign flip missing", because the flip is fixed.
  - Everything else holds: CP-3D, CP-8 and CP-2E fidelity; B; D (frozen readings moved: none; 4/15/15/40 triples); E (round 10 = 1759, W = 0).
- **Adapted copy** (`…/scratchpad/cp1d-r12/p_sign_breaks_cp1d.py`): exit 0. It checks CP-1D fidelity against the reference with W on, expects `["-1.80"]` in A, and adds a check that the CP-1D module equals the W-on reference on the frozen triples. The CP-3D, CP-8 and CP-2E checks are LEAD's, unchanged.
- **`cp1d-class-review/p_wrap_sign_drop.py`**: exit 0, so the defect is gone. HEAD reads `['-1.80']` and the bounds text fires on both cases.
- **`cp1d-class/p_frozen_readings.py`**: exit 0 (45 readings, none moved).

**Gates** (all exit 0)
- `pytest tests/test_method_cp1d.py tests/test_defect_classes_selfcheck.py`: 587 passed, 1 skipped.
- `ruff check` and `ruff format --check` on both changed files.
- `MYPYPATH=src mypy --strict` on both changed files.

**Leftovers**
- A scratch copy of the worktree is in `…/scratchpad/cp1d-r12/guard-copy/`. My cleanup command was refused by the rm safety check, so it is still there. It is outside the repo.
- The `methods/cp1d.md` guard-limit note (spaced range or dash bullet now refused) is a Stage 2 note for the controller, per the brief, so I did not write it.
- The recipe-text change in `cases/cp1d-owner/expected.json` and its builder belongs to the release batch and was not touched.

Not verified: only the CP-1D test file and the selfcheck ran, not the full suite or other modules. GitNexus impact and detect_changes were not run. The `.25`/`-.25` defect (R3 M3) is still present, pending the round 13 ruling. The `cases/` recipe text that describes W is not updated in this branch (release batch). The probe's frozen set covers JSON strings and the test pages, not every page a builder makes.

Ledger: agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n — the first format check failed on one long row, which ruff format fixed; all tests passed first time after the code change.
