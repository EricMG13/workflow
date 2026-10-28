# CP-5 fix round 1 re-review (mx-adversary)

**CP-5 fix round 1 re-review (750f036 on 8d9e2b1): APPROVE.** The 5 findings this round fixed (M1, L1, L2, L3, plus the gate) are all closed. Only `tests/test_connect_cp5.py` changed, and its new tests use no stub, fake value or catch-all. The 1-64 character hashes are the forgeries under test. The worktree is still clean at 750f036.

The new probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp5-s2-review/fix1/`. They run against a fresh `git archive 750f036` copy in `fix1/copy`.

**M1: closed.**
- **Scope test (`p10_killers.py`, exit 0).** `test_review_scope_equals_the_stage1_scope` builds its expected scope from the Stage 1 oracle, not from src:
  - `inherited` is `EXPECTED[case]["inherited_limitations"]["sequence"]` passed through `stage1._flatten`, not `execution.inherited_limitations`.
  - `heads` are filtered by the oracle's `evaluated`, not by `NOT_EVALUATED`.
  - `inputs` are built by hand.
  - The probe shows this expected scope equals `stage1.make_fixture(case).scope` on every field the authorising CP-0 leaves unchanged (pack, inherited with 11 and 13 entries, blocked, issues, input ids and statuses, head ids), on both cases.
  - A1 and A2 are killed by this test alone.
- **Forgeries (`p9a_forgery_issues.py` exit 0, `p9b_forgery_refusal_removed.py` exit 0).**
  - When every refusal that fires for a forgery is removed, that forgery's cases fail (2 of 2) for all 6:
    - `cp3_bound_blocked`: A3 and A5.
    - `drop_cp2`, `drop_cp3`, `forged_pack_hash`: A3.
    - `extra_input` and `forged_cp2_hash`: A3, A4 and the swallowed `ValueError`.
  - Removing just one of several refusals is covered by the others. That is expected, not a gap.
  - A3 is killed by `test_forged_attempt_inputs_are_refused`.
- **Mutants (`../p8_mutants.py` on the full copy, `PYTHONDONTWRITEBYTECODE=1`): exit 2.**
  - 13 are killed, A5 now included.
  - Only A4 and A7 survive, as judged before: A4 is redundant with the `current_inputs` check, and A7 is equivalent.

**L1: closed.** `p10_killers.py` shows P2 is killed by `test_probe_accepts_a_head_settled_at_attempt_one`. `_finish` settles through the real `settle` at attempt 1.

**L2: closed.** `p11_l2_l3.py`, exit 0:
- The settled journal's probe passes before CP-2 is re-settled. After it, the validator reports `Stale input CP-2`, so the probe's `identity_mismatch` comes from the stale replay.
- With both stale checks cut (A3 and A4), both stale tests fail.

**L3: closed.**
- In `p11_l2_l3.py`, pointing the CP-5 `_ENTRY_VALIDATORS` row at `cp2.ENTRY_VALIDATOR` makes `test_g1_invalid_step_replays_the_entry_validator_issues` fail.
- R1 (`_VIEWS` row pointed at `cp2.view`) is still killed in p8.
- `test_g1_entry_settles_cp5` goes through the real `submit_model_payload`.

**Gates**
- Fast set in the worktree: 399 passed, rc 0.
- On the copy: `ruff check` 0, `ruff format --check` 0, `mypy --strict tests/test_connect_cp5.py` 0.
- p8 exit 2 (A4, A7). p9a 0, p9b 0, p10 0, p11 0.

**Info (no action):** the scope test copies the body of `make_fixture` instead of deriving its expected value from `make_fixture(case).scope`. This cannot be done directly because the heads differ through CP-0. If Stage 1 changes, the two could drift. p10 shows they agree today.

Not verified: no OwnerWorkflow or R6 run, so `cp6_closed`, RT-1 to RT-3, D3, the receipt verifier and the tool refusals are still blocked on CP-6. A blocked head is still simulated by changing its status. I1 and I2 were not re-examined (ruled). The full suite was not run, only the fast set. No GitNexus.
