# Release W3 report (mx-feature)

W3 integration is built, but the fast set does not exit 0. Three `test_owner_s1a` tests fail. I reproduced all three on a detached fb231d4 worktree, so they predate this release.

**Tip SHA:** 5a6a746 on `claude/s2-release`. The tree is clean, no background process is running, and `pins.py --check` exits 0 on 75 paths. Commits above fb231d4, oldest first: five merge commits, then daebf79 (legal pin and view-tree pattern), 290000f (chain), 14841d9 (lease headers), b3a8877 (text fixes and rulings), 8915c17 (hoist), 5a6a746 (test pins).

**Merge conflicts**
- B, C, A2 and D merged cleanly. D's merge auto-resolved `tests/cp3c_runs.py` and `tests/cp4_runs.py` with no marker, and the tests that use them pass.
- A1 conflicted only in `cases/PINS.json`. I took ours, finished the merge, and regenerated it in the chain.

**Every sha the chain moved** (first 8 hex characters, old → new)
- Legal pin: `cases/legal/manifest.json` readiness.py pin 119058ff → 01616654, so the manifest itself went 3da3b746 → dceee076. `render-expected.json` d4eadecf → 95f298a8 and `source-host-expected.json` 5868a06c → 1a9db34d carry that hash.
- cp2d: builder ea673c0c → cc200e99, manifest 166c7b18 → 68d774a3.
- cp2g: builder 61f795ef → ea4c5a77, manifest 981401d0 → c7f66104.
- cp2h: builder d6cf602d → 28edf51f, manifest af046165 → ff74170b.
- cp3c: builder 8480e98a → 242b011e, manifest 235ee364 → 10e891ff.
- cp4: builder 8ec386bf → 72ad8c26, manifest 6495ca2e → 6f17b943, submissions ed069b1a → 094425aa.
- cp4c: builder c412b7e1 → 50ca14d5, manifest 866acfed → 73cbcfb4, submissions 6cddc510 → 6a3a2e3d.
- cp3d (the CP-3D text fix below): builder and `expected.json` moved; `docs/CP3D-OWNER-LEASE.md` has both shas.
- Cross-lane pins: cp2g→cp1d expected 293120368b5d → 8880a2c59a92, and cp4c→cp4 expected → 2b98b81b.
- cp4c's pin of the cp3c manifest ended at 10e891ff, not the 235ee364 the notes expected, because the cp3c builder re-pin moved the manifest again.
- Test pins moved: `tests/cp2d_runs.py` (builder) and `tests/cp3c_runs.py` (builder and manifest).

**Oracle values:**
- The chain moved no oracle value. The 8 changed owner json files differ from their pre-chain versions only in sha-valued leaves, and no `expected.json` moved.
- One value moved by explicit order (step 4): the cp3d `expected.json` `negative_cases.blocked_cp3d.result` text, "module blocked, no head" → "module blocked, the store holds a blocked head (status blocked)". It is recorded in the CP3D lease header.

**Chain:** it reached a fixed point after the manual repin sweeps. Two fresh-copy rebuilds (`r2`, `r3`) are byte-identical to each other and to the committed `cases/`. I ran them before the cp3d text fix; I re-ran the chain afterwards and it passed, but did not repeat the double rebuild.

