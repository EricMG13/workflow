# Stage 3 G2 continuation (stage contract)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6` (read-only). `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

You run in your own isolated worktree. Before any edit:
1. `git checkout -b claude/s3-g2c c43b681`, the integrated Stage 3 tip.
2. `git merge --no-ff claude/s3-g2rev3`, the frozen G2 rev 3 lease, d737d8f.
3. `git merge --no-ff claude/s3-g2`, the earlier G2 build, 234dfae.
4. `git apply <S>/g2-uncommitted.patch`, the earlier builder's uncommitted payload-path fix and indexed lookups. Commit it on its own.

Write only inside your own worktree. Python: `L/.venv/bin/python`.

You did not write the G2 lease, and you never edit it or `cases/`. **The disk is nearly full.** Run only the fast tests, never a genuine owner run, until the controller says space is free. The genuine runs go in your report as deferred commands.

## Inputs
| Item | File |
|---|---|
| Lease (body, then rev 1, rev 2 and rev 3 override in that order) | `docs/OWNER-RENDERING-LEASE.md` |
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` items 2, 4, 7, 15 and 16 |
| The earlier builder's report | `L/work/build/stage3/g2-report.md` |
| The original G2 brief (gates still apply) | `L/work/build/stage3/g2-brief.md` |

## Process
1. **Rev 3.** Bring the code and tests to rev 3.
   - The `cp1-model` sections are `model-chart-strip`, `capital-structure` and `financials-credit-metrics`.
   - Each assigned block's `figures` equal its frozen chart oracle's render expectation, or `()`. The comparison is field by field, under the rev 3 rules for S.1-S.4, refs and fact ids.
   - Test first: each changed expectation fails before you change the code.
2. Review the earlier builder's committed and patched code against the lease. Its genuine path never passed, so treat it as unverified.
3. Make the fast tests pass: refusals, read-only checks, determinism, the scope table against the oracles and drivers, and the figure rule on fixtures built from the oracles.
4. Commit after each step. Each commit ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Gates (report each exit code)
- `ruff check`, `ruff format --check`, `MYPYPATH=src mypy --strict` on both G2 files.
- The fast G2 tests (the earlier builder's `-k fast` selection, plus any you add), `tests/test_chart_seam.py`, `tests/test_legal_render.py`.
- Suppressions: `git grep noqa -- src tests | wc -l` ≤ 13; `git grep "type: ignore" -- src tests | wc -l` ≤ 5.
- **Deferred:** the `cp1-model` and the 16 other scopes' genuine tests. List their exact commands.

## Outputs (report as text, at most about 1.5k tokens)
- Your worktree path and tip SHA; what changed for rev 3; fast tests and counts; deferred commands; questions; `Not verified:` line; ledger line.

Rules: no stub or fake value standing in for real behaviour; no catch-all that hides a failure unless documented and logged. A test-only cache of genuine runs must be keyed on content, so that it can never hide a changed store. Stop any background process before you hand back.
