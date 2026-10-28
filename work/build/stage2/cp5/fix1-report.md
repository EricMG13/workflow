# CP-5 fix round 1 report (mx-feature)

CP-5 fix round 1 is committed as 750f036 on claude/s2-cp5, on top of 8d9e2b1. All findings are addressed. Only `tests/test_connect_cp5.py` changed; there is no `src` change. The review is not under the worktree, so I read it from `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/work/build/stage2/cp5/review.md`.

**Findings**
- **M1:**
  - `test_review_scope_equals_the_stage1_scope` (both cases) compares `review_scope` over the journal with a fixture-style `ReviewScope`, field by field: pack, inputs, heads, blocked, inherited, issues. It also asserts `inherited` is non-empty.
  - `test_forged_attempt_inputs_are_refused` has 6 forgeries: drop CP-3, drop CP-2, an extra input, a forged CP-2 hash, a forged pack hash, and CP-3 bound blocked. In each, `view` raises `identity_mismatch` and `ENTRY_VALIDATOR` returns issues with no output.
- **L1:** `test_probe_accepts_a_head_settled_at_attempt_one`. `make_journal` gained a `number` parameter, and the test asserts the settled CP-5 head is at attempt 1.
- **L2:**
  - `test_stale_head_status_is_a_stale_binding` now asserts the error code `identity_mismatch` and calls `ENTRY_VALIDATOR`.
  - `test_stale_binding_after_a_head_is_resettled` now runs on a settled journal and also exercises `probe`, which raises `identity_mismatch`.
- **L3:** three tests, all run on a hand-built journal.
  - `_inputs` serves exactly `cp5.view`, and `_VIEWS["integrity_review"] is cp5.view`.
  - `submit_model_payload` settles CP-5 on both oracle cases: finished, step valid, head restricted.
  - `_entry_outcome` on an invalid step replays issues equal to `ENTRY_VALIDATOR`'s and to the journal's `bounded_issues`.
- Round 1 remains "blocked on CP-6 freeze" for the OwnerWorkflow-level items: `cp6_closed`, RT-1 to RT-3, D3, and the receipt-level tamper and tool refusals. I1 and I2 are untouched, as instructed.

**Exit codes**
- `p1_scope_equals_stage1.py`: 0.
- `p4_g1_seams_without_r6.py`: 0. It was already 0 before the change, since it exercises `src` and not the tests.
- `p8_mutants.py` (15 mutants, run on a full copy, `PYTHONDONTWRITEBYTECODE=1`): exit 2. A1, A2, A3 and P2 are now killed, and so are the other 11 mutants except A4 and A7.
- A4 and A7 still survive. The review itself calls A4 redundant with the `current_inputs` check and A7 equivalent on `_FrozenExecution`, so I added no tests for them.

**Gates**
- Fast set (`test_connect_cp5`, `test_method_cp5`, `test_owner_g1x`, `test_host_h1`, `test_defect_classes_selfcheck`): 399 passed, exit 0.
- `ruff check` and `ruff format --check` on the changed files: exit 0.
- `mypy --strict` on `tests/test_connect_cp5.py` and `src/deploy_workflow/owners/cp5.py`: exit 0.

**Test-first:** the new tests pass against existing `src`, because the review's findings were test gaps and not code defects. The p8 mutants are the evidence: before this round A1, A2, A3 and P2 survived, and now they are killed.

Not verified: no OwnerWorkflow-level run, so the R6/CP-6 items are still blocked (receipt verifier end to end, tool refusals, forged read body at the verifier, the `RefusedBegin` blocked case). A blocked head is simulated by a status change, not settled through `settle`. I2 (the shared `probe_one_step` letting through forged step `issues`) is not tested. The shared hostile-text set was not run. No GitNexus `detect_changes`.

agent=mx-feature fix-rounds=1 gates-first-pass=y
