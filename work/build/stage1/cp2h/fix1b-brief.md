# CP-2H fix round 1, part b: LEAD round 11 rulings, applied before the re-review

These rulings belong to fix 1: the controller applies them before fix 1's re-review, so they open no new round. The re-review (mx-adversary, by finding id) covers 87f2d9d and this part together.

## Step 0
From `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a52b5ec0919986ddb`, run `git merge claude/module-dev-status-review-0981b6`. The lane now carries round 11 (d60035b). Confirm that the merge parent is the lane tip.

## Apply (`docs/rulings/2026-10-28-stage1.md`, `# Round 11`, `## CP-2H`)
1. **B2 (block rule; it amends round 7 item 8).** After a header, the line's field count (fields split on two or more spaces) decides what it is:
   - The header's field count: the line is a row.
   - 0 or 1 fields: the line ends the block.
   - 2 or more fields with any other count: the source is invalid. Report only that block's text: `Rating register not found`, `Rating scale not found` or `Trigger terms not found`. The steps keep item 8's order: scale rows, then register rows, then terms rows.
   - Cases: `<S>/cp2h-adversary/p05_block_truncation.py` (it must now see the refusal) and `spec_block_safety.py`.
2. **B3. A blank limitation is refused.** A non-null limitation with `not text.strip()` gets the pinned v10 frame (`views[<i>].limitation: empty text` / `overall.limitation: empty text`). It goes in `_limitation`, before `prose.check`. A null limitation is still allowed.
3. **B5, decided by the controller under lease :123.** Every T2R.1 status is taken from the bound Input's status, as CP-1D already is. This applies to `u_cp1` and `u_cp2g`. Kill G4 in `spec_more.py`.
4. **B6, decided by the controller under lease :107.** Add tests for the stale-issue order with several stale inputs, the `absent` wording and the `str` current path. Kill G2, G3 and C49.

No change for these, which the controller confirms as built:
- B4: the lineage of a known first year lists all three rows, and the positive `T2R.6.t02.down_first` pins it.
- round11 Q7: tightest and mixed years follow formula order in year order.

## Rules
- Files: `src/deploy_workflow/owners/cp2h.py` and `tests/test_method_cp2h.py`.
- Test-first, with each test seen red for the reported cause where code changes. No stub, fake value or catch-all. No new wording.
- Gates: the same as fix 1 (`work/build/stage1/cp2h/fix1-brief.md`).
- Mutants only from a full temporary copy, with `PYTHONDONTWRITEBYTECODE=1`. Rerun `runner.py` with `spec_refusals.py` (29 of 29), `spec_other.py`, `spec_more.py` and `spec_fix1_retarget.py`, and show that each ruling's revert is killed.
- `<S>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`.

## Report (as text)
- The commit.
- Each ruling and the test that covers it.
- Runner and probe exit codes, with survivors and the reason each survives.
- The gates.
- Stage 2 notes (methods/cp2h.md).
- A `Not verified:` line.
- The ledger line `agent=general-purpose(opus) fix-rounds=1 gates-first-pass=<y|n>`.