**W3-notes bullets**
- **B, `run_rate_annual` (item 20):** done. Added as item 20, and CP3C lease Q3 records the ruling.
- **TOOL-CONTRACT view-tree rows:** all six files exist (cp1c, cp1d, cp2g, cp2h, cp3c, cp4c).
- **`cp3c.py` comment:** done. The file is `src/deploy_workflow/owners/cp3c.py`, near :2368. The comment was reworded to say `expected.json#consumption` lists T2E.3.r01 under `reads_beyond_the_cp2d_lease_pins` and that no reader extension was made. The consumption block does name T2E.3.r01 there, so I reworded the comment rather than just deleting the pin claim.
- **D owner cores need no D12 records:** confirmed.
- **D duplication:** the four copies were identical. `one_per_page` is hoisted into `owners/blank.py`, the existing shared owners module. It is not strictly stdlib-only, because it imports `deploy_vii.contracts` and `deploy_vii.prose`. I added a direct test in `tests/test_owner_blank.py`. The `cp1d` copy is also identical but outside the brief, so I left it.
- **D v08 `unread_issues`:** not applied. It is an interpretation note for the release review.
- **D cross-lane pins:** done by the chain.
- **C readiness pin:** done, along with the render-expected and source-host-expected hashes.
- **C `prose.py` ISC004:** the known findings are unchanged.
- **C method notes:** the blank definition in `cp1d.md`, `cp2e.md` and `cp1c.md` now matches `prose.is_blank` (whitespace, Cc, Cf, the default-ignorable code points and U+2800). `cp1c.md` had no wrong definition, so I added one.
- **C verbatim sinks, A1 `T2E.5.r05`/`r06` currency, and `test_owner_cp4`/`test_probe_cp4`:** not applied. They are for the release review or Stage 5.
- **A1 drawings precedence (item 21):** recorded.
- **CP3C lease :154 sentence:** corrected. It is at :158 after the merge, and now matches the new `fact_copy_rule`.
- **View trees:** `cases/*-owner/*-view-tree.json` is added to `pins.py`, and the decision is recorded as a line under round 5. `PINS.json` went from 69 to 75 paths.
- **A2 lineage scope (item 22):** recorded.
- **CPL10 lease:** the "Queued for a later revision" text (now :15), :131 and :216 are updated to the item 22 scope.
- **CP-3D blocked wording:** applied. The condition holds, because `tests/test_owner_cp3d.py:159` asserts the store holds a blocked head.
- **A2 cascade:** done by the chain.
- **Lease headers:** "Amended by Modules 2026-10-29 (Stage 2 close release W3 chain)" lines added for CP2D, CP2G, CP2H, CP3C, CP4 and CP4C, plus a CP3D line for the text fix.

**D12:** `execution`, `live/tools`, `prose` and `readiness` are the only reused files changed since fb231d4. Each has a record whose sha256 equals the file on disk, and whose `project_commit` 30a1f7a brings the file to that sha, with `prior_project_sha256` equal to the first parent's sha. No other reused file changed. The older `shipped.py` record mismatch from the W1 report is still open for the owner.

**Gates**
- **`pins.py --check`:** exit 0.
- **Fast set:** exit 1, 9501 passed, 6 failed, 5 skipped (a run through a pipe that I stopped, then a verbose re-run).
  - Three failures were stale test pins in `cp2d_runs.py` and `cp3c_runs.py`. I fixed them in commit 5a6a746, and `test_connect_cp2d` and `test_connect_cp3c` pass (244 tests, exit 0).
  - The other three are `test_owner_s1a::test_plan_attempts_heads_and_cp0[positive]`, `[gap]` and `test_cp2_invalid_submission_without_a_read_refuses`. They also fail on a detached fb231d4 worktree, so no merged lane caused them. The cp0 pair fails on the unbound `<<PreparedPack.content_hash()...>>` placeholder in the oracle's `T7.run.preparation` fact. The third fails with `_verify_submissions` returning 7 issues (`assert 7 == 0`).
  - This contradicts the W1 report, which said the fast set passed. I did not look into why.
  - After the pin fix I re-ran only the cp2d and cp3c files, not the full fast set.
- **`ruff format --check` on the changed `.py` files:** exit 1. Only `cases/pins.py` fails, on a line unchanged from fb231d4. All 57 `src/` and `tests/` files are formatted.
- **`ruff check`:** exit 1, only the known findings: `prose.py` ISC004 :114 and :127, and `test_legal_render.py` C408 :220. Builder files carry many pre-existing findings that I did not clean up.
- **`mypy --strict` on the 16 changed `src/` files:** exit 0.
- **Counts:** `noqa` is 13 and `type: ignore` is 5.

Not verified: I did not run the slow render suites or any `test_owner_<cp>.py` genuine runs. I did not run the full suite, bandit, complexipy, jscpd or mutation gates, or any test of the lease header text. I did not check the new cp3d `expected.json` text against `test_owner_cp3d`, and I ran the double rebuild only before the cp3d text fix. Whether the three `test_owner_s1a` failures reproduce on the controller's machine is unchecked.

agent=mx-feature fix-rounds=0 gates-first-pass=n
