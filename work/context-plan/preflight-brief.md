# Pre-flight brief, used for O6, Phase 3 and Phase 6 (controller, 2026-11-01)

You are the pre-flight reviewer for one approved plan, named in your dispatch. You are read-only: return your result as text and the controller writes it down. The plan was written before several commits that changed the code it targets:
- O1 (to 675221a9);
- O5 (to 2605b745);
- O2 (to 9a85a694);
- O3 Task 1 and B23 (0a83d2b8..0de43f2c).

Global rule: most avoidable fix rounds come from plan text that predates its code.

## Lanes running alongside yours (ruling B24, `docs/rulings/2026-10-31-context-plan.md`)

| Lane | Files it edits |
|---|---|
| O3/O4 (in order, Tasks 2-7) | `src/deploy_workflow/owner_workflow.py`, `run_pathway.py`, `model/loop.py` (stop mapping), new `replay.py`, `tests/test_owner_{state,resume,replay,guards,o3_o4_done}.py` |
| O6 | `src/deploy_workflow/prompts/` (`__init__`, `fence`, `compose`, `rules`, `rule_lists/`, `texts/`, `g8`), `tests/prompts/` |
| Phase 3 Tasks 1-3 | `src/deploy_vii/cp3_relative_value.py` (B6), `docs/reuse/manifest.json` (D12), `owners/cp3d.py`, new `context_cites.py`, `tests/test_cp3d_context.py`, `tests/test_context_cites.py`, docs |
| Phase 6 Tasks 1-8, 10 | `context.py`, `docs/templates/context-form.html`, new `owners/pins.py`, `owners/{cp2a,cp2d,cp2e,cp3c,cp3d,cp4c}.py`, `tests/test_owner_*_pins.py`, lease docs |

Serial points:
- Phase 6 Task 7 (cp3d) runs after Phase 3 Task 2;
- one writer at a time for `cases/PINS.json`, `cases/pins.py`, `cases/context/primary-full.json` and `docs/reuse/manifest.json`.

## Process

1. Read the plan named in your dispatch, and every file and line it cites, at HEAD (`git show HEAD:<path>` or the worktree; the worktree may hold other lanes' uncommitted edits, so prefer `git show HEAD:`).
2. **Stale-cite map.** For every cited `file:line` or symbol, give either "still correct" or "now at X". Name symbols that were renamed or moved, and signatures that changed: for example `_run_pathway(checked, run_dir, adapter, prompt_for, *, entries)`, `ToolLoop(...)`, `OwnerWorkflow.phase`, `RefusedBegin.missing_inputs/missing_commands`, B22 `line:N` in `live/tools.py`, and CP-1B in `ow._CORES`.
3. **Conflict table.** Write one row for each pair of tasks in the plan that share a file or an interface: what one produces against what the other consumes. Write one row for each task, saying whether its own text agrees with itself (tests against code, files created against files touched). Add one row for each overlap with the lanes above that the table missed.
4. **Fast tests (B16).** List each task's RED and gate tests. Mark any that need `RUN_PROMOTION` or take over 5 minutes, and propose fast replacements in the way O3 ruling P1 did: a pure test on hand-built inputs, or a fast walk on `cases/o2-synthetic`.
5. **Rulings to make before the first build.** Number them `<lane>-P1`…. Give each a recommendation and what it costs if wrong. Give your answer for every open question in the plan.
6. **Per-task amendments.** For each task, list the exact lines the controller should add to the brief under "Controller amendments": cites at HEAD, ruling ids and fast-test node ids.

## Return

Return 1-3k tokens of plain text in the sections above. Fast only: never set `RUN_PROMOTION=1`, never run the full suite, never use git stash. You may run read-only probes; save any probe to the scratchpad path named in your dispatch.
