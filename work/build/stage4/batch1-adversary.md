## Stage 4 batch 1 adversary audit (515a8c6). Verdict: FINDINGS (1 High, 1 Medium, 2 Info)

The verifier code changes hold up. Every attack in plan §1-3 was refused, except the Medium route below. The High finding is a test defect, not a code defect.

Probe files are referred to by label:
- P-A: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch1-adv/probes/probe_class_a.py` (8 passed, exit 0)
- P-B: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch1-adv/probes/probe_class_b.py` (exit 0)
- P-C: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch1-adv/probes/probe_class_c.py` (exit 0)
- P-D: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch1-adv/probes/probe_class_d.py` (exit 0)
- P-R: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch1-adv/probes/probe_replay_differential.py` (exit 0)
- P-M: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch1-adv/probes/probe_cp_model.py` (4 passed, 976 s, exit 0)
- P-F: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch1-adv/probes/probe_cp_model_failed_first.py` (exit 0)
- P-V: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch1-adv/probes/probe_b3_vacuous.py` (exit 0)

### HIGH 1: the two MEDIUM 1 tests fail at the tip and never reach the verifier
- **Where:** `tests/test_owner_s1a.py:2051` and `:2068`.
- **Result:** I ran both. Each fails with `assert 'not_permitted' == 'identity_mismatch'` at :2065 and :2085; exit 1, 296 s. Log: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch1-adv/run-cpmodel-forgery.log`.
- **Cause:** the tests patch only `begin`.
  - The genuine `Execution.finish` then refuses with "Ticket inputs have changed" (`execution.py:696`), and the interrupt fails the same way.
  - `publish` sets `_phase="failed"` (`owner_workflow.py:1414-1416`), so `write_receipt` raises `not_permitted` (:1457).
  - MEDIUM 1 has no receipt-level RED test, and the deferred full s1a gate will exit 1 as committed.
- **The code itself is correct (P-M, P-F):**
  - With a patched producer that also lets `finish`/`interrupt` pass, drop-cp1 and other-cp1 both refuse `identity_mismatch`. The deterministic-head final binding refuses on its own (P-M p4).
  - P-F p5: a forged failed first publication on a drop-cp1 input set lets a second attempt 0 publish. The tip refuses it. With the publication-path `_expected_begin` made lenient it is **accepted** (p6), so that check is the one that closes this route.
- **Fix:** rebuild the two tests on P-M's patched producer, or on P-F's failed-first route.

### MEDIUM 1: a valid-step submission can relabel a repair attempt as a first try (code predates the batch, but plan §1's "no exemption remains" is not met)
- **Where:**
  - `owner_workflow.py:2083-2103`: the `_verify_submissions` valid branch never compares the after-attempt's begin-set fields with the historical attempt.
  - `:1580-1592`: `_verify_transition` lets a ticket's own attempt change freely.
  - `:1977-1979`: any number of attempt-0s is still accepted.
- **Forged input:** A0 is rejected genuinely and A1 is begun genuinely (number 1, `repair_of` A0). A patched core then rewrites A1 to `number=0, repair_of=None, repair_issues=()` in the snapshot of its first (valid) step. The second step is valid and settles the head.
- **Verdict: accepted**, both by the runtime seal and by `verify_owner_run_receipt` (P-A `test_a1`). The final snapshot holds two attempt-0s on one input set, the head Module says attempt 0, and the begin record says attempt 1. The same forgery is also accepted at 18dc1fa.
- **Impact:** no extra try is gained. Inputs cannot be rewritten (`_owner_historical` checks `current_inputs` at :747), and a third begin is still refused. But a repaired result passes as a first-try one, which bypasses R4-1.
- **Fix:** require the after-attempt's `(module_id, inputs, number, repair_of, repair_issues)` to equal the historical attempt's.
- **Routing:** since the code predates the change, the owner may need to rule on whether it belongs in this batch.

### Info
- **Class D gap is as documented.** Deleting a refused record and its binding, renumbering and resealing is accepted (P-D).
- **B3 test is partly vacuous.** In `test_tool_use_sections_match_registrations`, 11 of 28 rows reach only the `kind` assertion (the CP-0/CP-1/CP-1A rows) (P-V).

### Attacks refused (identity_mismatch unless noted)
- **Class A (P-A):**
  - `repair_issues` rewritten, both at the begin and in a valid step that keeps number 1.
  - A begin whose `before` is an older ancestor.
  - Two begins with swapped ticket ids.
  - A pending attempt relabelled finished with an interruption, no issues and no head.
  - A `before` where CP-0 no longer commands the module (NotAuthorized). A TypeError raised inside `current_inputs` propagates unchanged rather than being mapped.
  - The genuine-repair control is accepted.
- **Third-try, dangling, unblock:** the builder's tests pass.
- **CP-MODEL attempt numbered 1 with no failed first publication:** refused by code (`:1766-1775` yields number 0).
- **Replay exactness (P-R):** over 4000 seeded random snapshots, `_expected_begin` and `Execution.begin` never disagreed (3124 both refuse; 876 identical attempts, 222 of them number 1).
- **Class B (P-B):** dropped issue, reordered issues, refused changed to invalid, invented validator issue, refused call forged as ok with a body, evidence naming an unread page, altered `read_inputs` body, zero reads forged valid.
- **Class C (P-C):** payloads nested 65, 300 and 5000 deep, a dict or list tag, an escaped surrogate and CESU bytes all refuse `identity_mismatch`. No TypeError or RecursionError escaped.

### The builder's three test redesigns
1. **Patching `begin`:** proves the begin route. It does not cover the submission route in Medium 1.
2. **Calling `_verify_begins` directly:** a sound unit test. At receipt level, analytical inputs were already bound at every submission (`:747`; `financial_workflow.py:291`). The receipt-level route where begin inputs matter is CP-MODEL, which is High 1.
3. **Setting `_phase`:** a fair model of a patched runtime, and it reaches the same `_verify`. I found no other way to unblock a blocked head.

### Genuine runs
- **CP-MODEL second attempt after a failed first publication:** accepted (P-M p1).
- **Blocked-CP-1A controls and forgery_unblock:** 4 passed in 1408 s, exit 0.
- **Builder's gates re-run:** the fast gate set gave 131 passed, 1 skipped; ruff, ruff format and mypy --strict all exit 0.

Not verified: a genuine within-attempt repair (code reading only); the full `test_owner_s1a.py`, `test_owner_workflow.py` and `test_owner_cp*.py`; whether real module probes (rather than the g1x fake) would catch the Medium 1 relabel; an ok `read_pages` outside the H1 scope (the fake session accepts any page); the two-publication "already exists" control; mutation and property gates. I did not touch the builder's stray pid 79376.
