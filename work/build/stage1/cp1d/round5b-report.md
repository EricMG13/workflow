# CP-1D: 1D1 oracle amendment and round 5b report (controller-saved)

- **Commits.** On `claude/cp1d-stage1` (worktree `cp1d-stage1`):
  - lane merge ac10dac;
  - cherry-pick of LEAD 2ae589b as `5b83eab`. This commit alone is red, because the citations are not emitted yet;
  - `7e29075`, the green tip.
- **Tests:** 97 passed, 1 skipped (the Stage 2/4 marker), in 0.82 s.
- **Gates:** ruff, ruff format and `mypy --strict` on both files exit 0.

## Rulings
- **1D1.** `T1D.4.proposed_total.reported` and `.mgmt_ebitda.reported` cite their bridge total line, in both the one-sided and the both-sides branch. The positive case was red on exactly these two citations before the fix.
  - Pins: expected 6015b443…, manifest 7e176607…, submissions e19bc64b….
  - Tests: `test_oracle_is_the_pinned_revision`, `test_reported_bridge_totals_cite_their_line`.
- **Y1.** The invariant raise reads `CP-1 fact <fact_id> (<figure>) is outside financial_contracts.Number; CP-1D cannot hold it exactly`.
  - `Cp1Figure` gains a required `fact_id`. Stage 1 passes `cp1:<figure>`, and Stage 2 binds the real interface fact id.
  - Test: `test_cp1_amount_outside_the_product_bound_is_an_invariant_raise` ×4. These were red on the old code.
- **Y2.** This already held. Test: `test_missing_bridge_source_is_not_found`, coverage only.
- **Y3.** A hypothesis property shows that partial-mode issues are a subset of the full module's issues. The chip residual stays a recorded limit.
  - Test: `test_partial_checks_never_exceed_the_full_check`.
- **Y4.** `Accepted basis amount cannot be held exactly as a product amount: <label>` is raised before the bounds comparison. A basis of 1e18 or more against a stated proposed amount keeps the bounds wording.
  - Test: `test_basis_amount_outside_the_product_bound_is_an_issue` ×6. Five were red on the old code.

## Probes (scratchpad)
- Exit 0: probe12, probe11, probe6, probe7b, probe5, probe8 and probe13. probe13's 0.00000000001 basis now gets the Y4 wording.
- `cp1d_rr2_probe9_rulings.py` exits 1. Its "(d)" input, CP-1 EBITDA 1E-38, now hits the Y1 invariant raise, which is the ruled behaviour.
- `cp1d_rr2_probe10_partial_vs_full.py` exits 1. Its DIFF lines are the Y3 recorded residual. The reviewer counted three at the tip: `[T1D.3.claimed.value]`, `[T1D.2.a01.accepted]` and `[T1D.6.statements.cfo]`. 1D1 removed a fourth, `{T1D.4.proposed_total.reported|US$ m}`.

## For LEAD
- The Y1 message gives a `bare_figures` hit on the interpolated fact id (`cp1:adjusted_ebitda_ltm`, or an `interface-fact:<sha>`). The fixed wording is clean.
- B2 is untouched.

## Stage 2 notes
`methods/cp1d.md` gets:
- the Y1 guard limit;
- the Y3 recorded limit;
- the 1D4 note that an unknown bridge type blocks the run.

Not verified:
- any Stage 2 run;
- `{{FIG}}` binding and the overall rationale prose;
- RULES/Seen and the blocked-after-two head;
- FP02 rendering;
- CP-1B inherited lines;
- a real interface fact id in Y1;
- real CP-1 amounts within `Number`;
- a basis cited from a non-bridge source.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y
