#!/bin/bash
# Usage: czr-shard.sh <shard-file>; runs those node ids in the I5 worktree, one log per shard.
W="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s3-i4"
P="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/.venv/bin/python"
cd "$W" || exit 2
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests "$P" -m pytest -q -p no:cacheprovider $(cat "$1") > "$1.log" 2>&1
echo "exit=$?" >> "$1.log"
