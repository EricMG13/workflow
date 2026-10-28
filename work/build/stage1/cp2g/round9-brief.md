# CP-2G round 9 (rulings; after the fix 1+2 re-review APPROVE)

The Inputs, Rules and Output of `work/build/stage1/round5-brief.md` apply. Review afterwards: scoped mx-feature. Re-review of fixes 1-2: `work/build/stage1/cp2g/fix1-2-review.md` (APPROVE).

## Step 0
From `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a4377a7580e8e70db`, run `git merge claude/module-dev-status-review-0981b6` (lane: rounds 9 and 10). Report conflicts; resolve none outside your two files (a `docs/CP4C-OWNER-LEASE.md` header conflict takes the lane's version). Round 10 puts CP-2G outside the sign class: no change for it.

## Apply (`docs/rulings/2026-10-28-stage1.md`, `# Round 9`, `## CP-2G`, plus the two CP-2G bullets that follow the CP-2A section)
- **M2 wording.** `CP-2G: CP-1 <metric> must be USD MILLIONS at scale 1000000, not <currency> <unit> at scale <scale>`; `<metric>` is the OPERAND_METRIC name; a currency of None prints `None`. Re-check `F/q02_m2_book_units.py` in `<S>/cp2g-fix-review/` against it.
- **L1.** Tests on the five cells the ruling names (no code change expected; if a test fails, report it).
- **L2.** The new `T2H.2.cp1d` wording.
- **L3.** The all-not-calculable branch.
- **Info.** Catch only `decimal.Inexact` around each `_EXACT` block and raise `ValueError("CP-2G: <operation> needs more than 38 significant digits")`, `<operation>` naming the operation.
- **`T2H.1.u_cp1d.basis`.** The CP-2A row's period rule and fallback.
- **T2H.9 gap texts.** Spell each `{ref|unit}` as rendered in `gap`, `why_it_matters`, `affected_analysis`, `action` and the `Gap (<severity>): …` own line.

`<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Probes under `<S>/cp2g-r9/`. Mutants only from a full temporary copy, with `PYTHONDONTWRITEBYTECODE=1` (the re-review's I3: set it in `p06_mutants.py`, `p06b_mutants_followup.py` and `p_fix2_citation_mutants.py` before reusing them). Show each ruling's revert is killed.

## Ledger line
`agent=general-purpose(opus) fix-rounds=0 gates-first-pass=<y|n>`
