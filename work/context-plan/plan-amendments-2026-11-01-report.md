# Plan amendments 2026-11-01: report

Docs-only; six plan files edited in place, each change tagged `(amended 2026-11-01, ...)`. None of the six has a dated amendments list, so no list line was added.

- A1 `part-b-o5.md`: error-classification bullet (:75) gains `SentChargeUsage` (usage-bearing error or malformed 200 settles from usage, `computed`/`billed`; None input/output count = unknown), `SentChargeKnown` narrowed to 4xx with no usage; classification RED (:83) gains usage and None-count cases; Task 6 "Failures split" gains `sent_usage` (settle from usage, write record, stop; no retry, no repair). Sources: ledger `.superpowers/sdd/2026-10-31-part-b-o5/progress.md:5,8,11` (partial usage = unknown at :11); `src/deploy_workflow/model/providers.py:101-121`, `:339-347`, `:545-558`.
- A2 `phase-2-identity-periods.md`: Task 4 gains the B19 step before the RED list and two named REDs (`test_nonzero_delta_pair_not_flat`, `test_present_fy2024_basis_not_absent`); cites `earnings_workflow.py:1678,1688,1764,1789,1936-1937`, `owners/cp1b.py:122`, rulings :122-136. Test names are mine (the brief gives the behaviour only).
- A3 `phase-3-market-evidence.md`: Design 3 citation rule restated per B20/B20a/B20b; gap texts and `Gap (<severity>): ` rendering; ruled decision 3 restated (every colliding row dropped). Texts checked against `cases/cp3-context-owner/expected.json:2610-2611, 2669-2670`; rulings :129-144.
- A4 `phase-5-attachments-modes.md`: Task 3 RED "ten Task 0 cases" replaced by the 15 ids from `cases/context-attachments-owner/expected.json:25` (PINS.json:15), with the `legal-draft-missing` text from :13 (case at :193). No other "ten cases" text exists.
- A5 `phase-6-pinned-assumptions.md`: Task 5 (CP-2E) row adds `T2F.9.r08.text` (`cases/pins-context-owner/expected.json:807-811`, text :17); Task 7 (CP-3D) row adds `T3E.9.r12.text` (:8206-8210, text :20).
- A6 `phase-8-periods-currency.md`: Done-when 1 "no ... `2025`" replaced by "no stale unshifted literal", with the derivation rule from `cases/periods-currency-owner/builder/build.py:605-613, 631-657` and the oracle note `expected.json:58537`; list at `expected.json:207`; checked for R1/R2/R3/R6 (`build.py:783`).

Deviations: A2 notes that the B19 step edits `earnings_workflow.py`, which Task 4 previously said was NOT edited (a narrow stated exception, owner-path prose only). The brief's "ledger Task 2 rulings (01:30, 01:37 UTC)" were confirmed at progress.md lines 5 and 8.

Checks: cited lines read at HEAD with sed/grep. `git diff --stat` also shows other agents' files (tests/model/*, build-progress.md); they are not staged or committed.

Not verified: no gate or test ran (docs only); the new RED test names in A2 and the A4 split of cases between `submit_review` and unit tests are not exercised or checked against any code; the A3 gap texts for CP-3 were checked against expected.json strings only, not against the builder.
