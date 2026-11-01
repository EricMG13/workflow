# Redesign 2: step-by-step form (user, 2026-10-31)

Same rules as brief.md and fix-1.md (they still hold unless changed here). Edit only
docs/templates/context-form.html. Do not commit. Keep the `context/1` output, validation
rules, implication texts, palette and the "What this run will do" panel as they are.

User's requirements:
1. The user moves **section by section**, not down one long page, and **cannot move forward
   until the current section's requirements are met**.
2. **Examples** throughout, and it is **clear what is mandatory and what is not**.

## Steps

One section visible at a time. The step sequence:

1 Run type · 2 Issuer · 3 Dates · 4 Deal terms (only when run type is Primary; otherwise not
in the sequence) · 5 Market quotes · 6 Ratings · 7 Valuation · 8 Assumptions · 9 Attachments ·
10 Research questions · 11 Review & download.

Step numbers shown to the user are positions in the current sequence (so without Primary the
user sees 10 steps, numbered 1-10). Changing run type rebuilds the sequence; data already
entered in a removed step stays in the form but is not written (as today).

## Navigation and gating

- Header: a stepper replaces the section chips. Each step shows its number, short name and a
  state: Done (✓), Current, Optional (if the step has no required fields), or Locked. A step is
  Locked while any earlier step in the sequence is invalid. Done and the current step are
  clickable; Locked steps are not (`aria-disabled="true"`, no click effect). Use
  `aria-current="step"` on the current one. On narrow screens the stepper collapses to
  "Step 3 of 10 · Dates" with a thin progress bar.
- Footer of each step: **Back** (not on step 1) and **Next**. On Optional steps where nothing
  was entered, Next reads **Skip**. On the last data step, Next reads **Review**.
- **Gate:** Next always looks clickable but does not advance while the step has errors.
  Beside it, a live line: "2 required fields left" (or "Ready" when none). Clicking Next on an
  invalid step shows the step's errors inline and in a short list at the top of the step,
  each linked to its field, and focuses the first invalid field. Errors are not shown before
  the user first tries Next or leaves a field (no red on an untouched form).
- Moving to a step moves focus to that step's heading. Scroll to top on step change.
- A step that later becomes invalid (e.g. the user returns to step 1 and switches to Earnings
  update, making periods required) locks every later step until fixed; the stepper shows it as
  "Needs attention".
- **Review & download** (last step): a read-only summary of every step's answers (skipped
  optional steps say "Skipped: optional"), each with an **Edit** link to its step, the panel's
  consequences, and the Download button. Download stays disabled while any step is invalid.
- **Load existing context.json** moves to step 1 (as "Start from a saved file"). After a
  successful load, go to the first invalid step, or to Review if all are valid. Reset returns
  to step 1 after its confirm.
- The "What this run will do" panel stays visible beside every step (and under 900px stays the
  collapsible block under the stepper).

## Mandatory vs optional

- A legend at the top of every step: "**Required** fields must be filled to continue.
  **Recommended** fields improve the analysis. Everything else is optional."
- Every field label carries exactly one tag: **Required** (text tag, `--rb-neg` text on
  `--rb-neg-tint`), **Recommended** (`--rb-caut` on `--rb-caut-tint`), or **Optional**
  (`--rb-ink-2` on `--rb-neu-tint`). Conditional ones say when: "Required for Earnings update",
  "Required when listed". The tag must update when the condition changes. Required inputs also
  get `aria-required="true"`.
- Step heading line under the title: "2 required fields" / "Optional step: you can skip it" /
  "Required: at least one facility row".
- Classification (keep all existing row-level rules):
  - Step 1: run type, pathway, filing status: Required (all have defaults).
  - Step 2: issuer_name, issuer_id Required; borrower_name, sector Recommended; ticker
    Recommended when listed; the rest Optional.
  - Step 3: as_of, reporting_currency Required; current_period and prior_period Required for
    Earnings update, otherwise Recommended.
  - Step 4 (Primary): at least one facility row Required; inside a row keep today's required
    fields and mark the rest Optional.
  - Step 5: Recommended for Secondary (say why: "Without quotes CP-3 states Insufficient
    Information"), Optional otherwise.
  - Steps 6, 8, 9, 10: Optional steps (row fields required once a row exists, as today).
  - Step 7: Required fields only as each choice demands (today's rules); default choices need
    nothing.

## Examples

- Every text and number input has a placeholder starting with "e.g." using fictional values,
  and help text giving the format. Use these (adjust only where a field is not listed):
  issuer "e.g. Northbridge Group"; borrower "e.g. Northbridge Holdings LLC"; parent
  "e.g. Northbridge Topco Ltd"; guarantors "e.g. Northbridge Opco LLC, Northbridge IP LLC";
  aliases "e.g. Northbridge, NBG"; ticker "e.g. NBG"; sector "e.g. Gaming & Leisure"; country
  "e.g. United States"; sponsor "e.g. Harbour Peak Capital"; periods "e.g. q3-2026" and
  "e.g. q2-2026"; currency "e.g. USD"; facility_id "e.g. tlb-2031"; size_m "e.g. 1250";
  tenor_years "e.g. 7"; spread talk "e.g. 325" / "e.g. 350" (help: "basis points over the
  reference rate"); OID talk "e.g. 99.0" / "e.g. 99.5" (help: "price per 100"); floor
  "e.g. 0.50" (help: "percent"); call protection "e.g. 101 soft call, 6 months"; use of proceeds
  "e.g. Refinance 2027 term loan"; provider "e.g. Lead arranger"; bid/ask "e.g. 98.50" /
  "e.g. 99.00"; yield "e.g. 8.25"; spread "e.g. 340"; rating "e.g. B+ or B1"; peer name
  "e.g. Harbour Leisure Inc"; EV "e.g. 5400" (help: "millions"); EBITDA "e.g. 600"; multiple
  "e.g. 8.5"; rationale "e.g. Mid-point of 2024-26 sector LBO multiples"; research question
  "e.g. How much of 2025 adjusted EBITDA is run-rate cost savings?".
- Placeholders are examples only: never written to the JSON, never counted as filled.
- Each step opens with one sentence on what the step is for, and, for steps with rows, a small
  greyed example row (labelled "Example", not an input) above the empty rows.

## Unchanged

Output JSON shape and order, all validation bounds, implication texts, panel gating (fix-1),
load safety (fix-1), offline/CSP rules, accessibility rules, 11px minimum text.

Report as text: what changed, how gating works, the exit codes of
`p1_syntax_network.sh <html>` and `p2_planned_gating.sh <html>` (probes folder as in fix-1),
and a final `Not verified:` line.
