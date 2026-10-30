#!/bin/zsh
# usage: run_survey.sh <owner>  (runs tests/test_method_<owner>.py with the survey plugin)
R=/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/round4-plan
cd $R/tree
SURVEY_OUT=$R/survey_$1.json PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:$R/probes \
  "/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/.venv/bin/python" \
  -m pytest -p no:cacheprovider -p survey_plugin -q -m "not genuine" tests/test_method_$1.py > $R/log_$1.txt 2>&1
echo "$1 rc=$?"
