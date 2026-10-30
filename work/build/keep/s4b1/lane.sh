#!/bin/bash
# Usage: lane.sh <lane-name> <step-name>::<pytest args> ...
# Runs each step in the batch 1 fix worktree in order; one log per step; status lines to <lane>.status.
set -u
W="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s4-b1"
P="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/.venv/bin/python"
D="$(cd "$(dirname "$0")" && pwd)"
lane=$1; shift
cd "$W" || exit 2
for spec in "$@"; do
  name=${spec%%::*}; args=${spec#*::}
  free=$(df -g / | awk 'NR==2{print $4}')
  if [ "$free" -lt 4 ]; then echo "$(date +%H:%M) $name SKIPPED free=${free}G" >> "$D/$lane.status"; exit 3; fi
  start=$(date +%s)
  # shellcheck disable=SC2086
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests "$P" -m pytest -q -p no:cacheprovider $args > "$D/$name.log" 2>&1
  rc=$?
  echo "$(date +%H:%M) $name exit=$rc $(( ($(date +%s)-start)/60 ))m free=$(df -g / | awk 'NR==2{print $4}')G | $(tail -1 "$D/$name.log")" >> "$D/$lane.status"
done
