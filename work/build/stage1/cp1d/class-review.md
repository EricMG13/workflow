**Verdict: CHANGES REQUIRED.** There is one Medium, and it is a test gap. The code is correct; a one-row test fixes it.

**Spec verdict: pass.** B1 and blank text match the ruling text. The 12 exclusions are real. The riding Lows are in place. Nothing frozen moved. The diff is +383/−20, under the 800-line ceiling, and touches only the two files. It adds no issue wording beyond `EMPTY_TEXT`, and B3 is correctly not applied (CP-1D reads no name or text value from a quote).

**Quality verdict: changes required.** One money-relevant B1 rule part is not pinned by any test (M1 below).

## Findings

**M1 (Medium).** `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/cp1d-stage1/src/deploy_workflow/owners/cp1d.py:577`, `shift = 0 if at_start else len(needle) - len(plain)`. No test pins the start-edge branch for a joined (wrapped) quote.
- If the shift is applied at the start edge too, the full suite still passes (pytest exit 0).
- That mutant then counts `25` from `425` for the quote `"25 first-\npriority points."` on the page `"The level is 425 first-priority points."`. A cut figure would compose as the basis amount.
- HEAD is correct: it reads `[]`.
- `test_edge_cut_is_read_in_every_reading` (tests/test_method_cp1d.py:1136) only covers the end edge of a wrapped quote.
- B1 requires "every occurrence of the needle ... plus the joined quote", and sensitive code needs surviving mutants killed or justified.
- Fix: add that start-edge row (cut and whole twin) to tests/test_method_cp1d.py:1136/1154.
- Probes: `p_review_mutants.py` (SURVIVED) and `p_survivor_effects.py`.

**L1 (Low).** cp1d.py:592: the accepted side of the accounting-parenthesis rule is unpinned. Mutating the check to `'(' alone cuts` or `')' alone cuts` survives. Both mutants over-refuse cases the ruling accepts:
- `"25 percent over) holds."` on `"The level (25 percent over) holds."`;
- `"The level is 25"` on `"The level is 25) percent."`.

These fail closed, so no money leaks. A pin should ride with M1's fix. Probes: `p_review_mutants.py`, `p_survivor_effects.py`.

**L2 (Low).** cp1d.py:1692: blank text in `gaps[1+]` is unpinned. The fixtures have exactly one gap, so the `gaps[:1]` mutant survives. HEAD is correct: `gaps[1].action` and `assessments[1].rationale` are both caught. Probes: `p_review_mutants.py`, `p_blank.py`.

**I1 (Info, predates this change; to owner/LEAD, not this task).** A quote with its own hyphen wrap right before the figure drops the page's minus.
- Example: the quote `"The level is -\n1.80"` (or `"is -\n1.80 percent over"`) on the page `"The level is -1.80 percent ..."`.
- `quoted` accepts it through the joined quote reading, but `_basis_amounts` reads only `normalise(quote)` (`"- 1.80"`) and gets `["1.80"]`, with no bounds or exactly-one refusal.
- It reads the same at 864ffe3.
- Round 10 reads the sign on `normalise(quote)` only, and B1 checks the start-edge sign only when the figure is at the start edge. So this is a ruling gap: it is a sign flip in money code. The implementer flagged it as reasoned only.
- Probe: `p_wrap_sign_drop.py`, exit 1 (the defect is present).

**I2 (Info).** `_cited_text` (cp1d.py:545) mutants (first source with the id; last span with the locator) survive. They only matter when a source id or locator is duplicated. The code mirrors `citation_issues` (readiness.py:124/131) exactly. Probe: `p_review_mutants.py`.

**I3 (Info).** The `end test at start-only edge` mutant is equivalent: the greedy digit regex means the text after a start-only figure can never be a digit or `.` plus a digit. Probe: `p_review_mutants.py`.

## Check items

1. **B1 against the ruling.**
   - All parts hold at HEAD: both edges; every occurrence (`find` loop); the plain and joined readings on both the quote and the page side; the page found as `citation_issues` finds it.
   - On every library case and 10 extra scenarios, HEAD agrees with LEAD's `bounded` rule except one row: a whole start-edge figure in a wrapped quote. There HEAD counts it, as the ruling says, and LEAD's probe refuses it because its needle is `normalise(quote)` only. That is a weakness in LEAD's probe, not in the code.
   - The 12 not-applicable cases are all real:
     - `genuine-0` and `edge-start-0` get the bounds text;
     - the soft-hyphen prefix cases read the page's own `125` / `11.25`;
     - the six `*-inside-*` cases and `sign-2024-2025` / `sign-95-96` print two figures and get exactly-one.
   - None hides a defect. Probe: `p_b1_vs_lead.py`, exit 1 only because of that LEAD-probe row.
