# Release W1 report (mx-feature)

W1 done. Final SHA fb231d4 on claude/s2-release (merges e22dafe cp6-freeze, 93c1ffc 0d-d, then the re-pin commit). Tree clean.

**Conflicts**
- `docs/rulings/2026-10-28-stage2.md`: add/add in both merges. Each branch carried the old 181-line copy and the lane has 348 lines, so I kept the lane's.
- `tests/test_cp1b_registration.py`: methodology digest 43ce204f → c89118c6, recomputed from the merged bytes. `methodology.json` is 0932d9fb (T6-FINAL).
- `docs/reuse/manifest.json`: both sides appended records. I kept both.

**Re-pins (all pin hashes; no oracle value moved)**
- Builders: `business_context.py` 1672ba97 → 895cab5e in cp3c and cp4c. `legal/manifest.json` d6a8ec15 → 3da3b746 in cp2d, cp4 and cp4c; the manifest's readiness.py line moved 1038a37a → 119058ff. cpos `report_view.py` 51a6853e → 5c71a311; this was lane drift that predates the merges, and cpos failed to build until re-pinned. The cascade also re-pinned cp3c's pins of the cp2d manifest and builder, and cp4c's pins of the cp4 submissions and the cp3c manifest.
- `cases/legal/{render-expected,source-host-expected}.json` carry the legal manifest hash, so I re-pinned that.
- Regenerated manifests: cp2d, cp3c, cp4, cp4c, cpos. Regenerated submissions: cp4 and cp4c. In cp4 only the legal pin changed; cp4c's own sha changed. The other 12 owner oracles are byte-identical. `cases/PINS.json` was regenerated: 69 paths.
- Test pins: `tests/cp2d_runs.py` builder c274ce84 → fe138e2c. `tests/cp3c_runs.py` builder d160baa6 → 9a4bd933-derived current hash and manifest 06e39efb → current. The freeze's own re-pin missed the cp3c one.
- Lease headers: added an "Amended by Modules 2026-10-29 (Stage 2 close release W1…)" line with old → new sha to the CP2D, CP3C, CP4, CP4C and CPOS leases.

**Double rebuild**
- The scratch chain over the 17 builders in the freeze's `chain.sh` order, run from `fresh_copy.py` copies, ran clean.
- Two further scratch rebuilds (`r2` vs `r3`) are byte-identical, and equal the committed outputs.

**Manifest records**
- Methodology: `project_commit` e22dafe, prior 1bb6c0bc.
- The six 0d-d records (submission, cp3_relative_value, cp4_legal, business_context, readiness, source_context): `project_commit` 93c1ffc.
- `prior_project_sha256` is now taken from each merge's first parent. For submission.py the old value was wrong (6656846f vs actual 1b4aaa09); it is corrected. For the others I added the field.

**Gates**
- Pins check: exit 0.
- Fast set: 9095 passed, 4 skipped, exit 0. The first run had 3 failures from the stale test pins above, fixed.
- `ruff format --check`: exit 0.
- `ruff check` shows only the known findings: cp4_legal TRY004 :404, source_context ISC004 :581 and :583, and `test_cp1b_registration.py:98` PLW1510, which predates this change.
- `mypy --strict` on the six src files: exit 0. I also ran it on `tests/test_readiness_linear.py` after the edit below: clean.
- `noqa` count is 13.
- `type: ignore` was 6 because 0d-d's new test had one at `test_readiness_linear.py:518`. I removed it by typing `_synthetic_line` as pydantic_core `InitErrorDetails`; the count is now 5.

**Findings**
- The `docs/reuse/manifest.json` record for `bindings/shipped.py` has sha256 5c71a311, which is the current `report_view.py` hash. The real `shipped.py` hashes to 8cd0dbc9. This predates the merges; I did not touch it, and it needs an owner ruling.
- Older hash references in `docs/INTEGRATION.md`, `docs/QUEUE*.md`, `docs/reviews/*` and `docs/handoffs` are historical, and I left them.

Not verified: the full suite, other render suites, mutation and complexity gates, and the Opus review. The 0d-d timing tests ran only under the fast set. The `work/` freeze records (`report.md`) were not read in full. No test exercises the lease header text.

agent=mx-feature fix-rounds=0 gates-first-pass=n
