# G1-X plan-order ride-along report (mx-feature)

Commit 0cb0ec6 on `claude/s2-g1x-order`, cut at 93a627c. Step 0 passed: clean tree, HEAD 93a627c.

**Changes**
- In `src/deploy_workflow/owner_workflow.py`, a new helper `_upstream(graph, m)` returns the transitive producers of `m`.
- `_check_specs` now takes `graph = dependencies(requested)`. An analytical module after the deterministic one is refused `not_permitted` only if the deterministic module is in its upstream or it is in the deterministic module's upstream.
- Nothing beyond the guard changed. I read the walk, `publish`, `_refused`, `_terminal`, `_verify_walk`, `_verify_chain` and `_verify_transition`. None depends on list position, so I made no other change.
- New file `tests/test_owner_order.py`.
- Comment-only edits in `tests/test_owner_workflow.py` and `tests/test_owner_s1a.py` (symbols `test_unsupported_and_unknown_selection_write_nothing` and `test_cp5_selection_and_spec_overrides_refuse_before_writing`).

**Rules and invariants, with tests**
- R3 plan passes: `test_r3_plan_with_cp3_after_cp_model_passes`. It uses the G1-X fake core registered as CP-3, with `step_chain` patched so CP-3 reads as owner-only. The fake is test-only.
- A module after CP-MODEL that is unrelated to it passes: `test_unrelated_module_after_cp_model_passes_whatever_its_position`.
- A module that consumes CP-MODEL refuses (direct, transitive, deep): `test_module_after_cp_model_that_consumes_it_refuses`.
- A module that feeds CP-MODEL refuses (direct, transitive, deep): `test_module_after_cp_model_that_feeds_it_refuses`. These cases patch `plan` and `dependencies`, because the real registry never produces such plans.
- Two deterministic modules refuse: `test_two_deterministic_modules_refuse`.
- Invariant 3, walk order: `test_walk_order_is_planned_without_the_deterministic_module`.
- Invariant 1, `publish` only in phase `walked`, once:
  - `test_publish_waits_for_every_analytical_module_after_cp_model`.
  - `test_later_module_runs_beside_a_refused_publication_and_receipt_verifies`. It runs a real store with a blocked CP-1 (about 0.5 s). The module after CP-MODEL still runs, publication refuses, and the receipt verifies.
- Invariant 2: `test_a_blocked_later_module_does_not_refuse_publication` covers `_terminal`, and the real-store test above covers `_refused`.
- Invariant 4:
  - On the refused path, the receipt chain verifies in the real-store test.
  - On the published path it is deferred (see below).
- Invariant 5: `test_two_deterministic_modules_refuse`.

**TDD**
With the guard reverted, 5 tests fail. They are the positive ones (R3 plan, unrelated module, the walk-order and publish-waits tests, and the real-store test). They fail on the old unconditional refusal. The refuse-cases already pass on old code, since the old guard refuses them too. The mutants cover those.

**The two existing tests**
Both still refuse, and the expectation is unchanged. I updated the comments. Today the cause is that CP-5 has no `OWNER_SPECS` row. After CP-5 is registered it will still refuse. The registry's fan-in makes CP-5 require CP-MODEL, so it consumes CP-MODEL and the new rule refuses it. If the ruling expected CP-5 to be admitted once registered, it is not. The lead may want to confirm that.

**Deferred**
`test_publication_is_last_in_the_receipt_chain_and_verifies` is written but skipped. It needs a real CP-1 promotion (11–26 min). Run it with:
`cd "<worktree>"; RUN_PROMOTION=1 PYTHONPATH=src:tests "<venv>/bin/python" -m pytest -q -p no:cacheprovider tests/test_owner_order.py -k publication_is_last`

**Gate exit codes**
- pytest on the four files: 0 (298 passed, 1 skipped).
- The two `-k` tests: 0 (3 passed).
- `ruff check` and `ruff format --check` on the changed files: 0.
- `mypy --strict`:
  - `owner_workflow.py`, `test_owner_order.py` and `test_owner_workflow.py`: 0.
  - `test_owner_s1a.py`: exit 1 with 7 errors, all pre-existing. I only added comments there.

**Mutants** (exit 0; script `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/g1x-order/mutants.py`)
All seven were killed in a full temporary copy: guard open, direct-only consumes, direct-only feeds, consumes-only, feeds-only, publication moved earlier, and the walk including the deterministic module.

**Not verified:**
- A published CP-MODEL receipt chain with the module after CP-MODEL (the deferred test).
- A later module that is refused or blocked in a real run. I covered that only through `_terminal` with synthetic heads.
- A real CP-3 module, since its connection is a separate branch.
- `jscpd`, `complexipy` and the full suite.
- mx-adversary review.

agent=mx-feature fix-rounds=0 gates-first-pass=y

Controller check: claude/s2-cp3 merged with claude/s2-g1x-order in a scratch tree; `cp3-s2/p_create.py` -> positive created, gap created (R3 create succeeds with the real CP-3).
