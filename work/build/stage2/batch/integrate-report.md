# Stage 2 integration report (mx-feature)

All 9 merges are done and the final gates pass, with one caveat: ruff reports one SIM102 error that was already in the base (`report_view.py:293`). Final SHA ffa1c88a0ebae1f8d0b0e4734edef4fa385ec3f3 on claude/s2-integrate, tree clean.

**Merges and conflicts.** All conflicts were pure appends; I kept every existing row in merge order.
1. s2-defect-classes: no conflict.
2. s2-g1x-order: no conflict.
3. s2-cpdr: no conflict.
4. s2-cp3d: conflicts in `owner_workflow.py` and `shipped.py`. CP3D sits directly after CP3, as its lease states, and CPDR stays last.
5. s2-cp2e: conflicts in `owner_workflow.py`, `shipped.py` and `manifest.json`. CP2E is last in `SHIPPED_MAPS`.
6. s2-cp3: conflict in `owner_workflow.py`. CP-3 keeps `entry="model_payload"`.
7. s2-cp5: conflict in `owner_workflow.py`. CP-5 keeps `entry="model_payload"`.
8. s2-cp8: conflicts in `owner_workflow.py` and `shipped.py`. CP8 is last. The CP-8 lease states no position, so I used the branch's "appended last".
9. s2-cp2a: conflicts in `shipped.py`, `report_view.py` and `owner_workflow.py`.
   - CP2A is last in `SHIPPED_MAPS`, per its lease ("+= CP2A").
   - `_DISTRESSED` is kept after `_RELATIVE_VALUE`.
   - `_spec_of` loops over both compositions.
   - The `_PRESETS` insert auto-merged.
   - I sorted the function-local imports in `owner_workflow.py` to satisfy ruff I001.

**Test-side fixes under your ruling (a).** Each is its own commit, `tests(integrate): <file>: registration assertions survive later appends`.
- `tests/test_connect_cp3.py` (4f300e9):
  - It no longer asserts the full `OWNER_SPECS`, `_PROBES`, `_ENTRY_VALIDATORS`, `_QUALIFICATION` or `SUPPORTED_ANALYTICAL`. It now checks that the base rows are an unchanged prefix, that CP-3 comes after them, and that `SUPPORTED_ANALYTICAL` contains the base set.
  - The spec-less refusal test now takes its module ids from `registry.modules()`, minus those in `OWNER_SPECS`. It asserts loudly if none are left. I kept the old `CP-4C`, `CP-2D` and `CP-3C` params.
  - The "refuses and writes nothing" assertions are unchanged.
- `tests/test_connect_cp2e.py` and `tests/test_connect_cp8.py`: `SHIPPED_MAPS[-1] is CPxx` became "the map is present and sits after CP-6".
- `tests/test_connect_cp3d.py`: `_CORES[-1]` and the `OWNER_SPECS` tail check became a prefix check plus "CP-3D present after CP-MODEL".
- The cp2e, cp3d and cp8 failures only showed up in the final fast set. Their per-merge gates passed because each module was still last at that point.
- `test_connect_cp5.py` and `test_connect_cp2a.py` needed no change.

**D12 manifest.**
- Added records: `shipped.py` and `report_view.py` for CP-3D, `shipped.py` for the merged CP-2E tail, `shipped.py` for CP-8, and `shipped.py` plus `report_view.py` for CP-2A.
- Each record names the lease as its review, chains `prior_project_sha256`, and sets `project_commit` to the merge commit that holds that content. CP-DR's and CP-2E's own branch records are kept as history.
- There is no repo manifest-check script. I ran a one-off check: for all 19 destinations in `post_import_patches`, the newest record's sha equals the file's sha and equals `git show <project_commit>:<path>`. 0 mismatches.

**Gates**
| Gate | Exit | Result |
| :--- | :--- | :--- |
| Per-merge sets (1-9) | 0 | all passed, after the test fixes above |
| Fast set | 0 | 7913 passed, 3 skipped |
| Render suites | 0 | 238 passed in 54 min |
| `cases/pins.py --check` | 0 | matches 69 paths |
| `ruff format --check` on the 15 changed `src` files | 0 | 15 files already formatted |
| `ruff check` on the same files | 1 | one SIM102 at `report_view.py:293`, in the base's code at e9b7387 and not touched by the merge |
| `mypy --strict` on the 3 files | 0 | no issues |
| `git grep noqa -- src tests` | n/a | 13 (limit 13) |
| `--collect-only` over the 6 deferred `test_owner_cp*.py` files | 0 | 260 tests collected |

**Merge tree-state caveat.** Intermediate merge commits (for example 43a2561, the cp3 merge) fail the cp3 assertions that the later test-fix commits repair. Only the final tip is green.

Not verified:
- Real CP-1 promotion test (`test_owner_order.py:356`, skipped as deferred).
- `test_owner_order.py` was not rerun as part of each merge's gate set; it ran in the fast set only.
- The pre-existing SIM102 ruff error was not fixed.
- The deferred `test_owner_*` files were only collected, not executed.

agent=mx-feature fix-rounds=1 gates-first-pass=n
