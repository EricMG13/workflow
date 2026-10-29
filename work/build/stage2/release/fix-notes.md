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

## Lane A (APPROVE; 0d-d's first review passed)
- **Low, F1 test.** `tests/test_rule_issue_bounds.py:422` must assert on the stored record (`_largest(fin._audit(...))`), as its siblings do. Probe `release-review-A/probes/a10_f1_record_bound_static.py` must exit 0.
- **Low, 0d-d timing margins.** These are thin: prefill_scopes, scans and prefill_periods are about 2.3-2.8x on either side of their bounds. Widen the RED/GREEN gap, for example with a larger input size, so that a revert still fails by at least 5x and the fix passes by at least 5x. Probe `a02_timing.py`.
- **Info.** Fix the verbatim note wording at `tests/test_defect_classes_shared.py:114`: `missing_source` goes through the absence-claim rule at `readiness.py:321`, not a prohibited-text check. Also reflow the docstring at `owner_workflow.py:893`.
- **Owner items (predate; recorded in lows.md):**
  - The CP-DR gap id of 139-153 characters wedges compose (`cpdr.py:481`; probe `a04_cpdr_long_gap_id.py`). It is the sibling of the approved question_id fix, and the user is asked whether to fix it here.
  - CP-1 accepts blank limitations (`a05_cp1_scope_limitation_sink.py`).
- **The W3 verbatim-sink question is closed.** CP-1's absence rule covers scope limitations (`source_context.py:333, 374-398`).
