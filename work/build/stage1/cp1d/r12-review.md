## CP-1D round 12 review (rule W, B10, the :1154 row move): commit aa7c15f, diff 2ca1676..aa7c15f

**Spec verdict: APPROVE.** Every ruling part is implemented as written and pinned by a test.
**Quality verdict: APPROVE, with one Low.** There is no High or Medium finding. I found no stub, fake value or catch-all.

### Constraints and diff ceiling
- The diff touches only `src/deploy_workflow/owners/cp1d.py` and `tests/test_method_cp1d.py`: 74 lines added, 26 removed, 100 changed, well under 800.
- No file under `cases/`, `src/deploy_vii` or `methods/` is touched.
- The worktree is clean at aa7c15f.

### Spec, by ruling id
1. **Rule W in `_SIGNED_AMOUNT` (cp1d.py:353-355).** Both patterns match the ruling's text:
   - the sign group `(?<![A-Za-z0-9])- ?`;
   - the parenthesised arm `\( ?…  ?\)`.
   - The amount string is `-<digits>` with no space (cp1d.py:541, `'-' if match['sign']`).
   - The class cases and controls hold:
     - `A-\n25` reads `25` and `2024-\n2025` reads `2024, 2025` (both unsigned);
     - `95-96` and `95- 96` read unsigned;
     - `95 - 96` reads `["95","-96"]`, the accepted cost (tests at test_method_cp1d.py:835-851).
   - **No input found where the plain and joined readings disagree on sign.** 105,666 random hyphen-wrapped texts (CRLF, NBSP, thin space, U+2212, U+2013, soft hyphen, `-\n` plus spaces) gave 0 disagreements. 22 hand cases also hold, including `5 -\n0.25`, `(-\n0.25)` and `( 0.25\n)`. Probe: `p_closure_and_cut.py` part A/B.
   - The known `.25` defect (R3 M3) is not made worse. `.25`, `-.25`, `- .25`, `(.25)` and `( .25 )` read the same as under round 11. Probe: `p_dot_guard_not_worse.py`.
2. **Rule W in `_cut` (cp1d.py:563-565, 596-607).**
   - **Lookbehind past the window:** `_W_MINUS.search(text, lead, start)` sees characters before `lead`, as checked on `a- 25`, `4- 25`, ` - 25`, `x--25`. At text start (`lead=0`) the minus counts as starting the text, which is what the rule says.
   - **Round 11 B1 edge cases:** I compared against round 11's `_cut` (verbatim from 2ca1676) on 200,000 random texts with all four `at_start`/`at_end` combinations. There were 6,930 differences, and every one is a W form (`- ` with the lookbehind, `( `, or ` )`), so nothing else moved. Probe: `p_closure_and_cut.py` parts C/D.
   - The `(text, start, end)` refactor also keeps the `start=0` behaviour: `text[-1:0]` is `""`, as before.
3. **The :1154 row.** It was removed from `test_edge_figure_whole_on_the_page_is_counted` and added to `test_edge_cut_is_read_in_every_reading` (test_method_cp1d.py:1157). That test asserts `DEFECT_EXACTLY_ONE` and `[]`.
   - `w-2024-2025-wrap` is in the not-applicable set (:1122).
   - Its reason is real: the normalised quote `…2024- 2025.` prints two figures, so the pinned exactly-one rule refuses it.
4. **B10 (cp1d.py:1703).** `is_blank(text)` replaces `not text.strip()` in the same comprehension, at the same position and with the same frame.
   - `text is not None` is kept, so null still means no limitation.
   - `""` still gets the issue: `is_blank("")` is True, as `not "".strip()` was.
5. **Frozen readings.** None moved (45 checked). The rerun sign-breaks probe found no frozen reading moved by W.

### Quality findings
- **Low: the `\Z` anchors in `_W_MINUS` and `_OPEN_PAREN` (cp1d.py:563-564) are not pinned by any test.**
  - Removing either one leaves the gate green.
  - Each removal changes behaviour, in the fail-closed direction:
    - page `The level is -a25 percent.`, quote `25 percent.`: HEAD reads `['25']`, the mutant reads `[]`;
    - page `The level is (a25) percent.`, quote `25) percent.`: HEAD reads `['25']`, the mutant reads `[]`.
  - HEAD is correct; only the pin is missing.
  - Suggested fix (rides with the next fix): add those two pairs to `test_edge_figure_whole_on_the_page_is_counted`.
  - Probes: `p_review_mutants.py` (the two survivors) and `p_anchor_survivors.py` (exit 0, shows the divergence).

### Probe and mutant exit codes
All probes ran from a full temporary copy (`…/cp1d-r12-review/wtcopy`) with PYTHONDONTWRITEBYTECODE=1. The `rerun_*` files are the original probes with their paths rewritten to the copy.

| Probe | Exit | Result |
|---|---|---|
| `rerun_p_r12_mutants.py` (implementer's 11 mutants) | 0 | unmutated copy exits 0; all 11 killed |
| `rerun_p_sign_breaks_cp1d.py` | 0 | closure: round 10 = 1759 disagreements, W = 0; no frozen reading moved |
| `rerun_p_wrap_sign_drop.py` | 0 | HEAD reads `['-1.80']`; the bounds text fires on both cases |
| `rerun_p_frozen_readings.py` | 0 | 45 checked, none moved |
| `p_closure_and_cut.py` | 0 | parts A-D hold |
| `p_dot_guard_not_worse.py` | 0 | point-led figures read as in round 11 |
| `p_anchor_survivors.py` | 0 | shows the two survivors' divergence |
| `p_review_mutants.py` (9 reviewer mutants) | 1 | 7 killed, 2 survived (the Low) |

- Killed reviewer mutants: `lead` window cut to one character; `_W_MINUS` lookbehind without digits; `_SIGNED_AMOUNT` lookbehind without letters; the paren cut gated on `at_start`; the paren cut gated on `at_end`; the digit/point check widened to the window; B10 reduced to `isspace` only.
- Survivors: `_OPEN_PAREN` without `\Z`, and `_W_MINUS` without `\Z`. The SyntaxWarnings in this probe's output come from the mutant label strings only.

### Gates (run on the cp1d-stage1 worktree, all exit 0)
- pytest on `tests/test_method_cp1d.py` and `tests/test_defect_classes_selfcheck.py`: 587 passed, 1 skipped (the existing Stage 2/4 skip).
- `ruff check --no-cache` on both files.
- `ruff format --check --no-cache` on both files.
- `MYPYPATH=src mypy --strict` on both files, with the cache directory in the scratchpad.

### Files
Everything is in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp1d-r12-review/`:
- probes: `p_closure_and_cut.py`, `p_dot_guard_not_worse.py`, `p_anchor_survivors.py`, `p_review_mutants.py`, `rerun_p_r12_mutants.py`, `rerun_p_sign_breaks_cp1d.py`, `rerun_p_wrap_sign_drop.py`, `rerun_p_frozen_readings.py`;
- outputs: `review_mutants.out`, `rerun_mutants.out`, `rerun_p_*.out`;
- the temporary copy: `wtcopy/`.

Not verified: only the CP-1D test file and the selfcheck ran, not the full suite or other modules. GitNexus impact and detect_changes were not run. The closure check is a random search over a small alphabet, not a proof. The frozen-readings check covers the probe's 45 readings and the sign-breaks probe's frozen triples, not every page a builder makes. The `cases/` recipe text describing W (release batch) and the `methods/cp1d.md` guard-limit note are not in this diff and were not reviewed.