2. **The three decisions.**
   - **(a) Quote not on its page: a LEAD question, not a defect.** The submission is refused by the citation check either way.
     - Applying LEAD's reading fails only three module tests that use quotes not on their page: `test_basis_amount_at_or_below_zero_is_the_bounds_issue`, `test_basis_amount_outside_the_product_bound_is_an_issue` and `test_basis_amounts_read_the_printed_sign`.
     - No frozen oracle refusal fails, so the frozen data does not force the implementer's choice.
     - Probes: `p_not_on_page_reading.py` (exit 0), `p_edge_pages_lead_copy.py` (LEAD's probe rerun, exit 0).
   - **(b) Leading `-25` read literally: consistent with B1.** LEAD's `bounded` also measures from the digits, so it agrees: exactly-one on a `-25` page, the bounds text on `4-25`. Both are refused. Whether it should be the bounds text (round 10) or exactly-one (B1) is a wording question for LEAD (Info).
   - **(c) Blank issues placed last: consistent.** The rulings pin no position. The `placed first` mutant survives, so no test pins the position either.
     - `Bridge table not found` still comes alone, with blank text unreported, per ruling 1D-x. The `with bridge-not-found` mutant survives.
     - `compute` still raises in that case.
3. **Blank text.**
   - The 11 paths and the `<path>: empty text` frame are correct.
   - `""` on the 8 `Text` paths gives `ValidationError` with `string_too_short`.
   - `""` on the 3 `limitation` paths gives the frame.
   - `addback` is correctly excluded: it is a bridge label and gets `Unknown add-back`.
   - `compute` raises `ValueError("…: empty text")` through `validation_issues`. That is the module's existing refusal contract, not a crash path.
   - No analyst text field is missing. `Citation.quote` and `locator` are refused by the citation check, and the inventory leaves them out.
   - Probe: `p_blank.py`, exit 0.
4. **Riding Lows.** Both are present and each kills its mutant: `test_unstated_amount_rule_precedes_the_bounds_text` (test file :851) and the `("saving 1.80)", ["1.80"])` row (:834).
5. **Frozen readings and stubs.**
   - `p_frozen_readings.py` exits 0: 45 readings, none moved.
   - That check is not vacuous: all 3 distinct frozen basis quotes are on their cited page, and 1 has an edge figure (`p_frozen_located.py`, exit 0).
   - No stub, fake value or catch-all in the diff.
6. **Mutants.**
   - The implementer's `p_class_mutants.py` exits 0: the unmutated copy passes and all 21 mutants are killed.
   - Of my 11 extra mutants (`p_review_mutants.py`, exit 1), 2 are killed and 9 survive: M1, L1 ×2, L2, I2 ×2, I3, and the two position mutants under (c).

## Probe and gate exit codes

All probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp1d-class-review/`.

| Probe | Exit |
|---|---|
| `p_edge_pages_lead_copy.py` | 0 |
| `p_b1_vs_lead.py` | 1 (LEAD-probe row) |
| `p_not_on_page_reading.py` | 0 |
| `p_blank.py` | 0 |
| `p_wrap_sign_drop.py` | 1 (I1) |
| `p_review_mutants.py` | 1 (survivors; output in `review_mutants.out`) |
| `p_survivor_effects.py` | 0 |
| `p_frozen_located.py` | 0 |
| Implementer's `p_frozen_readings.py` (rerun) | 0 |
| Implementer's `p_class_mutants.py` (rerun; output in `impl_mutants.out`) | 0 |

| Gate (run in the cp1d-stage1 worktree) | Exit |
|---|---|
| `pytest tests/test_method_cp1d.py` (263 passed, 1 skipped) | 0 |
| `ruff check` | 0 |
| `ruff format --check` | 0 |
| `MYPYPATH=src mypy --strict` (both files) | 0 |

Not verified: no full suite, CP-2G/CP-2H suites or G1/Stage 2 run; no real (non-synthetic) source text; LEAD's `p_edge_pages.py` was found under another session's scratchpad (`review-wip-worktrees-0145fe/.../round11/`), not under `<S>`, and was run from a copy; whether any pack contract forbids duplicate source ids or locators (I2) was not checked; GitNexus `detect_changes` was not run.
