#!/bin/zsh
# Serial slow runs for the High 1 re-review (one pytest process at a time).
D=/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s4-batch1-fix1-adv
R="$D/run_probe.sh"
"$R" "$D/tip/src" run-high1-tip.log tests/test_owner_s1a.py -k forgery_cp_model
"$R" "$D/tip/src" run-cpmodel-rereview.log "$D/probe_cp_model_rereview.py"
"$R" "$D/mut-pub/src" run-high1-mut-pub.log "$D/probe_which_src.py" tests/test_owner_s1a.py -k "which_src or forgery_cp_model"
"$R" "$D/mut-head/src" run-high1-mut-head.log "$D/probe_which_src.py" tests/test_owner_s1a.py -k "which_src or forgery_cp_model"
"$R" "$D/mut-both/src" run-high1-mut-both.log "$D/probe_which_src.py" tests/test_owner_s1a.py -k "which_src or forgery_cp_model"
echo chain-done
