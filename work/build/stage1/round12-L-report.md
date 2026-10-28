## Round 12 Part L report (library and blank predicate)

**Commit:** `2ca1676` on `claude/round12`, worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/round12`. In Step 0, HEAD was c6bb19b as required. Before the change, the module tests and the selfcheck were green: 3544 passed, 2 skipped, 1 xfailed.

Files:
- `src/deploy_workflow/owners/blank.py` (new)
- `tests/test_owner_blank.py` (new)
- `tests/defect_classes.py`
- `tests/test_defect_classes_selfcheck.py`

### Rulings and their tests
- **B10, the predicate.** `is_blank(text: str) -> bool` is true when every character is `str.isspace()` or `unicodedata.category(c) == "Cf"`, so `""` is blank.
  - `tests/test_owner_blank.py` (21 tests) covers U+200B, U+FEFF, U+00AD, U+2060, `" ​\n"` and `""` as blank, and `"a​"` as not blank.
  - It also checks that `str.strip()` keeps these characters, plus three hypothesis properties: concatenation, runs of blank characters, and agreement with `strip()` when the text has no `Cf` character.
  - The test went red first, on the import error, and then green.
- **B10, the library.**
  - `BLANK_VALUES` gains U+200B, U+FEFF, U+00AD and `" ​\n"`, as `blank-5` to `blank-8`. The ids of the existing blank cases are unchanged.
  - Those four cases carry the new ruling `R12_B10`; the others keep `R11_BLANK`.
  - `whitespace_only` keeps its name, because CP-1D reads it. It now means blank but not `""`.
  - Selfcheck: `test_blank_values_hold_format_characters`, and `test_a_strip_reader_fails_exactly_the_format_cases`. The selfcheck's plain readers now use an independent `_blank` written from the ruling, so the selfcheck still imports no owner.
- **Rule W, refused cases.** Each is added for both figures, `25` and `1.25`, with ruling `R12_W`, and each has the twin made by deleting its sign:
  - `w-minus-space-<f>` (`- <f>`, page and quote), twin `genuine-<f>`;
  - `w-minus-wrap-<f>` (`-\n<f>`, the quote spans the break), twin `w-break-<f>`;
  - `w-minus-nbsp-<f>` (U+2212 then NBSP), twin `genuine-<f>`;
  - `w-parens-wrap-<f>` (`(\n<f>)`), twin `w-break-<f>`;
  - `w-edge-minus-space-<f>` (page `- <f>`, edge quote), twin `edge-start-<f>`. Only the page differs, as in the round 11 edge pairs, and the selfcheck asserts that.
- **Rule W, accepted controls.**
  - `w-break-<f>`: a line break with no minus.
  - `w-letter-wrap-<f>`: `A-\n<f>`.
  - `w-2024-2025-wrap`: `2024-\n2025`, value 2025.
  - `sign-95-96` already existed; it is kept and asserted.
- **Rule W, selfcheck.**
  - `test_rule_w_cases_are_present`.
  - `test_rule_w_case_is_signed_only_under_w`: a refused case is signed only one space away in the plain reading, so round 10 alone misses it, and it is signed in every reading. A control is unsigned in every reading of both page and quote.
  - The edge "only the page differs" check now includes the W edge cases.
- **Docstring.** The module docstring adds `R12_W` (the rule, the hyphen-wrap exception and the accepted cost) and `R12_B10`, and says which twin each W case has. The docstring is now a raw string, because it shows `\n`.

### Existing cases flipped
None. The reference reader with W on agrees with every pre-round-12 case (0 mismatches). With W off, it mismatches only the 10 new W refusals. No library case before this round held a spaced minus or spaced parentheses, so the spaced-range cost touches no existing case; `sign-95-96` is unspaced.

### Probes and mutants
All are under `<S>/round12-lib/`.
- `ref_reader_w.py` (the reviewer's reader copied, with W behind a flag):
  - `w`: exit 0, 0 mismatches over 89 cases.
  - `r10`: exit 1, as intended. Exactly the 10 new W refusals mismatch.
- `p_sign_breaks.py` (LEAD's probe copied, LANE pointed at round12): exit 0.
  - A/B/C hold: the bypasses are there on today's code, W refuses every class case, and the 4 controls are unchanged.
  - D: no frozen triple moved (CP-1D 4, CP-2E 15, CP-3D 15, CP-8 40).
  - E: on random wrapped texts, plain and joined readings disagree on a sign 1759 times under round 10 and 0 times under W.
  - The output is in `p_sign_breaks.out`.
- `p_lib_vs_lead_ref.py`: exit 0. It runs LEAD's reference functions (`ref_occurs` with W on and off, and the CP-1D-shaped `ref_amounts`) over all 76 figure cases, and finds no disagreement with the library's expected outcomes.
- `mutants.py`: exit 0. It works from a full temporary copy with `PYTHONDONTWRITEBYTECODE=1`. The unmutated copy passes (226 tests), and all 10 mutants are killed (pytest exit 1):
  - B10: the `Cf` test removed from `blank.py`;
  - B10: the four values dropped from `BLANK_VALUES`;
  - B10: the ruling not recorded on those cases;
  - W: the minus space reverted to `-<f>`;
  - W: the parenthesis space reverted to `(<f>)`;
  - W: the wrapped minus turned into a letter hyphen;
  - W: the NBSP case without its minus;
  - W: the edge page's space reverted;
  - W: the letter-wrap control turned into a minus;
  - W: the 2024-2025 control removed.

### Gates (all exit 0)
- `pytest tests/test_defect_classes_selfcheck.py tests/test_owner_blank.py`: 226 passed.
- `ruff check` and `ruff format --check` on the 4 changed files.
- `MYPYPATH=src mypy --strict` on the 4 changed files.

### Expected red (`tests/test_method_*.py`: 609 failed, 3424 passed, 2 skipped, 1 xfailed)
Output is in `<S>/round12-lib/expected_red.out`. Every failure is a new W refusal, a new `Cf` blank, or one of two pinned not-applicable sets. No accepted control (`w-break`, `w-letter-wrap`, `w-2024-2025-wrap`) fails in any reader.

| Module | Failures | What fails |
|---|---|---|
| cp1c | 32 | blank-5 to blank-8 |
| cpdr | 12 | blank-5 to blank-8 |
| cpl10 | 32 | blank-5 to blank-8 |
| cp2d | 44 | blank-5 to blank-8 |
| cp2g | 92 | blank-5 to blank-8 |
| cp1d | 71 | 60 blank; 10 `test_defect_class_basis_quote` W cases; 1 `test_defect_class_cases_not_applicable` |
| cp2e | 89 | 68 blank; 10 share-figure W; 10 labelled-operand W; 1 `test_class_cases_cover_the_bounds` |
| cp3d | 124 | 84 blank; 40 W figure cases (4 fields × 10) |
| cp8 | 113 | 108 blank; 5 W cases (size level, 1.25 only, since CP-8 holds only N.NN figures) |

- **The two pinned sets.** In CP-1D's `test_defect_class_cases_not_applicable` and CP-2E's `test_class_cases_cover_the_bounds`, the only extra id is `w-2024-2025-wrap`. Its quote prints two figures in CP-1D, and 2025 is above CP-2E's share bound. Each module adds the id to its pinned set.

### Not verified
- No module code was patched, so W is checked against reference readers only (the reviewer's reader with W added, and LEAD's probe functions), not against real module readers.
- The library has no W case for the labelled readers (`label_cases`). The brief listed none, so the CP-8 `_labelled` and CP-2E labelled-reader changes in Part M get no shared-class W coverage.
- GitNexus `detect_changes` was not run; implementers have no MCP tools.
- The full suite outside `tests/test_method_*.py`, the selfcheck and the blank test was not run.

**Ledger:** `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n`. The first `ruff check` failed (PLE2515: the Write tool had put a literal U+200B into `test_owner_blank.py`). The characters were replaced with `\u` escapes and every gate then exited 0.
