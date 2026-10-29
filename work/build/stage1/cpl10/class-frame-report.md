CP-L10 frame adjustment is done. All gates pass and all six mutants are killed. Under the controller ruling the module now uses one empty-text spelling, `<path>: empty`.

**Commit**: `ef8bf0c` on branch `worktree-agent-aa6ef474a0f78ec9e`, on top of `d7a9a9c` in the same worktree (`/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-aa6ef474a0f78ec9e`). The message ends with the Co-Authored-By line. Only `src/deploy_workflow/owners/cpl10.py` and `tests/test_method_cpl10.py` changed.

**Changes**
- **Code**: the three new refusals now read `overall.limitation: empty`, `gaps[i].why_it_matters: empty` and `gaps[i].action: empty`. Their positions are unchanged:
  - the limitation check still comes after r14/r15 in step (5);
  - the why_it_matters and action checks still come after r17 and before r18 in step (6).
- **Docstrings**: they now name the module frame instead of the fallback.
- **Tests**:
  - `BLANK_FIELDS` is now (path, keys) pairs. One constant, `EMPTY = "{path}: empty"`, goes to `blank_failure` for all 8 fields.
  - The `EMPTY_TEXT` import is gone.
  - Both order tests now expect `: empty`.
  - The header comment records the ruling: one spelling per module.
- **Stage 2 note** for `methods/cpl10.md`: all eight analyst text fields refuse whitespace-only text with `<path>: empty`. `""` keeps its `Text` shape issue.

**Mutants**: each ran in a full temporary copy with `PYTHONDONTWRITEBYTECODE=1`, and the script exited 0. Script: `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/cpl10-class/mutants.sh`

| Mutant | Change | pytest exit | Result |
|---|---|---|---|
| m1 | no limitation check | 1 | killed |
| m2 | no why_it_matters check | 1 | killed |
| m3 | no action check | 1 | killed |
| m4 | limitation frame changed to `: empty text` | 1 | killed |
| m5 | gap field frame changed to `: empty text` | 1 | killed |
| m6 | limitation check only on an Insufficient overall | 1 | killed |

**Gates** (all exit 0)
- `PYTHONPATH=src .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_method_cpl10.py`: exit 0, 126 passed. The frozen oracle and refusals r01 to r19 are unchanged and pass.
- `ruff check` on both files: exit 0.
- `ruff format --check` on both files: exit 0.
- `MYPYPATH=src mypy --strict` on both files: exit 0.

Not verified:
- I did not run the full pytest suite or `test_defect_classes_selfcheck.py`, only the module's own test file.
- I did not run GitNexus `detect_changes`, because the implementer has no MCP tools.
- `topic_id`, `affected_analysis`, the periods and the closed vocabularies are treated as not analyst text, following the probe adapter. A whitespace `affected_analysis` is refused only by r16.
- Index 1 is exercised only through `assessments[1].assessment`; the other fields at index 1 run the same code.
- The new `: empty` spellings for the three fields rest on the controller ruling, not on a lease line.

Ledger: `agent=general-purpose(opus) fix-rounds=0 gates-first-pass=y`
