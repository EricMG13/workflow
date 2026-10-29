# CP-3 fix round 1 re-review (mx-precise)

**CP-3 fix round 1 re-review (f5d5bc4, e2669a2 on 8704e1f): APPROVE.** No High or Medium findings. M1, M2 and L1 are closed, and L2 is recorded as deferred.

**Gates and probes I re-ran** (worktree `s2-cp3`, clean)
- Brief pytest set (`test_connect_cp3`, `test_method_cp3`, `test_owner_g1x`, `test_host_h1`, `test_defect_classes_selfcheck`): 421 passed.
- `tests/test_owner_cp3.py --collect-only`: 38 collected.
- `p_create_refusals.py`: exit 0, same output as before.
  - R3 as pinned is refused until the ordering change lands.
  - The control without CP-MODEL is created, and so is the CP-3B selection.
  - Adding CP-4C or CP-3D is refused, and nothing is written.
- `mutants.py`: exit 1, as expected. 4 killed (now including "probe attempt number hardcoded 0") and 4 survive, all of them L2 driver mutants.
- Both scripts are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp3-s2-review/`.

**M1, acceptance coverage against lease :204-229: closed.**
- Each lease item now has a test:
  - **Upstream:** CP-0 R3, CP-1A with its deltas and `catalogue_size`, CP-2 equal to S1 (`test_owner_cp3.py:159-216`).
  - **CP-2 read body (M4):** key tree and register counts at `:226-249`.
  - **CP-3 head:** tables, with the row-label `column` through `_cell`; claims; own and settled limitations; inherited order per the oracle `order` rule; inputs; CONTEXT; render; probe (`:255-319`).
  - **Receipt and store bytes:** `:133`.
  - **Tool use:** including `market page:1` in CP-0, CP-1 and CP-1A, at `:329-362`.
  - **Refusals:** unread page, out-of-scope read and `cp3-stale-snapshot`, which expects `stale_binding` as the oracle does (`:373-403`).
  - **A4 tamper:** (a), (b) and (c) at `:409-472`.
  - **Blocked-CP-1A:** receipt, re-derivation and the oracle equality at `:496-523`.
- D3 is marked "blocked on the CP-6 freeze" (`:13-15`).
- The fast mirrors in `test_connect_cp3.py:603-735` also vary the inputs, so a constant equal to the oracle cannot pass. The caps move with the CP-1A status, and the render summary differs between the positive and gap cases.

**Create-time refusals: each has a working control.**
- CP-4C, CP-3D, CP-2D, CP-3C and CP-5 refuse against `CONTROL` (no CP-MODEL), and `test_control_selection_is_created` shows `create` accepts that control. Each refusal asserts `not_permitted` and that nothing was written.
- The 4 spec-override variants are paired with `test_the_unmodified_spec_mapping_is_created`.
- The CP-5 test skips itself once CP-5 has a spec. That is correct: the reason for its refusal would change.

**M2, CP-3B canonicalises (round 3 ruling): closed.** All four required checks are present:
- the CP-3B plan equals the CP-3 plan (`test_connect_cp3.py:740`);
- heads and attempts name CP-3 only, fast at `:749` and through the real receipt, deferred, at `test_owner_cp3.py:529-538`;
- `MODULES.csv` CP-3B is `unverified` in all four columns with `case_evidence none` (`:761`);
- CP-3B is not in `OWNER_SPECS` or `SUPPORTED_ANALYTICAL`.

**L1: closed.** A `positive-attempt-1` settled fixture was added (`test_connect_cp3.py:163-190`), and the hardcoded-0 mutant is now killed.

**L2: recorded.** The four survivors (`drive_cp1` ignoring `context=`, `cp1_bindings` taking the first match, the market `extractor` dropped, `drive_cp3` skipping the reads) are named in `fix1-report.md` for the deferred list.

**Info (no reopen)**
- The `blocked` fixture builds its own `closed_positive` rather than reusing the parametrised positive run, so Stage 5 pays for an extra CP-1 promotion.
- The fix report's "test-first" covers only the tests: they were first run after the code existed, so no failing run was observed for the right cause.

Not verified: none of the 38 tests in `test_owner_cp3.py` has run, because R3 `create` needs `claude/s2-g1x-order`. So these error codes are read, not observed: tamper (b) through the blob hash check, tamper (c) at the moved :1120 site, and the `interrupt` that produces the stale snapshot. The fix's CP-1A delta application, the inherited-limitations formula and the alias run's third promotion are also unobserved.
