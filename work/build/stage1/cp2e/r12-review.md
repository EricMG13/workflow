## CP-2E round 12 review (3c883e5, diff 128c3ca..3c883e5)

**Verdict: CHANGES REQUIRED.** There is one Medium finding: replacing the test that pinned the asymmetry lost coverage of a refusal. The code itself is correct on every ruling I checked.

**Spec verdict: pass.** W, B10 and the `bool()` fix match the rulings.
- The diff touches only the two allowed files.
- It changes 105 lines, well under the 800 ceiling.
- It does not touch `cases/`, `deploy_vii` or `methods/`.
- The `fx.` path owner item is left alone, as the dispatch notes require.

**Quality verdict: changes required** (finding M1).

### Findings

**M1 (Medium): the "only for it" half of the limitation rule is no longer pinned by any test.**
- **Where:** `tests/test_method_cp2e.py:1192-1200`, which covers the rule at `src/deploy_workflow/owners/cp2e.py:723`.
- **Cause:** the old `test_class_blank_limitation_off_insufficient_information[spaces]` expected `empty text` plus `assessments[0]: limitation is required for Insufficient Information and only for it`. It was the only test that refused a limitation stated on an assessment that is not Insufficient Information.
- **Effect:** the new tests feed only blank values. So the mutant `if a["category"] == "Insufficient Information" and not stated:`, which drops the "only for it" half, now survives `test_method_cp2e.py`, the selfcheck and `test_host_h1.py` (511 passed).
- **Base comparison:** at 128c3ca the same mutant is killed by `[spaces]`, and the unmutated subset passes (30 passed).
- **Suggested fix:** a test that sets a non-blank, digit-free limitation on `assessments[0]` and expects exactly the "only for it" issue. A Cf-bearing non-blank twin such as `"a​"` would also pin `not is_blank`.
- **Probes:**
  - `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2e-r12-review/mutants_review.py`: exit 1. The mutant "drop the 'only for it' half" is the one survivor.
  - `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2e-r12-review/p_only_for_it_base.py`: exit 0, which means the coverage loss is present. The mutant is killed at base and survives at head.

**I1 (Info): CP-2E's tests never exercise the `2024-\n2025` control.**
- **Where:** `tests/test_method_cp2e.py:1031-1034`.
- **The exclusion reason is real.** The `w-2024-2025-wrap` figure is `2025` (`tests/defect_classes.py:273`). That is above the share bound of 100, and its four digits are outside `_SENTENCE_NUM` `{1,3}` (`cp2e.py:488`). So it is excluded from both sets, as `sign-2024-2025` already was.
- **Consequence:** the module's tests never run the control. My probe checks it directly: `_unsigned("2025", …)` stays unsigned in both readings. No change is needed.
- **Probe:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2e-r12-review/p_w_review.py`, exit 0.

### Checks by ruling (all confirmed)

**1. W in `_unsigned` (`cp2e.py:508-514`).**
- Both lookbehinds, `(?<!{minus})(?<!{minus} )`, match the ruling's fixed-width form.
- The accounting negative accepts `(` or `( ` before the figure and `)` or ` )` after it, and needs both sides. This is the same as CP-1D's `\( ?… ?\)` on claude/round12 (`cp1d.py:352-355`).
- The labelled reader (`cp2e.py:601`), the share check (`:691`) and the B1 page loop (`:541-548`) all go through `_once` → `_unsigned`.
- `p_w_review.py` (exit 0) confirms:
  - `spread - 25` and `spread ( 25 ) bps` are refused, and `spread 25` is accepted.
  - The B1 page check refuses an edge quote whose page reads `- 25`, `-\n25`, `( 25 )` with a right-edge quote, or `were ( 25` with a left-edge quote. The twin is accepted.
  - The spaced range `24 - 25` and the dash bullet `- 25` are refused (the accepted cost). Unspaced `24-25` and `A-\n25` are accepted.
  - `A-\n25` and `2024-\n2025` are unsigned in both readings.
- **Sign disagreement:** I looked for a plain/joined disagreement on the module's own `_unsigned`. I mapped each figure back to its raw position through `Reading.origin`, over random wrapped texts containing U+2212, NBSP, CRLF, `-\n  ` and parentheses. There were 0 disagreements.

**2. The `bool()` fix (`cp2e.py:720-724`).**
- Non-II: every `BLANK_VALUES` entry, Cf included, gives only `assessments[0].limitation: empty text`.
- II: every blank value gives `empty text` followed by the required issue, as the confirmed Info item says.
- Null on II still gives the frozen `insufficient_without_limitation` refusal.
- No frozen order moves: `empty` still runs before the II check.
- Coverage lost: see M1.

**3. B10.** `_Check.empty` calls `is_blank` (`cp2e.py:565`). No other blank `.strip()` test remains: `:613` and `:615` are the row-line matching.

**4. The bounds set.** The exclusion reason is real (I1).

**5. Frozen readings and stubs.**
- Frozen readings are unchanged. Part D moved 0 readings: CP-1D 4, CP-2E 15, CP-3D 15, CP-8 40.
- No stub, fake value or catch-all: the file has no `except`.
- The label-decimal gap is not made worse, because the label regex at `:604` is unchanged.

### Probe and mutant exit codes
All ran from a full temporary copy (`.../scratchpad/cp2e-r12-review/wt`) with PYTHONDONTWRITEBYTECODE=1.
- `p_sign_breaks_w.py` (copy, LANE pointed at the copy): exit 0. Part E: 1759 disagreements under round 10, 0 under W.
- `p2_behaviours_r12.py`: exit 0.
- Implementer's `mutants.py`: exit 0. The baseline passes and all 6 mutants are killed.
- `p_w_review.py`: exit 0.
- `mutants_review.py`: exit 1 (the M1 survivor). Seven mutants are killed:
  - the spaced minus without the alnum guard;
  - the direct minus without the guard;
  - the accounting test with `or` in place of `and`;
  - `stated` as not-None only;
  - `stated` using `strip`;
  - dropping the "required" half;
  - dropping `empty()` on the limitation.
- `p_only_for_it_base.py`: exit 0 (the coverage loss is confirmed).

All probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2e-r12-review/`.

### Gates (all exit 0, run on the copy)
- pytest on `tests/test_method_cp2e.py` and `tests/test_defect_classes_selfcheck.py`: 679 passed.
- `ruff check`.
- `ruff format --check`.
- `MYPYPATH=src mypy --strict` on both files.

Not verified: the full suite and the other modules' tests (only `test_host_h1.py` was run, and only under the M1 mutant). U+2060 is not in `BLANK_VALUES`, so CP-2E's own tests never feed it, though `is_blank` is generic. My closure probe sampled random texts; it is not a proof over every string. GitNexus was not used. I did not re-read CP-1D's approved review, only its `_SIGNED_AMOUNT`/`_cut` code.