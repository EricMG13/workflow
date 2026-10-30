#!/bin/zsh
# Probe 2: final tests against pre-fix cpdr.py (6e5f6a3) plus GAP_ID_MAX only (issue rule dropped).
# Expect: the two refusal cases FAIL on validation accepting the id; exit 0 iff exactly those fail.
D="${0:A:h}"; S="$D/scratch-prefix"; W="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-aca609fa82ea6d6e5"
PY="/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/.venv/bin/python"
rm -rf "$S"; mkdir -p "$S"
git -C "$W" archive 0471089 | tar -x -C "$S"
git -C "$W" show 6e5f6a3:src/deploy_workflow/owners/cpdr.py > "$S/src/deploy_workflow/owners/cpdr.py"
printf '\nGAP_ID_MAX = IDENTIFIER_MAX - max(len("TDR.1.") + len(f".{field}") for field, _ in TDR1_COLUMNS)\n' >> "$S/src/deploy_workflow/owners/cpdr.py"
cd "$S"
out=$(PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests "$PY" -m pytest -q -p no:cacheprovider tests/test_connect_cpdr.py -k gap_id 2>&1)
print -r -- "${out[-600,-1]}"
[[ "$out" == *"2 failed, 2 passed"* && "$out" == *"assert () == ('gap_id is t"* ]]
