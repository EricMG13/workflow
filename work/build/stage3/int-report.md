# I3 integration report (mx-feature a24d283c, claude/s3-int) - partial, disk full

I3 is only partly done. The disk filled up, so the render suites, mypy and the suppression counts did not run, and I could not remove my `.venv` symlink.

**Worktree and tip.** Worktree: `/Users/ericguei/Documents/Deploy Workflow/.claude/worktrees/agent-a24d283c066edc2c8`, branch `claude/s3-int` from 697fe8a. Tip is the commit "test: group c chart fixtures carry CP-1's chart identity..." (run `git rev-parse HEAD` for the SHA; I could not run it after the disk filled). Everything is committed. The untracked `.venv` symlink to the lane venv is still in the worktree root. Please delete it.

**Merges.** All seven merged with `--no-ff` in the brief's order.
- **oracles, cpos:** clean.
- **wire, w2a:** clean.
- **w2b conflicts:** `report_view.py` registration block and `test_chart_seam.py`. I kept both sides.
- **w2c conflicts:** `report_view.py` (5 hunks), `test_chart_seam.py` and `test_connect_cp2d.py`. I took our side of `report_view.py` and re-applied group c's two changes by hand: the `funding-gap` spec gets CP-3C as a producer, and group c's CR.2/CR.3 block is appended. In `test_connect_cp2d.py` I kept the chart-kind maturity-wall row and the CP-3C `funding-gap` row.
- **w2d conflicts:** `report_view.py` and `test_chart_seam.py`. I took our side and appended group d's `_register_group_d` block.
- **Registration order:** the registrations are appended in order a, b, c, d.
- **Registry test:** the group variants are now one test, `test_the_registry_holds_exactly_the_producers_of_the_four_w2_groups`. It asserts all 8 block ids, producer names and pathways, plus order. `test_chart_seam.py` passes (56).
- **`test_legal_render.py`:** no conflict. I added `# Stage 3 item 13: temporary until the legal oracle move` above `_producers_after_stage3` and `_note_after_stage3`.
- **`cases/PINS.json`:** it did not conflict, so I did not regenerate it by hand. `python3 -I cases/pins.py --check` exits 0 ("matches 86 paths").
- **`docs/reuse/manifest.json`:** it merged automatically, nothing was lost, and it is still valid JSON.

**D12.** I appended 5 `post_import_patches` records, each pointing to its merge commit and to the stage3 ruling as review.
- `bindings/cp1.py`: the w2a merge (65cc982), d94f6a46 to f1d39b51.
- `report_view.py`: w2a ec311130 to 0812b2c0, w2b to ac9565d9, w2c to fedb5fa0, and w2d to 1f50c7b9.
- I added no record for the wire merge. Its `charts.py` and `report_view.py` changes are already covered by the 80ab9f5 records.
- The D12 chain probe exits 0, and the last record of each file equals the file at HEAD (`report_view.py` 1f50c7b9, `charts.py` a1805bca, `cp1.py` f1d39b51).

**Method notes.** I changed only `src/deploy_vii/methods/cp1c.md:23`: RV.3 is now drawn by the report from the T1C.3/4/5 facts, not "deferred, tables only". I left `cp2h.md:20` ("the DR.6 chart") alone, because it is still true. No other method file mentions a figure id in a false way.

**One fix beyond the brief.** The first fast-set run had 20 failures in `test_chart_render_cr2.py` and `test_chart_render_cr3.py`, all `ValueError: Incomplete T4.14 chart identity`. Once the maturity wall became a chart, group c's CP-1 fixtures lacked the T4.14 chart-identity rows. In `tests/chart_wiring_c.py`, `cp2d_view` now passes `charts=True`, and `cp3c_view` applies `with_chart_identity` to the CP-1 module. The CR2/CR3 tests then pass (48). No oracle or lease changed.

**Gates.**
- `cases/pins.py --check`: exit 0.
- **Fast set:**
  - It ran once before the CR2/CR3 fix: 20 failures, all the T4.14 error above, 9952 passed, 1 xfailed.
  - It ran again after the fix, with `tests/test_owner_cpos.py` added: 9974 passed, 12 skipped, 1 xfailed (the DR.6 chip tripwire), 42 errors, exit nonzero.
  - All 42 errors are in `test_owner_cpos.py` and are `OSError: [Errno 28] No space left on device`.
  - The CPOS tests have therefore not run to completion. `test_owner_cpos` is not in the brief's fast set.
- **Render suites:** `test_financial_render.py`, `test_earnings_render.py` and `test_cp1_chart_render.py` ran 16 minutes (not the expected 48), then stopped on the full disk: 140 passed, 3 failed, 5 errors. The 8 failures and errors I traced were all disk-full errors. They need a rerun, and I could not confirm the CP-1 fixtures carry the S.5 rows.
- **`ruff format --check` on the changed `.py` files:** 5 files would be reformatted: the three oracle builders (`cases/cp1c-owner`, `cp3c-owner`, `cp4c-owner`), `cases/pins.py` and `src/deploy_workflow/financial_series.py`.
- **`ruff check` on the changed `.py` files:** every finding outside the known list is in the oracle builders, which I did not touch. The known `report_view.py` SIM102, `test_financial_series.py` C408s and `test_legal_render.py:220` C408 also appear.
- **mypy `--strict`:** not run.
- **Suppression counts:** not run.

**Disk.** `/System/Volumes/Data` is at 100%, with 122 MB free. About 61 GB sits in `/var/folders/81/bwblpst93lb6wb3lwrk8k6800000gn/T/pytest-of-ericguei`, mostly from other sessions' older runs. My attempt to delete the stale ones (more than 7 hours old) was denied by the permission classifier, and I did not work around it. Once that space is freed, a fresh agent should:
1. Delete the `.venv` link.
2. Rerun the three render suites, `test_owner_cpos.py`, mypy and the suppression counts.

Background processes: mine have exited. The other pytest processes visible belong to other sessions.

Not verified: render suites, `test_owner_cpos.py`, mypy, the noqa and type-ignore counts, the browser look of the new figures, and any tests I did not run.

Ledger: agent=mx-feature fix-rounds=0 gates-first-pass=n (fast set failed first, fixed once; the render suites ended on ENOSPC)
