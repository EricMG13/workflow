CP-3C fix round 1: all the requested fixes are done and every gate exits 0. Commit 8a45037 is on branch worktree-agent-aa5a4817fa00cd287, in worktree /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-aa5a4817fa00cd287.

**Step 0:** the merge of `claude/module-dev-status-review-0981b6` was clean (eccbbd6), with no conflicts. Round 10 needs no change in CP-3C.

**Files changed:** only `src/deploy_workflow/owners/cp3c.py` and `tests/test_method_cp3c.py`.

**Finding → fix → test.** M1, M2, L1 and L2 were seen red for the reported cause before the fix:
- **M1, maturity before D0.** `_facility` now raises `ValueError("CP-3C {fid}: maturity date {maturity} is before the balance date {balance_date}")` right after it parses the date. That is before `months_from` and before any figure is formed. No user wording.
  - Test: `test_m1_a_maturity_before_the_balance_date_is_an_invariant`.
  - Red was "DID NOT RAISE".
  - The same test also checks that a maturity exactly on D0 is 0 months and still computes.
  - Listed for LEAD.
- **M2, facility ids with digits.** `_Claims` takes the facility ids (`c.ids`) and passes them to `prose.check` as `names=`.
  - Test: `test_m2_facility_ids_with_digits_are_names_not_figures` (ids `tl2` and `tla1`).
  - Red was "Bare figure: tl2".
- **M3, four survivors:**
  - A13: `test_a13_a_positive_cp1_cash_interest_is_a_negative_interest_paid`
  - A18: `test_a18_a_maturity_exactly_on_the_horizon_end_is_inside` (2027-12-31 with H = 24)
  - A25: `test_a25_own_lines_name_currency_then_maturity_date_then_principal`. It compares every own line of the facility, because a slice check let the mutant survive.
  - A39: `test_a39_a_usd_principal_gap_keeps_its_own_cause_beside_a_eur_facility`
- **L1, T3D.5 Base.** `_creditor_rows` now returns the largest claims at or ahead. If the last rank is a gap, it returns that gap, since the last rank holds every facility.
  - Test: `test_l1_junior_claims_are_the_largest_claims_at_or_ahead` (negative junior principal).
  - Red was 20 against 30.
- **L2, precision.** `_CONTEXT` is now `Context(prec=60)`, and the comment cites `cases/cp3c-owner/builder/build.py:19`. Every frozen value stayed equal at 60: the full suite passed unchanged.
  - Test: `test_l2_amounts_are_computed_at_the_builders_precision`.
  - Red was the 28-digit value 2.916…667.
- **Optional Low survivors:** all killed, with these tests:
  - A33, A34: `test_absence_reason_and_path_limitation_are_guarded`
  - A40: `test_the_covenant_guard_window_is_four_words`
  - A35, A36, A37: `test_a_malformed_wall_fact_is_an_invariant`
  - A41: `test_interest_and_ebitda_over_different_periods_is_an_invariant`
  - A42: `test_a_repeated_operand_facility_is_an_invariant`
  - A45: `test_a_claim_template_with_a_bare_figure_is_refused`

**Probes.** I ran these from copies in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3c-fix1/probes/`. There, `probe_root` points at a full copy of the fixed tree; the reviewer's own `probe_root` is the old code.
- **`probe_past_maturity.py`: exit 1.** It now ends on the intended uncaught `ValueError: CP-3C term-loan: maturity date 2025-06-30 is before the balance date 2025-12-31`. The probe does not check for a raise; it still expects figures. The unit test is what checks the raise.
- **`probe_digit_id.py`: exit 0.**
- **`probe_survivor_states.py`: exit 0.**
- **`probe_negative_principal.py`: exit 1.**
  - The L1 check now passes: junior is 50, the largest claims.
  - The two checks that still fail are the negative-principal and amortisation sign questions: −10 amortisation, and resources of 20 against 10. Those are the reviewer's item 5, which goes to LEAD and is not in this round.
- **`probe_precision.py`: exit 1.**
  - The builder-precision part now matches: the amortisation equals the 60-digit value.
  - The exact-conservation part cannot hold at any finite precision. The residue is 3E-59, because 5 × 7 / 12 does not terminate. The builder at prec 60 has the same residue.
- **`mutants.py`: exit 1.** I ran it on a full temp copy with `PYTHONDONTWRITEBYTECODE=1`, through `scratchpad/cp3c-fix1/run_mutants.py`, and the source was restored to the same sha.
  - A16's pattern no longer exists after L1, so I replaced it with A16′ (first rank). I also added L1a (last rank), L1b (min), M1a (guard dropped), M1b (`<=` in the guard) and M2a (names dropped). All are killed.
  - Two survivors remain, and both are Info in the review:
    - A19 (the leap-year rule that drops the 400 case) is equivalent for 1901–2099.
    - A44 (the order of the two wall lines) is unruled.

**Gates:**
- pytest `tests/test_method_cp3c.py`: 158 passed, exit 0.
- `ruff check`: 0.
- `ruff format --check`: 0.
- `MYPYPATH=src mypy --strict`: 0.

**New strings:** only the invariant text. `bare_figures` and `prose.issues` find nothing on the resolved text. On the f-string template, `prose.issues` reports only "Unresolved reference" for its `{fid}`, `{maturity}` and `{balance_date}` placeholders.

**Stage 2 notes:**
- MC-2 must pass the facility ids as `names=` to its prose check, as `_Claims` now does. Otherwise a digit-bearing id such as `tl2` reads as a bare figure.
- The pre-D0 invariant is raised inside `compute`. The Stage 2 caller must surface it as a refusal of the inputs, not a crash, until LEAD rules on it.

**For LEAD:**
- M1: a pre-D0 maturity fails closed, with no ruling behind it.
- The reviewer's items 1–6 are unchanged. Item 5 is still visible in `probe_negative_principal`.

Not verified: a hand-built `Operands` with negative months sent straight to `compose_refinancing` is not guarded, because the M1 guard is in `_facility`, the path from bound facts. GitNexus `detect_changes` was not run (no MCP tools). The full repository suite was not run; only the brief's gate was.

agent=general-purpose(opus) fix-rounds=1 gates-first-pass=y
