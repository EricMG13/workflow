# Plan amendments batch (controller brief, 2026-11-01)

These are docs-only edits to six plan files, bringing them in line with rulings and frozen oracles that postdate them. The authorities, in order:
1. `docs/rulings/2026-10-31-context-plan.md`
2. the frozen oracle case named in each item (`cases/<case>/`; frozen means pinned in `cases/PINS.json`)
3. the SDD ledger lines quoted below

Where a plan's text and the oracle disagree, the oracle wins. If the disagreement needs a decision the oracle does not settle, stop and report NEEDS_CONTEXT.

Each change is made in place and tagged `(amended 2026-11-01, <ruling or oracle>)`. Where a plan has a dated amendments list, add one line to it as well. Never rewrite an earlier dated amendment line. Cite path:line for every value you copy. Never edit `src/`, `tests/`, `cases/`, `docs/rulings/` or any other plan.

| # | Plan | Where | Change |
|---|---|---|---|
| A1 | `docs/superpowers/plans/2026-10-31-part-b-o5.md` | :75 (error classification), :83 (classification REDs), Task 6 "Failures split" (~:171) | Add `SentChargeUsage`: an error reply (any status, or a 200 refused as malformed) that carries provider usage is `SentChargeUsage` and is settled from that usage (Task 3 charge; `computed`, or `billed` when billed). `SentChargeKnown` is a 4xx with no usage and settles `0`. A `Usage` with an input or output count of `None` is unknown, never a partial charge. Task 6: `sent_usage` settles from usage, writes the record, then stops the run (no retry, no repair). Source: ledger `.superpowers/sdd/2026-10-31-part-b-o5/progress.md`, the Task 2 rulings (01:30, 01:37 UTC), and the code at `src/deploy_workflow/model/providers.py` (`ErrorKind`, `ProviderError.__post_init__`). |
| A2 | `docs/superpowers/plans/2026-10-31-phase-2-identity-periods.md` | Task 4 (:218 onward) | Add the B19 step (rulings :122-136). Before Task 4 widens the pairs `owners/cp1b.py` `supported()` accepts, generalise the CP-1B composer prose (`earnings_workflow.py`, the split composer and `_own_limits(owner=)`) so the head, claims and limits are true for every accepted pair. RED: a pair whose deltas are non-zero must not render "is flat", and a pair whose FY2024 basis is present must not render "Requested FY2024 comparison basis is absent". Task 4 lands only with that RED. |
| A3 | `docs/superpowers/plans/2026-10-31-phase-3-market-evidence.md` | Design 3 (:65-67), ruled decision 3 (:274) | Restate the citation rule per B20, B20a and B20b (rulings, from the B20 entry through :144). Cite a figure by key/value when its member is alone on its line. Otherwise quote from the object's `{` through the figure on one unique line. Otherwise drop the row. Drop every colliding row, with gap text `context quote row <n> for facility <id> cannot be cited as one unique span; not used` (or `context deal terms row <n> …`). Drop gaps render as `Gap (<severity>): …`, like the Design 5 gaps. Check the exact texts against `cases/cp3-context-owner/expected.json`. |
| A4 | `docs/superpowers/plans/2026-10-31-phase-5-attachments-modes.md` | Task 3 (:134 onward), plus any "ten cases" text | Replace "ten cases" with the case ids in `cases/context-attachments-owner/expected.json`; the ledger counts 15. That set includes `legal-draft-missing` (with its gap) using the draft-missing text frozen there. List the ids. |
| A5 | `docs/superpowers/plans/2026-10-31-phase-6-pinned-assumptions.md` | Task 5 and Task 7 RED lists | The pinned rows also include `T2F.9.r08.text` (CP-2E) and `T3E.9.r12.text` (CP-3D), as frozen in `cases/pins-context-owner/` (cite the file:line). |
| A6 | `docs/superpowers/plans/2026-10-31-phase-8-periods-currency.md` | Done-when 1 (:378 onward) | Replace any "no 2025" wording with "no stale unshifted literal". The stale list is derived from `cases/periods-currency-owner/` (builder and expected), not hand-listed. State the derivation rule as the oracle's builder applies it, citing path:line. |

Checks: `git diff --stat` shows only the six plan files. Every path:line you cite exists at HEAD; check it with `sed -n`.

Commit: `git commit -m "docs(plans): amendments for SentChargeUsage, B19, B20-B20b and frozen-oracle counts" -- <the six paths>`, with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never `git add -A`.

Report to `work/context-plan/plan-amendments-2026-11-01-report.md`: per item A1-A6, the lines changed and the source cited, any deviations, and a last line `Not verified:`. Reply with only: Status; commit; concerns; report path (under 8 lines).
