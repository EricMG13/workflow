# CP-DR long gap id fix: review (stage contract; mx-precise, read-only)

Change: `claude/s5-cpdr-gapid` `6e5f6a3..0471089`, in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-aca609fa82ea6d6e5`. RED tests are in 8e83331 and the fix is in 0471089. Only `src/deploy_workflow/owners/cpdr.py` and `tests/test_connect_cpdr.py` changed. Write probes only under `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/module-dev-status-review-0981b6/work/build/keep/cpdr-gapid-review/`, and name each probe in the finding it supports.

## Inputs
| Item | File |
|---|---|
| Brief and ruling | lane `work/build/stage5/cpdr-gapid-brief.md`; `docs/rulings/2026-10-29-stage3.md` item 69 |
| Defect | lane `work/build/stage2/lows.md`, the "CP-DR gap id of 139-153 characters" line |
| Builder's report | the deviation: the second case is 153 characters, because a CP-0 `T5.<gap>.gap` fact id is itself an `Identifier` |

## Process
1. **Tightness and coverage.** Is `GAP_ID_MAX` (138) the true bound? Enumerate every id or `Identifier`-typed field `cpdr.py` builds from a gap id: fact ids, `row_id`, calculation ids, claim ids, limitation ids, consumed or upstream references, and `TDR.1` cells. Probe each at 138 and 139 characters through `compose` and `research_module`, and through settlement or `cpdr_reader` where reachable.
2. **No raise after the binding write.** Is a gap id of 139-153 characters now refused at validation (in `ENTRY_VALIDATOR` and on verifier replay), so that the run cannot wedge? Is any path left that composes before validating?
3. **RED is genuine.** Check that the final tests fail on the pre-fix `cpdr.py` for the reported cause. Compose would raise, or validation would accept the id. A missing constant alone does not count, so define `GAP_ID_MAX` and drop only the new issue rule.
4. **No frozen text moves.** Check issue order (the rule-2 position) and that existing oracles and texts are unchanged.
5. **Policy.** No stub or fake value standing in for real behaviour. No catch-all that hides a failure.

## Output (return as text, under 700 tokens)
- verdict (APPROVE / REVISE);
- findings ranked High, Medium, Low, each with the location, the evidence and the probe path, plus the probe's exit code;
- a `Not verified:` line.
