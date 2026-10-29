# Stage 3 end check (stage contract; Fable mx-architect, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. The code under review is `claude/s3-i5` 18dc1fa, checked out at `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/s3-i4` (read it there; never write there). Base: the Stage 2 release, `697fe8a`. `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Python: `L/.venv/bin/python`.

You write no code. A separate `mx-precise` reviews the builder branches line by line; you check the pathways end to end.

## Inputs
| Item | File |
|---|---|
| Stage 3 scope and review focus 5 | `L/docs/superpowers/plans/2026-10-28-verified-module-builds.md` :40-46, :138-144 |
| Rulings | `L/docs/rulings/2026-10-29-stage3.md` items 1-20 |
| Lease | `docs/OWNER-RENDERING-LEASE.md` (body, then rev 1-3) |
| Chart oracles | `cases/charts/*-expected.json`; inventory `L/work/build/stage3/charts-inventory.md` |
| Build reports | `L/work/build/stage3/w1-report.md`, `w2a`-`w2d-report.md`, `int-report.md`, `g2c-report.md`, `cpos-report.md`, `czr-report.md`, `legal-move-report.md` |
| Gate runs (running now) | `<S>/i5/A.status`, `<S>/i5/B.status`, logs `<S>/i5/*.log` |

## Process
1. For each of the six pathways, list its assigned blocks (core `_spec_of`/pathway tables) and confirm each renders from settled facts (`store.head_module(head)`), through G2's `DELIVERY_SCOPES`, with the figures its frozen chart oracle names, or `()`.
2. Flag any assigned block with no producer, no scope row, no test, or a figure no frozen oracle backs.
3. Check that no stub, fake value or catch-all hides a failure (a documented, logged fail-open is allowed).
4. Read the gate status files last. Report each step's state; a step still running is "pending", not passed.

Save each probe you run as a script in `<S>/stage3-review/arch/` and name it in the finding.

## Output (return as text, at most about 2k tokens)
Verdict (PASS / REVISE); findings ranked High, Medium, Low, Info, each with file:line, failure scenario, probe script; a pathway × block table (one line per pathway, gaps only); `Not verified:` line.
