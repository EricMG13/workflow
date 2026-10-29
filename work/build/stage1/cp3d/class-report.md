CP-3D class round (round 11): B1, B3 and blank text are fixed, and the riding B2 item is applied. All gates exit 0 and all 22 mutants were killed. Commit **eb4b3cb** on `claude/cp3d-stage1`, built on lane tip 864ffe3 as you instructed. Step 0 was a fast-forward.

Only two files changed: `src/deploy_workflow/owners/cp3d.py` and `tests/test_method_cp3d.py`.

**Class by class.** The adapter runs the library's case lists, parametrised, in `tests/test_method_cp3d.py`. Before the fix: 158 failed, 209 passed. After: all pass.
- **Figure cases (`FIGURE_CASES`) × 4 readers** (margin `bps_text`, amortisation `value_text`, reference-rate level `percent_text`, talk `level_text`):
  - soft hyphen, dashes, NBSP, signs and parentheses: passed;
  - edge cut: **fixed** (13 cases per reader were red).
  - The probe only covered margin and the level; I added amortisation and talk so every `_token_once` caller is exercised.
- **Label cases (bid)** for figures 25 and 1.25: passed. An accepted case gets neither the "not labelled" nor the "does not occur" refusal.
- **Text cases × instrument.name and reference_rate.name:** soft hyphen and NBSP passed; wrap-split **fixed**.
- **Blank text × 21 analyst text fields:** **fixed**. This includes the three fields the probe skipped: `maturity.absence.follow_up`, `margin.absence.follow_up`, `amortisation.absence.reason`.
  - Whitespace-only and `""` both get `<path>: empty text`, because CP-3D fields are plain `str` with no schema refusal.
  - The new check is the first step of `_Issues.analyst_text`.

**What the fixes do (no new wording; pinned issues only)**
- **B1:**
  - New `_whole_on_page`, reached through `_Issues.occurs` at all three occurrence checks, so the issue still fires at the occurrence check.
  - The needles are `normalise(quote)` plus the joined reading of a wrapped quote; the page readings are `normalise(page)` plus the joined reading of a wrapped page. Every occurrence is checked, and if any one is cut the figure does not occur.
  - Start edge: digit, `.`, round 10 minus, or closed `(`. End edge: digit, `.` plus a digit, or closing `)`.
  - I simplified the start edge to "nothing before the figure". The ruling's "or only a sign" changes no outcome: the sign is quoted, so it is on the page too; a minus is already not a token, and `+` or an unclosed `(` is never a cut. The docstring says this.
- **B3:** `_name_occurs` refuses when `hyphen_wrapped(quote)` holds and `"- "` is in `normalise(name)`. It is used for `inst.name` and `rr.name`.
- **B2 (riding):** `_tokens` applies the parenthesis exclusion only when `value_text` starts with a digit.

**Riding item and its tests.** `test_r11_b2_parentheses_read_only_around_a_digit`:
- `(-425)` with `-425` gets `margin: bps_text -425 <_SHAPE>`;
- `(-4.30)` gets the level `_SHAPE` issue, and amortisation `(-0)` gets its `_SHAPE` issue;
- `(425)` with `425` still gets "does not occur".
- Probe `<S>/cp3d-r10-review/p_tip_sign_rule.py` exits 0, and check C now shows the `_SHAPE` issue. Output: `<S>/cp3d-class/p_tip_sign_rule.out`.

**B1 tests the library cases do not reach:**
- `test_r11_b1_every_occurrence_in_every_page_reading`: a minus across a page wrap, one of two occurrences cut, and `.` before the figure, each with an accepted counterpart;
- `test_r11_b1_a_wrapped_quote_is_read_joined_on_the_page`;
- `test_r11_b1_a_full_stop_after_the_figure_is_still_its_end_edge` (`The level is 25.` against `25.5`).
- The 25.5 test was written after the fix; the mutant that drops `.` from `_EDGE_AFTER` shows it fails without it.

**Mutants.** Script: `<S>/cp3d-class/mutants.py`. It ran on a full temporary copy with `PYTHONDONTWRITEBYTECODE=1` and exits 0; output is in `<S>/cp3d-class/mutants.out`.
- The unmutated copy exits 0. All 22 mutants exit 1 (killed):
  - B1 off;
  - B1 per caller: observations, margin/amortisation, reference-rate level;
  - B1 parts: page joined reading dropped, quote joined needle dropped, last occurrence only, start digit and `.`, start `.`, start minus, closed parentheses, end digit, end `.` plus digit, end edge `.`, start edge off, end edge off;
  - B3 off, B3 off for instrument.name, B3 off for reference_rate.name;
  - blank off, blank "only `""`";
  - B2 revert.

**Gates (all exit 0)**
- `pytest tests/test_method_cp3d.py`: 650 passed. Every frozen case still passes unchanged, including `test_every_oracle_literal_still_validates`.
- `ruff check`, `ruff format --check` and `MYPYPATH=src mypy --strict` on both files.
- `tests/test_defect_classes_selfcheck.py` also passes: 152 passed.

**Stage 2 notes for `methods/cp3d.md`** (not written; outside my allowed files):
- Quote readers read signs per round 10, with parentheses only around a token that starts with a digit (B2). A figure at a quote edge is checked on the page at every occurrence, in every reading (B1). A wrapped quote does not hold a name spelled with `- ` (B3).
- Blank analyst text gets `<path>: empty text`; no frame is pinned for CP-3D. For a blank name, the "does not occur" issue may also appear: it does for `"\t "`, not for `" "`.
- The unsigned grammars are a lease limitation (round 10): CP-3D cannot record a negative reference rate.
- `technicals[i].limitation = ""` now gets `empty text` as well as the existing "limitation is required" issue.

**Not verified:**
- The scratchpad inventory runner (`<S>/defect-classes/inventory.py`) was not re-run, because it is hard-wired to the `defect-classes` worktree; my test file covers the same cases.
- No full suite was run (deferred to LEAD's final phase).
- No frozen pages beyond CP-3D's own were checked.
- One case the rulings do not pin: a quote that wraps right after a minus (`is -\n25`) reads `- 25` under `normalise`, so it is unsigned by round 10. B1 does not catch it, because the joined needle's `-25` is not an edge token.
- GitNexus `detect_changes` was not run; this agent has no MCP tools for it.

Ledger: `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y`

`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`
