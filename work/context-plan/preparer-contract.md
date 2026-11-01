# Oracle preparer contract (context plan build, every Task 0)

Work from `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/tool-use-m365-copilot-research-8ff28f`
on branch `claude/context-plan-build`. You are the **preparer** (B2, AGENTS.md "Module builds"): you are not
the builder of the phase's later tasks and you never review your own case.

1. Read your Task 0 brief first; it is your requirements. Read the plan only where the brief points, and the
   rulings in `docs/rulings/2026-10-31-context-plan.md` it cites.
2. Write only under the brief's new case directory (`cases/<case>/`), including `builder/build.py` (stdlib
   only; never imports `deploy_vii` unless the brief says so). The builder writes every case file
   deterministically; a scratch double rebuild must be byte-identical (`diff -r`).
3. Expected values are hand-derived from the brief, the rulings and the frozen upstream oracles the brief
   names, never from running the code the phase will build. Upstream values are copied from the frozen files
   and cited (path:line).
4. Never edit `cases/PINS.json`, `cases/pins.py`, any existing case, `src/`, `tests/` or `docs/`. Pins are
   written at freeze, after review. If your case matches an existing PINS glob, `cases/pins.py --check` will
   report its files as unpinned until the freeze: expected; say so in the report.
5. Run the product validators the brief names (and any that exist today for the shapes you write) and report
   each exit code; a validator that cannot judge the new behaviour yet is reported as such, not skipped
   silently. Fast checks only (B16): each command under 5 minutes, no pytest files, no `RUN_PROMOTION`.
6. Never: a stub or fake value standing in for real data; a catch-all that hides a failure; a network call;
   reading a credential or provider env var; editing DEPLOY VII.
7. Commit only your paths: `git add <paths>` then `git commit -m "<message from brief or
   'test(oracle): <case>, prepared (Task 0, preparer)'>" -- <paths>`, message ending with
   `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never `git add -A`, `.` or `-a`; other agents
   work in the tree. If `index.lock` exists, wait and retry. Do not push, merge or switch branches.
8. If the brief and the frozen files disagree, or a value cannot be derived without a decision, stop and
   report NEEDS_CONTEXT with specifics.
9. Write the full report to the report path in your dispatch: files, how each expected value was derived
   (case by case), validator and rebuild commands with exit codes, deviations from the brief, concerns, and a
   last line `Not verified:`.
10. Reply with ONLY (under 12 lines): Status; commit; exit codes; concerns; report path.
11. If resumed with review findings: fix, rebuild twice, re-run the reviewer's probes, append a fix section to
    the report, reply with the same short contract.
