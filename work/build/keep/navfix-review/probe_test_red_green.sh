#!/bin/zsh
# Runs tests/test_shell_css.py against trees at 64cfca9 (+new test) and 3c90773. Expect RED then GREEN.
set -u
L="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6"; D=/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/navfix-review
rm -rf $D/old $D/tree; mkdir -p $D/old $D/tree
cd "$L"
git archive 64cfca9 | tar -x -C $D/old
git show 3c90773:tests/test_shell_css.py > $D/old/tests/test_shell_css.py
git archive 3c90773 | tar -x -C $D/tree
cd $D/old; PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests "$L/.venv/bin/python" -m pytest -p no:cacheprovider -q tests/test_shell_css.py; r1=$?
cd $D/tree; PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests "$L/.venv/bin/python" -m pytest -p no:cacheprovider -q tests/test_shell_css.py; r2=$?
echo "old=$r1 new=$r2"; [ $r1 -ne 0 ] && [ $r2 -eq 0 ]
