# Rulings rounds 6h, 6i, 7 and 8: brief (CP-2H, CP-2E, CP-3C, CP-4C, CP-1C)

The Inputs, Process, Rules and Output of `work/build/stage1/round5-brief.md` apply. This brief overrides that file's Step 0 and names the sections you apply.

## Step 0
1. Run `EnterWorktree(path=...)` for your worktree.
2. From the worktree root, run `git merge claude/module-dev-status-review-0981b6` (the lane branch). The lane now carries:
   - LEAD 8483de4 (E6) and 3674158 (the round 6 oracle batch);
   - the rulings commits for rounds 6h, 7, 6i and 8;
   - the CP-4C lease header amendment.

   Where your branch already has 8483de4 or 3674158 as a cherry-pick, the patches are identical and the merge is clean. Report any conflict, and resolve none outside your two files.
3. Re-pin any oracle sha your test asserts that moved. Use the new value only, confirmed with `shasum -a 256` against the file, and make no oracle edits. Report each full value.

## Your sections in `docs/rulings/2026-10-28-stage1.md`
| Module | Worktree | Apply |
|---|---|---|
| CP-2H | `agent-a52b5ec0919986ddb` | `# Round 7`, all of it. Re-pin `test_oracle_pins` to the 3674158 values. Every refusal and fail-closed state gets its own test that fails without its code. The first adversary review will show a killed mutant for each of the 29 refusals, so make that possible. |
| CP-2E | `agent-a219254fe68cc1c2d` | `# Round 6i`, CP-2E A4: no floor limitation on fixed-rate debt; this replaces the fail-closed raise. Also the round 5–6 review Low: add a test that pins the E8 `\b` anchors ("fixed rates" and "prefixed rate" give the neither-stem issue). It must kill `e8_no_trailing_b` and `e8_no_leading_b` in `<S>/cp2e-r6-review/mutants_review.sh`. |
| CP-3C | `agent-aa5a4817fa00cd287` | `# Round 8`, Part B (your round 5 follow-up and the T4.18 row with no currency), plus `# Round 6i`, CP-3C (no action; confirm). |
| CP-4C | `agent-a2c15c441717ec41c` | `# Round 8`, Part A: A-1 to A-5 and the LEAD notes. **A-1 is money arithmetic:** an exact largest-remainder allocation, T4E.9 summed exactly, and fail-closed state 14. It needs a hypothesis property test (conservation: allocations sum exactly to the paid amount, and each class is within one unit of its exact share in the allocation's least unit; check the ruling for the unit) and hand mutation of the allocation code from a full temporary copy, with every mutant killed or justified. A-2: the 13 states' wording. A-4: `_copy_status` accepts `conflicting`. A-3 is a CP-2G defect; don't touch CP-2G. |
| CP-1C | `cp1c-stage1` | `# Round 6h`, CP-1C (a): for a `conflicting` CP-1 value, the T1C.5 issuer deviation and flag are missing with `Not calculable: the issuer's CP-1 value is conflicting`. The value step of the 1C1 order stays, so "excluded" and "median missing" still come first. (b) is confirmed; no change. |

`<S>` is `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad`. Save your probes under `<S>/<cp>-r6h-8/`.

## Ledger line
`fix-rounds=0` for a rulings round. CP-2E and CP-1C rounds that also close a review Low still count 0.
