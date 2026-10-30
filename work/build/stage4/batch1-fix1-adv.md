## Stage 4 batch 1 fix round 1 re-review (claude/s4-batch1-fix1, 515a8c6..715dc98). Verdict: PASS (0 High, 0 Medium, 0 Low, 3 Info)

**Bottom line:** High 1 and Medium 1 are closed, and I found no genuine run that the Medium 1 rule refuses. All results below are from fresh runs on `git archive` copies. The copies are deleted; the probes, logs and the scripts that rebuild the copies are kept.

**Medium 1: closed** (`src/deploy_workflow/owner_workflow.py:1596-1601`)
- **P-A rerun:** 7 passed, 1 failed, exit 1. The one failure is `test_a1`, whose old assertion expects `accepted`; it now gets `write_receipt:identity_mismatch`.
- **Field probe:** 30 passed, exit 0. Every forgery is refused both by `write_receipt` and by `verify_owner_run_receipt`:
  - **Valid step relabelled to a first try** (number 0, repair cleared; first or settling step): refused at `_verify_transition:1601`. At 515a8c6 the first-step relabel is **accepted**, so this route is the one the fix closes.
  - **Valid step, one field changed** (module_id, inputs, number only, repair_of, repair_issues): refused at `_verify_attempts:1988/2001`, or at runtime and then `_verify:2231`.
  - **Rejected step:** module_id or inputs changed is refused at `:1601`. number, repair_of or repair_issues changed is refused at `_verify_attempts`. A blocked attempt 1 relabelled to number 0 is refused at `:1601`.
  - **Interrupts:** an analytical interrupt is refused at `_verify_attempts:2011`. A CP-MODEL interrupt that rewrites repair_issues or inputs is refused at `_verify_publications:1784`.
  - **Final snapshot:** a snapshot appended after the last step is refused at `_verify_chain:1657`; a resealed sibling snapshot is refused at `:1601`.
  - **A step that rewrites another ticket's attempt** (the same module's attempt 0, or CP-0's): refused at `_verify_attempts`.
  - **Attempt absent before the step:** before-only, both, or ticket None all give identity_mismatch (`:1583`).
  - **Control:** a genuine repair is accepted.
- **Fixer's RED:** at 515a8c6 the relabel test fails with DID NOT RAISE; at the tip `test_owner_stage4.py` gives 34 passed.

**No genuine refusal.** Only `Execution.begin` writes the five fields: `execution.py:662-667` (written at `:669`). No later write touches them:
- `finish` sets `payload_sha256` only (`:713`).
- `settle` sets status, issues, result and interruption (`:493-500`); `_save_finished` stores that attempt (`:753-762`).
- `submit_step` sets steps and step_repairs (`:835`, `:860-862`, `:865`) and `payload_sha256` (`:875`).
- `interrupt` goes through `finish` (`:893`). `replace_pack` touches only heads and the pack, and refuses while an attempt is pending (`:902-917`).
- Owner-side writers: begin at `owner_workflow.py:1117` and the one interrupt at `:1411`, which is CP-MODEL only and a publication transition, so the new rule does not apply.

Probe results:
- Genuine within-attempt repairs (attempt 0, repair attempt 1, sourced step) and a genuine twice-rejected run: all accepted, fields kept; exit 0.
- CP-MODEL second attempt after a failed first publication (p1): accepted by both.

**High 1: closed**
- The 3 `forgery_cp_model` tests: 3 passed, exit 0, 425 s.
- The probe gives the same receipts, sealed, to `verify_owner_run_receipt`: drop-cp1 and other-cp1 are refused at `_verify:2244`, failed-first at `_verify_publications:1784`.
- After the test helper returns, `execution.current_inputs` is the original function again, and `owner_workflow` bound the original at import. Tripwires during verification counted 0 calls to `Execution.begin` and 0 to `execution.current_inputs`.
- Lenient copies (each run exited as noted):

| Made lenient | P-M tests (drop-cp1, other-cp1) | P-F test | Exit |
|---|---|---|---|
| Publication check only | pass | fails, DID NOT RAISE | 1 |
| Head binding only | pass | pass | 0 |
| Both | fail | fails | 1 |

  This matches the fixer's evidence.

**Info (Low/Info scope).** Info 1 closed: a source-level mutant of `host._SOURCE_STEPS` (CP-1 loses `financials`) fails 5 rows (exit 1), and runtime mutants fail every pack-tool row.

**Info findings**
1. **The P-M tests do not pin either check on its own** (`owner_workflow.py:1776-1784` and `:2243`; see the table). The P-F test does pin the publication check. At receipt level the head binding seems to follow from the publication check plus `:1602-1607`, so no receipt-level test could pin it alone. I'd accept this.
2. **An in-step relabel that is undone before the step ends passes the endpoint equality, by design.** What it leaves behind is caught elsewhere:
   - mid-settle (head Module says attempt 0): `write_receipt` raises a raw `ValueError` from the g1x fake core's probe (`_verify_settlements:2190`); `verify_owner_run_receipt` maps it to identity_mismatch (`:2413`). This is fail-closed, fake-core behaviour that predates the batch.
   - mid-rejected: refused at `_verify_walk:1685`.
   - mid-sourced: accepted, but nothing forged is left in the store.
3. **`test_valid_step_rewriting_repair_issues_is_refused` also passes at 515a8c6**, so it is a regression guard, not a RED test.

**Probes and logs** (exit codes are given above):
- Folder: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch1-fix1-adv/`. It holds `run-*.log`, `run_probe.sh`, `run_slow_chain.sh`, `make_mutants.py` and `make_info_mutant.py`.
- P-A: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch1-adv/probes/probe_class_a.py`
- Field probe: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch1-fix1-adv/probe_m1_fields.py`
- Extra relabel probe (5 passed, exit 0 at the tip): `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch1-fix1-adv/probe_m1_extra.py`
- Genuine within-attempt repairs: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch1-fix1-adv/probe_genuine_within_attempt.py`
- CP-MODEL routes (7 passed, exit 0, 1126 s): `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch1-fix1-adv/probe_cp_model_rereview.py`
- Which src a run loaded: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch1-fix1-adv/probe_which_src.py`
- Info mutants (18 passed, exit 0): `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch1-fix1-adv/probe_info_source_steps.py`

The lane worktree is unchanged, and none of my processes are still running.

Not verified: a genuine run that repairs on real modules (only the g1x fake harness and the S1a CP-MODEL path were exercised); whether real module probes catch an in-step relabel the way the fake core's probe does; the deferred full suites `test_owner_s1a.py`, `test_owner_workflow.py` and `test_owner_cp*.py`, including how the new `pytest_plugins = ("test_owner_g1x",)` behaves in a full-suite collection; mutation and property gates.
