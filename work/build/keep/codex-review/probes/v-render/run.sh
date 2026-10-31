#!/bin/zsh
S=/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-codex-findings-review-64c673/ee01671b-a922-47ba-ad87-32129314cd1e/scratchpad/v-render
cd $S/tree
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$S/tree/src:$S/tree/tests TMPDIR=$S/tmp HYPOTHESIS_STORAGE_DIRECTORY=$S/tmp/hyp '/Users/ericguei/Documents/Deploy Workflow/.venv/bin/python' "$1" > "$1.log" 2>&1
rc=$?
echo "EXIT $rc" >> "$1.log"
tail -15 "$1.log"
exit $rc
