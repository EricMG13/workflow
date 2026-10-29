# G1-X order fix1 re-review (mx-adversary)

**Scoped re-review, G1-X plan-order fix round 1 (5b3756a on 3218b49): APPROVE.** All three items are closed and every gate exits 0. Only test files changed: `test_owner_order.py`, `test_owner_s1a.py` and `test_owner_workflow.py`.

I ran everything on a scratch copy of 5b3756a at `<R>/fix1`, where `<R>` = `/private/tmp/claude-501/-Users-ericguei-Documents-Deploy-Workflow--claude-worktrees-module-dev-status-review-0981b6/23b694e3-18f9-4a89-b4fc-e92c726d3861/scratchpad/g1x-order-review`.

- **M1, closed.**
  - The deferred test now uses `consumers = [row, {**row, "module_id": g1x.MODULE}]`.
  - It asserts that `publish` returns ok exactly once after the walk, and that the sealed receipt verifies with `publication_directory`.
  - It asserts the publication is last: the last publication's `snapshot_after_sha256` is the final snapshot, the final snapshot's last attempt is CP-MODEL, and the last begin is CP-3D.
  - The fixer's output in `scratchpad/g1x-order/deferred.out` reads "1 passed, 15 deselected in 586.85s", exit 0. That matches the 16 tests now in the file and my own earlier run of the same fix (`<R>/p6_published_path_corrected.py`), so I did not re-run it.
  - The refused-path check `receipt.publications[-1].snapshot_after_sha256 == store.read().content_hash()` is in the real-store test.
- **M2, closed.** `test_consumer_is_refused_behind_an_unrelated_module_after_cp_model` uses the order (CP-0, CP-1, CP-MODEL, CP-3D, CP-3).
  - `<R>/mut.py` (`<R>/fix1_mut.out`, exit 0): `first_later_only` and `publisher_is_previous` are now KILLED, and the other six of mine stay killed.
  - The implementer's 7 mutants are all KILLED (`<R>/fix1_impl_mut.out`, exit 0).
- **L1, closed.**
  - Both comments now say CP-5 has no `OWNER_SPECS` row on this branch, and that once it is registered the round-2 rule refuses it through the fan-in (DC-5 open).
  - The `test_owner_workflow.py` comment states that `plan` raises `ValueError` for `CP-NOT-A-MODULE`.
  - Both statements match my earlier probes `<R>/p2_two_later_real.py` and `<R>/mut_cp5sel_*.out`.

**Exit codes**
- `ruff check`: 0
- `ruff format --check`: 0
- `mypy --strict` on `owner_workflow.py`, `test_owner_order.py` and `test_owner_workflow.py`: 0
- pytest on `test_owner_order.py`, `test_owner_g1x.py` and the two CP-5 tests: 0 (42 passed, 1 skipped)
- mutants: 0

Not verified: I did not re-run the 587 s deferred test myself. Also not run: the full `test_owner_workflow.py` and `test_owner_s1a.py` files (slow promotion fixtures), mypy on `test_owner_s1a.py` (which has 7 errors from before this change, per the implementer), complexipy and jscpd (not installed), and the full suite.
