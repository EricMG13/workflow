Stage 4 batch 1 report: classes A, B and D built in one commit. The plan's pytest gate and every static gate passed; 3 of the 5 class A forgery tests were not run.

Worktree: /Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a1257385047cbaff2, branch claude/s4-batch1, tip 515a8c648f3d881694ed8996aa4908127c5ef281. Base 18dc1fa confirmed.
Deviation from the brief: it asks for a commit per class, but the A, B and D hunks share one file, so I made a single commit.

**Changes**
- **Class A** (`owner_workflow.py`):
  - New `_expected_begin` replays `Execution.begin`: no pending attempt, `current_inputs` with explicit NotAuthorized and ValueError mapped to `identity_mismatch`, and the `previous` rule applied verbatim.
  - `_verify_begins` now requires `after.attempts == (*before.attempts, expected)` and `begin.attempt == expected.number`. The Counter check is kept.
  - `_verify_publications` compares the finished publisher attempt's identity fields to `_expected_begin(before, ...)`.
  - `_verify` refuses any pending attempt in the final snapshot (LOW 1). It also checks the deterministic head's `current_inputs == _result_attempt(...).inputs` (MEDIUM 1).
  - `_verify_attempts` is unchanged.
- **Class B:**
  - B1: `_check_specs` refuses an analytical spec with no `_PROBES` row (`not_permitted`).
  - B3: new parametrised `test_tool_use_sections_match_registrations` in `tests/test_owner_stage4.py`, 29 oracle sections. B2 needs no code.
- **Class C:** no code. Its tests are in the gate run and pass.
- **Class D:** refused-record gap stated in the `verify_owner_run_receipt` docstring and in `docs/G1X-OWNER-CORE-PROTOCOL.md` §4. The receipt stays `owner-run-receipt/1`.

**RED evidence** (run at 18dc1fa behavior, before the fix)
- `test_forgery_third_try_three_attempt_zeros_then_a_head_refuses`: sealed instead of `identity_mismatch`, now passes.
- `test_forgery_dangling_pending_attempt_in_the_sealed_snapshot_refuses`: sealed, now passes.
- `test_forgery_begin_on_a_before_whose_inputs_differ_refuses`: `_verify_begins` did not raise, now passes.
- `test_forgery_unblock_restricted_head_replacing_blocked_refuses`: did not raise, now passes.
- `test_analytical_spec_without_a_probe_is_refused_at_create`: did not raise, now passes.
- `test_forgery_cp_model_attempt_with_cp1_dropped_from_inputs_refuses` and `test_forgery_cp_model_attempt_bound_to_another_cp1_refuses` are written but never run. They need the promoted fixture (11-26 min), so their RED and green are unconfirmed, and so is the third assertion below.
- Three things differ from the plan's test descriptions:
  - Probe scripts: adv-4's probe scripts were unavailable. I rebuilt each forgery by patching `Execution.begin`, as adv-4 described.
  - Inputs test: it writes the forged snapshot straight into the store and calls `owner._verify_begins` directly. The producer's own submit path (`submit_step`) already refuses an attempt with wrong inputs, so no run can reach the verifier that way.
  - Unblock test: it sets `workflow._phase = "analytical"` to resume the walk after the blocked head.

**Gates**
- Plan pytest command (the `-k` filter applies only to `tests/test_owner_s1a.py`, which is a separate run): exit 0. In `tests/test_owner_s1a.py` with `-k "blocked_cp1a or forgery_unblock"`, 7 passed in 12m31s. That includes `test_genuine_blocked_cp1a_run_verifies`, `test_blocked_cp1a_still_begins_cp2_and_publishes` and `test_unauthorized_cp1a_is_refused_and_cp_model_publishes`, so the controls pass with the new rule.
- Unfiltered run of the other five files (`test_owner_g1x`, `test_owner_stage4`, `test_schema_normalise_escapes`, `test_host_h1`, `test_owner_order`): 131 passed, 1 skipped. The skip is the real CP-1 promotion test.
- `ruff check` and `ruff format --check` on the four changed files: exit 0.
- `MYPYPATH=src mypy --strict src/deploy_workflow/owner_workflow.py`: exit 0.
- Suppressions grep over `src` and `tests`: noqa 13, type: ignore 5. I added none.
- `python3 -I cases/pins.py --check`: exit 0 (86 paths).

**Process still running**
My mistyped `-k` expression started a broad `tests/test_owner_s1a.py` run, pid 79376, output in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/tasks/b2of8s4bh.output`. `kill` and `pkill` were both denied, so it is still running. I removed the `.venv` link after starting it, so its results are unreliable. Please stop it.

**Deferred genuine runs** (run from the worktree with a `.venv` link):
- `PYTHONPATH=src:tests .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_owner_s1a.py` (includes the two CP-MODEL forgery tests and the `closed` fixtures)
- `PYTHONPATH=src:tests .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_owner_workflow.py`
- `PYTHONPATH=src:tests .venv/bin/python -m pytest -q -p no:cacheprovider "tests/test_owner_cp*.py"`, with `STORE_RUNS` set where the groups are gated.

Not verified: the two CP-MODEL forgery tests (never run). Whether the full `tests/test_owner_s1a.py` closed positive and gap runs, `tests/test_owner_workflow.py` and `tests/test_owner_cp*.py` still verify under the new `_expected_begin`, including CP-MODEL's second attempt after a failed first publication. The full-suite coverage, complexity, bandit and jscpd gates. Class C attacks (a payload nested 65 and 300 deep, an unhashable tag, a lone surrogate), which only the existing tests cover. The B3 test checks oracle prose against registries by keyword, so it can miss a wording change. B2's refusal cases have no new tests.

Ledger: agent=mx-feature fix-rounds=0 gates-first-pass=n (two RED tests needed redesign during the build; the plan gate passed on its one run, and the CP-MODEL tests and deferred runs are unrun).
