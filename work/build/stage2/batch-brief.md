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

## CP-1D folded in (user, 2026-10-28)
CP-1D joins the batch at 8a5d3d9. Before CP-2G, the first builder fixes CP-1D's two Mediums, test-first. The review is `work/build/stage2/cp1d/review.md`. The probes are in `<S>/cp1d-s2-review/`.
- **M1:** the view's `shown` is the cell spelling (`fact_spelling(fact, None)[2]`), not `spelled(fact)`.
  - Add a fast test that runs `tests/cp1d_runs.py` `fig_bindings` over a fast settled store.
  - `p11_driver_fig_bindings.py` and `p10_view_shown_vs_oracle.py` must exit 0.
- **M2:** the FP02 `restated-leverage` `_Spec` title and the T1D.6 binding and tab labels must equal `expected.json` FP02.
  - Add a fast test that compares `report_view.build` over the fast module with the oracle FP02 titles and tab labels.
  - `p5_fp02_render_vs_oracle.py` must exit 0.
- **Also:** move `OWNER_SPECS["CP-1D"]` after CP-MODEL (L4). Record round 5 item 12's `1.5-Q` and `1.5-\nnd` readings in `methods/cp1d.md`.
- CP-1D's other Lows go to the end batch.

## Branch and order
- Branch `claude/s2-batch` in worktree `../s2-batch`. One builder runs at a time; each one commits on top of the last.
- Build order follows the dependencies (plan-draft §2):
  1. CP-2G: ships `cp2g_reader`, consumes CP-2A and CP-1D.
  2. CP-1C: appends to `_RELATIVE_VALUE`.
  3. CP-3C: consumes `cp2d_reader`.
  4. CP-2H: consumes `cp2g_reader`.
  5. CP-4C: consumes `cp2g_reader`, CP-4 and CP-2A; selects into its own `Cp2gHead` (Q6).
- Step 0 for each builder: the tree is clean and HEAD equals the tip named in your dispatch.

## Builder (user, 2026-10-28: "use opus for batch connection")
Each batch builder is an Opus implementer (`general-purpose`, `model: opus`), one fresh agent per module, run in sequence on the batch branch. Commits end `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Parallel connectors (user, 2026-10-28: "use multiple agents for connectors")
- CP-1C builds on `claude/s2-batch`. CP-3C, CP-2H and CP-4C build in parallel, each on its own branch `claude/s2b-<cp>` in worktree `../s2b-<cp>`, cut at batch 8d5d404, which holds CP-2G, CP-2D, CP-4 and CP-2A.
- Parallel builders do not touch `docs/reuse/manifest.json`. The integration pass adds and chains the D12 records when it merges.
- Registration-order assertions use a base prefix plus "after its dependencies", so parallel appends merge cleanly.
- An integration pass then merges the three onto `claude/s2-batch`. The stage-level class test comes last.

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
