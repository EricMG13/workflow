## Stage 1 riding-Lows batch: report

All nine items are done. No new test failed against the current code, so no code defect was found. Item 2 needed no new tests, because its mutants were already killed at the lane tip.

**Step 0:** HEAD was 76b13f0. I fast-forwarded with `git merge --ff-only` to the lane tip eecfe1b, which is docs-only (`work/build/ledger.md` and `lows-brief.md`). `git diff 76b13f0 HEAD -- src tests cases docs/rulings` was empty.

### Commits on `claude/stage1-lows` (worktree `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/stage1-lows`)
Each commit ends with the Co-Authored-By line.
- 7c45f80 test(cp2d)
- caa7a0b test(cp8)
- e6e284f test(cp3d)
- 5de3b29 test(cp2e)
- a3d3601 test(cp4c)
- 4dca8b7 test(cp2h)
- 9a6c089 test(h1), which also changes the host.py comment

The batch is 8 files, +191/−22. Nothing changed under `cases/`, `tests/defect_classes.py` or `src/deploy_vii`.

### Items
Mutant scripts and outputs are in `<S>/stage1-lows/`. Each mutant ran from a full temporary copy with PYTHONDONTWRITEBYTECODE=1 and counts as killed only on pytest exit 1. "Tip" means the eecfe1b tree in `<S>/stage1-lows/base_tree`.

1. **CP-2D, class-review Low.** Test: `test_r11_a_foreign_facility_before_d0_takes_the_fx_reason_in_the_schedule`. A EUR facility that matures before D0 gives T2E.3.r06, r07 and r08 the FX reason.
   - Mutant "schedule: pre-D0 before currency": survived at the tip (exit 0), killed after (exit 1).
   - The reviewer's `cp2d-class-review/mutants_review.py`, rerun on the worktree: exit 0, all 15 killed.

