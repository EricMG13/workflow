# Batch 2 round 3: review (stage contract; mx-precise, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Change: `claude/s5-round3` `2f345c2..ca17721` (`src/deploy_vii/report_view.py`, `src/deploy_vii/render.py`, `tests/test_connect_cp8.py`, `tests/test_connect_cpdr.py`, `docs/reuse/manifest.json`). Read with `git show`/`git diff` from `L`. For probes, extract a copy with `git archive ca17721 | tar -x -C <S>/round3-review/tree`, write only under `<S>/round3-review/`, never into any worktree, and delete the copy when done. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python` with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests -p no:cacheprovider`. Fast tests and probes only.

You did not plan or build this change.

## Inputs
| Item | File |
|---|---|
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` items 54, 56 |
| Plan | `L/work/build/stage5/token-class-plan.md` |
| Fixer's report | `L/work/build/stage5/round3-fix-report.md` |
| Probes | `L/work/build/keep/s53-conf/probe_c1_free_text_bracket_render.py`, `L/work/build/keep/token-plan/probe_rule.py`, `L/work/build/keep/stage4-review-arch/probe_e_report_data_payload.py` |

## Process
1. Check the change against the plan. The registry holds only `("CP-8", "cp8.what_changed")`. `_carries_reference` is registry membership plus `prose._RESERVED`, with no try/except. Both paths pass `names=(issuer_name,)`. No other fact is respelled.
2. Check that the CP-8 outcome still shows `∅ G<n>` in the block, the module table and the inspector (the payload probe). Check that a typo or unbalanced token in `cp8.what_changed` still fails closed on both paths, and that free or verbatim text with "[sic]", "[Reserved]", "[1]" or "{a|b}" in any other table renders as written.
3. Look for any table, other than `cp8.what_changed`, where a producer composes run text with tokens that the registry would now show raw. Search the owner modules for facts whose text is built from claim run text or tokens. A miss here is a High.
4. Show that the RED tests fail without the GREEN commit, on the copy. The D12 records must be correct.

Save each probe as a script under `<S>/round3-review/` and name it in its finding.

## Output (return as text, under 700 tokens)
Verdict (APPROVE / REVISE); findings ranked High, Medium, Low, Info, each with file:line, the failure scenario and the probe with its exit code; `Not verified:` line.
