CP-3D round 12 (rule W and B10) is committed: **504d084** on `claude/cp3d-stage1`, parent 128c3ca. The working tree is clean. Step 0 passed: the fast-forward from eb4b3cb reached 128c3ca. Only two files changed: `src/deploy_workflow/owners/cp3d.py` and `tests/test_method_cp3d.py`.

**Rulings and their tests**
- **Rule W, minus (`_MINUS`/`_tokens`, `_CUT_BEFORE`).**
  - `_tokens` now has the second lookbehind, `(?<![0-9.])(?<!{_MINUS})(?<!{_MINUS} )<v>(?![0-9]|\.[0-9])`.
  - `_CUT_BEFORE` is now `(?:[0-9.]|{_MINUS} ?)\Z`.
  - Tests: the 40 library W cases in `test_r11_class_figure_cases` (red before, green now).
  - New `test_r12_w_a_labelled_bid_after_a_spaced_minus_does_not_occur`: `bid - 1.25` and `bid -\n1.25` give exactly `observations[0]: level_text 1.25 does not occur in the quote`; the twins `bid 1.25` and `bid\n1.25` give `()`. This covers the labelled reader, which the library has no W cases for.
  - In the new `test_r12_w_spaced_parentheses_and_a_leading_minus`, the `start-minus-space` case covers a `- ` that starts the text.
- **Rule W, accounting parentheses (`_tokens`, `_cut`).**
  - A new helper `_parenthesised(before, after)` accepts `(` or `( ` before the figure and `)` or ` )` after it. Both `_tokens` and `_cut` use it.
  - Tests: the library's `w-parens-wrap` cases.
  - The new test above also covers the close-paren space, both spaces, `(25\n)`, and spaced parentheses at the start and end edges of a quote. Each refused case has an accepted twin.
  - Eight new cases were red before the fix for the W cause; the six twins were green before and after.
- **B10.** `_Issues.analyst_text` now uses `is_blank(text)` from `deploy_workflow.owners.blank` instead of `not text.strip()`. The position, the `<path>: empty text` frame and null handling are unchanged. Tests: the 84 library blank cases in `test_r11_class_blank_text` (red before, green now).
- No existing case changed its expected outcome. All 124 expected failures now pass.

**Probe and mutant exit codes** (all under `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3d-r12/`)
- **LEAD `p_sign_breaks.py`, path-only copy** (`p_sign_breaks_pathonly.py`, `.out`): exit 1, as expected.
  - The probe expects every reader to still be on round 10. CP-1D is already W in `claude/round12`, and CP-3D now is too.
  - So all failures are "C fidelity" for CP-3D and CP-1D in 10 class cases each (they now equal the W-on reference), plus the two A "bypass/flip missing" lines.
  - B, D and E hold. D: no frozen reading moved, over 4/15/15/40 triples. E: 1759 disagreements under round 10, 0 under W.
- **Adapted copy** (`p_sign_breaks_cp3d.py`, built from `cp1d-r12/p_sign_breaks_cp1d.py` by `make_cp3d_copy.py`; output in `.out`): **exit 0**.
  - It checks CP-1D and CP-3D against the W-on reference, in C, in A (CP-3D bypass gone) and in D on frozen triples.
  - The CP-8 and CP-2E checks are LEAD's, unchanged.
- **`cp3d-class-review/p_wrap_minus_and_edges.py`** (rerun output in `cp3d-r12/p_wrap_minus_and_edges.out`): **exit 0**.
  - Check W: all four lines now give `reference_rate: level percent_text 0.25 does not occur in the quote`. At the class review, three of them returned `()`.
  - The E and B lines are unchanged.
- **Mutants** (`p_r12_mutants.py`, `mutants.out`; full temporary copy in `cp3d-r12/mutcopy`, `PYTHONDONTWRITEBYTECODE=1`): **exit 0**. The unmutated copy passes, and all 7 mutants are killed (pytest rc=1):
  - the minus space in `_tokens`;
  - the minus space in `_CUT_BEFORE`;
  - the open-paren `( `;
  - the close-paren ` )`;
  - the parenthesis space reverted in `_tokens` only;
  - the parenthesis space reverted in `_cut` only;
  - the B10 `Cf` test reverted to `not text.strip()`.

**Gates** (all exit 0)
- `pytest tests/test_method_cp3d.py tests/test_defect_classes_selfcheck.py`: 1016 passed. Before the fix it was 124 failed, 878 passed.
- `ruff check` and `ruff format --check` on both changed files. One test signature was reformatted before the commit.
- `MYPYPATH=src mypy --strict` on both changed files.
- Also run, since these tests import cp3d or the predicate: `tests/test_host_h1.py` and `tests/test_owner_blank.py`, 58 passed.

**Not verified:**
- The full suite was not run.
- GitNexus `impact` and `detect_changes` were not run; I have no MCP access as implementer.
- The guard-limit note in `methods/cp3d.md` (spaced range or dash bullet now refused) is not written. It is a Stage 2 note for the controller, and the brief forbids editing `methods/*.md`.
- The CP-8 and CP-2E lines in the adapted `p_sign_breaks` copy still show their round-10 bypasses, which is expected because those modules are not done yet.
- W was checked on frozen triples only through the probe's inventory, not on every page a builder makes.

Ledger: `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y`
