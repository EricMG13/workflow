---
name: audit-prove-it
description: Use at each stage close or after a comparison changes in Deploy Workflow. Plants one realistic bug and checks the plan's comparisons catch it.
---
# audit-prove-it

The controller runs this skill. Mutations are never committed or pushed.

1. **Target.** A `src/` file changed since the last audit (lane ledger); prefer money,
   ordering and receipt code.
2. **Plant.** A planter agent (`mx-feature`) in its own worktree edits ONE site with a
   realistic mutation: off-by-one period, sign or parentheses flip, Decimal to float, zero
   and missing swapped, a dropped submission or render field, an inverted refusal or
   readiness condition, a skipped hash check. It does not commit. It reports the file, line
   and mutation to the controller only.
3. **Run.** In that worktree the controller runs, unchanged, the comparisons the plans name
   for that file's surfaces and the affected tests
   (`python3 -I cases/prove/affected_tests.py --tier fast <base> HEAD`, with the working
   tree's change committed to a throwaway local commit only if the script needs one).
   Judgment rows only: a fresh evaluator agent, told nothing about the mutation, inspects
   the surface.
4. **Score.** Caught means a comparison exits 1 on the affected surface. Then discard the
   worktree and confirm no branch or commit with the mutation remains.
5. **Missed** goes to `/maintain-prove-it` with the mutation as the escaped bug.
6. **Ledger.** `audit target=<file> mutation=<kind> caught=y|n comparison=<argv>`.

`mutmut` on sensitive files (global rules §3) stays; this is the end-to-end complement.
