# Owner suites: test and driver fixes A, B, D, E, F (stage contract)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: a relative `.venv` link in your worktree root to `L/.venv`; remove it before you hand back.

You run in your own isolated worktree. Before any edit, run `git checkout -b claude/s4-owner-tests ff9070e` (`claude/s4-int`) and confirm the tip. Edit only `tests/test_owner_cp2g.py`, `tests/test_owner_cp4c.py`, `tests/cp2g_runs.py`, `tests/cp4c_runs.py`, `tests/test_owner_cp3.py` and `tests/test_owner_cpl10.py`. Do not edit `cases/`, `src/`, `tests/test_method_cp2g.py` (another branch is changing it) or any lease.

## Inputs
| Item | File |
|---|---|
| Ruling (follow it) | `L/docs/rulings/2026-10-29-stage3.md` item 41 |
| Root cause and fixes (follow them) | `L/work/build/stage4/owner-suites-rca.md` causes A, B, D, E, F |
| Probes | `<S>/owner-rca/` (`probe_cp2g.py`, `probe_cp4c.py`, `probe_cp3.py`, `probe_cpl10_fix.py`, `run_probe.sh`) |
| Shard logs (the RED evidence) | `<S>/s4int/cp-0.log` (cp3), `<S>/s4int/cp-2.log` (cp2g, cpl10); cp4c tracebacks arrive in `<S>/s4int/cp-1.log` when that shard ends |
| Precedents | `tests/test_owner_s1a.py:376-381` (pack-hash marker), `:484` (signal count) |

## Process
The failing genuine tests are the RED tests; their failures are in the shard logs. Apply each fix exactly as the root-cause report gives it:
- **A:** in both `_assert_head_equals_oracle`, when the oracle `shown` is None, compare `text.replace("G1", "G#")` with `"∅ G#"` (missing) or `"∅ G# n.m."` (not applicable), taken from the manifest `cell_notation`, not hard-coded if the test can read it.
- **B:** in both drivers, bind a figure whose unit token differs as `{<fact_id>|<payload token>}`.
- **D:** replace the pack-hash marker with `closed.pack.content_hash()` before comparing.
- **E:** compare `len(body["cp1a_signals"])` with the frozen count.
- **F:** copied cells expect CP-1's own citations; derived cells use `one_per_page` in `_cites`.
Commit once per cause, each ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates (report each exit code and duration; one genuine pytest process at a time)
- The 17 failing tests that are not cause C (list in `<S>/s4int/failed-so-far.txt`; leave out `test_owner_cp2g.py::test_a1_one_ok_read_and_no_ok_pack_call_in_the_cp2g_step`, which needs the C oracle). Run them per file in the background: `tests/test_owner_cp3.py -k "cp0_r3 or register_counts"`, `tests/test_owner_cpl10.py -k closed_run_equals`, `tests/test_owner_cp4c.py -k "a1_positive or a2_gap or a3_each"`, `tests/test_owner_cp2g.py -k "a1_positive or a2_gap or a2c or a3_each"`.
- `tests/test_method_cp2g.py tests/test_method_cp4c.py tests/test_method_cpl10.py tests/test_connect_cp2g.py tests/test_connect_cp4c.py` (fast);
- `ruff check`, `ruff format --check`, `MYPYPATH=src mypy --strict` on the changed files; suppressions noqa ≤ 13 and type: ignore ≤ 5 (`git grep -c … -- src tests`).

If a test then fails for a reason the report does not name, find its root cause and stop and report it; do not change anything outside these files.

## Outputs (return as text, at most about 900 tokens)
Worktree path and tip SHA; the change per cause; gate exit codes and durations; `Not verified:` line; ledger line `agent=… fix-rounds=0 gates-first-pass=…`.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged. Never use bare `git stash`. Stop any background process you start before you hand back; if a stop is refused, say so and leave it.
