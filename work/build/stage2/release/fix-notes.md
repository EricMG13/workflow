# Release fix batch: collected findings and rulings

## Lane C (REQUEST CHANGES)
- **M1, ruled in scope.** Round 5 item 17 extends round 3 to "every module whose frozen oracle carries derived-fact citation lineage that differs … and any later module" at the close re-pin, so it is not an owner item. Test-first, apply `owners.blank.one_per_page` to:
  - CP-L10 `cpl10.py:573` (`_Cells.add`/`_unique`), together with its rule text (`cases/cpl10-owner/builder/build.py:994`) and `tests/test_method_cpl10.py:561-563`;
  - CP-2A `cp2a.py:812-821` `lineage`;
  - CP-2D sum copies `cp2d.py:2308-2310`, after confirming them by test.

  No literal oracle citation should move, because these modules bind citations at run time. If one does, re-pin it under item 17. Probe: `release-review-C/c8_cpl10_round3.py` must exit 0.
- **L1.** Refresh the 15 drifted file:line cites (`release-review-C/c1_cites.py` must exit 0).
- **L2.** `methods/cp1c.md:36`, `cp2g.md:54` and `cp4c.md:37` must name `deploy_workflow.owners.blank.one_per_page`.
- **L3.** The rulings heading at :354 should say CP-2D, not CP-3C.
- **Info.** cp1d's own `_one_per_page` should use the shared helper, since it differs only in its docstring.

## Q-C1 batch (user, 2026-10-29, approved via the LEAD peer)
- The FP-04 maturity wall becomes MODEL-owned in this release, as one batched oracle change. Contract: `release/qc1-brief.md`. Roles: preparer, then an mx-precise review, then a builder. The builder runs after the fix batch, because both touch cp2d.
