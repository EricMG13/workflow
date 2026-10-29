# Release fix 2 report (mx-feature)

Release fixer 2: all nine items applied, tip a8e93cf on claude/s2r-f2 (3 commits over 5a6a746: 8540564, fc9c54e, a8e93cf). Tree is clean and no background process is left. One probe cannot exit 0 as written (item 7, below).

**Items**
1. **D12 (B M1):** the four f1544a3 records are back in `docs/reuse/manifest.json`, each just before its 93c1ffc record. They are `live/submission.py` @bb4553b, and `cp3_relative_value.py`, `cp4_legal.py` and `business_context.py` @cffdf9f. `probe_d12_chain.py` exits 0 for all four files.
2. **Legal pin (B L1):** `cases/legal/manifest.json` `readiness.py` is back to `1038a37a…ccffa`, which is the imported sha and the one in `docs/reuse/manifest.json`. I ran the cascade with `chain.sh` and a `repin.py` loop that also covers the builder files.
   - It reached a fixed point after 3 iterations.
   - Two fresh rebuilds (`fresh_copy.py` + `chain.sh`) both exit 0, are byte-identical, and match the tree.
   - `pins.py --check` exits 0 ("matches 75 paths"). `probe_legal_inspection_pin.py` exits 0.
   - Moved shas (8-char prefixes, old → new):

     | File | Old → new |
     | :--- | :--- |
     | `cases/legal/manifest.json` | dceee076 → d6a8ec15 |
     | `cases/legal/render-expected.json` | 95f298a8 → 499289b9 |
     | `cases/legal/source-host-expected.json` | 1a9db34d → 7d359fd5 |
     | `cases/cp2d-owner/builder/build.py` | cc200e99 → 0e3bdde3 |
     | `cases/cp2d-owner/manifest.json` | 68d774a3 → d92861e0 |
     | `cases/cp3c-owner/builder/build.py` | 242b011e → 6b6b9c2f |
     | `cases/cp3c-owner/manifest.json` | 10e891ff → 551c3125 |
     | `cases/cp4-owner/builder/build.py` | 72ad8c26 → 94010ed0 |
     | `cases/cp4-owner/manifest.json` | 6f17b943 → 2c12bf68 |
     | `cases/cp4-owner/submissions.json` | 094425aa → f2ef2e30 |
     | `cases/cp4c-owner/builder/build.py` | 50ca14d5 → d0908522 |
     | `cases/cp4c-owner/manifest.json` | 73cbcfb4 → c9ea23d4 |
     | `cases/cp4c-owner/submissions.json` | 6a3a2e3d → 1f76a1d1 |

   - No `expected.json` changed. Test pins re-pinned: `tests/cp2d_runs.py` builder cc200e99 → 0e3bdde3; `tests/cp3c_runs.py` builder 242b011e → 6b6b9c2f and manifest 10e891ff → 551c3125.
   - The CP-2D, CP-3C, CP-4 and CP-4C leases each have one new "Amended by Modules 2026-10-29 (Stage 2 close release fix batch)" line with the old and new shas. `cases/PINS.json` was regenerated.
3. **S1a (B):** both test-only fixes are in `tests/test_owner_s1a.py`.
   - **cp0 pair:** the oracle's pack-hash placeholder is bound to `closed.pack.content_hash()`, and the test asserts exactly one fact carries it.
   - **`test_cp2_invalid_submission_without_a_read_refuses`:** it now uses `valid, _ = …` and asserts `"credit_synthesis"` is not among the valid steps.
   - I ran the two tests once, in the background: `test_plan_attempts_heads_and_cp0` (both cases) and the CP-2 test. Result: 3 passed in 687s, exit 0.
   - I first started the whole file and killed it after about 25 minutes. It had passed 16 tests and failed none. It runs far longer than the ~10 minutes the brief expected, so I did not use it as the gate.
   - `probe_s1a_cp0_placeholder.py` and `probe_s1a_verify_submissions_valid.py` exit 0.
