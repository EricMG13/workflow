# Release review lane B (mx-adversary)

## Lane B release review (oracle re-pins: W1, W2-A1, W2-A2, W3 chain), tip 5a6a746

**Verdict: REQUEST CHANGES.** There is one Medium finding, in the D12 records. Every oracle value that moved traces to a named item, and each test that replaced a removed delta fails when its oracle is reverted. The three S1a failures predate Stage 2.

### Findings

**M1 (Medium): the release deleted four D12 patch-history records.**
- Where: `docs/reuse/manifest.json` `post_import_patches`.
- Cause: commit 0daac2c (0d-d, followed its brief's "update the existing entries") overwrote the existing records in place instead of adding new ones. The four lost records are:
  - `live/submission.py` @bb4553b → 1b4aaa09;
  - `cp3_relative_value.py`, `cp4_legal.py` and `business_context.py` @cffdf9f → 5811d454, 5b005aaf and 1672ba97.
- Effect: W1 then set each record's `prior_project_sha256` from the merge's first parent. So each of the four 93c1ffc records now names a prior sha that no record produces, and the history of the B10 and 0d-c patches is gone.
- This breaks the spec at `README.md:22` ("original hashes and patch history retained") and the repo's add-a-record convention (`report_view.py` has 16 records).
- Each surviving record does pass the round 5 item 19 check, and every changed reused file's last record equals the file at the tip.
- Fix: re-insert the four f1544a3 records just before each file's 93c1ffc record. Nothing else changes. Probe #8 shows this closes every chain.
- Probes: #6 `probe_d12_records.py` exits 0; #7 `probe_d12_chain.py` exits 1 at the tip and 0 at f1544a3; #8 `probe_d12_fix.py` exits 0.

**L1 (Low): a historical inspection record was re-pinned to the current file.**
- Where: `cases/legal/manifest.json:290`, `immutable_inspection.files["src/deploy_vii/readiness.py"]`. W1 moved it from 1038a37a (the imported sha) to 119058ff, and W3 to 01616654.
- Why it is wrong: this block records the imported bytes at `old_reuse_commit`. The same manifest says at `:333` that it is "draft provenance, not claims about future implementation revisions". The sibling entries keep their imported shas even though the files were patched since (`cp4_legal` 1b2246ff against 17c96b6f on disk, `methodology` e52360e4).
- No code reads the block. The plan and the W3 notes ordered the re-pin on a misread of what the block is.
- Fix: restore 1038a37a. That moves the legal manifest back to d6a8ec15, so the cascade has to be rerun: the cp2d, cp4 and cp4c builders, the render-expected and source-host-expected hashes, and the lease headers. Alternatively, record a ruling that keeps the current pin.
- Probe: #12 `probe_legal_inspection_pin.py` exits 1.

**L2 (Low): ruling item 21 names the wrong module.** The heading at `docs/rulings/2026-10-28-stage2.md:354` says "CP-3C drawings precedence wording". The wording is CP-2D's (`cp2d.py`, round 5 item 4 at `:283`). Probe: #11 `probe_item21_heading.sh` exits 1.

**I1 (Info): should CP-2D `T2E.5.r05` and `r06` carry a currency?**
- r05 and r06 are money cells (US$ m), and the product already stamps USD on them and on every MILLIONS fact.
- The oracle carries `currency` only on the twins CP-3C reads (r04 and r07) and on no known money cell. No consumer reads r05 or r06, so the release needs no change.
- Predates: `_assert_fact` (`tests/test_connect_cp2d.py:752`) checks currency only where the oracle names one. Currency on other money cells is pinned only by the single cell in `test_module_scale_unit_currency_of_each_cell_class`.
- Probe: #5 `probe_cp2d_r05_r06_currency.py` exits 0.

### Checks that passed
- **Traceability (#3 `probe_oracle_leaf_diff.py`, #4 `probe_round3_citations.py` exit 0).** Every value that moved in `cases/` maps to an item or is a sha-only re-pin:
  - CP-2D: `period`, `value_class` and the r04/r07 currency (R1 M1, `GAP_CURRENCY`); the stale-head text (item 15).
  - CP-3C: 6 periods, CP-1A, `fact_copy_rule`, `frozen_inputs[8]`.
  - CP-4 `other_five_sections`; FP04 blocks (round 4, item 18).
  - CP-3D amortisation and blocked text; CP-1D recipe; CP-2E blocked text.
  - CP-L10 lineage (item 22); CP-2G blocked limitations and scenario name; CP-4C `unread_issues`.
  - CP-1C (107 facts) and CP-2H (17 facts): pure round-3 reductions.
  - cp3-cp6: the cp6-freeze.
- **Removed deltas.** All 10 replacement tests compare product output with the oracle, or assert the oracle value directly. I ran the revert for two: restoring the f1544a3 values in memory makes `test_legal_render ...honest_states[0,1]` and `test_method_cp3d ...[amortisation_nonzero]` fail. Probe: #9 `probe_delta_revert.sh` (control 0, revert 1, exit 0).
- **Drawings precedence.** `cp2d.py:673-696, 997-999` match item 21. `test_connect_cp2d.py:144-178` covers both unsettled states, all four gaps, the runway reason and the LIQ-01 wording.
- **Lease headers.** All 14 old → new shas in the W3-chain lines are correct. Probe: #10 `probe_lease_headers.py` exits 0.
- **Double rebuild.** Two fresh rebuilds of all 17 builders are byte-identical to each other and to 5a6a746. This covers the gap W3 left after the cp3d text fix. Probe: #13 `probe_rebuild.sh` exits 0.
- No stub or catch-all found in the lane's builder or src changes.

### The three S1a failures
- **Origin:** 235c208, "integrate S1a owner-run extension (fix round 4, build-only)", 2026-10-28. Its tests were never run.
  - 235c208 is an ancestor of e89b2a2 (the Stage 1 close).
  - `git blame` at f1544a3 attributes `tests/test_owner_s1a.py:373-381` and `:1310-1318` to 235c208. No commit in e89b2a2..f1544a3 touched those lines.
  - **Neither W1 nor any Stage 2 commit caused them; they predate Stage 2.**
- **The cp0 pair (oracle placeholder never filled in):**
  - The oracle (6e9305c, `cases/snapshot/builder/build_s1_oracle.py:993`) writes the `T7.run.preparation` text as `<<PreparedPack.content_hash(), bound at run time>>`. The product writes `pack.content_hash()` (`readiness.py:542`).
  - The test compares the facts raw at `:373-380`, and `s1a_runs` only replaces the other spelling, `<<PACK_SHA256…>>`. The lease (`S1A-OWNER-RUN-LEASE.md:97`) declares this substitution for the CP-0 facts.
  - Probe #1 drives CP-0 alone for both cases: the raw diff is only `T7.run.preparation`; with the placeholder replaced, the facts and limitations are equal.
  - Fix: compare against `[{**f, "text": f["text"].replace(CP0_PACK, closed.pack.content_hash())} for f in cp0["facts"]]`, with `CP0_PACK` the oracle's string, and assert exactly one fact carries it.
- **`test_cp2_invalid_submission_without_a_read_refuses` (wrong reading of the return value):**
  - `_verify_submissions` returns `(valid_steps, settlements)` (`owner_workflow.py:1980-1986`; the same at 235c208). The test asserts `len([0]) == 0` at `:1317`.
  - The forked workflow keeps every earlier submission: CP-0 source_readiness, CP-1 source_context, financials, narrative, readiness and quality, and CP-1A business_context. That is 7 valid steps, so the "7 issues" are these valid-step tuples, not issues. Probe: #2.
  - Fix: `valid, _ = _verify_submissions(store, with_read, OWNER_SPECS)` (it must not raise), then `assert "credit_synthesis" not in {s for _, s, _ in valid}`.
- Both fixes are test-only. I did not run either test, per your instruction.

### Gate exit codes
- `pins.py --check`: 0 (75 paths).
- pytest, CP-2D/3C/3D/4 method and connect files, legal render and cp1b registration: 2067 passed, exit 0.
- pytest, CP-1D/2E/L10/2G/4C/2H/1C method and connect files, both stage2 class files, connected render and owner blank: 4760 passed, 2 skipped, exit 0.
- `ruff format --check` on 16 files: 0. `ruff check`: 1, only the known `test_legal_render.py:220` C408.
- `mypy --strict` on `cp2d.py`, `cp1d.py` and `cpl10.py`: 0.

### Probes
Each line gives the exit code from my run.
1. `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-review-B/probe_s1a_cp0_placeholder.py` (exit 0)
2. `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-review-B/probe_s1a_verify_submissions_valid.py` (exit 0)
3. `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-review-B/probe_oracle_leaf_diff.py` (inventory, no pass/fail)
4. `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-review-B/probe_round3_citations.py` (exit 0)
5. `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-review-B/probe_cp2d_r05_r06_currency.py` (exit 0)
6. `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-review-B/probe_d12_records.py` (exit 0)
7. `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-review-B/probe_d12_chain.py` (exit 1 at the tip, 0 at f1544a3)
8. `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-review-B/probe_d12_fix.py` (exit 0)
9. `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-review-B/probe_delta_revert.sh`, with its plugin `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-review-B/revert_plugin.py` (exit 0)
10. `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-review-B/probe_lease_headers.py` (exit 0)
11. `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-review-B/probe_item21_heading.sh` (exit 1)
12. `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-review-B/probe_legal_inspection_pin.py` (exit 1)
13. `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/release-review-B/probe_rebuild.sh` (exit 0, twice)

Not verified: I did not run the S1a tests themselves or their fixes, per your instruction. Probes #1 and #2 cover only the CP-0 facts and the count of valid steps, not the rest of each test. The full fast set was not re-run; I ran only the subsets above, which leave out `test_owner_s1a`, `test_readiness_linear`, the defect-class files and G1-X. No genuine `test_owner_<cp>` run and no render suite ran, including the de-xfailed CP-2G blocked test (I checked its fast twin by reading it). I did not run reverts for the other 8 deltas; I reasoned through them from the code. I did not check CP-L10's derived citations against the round 3 one-per-page rule: it uses ordered de-duplication, it predates the release, and it is outside the four named modules. I did not check the CP-2G/CP-4C citation structure beyond the lineage text (lane C). I did not re-review the cp3-cp6 freeze values (LEAD passed them).
