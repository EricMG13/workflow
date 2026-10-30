#!/bin/zsh
# usage: run_probe.sh <src-dir> <log-name> <pytest args...>
# Runs one pytest process from the tip copy's root with <src-dir> first on the path.
D=/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch1-fix1-adv
L="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6"
T="$D/tip"
SRC="$1"; LOG="$D/$2"; shift 2
cd "$T" || exit 2
start=$(date +%s)
PYTHONSAFEPATH=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$SRC:$T/tests:$T" \
  "$L/.venv/bin/python" -m pytest -q -s -rA -p no:cacheprovider --rootdir "$T" -c "$T/pyproject.toml" \
  -o "pythonpath=$SRC $T" "$@" > "$LOG" 2>&1
rc=$?
echo "exit=$rc elapsed=$(( $(date +%s) - start ))s" >> "$LOG"
exit $rc