4. **F1 (A L1):** `test_the_real_worst_case_record_bound_holds_for_escaped_characters` now submits the payload through a financial workflow. It asserts the refusal has 40 issues and `LIMIT < stored record size <= WORST_CASE`. The stored record is 126451 bytes, measured with `_largest(fin._audit(...).parent)`. `a10_f1_record_bound_static.py` exits 0.
5. **Timing (A L2):** sizes and bounds are widened in `tests/test_readiness_linear.py`. Each measurement is the tip's time against the bound, and the base tree `release-review-A/base`'s time against the bound.

   | Case | Bound | Fix | Old code | Change |
   | :--- | :--- | :--- | :--- | :--- |
   | `scans` | 3.0s | 0.58s, passes 5.2x | 17.4s, fails 5.8x | 200 sources × 1000 event ids each, 20000 events |
   | `prefill_scopes` | 2.0s | 0.21s, passes 9.6x | 11.1s, fails 5.5x | 2000 books, 60000 scopes |
   | `prefill_periods` | 1.5s | 0.23s, passes 6.6x | 9.1s, fails 6.0x | 1000 periods, 20000 scopes |
   | `refs` (was thin on the old-code side, 2.5x) | 2.5s | 0.46s, passes 5.4x | 19.5s, fails 7.8x | event citations `n//40` → `n//10` |

   - The scopes are spread 2000 to a financial source, which is the contract cap.
   - The `a02_timing.py` margins are on a quiet machine. The 5.2x and 5.4x passes are near the 5x floor and could slip under load.
   - `gaps` (3.9x) and `attach` (4.4x) also fail on the old code by less than 5x. They were not named in the notes, so I left them. Cheap fix if wanted: bound 1.5 → 1.0 and 0.5 → 0.4.
6. **Infos (A):** the verbatim note at `tests/test_defect_classes_shared.py:114` now says the absence-claim rule (`readiness.py:321`). The docstring at `owner_workflow.py:893` is reflowed. The reflow shifts later lines by -1, which also fixes the cites at `owner_workflow.py:949` and the CP-8 lease's 1090 and 1454.
7. **Cites (C L1):** 13 cites were stale in the tree after the reflow. They are in `docs/TOOL-CONTRACT.md` (9 owner view ranges, now `context_block..def view`) and in the CP2G, CP2H, CP3C and CP4C leases.
   - **`c1_cites.py` problem:** it hard-codes the old cites, so as shipped it reports 13 misses against any fix. I copied it to `…/scratchpad/f2/c1_cites_updated.py` with the new cites. That copy exits 0 ("51 cites, 0 miss at HEAD").
   - **cp1d/cp2d/cpl10 cites move again when fixer 1 lands.** Re-run `…/scratchpad/f2/refresh_view_cites.py` from the repo root, which rewrites the 9 view ranges, and then check the cp2a/cp2d reader cites by hand.
8. **Method notes (C L2):** `cp1c.md`, `cp2g.md` and `cp4c.md` now name `deploy_workflow.owners.blank.one_per_page`. I left `cp1d.md:78` alone because cp1d is fixer 1's.
9. **Heading (C L3 / B L2):** `docs/rulings/2026-10-28-stage2.md:354` now says CP-2D. `probe_item21_heading.sh` exits 0.

**Gate exit codes (all 0)**
- **pytest:** one run over `test_rule_issue_bounds`, `test_defect_classes_shared`, `test_owner_g1x`, `test_legal_render`, the cp2d/cp3c/cp4/cp4c connect files and the cp2d/cp3c/cp4/cp4c method files: 2588 passed. Separately `test_readiness_linear`: 29 passed.
- **Lint and types:** `ruff check` and `ruff format --check` on the 7 touched `.py` files. `mypy --strict` on `owner_workflow.py`.
- **Suppressions:** `noqa` count is 13 (≤ 13) and `type: ignore` is 5 (≤ 5), both unchanged.

Not verified: the whole of `test_owner_s1a.py`, since only the 3 affected tests ran. `test_owner_cp2d`, `test_owner_cp3c`, `test_owner_cp4` and `test_owner_cp4c`, which I did not run. The full suite and the other `test_readiness_linear` timing cases on a loaded machine. Fixer 1's files (`cpl10.py`, `cp2a.py`, `cp2d.py`, `cp1d.py`), so the cp1d, cp2d and cpl10 cites need a refresh after that merge, and the lease headers' cp2d shas describe my tree only. `probe_lease_headers.py`, which looks for the W3 chain header and was not run. For items 6, 8, 9 and the docs cites, no test applies (text-only changes).

agent=mx-feature fix-rounds=1 gates-first-pass=y
