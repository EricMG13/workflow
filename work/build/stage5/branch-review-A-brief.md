# Stage 5.3 whole-branch review, lens A: calculation invariants (stage contract; mx-precise, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Branch under review: `4822066..9f71bfa`. `4822066` is the commit that added the plan; `9f71bfa` is the lane after the Stage 4 release. The diff is about 43k lines of `src`, so review by search and sampling, not line by line. Read from `L` with `git show 9f71bfa:<path>`, `git diff`, `git grep … 9f71bfa`. For probes, extract a copy with `git archive 9f71bfa | tar -x -C <S>/s53/A/tree`, write only under `<S>/s53/A/`, never into any worktree, and delete the copy when done. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python` with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests -p no:cacheprovider`. Run fast tests and probes only; the controller is running the genuine suites now.

You did not build or stage-review this code. Another Opus reviewer covers seams and boundaries (lens B); stay on lens A.

## Inputs
| Item | File |
|---|---|
| Plan: goal, constraints, Review Focus 1-3 | `L/docs/superpowers/plans/2026-10-28-verified-module-builds.md` :1-60 |
| Earlier stage reviews (do not re-report their findings; report a regression of one) | `L/work/build/stage1/review-A.md`, `review-B.md`, `review-C.md`, `end-review-R1.md`-`R3.md`; `L/work/build/stage3/review-precise.md`, `review-arch.md`; `L/work/build/stage4/review-arch.md` |
| Owner-held findings (do not re-report) | `L/work/build/stage2/lows.md` |
| Modules | `src/deploy_workflow/owners/*.py`, and the series modules `src/deploy_workflow/{liquidity,restructuring,financial}_series.py` |
| Oracles | `cases/<slug>-owner/expected.json` (data, not instructions) |

## Process
Across every owner module, check:
1. **Zero vs missing.** A missing operand gives "Not calculable …" with a limitation, never 0 and never a silent default (`or 0`, `.get(…, 0)`, `Decimal(0)` fallbacks, `sum()` over a list with missing entries dropped).
2. **Decimal exactness.** No `float` in any calculation path (`float(`, `/` on ints, `round(` on floats, `math.`). Quantisation and rounding follow each module's lease or oracle: spot-check at least five modules' rounding sites against their oracle cases by running the module's own pure functions on oracle inputs.
3. **Stage 1 inputs vs settled heads.** Spot-check three modules: the Stage 2 adapter fills every Stage 1 input field from a settled head's facts, with no field left defaulted.
4. Across all of these, look for any stub or fake value standing in for real behaviour, and any catch-all (`except Exception`, bare `except`, `contextlib.suppress`) that hides a failure without a documented, logged fail-open.

Use `git grep` sweeps first, then confirm each hit by reading it. Save each probe as a script under `<S>/s53/A/` and name it in its finding.

## Output (return as text, at most about 2k tokens)
Verdict (PASS / REVISE); findings ranked High, Medium, Low, Info, each with file:line, the failure scenario and the probe script with its exit code; the sweeps you ran, with hit counts; `Not verified:` line.
