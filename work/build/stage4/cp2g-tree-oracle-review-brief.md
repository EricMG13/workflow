# CP-2G view-tree oracle change: independent review (stage contract; mx-precise, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Change under review: `claude/s4-cp2g-tree` `ff9070e..cb66e6c` (`cases/cp2g-owner/cp2g-view-tree.json`, `cases/PINS.json`, `tests/test_method_cp2g.py`). Read with `git show`/`git diff` from `L`; for probes make a fresh copy under `<S>/cp2g-tree-review/` with `git archive cb66e6c | tar -x -C …` and delete it when done. Never write into any worktree. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python`. One genuine pytest process at a time.

You are the independent reviewer of an oracle change: you did not prepare it and you did not build CP-2G.

## Inputs
| Item | File |
|---|---|
| Ruling | `L/docs/rulings/2026-10-29-stage3.md` item 41, cause C |
| Root cause | `L/work/build/stage4/owner-suites-rca.md` cause C |
| Preparer's brief and report | `L/work/build/stage4/cp2g-tree-oracle-brief.md`, `L/work/build/stage4/cp2g-tree-oracle-report.md` |
| Probe | `<S>/owner-rca/probe_cp2g_viewtree.py` (takes a saved `owner-receipt.json`) |

## Process
1. Confirm that only the six `limitation` leaves (`base.operands.cash_interest` and `cash_taxes`, in positive, gap and cp1d_blocked) and the `_note` moved in the tree, and only that one pin moved; `pins.py --check` exits 0 on the copy.
2. **The preparer's open point.** Prove from code, with file:line, the path from CP-1's `SIGN_NORMALISED` note to the CP-2G view's `limitation` leaf, and that the gap and cp1d_blocked runs carry the same CP-1 head for these two metrics (read the drivers' pack and case selection in `tests/cp2g_runs.py`). If a case would not carry it, that case's leaves must not move: report it as a finding.
3. The seed change in `tests/test_method_cp2g.py` gives "sign normalised" only to known `cash_interest` and `cash_taxes`, matching genuine CP-1, and does not loosen any assertion. Run `tests/test_method_cp2g.py tests/test_connect_cp2g.py` on the copy.
4. Run `tests/test_owner_cp2g.py -k a1_one_ok_read` once on the copy (genuine, about 6 minutes).

## Output (return as text, under 700 tokens)
Verdict (APPROVE / REVISE); findings ranked High, Medium, Low, Info, each with file:line and a probe script with its exit code; `Not verified:` line.
