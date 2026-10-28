## Defect-class library and inventory: report

I built the shared defect-class library and its self-check, committed them, and ran every case against every owner on the lane. Round 10 holds everywhere it applies. The round 11 rules (B1 edge cut, B3 wrap refusal, blank text) are not built in any module yet. No owner, `cases/` or `src/deploy_vii` file was touched.

**Commit:** `c032752` on `claude/defect-classes`, in worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/defect-classes`. Step 0 confirmed HEAD = lane tip b6c3392 before any work. Two files:
- `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/defect-classes/tests/defect_classes.py` (helper module, not collected)
- `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/defect-classes/tests/test_defect_classes_selfcheck.py`

### The library
- **Adapter protocol:** `Adapter = Callable[[str, str, str], Sequence[str]]`, (page, quote, value) to issues. The library imports no owner.
- **Helpers:** `quote_failure(case, adapter, refusal)`, `blank_failure(case, adapter, expected)`, `label_cases(label, figure)`, and `EMPTY_TEXT = "{path}: empty text"`.
- **Two figures:** the figure and label cases run once with `25` and once with `1.25`. CP-8's sizes and levels accept only N.NN, so with `25` alone nearly all CP-8 cases were n/a.
- **Twins:** every refused case names an accepted twin with the same value.

### Cases and their ruling source
- **Genuine figures** (`25`, `1.25`, `0`, `0.25`), the twins: R10 §1.
- **Soft hyphen:**
  - inside a figure: `2­5` accepted; `1­25` with value 25 refused;
  - inside a label: accepted;
  - inside a name: accepted.
  - Source: R9 CP-8 heading ("M1's normalised quote applies to every new check") plus the R11 shared class test list.
- **Dashes and minus:**
  - em dash before the figure: refused;
  - en dash, em dash or U+2212 inside a range (`9–25`): accepted.
  - Source: R10 §1.
- **NBSP:** before or after a figure, between a label and a figure, and inside a name: all accepted. Source: R9 M1.
- **Signs and parentheses:**
  - `−25`, `-25`, `–25`, `(25)` refused for an unsigned 25 (also as 1.25);
  - `1-December`, `2024-2025`, `95-96`, `S-350`, `mid-25`, `+25` and `(25 percent)` accepted.
  - A signed figure right after a label, with the unsigned figure later in the quote: refused at the label check.
  - Source: R10 §1 and Parentheses; the label case from R10's CP-3D, CP-8 and CP-2E bullets.
- **Edge cut (R11 B1):**
  - refused: the five ruling examples (`425`, `0` from `10`, `0.25` from `-0.25`, `25)`, `(25`), plus two cuts I derived from the B1 end-edge rule (`25` from `250`, `25` from `25.5`);
  - accepted: a genuine figure at the start, at the end, before a full stop, and `25` cut from `mid-25`.
- **Wrap (R11 B3):** with a wrapped quote, the value `first- priority` is refused; the re-quoted, joined spelling is accepted.
- **Blank text:** `""`, `"   "`, `"\n"`, `" "`, `"\t "` in every analyst text field. Source: R11 "Blank text is one defect class".

### Inventory, module × class
Probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/defect-classes/inventory.py`, with adapters in `adapters/` beside it. It exits 1 by design. Full output is in `inventory.out` and `inventory-detail.out` in the same folder.

Genuine, soft hyphen, dashes, NBSP and signs pass in all four quote readers, so they are left out of this table.

| Module | Edge cut (B1) | Wrap (B3) | Blank text | Failing example |
|---|---|---|---|---|
| CP-3D | FAIL 26/42 | FAIL 2/4 | FAIL 75/75 | `margin` 25 cut from `425` is accepted; `instrument.name` with `first- priority` is accepted; whitespace text passes |
| CP-8 | FAIL 6/21 | FAIL 3/6 | pass | `downside_sizes[0].level_text` 1.25 cut from `41.25` is accepted; `decision.instrument` wrap is accepted |
| CP-2E | FAIL 13/21 | FAIL 1/2 | FAIL 65/65 | `fx.foreign_ebitda_share` 25 cut from `425` is accepted; `reference_rate` wrap is accepted |
| CP-1D | FAIL 12/21 | n/a | FAIL 40/40 (6 schema) | basis `25` cut from `425` composes instead of giving exactly-one |
| CP-1C | – | – | FAIL 40/40 | – |
| CP-2D | – | – | FAIL 30/30 (5 schema) | – |
| CP-2G | – | – | FAIL 45/115 | every `limitation` passes blank |
| CP-DR | – | – | FAIL 15/15 (2 schema) | – |
| CP-L10 | – | – | FAIL 19/35 | `""` gets a shape issue, not the frame; three fields have no check |
| CP-2A, CP-3, CP-4, CP-5 | – | – | pass | – |

- **Other quote readers:** none found beyond the four. CP-1C reads table cells only, which round 10 puts out of class; CP-2D, CP-2G, CP-DR, CP-L10, CP-3, CP-4 and CP-5 read no value from an analyst quote.
- **No submission at all:** CP-1A and CP-2 have no analyst submission.

### Analyst text fields, and whether whitespace-only text passes today
Each owner's full list (path and type) is in the probe output. Summary:

- **CP-1C:**
  - fields: `assessments[0].rationale`, `.limitation`, `overall.rationale`, `.limitation`, `gaps[0].{gap, why_it_matters, affected_analysis, action}`;
  - all `str`, all pass blank today;
  - no pinned frame.
- **CP-1D:**
  - fields: `assessments[0].rationale`, `.limitation`, `overall.rationale`, `.limitation`, `gaps[0].{gap, why_it_matters, affected_analysis, action}`;
  - all pass blank today;
  - the `Text` fields refuse `""` only through the pydantic schema;
  - no pinned frame.
- **CP-2A:**
  - fields: `scenarios[0].{name, rationale, limitation}`, `thresholds[0].{label, rationale}`, `assessment.{rationale, limitation}`, `gaps[0].*`;
  - all refused with the pinned `<path>: empty text` (ruling M4).
- **CP-2D:**
  - fields: `assessments[0].text`, `.credit_implication`, `minimum_cash.rationale`, `minimum_cash_absence.{reason, follow_up}` all pass blank;
  - `assessments[2].limitation` gets only "an Insufficient Information assessment states its limitation";
  - no pinned frame.
- **CP-2E:**
  - fields: `shock_rationale`, `assessments[0].text`, `[2].limitation`, `summary.text`, `hedge_ratio.rationale`, and the reason and follow_up of the hedge, operating FX, rate and debt-currency absences;
  - all pass blank today;
  - no pinned frame.
- **CP-2G:**
  - 15 rationale and gap fields are refused with the pinned `<path>: empty text`;
  - the 9 `*.limitation` fields pass blank.
- **CP-3D:**
  - 13 fields pass blank: absence reasons and follow-ups, `recovery.rationale`, `technicals[*].text` and `.limitation`, `summary.text`;
  - `instrument.name` and `reference_rate.name` are refused only by "name does not occur in the quote", and `""` or `" "` pass;
  - no pinned frame.
- **CP-8:**
  - all 25 fields are refused with the pinned `<path>: text is empty` (r27 / round 9 item 1): decision texts, absences, `attributions[0].basis`, `lessons[0].lesson`, `extra_gaps[0].*`, `synthesis.text`, `outcome_absence.*`.
- **CP-DR:**
  - `gaps[0].questions[0].text`, `.answer` and `questions[2].limitation` pass blank;
  - no pinned frame.
- **CP-L10:**
  - `assessments[0].assessment`, `.credit_transmission`, `overall.rationale` and `gaps[0].gap` are refused with `<path>: empty` (pinned by r11 and r17; for the assessments only by lease step 4);
  - `overall.limitation`, `gaps[0].why_it_matters` and `.action` pass blank.
- **CP-3, CP-4, CP-5:**
  - all refused with the engines' `<path>: empty text`;
  - only CP-5's `claim_reviews[].rationale` is oracle-pinned (`cp5-empty-rationale`); CP-3 and CP-4 have no pinned frame.
- **No pinned empty-text frame:** CP-1C, CP-1D, CP-2D, CP-2E, CP-3D, CP-DR, and CP-3 and CP-4 (their engines emit one, but no oracle pins it). These get the fallback `<path>: empty text`.

### Decision for you
For `Text` fields (`min_length=1`), `""` is refused by pydantic before the empty-text frame can fire. The inventory counts that as a fail, shown as "schema N" (CP-1D, CP-2D, CP-DR; CP-L10 gets a shape issue instead). The ruling names the frame, but you may want to accept schema refusal of `""` and require the frame only for whitespace.

### Cases left out (the rulings do not pin them)
- A value that itself carries a soft hyphen or NBSP, or a joined value against a wrapped quote.
- `- ` in a value when the quote is not wrapped.
- A refused soft-hyphen name.
- A page minus followed by a line break before the digits (R11 lists this as not examined).
- CP-3D's `(-425)` (B2, Modules' decision).
- CP-2E's statement `row` reader (out of class under round 10).

