# Stage 4 batch 2 fix round 2: scoped re-review (stage contract; mx-precise, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Change under review: `claude/s4-batch2-fix2` `e37b73e..35809c2` (`src/deploy_vii/render.py`, `tests/test_connect_cp8.py`, `docs/reuse/manifest.json`). Read it with `git show`/`git diff` from `L`. For probes, extract a copy with `git archive 35809c2 | tar -x -C <S>/fix2-rereview/tree`, write only under `<S>/fix2-rereview/`, never into any worktree, and delete the copy when done. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python` with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests -p no:cacheprovider`. Run fast tests and probes only; the controller is running the genuine CP-8 and CP-L10 cases on the integration branch.

## Inputs
| Item | File |
|---|---|
| Finding | `L/work/build/stage4/review-arch.md` Medium 1 |
| Ruling | `L/docs/rulings/2026-10-29-stage3.md` item 45 |
| Fixer's report | `L/work/build/stage4/batch2-fix2-report.md` |
| Probe | `L/work/build/keep/stage4-review-arch/probe_e_report_data_payload.py` |

## Process
1. Medium 1 only. Check that a known text fact that `_carries_reference` gets `display` and `table_display` from `resolve`, with the same binding and refs the block path uses (`report_view._token_runs`). Check that every other fact's spelling is unchanged, that there is no try/except, and that the helper is imported, not copied. Run the probe; it must exit 0. Show the RED test fails without the change, on the copy.
2. The fixer's scope probe also matched `{{…}}` template literals in `cases/cp5-owner/expected.json` and `cases/cpl10-owner/expected.json`. Decide, with file:line evidence, whether `prose._TOKEN` matches them, and whether any settled known text fact can still carry such text when a page is rendered (the drivers' substitution in `tests/cp5*_runs.py` and `tests/cpl10_runs.py`). If one can, the page now fails closed or changes. Show it with a probe on a fast fixture if possible.
3. The manifest record sits in `post_import_patches` and names the change.

Save each probe as a script under `<S>/fix2-rereview/` and name it in its finding.

## Output (return as text, under 600 tokens)
Verdict (APPROVE / REVISE); findings ranked High, Medium, Low, Info, each with file:line, the failure scenario and the probe script with its exit code; `Not verified:` line.
