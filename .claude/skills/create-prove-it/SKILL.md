---
name: create-prove-it
description: Use before building a new feature, surface or refactor in Deploy Workflow, or when a plan or lease Answer Key row has no runnable comparison. Maps surfaces, picks answer keys and has a verifier written for them.
---
# create-prove-it

The controller runs this skill and writes no code. Agents: oracle preparer, verifier author
and builder are three different agents (CLAUDE.md, Verifier gate).

1. **Surfaces.** List the ones the change touches; add new ones.
   | Surface | Reach offline | Comparison today |
   |---|---|---|
   | Owner oracle outputs | module tests vs `cases/<slug>-owner/expected.json` | `python3 -I cases/pins.py --check`; builder double rebuild |
   | Public goldens | `cases/goldens/<case>/` | `python3 -I cases/goldens/check.py cases/goldens/<case>/` |
   | Chart blocks | `report_view.build` + `render` | `tests/test_chart_render_*.py` vs `cases/charts/*-expected.json` |
   | CLI JSON-lines | `python -m deploy_workflow.financial_workflow` (argv: docs/RUN-GUIDE.md) | none |
   | Sealed receipt | `verify_financial_slice_receipt` | tamper tests |
   | Rendered HTML | `render_financial_slice` -> `report.html`, `model.html`, `calculation.json` | none automated; native DOM checks are manual |
2. **Reach.** Run each surface once on a frozen case. Record argv, exit code and wall time.
   No provider or live calls.
3. **Answer keys.** Present `| Method | Answer key | What it catches | Setup cost |`, in this
   order of preference:
   - an existing pinned oracle;
   - for a refactor that must not change output: the output of the pre-refactor commit,
     frozen by the oracle preparer (never `src/deploy_vii` run beside its own wrapper: it is
     on the call path and not qualified, AGENTS.md);
   - a visible-text check of a rendered section against the plan's table rows, following
     the visible-text rules in `cases/goldens/check.py` (reuse them; do not copy them);
   - evaluator judgment, only for rows no script decides: a fresh agent, told nothing about
     the build, inspects the surface; the controller drives the built-in browser for it.
4. **Stop for the owner's approval of the table.**
5. **Key.** The oracle preparer (`mx-feature`) writes any new key under `cases/`, adds it to
   `cases/pins.py` PATTERNS and re-pins, in a commit that touches no `src/` or `tests/` file.
   `mx-precise` reviews the key without reading the build.
6. **Comparison.** The verifier author (`mx-feature`, not the builder) writes
   `cases/prove/<surface>.py` (stdlib where it can; one failure per line:
   `<surface>: <key path>: expected <x>, got <y>`) and, when the check is reusable, a
   `.claude/skills/prove-<surface>/SKILL.md` naming when to run it and its exact argv.
   `mx-precise` reviews it.
7. **Smoke.** A planter agent (`mx-feature`) plants one bug the comparison must catch, uncommitted; the controller confirms exit 1; the planter reverts it.
8. **Record.** Fill the plan's Comparison column with the argv. A comparison over 5 minutes
   goes into `HEAVY` in `cases/prove/affected_tests.py`.

Failure lines go into the builder's next fix brief; the key file is never pasted there.
