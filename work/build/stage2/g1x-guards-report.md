Both guards are in and each has a test that failed before the code change. Commit 3d25683 on `claude/s2-g1x` (cut at 6e51653; the tree was clean at the start). It touches only `owner_workflow.py` and `tests/test_owner_g1x.py`, and the tree is clean after the commit.

**Guard 1: `sources` against `host._OWNER_SCOPES`**
- The owner-only `served` clause in `_check_steps` now also requires `item.sources == ((module_id, item.step_id) in host._OWNER_SCOPES)`. It is read through `host` as a module attribute so tests can patch it.
- The refusal is the existing `WorkflowError("not_permitted")` at create, the same as the other checks. I also extended the docstring.
- Test: `test_owner_step_sources_follow_the_h1_scope_table` covers both directions, "sources without a scope row" and "scope row without sources".
- The `g1x` fixture now adds a `(MODULE, SOURCED)` row to `host._OWNER_SCOPES`, as a real module task would. Without it the fake sourced step would be refused.

**Guard 2: `STEP_IDS` must be a tuple of str**
- The owner-only branch reads `STEP_IDS` raw and refuses `not_permitted` unless `type(raw) is tuple` and every item is exactly `str`. This check runs before the sequence comparison, and the old `tuple(...)` coercion is gone.
- Test: `test_owner_core_step_ids_are_a_tuple_of_str`, with a list case and a `(SOURCED, 2)` non-str case.
- The non-str case is not independently red. A non-str item always mismatches the spec's str step ids, so the old code already refused it. The list case is the red one.

**Registered modules:** `test_every_registered_module_passes_the_step_check` runs `_check_steps` on every `OWNER_SPECS` row that has a financial or entry-validator registration. It passes.

**Gates (all exit 0)**
- The pytest command, 4 files: 236 passed.
- `ruff check` and `ruff format --check` on both changed files.
- `MYPYPATH=src mypy --strict src/deploy_workflow/owner_workflow.py`.

**Mutants:** each was run from a full temporary copy with `PYTHONDONTWRITEBYTECODE=1`, against `tests/test_owner_g1x.py` only. Both pytest runs exited 1, so both mutants are killed.
- Dropping the `_OWNER_SCOPES` clause fails `test_owner_step_sources_follow_the_h1_scope_table`.
- Restoring `tuple(raw)` in place of the tuple/str guard fails `test_owner_core_step_ids_are_a_tuple_of_str`.
- My first tuple mutant only deleted the check and left `sequence = raw`, which survived because a list never equals the spec tuple. That was a weak mutant, not a weak test, and I replaced it with the true revert above.
- Scripts are in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/s2-g1x/`: `run.sh` and `mutate.py`.

Not verified: the full test suite, because I ran only the four briefed files. The mutants ran only `tests/test_owner_g1x.py`. The non-str-item branch has no test that fails without it, because it is redundant with the spec-steps comparison. No real module task was exercised against the new `_OWNER_SCOPES` guard beyond the currently registered specs.

agent=mx-feature fix-rounds=0 gates-first-pass=n (the first ruff run failed on import order and format, fixed before commit)