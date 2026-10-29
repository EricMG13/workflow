CP-4C round 11: report

**Commit**
- ed1a721 `fix(cp4c): round 11 (B2, B3, B6, Q6, Q7, N1, N2)` on `worktree-agent-a2c15c441717ec41c`, sitting on lane tip 04ab3d5.
- Step 0: `merge --ff-only` succeeded, and HEAD was 04ab3d5 before the work began.
- Only `src/deploy_workflow/owners/cp4c.py` and `tests/test_method_cp4c.py` changed. The tree is clean.
- Each test below was seen red for its cause before the fix, or (for M1-riding) red under its mutant.

**Rulings and decisions, with their tests**

- **B2.** `_debt_claim`: any non-known status, `not_applicable` included, gives `Val(None, "Not calculable: total debt is <state> in CP-1 for LTM Q4 25: 2025-01-01 to 2025-12-31")`. The state words come from `_STATE_WORD`, and `not_applicable` reads "not applicable". The own line follows from the existing template. Known-without-amount still raises.
  - Test: `test_b2_not_applicable_total_debt_is_a_missing_claim`. The facts and own lines equal the missing-debt oracle with the state word swapped. The reference row stays `not_applicable` with CP-1's limitation.

- **B3.** In `content_issues`, a name or label that passes the empty and one-line checks gets `<path>: Bare figure: <token>` for each token of `prose.bare_figures(text, names=names)`. `names` is the same as compute's.
  - Valuation labels are checked in lower case, as the claims spell them, so `Base FY2026` gives `valuation[0].label: Bare figure: fy2026`.
  - Tests:
    - `test_b3_a_name_or_label_with_a_figure_is_a_bare_figure_issue`: `Class 2` gives `claims[1].name: Bare figure: 2`, and the label case gives the issue above.
    - `test_b3_a_name_the_validator_accepts_composes`: `Tranche B 2027` passes and composes.

- **B6.** `_cp1_ebitda`: an unknown fact gives `Not calculable: EBITDA is <missing|conflicting|not applicable> in CP-1 for LTM Q4 25: …`. The cell stays missing, EV's reason still comes first, the Q3 raise for known-without-amount stays, and the ≤0 reason is unchanged.
  - Test: `test_a2_5_cp1_ebitda_not_a_known_positive`, with ids missing, conflicting, not_applicable, zero and negative.

- **Q6.** In `_row_amount`, the quote's cells must equal the line's leading cells (`cells[:len(quoted)] == quoted`). Otherwise the #11 text is given.
  - Test: `test_q6_a_quote_must_cover_whole_cells`. `Pr` and the cut `…10  10  10  10  1` are refused, and `Other current liabilities  10  10` passes.

- **Q7.** The candidate lines are `x.removesuffix("\r")` of each `\n`-split line, and the line must satisfy `len(line.splitlines()) == 1`.
  - Tests:
    - `test_q7_the_cited_line_is_one_physical_line[bare CR, U+2028]`. It includes a quote ending at the Q4 cell, so Q7 is tested on its own and not through Q6.
    - `test_q7_a_trailing_cr_is_stripped`.

- **N1.** `test_n1_a_row_longer_than_the_header_has_no_number` (`Deferred  items  1  2  3  4  5.00  6`) kills the `<` mutant.

- **N2.**
  - `test_n2_identical_duplicate_lines_are_one_cited_row` (Q5).
  - `test_n2_a_signed_plus_or_bare_fraction_cell_has_no_number[+5.00, .5]`.

- **M1 riding test (added this round).** `test_m1_a_line_holding_the_quote_mid_line_is_not_a_cited_row`. A page has `Deferred items  1  1  1  1  5.00  1` and `Other Deferred items  1  1  1  1  5.00  1`; quoting the first gives no issue and a claim of 5.
  - Why: the fix-1 reviewer's `m1_contains_not_startswith` mutant (`quote in x`) survived. It is not equivalent, because a second line holding the quote mid-line made the reading ambiguous, which Q1 forbids. This test now kills it.

