# Stage 2 batch integration pass 2 (mx-feature)

All four merges are done on claude/s2-batch (HEAD == e1d0630 at start, tree clean at end), and the final gates pass except one ruff finding that was already in the base. Final SHA: e3ff4823cf53a2b3decdd1503a44089d085c0dc9.

**Conflicts.** Every conflict was a pure append, resolved in merge order. No existing row was dropped or reordered.
- **cp2d:** conflicts in `owner_workflow.py` (registration tails), `shipped.py` and `manifest.json`.
  - CP2D sits directly after CP2 in `SHIPPED_MAPS`, per its lease.
  - `report_view.py` merged cleanly; `CP2D_D7_DELTA` in `test_legal_render.py` is kept.
- **cp4:** `owner_workflow.py` only. CP-4 keeps `entry="model_payload"`.
- **cpl10:** `owner_workflow.py`, `shipped.py`, `manifest.json`. CPL10 is appended last in `SHIPPED_MAPS`.
- **cp1d:** `owner_workflow.py`, `shipped.py`, `report_view.py`.
  - `_EARNINGS_QUALITY` is added to the `_spec_of` loop after `_DISTRESSED`.
  - CP1D is appended last in `SHIPPED_MAPS`; its lease names no position.
  - Its `OWNER_SPECS` row stays where the branch put it, after CP-2 and before CP-MODEL. I did not move it.

**Test-side fixes.** One commit each, `tests(integrate): <file>: registration assertions survive later appends`.
- **`test_connect_cp4.py`:** prefix-plus-membership checks, and the covenant composition check became `own <= set(...)`.
- **`test_connect_cp1d.py`:** the full `SHIPPED_MAPS` list became a base prefix plus CP-1D after CP-6.
- **Re-fixed after CP-1D's row landed:**
  - `test_connect_cp2a.py`, `test_connect_cp2d.py`, `test_connect_cp3.py`, `test_connect_cp3d.py`, `test_connect_cp4.py` and `test_connect_cp8.py` now exclude CP-1D from the base-prefix comparison, with a comment saying why.
  - In `test_connect_cp3.py` I also dropped the hard-coded `CP-2D` from the spec-less refusal params; the dynamic list covers it.
- **`test_connect_cpl10.py`:** the `[-1] ==` checks became membership plus order checks.
- The cp4 and cp1d edits were found at their own merge gates, so they are not in the fast-set failures below.
- The fast set failed with 8 failures on the first run after cp1d landed, before the re-fix commits.

**Manifest records.** Chained as before; `project_commit` is the merge commit holding the content.
- `shipped.py` and `report_view.py` for CP-2D.
- `shipped.py` for CP-L10.
- `shipped.py` and `report_view.py` for CP-1D.
- CP-4 touched no reused file, so it has no record.
- My one-off check over all 19 destinations: the newest record's sha equals the file and equals `git show <project_commit>:<path>`. 0 mismatches.

**Gates**
- Per-merge sets all passed:
  - cp2d: 731 passed, 9 skipped (the store runs).
  - cp4: 394 passed, including `test_probe_cp4`.
  - cpl10: 576 passed, 1 skipped.
  - cp1d: 927 passed, 1 skipped.
- Fast set, exit 0: 8302 passed, 4 skipped.
- `test_legal_render` and `test_connected_render`, exit 0: 90 passed.
- Pins: exit 0.
- `ruff format --check` on the changed `src` files: exit 0.
- `mypy --strict` on the three registration files: exit 0.
- `noqa` count: 13 (limit 13).
- `--collect-only` over `tests/test_owner_cp*.py`: 357 tests collected, exit 0.
- `ruff check`: exit 1, one SIM102 at `report_view.py:293`. That code was in the base e9b7387 and the merges did not touch it.

Not verified:
- `test_financial_render.py` and the other slow render files (skipped as briefed).
- The store-backed `test_owner_cp2d.py` runs (skipped, need a real CP-1 promotion).
- The real CP-1 promotion in `test_owner_order.py` (deferred).
- The `test_owner_cp*.py` files were only collected, not executed beyond the per-merge sets.
- The SIM102 ruff finding is not fixed.
- Intermediate merge commits fail some registration assertions that the later test-fix commits repair, so only the tip is fully green.

agent=mx-feature fix-rounds=1 gates-first-pass=n
