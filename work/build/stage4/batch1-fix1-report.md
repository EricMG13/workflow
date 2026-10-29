Batch 1 fix round 1 is done. All three findings are fixed and every required gate and probe exited 0 except the one that is meant to fail. Tip is 715dc98 on `claude/s4-batch1-fix1` (from 515a8c6), in `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a2b07df1043618c51`. The `.venv` link is removed and the tree is clean. Only the three named files changed.

**Change per finding**
- **Medium 1** (1321878 RED, d75a6b3 fix):
  - `_verify_transition` in `src/deploy_workflow/owner_workflow.py` now requires the after-attempt's `(module_id, inputs, number, repair_of, repair_issues)` to equal the attempt before the step, for every submission. Since the first step is bound to the begin's `after`, this means "as begun". A mismatch gives `identity_mismatch`.
  - New tests in `tests/test_owner_stage4.py`: the relabel to number 0 is refused, a rewrite of `repair_issues` is refused, and a genuine repair is accepted (control, numbers [0, 1]).
  - I added `pytest_plugins = ("test_owner_g1x",)` there to get the `g1x` fixture without a `noqa`.
- **High 1** (715dc98): in `tests/test_owner_s1a.py`, `_publish_forged_cp_model` now uses P-M's patched producer. It also patches `execution.current_inputs` so `finish` and `interrupt` accept the forged inputs, and asserts publish returned `ok` and `_phase == "complete"`, so the forged run reaches the verifier. The two tests are rebuilt on it. I added a third test on P-F's failed-first route (`fail_first_write`): `test_forgery_cp_model_failed_first_publication_on_forged_inputs_refuses`.
- **Info** (a369a76): the CP-0, CP-1 and CP-1A rows now assert that the spec's source-bearing steps equal `host._SOURCE_STEPS[module]`, and that the set is non-empty. They are listed in `PACK_TOOL_MODULES`.

**RED and non-vacuity**
- **Medium 1:** at 515a8c6 the relabel test failed with `DID NOT RAISE WorkflowError`. After d75a6b3, `tests/test_owner_stage4.py` gives 34 passed.
- **High 1 genuine run:** the 3 `forgery_cp_model` tests pass, exit 0, 688 s (log `run-high1b.log`). An earlier run failed only on my own wrong `"published"` status string, which I fixed.
- **Non-vacuity:** I made the lenient edits in scratch copies of `src` (`s4fix1/both` and `s4fix1/pub`) and ran pytest with `-o pythonpath=<scratch>/src .`. Without that override, pytest's `pyproject` `pythonpath` loads the real `src` and the lenient copy is ignored; my first lenient run passed for that reason and I discarded it.
  - Publication-path `_expected_begin` check and final deterministic-head binding both made lenient: all 3 tests fail with DID NOT RAISE (exit 1, 958 s).
  - Only the publication-path check lenient: the P-F test fails with DID NOT RAISE (exit 1, 380 s).
  - The P-M tests have two independent refusing checks, so the test fails only when both are lenient. That matches P-M p4.
  - Nothing lenient was committed.

**Gates and probes (exit 0 unless noted)**
- Plan §6 batch 1 pytest command: 8 passed, 195 deselected, 731 s.
- `ruff check` and `ruff format --check` on the 3 files; `MYPYPATH=src mypy --strict src/deploy_workflow/owner_workflow.py` (success).
- Suppressions: noqa 13 and type: ignore 5, both within the limits.
- `python3 -I cases/pins.py --check`: matches 86 paths.
- P-A: 7 passed, 1 failed. The failure is `test_a1`, on its old-acceptance assertion (`write_receipt:identity_mismatch` instead of `accepted`), as expected.
- P-B, P-C, P-D and P-R: 12 passed.
- P-V: exit 0. It still reports 11 vacuous rows, because it mirrors the old test branches and does not see the new `PACK_TOOL_MODULES` assertion. The 11 rows now reach it, and it passes on all of them.
- P-F: exit 0.
- P-M `probe_cp_model.py`: 4 passed, exit 0, 666 s.

**Stopped processes:** after your overload message I stopped two of my three concurrent `forgery_cp_model` runs. I also stopped my first batch-1, P-M and P-F runs, and reran those one at a time. No stop was refused. I did not touch the builder's stray pid 79376 or the lane's own processes.

**Deferred for the controller:**
- `PYTHONPATH=src:tests .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_owner_s1a.py`
- `PYTHONPATH=src:tests .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_owner_workflow.py`
- `PYTHONPATH=src:tests .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_owner_cp*.py`

Not verified: a genuine run that actually repairs and then passes the new rule, beyond the g1x fake harness and the lane gate `-k` selections; the deferred full suites above (which exercise genuine repairs on real modules); whether real module probes catch the Medium 1 relabel; mutation and property gates; the new PACK_TOOL_MODULES assertion has no mutation check of its own.

Ledger: agent=mx-feature fix-rounds=1 gates-first-pass=n (the first High 1 run failed on my wrong status string, then passed)
