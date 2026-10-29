# Stage 2 review, lane C: the rest (mx-adversary)

**Stage 2 whole-stage review, lane C: `claude/s2-batch` at a1a0574 (read-only; the worktree is still clean)**

There are no High or Medium findings. Every module in lane C is APPROVE. Four Lows below ride the fix batch.

## Verdicts
- **CP-1C: APPROVE.**
  - The fix in 3d0392e is correct. On a fast real store the attempt's inputs are `[prepared-pack, CP-0, CP-1]`. The old loop raises `KeyError 'prepared-pack'` and the new assertion passes (probe pcc1, exit 0).
  - The builder's 34 mutants are all killed at a1a0574. Two of them had to be re-anchored, because later merges appended rows after CP-1C.
  - The CP-1C stage class case passes. See L3.
- **CP-1D fixes: APPROVE.** The reviewer's probes were run with the s2-batch root.
  - M1 closed: p10 exits 0 (0 mismatches on real-shaped facts) and p11 exits 0 (all 3 cases bind).
  - M2 closed: p5 exits 0, `bad: 0`.
  - L4 closed: p8 exits 0, and every dict keeps its base order with additions at the tail.
- **CP-L10 fix 1: APPROVE.**
  - **M1 closed.** I ran p7 with a1a0574 code over the fixer's genuine store: exit 0, 0 differences. CP-1 stores `17.50` and the view reads `17.5`.
  - **M2 closed.**
    - The `readiness_literal` fast tests are in the gate and pass.
    - `test_owner_cpl10.py` passed 10 of 10 at 1ec5ba8 (`cpl10-s2-fix/owner_tests.out`, exit 0).
    - Since then `cpl10.py`, `cpl10_runs.py` and `test_owner_cpl10.py` are unchanged.
  - **M3 closed.** Every listed store test exists:
    - limited case and cell-for-cell check;
    - `invoke` refused, submit before `read_inputs`, `stale_binding`;
    - blocked walk with a receipt;
    - verifier tamper with a `_PROBES` recorder;
    - both `RefusedBegin` cases;
    - store bytes unchanged;
    - navigator.
  - **The "8 equivalent survivors" claim.** The fixer's `p9.out` (20:18) is older than the commit (20:41). At a1a0574, `p9_cpl10_mutants_batch.py` leaves 7 survivors:
    - the review's own 6 equivalent mutants;
    - plus the NOAPPLY `validate_reraise`. Re-anchored to `except UpstreamError` → `KeyError`, it is killed.
    - `reader_status_const` is now killed by `test_reader_reports_the_status_of_the_head_it_is_given`.
    - My two extra M1 mutants (no `normalize`, default context) are killed.
  - The claim holds, but the stated count came from a stale run.
- **Stage class test: APPROVE.**
  - **Real submit path.** Each `fresh()` calls `ow._CORES[m].submit`, the same call as `owner_workflow.py:1272`, with `rules=None` (as documented). The only `_PRECHECKS` row is CP-4, which has no core.
  - **Verbatim sinks (pc2, exit 0).** For every verbatim pattern, a hostile value lands only in `Fact.text`, `Fact.limitation`, `Claim.limitation` or `Module.limitations`. RETAINED paths appear nowhere in the module, and nothing lands in `Claim.text`.
  - **The two strict xfails are confirmed** through `OwnerWorkflow`: a Claim `ValidationError`, then `stale_binding`. They are not re-raised here.
  - **Missed paths.**
    - A strict xfail stops CP-DR and CP-3D at their first raising path. I ran every other path on its own with the 3 ruled values plus two well-formed references (`[zz-nope]`, `{zz-nope}`), over all 13 cores.
    - Result: no raise, no wedge, and no unexpected accept (pc1). Its exit 1 is entirely a probe artifact: 150 lines for the five non-journaled cores, which have no `RULES`.
    - The string paths the test leaves out are all ids, hashes or numbers (pc4).
    - CP-3 and CP-5 are outside the stage test. Through `submit_model_payload`, 48 and 107 paths × 3 values gave no raise and no wedge (pc3).
  - The only remaining gap is null or absent fields, already on the L2 backlog.
- **Integration: APPROVE with L1, L2 and L4.**
  - No `tests(integrate)` rewrite dropped a behavioural check. Each relaxed row is still pinned by a base-prefix test or by the module's own "not in `_PRECHECKS`" test.
  - `hide_row` is sound, because G1 and `host.py` look the dicts up through the module.
  - **D12 chain:** for all 19 destinations the newest sha equals the file and `git show <project_commit>`, the list chain is unbroken, and no imported file moved without a record (pd1, pd2). pd1 exits 1 only on 6 records dated 2026-10-27 whose `project_commit` is not an ancestor (predates).
