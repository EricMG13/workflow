# Stage 2 batch integration pass 3 (mx-feature)

All three merges and the D7 patch are on claude/s2-batch, and the final gates pass except the same ruff SIM102 at `report_view.py:293` that was in the base before this pass. Final SHA: 5977ae4ba74fea418062ca2671de31c301981b7e. Step 0 held: HEAD was 3d0392e and the tree was clean.

**Conflicts.** Every one was a pure append; I resolved them in merge order. No existing row was dropped or reordered.
- **cp3c:** `shipped.py` comment and `owner_workflow.py` tails. CP3C sits directly after CP2D, as its lease states.
- **cp2h:** `shipped.py` and `owner_workflow.py`. CP2H is last in `SHIPPED_MAPS`.
- **cp4c:** `shipped.py`, `owner_workflow.py`, `report_view.py` and `tests/test_connect_cp3.py`.
  - `_DISTRESSED` rows are in merge order: CP-2G, then `rating-triggers`, then `recovery-by-class`, then `value-allocation-claims`. The CP-4C lease states no order.
  - CP4C is last in `SHIPPED_MAPS`.
  - The `test_connect_cp3.py` spec-less parametrize is now `_specless_modules()` only.

**D7 patch.** I read `d7_patch.py` first; it matched your description.
- It applied cleanly, in its own commit 49c5865 `feat(cp3c): D7 rows with CP3C_D7_DELTA (round 5 item 18)`.
- The two CP-3C `_Spec` rows landed in `_COVENANT_REFINANCING` after the CP-2D rows, not in `_DISTRESSED`.
- `CP3C_D7_DELTA` sits beside `CP2D_D7_DELTA`, and `test_spec_rows_serve_the_two_blocks` is added.
- `test_connect_cp3c`, `test_legal_render` and `test_connected_render` gave 213 passed.

**Test-side fixes.** Only the `test_connect_cp3.py` conflict resolution above. No other registration assertion broke this pass.

**Manifest.** Both parts are in the manifest commit.
- **Added:** `shipped.py` records for CP-3C, CP-2H and CP-4C, and `report_view.py` records for the same three. Each chains from the previous sha, with `project_commit` set to the merge commit (or the D7 commit) holding that content.
- **Re-chained:** only the `prior_project_sha256` links of the forks.
  - CP-2D `shipped.py`: from 8afa15fc.
  - CP-2E `shipped.py`: from the CP-2D record, 0b74f88e.
  - CP-L10 `shipped.py`: from f51954d7.
  - CP-2D `report_view.py`: from 09ab059d.
- **Extended check, 19 destinations:** the chain has 0 breaks, and for every destination the newest sha equals the file and equals `git show <project_commit>:<path>`.

**Gates**
| Gate | Result |
| :--- | :--- |
| Per merge: cp3c (+ `test_owner_cp3c`, `test_legal_render`) | 848 passed, 11 skipped |
| Per merge: cp2h | 732 passed |
| Per merge: cp4c (+ `test_connect_cp3`) | 1825 passed, 1 skipped |
| Full fast set | exit 0, 8916 passed, 4 skipped |
| `test_legal_render` + `test_connected_render` | 90 passed |
| Pins | exit 0 |
| `ruff format --check` on the changed `src` files | clean |
| `ruff check` on the changed `src` files | 1 error, the pre-existing SIM102 |
| `mypy --strict` on the 3 registration files | clean |
| `noqa` count | 13 |
| `type: ignore` count | 8 |
| `--collect-only` over `tests/test_owner_cp*.py` | 592 collected |

Not verified:
- `test_financial_render.py` and the other slow render files.
- The deferred `test_owner_cp*.py` store runs, which were collected only.
- The real CP-1 promotion in `test_owner_order.py` (skipped).
- The builders' report files were not read; I computed the manifest shas from the merged files.
- Intermediate merge commits were not each run against the fast set; only the final tip was.
- The pre-existing SIM102 is not fixed.

agent=mx-feature fix-rounds=0 gates-first-pass=y
