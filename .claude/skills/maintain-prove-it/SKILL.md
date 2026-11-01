---
name: maintain-prove-it
description: Use when a bug escaped the verifiers in Deploy Workflow (found in review, a native check, a user report or a live run). Hardens the comparison for the bug's class before the product fix.
---
# maintain-prove-it

The controller runs this skill and writes no code.

1. **Freeze the input.** The oracle preparer (not the fixer) freezes the failing input and
   its expected result under `cases/` and re-pins.
2. **Find the gap.** Run the comparisons the plan names for that surface on the frozen
   input. If they pass, classify why: surface not covered, input class missing (for example
   a soft hyphen or U+2212), key lacks the field, comparison too loose (subset instead of
   exact), or environment missing.
3. **Fix the class.** The verifier author upgrades the comparison for the whole class, not
   the instance (the `tests/defect_classes.py` pattern: one shared case every module runs).
4. **Red.** The controller confirms the upgraded comparison fails on the unfixed code.
5. **Fix.** Only then is the product fix dispatched. Done is the comparison exiting 0.
6. **Ledger.** `escaped=<bug> gap=<class> verifier=<commit>` in the lane ledger.

Never add a CLAUDE.md or AGENTS.md rule for the instance.
