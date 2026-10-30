#!/bin/zsh
# D12 strict probe over 697fe8a..3c90773 (repo arg must be the git lane). Expected bad: 3e5b537 24f879a 8aef58d only.
python3 -I "/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/work/build/keep/stage3-review/precise/probe_d12_strict.py" "/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6" 697fe8a 3c90773 | grep -E "BAD|GAP|MISPLACED" | grep -vE "3e5b537|24f879a|8aef58d" && exit 1 || exit 0
