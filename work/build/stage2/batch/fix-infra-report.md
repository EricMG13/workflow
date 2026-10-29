# Fix batch, fixer 3: infra and Lows (mx-feature)

Fixer 3 (`claude/s2-fix-infra`) is committed as acdaee7 on a1a0574, one commit. All my items are done except that the CP-1D L3 test is written but not run. The Edit tool was fine, so I did not need Python-from-Bash for editing. The D12 provenance fix has one side effect, described below.

**Items, red then green**
- **hide_row (g1x:523, :640).** Red was the `pi3` order run: 5 failures, `_CORES[:2] == ('CP-DR','CP-2E')`. Both `delitem` calls on `_CORES` and `_ENTRY_VALIDATORS` now use `hide_row`. Green: that order run gives 625 passed, and `pi2` shows reordered [].
- **SHIPPED_MAPS order pin.** New test `test_the_stage_1_binding_maps_keep_their_shipped_order` in `tests/test_owner_g1x.py`. Before the test, `pi1` printed SURVIVED, exit 1. After it, KILLED, exit 0. I pointed `pi1` at my tree and added `test_owner_g1x.py` to its test list.
- **G1 I2.** Two new tests in `tests/test_owner_s1a.py`: the first shows a valid step with issues is refused, the second shows `identity_mismatch` after a consistent reseal. Dropping the `or self.issues` guard fails the first test, and the second fails on "DID NOT RAISE". The backlog row now reads `[G1] CLOSED`. `pg1` exits 0.
- **D12 provenance.**
  - Before: `pd3` reported 7 NOPARENT records. After: only #25 (CP-DR) remains, which is the owner item.
  - The records changed are listed in the next section.
- **Info, `test_legal_render.py`.** Fixed the stale comments and removed `UNBOUND_FALLBACK` and the self-comparing note fallback. The tests now index `CP2D_D7_DELTA[block_id]` and `CP2D_D7_NOTE[block_id]` directly. 76 passed.
- **CP-8 L-a.** The identity read is now pinned to `("refused","not_permitted")`. It fails under a mutant that changes `error.code` (host.py:1076).
- **CP-8 L-b.**
  - A new test shows the `not_permitted` calls leave the attempt unchanged and appear in `receipt.calls`. It fails under a mutant that drops `self._calls.append`.
  - The stale test now asserts the refused submit adds no step and no attempt beyond the interrupt's.
  - A stale refusal cannot be recorded in a receipt, because `write_receipt` itself raises `stale_binding`. Lease line 85 ("both recorded in receipt") cannot hold for stale as written.
- **CP-1D L2.** Three new tests in `tests/test_connect_cp1d.py` against the three surviving mutants (constant status, `attempt.inputs`, known filter removed). On the old tests all three SURVIVED; on the new tests all three are killed (script `cp1d_mutants.py`, exit 0).
- **CP-1D L3.** I added an edited step-output case and a `monkeypatch.setitem(_PROBES, "CP-1D", spy)` check to the deferred tamper test in `tests/test_owner_cp1d.py`. That file needs an 11-26 minute run per case, so I only collected it (29 tests collected, ruff clean).
- **CP-1D L5.** The three `type: ignore` are gone (`monkeypatch.setattr` and `cast`). The count goes 8 to 5, with no other suppression added.
- **Shared defect-test Info.** The test now uses `TWO_NOTES` and a new `strict_first_note` fake. It shows one refusing path excused when another path accepts. A mutant that fails any refusing path on a verbatim pattern kills it; the old test survived that mutant.

**Manifest records changed**
All six records now have `prior_project_sha256` equal to the file hash in the first parent of `project_commit`.

| Record | `prior_project_sha256` before | `prior_project_sha256` after | `project_commit` |
| :--- | :--- | :--- | :--- |
| #27 | 8afa15fc | 4ef3f9ff | unchanged (8aef58d8) |
| #29 | 0b74f88e | 4ef3f9ff | unchanged (0fa5b4aa) |
| #34 | 09ab059d | 51a6853e | unchanged (8aef58d8) |
| #37 | f51954d7 | 4ef3f9ff | unchanged (6b679cab) |
| #39 | unchanged (11185049) | unchanged | 94d9f29e -> 7831ef12 |
| #40 | unchanged (8ed326cb) | unchanged | 94d9f29e -> 7831ef12 |

Side effect of the ruling: `pd1_manifest_chain` previously reported `bad: 6` and now reports `bad: 10`. The four new ones are #27, #29, #34 and #37, because `pd1` demands that each prior equal the previous record's sha, which the first-parent rule contradicts on merged histories. The owner may want to retire `pd1`'s chain check.

**Probe and gate exit codes**
- **Probes:** `pi1` 0, `pi2` 0, `pg1` 0, `p14` 0.
- **`pd3`:** exit 1, because #25 (the owner item) still fails. Every Stage 2 record passes.
- **`pd2`:** checked 89, bad 0.
- **Pytest, order run:** the six files, 626 passed, exit 0.
- **Pytest, wide run:** every `test_connect_*`, plus `test_legal_render`, `test_owner_cp8`, `test_defect_classes_selfcheck` and `test_owner_g1x`. 2843 passed, 2 skipped, exit 0. This includes `test_connect_cp8`, `test_connect_cp1d` and `test_owner_cp8`.
- **`ruff format --check`:** exit 0.
- **`ruff check`:** one error remains, C408 at `tests/test_legal_render.py:237`. It is not in a line I changed, and I left it.
- **`mypy --strict`:** errors remain in `tests/test_owner_s1a.py` (7) and `tests/test_legal_render.py` (about 130). I added none; mine are clean.
- **`cases/pins.py --check`:** exit 0.
- **Counts:** `type: ignore` is 5. The `noqa` count is 24 by `grep` both at a1a0574 and now, so it did not change, but I could not reproduce the baseline of 13 you quoted.

**Not verified:**
- The CP-1D deferred tamper test (`tests/test_owner_cp1d.py`): written and collected, never run.
- The full `tests/test_owner_s1a.py`: only the two new tests ran.
- The slow suites (render, a11y).
- GitNexus `detect_changes`.

agent=mx-feature fix-rounds=1 gates-first-pass=n