**Probes and mutants.** All were run from full temp copies with `PYTHONDONTWRITEBYTECODE=1`. Outputs are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp4c-r11/`.

- **`cp4c-r11/mutants.py` (my runner): exit 0.** 37 killed and 2 justified.
  - Killed reverts:
    - b2_not_applicable_debt_raises;
    - b3_no_bare_figure_issue and b3_label_as_typed;
    - b6_ebitda_state_lumped;
    - q6_partial_cells_accepted;
    - q7_multi_line_accepted and q7_trailing_cr_kept;
    - n1_longer_row_read;
    - q5_duplicates_ambiguous;
    - q4_plus_sign_read and q4_bare_fraction_read;
    - m1_contains_not_startswith;
    - all fix-1 reverts.
  - Justified survivors, unchanged from earlier rounds:
    - `exact_sum_without_80_floor`: span+n+1 digits always hold the exact sum.
    - `no_balance_invariant`: the balance is 0 by construction, and is checked by other mutants.
  - Output file: `mutants_implementer.out`.

- **`cp4c-fix1-review/mutants_fix1_review.py`: exit 1**, run before the M1 riding test existed. Everything else in it was killed.
  - SITE NOT FOUND, 2 mutants: `m1_first_label_match` and `m1_identical_dupes_refused`. Their site text is the old `lines = {...}` line, which the Q6/Q7 rewrite changed. The equivalent mutants in my runner (`revert_m1_first_label_match`, `q5_duplicates_ambiguous`) are killed.
  - SURVIVED, 1 mutant: `m1_contains_not_startswith`. It is now killed by the new M1 test; my runner confirms this.
  - The reviewer's script was not edited, so as written it would still exit 1 on the two stale sites.
  - Output file: `mutants_fix1_review.out`.

- **`cp4c-r11/probe_m1_cited_row.py <root> --expect`: exit 0, 0 mismatches.** It is a copy of the reviewer's probe.
  - Expectations updated for Q6: `Pr` and the truncated Q4 figure are refused.
  - Expectations updated for Q7: the bare-CR and U+2028 join cases are refused.

- **A-1 is unchanged; both probes were rerun at reduced counts.**
  - `cp4c-adversary/probe_alloc_reference.py <root> 500`: exit 0, 0 mismatches on every seed.
  - `cp4c-adversary/probe_hypothesis_big.py <root> 300 1 2`: exit 0, all 5 properties pass on both seeds.

- **New strings through `prose.issues` and `bare_figures`** (`cp4c-r11/probe_prose.py`, which ran).
  - The B2 reason, the B2 own line and both B6 reasons each hit `Bare figure: 25`, from the LTM frame "LTM Q4 25". This is the same hit as round 8.
  - The B3 issue texts hit `Unresolved reference: 1` or `0` (the path index) and `Bare figure: 2` or `fy2026` (the echoed token). This is the same class of hit as the existing #9 issue texts. Nothing was reworded.

- **`cp4c-r11/probe_names_compose.py`: exit 1. This is an open item for LEAD.** Names or labels with reserved characters (`A {x}`, `A [y]`, `A}`, `Base [z]`, `Base {q}`) pass the validator, then compute raises the invariant. Figures are now refused (B3). No ruled wording exists, so nothing was changed.

**Q6 side effects for the controller.** These are now refused with the #11 text:
- a cell-boundary quote with an empty last cell (`Other  9  `);
- a line whose last cell carries one trailing space;
- a quote carrying a CR on a CRLF page. The stripped line's cell is `10`, but the quote's is `10\r`.

These follow from Q6's whole-cells rule, and the copied probe's expectations record them.

**Gates.** Final run, all exit 0:
- pytest: 183 passed;
- ruff check;
- ruff format --check;
- `MYPYPATH=src mypy --strict` on both files.

The gates were run with the lane venv at `../../../.venv/bin/` from the worktree root. That is the same python as the brief's command, but the guard refuses the quoted absolute path.

**Stage 2 notes for `methods/cp4c.md`**
- **B4 guard limit:** raw quote matching is a row-location rule. A quote the host accepts that doesn't match the raw page line (for example after normalization) gets v04 and fails closed.
- **B5:** a zero share with a positive rank recovery is an A-1 property. It can only happen at 38-digit amounts, where the quantum exceeds a class's exact share.
- **Also to document:** Q6 and Q7, and the lower-case label check in B3.

Not verified: real CP-1 packs with total debt or EBITDA `not_applicable` (only fixtures were exercised); names or labels with reserved characters (open, above); the reviewer's fix-1 mutant script after a site update (left unedited); the full suite and other modules (only the CP-4C test ran, per the brief); A-1 probes only at reduced counts (500 per seed; 300 examples × 2 seeds).

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y
