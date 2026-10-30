# G2 fix round 4: one-register tabs-only oracle (stage contract)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: a relative `.venv` link in your worktree root to `L/.venv`; remove it before you hand back.

You run in your own isolated worktree. Before any edit, run `git checkout -b claude/s3-fix4-g2 a020996` (`claude/s3-i7`) and confirm the tip. Edit only `tests/test_owner_rendering.py`: `assert_block_equals_oracle` (about :2060-2095) and `test_fast_block_rule_handles_s_chip_gap_placeholder_and_tabs_only_oracle`.

## Inputs
| Item | File |
|---|---|
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` items 35 and 36 |
| Root cause and fix (follow it) | `L/work/build/stage3/cp1d-tab-rca.md` |
| Probes | `<S>/cp1d-tab-rca/probe3_cp1d_fast_block_rule.py`, `<S>/cp1d-tab-rca/probe4_proposed_fix.py` (each takes as its argument a copy made with `git archive <rev> src tests cases docs pyproject.toml`) |
| Failure log | `<S>/i6/g2d-0.log` |

## Process (test first)
1. Add the RED fast cases: an untabbed block (`tab_label` None, no tabs) against a tabs-only oracle with one entry passes on rows; a tabbed block against that oracle raises; the untabbed block with wrong rows raises. Record that the first case fails at a020996.
2. In `assert_block_equals_oracle`, after `wants = …`, compare a one-entry tabs-only oracle against `(None, rows)`, with a one-line comment naming `report_view`'s `tab_structure` rule and `tests/test_connect_cp1d.py:319-340`. Keep every other comparison strict. Record that the fast cases pass.
3. One commit, ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates (report each exit code and duration)
- `tests/test_owner_rendering.py -k fast`;
- both probes on a fresh `git archive` copy of your tip, under `<S>/fix4-g2/` (delete the copy afterwards; disk is low): probe 3 must now pass the cp1d blocks, probe 4 must exit 0;
- `tests/test_owner_rendering.py -k "genuine_deferred and cp1d"` (3 genuine cases), in the background, one pytest process;
- `ruff check`, `ruff format --check`, `MYPYPATH=src mypy --strict tests/test_owner_rendering.py src/deploy_workflow/owner_rendering.py`; suppressions noqa ≤ 13 and type: ignore ≤ 5 (`git grep -c … -- src tests`).

If a cp1d case then fails for another reason, find its root cause and stop and report it; do not change anything else.

## Outputs (return as text, under 800 tokens)
Worktree path and tip SHA; the change; RED evidence; gate and probe exit codes and durations; `Not verified:` line; ledger line `agent=… fix-rounds=4 gates-first-pass=…`.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged. Never use bare `git stash`. Stop any background process you start before you hand back; if a stop is refused, say so and leave it.
