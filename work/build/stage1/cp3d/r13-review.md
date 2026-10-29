**CP-3D round 13 review (claude/r13-cp3d at a212da3). Verdict: FINDINGS. Spec has one Medium; quality has no High or Medium.**

The non-merge diff is fcd7db2, d96448b and a212da3 on the four named files. The other files in d96448b's stat came in with the round12 merge.

## Spec

**M1 (Medium): a comma at the quote edge still reads a figure out of a page comma run.**
- Where: `src/deploy_workflow/owners/cp3d.py:261-262`, with `_EDGE_AFTER` at :183.
- Cause: a figure is only edge-checked when the quote ends in nothing or `.` after it, or the figure starts at quote index 0. A trailing `,`, a leading `,` or a leading `, ` is never sent to `_cut`, so the page's `, <digit>` or `<digit>,` is never seen.
- Inputs, run through `occurs`'s own path (`quoted` + `_token_once` + `_whole_on_page`). All are accepted:
  - quote `fee of 1,` on page `a fee of 1,250 per year.` gives value `1`;
  - the same quote on `1, 250` and on `1,\n250` also gives `1`;
  - quote `,250 per year` on `1,250` gives `250`, and `, 250 per year` on `1, 250` gives `250`;
  - quote `margin of 25,` on `25,5 bps.` gives `25`.
- Control: the `.` version (`fee of 1.` on `1.25`) is refused.
- Ruling broken: LEAD item 8 says "no figure is read after either, nor before `,<digit>` or `, <digit>`. This closes `1,\n250` at the quote edge". Item 8 also says "A digit-comma-digit sequence joins one run; no figure is read from part of it."
- Mitigation: the implementer applied the ruled `_tokens`, `_CUT_BEFORE` and `_CUT_AFTER` forms exactly. The gap is in round 11 B1's edge definition, which item 8 did not amend. The fix (treat a quote's trailing `,` and leading `,` or `, ` as an edge) probably needs a LEAD ruling.
- The failure fails open on an in-grammar figure: CP-3D grammars allow up to 3 integer digits, so `1` and `250` both read.
- Probe: `<S>/cp3d-r13-review/p_comma_edge.py`, exit 1 (reproduces).

**Fuzz.** `<S>/cp3d-r13-review/p_fuzz_join.py` (exit 0) ran 300k random pages over every page and quote reading. It checks every accepted figure against an independent item 8 whole-run oracle.
- All 6,217 violations are the M1 class: a comma or comma-space at the quote edge.
- Nothing else was found, and no plain/joined disagreement.

**Item 8 otherwise holds:**
- `_tokens` (:203-205), `_CUT_BEFORE` (:179-181) and `_CUT_AFTER` (:182) join exactly `<digit>,` and `<digit>, `, and nothing broader.
- The riding Low is pinned. The reviewer's r12 surviving mutant 2, in its exact form, is now killed (`<S>/cp3d-r13-review/p_r12_mutant2.py`, exit 0).

**B3 exemption is correct** (:272-287).
- `_W_SIGN` is exactly `(?<![A-Za-z0-9])- (?=[0-9])`. U+2212 maps to `-` in `normalise`, so CP-3D's `_MINUS` characters are covered. The index-0 guard is `m.start() > 0`.
- Accepted: `is -\n1.25`, with ASCII `-` and with U+2212.
- Refused: `A-\n25`, `2024-\n2025`, `a - b`, `- 1.25 notes` on `A-\n1.25`, and `- 2025 notes` on `2024-\n2025`.
- Probe: `<S>/cp3d-r13-review/p_b3.py`, exit 0.

**The `amortisation_nonzero` delta is correct.**
- `STAGE2_REFUSAL_DELTA` (`tests/test_method_cp3d.py:232`) holds only that mutation, with exactly the ruled issue `amortisation: value_text 31 does not occur in the quote`.
- The re-pin guard (:248) fails once the frozen issue equals the delta.
- The nonzero branch is pinned at :255 on a `_sign_context` page with no date. That page is not frozen, and the test expects the frozen issue text.
- Removed test lines: only the combined assert `list(issues) == entry["all_issues"] == [entry["issue"]]`. It is kept for every non-delta entry (:244-245).

**Library cases** (`tests/defect_classes.py`, selfcheck) are correct and follow the library's conventions.
- Each refused case has a joined twin on the same page, and each twin's quote has no wrap. The accepted W case carries no twin, as the other accepted cases do.
- Lane bb0190e with only a212da3's two library files applied: `tests/test_method_cp8.py` gives 596 passed and exit 0. All 9 new text cases pass on all 5 CP-8 text fields, so CP-8's f99db43 exemption, index-0 guard included, already passes them. No library case fails there.
- CP-2E on the same copy: 1 failed, `test_class_reference_rate_text[w-minus-wrap-text]`. This is the expected red until CP-2E's round 13 change; the other 8 new cases pass.

## Quality
- **Info:** the riding-Low twin is `2024-\n25 percent` (`tests/test_method_cp3d.py:1871`), not the brief's `2024-\n2025`. It pins the same digit-before-hyphen guard and kills mutant 2. No action needed.
- **Info:** the implementer's "121 CP-8 failures that predate" did not reproduce on lane bb0190e plus the library (0 failures).
- **Info:** the brief bars edits to `tests/defect_classes.py`, but addenda 1 and 3 order the shared class cases. The rulings win, so this is not a finding.
- No stub, fake value or catch-all in the diff.

## Exit codes
- pytest on `test_method_cp3d.py` and `test_defect_classes_selfcheck.py`: 0 (1083 passed)
- `ruff check`: 0
- `ruff format --check`: 0
- `mypy --strict` (4 files): 0
- implementer mutants `<S>/cp3d-r13/mutants.py`: 0 (14/14 killed)
- `p_r12_mutant2.py`: 0
- `p_b3.py`: 0
- `p_fuzz_join.py`: 0
- `p_comma_edge.py`: 1 (reproduces M1)
- CP-8 on lane plus library: 0 (596 passed)
- CP-2E on lane plus library: 1 (expected)

`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. All probes ran from the archive copy at `<S>/cp3d-r13-review/copy`; the lane copy is at `<S>/cp3d-r13-review/lane`.

Not verified: M1 was not driven through `submission_issues` on a full frozen-shape submission; the probe uses `occurs`'s exact composition at cp3d.py:539 plus `quoted`. Also not checked: whether CP-8, CP-2E and CP-1D share the M1 edge gap; the full suite and `test_host_h1`; GitNexus `impact` and `detect_changes`; the LEAD probes `p13_*` (not re-run); the `methods/cp3d.md` guard-limit notes.