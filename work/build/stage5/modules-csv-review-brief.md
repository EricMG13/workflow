# MODULES.csv update: overclaim review (stage contract; mx-precise, read-only)

`L` = the lane `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6`. Change under review: `claude/s5-modules-csv` `02f7f94..7c1a702`. Only `docs/MODULES.csv` changed: 16 rows, 7 cells each. Read it with `git diff 02f7f94 7c1a702 -- docs/MODULES.csv` and `git show 7c1a702:docs/MODULES.csv` from `L`. Write probes only under `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/modules-csv-review/`. Run no tests.

## Inputs
| Item | File |
|---|---|
| Ruling and brief | `L/docs/rulings/2026-10-29-stage3.md` item 65; `L/work/build/stage5/modules-csv-brief.md` |
| Preparer's report | `L/work/build/stage5/modules-csv-report.md` |
| Evidence | `L/work/build/ledger.md`, `L/work/build/stage5/dom-proof.md`, `L/work/build/stage2/lows.md`, the leases' MODULES.csv sections (`docs/*-OWNER-LEASE.md`), `AGENTS.md` completion rule |

## Process
1. For every changed cell that says `verified`, find the ledger line it cites. Check four things:
   - the run passed (exit 0, or the failures named were later fixed and rerun green);
   - it ran on the final code, or on code a ruling accepts as equivalent (items 38, 49, the 05:20 Stage 5.1 note);
   - the cited test actually exercises what the column claims: tool execution, validated output, downstream consumption by a named consumer, rendering;
   - the time matches.

   Flag any cell that claims more than its evidence. Typical overclaims:
   - "verified" consumption where only the producer ran;
   - rendering verified without that scope's G2 case and 5.2 row;
   - a run that predates a later change to that owner's code.
2. Where a lease fixes the row text, check that the row follows it or departs only where the evidence requires.
3. Check the preparer's judgement calls:
   - CP-4C is marked verified with the never-wedges test unfinished;
   - CP-1D consumption is verified through CP-2G while `test_owner_cp1d.py` still asserts the own-run open status;
   - CP-OS rendering with the `shell_skip_link` fix (the CP-OS oracle says it resolves since 0d, 41a8fdb).

   Say whether each is honest as worded.
4. Rows outside the 16 are byte for byte unchanged. The CSV is valid (11 columns).

## Output (return as text, under 900 tokens)
- verdict (APPROVE / REVISE);
- findings ranked High, Medium, Low, each with the (module, column) cell, the evidence, and the wording that would be honest;
- a `Not verified:` line.
