#!/bin/bash
# Probe: run the CZR RED tests (a3508c7 tests/test_czr_fixes.py) against the pre-fix code a3508c7
# and against the fix tip 57d3caf, each from a git archive (no worktree write). Prints the outcomes.
set -u
R="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s3-i4"
PY="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/.venv/bin/python"
D="$(cd "$(dirname "$0")" && pwd)/czr_red"
for c in a3508c7 57d3caf; do
  rm -rf "$D/$c"; mkdir -p "$D/$c"
  git -C "$R" archive a3508c7 tests/test_czr_fixes.py | tar -x -C "$D/$c"
  git -C "$R" archive "$c" src cases/czr-2026q2-earnings-update/documents pyproject.toml | tar -x -C "$D/$c"
  echo "== code at $c"
  (cd "$D/$c" && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src "$PY" -m pytest -q -p no:cacheprovider tests/test_czr_fixes.py 2>&1 | grep -E "passed|failed|Error" | tail -12)
done