- **G1 I2: no finding, not Medium** (pg1, exit 0).
  - `probe_one_step` alone does pass a valid step that carries forged `issues` (reproduced).
  - But the store cannot hold such a step: `StepSubmission.coherent_state` (`execution.py:71-72`) refuses it when the snapshot is parsed. So `verify_owner_run_receipt` returns `identity_mismatch` both with the receipt untouched and after a consistent reseal (snapshot hash, step hash, `snapshot_after`, seal).
  - The guard is the contract, not the step-hash check. The backlog row can close with a pinned test.

## Low
- **L1. Test isolation is still broken; the 165bd0b fix is incomplete.**
  - `tests/test_owner_g1x.py:523` and `:640` still call `m.delitem(owner._CORES / _ENTRY_VALIDATORS, "CP-3D")` on top of the fixture's `setitem`. The undo puts CP-3D back at the end.
  - Any run that puts `test_owner_g1x.py` before the connect files fails 5 batch tests: `test_registrations_are_appended_after_their_dependencies` in cp1c, cp2g, cp2h, cp3c and cp4c, which pin `tuple(_CORES)[:2] == ("CP-DR","CP-3D")`.
  - pi2 exits 1 (both dicts reordered); pi3 exits 1 (5 failed).
  - Fix: use `hide_row` at both sites. This is not in `lows.md` or the backlog.
- **L2. D12 provenance.**
  - Seven Stage 2 records name a prior that no parent of their `project_commit` holds:
    - CP-2D `shipped.py` #27 (prior 8afa15fc; the parent holds 4ef3f9ff);
    - CP-2D `report_view.py` #34;
    - CP-2E #29;
    - CP-L10 #37 (the CP-L10 review had called 4ef3f9ff correct; the 5977ae4 re-chain replaced it);
    - CP-1D #39 and #40, which also name 94d9f29, a commit that only touches tests;
    - CP-DR #25 (predates the batch).
  - Probe pd3, exit 1. I found no contract text defining the prior, so I judged it against the parent's bytes.
- **L3. The CP-1C A1 check is narrowed** (`tests/test_owner_cp1c.py:198-203`).
  - The fix no longer asserts the list of input ids or the `prepared-pack` hash. Forged inputs (wrong pack hash, an extra CP-2A) pass the new assertion (pcc1 part c).
  - Suggest asserting the ids equal `[prepared-pack, CP-0, CP-1]` and the pack sha equals `snapshot.pack_sha256`.
- **L4. The Stage 1 `SHIPPED_MAPS` order is no longer pinned.**
  - The 94d9f29 rewrite removed the only full-order assertion. A mutant moving CP4 after CP6 survives every fast file that names `SHIPPED_MAPS` (2550 passed; pi1 exit 1 = survived).
  - I saw no functional effect, but brief §3's "existing order unchanged" rule is no longer guarded.

## Gates
- Lane pytest command: **exit 0** (1345 passed, 2 skipped, 2 xfailed, 114 s).
- `git grep noqa -- src tests | wc -l` = **13** (≤13). The `type: ignore` count = **8** (≤8).

## Probes
All are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/stage2-review-C/`, and each writes a matching `.out`:
- `pcc1_cp1c_bound_input_fix.py`
- `cp1c_mutants.py`, `cp1c_mutants_two.py`
- `cp1d_p*.out` (the reviewer's CP-1D probes, run with this root)
- `p7_view_vs_oracle_genuine.py`
- `p9_cpl10_mutants_batch.py`
- `pc1_class_paths_beyond.py`
- `pc2_verbatim_sinks.py`
- `pc3_model_payload_modules.py`
- `pc4_excluded_string_paths.py`
- `verify_findings_owner.py`
- `pi1_shipped_order_mutant.py`
- `pi2_g1x_delitem_reorders.py`
- `pi3_g1x_first_order.out`
- `pd1_manifest_chain.py`, `pd2_unrecorded_reuse_edits.py`, `pd3_prior_vs_parent.py`
- `pg1_forged_valid_step_issues.py`
- `gate_pytest.out`

Not verified: the fixed CP-1C A1 test was not re-run on a genuine promotion; it takes over 2 minutes and needs the heavy-job lock, so it was checked only on a fast store. `test_owner_cpl10.py` was not re-run at a1a0574, and p7 used the store the fixer built at fix time. The stage class test was not run through `OwnerWorkflow` with the journaled `RULES` for each core; only the two findings were. Null or absent free-text fields, G2 rendering, ruff and mypy, the full fast set and GitNexus `detect_changes` were not run.