2. **CP-2D, round 5-6 L1–L6: skipped, already killed at the tip.**
   - Round 9 had already added `test_r9_l1`…`l6`. At the tip, K1, K2, K8, K9, K12, K14, K16, K17 and K11b all exit 1.
   - K5 and K18 no longer match the code, so I retargeted them. K5r (the current `elif` line) and K18r (round 9's own retarget in `<S>/r9_mutate_review.py`) both exit 1 at the tip.
   - The r56 folder is `<S>/cp2d-r6-review/`, not `cp2d-r56-review/`.
   - `cp2d_mutants.py`: exit 0 after the change, 12 of 12 killed.

3. **CP-8, Low-1.** I added `assert not cp8_module._on_page("1.25", "1.25 -1.2", "1.25 -1.25 -1.2")` to `test_r11_b1_every_occurrence_of_the_quote_on_the_page_is_read`.
   - The `at+len(needle)` mutant survived at the tip and is killed after.
   - `p_overlap_mutant.py`: exit 0.

4. **CP-8, Low-2.** I added a `blank_exit_trigger_absence(key)` adapter. It gives `thesis.exit_trigger` an absence that keeps the quote the field had.
   - Both `thesis.exit_trigger.absence.{reason,follow_up}` keys are added to `BLANK_FIELDS`.
   - I also added a control test: with non-blank text the adapter gives no issue, `()`.
   - `p_blank_exit_trigger.py` is a probe, not a mutant, so I wrote one: "exit_trigger absence text not checked". It survived at the tip and is killed after.
   - `p_blank_exit_trigger.py`: exit 0.

5. **CP-3D, L2 and I1.**
   - `test_r11_b3_names_the_wrap_refusal_accepts` runs through both name readers. An unwrapped quote that prints `Acme first- priority Term Loan` gives `()`.
   - In the wrapped case, `Acme Term Loan B-2` is not refused as "does not occur". Its only issue is `<reader>: digits are not allowed`, which is the current behaviour for a digit in a name.
   - `test_r11_b1_an_overlapping_occurrence_is_read`: `_whole_on_page("5","5 .5","x 5 .5 .5")` is False, with a True control.
   - The R mutants are in `<S>/cp3d-class-review/mutants.py`; the brief said `cp3d-class/`.
   - At the tip, 7 of 12 were killed. After the change, 10 of 12 are killed: the B3 gate-dropped, `'- '` widened and non-overlapping mutants are now killed.
   - The 2 that remain are the ones the reviewer called equivalent (I3): "name not normalised" and "no early return". The script exits 1 only because of those two.
   - `p_survivors.py`: exit 0.

6. **CP-2E, L2 and L3.**
   - L2: added the accepted twin `wrapped-page-joined-twin` (the b1 page) to `test_b1_every_occurrence_in_every_reading`.
   - L3: `test_class_blank_limitation_off_insufficient_information[empty|spaces]`. `""` gives exactly `assessments[0].limitation: empty text`. `"  "` gives that issue plus the "only for Insufficient Information" issue, as the probe's c3 shows.
   - Killed after, having survived at the tip: "plain page spans only" and "limitation only when II".
   - The 2 still surviving are the reviewer's I1 equivalents (raw reference_rate, frame order), so the script exits 1.
   - `p2_behaviours.py`: exit 0.

7. **CP-4C, L1, L2 and the Info pins.** New tests:
   - `test_b3_the_issuer_name_is_spared_in_a_class_name`: issuer `Northbridge 2 Holdings`, class `Northbridge 2 Holdings Notes`. It passes and composes, and is refused under the frozen issuer.
   - `test_b3_a_class_name_is_read_as_spelt[Term Loan B-2|Q1 Notes]`.
   - `test_b2_a_known_total_debt_without_an_amount_still_raises`.
   - `test_b6_ev_reason_comes_first_when_both_operands_are_unknown`: gap v03 takes EV's reason, and v01 takes CP-1's.
   - All 4 named mutants survived at the tip and are killed after; `cp4c_mutants.py` exits 0.

8. **CP-2H, N1 and N2.** `SOURCE_BREACHES` lives in `tests/test_method_cp2h.py`, not under `cases/`, so I went ahead.
   - `threshold_unit` is now `Below  10.00x`, still refused with "Trigger terms not found".
   - Added the refused forms `multiple_no_integer` (`.75x`), `percent_no_integer` (`.5%`) and `percent_minus` (`-10.0%`).
   - M5, M6, M7 and M14 survived at the tip and are killed after; `cp2h_mutants.py` exits 0.
   - `n1_unit_check_unpinned.py` exits 0. It had exited 1 at review. I ran it from a copy whose `_probe_base` ROOT points at this worktree.

9. **H1, Low A, Low B and Info 1–2.**
   - **Low A:** added `_LEASED_ROWS`, a shared `_UNIVERSE` of 12 ids and a `_leased_row_checks` helper. The five row tests now use them.
   - **Low B:** the unreadable branch of `_source` now carries a sha256 and a page span. The L3 test also asserts that an unscoped search never surfaces "SECRET late".
   - **Info 1:** the host.py:48 comment now reads "Eight modules are owner-only (G1-X §1): …".
   - **Info 2:** the test comment now says "eight others".
   - **Mutants:** `h1_mutants.py` runs all 48 single-id widenings plus p09's tools.py mutant against `test_host_h1.py` and `test_owner_g1x.py`.
     - At the tip: 10 killed and 39 survived (the 38 widenings plus Low B).
     - After: 49 of 49 killed, exit 0.
   - **Probes:** p06 exit 0 (0 survivors), p07 exit 0, p08 exit 0 (3 of 3 killed), p10 exit 0.

### Gates (all exit 0)
- pytest on the seven test files plus `tests/test_owner_g1x.py`: 2041 passed, 1 xfailed. The xfail is the strict B5 marker in cp2h and was already there.
- `ruff check` and `ruff format --check` on the 8 changed files: exit 0.
- `MYPYPATH=src mypy --strict` on the 7 test files and `src`: exit 0, 124 files.

### Notes
- **CP-2D, outside L3:** with the revolver undisclosed and cash missing, T2E.2.r09 takes the cash reason. No test pins this, and a mutant that forces REV_RATIO in that case (`if undisclosed:`) survives. The code looks consistent with 2D-b. I did not add a test because this is outside the brief.
- **CP-3D:** I used the brief's `Acme Term Loan B-2`. Because the name has a digit, the test pins the absence of the B3 refusal and the digit refusal as the only issue. It does not pin a fully clean accept.

Not verified: the full repo suite and the slow gates (only the eight files above were run). GitNexus `detect_changes` and `impact` were not run (I have no MCP tools here). The ruff and mypy gates ran on the H1 files just before the H1 commit, though the files did not change between the run and the commit. Mutants were hand-written, not mutmut. Item 2's L1–L6 kills come from round 9's tests, which I did not re-review, and two of its mutants (K5, K18) are retargeted versions. No frozen oracle case was rebuilt.

agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y
