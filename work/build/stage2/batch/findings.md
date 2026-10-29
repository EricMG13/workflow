# Stage 2 batch: findings for the fix batch

## From the stage-level class test (a1a0574), Medium: round 3 says "nothing raises after the binding write"
- **CP-DR `gaps.*.questions.*.answer`.** It is built as `Claim.text` (`CPDR-ANS-<id>`) with no `RunText` check. A hostile value raises `ValidationError` inside `cpdr.submit` after the step is journaled. The follow-up then gets `stale_binding`, so the run is wedged. Strict xfail in `tests/test_stage2_classes.py`. Probe: `<S>/stage2-classes/verify_findings_owner.py`.
- **CP-3D `summary.text`.** It is built as `Claim.text` (`CP-3D-VIEW-01`) and fails the same way. Strict xfail; same probe.