### How the adapters judge cases (probe-side choices, not owner behaviour)
- A case is n/a where a field folds its own bound into the same refusal wording: CP-8 holds only N.NN, CP-2E's FX share caps at 100, CP-1D needs an amount above 0.
- CP-1D has no analyst figure, so its refused soft-hyphen case is n/a. Its accepted cases whose quote prints two figures are n/a, because CP-1D's pinned exactly-one rule refuses those by design.
- CP-1D runs on gap row 3 made Partly supported and Recurring. Accepted cases there also get "Recurrence does not fit the add-back type", which is outside the class.
- For label cases, and some text cases, adapters add a date sentence or a floating-rate phrase to both page and quote, as the module requires. Figure cases are never modified.
- The CP-2E sign-label refusal was set to the "is not labelled" frame, because round 10 places that refusal at the label check. The first CP-2E adapter draft expected "does not occur" there.

### Gates (all exit 0; the first run of each passed)
- pytest on `tests/test_defect_classes_selfcheck.py`: 144 passed.
- `ruff check` and `ruff format --check` on both files.
- `MYPYPATH=src mypy --strict` on both files.

Not verified: no module's own test file runs these cases yet (that is the next fix rounds), and the full pytest suite was not run. The probe adapters are scratch code with no gate: 11 ruff findings remain, under the repo config. CP-1D's composed basis value was not compared with the page figure; only its refusals were checked. Index-0 items stand in for repeated items, and some absence and limitation fields needed a minimal state change to be set (noted per owner in the probe output). CP-5's contradiction fields are run on a contradiction the adapter adds. The CP-2D, CP-2G, CP-L10, CP-3, CP-4 and CP-5 frame citations come from sub-agent adapters and were not re-checked against the leases.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y
