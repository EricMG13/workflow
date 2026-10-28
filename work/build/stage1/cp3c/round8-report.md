# CP-3C round 8 Part B report (controller-saved from the implementer's hand-back)

CP-3C round 8 Part B is committed and round 6i is confirmed, with no action needed. The lane merge in step 0 conflicted outside my files, so I aborted it. The branch is therefore not merged with the lane.

**Commit:** `97153a8` on `worktree-agent-aa5a4817fa00cd287`. It sits on `9e78d63` (round 6). Only two files changed:
- `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-aa5a4817fa00cd287/src/deploy_workflow/owners/cp3c.py`
- `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-aa5a4817fa00cd287/tests/test_method_cp3c.py`

The diff is +333/−75.

**Step 0:**
- **Worktree:** `EnterWorktree` refused because the session was already in this worktree.
- **Merge conflict:** `git merge claude/module-dev-status-review-0981b6` conflicted in `docs/CP4C-OWNER-LEASE.md`. The lane's round 8 A-1 header paragraph and the round 6 batch header paragraph meet at the top of the file. The brief says to resolve nothing outside my two files, so I ran `git merge --abort` and the branch stays at the round 6 tip. The conflict looks like it needs both paragraphs kept, but that is your call.
- **Rulings read without the merge:** I read rounds 6f, 6i and 8 from the lane branch with `git show`.
- **Re-pin:** none was needed. `git diff` between HEAD and the lane shows no change in `cases/cp3c-owner`, `cases/cp2d-owner`, the CP-3C lease, or any other `manifest.frozen_inputs` file. The pins stay at:
  - manifest `7a0056a1145f9a92efd11f18fd6512e8c86e508b25176d457f0fe07394ad8a5a`
  - builder `b2cdb63c560abdfdd4387f5d337fb7462c93218b4c24f48c6c4142deaf00bf56`
  - expected `50ef4a7f9199e1da4a73fc75eaaf6bc8215bef12cec26067d2d44aead0952e5f`
  - submissions `8c2b08fa3a7022097aca03798b81a23fd678ba2654ff9ef970a4c02166c34e3c`

**Rulings and their tests.** Every new or changed test was seen failing against the cited raise or the old wording first.
- **8-B1 (figure-or-chip), 8-B4 (unmatched own line), 8-B5 (precedence), 8-B7 (Stage 2 and no builder sync):** confirmed; no code change. The existing round 5 tests cover them.
- **8-B2, the currency cause frames:** `test_c6_a_facility_in_another_currency_uses_the_2d5_wording` now checks `because the total needs every facility in USD, and one is not` on NEED-01 and LME-01, which removes the stacked semicolons. `test_b6_a_t418_row_without_a_currency` checks `…with its currency stated, and one is not`.
- **8-B3, the `Facility <term> (<id>)` (Gap) labels:** covered in the B6 tests below. I added own lines for principal, maturity date and currency only. I added no lines for amortisation or ranking, since no own-line text is ruled for those.
- **8-B6:** every "(not pinned)" raise is gone. What remains are invariants, plus the unknown ranking flag kept per C-6.
  - USD facility with no wall principal: `test_b6_a_usd_facility_without_a_wall_principal`
  - Maturity date not stated: `test_b6_a_facility_without_a_maturity_date`, `test_b6_an_undated_facility_sorts_after_every_dated_one`, `test_b6_an_undated_row_names_its_own_date_before_any_amortisation`
  - Months or inside flag missing while the date is known: `test_b6_a_wall_row_without_months_or_flag_uses_the_recomputed_position`, with one case for each
  - Horizon missing: `test_b6_a_missing_horizon_leaves_the_position_dependent_cells_missing`. Only T3D.2.r04 depends on the horizon, and there is no own line.
  - Name missing: `test_b6_a_missing_name_labels_the_facility_by_its_id`
  - Negative total: `test_b6_a_negative_total_principal_keeps_totals_and_has_no_shares`, which replaces the fail-closed test
  - Currency absent: `FacilityTerms.currency` is now `str | None`, tested by `test_b6_a_t418_row_without_a_currency`
- **6i, CP-3C:** confirmed, no action. No test applies, because consistent heads cannot disagree after A1.

**Choices for LEAD.** No ruling fixes these points, so I chose:
- **Own-line order per facility:** currency, then maturity date, then principal (CP-2D D-2 order), then the wall-row lines.
- **Currency before principal:** an unstated or non-USD currency wins over a missing wall principal. Under 2D5 a non-USD facility's wall principal is always missing, so the other order would mislabel it.
- **No "states no flag" line when the horizon is missing:** CP-3C has no recomputed flag to put beside CP-2D's, and the ruling gives the missing horizon no own line.
- **Where CP-2D's months and flag are checked:** `_facility` no longer reads them. They are checked when the limitations are built, and only for a dated facility.

**Probes** (in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3c-r6h-8/`):
- **`mutate.py`, exit 0:** 29 hand mutants covering rounds 5, 6 and 8, all killed, with the source restored by sha. On the first run M29 survived: dropping the months check let an earlier facility's amortisation outrank an undated row's own date. The precedence test above now pins it.
- **`prose_probe.py`, exit 0:** 27 input states, with output in `prose_probe.out`.
- **`edit_tests.py`, `edit_tests_2.py`, `splice.py`, `composer_part.py`, `operands_part.py`:** the edit scripts.

**Gates:** pytest gave 141 passed. ruff check and ruff format --check exit 0. `MYPYPATH=src mypy --strict` failed on the first pass with 3 test errors from the widened `months` type, all fixed; the final run exits 0.

**Prose and bare-figure hits:** `bare_figures` found none in any new reason, own line, label or claim. `prose.issues` found only the Stage 2 class, "Figure reference has no citation or calculation". None of the new claim templates hit it, since they carry chips.

**Stage 2 notes:**
- The T4.18 reader now passes `currency=None` when the row's `currency` fact is absent or not known, instead of failing closed. It still reads the currency and name from the row by `facility_id` and never through `_maturity_figure` (A5).
- The items still open from earlier rounds: the `methods/cp3c.md` C-4 headers and C-5 trace locator, and "shows both" (L4).

**Not verified:**
- **Lane merge:** not done because of the CP-4C lease conflict, so this commit has not been tested on top of the lane.
- **Stage 2:** the T4.18 currency and name reader, and CP-2D gap-copy periods against real heads.
- **Prose and lineage:** `prose.issues` with citations, and `cites_from` for unmatched facilities.
- **Other gates:** the repo-wide suite, mutmut (mutation was by hand), and size.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=n

## Controller notes (2026-10-28)
- The controller completed the step 0 lane merge as adf826a: `docs/CP4C-OWNER-LEASE.md` takes the lane's version (3674158 + round 8 header, a superset). The branch now differs from the lane only in cp3c.py and its test; 141 passed on the merge.
- Choices confirmed by the controller before the first review: own-line order per facility (currency, maturity date, principal, then wall rows); currency before principal; no "states no flag" line when the horizon is missing; months/flag checked at limitation build for dated facilities only. Sent to LEAD for information.
