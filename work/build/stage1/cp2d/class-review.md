## CP-2D Stage 1 class round review (commit 4a0607e, diff 4dfc5ff..4a0607e)

I found no High or Medium defect, so this is APPROVE. The spec and quality verdicts are separate below. There is one Low finding, a test gap; the code is correct there. It can ride with CP-2D's next change. Two Info items are judgement calls.

**Spec verdict: APPROVE.** The diff stays inside the brief's limits:
- Only `src/deploy_workflow/owners/cp2d.py` and `tests/test_method_cp2d.py` changed, +304/−42.
- `cases/`, `src/deploy_vii` and `tests/defect_classes.py` are untouched.
- Every frozen case passes unchanged.

**Quality verdict: APPROVE, with one Low finding.** The diff has no stub, fake value or catch-all. The two `assert`s in the touched code (cp2d.py:360 and :428) were already there before this change.

### 1. Maturity before D0, against the ruling (probe `probe_pre_d0.py`, exit 0)
- **Reason string:** `PRE_D0` at cp2d.py:206 is identical to `cp3c.PRE_D0`.
- **Which cells go missing:** the probe swept D0 − 3 days to D0 + 3 days. With a maturity of D0 − 1 day, exactly these cells take the reason: T2E.4.r01.c3 and c4, T2E.3.r06, r07 and r08, and T2E.5.r01, r03, r05, r06 and r07.
  - Every other changed cell is the date itself, which stays known.
  - No cell carries a different reason.
  - Known, as the ruling and CP-3C require: the date (c2), principal (c1), share (c5), cumulative share (c6), the runway (T2E.3.r09) and T2E.2.r06.
- **Dependants:** in other facilities, months and inside-horizon stay known (48 months, False).
- **Own line:** the text at cp2d.py:721 is identical to CP-3C's `_PRE_D0_LINE`. Its label is `Facility maturity date (<id>)` and its kind is Limitation. There is one line, in the maturity-date slot after the FX line (cp2d.py:770). It is still written when the facility is also in a foreign currency.
- **GAP-01 cause:** the template reads `...[T2E.5.r07] needs every facility to mature on or after the balance date, and one does not.` It carries no facility id.
  - The cause sits in the maturity-date slot (cp2d.py:1248): after FX and currency, before principal.
  - When a facility is in a foreign currency and also matures before D0, GAP-01 gives the "in USD" cause, which is the correct order.
- **No off-by-one:** the test is strict `<` (cp2d.py:296). On D0 the months are 0, inside-horizon is "Yes", the principal counts, and there is no pre-D0 line. D0 − 1 day takes the gap.
- **`maturity_inside_horizon`:**
  - It is True when another facility is known to fall inside the horizon, and "Interest after maturity" is then written.
  - It takes the pre-D0 reason when the other facility matures after the horizon.
  - When the other facility is undated, the pre-D0 facility sorts first in wall order, so its reason wins.
- **Prose checks:** I bound a fact set built from the composed result's cells. GAP-01 and MAT-01 are both clean under `prose.issues` (the templates; the rendered `.text` is the wrong input). `bare_figures` is clean on the reason, the own line, the label, the cause and the literal part of GAP-01.
- **The implementer's two choices where the ruling is silent:**
  - **Cumulative share stays known.** This matches CP-3C B1 ("shares ... stay known"). An undated facility makes it missing only because its wall order is unknown; a facility dated before D0 has a known order. Consistent, no question for LEAD.
  - **MAT-01 keeps its chip form.** This is consistent: in CP-2D the L5 cause frame is used for MAT-01 only for FX and currency (MAT_FX and MAT_CURRENCY), and an unstated maturity date already gives the chip form. Info only: the ruling's "Claim cause, in the L5 frame" does not name a claim, so LEAD may confirm it is GAP-01 alone.

