# G2 coverage gaps: specification review (stage contract; mx-precise, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Code base: `e37b73e` (`claude/s4-int2`); read with `git show e37b73e:<path>` from `L`. For probes, extract a copy with `git archive e37b73e | tar -x -C <S>/g2-gaps-spec-review/tree`, write only under `<S>/g2-gaps-spec-review/`, never into any worktree, and delete the copy when done. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python` with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests`. Run no genuine (real-data) tests.

You are the independent reviewer. You did not prepare this specification and you did not build G2.

## Inputs
| Item | File |
|---|---|
| Specification and controller rulings | `L/work/build/stage5/g2-gaps-spec.md` (the rulings at the end are part of it) |
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` items 28, 44, 46 |
| Lease | `docs/OWNER-RENDERING-LEASE.md` Acceptance 1 (:105-112), R2.5 (:281-), R2.8 (:328-) |
| Oracles | `cases/cp3d-owner/expected.json`, `cases/cp4-owner/expected.json`, `cases/cp8-owner/expected.json`, `cases/snapshot/expected.json` |
| Preparer's probes | `L/work/build/keep/g2-gaps-spec/` (`common.py`, `probe0`-`probe4`) |

## Process
1. For each rule, check it against the lease text and the oracle: it reads expectations from the oracle, never from G2. It is no looser than the lease, and the controller rulings are applied.
2. Rerun the preparer's probes on a fresh copy and report each exit code. Then try at least one perturbation per rule that the preparer did not try, and confirm the rule fails it.
3. Check for any stub, fake value or catch-all. Check that no rule can pass vacuously, for example on zero registers, zero cells or an empty `cites` list where the oracle has entries.
4. Check that the genuine node ids listed for rerun cover every scope the rules touch.

Save each probe as a script under `<S>/g2-gaps-spec-review/` and name it in its finding.

## Output (return as text, under 900 tokens)
Verdict (APPROVE / REVISE); findings ranked High, Medium, Low, Info, each with the spec section, the failure scenario and the probe script with its exit code; `Not verified:` line.
