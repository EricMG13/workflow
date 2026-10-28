# Stage 2 close release: collected items (Modules owns the release; LEAD stopped)

Each item names its source. Applied once, at the Stage 2 close, with the re-pin cascade.

## Oracles and pins (`cases/`)
- **CP-2G `expected.json` `cases.blocked.attempt_1.limitations`.** It lists only the High line. That run requests CP-2G alone, so CP-1D is unbound, and v13's rationale names `T1D.6.supported.total_leverage`. The real issues are `[assessment.rationale: Unresolved reference: T1D.6.supported.total_leverage, High…]`. The deferred test marks it as a strict xfail. Source: batch/cp2g-report.md release 1.
- **CP-2G view tree.** Commit `cases/cp2g-owner/cp2g-view-tree.json`.
- **CP-1D view tree.** Commit `cases/cp1d-owner/cp1d-view-tree.json`.
- **Re-pins in stage2-backlog.md.** They cover:
  - CP-2D and CP-3C deltas;
  - CP-3D `amortisation_nonzero`;
  - CP-1D recipe text;
  - CP-3C `frozen_inputs[8]` and `fact_copy_rule`;
  - CP-2G name;
  - CP-L10 lineage;
  - FP04 render (`CP2D_D7_DELTA`);
  - CP-2E blocked wording;
  - the CP-2D stale-head oracle wording (round 5 item 15).

- **CP-2H `expected.json` citations (round 5 item 17).** Several derived facts carry more than one quote from the same page:
  - positive: T2R.8.p01.notches, T2R.8.p01.lower_rated, T2R.8.p01.outlook_match, T2R.9.total.triggers, T2R.9.total.downgrade_down;
  - gap: T2R.9.total.triggers;
  - fixtures: the same facts, plus not_calculable_down.

  Re-pin to round 3: one citation per page, quoting the first input quote. Then switch CP-2H's own citations to the round 3 rule.
- **CP-2H view tree.** Commit `cases/cp2h-owner/cp2h-view-tree.json`.

## Leases and contract text
- **CP-2H lease.** `TriggerReport` is renamed `RatingTriggersReport`; add the TOOL-CONTRACT row.
- **CP-2G lease.**
  - :61 should show `Upstream` with `inherited`.
  - The scenario name comes from `T2B.1.<row>.name`.
  - Add the `base_period` invariant text.
  - Add the TOOL-CONTRACT row (text in batch/cp2g-report.md).
- **CP-1D lease.**
  - `parse_bridge(pages)` (round 5 item 13).
  - Add the TOOL-CONTRACT row (cp1d/report.md).
- **CP-2A lease.** The unit rule applies to settled operands only (lows.md).
- `MODULES.csv`: record the D3 closures once runs are accepted.

## LEAD product items
- **`lead/cp6-freeze`.** Merge 562a3bc.
- **`lead/0d-d`.** Finish it and review it (the user stopped its reviews earlier).
- **`is_blank`.** Extend it to Cc, default-ignorables and U+2800.
- **`citation_issues`.** Refuse a blank quote.
- **0d-c Lows.**