### 2. Blank text (probes `probe_blank.py` and `probe_frozen_refusals.py`, both exit 0)
- **Coverage:** all 11 fields are caught. I tested every assessment index (0–2) × text, credit_implication and limitation × five whitespace forms (space, tab, newline, non-breaking space, `"  \r\n"`), plus `minimum_cash.rationale` and both `minimum_cash_absence` fields. A fourth, duplicate assessment reports path index `[3]`.
- **Placement:** the frame is `<path>: empty text`. It comes after HORIZON_ISSUE and SECTION_ISSUE, and before the DIGIT, CONCLUSION, BASIS and LIMITATION issues.
- **Frozen order:** none moves. The 13 frozen refusal inputs give exactly their issues with no empty-text issue, and no frozen submission field is blank.
- **Missing fields:** none. Every `Text` and `str` field in the submission model (cp2d.py:45-70) is listed.
- **Schema refusal of `""`:** it still stands for the `Text` fields; a ValidationError is raised.
- **Info, `""` limitation:** `Assessment.limitation` is `str | None`, so the schema does not refuse `""`. A `""` limitation now gets `assessments[i].limitation: empty text` in addition to the existing INSUFFICIENT_ISSUE or LIMITATION_ISSUE. A whitespace-only limitation on an Insufficient Information assessment also gets both issues. CP-3C B5 instead gives only its pinned Insufficient Information frame. CP-2D pins no empty-text frame, so the fallback is within the ruling. No frozen case uses `""`; the oracle uses None. Raise this with LEAD only if a single issue is wanted.

### 3. The `_texts` → `analyst_text_fields` rename
There is no change in behaviour. No caller outside cp2d.py ever used `_texts`; I checked at 4dfc5ff with `git grep`. The new function returns the same texts in the same order as the old one, which `probe_blank.py` asserts.

### 4. Findings
- **Low: the order of the two schedule-cell reasons is not pinned by any test.** When a facility is in a foreign currency and also matures before D0, `blocked = _currency_gap(f) or _position_gap(f, balance_date)` at cp2d.py:356 is correct: the cells take the FX reason (shown in `probe_pre_d0.py`). That keeps the precedence the ruling requires ("in the position slot that an unstated maturity date takes ... every existing precedence holds"). But swapping the two operands survives the suite (pytest exit 0). The fix is one test: a facility in EUR that matures before D0 must give T2E.3.r07 the FX reason. Probe: `mutants_review.py`, mutant "schedule: pre-D0 before currency".
- **Info: MAT-01 chip form.** See section 1. Probe: `probe_pre_d0.py`.
- **Info: double issue on a blank limitation.** See section 2. Probe: `probe_blank.py`.

### 5. Probe and mutant exit codes
- `probe_pre_d0.py`: exit 0.
- `probe_blank.py`: exit 0.
- `probe_frozen_refusals.py`: exit 0.
- The implementer's `cp2d-class/mutants.py`, rerun from a full temporary copy with PYTHONDONTWRITEBYTECODE=1: exit 0. All 14 mutants are killed, each with pytest exit 1.
- My `mutants_review.py`: exit 1. 14 of its 15 mutants are killed (exit 1); 1 survives (exit 0):
  - Killed: the wall's cumulative share made missing, its inside cell kept known, its months kept known, its date made missing; the inside fallback ignoring the pre-D0 reason; a pre-D0 facility counted as inside; the own line written after all the terms; the own line's label wording; the reason wording; the cause placed before currency; blank issues placed before SECTION_ISSUE; 1-based paths; the limitation field dropped; the follow_up field dropped.
  - Survived: "schedule: pre-D0 before currency" (the Low finding).
- My mutant script counts a mutant as killed only on pytest exit 1. The implementer's script also counts exit 2 (a collection error) as killed, but none of its mutants exited 2.

### Gates (each exit 0, on 4a0607e)
- `PYTHONPATH=src .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_method_cp2d.py`: 220 passed, exit 0.
- `ruff check` on both files: exit 0.
- `ruff format --check` on both files: exit 0.
- `MYPYPATH=src mypy --strict` on both files: exit 0.
- The target worktree was clean after review; nothing was edited or committed.

### Probes
All are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2d-class-review/`:
- `probe_pre_d0.py`
- `probe_blank.py`
- `probe_frozen_refusals.py`
- `mutants_review.py`

Run the three probes from the worktree root with `PYTHONPATH=src:tests`. Run `mutants_review.py` with the worktree path as its only argument.

Not verified: the bound fact set for `prose.issues` is my own build from the result's cells (unit MILLIONS, currency USD, period "Q4 25"), not the real Stage 2 Fact mapping, which does not exist yet. No other module's suite and no full suite was run. The Stage 2 render was not run. GitNexus `detect_changes` was not run (I have no MCP tools). Whether LEAD wants the pre-D0 cause in MAT-01 too, and a single issue for a blank limitation, is open.
