#!/bin/bash
# Usage: run_probe.sh <probe.py> <case> ; runs one probe in the s4-int checkout (read-only), store under owner-rca/<probe>-<case>
O="$(cd "$(dirname "$0")" && pwd)"
W="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s4-int"
P="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/.venv/bin/python"
name=$(basename "$1" .py)
cd "$W" || exit 2
PYTHONDONTWRITEBYTECODE=1 "$P" -I -c "import sys; sys.path[:0]=['src','tests']; sys.argv=['p','$2','$O/$name-$2']; exec(open('$O/$1').read())" > "$O/$name.$2.log" 2>&1
echo "exit=$?" >> "$O/$name.$2.log"
