# Stage 3 end-batch Low L1: S.4 composer fixture title (stage contract)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). Python: a relative `.venv` link in your worktree root to `L/.venv`; remove it before you hand back.

You run in your own isolated worktree. Before any edit, run `git checkout -b claude/s3-low-s4 49628a0` (`claude/s3-i6`, the Stage 3 integration) and confirm the tip.

Edit only `tests/test_cp1_chart_render.py` and `tests/test_owner_rendering.py`.

## Inputs
| Item | File |
|---|---|
| Ruling | `L/docs/rulings/2026-10-29-stage3.md` item 25 ("S.4 fixture" and "End batch (Low L1)") and item 20 (Q1, the S.4 title regex) |

## Process (test first)
1. In `tests/test_cp1_chart_render.py` (about :155), change the hand-built S.4 title `"Maturity wall — current principal at 2025-12-31 (not a forecast)"` to `"Maturity wall — principal at 2025-12-31 (not a forecast)"`. Change any assertion in that file that expects the old title, and only those.
2. In `tests/test_owner_rendering.py`, remove the `exact_titles` parameter (about :1796-1803) and its use (about :1907-1917, including `fixture_title` and its comment), so the composer test checks S.4 against `_S4_TITLE_PATTERN` like every other figure.
3. Before step 2, show that the composer test passes with `exact_titles` removed only once step 1 is in place (run it with step 2 alone first and record that it fails; then apply step 1 and record that it passes).
4. One commit, ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates (report each exit code and duration)
- `tests/test_owner_rendering.py -k fast`;
- `tests/test_cp1_chart_render.py` in full (run it in the background if it is slow; report the result);
- `ruff check` and `ruff format --check` on both files;
- `MYPYPATH=src mypy --strict tests/test_owner_rendering.py tests/test_cp1_chart_render.py`;
- suppressions: `git grep -c noqa -- src tests` total ≤ 13, `type: ignore` ≤ 5.

## Outputs (return as text, at most about 600 tokens)
Worktree path and tip SHA; the change; the fail-then-pass evidence; gate exit codes; `Not verified:` line; ledger line `agent=… fix-rounds=0 gates-first-pass=…`.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged. Never use bare `git stash`. Stop any background process before you hand back.
