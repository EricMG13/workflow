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

## Lane C (review-C.md): CP-1C, CP-1D fixes, CP-L10 fix1, class test, integration all APPROVE; G1 I2 no finding
- **L1 (test isolation, incomplete fix).** `tests/test_owner_g1x.py:523` and `:640` still `delitem` CP-3D from `_CORES` and `_ENTRY_VALIDATORS`. Use `hide_row` at both sites. Probes: `<S>/stage2-review-C/pi2_*`, `pi3_*`.
- **L2 (D12 provenance), round 5 item 19.**
  - `prior_project_sha256` = the file's sha256 in the first parent of `project_commit`.
  - `project_commit` = a commit whose change brings that file to `sha256`.
  - Fix the Stage 2 records #27, #34, #29, #37, #39 and #40. #25 and the 2026-10-27 records predate this work and go to the owner.
  - Probe: `pd3_prior_vs_parent.py`.
- **L3.** CP-1C A1 (`tests/test_owner_cp1c.py:198-203`): assert the ids equal `[prepared-pack, CP-0, CP-1]` and the pack sha equals `snapshot.pack_sha256` (`pcc1` part c).
- **L4.** Pin the Stage 1 `SHIPPED_MAPS` order again: the base prefix is unchanged (`pi1_shipped_order_mutant.py`).
- **G1 I2: close the backlog row with a pinned test.** `StepSubmission.coherent_state` (`execution.py:71-72`) refuses a valid step that carries issues, so the verifier returns `identity_mismatch` even after a consistent reseal (`pg1_forged_valid_step_issues.py`).
