# Stage 2 batch build (stage contract)

Ruling (user, 2026-10-28): "no more per module work from stage 2 onwards". The five unconnected modules are connected in one batch on one branch and get one whole-stage review. There are no per-module reviews and no per-module fix rounds.

## Inputs
| Item | File | Why |
|---|---|---|
| Per-module contract | `work/build/stage2/brief.md` (Process 0-7, Gates, Outputs, "Rulings that bind every module", Source quotes) | what "connected" means. Everything in it applies, except the review routing |
| Your row | `work/build/stage2/plan-draft.md` §4 | files, symbols, D3 |
| Rulings | `docs/rulings/2026-10-28-stage2.md` rounds 1-5, `work/build/stage2/questions.md` | Q6 readers, Q-SQ1, judgements |
| Backlog | `work/build/stage2-backlog.md`, your module's rows | applied first |
| Shared helpers | `tests/defect_classes.py` (`assert_hostile_refused`, `model_text_failures`, `path_matches`) | the stage-level class test |

## Branch and order
- Branch `claude/s2-batch` in worktree `../s2-batch`. One builder runs at a time; each one commits on top of the last.
- Build order follows the dependencies (plan-draft §2):
  1. CP-2G: ships `cp2g_reader`, consumes CP-2A and CP-1D.
  2. CP-1C: appends to `_RELATIVE_VALUE`.
  3. CP-3C: consumes `cp2d_reader`.
  4. CP-2H: consumes `cp2g_reader`.
  5. CP-4C: consumes `cp2g_reader`, CP-4 and CP-2A; selects into its own `Cp2gHead` (Q6).
- Step 0 for each builder: the tree is clean and HEAD equals the tip named in your dispatch.

## Process differences from brief.md
- There is no review after your module. Write your report as text; the controller saves it to `work/build/stage2/batch/<cp>-report.md`.
- Source quotes rule (b): never read a figure from a model quote. CP-4C `source_row` complies (Q-SQ1). Model-typed judgements are outside the rule.
- Never edit another module's files except append-only registration rows.
- If you find a defect in a merged module, report it. Do not fix it.

## Last step (the final builder)
Add `tests/test_stage2_classes.py`, one stage-level class test over every connected owner module, so that no module's `test_connect_<cp>.py` has to be edited for it.
- `assert_hostile_refused` runs over each module's `SCHEMAS`.
- `model_text_failures` runs over each module's oracle positive payload, with a `fresh()` `ReviewRun` that wraps the module's real `submit` path. Each module's `verbatim` set is listed with its sink, as `CP0_VERBATIM` is.
- Keep each file under about 60 s. Split by module group if needed.

## Gates
These are the brief.md gates for your module. The final builder also runs the stage-level test and the fast set over all `test_connect_*` and `test_method_*` files.

## Outputs
The brief.md report items, plus the D12 manifest record for each reused file you touch.
