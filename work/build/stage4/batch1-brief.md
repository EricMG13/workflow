# Stage 4 batch 1: receipt verifier hardening, classes A-D (stage contract)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). Python: a relative `.venv` link in your worktree root to `L/.venv`; remove it before you hand back.

You run in your own isolated worktree. Before any edit, run `git checkout -b claude/s4-batch1 18dc1fa` and confirm the tip. Edit only:
- `src/deploy_workflow/owner_workflow.py`;
- `tests/test_owner_g1x.py`;
- `tests/test_owner_s1a.py`;
- the new `tests/test_owner_stage4.py`;
- `docs/G1X-OWNER-CORE-PROTOCOL.md` §4.

This is security-sensitive verifier code. An `mx-adversary` attacks it after you.

## Inputs
| Item | File |
|---|---|
| The plan (follow it exactly) | `L/work/build/stage4/plan.md` §0-4 and §6 batch 1 (line numbers are from c43b681; `owner_workflow.py` is unchanged at 18dc1fa) |
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` items 17, 19 (D1: document the gap) and 29 |
| Findings | `/Users/ericguei/Documents/Deploy Workflow Sessions/s1a-build/work/s1a/review-adversary-4.md` (HIGH 1, MEDIUM 1, LOW 1); `L/docs/reviews/s1a-owner-run.md` |
| Producer rule | `src/deploy_vii/execution.py` `Execution.begin` (read only) |

## Process (test first; commit after each class)
1. **Class A.** Write the plan's RED tests first and confirm they fail. Then add `_expected_begin` and change `_verify_begins`, `_verify_publications` and `_verify`, as §1 says. Keep `_verify_attempts` unchanged.
2. **Class B.** B1: add the `_check_specs` refusal for an analytical spec with no `_PROBES` row, with its RED test. B3: add the static `test_tool_use_sections_match_registrations` conformance test. B2 has no code change.
3. **Class C.** No code; run its named tests.
4. **Class D.** State the refused-record gap in `verify_owner_run_receipt`'s docstring and in `docs/G1X-OWNER-CORE-PROTOCOL.md` §4. The receipt stays `owner-run-receipt/1` (D1).

Each commit ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`. Never move an oracle or an existing genuine test. A genuine run that the new rule refuses is a defect in the replay; stop and report it.

## Gates (report each exit code)
- The plan's §6 batch 1 pytest command.
- `ruff check` and `ruff format --check` on the changed files.
- `MYPYPATH=src mypy --strict src/deploy_workflow/owner_workflow.py`.
- Suppressions: noqa ≤ 13, type: ignore ≤ 5.
- `python3 -I cases/pins.py --check`.
- **Deferred:** list the plan's batch 1 genuine runs as exact commands. Do not run them unless the gates above finish with time to spare. If you do run any, run them in the background and report each.

## Outputs (return as text, at most about 1.2k tokens)
Worktree path and tip SHA; what changed per class; RED test evidence (fail before, pass after); gate exit codes; deferred commands; `Not verified:` line; ledger line `agent=… fix-rounds=0 gates-first-pass=…`.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged. Never use bare `git stash`. Stop any background process before you hand back.
