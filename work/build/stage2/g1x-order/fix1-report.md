# G1-X order fix round 1 report (mx-feature)

Fix round 1 is committed as 5b3756a on top of 3218b49, branch `claude/s2-g1x-order`. Only tests changed; `owner_workflow.py` is untouched. `/private/tmp/.../scratchpad/g1x-order-review/mut.py` kills all 7 mutants, including `first_later_only` and `publisher_is_previous`. I could not read `work/build/stage2/g1x-order/review.md` from this worktree, so I worked from the probes in `<R>` and your message.

- **M1:** In `tests/test_owner_order.py`, the deferred `test_publication_is_last_in_the_receipt_chain_and_verifies` now sets `review["consumers"] = [row, {**row, "module_id": g1x.MODULE}]` (CP-1 plus the module after CP-MODEL). I ran it with `RUN_PROMOTION=1`: 1 passed in 586.85 s, exit 0. Output is in `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/g1x-order/deferred.out`. I also added the refused-path check to the real-store test: `receipt.publications[-1].snapshot_after_sha256 == store.read().content_hash()`. It passes.
- **M2:** New test `test_consumer_is_refused_behind_an_unrelated_module_after_cp_model`, plan order (CP-0, CP-1, CP-MODEL, CP-3D, CP-3). With CP-3 requiring CP-MODEL it refuses `not_permitted`. With CP-3 changed to need only CP-0, both modules are admitted in plan order.
- **L1:** The comments in `test_owner_workflow.py` and `test_owner_s1a.py` now say "on this branch CP-5 has no OWNER_SPECS row; once registered, round 2's rule refuses it through the CP-5 -> CP-MODEL fan-in (DC-5 open on the CP-MODEL row)". The `test_owner_workflow.py` comment also mentions the `("CP-NOT-A-MODULE",)` case, which `plan` refuses with a `ValueError`.
- **Test-first:** The M1 test failed at CP-0 before the fix, per your report, and passes now. The M2 test passes on the current guard, and it is the one that kills the two mutants.

**Exit codes**
- pytest on the four files: 0 (299 passed, 1 skipped).
- The two `-k` tests: 0 (3 passed).
- `ruff check` and `ruff format --check` on the four changed files: 0.
- `mypy --strict` on `owner_workflow.py`, `test_owner_order.py` and `test_owner_workflow.py`: 0. `test_owner_s1a.py` still has its 7 errors from before this task.
- `<R>/mut.py` on `first_later_only`, `publisher_is_previous`, `guard_open`, `required_only_graph`, `terminal_waits_on_all`, `second_det_allowed` and `advance_last_not_walked`: exit 0, all killed.
- My earlier 7-mutant script: exit 0.

**Not verified:**
- A later module that is refused or blocked in a real run, as opposed to the `_terminal` unit check.
- A real CP-3 module.
- Mutation runs against the deferred promotion test.
- The full suite, `jscpd` and `complexipy`.

agent=mx-feature fix-rounds=1 gates-first-pass=y
