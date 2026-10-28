# CP-5 Stage 2 review (mx-adversary)

**CP-5 Stage 2 review (8d9e2b1 on claude/s2-cp5, base 7a39384): REQUEST CHANGES. One Medium finding, which is a test gap. I found no behaviour defect.**

All probes are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp5-s2-review/`. I re-ran the gates: the fast set gives 380 passed (rc 0); `ruff check`, `ruff format --check` and `mypy --strict` on the 3 changed files all give rc 0. The worktree is still clean.

## Findings

**M1 (Medium): the store adapter has no test pinning its output, and mutants of its fields survive.**
- The brief §6 requires a test that the adapter returns exactly the Stage 1 test's input object. The brief's gate says every adapter-field mutant must be killed. The implementer's 14 mutants did not mutate any field of `review_scope`.
- The test that should do this proves nothing: `test_view_is_the_stage1_view_body_of_the_journal_scope` compares `view` with `view_body(review_scope(...))`, which is the same code.
- `test_view_matches_the_oracle_tree_counts…` compares `block["inherited_limitations"]` with `scope.inherited`, which comes from the same function.
- In `p8_mutants.py` (run in a full copy, against test_connect_cp5 and test_method_cp5), these mutants survived:
  - **A1:** `inherited=()`.
  - **A2:** `inherited` reversed.
  - **A3:** the `current_inputs` stale check dropped.
- G1 cannot catch A1 or A2: the probe rebuilds the head with the same mutated code, so only the Stage 5 R6 oracle would.
- The real adapter is correct. `p1_scope_equals_stage1.py` (exit 0) shows `review_scope` over the journal equals a Stage 1 fixture-style `ReviewScope` on both oracle cases, field by field (pack, inputs, heads, blocked, inherited, issues).
- **Fix:** add that probe's equality as a test. Also add a forged-attempt-inputs case for `view` and `ENTRY_VALIDATOR` (drop CP-3, or add an extra input), which kills A3.

**L1: the probe's use of `attempt.number` is not pinned.** My mutant P2 (`attempt.number` replaced by 0) survives, because every test settles attempt 0. A probe test on a head settled at attempt 1 would kill it.

**L2: the report overstates two tests.**
- `test_stale_head_status_is_a_stale_binding` (CP-1A) checks only `pytest.raises(WorkflowError)`. It does not check the error code and does not call `ENTRY_VALIDATOR`, although the report says both.
- The docstring of `test_stale_binding_after_a_head_is_resettled` names the probe, but the test does not exercise it.

**L3: some of the rows reported blocked can partly be tested now.**
- `p4_g1_seams_without_r6.py` (exit 0) runs these on a hand-built journal, with no R6 and no CP-6:
  - `owner._inputs` → `_owner_historical` → `_VIEWS["integrity_review"]` returns exactly `cp5.view`. This is the read-body recompute behind `cp5-tamper-read-body`.
  - `submit_model_payload` settles CP-5.
  - `_entry_outcome`, replaying an invalid step through `_ENTRY_VALIDATORS["CP-5"]`, reproduces the journaled issues exactly.
- **Genuinely blocked:** `cp6_closed`, the `test_owner_cp5.py` run assertions, RT-1 to RT-3 (they need the bound CP-1 head of a genuine R6 promotion), D3, `RefusedBegin` for CP-6, submit-before-read, the tool refusals, and receipt/store bytes at workflow level.

**Info:**
- **I1 (for LEAD):** registering CP-5 makes G1 accept CP-5 plans outside R6. `p3_plans_admitted.py` shows `_check_specs` accepts `(CP-0, CP-5)`, where nothing is evaluated, and `(CP-0, CP-1, CP-1A, CP-2, CP-5)`. R6 itself is refused while CP-6 is unregistered, and `CP-1 + CP-MODEL + CP-5` stays refused, as LEAD ruled. No lease line asks G1 to refuse the other plans.
- **I2 (predates this change):** the shared `probe_one_step` lets through a valid step carrying forged `issues`, because it does not recompute them (`p2_probe_forgeries.py`). The receipt step-hash check should catch this; I did not verify that.

## Checks with no defect
1. **Adapter, `view` and `ENTRY_VALIDATOR`.**
   - `p1b_forged_upstream.py` (exit 0) tries 10 forgeries × 2 cases. These are: a stale or re-settled CP-0, a re-settled CP-3, a flipped CP-1 head status, CP-3 bound as blocked, CP-3 or CP-2 dropped, a forged CP-2 or pack hash, and an extra input.
   - For every one, `view` raises `identity_mismatch`, `ENTRY_VALIDATOR` returns issues without raising, and `probe` refuses.
   - A blocked CP-3 is listed as blocked and its claims are excluded (tested).
   - **Dropping `pack` is admissible under protocol §2:**
     - `submit_cp5_step` hands `Execution.submit_step` the same `lambda _pack, current: _validate_step(store, current)`.
     - The core reads `store.pack(snapshot)`, which is checked against `snapshot.pack_sha256`. That is the same pack that `submit_step` and `_entry_outcome` would pass.
     - The lease's Public API names this adapter.
2. **`probe`.** In `p2_probe_forgeries.py`, every forgery of the CP-5 result is refused: head-row status, blob status, a fact's text, inherited limitations, a well-formed but forged output, the attempt payload hash, and a different valid payload.
3. **Registrations.**
   - Every row is appended last, and the only lines removed are two in-place edits.
   - The `OWNER_SPECS` row equals the lease, and `_check_steps` passes.
   - There is no `_CORES` and no `_PRECHECKS` row, which matches lease L2 and `rules="none"`.
   - The diff touches only 3 files, none of them CP-6. The two CP-5 selection tests pass (3 passed).
5. **Store-level tests already written.** Stale, tamper, blocked, store bytes and validator are correct for what they assert, apart from L2.
6. **Blank-quote inventory.** It is nil, as reported. `IntegritySubmission` has no citation or quote field, and CP-5 builds no `Citation`.
7. **Model-text rule.** `p7_model_text_no_raise.py` (exit 0) fed 15 hostile strings into every free-text and reference field and went through the real entry (`normalise` then `submit_cp5_step`). That is 210 cases with 0 raises.
   - CP-5 builds no `RunText`. `Finding.detail` and `subject` are `Text` and always carry a prefix. `Fact.text` and `Module.limitations` are plain `str`.
   - `_text_issues` returns syntax errors as issues instead of raising.
   - The round 3 ruling (be06667, 19:51) postdates the commit (19:43), so its `TypeAdapter` wording is not held against this commit.
8. **Mutants** (`p8_mutants.py`, 15 in total, 7 survivors):
   - **Killed (8):** A6, V1, V2, E1, P1, R1, R2, R3.
   - **Survivors that are gaps:** A1, A2, A3 (M1) and P2 (L1).
   - **Survivors that are redundant or equivalent:** A4 and A5 (covered by the `current_inputs` check), and A7 (equivalent on `_FrozenExecution`).

## No stubs, fakes or catch-alls
There is no stub, fake value or catch-all in `src`. The only fake in tests is the T8 "Run CP-5" fact the test fixture adds to CP-0.

Not verified: no R6 or OwnerWorkflow run (`read_inputs`, the receipt verifier, `_verify_settlements` end to end). The workflow-level tamper, refusal and store-bytes items were not run. Whether the receipt catches the I2 forged-issues step was not checked. The shared hostile-text test on claude/s2-defect-classes was not run against CP-5. A blocked head was only simulated by changing a status, not settled through `settle`. No GitNexus.
