#!/bin/zsh
# Restores e37b73e render.py on the copy; the two item-45 tests must fail, then restore 35809c2.
cd /private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/fix2-rereview/tree
git -C "/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6" show e37b73e:src/deploy_vii/render.py > src/deploy_vii/render.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests "/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/.venv/bin/python" -m pytest -p no:cacheprovider -q tests/test_connect_cp8.py -k spell 2>&1 | tail -4
r=${pipestatus[1]}
git -C "/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6" show 35809c2:src/deploy_vii/render.py > src/deploy_vii/render.py
echo red_pytest_exit=$r
[ $r -eq 1 ]
