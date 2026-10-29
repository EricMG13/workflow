# Stage 3 chart oracles: independent review (stage contract; halves A and B)

Read-only. Never edit files. You prepared none of these oracles.

`R` = `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s3-oracles`, branch `claude/s3-oracles` at 6288196. That is groups A and B merged on release ab9777f, with `cases/PINS.json` regenerated. Diff: `git diff ab9777f..6288196`. `L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. `D` = `/Users/ericguei/Documents/DEPLOY VII/design/reference/` (read-only). `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

## Inputs
| Item | File |
|---|---|
| Preparer contract | `L/work/build/stage3/oracle-brief.md` |
| Rulings (items 3, 5, 6) | `L/docs/rulings/2026-10-29-stage3.md` |
| Preparer reports | `L/work/build/stage3/orc-a-report.md` (A), `L/work/build/stage3/orc-b-report.md` (B) |
| Figure list and user rulings Q-C1, Q-C2, Q-C10, Q-C11 | `L/work/build/stage3/questions.md` |
| Pattern | `R/docs/CP1-CHART-SLICE.md`, `R/cases/charts/expected.json` |
| Code the wiring must meet the oracle with | `R/src/deploy_vii/report_view.py` (`_Spec`, `_STRIP_FIGURES`, `ChartSpec`), `R/src/deploy_vii/bindings/` (`validate_bindings`), the producers in `R/src/deploy_vii` |

## Halves
- **A:** `cases/charts/builder/build_a.py`, `s5`, `rv3`, `cr1`, `s4fp04`, and the `cases/pins.py` patterns.
- **B:** `cases/charts/builder/build_b.py`, `cr2`, `cr3`, `dr2`, `dr345`, `dr6`, and the moves in `cases/cp3c-owner` and `cases/cp4c-owner` (through their builders) and in `docs/CP3C-OWNER-LEASE.md`.

## Check, citing file:line
1. **Values.** Every chart value equals a settled fact in the module oracle it cites. The builder reads values and types none by hand. Run the builder from a fresh copy and diff the output (under 60 s). Spot-check at least three points per figure against the module oracle by hand.
2. **Gaps.** Missing or `not_meaningful` facts are gaps with their G# rule, never 0. Adversarial cases cover each gap the module oracle has.
3. **Form and owner.** These follow the approved page, then the brief, then inference, and each inference is flagged. Pack numbers are never used.
4. **Rulings.** Each ruling in items 3, 5 and 6 is applied as written.
5. **Moves.** No frozen oracle moves except as rulings allow (Q-C1, Q-C2 move, item 6.7 prose). Each move goes through its builder, and the pins are regenerated.
6. **Feasibility.** The `builder_targets` can be met by a builder in `src/` and `tests/` without changing `cases/`. Name every target the current code cannot reach without a shared-interface or `src/deploy_vii` change beyond the chart seam (for example new `ChartKind` values, two-panel figures, the T3D.1 binding move). The chart seam itself is in scope for the wiring.
7. The oracles need no stub or fake value standing in for real behaviour.

Save each probe as a script under `<S>/oracle-review-<half>/` and name it in the finding.

## Output
APPROVE or REVISE. Findings are High, Medium, Low or Info, each with file:line, the failure scenario and the fix. Only High and Medium block. Return as text, at most about 1.5k tokens.
