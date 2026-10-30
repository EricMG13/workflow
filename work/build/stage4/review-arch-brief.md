# Stage 4 review (stage contract; Fable mx-architect, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Change under review: `3429790..e37b73e` (`claude/s4-int2`; base `3429790` = the closed Stage 3 integration). Read it with `git show`/`git diff`/`git log` from `L`. For probes, extract a fresh copy with `git archive e37b73e | tar -x -C <S>/stage4-review/arch/tree` and write only under `<S>/stage4-review/arch/`; never write into any worktree, and delete the copy when done. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python` with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests` and `-p no:cacheprovider`. Run fast tests only; the controller runs the genuine (real-data) ones.

You write no code. `mx-adversary` already attacked batch 1 and its fix round; `mx-precise`/`mx-feature` reviewed each change. You check the stage end to end against its plan.

## Inputs
| Item | File |
|---|---|
| Stage 4 plan (the spec) | `L/work/build/stage4/plan.md` (principle and threat model §0; classes A-E §1-5; decisions §7) |
| Plan boxes | `L/docs/superpowers/plans/2026-10-28-verified-module-builds.md` :146-165 |
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` items 19, 21, 29-31, 33, 38, 41-43 |
| Batch 1 (classes A-D) | `L/work/build/stage4/batch1-report.md`, `batch1-adversary.md`, `batch1-fix1-report.md`, `batch1-fix1-adv.md` |
| Batch 2 (class E) | `L/work/build/stage4/batch2-report.md`, `batch2-review.md`, `cp8-oracle-report.md`, `cp8-oracle-review.md` |
| Owner-suite fixes | `L/work/build/stage4/owner-suites-rca.md`, `owner-tests-fix-report.md`, `owner-tests-review.md`, `cp2g-tree-oracle-report.md`, `cp2g-tree-oracle-review.md` |
| Gate runs (read last) | `<S>/s4int2/r-0.log`, `<S>/s4int2/r-1.log` (the 14 owner tests that failed on `ff9070e`, rerun on `e37b73e`), `<S>/s4int2/A.status` and `<S>/s4int2/fast.log` |

## Process
1. **Class A.** For every recorded transition, confirm the verifier re-runs `Execution.begin`'s rule on `before` and requires `after` exactly (plan §1): pending refusal, `current_inputs` with the explicit exception mapping, the `previous` rule, publication and submission identity binding, the final pending check and the deterministic head's final inputs binding. Name any recorded transition the verifier still accepts without replaying its rule.
2. **Class B.** The `_PROBES` row refusal at `create` and the `tool_use` conformance test assert against registries only and cannot pass vacuously (for example, zero oracles parametrised).
3. **Classes C, D.** C has no new code; D's known gap is stated in `verify_owner_run_receipt`'s docstring and `docs/G1X-OWNER-CORE-PROTOCOL.md` §4, and nothing claims more than it detects.
4. **Class E.** The CP-8 rails cell resolves `∅ G<n>` on the page with the same `n` as `T7.3.window.realized_value`; no settled fact carries a literal `∅ G#`; the `report_view` edits (items 30, 31) stay within the allowed scope; the CP-8 re-pin moved only the fields ruling 21 names.
5. **Owner fixes and oracle.** The test and driver changes (A, B, D, E, F) and the CP-2G tree change follow item 41 and do not loosen any comparison.
6. Across the diff: no stub or fake value standing in for real behaviour; no catch-all that hides a failure (a documented, logged fail-open is allowed); `src/deploy_vii` touched only where a ruling allows it.
7. Read the gate files last and report each one's state; a run without an `exit=` line is "pending", not passed.

Save each probe you run as a script in `<S>/stage4-review/arch/` and name it in its finding.

## Output (return as text, at most about 2k tokens)
Verdict (PASS / REVISE); findings ranked High, Medium, Low, Info, each with file:line, failure scenario and probe script (with its exit code); a class × status table (one line per class A-E, gaps only); `Not verified:` line.
