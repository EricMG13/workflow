# Stage 3 fix round 1, group F1: G2 (stage contract)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python`.

You run in your own isolated worktree. Before any edit, run `git checkout -b claude/s3-fix1-g2 18dc1fa` (`claude/s3-i5`) and confirm the tip. Edit only `src/deploy_workflow/owner_rendering.py` and `tests/test_owner_rendering.py`. Never edit the lease, `cases/` or another worktree.

## Inputs
| Item | File |
|---|---|
| Ruling | `L/docs/rulings/2026-10-29-stage3.md` item 22 (F1) and item 20 |
| Findings | `L/work/build/stage3/review-arch.md` M1, L2; `L/work/build/stage3/review-precise.md` M1, L1 |
| Lease rows | `docs/OWNER-RENDERING-LEASE.md` :234, :271, :298, :338 item 7, :339 item 8, :398, :406 |
| Probes | `<S>/stage3-review/arch/p2_cp3c_scope_refused.py`; `<S>/stage3-review/precise/probe_g2_title_and_reason.py` |

## Process (test first; commit after each step)
1. **`cp3c-fp04-refinancing`.** Write the failing tests first: the scope row exists with the lease's tuple, sections, outcomes and banner; the R3.2 CR.3 figure assertions for `positive`, `gap_minimum_cash` and `gap_no_repricing`; and the item 7 extra (`funding-gap` facts each a member of the CP-2D or CP-3C head). Then add the row and drop it from `GATED_IDS`. The `cp6-fp01-committee` gated test stays.
2. **DR.6 suffix** (precise M1). Assert the exact form ruled in item 22. Each forged case in the probe must now fail the comparator.
3. **S.4 title** (item 20 Q1). Exact on the FP-04 fixture; `^Maturity wall — principal at \d{4}-\d{2}-\d{2} \(not a forecast\)$` elsewhere.
Each commit ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates (report each exit code)
- `ruff check`, `ruff format --check`, `MYPYPATH=src mypy --strict` on both files.
- `PYTHONPATH=src:tests L/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_owner_rendering.py -k fast`, plus `tests/test_chart_seam.py tests/test_chart_render_cr3.py tests/test_chart_render_dr6.py`.
- The genuine test for the new row only (the disk has room for one): select it by name and report its exit code and duration.
- Both probes rerun: `p2_cp3c_scope_refused.py` must no longer find the triple refused; `probe_g2_title_and_reason.py` must reject every forged input. Report exit codes and what each now means.
- Suppressions: `git grep noqa -- src tests | wc -l` ≤ 13; `git grep "type: ignore" -- src tests | wc -l` ≤ 5.

## Outputs (return as text, at most about 1k tokens)
Worktree path and tip SHA; what changed per finding; gate and probe exit codes; `Not verified:` line; ledger line `agent=… fix-rounds=1 gates-first-pass=…`.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged. Never use bare `git stash`. Stop any background process before you hand back.
