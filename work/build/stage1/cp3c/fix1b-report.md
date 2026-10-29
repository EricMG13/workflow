CP-3C fix 1b: B1, Q3, B2 and B5 from LEAD round 11 are applied test-first, and all gates exit 0. Commit b9972fd is on branch worktree-agent-aa5a4817fa00cd287, in worktree /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-aa5a4817fa00cd287.

**Step 0:** the lane merge is fd66af1. It was clean, with no conflicts. Its parents are 8a45037 (fix 1) and b6c3392, and b6c3392 equals the lane tip (`git rev-parse claude/module-dev-status-review-0981b6`).

**Files changed:** only `src/deploy_workflow/owners/cp3c.py` and `tests/test_method_cp3c.py`. Each new or changed test below was red for its reported cause before the code change.

**Ruling → change → test:**
- **B1, maturity before D0.** In `_facility`, in the unstated date's position slot:
  - The date stays known. Months and the inside flag become `Gap("Not calculable: facility <id> maturity date is before the balance date")`, and every listed dependant takes that reason through the existing precedence.
  - Total principal, shares, creditor rows and the nearest date stay known. The copies are verbatim, with no wall cross-check line.
  - The own line is written as ruled: label `Facility maturity date (<id>)`, kind Limitation. The claim cause is the ruled one.
  - Fix 1's raise is removed.
  - Tests: `test_b1_a_maturity_before_the_balance_date_is_a_gap` (red was the old ValueError) and `test_b1_a_maturity_on_the_balance_date_is_zero_months`.
- **Q3, id-free causes.**
  - `Gap` has a new `cause` field (`compare=False`). It is set where the gap is made, by kind:
    - unstated principal, maturity date, annual amortisation, secured status, seniority or currency;
    - unmatched facility;
    - pre-D0;
    - FX (8-B2).
  - `_because` takes the refinancing Gap (`total_need` or `junior_claims`) and returns its `cause`, or else the reason without its prefix. Reason strings are no longer compared.
  - The `names=` change and the `_Claims` ids are dropped, so `prose.check` takes no facility ids.
  - Tests:
    - `test_q3_causes_carry_no_facility_id` (ids `tl2`/`tla1`; NEED-01 and LME-01);
    - `test_q3_an_unmatched_facility_takes_the_register_and_wall_frame`;
    - existing tests updated to the new frames: `test_c3_need_claim_names_the_unstated_amortisation`, `test_c3_lme_claim_names_the_unstated_ranking`, `test_b6_a_usd_facility_without_a_wall_principal` and the A39 test.
- **B2, one line per unstated term.**
  - Annual amortisation gets the maturity-wall text. Secured status and seniority each get their own creditor-position line, whether the term is missing or NOT_STATED. All are kind Gap with the ruled labels.
  - The order is the ruled one: currency, maturity date (unstated or pre-D0), principal, annual amortisation, secured status, seniority, wall rows, unmatched lines, path lines.
  - Tests:
    - `test_b2_no_currency_undated_and_every_term_unstated`;
    - `test_b2_principal_terms_then_the_wall_row_lines`;
    - `test_b2_a_pre_d0_line_comes_before_the_principal_line`.
- **B5, blank II limitation.** The check is `not (p.limitation or "").strip()`, which gives the pinned issue at its current position. Test: `test_b5_a_blank_insufficient_information_limitation_is_refused` (`""`, `" "`, `"\t\n"`).
- **Frozen values:** none moved. The pack, claim and limitation oracle tests pass unchanged.

**New strings:** `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3c-fix1b/prose_probe.py` exits 0 with no hits. It checks:
- every claim in nine states (pre-D0, unmatched, each unstated term, ids `tl2`/`tla1`, FX), using `prose.check` without names, plus `bare_figures` on the claim text runs;
- the nine cause frames, using `prose.issues` and `bare_figures`.

The own-line texts are outside the claim prose check (6f item 3).

**Probes** (in `<S>/cp3c-fix1b/`; `probe_root` points at a full copy of the fixed tree):
- Updated to the ruled behaviour; none retired, because every state still exists:
  - `probe_past_maturity.py`: 0. It now checks the B1 gap, the own line, the ledger row and the cause.
  - `probe_empty_register.py`: 0. B3: an empty register with a wall row is the C-6 unmatched state.
  - `probe_burden_collision.py`: 0. B4 as built: r08 keeps the numerator's gap, and there is no EBITDA clause.
  - `probe_negative_amort_months.py`: 0. Part 1 is B6, recorded as a guard limit and printed only. Part 2 is the B1 gap.
- `probe_survivor_states.py`: 0. Its A39 expectation also encoded an id-bearing cause, so I updated it to the Q3 frame as well.
- `probe_digit_id.py`: 0.
- `probe_negative_principal.py`: 1. The L1 part passes. The two failures are the negative-principal and amortisation sign questions (reviewer item 5, B6 territory).
- `probe_precision.py`: 1. The builder-precision equality holds; the conservation residue is 3E-59, which no finite precision can remove.

**Mutants:** `<S>/cp3c-fix1b/run_mutants.py` on a full temp copy, with `PYTHONDONTWRITEBYTECODE=1`; the source was restored to the same sha.
- Every revert is killed:
  - B1a–e (negative months computed, `<=` D0, own line dropped, line kind Gap, cause dropped);
  - Q3a–e (cause from the reason, and each frame dropped);
  - B2a–e (amortisation line dropped, ranking lines dropped, wrong text, missing fact not lined, amortisation before principal);
  - B5a;
  - A16′, L1a and L1b from fix 1.
- Left:
  - A19 and A44 are Info, as before.
  - A39's pattern no longer exists: Q3 removed the reason-string comparison. That behaviour is covered by Q3a and the A39 test.
  - Fix 1's M1 and M2 mutants are dropped along with the code they targeted.

**Gates:** pytest 166 passed (exit 0); `ruff check` 0; `ruff format --check` 0; `mypy --strict` 0. They were not first pass:
- `test_c3_lme_claim_names_the_unstated_ranking` needed the Q3 frame;
- `ruff check` flagged three things, all fixed: `field` shadowed (now imported as `_field`), TRY004 (now `TypeError`), and ISC004 in two tests.

**Stage 2 notes:**
- `methods/cp3c.md` entry for B3: an empty CP-1 register with a non-empty CP-2D wall is the C-6 unmatched state, not 8-B5's "empty register overrides". NO_FACILITY applies only when both are empty.
- `methods/cp3c.md` entry for B6: a guard limit. A negative annual amortisation or principal computes as given: the Method's formula has no sign guard, and these states are reachable only from heads CP-1 refuses.
- MC-2 needs only the issuer name (lease :140), because claims no longer carry facility ids.
- I could not write `methods/cp3c.md`; it is outside my file list.

Not verified:
- Q2(f) is not built, per the controller's decision.
- The CP-2D side of B1 is not built; it rides with CP-2D's next change.
- `_because` raises `TypeError` for a known value. That path is unreachable from `_claims`, and no test exercises it.
- GitNexus `detect_changes` was not run.
- Only the brief's gates were run, not the full repository suite.

agent=general-purpose(opus) fix-rounds=1 gates-first-pass=n
