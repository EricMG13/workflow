# Type annotations for `tests/test_cp1_chart_render.py` (stage contract; mechanical)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). Python: `L/.venv/bin/python`.

You run in your own isolated worktree. Before any edit, run `git checkout -b claude/s3-mypy-chart 18dc1fa` and confirm the tip. Edit only `tests/test_cp1_chart_render.py`.

## Why
`tests/test_owner_rendering.py` imports `test_cp1_chart_render`, so `MYPYPATH=src mypy --strict src/deploy_workflow/owner_rendering.py tests/test_owner_rendering.py` reports 61 errors, all in `tests/test_cp1_chart_render.py` (mostly missing return and parameter annotations). The gate must pass without `--follow-imports=silent`.

## Process
1. Add type annotations only, with the precise types the code already uses. No behaviour change: no logic, value, assertion, fixture or test-name change. No `type: ignore`, no `Any` where a concrete type is known, and no `cast` unless it is needed and states a true type.
2. One commit ending with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates (report each exit code)
- `MYPYPATH=src mypy --strict --cache-dir /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/mypy-cache/chart tests/test_cp1_chart_render.py` exits 0.
- `ruff check` and `ruff format --check` on the file.
- `PYTHONPATH=src:tests L/.venv/bin/python -m pytest -q -p no:cacheprovider --collect-only tests/test_cp1_chart_render.py` shows the same test count as at 18dc1fa.
- `git diff 18dc1fa -- tests/test_cp1_chart_render.py` changes only signatures and annotations. List any other line.
- Suppressions: `type: ignore` stays at 5 or fewer, `noqa` at 13 or fewer.

## Outputs (return as text, under 600 tokens)
Worktree path and tip SHA; error count before and after; gate exit codes; `Not verified:` line (the full render run of this file is deferred to the stage close); ledger line.
