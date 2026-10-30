# Stage 4 batch 1 fix round 1 (stage contract)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: a relative `.venv` link in your worktree root to `L/.venv`; remove it before you hand back.

You run in your own isolated worktree. Before any edit, run `git checkout -b claude/s4-batch1-fix1 515a8c6` (`claude/s4-batch1`) and confirm the tip. Edit only `src/deploy_workflow/owner_workflow.py`, `tests/test_owner_s1a.py` and `tests/test_owner_stage4.py`.

This is security-sensitive verifier code. An `mx-adversary` re-attacks it after you.

## Inputs
| Item | File |
|---|---|
| Ruling (follow it) | `L/docs/rulings/2026-10-29-stage3.md` item 33 |
| Adversary report | `L/work/build/stage4/batch1-adversary.md` |
| Adversary probes | `<S>/s4-batch1-adv/probes/` (`probe_class_a.py`, `probe_class_b.py`, `probe_class_c.py`, `probe_class_d.py`, `probe_replay_differential.py`, `probe_cp_model.py`, `probe_cp_model_failed_first.py`, `probe_b3_vacuous.py`); the failing log `<S>/s4-batch1-adv/run-cpmodel-forgery.log` |
| Plan | `L/work/build/stage4/plan.md` §1 and §6 batch 1 |
| Producer rule | `src/deploy_vii/execution.py` `Execution.begin`, `finish`, `interrupt` (read only) |

## Process (test first)
1. **Medium 1.** Port P-A `test_a1` into `tests/test_owner_stage4.py` as a refusal test (a valid-step snapshot that relabels repair attempt A1 to `number=0, repair_of=None, repair_issues=()` must be refused `identity_mismatch`). Run it and record that it fails at 515a8c6. Then make every submission step require that the after-attempt's `(module_id, inputs, number, repair_of, repair_issues)` equals the attempt as begun, and record that it passes. Keep the genuine-repair control (P-A `test_a8`) accepted.
2. **High 1.** Rebuild `test_forgery_cp_model_attempt_with_cp1_dropped_from_inputs_refuses` and `test_forgery_cp_model_attempt_bound_to_another_cp1_refuses` (`tests/test_owner_s1a.py` about :2051 and :2068) so the forged receipt reaches `verify_owner_run_receipt` and is refused `identity_mismatch`. Use P-M's patched producer (one that also lets `finish`/`interrupt` accept the forged inputs) or P-F's failed-first route. For each test, show it is not vacuous: with the publication-path `_expected_begin` check (or the deterministic-head final binding it targets) made lenient in a scratch copy, the test fails. Do not commit the lenient version.
3. **Info.** In `test_tool_use_sections_match_registrations`, give the CP-0, CP-1 and CP-1A rows the registry assertion their `tool_use` section implies, or state in the test why only `kind` applies to them. Rerun P-V and report its count.
4. Commit after each step, each ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates (report each exit code and duration)
- The plan's §6 batch 1 pytest command.
- The two rebuilt High 1 tests (genuine, about 5 minutes each).
- Every probe in `<S>/s4-batch1-adv/probes/` except `probe_cp_model.py`. P-A `test_a1` asserts the old acceptance, so after the fix it must fail on that assertion (report its verdict). Every other probe case must still pass.
- `probe_cp_model.py` (about 16 minutes) in the background; report its result.
- `ruff check` and `ruff format --check` on the changed files; `MYPYPATH=src mypy --strict src/deploy_workflow/owner_workflow.py`; suppressions noqa ≤ 13 and type: ignore ≤ 5 (`git grep -c … -- src tests`); `python3 -I cases/pins.py --check`.
- **Deferred** (the controller runs these): full `tests/test_owner_s1a.py`, `tests/test_owner_workflow.py`, every `tests/test_owner_cp*.py`. List them as exact commands.

If a genuine run is refused by the new rule, that is a defect in the replay: stop and report it.

## Outputs (return as text, at most about 1k tokens)
Worktree path and tip SHA; the change per finding; RED evidence (fail before, pass after) and the non-vacuity evidence; gate and probe exit codes; deferred commands; `Not verified:` line; ledger line `agent=… fix-rounds=1 gates-first-pass=…`.

Rules: no stub or fake value standing in for real behaviour (a patched producer in a forgery test is the forgery, as the threat model allows); no catch-all that hides a failure unless documented and logged. Never use bare `git stash`. Stop any background process you start before you hand back; if a stop is refused, say so and leave it.
