# Stage 2 batch: findings for the fix batch

## From the stage-level class test (a1a0574), Medium: round 3 says "nothing raises after the binding write"
- **CP-DR `gaps.*.questions.*.answer`.** It is built as `Claim.text` (`CPDR-ANS-<id>`) with no `RunText` check. A hostile value raises `ValidationError` inside `cpdr.submit` after the step is journaled. The follow-up then gets `stale_binding`, so the run is wedged. Strict xfail in `tests/test_stage2_classes.py`. Probe: `<S>/stage2-classes/verify_findings_owner.py`.
- **CP-3D `summary.text`.** It is built as `Claim.text` (`CP-3D-VIEW-01`) and fails the same way. Strict xfail; same probe.

## Lane B (review-B.md): CP-2D fix1 APPROVE, CP-4 fix1 APPROVE, CP-3C REQUEST CHANGES
- **CP-3C M1 (Medium, money-path test strength).** 8 of 17 mutants survive (`<S>/stage2-review-B/b5_cp3c_mutants.py`; probe `b9_cp3c_alias_untested.py`).
  - Alias presence check (`cp3c.py:2231`). Without it, an fy-2025-only facility is dropped silently.
  - Alias terms: `_ALIAS_TERMS` (`:2080`) and `_same` (`:2204`); currency, rate_type and scale are uncompared.
  - CP-2D scale check (`_cp2d_fact`, `:2306`).
  - View run-id check (`:2711`).
  - Reader `total_principal_payable` (`:2909`) and `base_claims` (`:2920`) pass with a constant equal to the oracle.

  Kill each one with a varied fixture.
- **CP-3C L1.** Add a `GAP_CURRENCY` tripwire (`b12_gap_currency_target.py`). Re-aim the release item at the CP-2D oracle; the release list is updated.
- **Info.**
  - `test_legal_render.py:36-38` and `:44` comments are stale after round 5 item 18.
  - `UNBOUND_FALLBACK` and the self-comparing note fallback are unreachable.
  - The connect fixture writes `cash_closing` as `calculated`, where the real head writes `source`.
