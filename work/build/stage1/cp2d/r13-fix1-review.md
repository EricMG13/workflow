**Verdict: APPROVE.** M1 and addendum 4(a) are fixed. The R1, R3 and R4 pins kill their mutants. I found two Lows and no High or Medium.

**Exit codes** (fresh `git archive 36d3746` copy, PYTHONDONTWRITEBYTECODE=1)
- Gate (cp2d, cp3c, defect_classes_selfcheck): 0, 822 passed.
- `<S>/cp2d-r13-review/probes/r3_review_mutants.py`: 1. R1, R2, R3, R4, R6 and R7 are killed. Only R5 survives, and it is the equivalent mutant.
- `<S>/cp2d-r13-review/probes/r2_conflicting_revolver_prose.py`: 0, with 0 "undisclosed" hits.
- `<S>/cp2d-r13/mutants_fix1.py`: 0, all 26 killed (M1–M19 and F1–F7).
- New probe `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cp2d-r13-fix1-review/f1_state_prose_and_mixed.py`: 0.

**Checks**
1. **Runway.** cp2d.py:555-556 returns the `OperandGap` reason, for example `Not calculable: RCF commitment is conflicting`, for both operands in both states. A plain missing `Gap` still falls through to `revolver_reason` (cp2d.py:557), so the missing path is unchanged.
2. **State-word strings.** `LIQ_STATE`, `GAP_STATE` and `FUNDING_GAP_ON_CASH_ALONE_STATE` (cp2d.py:826, 1390, 1394) follow GAP_OPERAND's `{label}, which is {state}` frame. The f1 probe ran four cases: commitment and drawings, each conflicting and not_applicable. In every case `prose.check` and `bare_figures` came back empty and nothing said "undisclosed". The diff's only removed lines are the old limitation selector. For a plain `Gap`, `revolver_state` returns None, so the missing-revolver constants and branches are byte-unchanged and the pinned and frozen tests pass.
3. **Pins.** Confirmed by the mutant runs above.
4. **Open point (Low, not a false statement).** I ran a conflicting or not_applicable commitment with drawings missing or None:
   - The runway reads `Not calculable: revolver drawings undisclosed`.
   - LIQ-01, GAP-01 and the limitation say the drawings "are undisclosed".
   - That is true, because the drawings really are missing. But it names only one of the two causes, and with a not_applicable commitment it implies a revolver exists.
   - The cause is the precedence at cp2d.py:617, `drawings = not undisclosed and _absent(o, "rcf_drawn")`. It predates this diff, and its ruling L1 assumes the commitment is known.
   - This is a ruling gap, so it goes to LEAD or the backlog, not this task.
5. **Scope.** The diff touches only cp2d.py (+41/-5) and adds tests (+93/-0). The sum-copy status, the recomputed-cell period and the balance-date fallback are untouched.

**Low L1 (wording).** cp2d.py:1390, 1394 and 826 take the label from `OPERAND_LABELS["rcf_drawn"]` = "RCF drawings" (cp2d.py:207). That gives a plural subject with a singular verb: `needs RCF drawings, which is conflicting` and `because RCF drawings is conflicting`. The cell reason built by `state_reason` (cp2d.py:225) has the same mismatch, and it dates from 7f2a9a2. This fix carries it into the claim and limitation prose. It is not a correctness issue, so it can go in the end-of-branch batch.

Not verified: `prose.issues` itself. CP-2D emits no `Fact`s, so I used `prose.check` with refs set to the known cells and gaps to the gap cells, which leaves out `issues`' fact-kind check. I also did not run the whole-repo suite, ruff, mypy, jscpd, complexipy or bandit, or check how the downstream renderer and CP-4C use the new texts. The mixed case has no test in the branch.