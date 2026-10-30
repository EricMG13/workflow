#!/bin/zsh
# RED: ca17721's two test files copied into the base (2f345c2) copy -> expect 5 failures; GREEN: ca17721 copy -> 5 pass.
T=/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/round3-review/tree; B=/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/round3-review/base
K="verbatim_quote_holding or malformed_run_text or issuer_with_digits or bracketed_citation"
cp $T/tests/test_connect_cp8.py $T/tests/test_connect_cpdr.py $B/tests/
cd $B
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests "/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/.venv/bin/python" -m pytest -p no:cacheprovider -q -m "not genuine" tests/test_connect_cp8.py tests/test_connect_cpdr.py -k "$K" 2>&1 | grep -E "passed|failed|^FAILED" | cut -c1-220
cd $T
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests "/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/.venv/bin/python" -m pytest -p no:cacheprovider -q -m "not genuine" tests/test_connect_cp8.py tests/test_connect_cpdr.py -k "$K" 2>&1 | tail -1
