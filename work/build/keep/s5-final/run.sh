#!/bin/bash
# Final verification (post-Stage-5 delta: CP-DR items 69/73, CZR items 70/74) on ../s5-final.
# Starts at 13:08Z per the test-speed session's window; 6 concurrent pytest processes at most.
W="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s5-final"
P="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/.venv/bin/python"
O="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/work/build/keep/s5-final"
until [ "$(date -u +%H%M)" -ge 1308 ]; do sleep 30; done
cd "$W" || exit 2
fast=$(tr ' ' '\n' < "$O/../fast-set.txt" | grep . | tr '\n' ' ')
run() { name=$1; shift; echo "start $(date +%H:%M)" > "$O/$name.log"; PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests "$P" -m pytest -q -p no:cacheprovider -rfE "$@" >> "$O/$name.log" 2>&1; echo "exit=$? end $(date +%H:%M)" >> "$O/$name.log"; echo "$name done"; }
run f1 $fast tests/test_shell_css.py &
run f2 tests/test_financial_workflow.py &
run f3 tests/test_financial_render.py &
run f4 tests/test_owner_s1a.py &
run f5 tests/test_owner_cp2a.py &
run f6 tests/test_owner_cpl10.py &
wait
grep -h "exit=" "$O"/f*.log
