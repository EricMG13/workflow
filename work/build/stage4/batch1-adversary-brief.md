# Stage 4 batch 1 adversary audit (stage contract; mx-adversary, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Change under attack: `claude/s4-batch1` `18dc1fa..515a8c6` (read with `git show`/`git diff` from `L`). Work only in fresh copies under `<S>/s4-batch1-adv/`, made with `git archive 515a8c6 | tar -x -C …`, and never write into any worktree. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python`. Note that `pyproject.toml` sets `pythonpath = ["src", "."]`, so run from the copy's root.

This is security code: the owner-run receipt verifier. The threat model is in `L/work/build/stage4/plan.md` §0. The attacker controls every receipt byte, every store file, the publication directory, and a patched runtime that writes them.

## Inputs
| Item | File |
|---|---|
| Plan, threat model, attack lists | `L/work/build/stage4/plan.md` §0-4 |
| Builder's report | `L/work/build/stage4/batch1-report.md` |
| Earlier findings | `/Users/ericguei/Documents/Deploy Workflow Sessions/s1a-build/work/s1a/review-adversary-4.md` (HIGH 1, MEDIUM 1, LOW 1) |
| Producer rule | `src/deploy_vii/execution.py` `Execution.begin` |

## Process
1. Try every attack case listed in plan §1 (class A), §2 (classes B1-B3) and §3 (class C). For each, either build the forged receipt or store and show the verifier's verdict, or show by code reference why it cannot be built. Prefer the fast `g1x` fake-module harness (`tests/test_owner_g1x.py` `_sealed`, `_reseal`, `_verdict`) over a genuine run.
2. Check that `_expected_begin` replays `Execution.begin` exactly: the pending rule, `current_inputs`, the `previous` rule, `number`, `repair_of` and `repair_issues`. Check that the exception mapping cannot be reached with a programming error. Check that the MEDIUM 1 final binding holds for the deterministic head.
3. Judge the builder's three test redesigns:
   - the forgeries patch `Execution.begin`;
   - the inputs test writes the store and calls `_verify_begins` directly;
   - the unblock test sets `workflow._phase`.
   For each, say whether it still proves the finding, or whether a forged receipt can pass by a route the test does not cover.
4. Check whether a genuine run could now be refused: CP-MODEL's second attempt after a failed first publication, a within-attempt repair, and the blocked-CP-1A controls. Use code reading, plus a fast-harness probe where you can.

Save every probe as a script in `<S>/s4-batch1-adv/` and name it in its finding.

## Output (return as text, at most about 1.5k tokens)
Verdict (PASS / FINDINGS); findings ranked High, Medium, Low and Info. Each finding gives file:line, the forged input, the verifier's verdict, and the probe script with its exit code. End with a `Not verified:` line.
