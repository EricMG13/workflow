#!/bin/bash
# Usage: czr-shard2.sh <shard-file>; node ids one per line (may contain spaces).
W="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s3-i6"
P="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/.venv/bin/python"
ids=()
while IFS= read -r line; do [ -n "$line" ] && ids+=("$line"); done < "$1"
cd "$W" || exit 2
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests "$P" -m pytest -q -p no:cacheprovider "${ids[@]}" > "$1.log" 2>&1
echo "exit=$?" >> "$1.log"
